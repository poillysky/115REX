"""NexusPHP 站点解析（搜索列表页 → 候选）。

做法对齐 MoviePilot 的 NexusPHP spider：先定位 `table.torrents`，
再按 DOM 结构取「行 → 列」，而不是在整页正则里按体积文本猜。
（MoviePilot 用 lxml + CSS 选择器；本项目只依赖 6 个包，故用等价的
手写 DOM 游标实现列定位，不引入新依赖。）

NexusPHP 的难点是**行是嵌套的**：标题单元格里还套着一个
`<table class="torrentname"><tr>…</tr></table>`，所以按 `</tr>` 非贪婪切行
会在标题处就被截断，后面的 size / seeders / snatches 列全部丢失。
这里改成「只认 `table.torrents` 的顶层 `<tr>`，跨过所有嵌套 table」。

只做解析，不发请求；请求与 Cookie 由 SiteProvider 负责，
这样「探测」和「搜索」共用同一份解析逻辑。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import quote, urljoin

from app.api import schemas

_DETAILS_RE = re.compile(r"details\.php\?(?:[^\"'&]*&(?:amp;)?)*id=(\d+)", re.I)
_DOWNLOAD_RE = re.compile(r"(download\.php\?[^\"'\s>]+)", re.I)
_MAGNET_RE = re.compile(r"(magnet:\?[^\"'\s<]+)", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_CAT_RE = re.compile(r"torrents\.php\?(?:[^\"'&]*&(?:amp;)?)*cat=(\d+)", re.I)
_CAT_CLASS_RE = re.compile(r"cat-(\d+)", re.I)
_CAT_HREF_RE = re.compile(r'href\s*=\s*["\'][^"\']*[?&](?:amp;)?cat=(\d+)', re.I)
_IMDB_RE = re.compile(r"imdb\.com/title/(tt\d+)", re.I)
_DOUBAN_RE = re.compile(r"douban\.com/subject/(\d+)", re.I)
_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(TB|GB|MB|KB|TiB|GiB|MiB|KiB|B)\b", re.I)
_YEAR_RE = re.compile(r"[(.．\s_\[【](19\d{2}|20\d{2})[)）\].．\s_\]】]")
_RESOLUTION_RE = re.compile(r"(2160p|1440p|1080[pi]|1080|720p|480p)", re.I)
_PASSKEY_RE = re.compile(r"passkey=([0-9a-zA-Z]+)", re.I)

_SIZE_UNIT = {
    "B": 1,
    "KB": 1024,
    "KIB": 1024,
    "MB": 1024**2,
    "MIB": 1024**2,
    "GB": 1024**3,
    "GIB": 1024**3,
    "TB": 1024**4,
    "TIB": 1024**4,
}

# 子分类里出现这些词就当作剧集，其余按电影
_SERIES_HINTS = ("TV", "TV Series", "TV Shows", "剧集", "电视剧", "综艺", "纪录片", "动画")


def _text(html: str) -> str:
    """去标签、解实体、压空白。所有文本抽取都走这里，避免各处重复。"""
    return re.sub(r"\s+", " ", unescape(_TAG_RE.sub(" ", html))).strip()


# 未登录标志：有密码框，或表单提交到 takelogin.php
_LOGIN_FORM_RE = re.compile(
    r"type\s*=\s*[\"']?password|action\s*=\s*[\"']?[^\"'\s>]*takelogin", re.I
)
# 已登录标志：NexusPHP 系模板的登出入口与用户面板
_LOGGED_IN_RE = re.compile(
    r"logout\.php|"
    r"mybonus\.php|"
    r"usercp\.php|"
    r"userdetails\.php\?id=|"
    r"userdetails\.php\?uuid=|"
    r"id\s*=\s*[\"']myitem[\"']|"
    r"class\s*=\s*[\"'][^\"']*user-info-side",
    re.I,
)


def is_logged_in(html: str) -> bool:
    """判断站点页面是否处于登录态，口径同 MoviePilot 的 `SiteUtils.is_logged_in`。

    先否决：页面存在密码框或 takelogin 表单 → 未登录。
    再确认：出现登出链接 / usercp / mybonus / userdetails 等用户入口 → 已登录。
    两者都没有时按未登录处理，宁可提示重填 Cookie 也不误报成功。
    """
    if not html or not html.strip():
        return False
    if _LOGIN_FORM_RE.search(html):
        return False
    return bool(_LOGGED_IN_RE.search(html))


def parse_size(text: str) -> int | None:
    """从一段文本里找第一个体积，如 `1.85 GB`。找不到返回 None。"""
    match = _SIZE_RE.search(text)
    if not match:
        return None
    value, unit = float(match.group(1)), match.group(2).upper()
    return int(value * _SIZE_UNIT.get(unit, 1))


def parse_resolution(text: str) -> str | None:
    match = _RESOLUTION_RE.search(text)
    if not match:
        return None
    value = match.group(1).lower()
    return "1080p" if value == "1080" else value


def _parse_seeders(row_html: str) -> int | None:
    """做种数。优先走列定位（见 `_cell_by_header`），这里只做兜底。"""
    for pattern in (
        r'class="[^"]*seeders[^"]*"[^>]*>(.*?)</',
        r"做种(?:者)?[:：]?\s*(?:<[^>]+>\s*)*(\d+)",
        r"seeds?[:：]?\s*(?:<[^>]+>\s*)*(\d+)",
    ):
        match = re.search(pattern, row_html, re.S | re.I)
        if match:
            digits = re.search(r"\d+", match.group(1))
            if digits:
                return int(digits.group())
    return None


def _parse_category(row_html: str, base_url: str) -> str | None:
    match = (
        _CAT_CLASS_RE.search(row_html)
        or _CAT_HREF_RE.search(row_html)
        or _CAT_RE.search(row_html)
    )
    if not match:
        return None
    return urljoin(base_url, f"torrents.php?cat={match.group(1)}")


def _parse_title(row_html: str) -> str:
    """标题优先取 details.php 链接的锚文本，取不到再退回整行文本。"""
    anchor = re.search(
        r'<a[^>]+href="[^"]*details\.php\?[^"]*"[^>]*>(.*?)</a>', row_html, re.S | re.I
    )
    if anchor:
        value = _text(anchor.group(1))
        # 个别模板锚文本是空图标，退回收起
        if value:
            return value
    return _text(row_html)


# 副标题行在标题格 `<br />` 之后：站点的语种标签 + 译名 / 类型 / 主演，是纯文本节点
_SUBTITLE_STOP_RE = re.compile(r"\s*\|\s*(类型|主演|导演|集数|年代|地区)\s*[:：]")
_LANG_BADGE_RE = re.compile(
    r"^(中字|简中|繁中|中英|英字|国语|粤语|日语|韩语|双语|字幕|高清|标清|官方|自制|转载)+$"
)

# ---- 促销 / 标记 ----
# 图标的 class 决定促销类型（NexusPHP 约定），alt 是站点给的英文名
_PROMO_CLASS_RE = re.compile(r'<img[^>]+class="[^"]*\bpro_([a-z0-9_]+)\b[^"]*"[^>]*>', re.I)
_PROMO_ALT_RE = re.compile(r'alt="([^"]+)"', re.I)
# 促销块紧跟着的 `<font>剩余时间：<span title="到期时间">1天11时</span></font>`
_PROMO_UNTIL_RE = re.compile(
    r"剩余时间[：:]?\s*<span[^>]*title=[\"'](\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)", re.I
)
_HR_RE = re.compile(r'class="[^"]*\bhitandrun\b', re.I)
_STICKY_RE = re.compile(r'title="([^"]*置顶[^"]*)"', re.I)
_BONUS_RE = re.compile(r"[\[【]\s*奖励魔力\s*[：:]\s*([\d,，]+)\s*[\]】]", re.I)
# 促销 class → 中文说明。未命中的直接回退用 alt 原文
_PROMO_LABELS: dict[str, str] = {
    "free": "免费",
    "2up": "2X",
    "free2up": "2X 免费",
    "50pctdown": "50% 下载",
    "30pctdown": "30% 下载",
    "50pctdown2up": "2X 50% 下载",
    "30pctdown2up": "2X 30% 下载",
}


def _parse_promo(row_html: str) -> tuple[str | None, str | None, bool]:
    """返回 (促销标签, 促销到期时间, 是否 H&R)。无促销时标签与时间为 None。"""
    label: str | None = None
    match = _PROMO_CLASS_RE.search(row_html)
    if match:
        key = match.group(1).lower()
        alt_match = _PROMO_ALT_RE.search(match.group(0))
        label = _PROMO_LABELS.get(key) or (alt_match.group(1) if alt_match else "") or key.upper()
    until_match = _PROMO_UNTIL_RE.search(row_html)
    until = until_match.group(1).replace("T", " ") if until_match else None
    return label, until, bool(_HR_RE.search(row_html))


def _parse_sticky(row_html: str) -> bool:
    return bool(_STICKY_RE.search(row_html))


def _parse_bonus(row_html: str) -> int | None:
    match = _BONUS_RE.search(row_html)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


# ---- 中文标题 ----
# 中文标题有三种落法：标题行 `<br>` 之后（CarPT 等）、`details.php` 的 title 属性、
# 以及同格里的 IMDb / 豆瓣外链。前两种覆盖绝大多数行，最后一种是兜底。
_TITLE_ATTR_RE = re.compile(
    r'<a[^>]+href="[^"]*details\.php\?[^"]*"[^>]*\btitle="([^"]*)"', re.I
)
# 站点给外链挂的文字就是中文片名（`<a href="...douban.com...">锦衣之下</a>`）
_CN_LINK_RE = re.compile(
    r'<a[^>]+href="[^"]*(?:douban\.com|imdb\.com|themoviedb\.org)[^"]*"[^>]*>(.*?)</a>',
    re.S | re.I,
)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# 混着英文的标题里，这些词属于规格而不是片名
_SPEC_WORD_RE = re.compile(
    r"\b(?:FLAC|APE|WAV|DSF|DSD|DTS|AAC|MP3|分轨|分軌|整轨|整軌|镜像|Mirror|Hi-?Res|"
    r"\d{3,4}p|\d{3,4}i|x26[45]|H\.?26[45]|HEVC|AVC|BluRay|Blu-?ray|WEB-?DL|WEB-?Rip|"
    r"HDTV|DVDRip|REMUX|S\d{2}E?\d*|E\d{2,})\b",
    re.I,
)


def _looks_like_name(text: str) -> bool:
    """判断一段标题文字是不是「片名」而不是规格。

    纯中文直接算片名；中英混排的要排除「群星 - 专辑 2003 - FLAC 分轨」这类音乐发布，
    它的中文前半段是歌手和专辑，后半段全是码率与音轨格式。
    """
    if not _CJK_RE.search(text):
        return False
    if len(_CJK_RE.findall(text)) < 2:
        return False
    return not _SPEC_WORD_RE.search(text)


def _parse_title_cn(row_html: str) -> str:
    """中文标题：优先取标题行 `<br>` 之后的译名，其次 title 属性，最后外链锚文本。"""
    sub = _parse_subtitle(row_html)
    if _looks_like_name(sub):
        return sub
    attr = _TITLE_ATTR_RE.search(row_html)
    if attr:
        text = unescape(attr.group(1)).strip()
        if _looks_like_name(text):
            return text
    for anchor in _CN_LINK_RE.findall(row_html):
        text = _text(anchor)
        if _looks_like_name(text):
            return text.strip(" .-|｜*")
    return ""


def _parse_subtitle(row_html: str) -> str:
    """取标题下方的中文译名等附加信息，去掉站点的语种角标与「类型/主演」尾巴。"""
    anchor = re.search(
        r'<a[^>]+href="[^"]*details\.php\?[^"]*"[^>]*>.*?</a>(.*)', row_html, re.S | re.I
    )
    if anchor is None:
        return ""
    tail = anchor.group(1)
    # 只保留第一个 <br> 之后、下一个单元格之前的文本；角标 span 属于副标题行，不能当边界
    br = re.search(r"<br\s*/?>(.*)", tail, re.S | re.I)
    if br is None:
        return ""
    segment = re.split(r"<t[dh]\b|<table\b|</t[dh]\s*>", br.group(1), maxsplit=1)[0]
    text = _text(segment)
    # 站点角标是独立 span，_text 后会贴在开头，逐词剥掉
    words = text.split(" ")
    while words and _LANG_BADGE_RE.match(words[0]):
        words.pop(0)
    text = " ".join(words)
    text = _SUBTITLE_STOP_RE.split(text)[0]
    # 副标题后半段是站点的语种标记（`｜ *国语|中字*`），只留译名本体
    text = re.split(r"\s*[|｜]\s*\*", text)[0]
    return text.strip(" .-|｜*")


_TABLE_OPEN_RE = re.compile(r"<table\b([^>]*)>", re.I)
_TABLE_TOKEN_RE = re.compile(r"<table\b[^>]*>|</table\s*>", re.I)
_ROW_OPEN_RE = re.compile(r"<tr\b[^>]*>", re.I)
_CELL_OPEN_RE = re.compile(r"<t([dh])\b[^>]*>", re.I)
_TORRENTS_CLASS_RE = re.compile(r'class\s*=\s*["\'][^"\']*\btorrents\b', re.I)

# 表头关键词 → 字段。NexusPHP 各站表头文字不同，因此按「包含」匹配，并带上
# 表头里的 <img alt="size"> 这类图标标记（MoviePilot 的选择器也是按列号取的）。
_HEADER_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("size", ("size", "大小", "体积")),
    ("seeders", ("seeder", "seeds", "做种")),
    ("leechers", ("leecher", "下载中", "吸血")),
    ("snatched", ("snatch", "完成", "下载量")),
    ("time", ("time", "时间")),
)
_IMG_ALT_RE = re.compile(r'alt\s*=\s*["\']([^"\']*)["\']', re.I)


def _outer_html(html: str, start: int) -> str:
    """从 `start` 处的 `<table …>` 起截到配对的 `</table>`，跨过所有嵌套 table。"""
    depth = 0
    for token in _TABLE_TOKEN_RE.finditer(html, start):
        depth += -1 if token.group().lstrip("<").startswith("/") else 1
        if depth == 0:
            return html[start : token.end()]
    return html[start:]


def _find_element(html: str, tag: str, start: int = 0) -> tuple[int, int] | None:
    """找 `tag` 元素的开标签位置与配对闭合标签位置，支持同名嵌套。"""
    open_re = re.compile(rf"<{tag}\b", re.I)
    close_re = re.compile(rf"</{tag}\s*>", re.I)
    opening = open_re.search(html, start)
    if not opening:
        return None
    depth = 0
    for token in re.finditer(rf"<{tag}\b|</{tag}\s*>", html[opening.start() :], re.I):
        depth += -1 if token.group().startswith("</") else 1
        if depth == 0:
            return opening.start(), opening.start() + token.end()
    return opening.start(), len(html)


def _split_top_level(html: str, tag: str) -> list[str]:
    """按 `tag` 切分，只取当前层，不进入同名子元素内部。

    用于把 `table.torrents` 切成顶层 `<tr>`，以及把 `<tr>` 切成顶层 `<td>`。
    """
    parts: list[str] = []
    opening = re.compile(rf"<{tag}\b[^>]*>", re.I)
    token_re = re.compile(rf"<{tag}\b[^>]*>|</{tag}\s*>", re.I)
    pos = 0
    while True:
        match = opening.search(html, pos)
        if not match:
            return parts
        depth = 0
        for token in token_re.finditer(html, match.start()):
            depth += -1 if token.group().startswith("</") else 1
            if depth == 0:
                parts.append(html[match.start() : token.end()])
                pos = token.end()
                break
        else:
            parts.append(html[match.start() :])
            return parts


def _cells(row_html: str) -> list[str]:
    """取一行里的顶层单元格（标题格里嵌套的 table 不会混进来）。"""
    return _split_top_level(row_html, "td") or _split_top_level(row_html, "th")


def _column_map(header_row: str) -> dict[str, int]:
    """从表头行推出「字段 → 列号」。表头靠 `size`/`seeders` 等文字或图标 alt 标记。"""
    columns: dict[str, int] = {}
    for index, cell in enumerate(_cells(header_row)):
        haystack = " ".join([_text(cell), *[a for a in _IMG_ALT_RE.findall(cell)]]).lower()
        for key, words in _HEADER_KEYS:
            if key in columns:
                continue
            if any(word.lower() in haystack for word in words):
                columns[key] = index
                break
    return columns


def _cell_text(row_html: str, index: int | None) -> str:
    cells = _cells(row_html)
    if index is None or index >= len(cells):
        return ""
    return _text(cells[index])


def _integer_or_none(text: str) -> int | None:
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


@dataclass(frozen=True)
class ParsedTorrent:
    """列表页里一条种子。downloadUrl 已补全为绝对地址并带上 passkey（若站点提供）。"""

    torrent_id: str
    title: str
    subtitle: str
    download_url: str
    magnet: str | None
    size_bytes: int | None
    seeders: int | None
    category: str | None
    snatched: int | None = None
    promo: str | None = None
    promo_until: str | None = None
    hit_and_run: bool = False
    sticky: bool = False
    bonus: int | None = None


def _torrent_rows(html: str) -> tuple[list[str], dict[str, int]]:
    """取出 `table.torrents` 的顶层数据行与表头列映射。

    MoviePilot 用 `table.torrents > tr` 拿行；这里等价地：
    1. 找到 class 含 `torrents` 的 table，跨过嵌套 table 截出整表；
    2. 只切顶层 `<tr>`，标题格里那个 `table.torrentname` 的行不会被带出来；
    3. 第一行含 `details.php` 的行之前视为表头，用来推列号。
    """
    opening = None
    for match in _TABLE_OPEN_RE.finditer(html):
        if _TORRENTS_CLASS_RE.search(match.group(0)):
            opening = match
            break
    if opening is None:
        return [], {}

    rows = _split_top_level(_outer_html(html, opening.start()), "tr")
    header_row = ""
    body: list[str] = []
    for row in rows:
        if "details.php" in row:
            body.append(row)
        elif not body:
            header_row = row
    return body, _column_map(header_row) if header_row else {}


def parse_torrent_list(html: str, base_url: str) -> list[ParsedTorrent]:
    """从搜索结果页抽出种子行。跳过置顶广告、无下载地址的行。"""
    rows, columns = _torrent_rows(html)
    result: list[ParsedTorrent] = []
    seen: set[str] = set()
    for row_html in rows:
        detail = _DETAILS_RE.search(row_html)
        magnet = _MAGNET_RE.search(row_html)
        if detail is None and magnet is None:
            continue
        torrent_id = detail.group(1) if detail else ""
        if torrent_id and torrent_id in seen:
            continue
        if not torrent_id:
            # 只有磁力时用磁力当唯一标识，便于后续去重
            torrent_id = f"m{abs(hash(magnet.group(1))) % 10**10}"
        download = _DOWNLOAD_RE.search(row_html)
        download_url = urljoin(base_url, unescape(download.group(1))) if download else ""
        if not download_url and not magnet:
            continue
        seen.add(torrent_id)
        title = _parse_title(row_html)
        # 大小/做种优先按表头列号取（不受标题里数字干扰），取不到再退回整行正则
        size_text = _cell_text(row_html, columns.get("size"))
        seeders_text = _cell_text(row_html, columns.get("seeders")) or _cell_text(
            row_html, columns.get("leechers")
        )
        seeders = _integer_or_none(seeders_text)
        promo, promo_until, hit_and_run = _parse_promo(row_html)
        result.append(
            ParsedTorrent(
                torrent_id=torrent_id,
                title=title or f"种子 {torrent_id}",
                subtitle=_parse_title_cn(row_html),
                download_url=download_url,
                magnet=unescape(magnet.group(1)) if magnet else None,
                size_bytes=parse_size(size_text) if size_text else parse_size(row_html),
                seeders=seeders if seeders is not None else _parse_seeders(row_html),
                category=_parse_category(row_html, base_url),
                snatched=_integer_or_none(_cell_text(row_html, columns.get("snatched"))),
                promo=promo,
                promo_until=promo_until,
                hit_and_run=hit_and_run,
                sticky=_parse_sticky(row_html),
                bonus=_parse_bonus(row_html),
            )
        )
    return result


def build_search_url(base_url: str, keyword: str) -> str:
    """NexusPHP 通用搜索入口。同时带 search_area/search_mode，多数变体都能接受。"""
    return (
        urljoin(base_url.rstrip("/") + "/", "torrents.php")
        + f"?search={quote(keyword)}&search_area=0&search_mode=0"
    )


def _guess_year(title: str) -> int | None:
    match = _YEAR_RE.search(f" {title} ")
    return int(match.group(1)) if match else None


def _clean_title(title: str) -> str:
    """作品层标题：去掉站点附加的促销前后缀与方括号标记。"""
    value = re.sub(r"\[[^\]]*\]", " ", title)
    value = re.sub(r"【[^】]*】", " ", value)
    value = re.sub(r"(Free|2x|2X|50%|免费|促销)", " ", value)
    return re.sub(r"\s+", " ", value).strip(" .-_|") or title


def _guess_kind(title: str, category: str | None) -> str:
    haystack = f"{title} {category or ''}"
    lowered = haystack.lower()
    if re.search(r"\bS\d{1,2}(E\d{1,3})?\b", haystack, re.I) or re.search(
        r"第[一二三四五六七八九十\d]+季|全\d+集", haystack
    ):
        return "series"
    if any(hint.lower() in lowered for hint in _SERIES_HINTS):
        return "series"
    return "movie"


def to_candidate(
    torrent: ParsedTorrent,
    *,
    site_id: int,
    site_name: str,
    download_available: bool,
    download_reason: str | None,
) -> tuple[schemas.CandidateView, str, int | None, str]:
    """转成候选，并给出作品层需要的标题 / 年份 / 类型。

    ref 用 `站点ID:种子ID`，后续下载动作据此回找站点与种子，
    因此搜索结果不需要在服务端做缓存。
    """
    title = _clean_title(torrent.title)
    year = _guess_year(torrent.title)
    kind = _guess_kind(torrent.title, torrent.category)
    actions = [
        schemas.CandidateActionView(
            kind="download",
            label="推送到 qBittorrent",
            available=download_available,
            reason=download_reason if not download_available else None,
        )
    ]
    candidate = schemas.CandidateView(
        ref=f"{site_id}:{torrent.torrent_id}",
        providerId=f"site-{site_id}",
        providerName=site_name,
        title=torrent.title,
        sizeBytes=torrent.size_bytes,
        resolution=parse_resolution(torrent.title),
        sourceType="PT 种子",
        completeness="full",
        seeders=torrent.seeders,
        actions=actions,
    )
    return candidate, title, year, kind


def apply_passkey(download_url: str, passkey: str) -> str:
    """站点若在列表页给了 passkey 就用页面的；没给则按配置里的补上。"""
    if not download_url or not passkey:
        return download_url
    if _PASSKEY_RE.search(download_url):
        return download_url
    joiner = "&" if "?" in download_url else "?"
    return f"{download_url}{joiner}passkey={passkey}"


