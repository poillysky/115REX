"""115 集成（docs/06 §4）。

凭据只在集成层解密；对外只暴露「列目录 / 转存 / 解析直链」这些能力。
直链解析尚未实现（docs/06 §11 Q1），调用方拿到 NotReady 时按可重试错误处理。

扫码登录走 115 开放平台的设备码流程（PKCE），四步：
申请设备码 → 查扫码状态 → 设备码换令牌 → 刷新令牌。
协议细节照 MoviePilot 的实测写法，错误一律收敛成 P115TransportError。
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Any

import httpx

_DEVICE_CODE_URL = "https://passportapi.115.com/open/authDeviceCode"
_QRCODE_STATUS_URL = "https://qrcodeapi.115.com/get/status/"
_DEVICE_CODE_TO_TOKEN_URL = "https://passportapi.115.com/open/deviceCodeToToken"
_REFRESH_TOKEN_URL = "https://passportapi.115.com/open/refreshToken"
# 账号信息（容量 / 昵称）。与扫码登录不同，这里带 Bearer 访问令牌
_USER_INFO_URL = "https://proapi.115.com/open/user/info"
_FILES_URL = "https://proapi.115.com/open/ufile/files"
_FOLDER_ADD_URL = "https://proapi.115.com/open/folder/add"
_FILE_UPDATE_URL = "https://proapi.115.com/open/ufile/update"
_FILE_DELETE_URL = "https://proapi.115.com/open/ufile/delete"
_FILE_DOWNURL = "https://proapi.115.com/open/ufile/downurl"
_VIDEO_PLAY_URL = "https://proapi.115.com/open/video/play"
_OFFLINE_QUOTA_URL = "https://proapi.115.com/open/offline/get_quota_info"
_OFFLINE_TASK_LIST_URL = "https://proapi.115.com/open/offline/get_task_list"
_OFFLINE_ADD_URLS_URL = "https://proapi.115.com/open/offline/add_task_urls"
_OFFLINE_DEL_TASK_URL = "https://proapi.115.com/open/offline/del_task"

# 扫码状态接口实测偶发慢，比申请设备码留更长的等待
_TIMEOUT_SECONDS = 20
_STATUS_TIMEOUT_SECONDS = 10

# 115 业务码：0 成功；未确认扫码时换令牌会返回这个码，属正常等待态
_CODE_OK = 0
_CODE_NOT_CONFIRMED = 40101017
# 刷新过于频繁：令牌本身有效，只是要求放慢，不能当成授权失效
_CODE_REFRESH_THROTTLED = 40140117
# 未登录 / 访问令牌过期或校验失败：需要先刷新再重试，刷新也失败才算授权作废
_CODES_UNAUTHORIZED = (40140101, 40140102, 40140126, 990001)

# 扫码状态：0 待扫、1 已扫、2 已确认、-1 过期、-2 取消
_STATUS_PENDING = 0
_STATUS_SCANNED = 1
_STATUS_CONFIRMED = 2

_UA = "W115Storage/2.0"


class NotReady(RuntimeError):
    """适配器未就绪。play 服务据此返回 PLAY_ADAPTER_NOT_READY。"""


class P115TransportError(RuntimeError):
    """115 请求失败。retryable 为真表示网络或上游抖动，稍后重试即可。

    throttled 单独标出「刷新过于频繁」：它不是授权失效，也不该置 expired，
    只是要求放慢节奏，调用方等冷却后重试即可。

    unauthorized 标出「令牌不被承认」（HTTP 401 或 115 的未登录业务码），
    调用方据此决定要不要先刷新再重试。

    code 是 115 回的业务码，只有它非空才说明这确实是 115 给出的判定；
    请求根本没送到、参数写坏了时留空，调用方不能据此认定令牌作废。
    """

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = True,
        throttled: bool = False,
        unauthorized: bool = False,
        code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.throttled = throttled
        self.unauthorized = unauthorized
        self.code = code


@dataclass(frozen=True, slots=True)
class DeviceCode:
    """扫码登录的设备码。code_verifier 只在服务端留存，绝不下发。"""

    uid: str
    time: int
    sign: str
    qrcode: str
    code_verifier: str


@dataclass(frozen=True, slots=True)
class QrcodeStatus:
    """扫码状态。value 为 115 原始状态码，confirmed 表示用户已在手机端确认。"""

    value: int
    message: str = ""
    expired: bool = False

    @property
    def confirmed(self) -> bool:
        return self.value == _STATUS_CONFIRMED

    @property
    def scanned(self) -> bool:
        return self.value == _STATUS_SCANNED


@dataclass(frozen=True, slots=True)
class UserInfo:
    """账号概况。容量单位为字节；115 未返回时按 0。

    avatar_url / vip_* 来自 open/user/info，缺字段时留空，不阻塞绑定。
    """

    name: str
    total_bytes: int
    used_bytes: int
    avatar_url: str = ""
    vip_level: str = ""
    vip_expire: int = 0


@dataclass(frozen=True, slots=True)
class DrivePathNode:
    """面包屑节点。根目录 cid 为 \"0\"。"""

    cid: str
    name: str


@dataclass(frozen=True, slots=True)
class DriveEntry:
    """网盘条目。is_dir 为真时 size 恒为 0。"""

    id: str
    parent_id: str
    name: str
    is_dir: bool
    size: int
    modified_at: int
    extension: str = ""
    pick_code: str = ""
    # 列表缩略图（图片 thumb；视频真实封面若有）。静态占位图不填。
    thumb_url: str = ""
    # 图片大图预览（uo）；无则前端可回退 thumb / 直链
    preview_url: str = ""


@dataclass(frozen=True, slots=True)
class DriveOpenResult:
    """打开文件结果：直链或可播地址。"""

    kind: str  # image | video | file
    url: str
    name: str
    mime_hint: str = ""


@dataclass(frozen=True, slots=True)
class DriveListing:
    """一层目录列表 + 面包屑。"""

    cid: str
    count: int
    offset: int
    limit: int
    entries: tuple[DriveEntry, ...]
    path: tuple[DrivePathNode, ...]


@dataclass(frozen=True, slots=True)
class OfflineQuota:
    """云下载月度配额。"""

    surplus: int
    used: int
    count: int


@dataclass(frozen=True, slots=True)
class OfflineTask:
    """一条云下载任务。status: -1 失败 / 0 等待 / 1 下载中 / 2 完成。"""

    info_hash: str
    name: str
    size: int
    add_time: int
    status: int
    status_text: str
    percent_done: float
    url: str
    file_id: str
    pick_code: str
    wp_path_id: str
    file_category: int
    rate_download: int
    left_time: int


@dataclass(frozen=True, slots=True)
class OfflineTaskPage:
    """云下载任务分页。"""

    page: int
    page_count: int
    count: int
    tasks: tuple[OfflineTask, ...]


@dataclass(frozen=True, slots=True)
class OfflineAddResult:
    """添加链接任务的单条结果。"""

    url: str
    info_hash: str = ""
    name: str = ""
    ok: bool = True
    message: str = ""


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    # 未确认扫码等业务态；非空时其余字段为空
    pending: bool = False


def make_code_verifier() -> str:
    """PKCE 校验码：96 字节 URL 安全随机串截到 128 位。"""
    return secrets.token_urlsafe(96)[:128]


def code_challenge(verifier: str) -> str:
    """PKCE 挑战码：校验码的 SHA256 再做 Base64（不带填充）。"""
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


_IMAGE_EXTS = frozenset({"jpg", "jpeg", "png", "gif", "webp", "bmp", "heic", "svg", "ico"})
_VIDEO_EXTS = frozenset({"mp4", "mkv", "avi", "mov", "wmv", "flv", "ts", "m2ts", "webm", "rmvb"})
_AUDIO_EXTS = frozenset({"mp3", "flac", "aac", "wav", "m4a", "ogg", "wma", "opus"})
_PDF_EXTS = frozenset({"pdf"})
_TEXT_EXTS = frozenset(
    {
        "txt",
        "md",
        "markdown",
        "json",
        "xml",
        "csv",
        "tsv",
        "log",
        "srt",
        "ass",
        "ssa",
        "vtt",
        "html",
        "htm",
        "css",
        "js",
        "ts",
        "py",
        "go",
        "rs",
        "yaml",
        "yml",
        "toml",
        "ini",
        "conf",
        "sql",
        "nfo",
    }
)


def _open_kind(extension: str) -> str:
    ext = extension.lower().lstrip(".")
    if ext in _IMAGE_EXTS:
        return "image"
    if ext in _VIDEO_EXTS:
        return "video"
    if ext in _AUDIO_EXTS:
        return "audio"
    if ext in _PDF_EXTS:
        return "pdf"
    if ext in _TEXT_EXTS:
        return "text"
    return "file"


def _is_real_thumb(url: str) -> bool:
    """过滤 115 静态分辨率徽章（/static/plug/vq/...），只留真实缩略图。"""
    if not url:
        return False
    lowered = url.lower()
    if "/static/" in lowered:
        return False
    return lowered.startswith("http://") or lowered.startswith("https://")


def _thumb_url(item: dict[str, Any]) -> str:
    for key in ("thumb", "u"):
        url = str(item.get(key) or "").strip()
        if _is_real_thumb(url):
            return url
    # 视频偶发封面；静态徽章丢弃
    url = str(item.get("v_img") or "").strip()
    return url if _is_real_thumb(url) else ""


def _preview_url(item: dict[str, Any]) -> str:
    url = str(item.get("uo") or "").strip()
    if _is_real_thumb(url):
        return url
    return _thumb_url(item)


def _space_size(space: dict[str, Any], key: str) -> int:
    """115 把容量放在 rt_space_info.<key>.size；缺字段或类型异常按 0 处理。"""
    node = space.get(key)
    if not isinstance(node, dict):
        return 0
    return _optional_int(node.get("size")) or 0


class P115Client:
    """同步 httpx 客户端。扫码授权是低频动作，不需要异步链路。"""

    def __init__(self, proxy: str = "") -> None:
        # 代理来自设置页的网络出口配置；留空直连
        self._proxy = proxy.strip() or None

    def _client(self, timeout: float = _TIMEOUT_SECONDS) -> httpx.Client:
        # trust_env=False：不让机器上的 HTTP_PROXY 环境变量偷偷改变出口
        return httpx.Client(
            headers={
                "Accept": "application/json",
                "User-Agent": _UA,
            },
            proxy=self._proxy,
            timeout=timeout,
            follow_redirects=True,
            trust_env=False,
        )

    def request_device_code(self, app_id: str) -> DeviceCode:
        """申请扫码设备码，内含 PKCE 校验码生成。"""
        verifier = make_code_verifier()
        payload = self._post(
            _DEVICE_CODE_URL,
            {
                "client_id": app_id,
                "code_challenge": code_challenge(verifier),
                "code_challenge_method": "sha256",
            },
        )
        data = self._data(payload, "申请 115 扫码登录失败")
        uid = str(data.get("uid") or "").strip()
        sign = str(data.get("sign") or "").strip()
        qrcode = str(data.get("qrcode") or "").strip()
        time_value = _optional_int(data.get("time"))
        if not uid or not sign or not qrcode or time_value is None:
            raise P115TransportError("115 返回的扫码信息不完整", retryable=False)
        return DeviceCode(
            uid=uid, time=time_value, sign=sign, qrcode=qrcode, code_verifier=verifier
        )

    def poll_qrcode(self, uid: str, time_value: int, sign: str) -> QrcodeStatus:
        """查一次扫码状态。已过期 / 已取消折算成 expired。

        该接口实测偶发单次超时，就地重试一次再判定失败。
        """
        last_error: P115TransportError | None = None
        for _ in range(2):
            try:
                payload = self._get_qrcode_status(uid, time_value, sign)
                break
            except P115TransportError as exc:
                last_error = exc
        else:
            raise last_error or P115TransportError("无法连接 115，请稍后重试。")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise P115TransportError("115 返回了无效的扫码状态")
        value = _optional_int(data.get("status"))
        if value is None:
            raise P115TransportError("115 返回了无效的扫码状态")
        message = str(data.get("msg") or "").strip()
        return QrcodeStatus(
            value=value,
            message=message,
            expired=value not in (_STATUS_PENDING, _STATUS_SCANNED, _STATUS_CONFIRMED),
        )

    def _get_qrcode_status(self, uid: str, time_value: int, sign: str) -> dict[str, Any]:
        with self._client(_STATUS_TIMEOUT_SECONDS) as client:
            try:
                response = client.get(
                    _QRCODE_STATUS_URL,
                    params={"uid": uid, "time": time_value, "sign": sign},
                )
            except httpx.HTTPError as exc:
                raise P115TransportError("无法连接 115，请稍后重试。") from exc
        if response.status_code >= 400:
            raise P115TransportError("115 拒绝了扫码状态查询")
        return self._json(response)

    def exchange_device_code(self, uid: str, code_verifier: str) -> TokenPair:
        """设备码换令牌。用户还没确认时返回 pending，不算失败。"""
        payload = self._post(
            _DEVICE_CODE_TO_TOKEN_URL,
            {"uid": uid, "code_verifier": code_verifier},
        )
        code = _optional_int(payload.get("code"))
        # 已确认但令牌还没生成时 115 也可能回「未确认」，继续轮询即可
        if code in (_CODE_NOT_CONFIRMED, *_CODES_UNAUTHORIZED):
            return TokenPair(pending=True)
        data = self._data(payload, "115 授权失败，请重新扫码")
        return self._tokens(data, "115 未返回有效的令牌")

    def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """用刷新令牌换新的访问令牌。限频单独标记，调用方据此冷却重试。"""
        payload = self._post(_REFRESH_TOKEN_URL, {"refresh_token": refresh_token})
        code = _optional_int(payload.get("code"))
        if code == _CODE_REFRESH_THROTTLED:
            raise P115TransportError(
                "115 刷新过于频繁，请稍后重试", throttled=True, code=code
            )
        data = self._data(payload, "115 令牌刷新失败")
        return self._tokens(data, "115 未返回有效的令牌")

    def user_info(self, access_token: str) -> UserInfo:
        """读账号信息。字段缺失按 0 处理，不让容量展示阻塞绑定流程。"""
        with self._client() as client:
            try:
                response = client.get(
                    _USER_INFO_URL, headers={"Authorization": f"Bearer {access_token}"}
                )
            except httpx.HTTPError as exc:
                raise P115TransportError("无法连接 115，请稍后重试。") from exc
        if response.status_code == 401:
            raise P115TransportError("115 授权已失效", retryable=False, unauthorized=True)
        if response.status_code >= 400:
            raise P115TransportError("115 账号信息读取失败")
        # 115 有时以 HTTP 200 + 未登录业务码回令牌失效，同样按 401 处理
        payload = self._json(response)
        code = _optional_int(payload.get("code"))
        if code in _CODES_UNAUTHORIZED:
            raise P115TransportError("115 授权已失效", retryable=False, unauthorized=True)
        data = self._data(payload, "115 账号信息读取失败")
        space = data.get("rt_space_info") if isinstance(data.get("rt_space_info"), dict) else {}
        vip = data.get("vip_info") if isinstance(data.get("vip_info"), dict) else {}
        # 头像优先大图；都空就留空，前端退回品牌标
        avatar = (
            str(data.get("user_face_l") or data.get("user_face_m") or data.get("user_face_s") or "")
            .strip()
        )
        return UserInfo(
            name=str(data.get("user_name") or "").strip(),
            total_bytes=_space_size(space, "all_total"),
            used_bytes=_space_size(space, "all_use"),
            avatar_url=avatar,
            vip_level=str(vip.get("level_name") or "").strip(),
            vip_expire=max(_optional_int(vip.get("expire")) or 0, 0),
        )

    def list_files(
        self,
        access_token: str,
        *,
        cid: str = "0",
        offset: int = 0,
        limit: int = 200,
        order: str = "user_utime",
        asc: bool = False,
    ) -> DriveListing:
        """列一层目录。根目录 cid=\"0\"；show_dir=1 把文件夹也列出来。"""
        folder_id = str(cid or "0").strip() or "0"
        page_size = max(1, min(int(limit), 1000))
        page_offset = max(0, int(offset))
        payload = self._auth_get(
            access_token,
            _FILES_URL,
            params={
                "cid": folder_id,
                "limit": str(page_size),
                "offset": str(page_offset),
                "show_dir": "1",
                "cur": "1",
                "o": order or "user_utime",
                "asc": "1" if asc else "0",
            },
            fallback="115 列目录失败",
        )
        raw_items = payload.get("data")
        if not isinstance(raw_items, list):
            raw_items = []
        entries: list[DriveEntry] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            entry_id = str(item.get("fid") or "").strip()
            name = str(item.get("fn") or "").strip()
            if not entry_id or not name:
                continue
            is_dir = str(item.get("fc") or "") == "0"
            extension = "" if is_dir else str(item.get("ico") or "").strip()
            thumb = "" if is_dir else _thumb_url(item)
            preview = "" if is_dir else _preview_url(item)
            entries.append(
                DriveEntry(
                    id=entry_id,
                    parent_id=str(item.get("pid") or folder_id),
                    name=name,
                    is_dir=is_dir,
                    size=0 if is_dir else max(_optional_int(item.get("fs")) or 0, 0),
                    modified_at=max(_optional_int(item.get("upt")) or 0, 0),
                    extension=extension,
                    pick_code=str(item.get("pc") or "").strip(),
                    thumb_url=thumb,
                    preview_url=preview,
                )
            )
        path_nodes: list[DrivePathNode] = [DrivePathNode(cid="0", name="根目录")]
        raw_path = payload.get("path")
        if isinstance(raw_path, list):
            for node in raw_path:
                if not isinstance(node, dict):
                    continue
                node_cid = str(node.get("cid") or "").strip()
                node_name = str(node.get("name") or "").strip()
                if not node_cid or node_cid == "0":
                    continue
                path_nodes.append(DrivePathNode(cid=node_cid, name=node_name or node_cid))
        # 当前目录若不在 path 里（少数响应），补上
        current_cid = str(payload.get("cid") or folder_id)
        if current_cid != "0" and all(node.cid != current_cid for node in path_nodes):
            path_nodes.append(DrivePathNode(cid=current_cid, name=current_cid))
        return DriveListing(
            cid=current_cid,
            count=max(_optional_int(payload.get("count")) or len(entries), 0),
            offset=max(_optional_int(payload.get("offset")) or page_offset, 0),
            limit=page_size,
            entries=tuple(entries),
            path=tuple(path_nodes),
        )

    def create_folder(self, access_token: str, *, parent_id: str, name: str) -> DriveEntry:
        """在父目录下新建文件夹。"""
        pid = str(parent_id or "0").strip() or "0"
        folder_name = name.strip()
        if not folder_name:
            raise P115TransportError("文件夹名称不能为空", retryable=False)
        payload = self._auth_post(
            access_token,
            _FOLDER_ADD_URL,
            body={"pid": pid, "file_name": folder_name},
            fallback="创建文件夹失败",
        )
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        if not isinstance(data, dict):
            raise P115TransportError("创建文件夹失败", retryable=False)
        # 同名已存在时 115 可能回 code 非 0，已在 _auth_post 抛出；这里取新目录 id
        new_id = str(data.get("file_id") or data.get("cid") or data.get("fid") or "").strip()
        if not new_id:
            raise P115TransportError("创建文件夹失败：未返回目录标识", retryable=False)
        return DriveEntry(
            id=new_id,
            parent_id=pid,
            name=str(data.get("file_name") or folder_name).strip() or folder_name,
            is_dir=True,
            size=0,
            modified_at=0,
        )

    def rename_entry(self, access_token: str, *, file_id: str, name: str) -> None:
        """重命名文件或文件夹。"""
        new_name = name.strip()
        if not file_id.strip() or not new_name:
            raise P115TransportError("重命名参数不完整", retryable=False)
        self._auth_post(
            access_token,
            _FILE_UPDATE_URL,
            body={"file_id": file_id.strip(), "file_name": new_name},
            fallback="重命名失败",
        )

    def delete_entries(self, access_token: str, *, file_ids: list[str]) -> None:
        """删除若干文件 / 文件夹（进回收站）。"""
        ids = [item.strip() for item in file_ids if item and item.strip()]
        if not ids:
            raise P115TransportError("未选择要删除的项目", retryable=False)
        self._auth_post(
            access_token,
            _FILE_DELETE_URL,
            body={"file_ids": ",".join(ids)},
            fallback="删除失败",
        )

    def download_url(self, access_token: str, *, pick_code: str) -> tuple[str, str]:
        """取直链。(url, file_name)"""
        code = pick_code.strip()
        if not code:
            raise P115TransportError("缺少文件标识", retryable=False)
        payload = self._auth_post(
            access_token,
            _FILE_DOWNURL,
            body={"pick_code": code},
            fallback="获取下载地址失败",
        )
        data = payload.get("data")
        if not isinstance(data, dict) or not data:
            raise P115TransportError("获取下载地址失败", retryable=False)
        # data 形如 { file_id: { file_name, url: { url } } }
        first = next(iter(data.values()), None)
        if not isinstance(first, dict):
            raise P115TransportError("获取下载地址失败", retryable=False)
        raw_url = first.get("url")
        url = ""
        if isinstance(raw_url, dict):
            url = str(raw_url.get("url") or "").strip()
        elif isinstance(raw_url, str):
            url = raw_url.strip()
        if not url:
            raise P115TransportError("获取下载地址失败：未返回链接", retryable=False)
        name = str(first.get("file_name") or "").strip()
        return url, name

    def video_play_url(self, access_token: str, *, pick_code: str) -> tuple[str, str]:
        """取视频可播地址（优先 m3u8 原画）。(url, file_name)"""
        code = pick_code.strip()
        if not code:
            raise P115TransportError("缺少文件标识", retryable=False)
        payload = self._auth_get(
            access_token,
            _VIDEO_PLAY_URL,
            params={"pick_code": code},
            fallback="获取播放地址失败",
        )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise P115TransportError("获取播放地址失败", retryable=False)
        name = str(data.get("file_name") or "").strip()
        urls = data.get("video_url")
        if isinstance(urls, list):
            for item in urls:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or "").strip()
                if url:
                    return url, name
        raise P115TransportError("该视频暂无可用播放地址", retryable=False)

    def open_entry(
        self,
        access_token: str,
        *,
        pick_code: str,
        extension: str = "",
        name: str = "",
    ) -> DriveOpenResult:
        """按扩展名打开：图片 / 视频走直链或播放地址。"""
        ext = extension.lower().lstrip(".")
        kind = _open_kind(ext)
        if kind == "video":
            # 浏览器 <video> 对直链 mp4 更友好；失败再回退转码流
            try:
                url, file_name = self.download_url(access_token, pick_code=pick_code)
                return DriveOpenResult(kind=kind, url=url, name=file_name or name, mime_hint="video/mp4")
            except P115TransportError:
                url, file_name = self.video_play_url(access_token, pick_code=pick_code)
                return DriveOpenResult(kind=kind, url=url, name=file_name or name, mime_hint="application/x-mpegURL")
        url, file_name = self.download_url(access_token, pick_code=pick_code)
        mime = "image/*" if kind == "image" else ""
        return DriveOpenResult(kind=kind, url=url, name=file_name or name, mime_hint=mime)

    def offline_quota(self, access_token: str) -> OfflineQuota:
        """云下载本月配额。"""
        payload = self._auth_get(
            access_token,
            _OFFLINE_QUOTA_URL,
            params={},
            fallback="获取云下载配额失败",
        )
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        if not isinstance(data, dict):
            data = {}
        return OfflineQuota(
            surplus=max(_optional_int(data.get("surplus")) or 0, 0),
            used=max(_optional_int(data.get("used")) or 0, 0),
            count=max(_optional_int(data.get("count")) or 0, 0),
        )

    def offline_task_page(self, access_token: str, *, page: int = 1) -> OfflineTaskPage:
        """云下载任务列表（115 原生分页，约每页 30 条）。"""
        page_no = max(1, int(page))
        payload = self._auth_get(
            access_token,
            _OFFLINE_TASK_LIST_URL,
            params={"page": str(page_no)},
            fallback="获取云下载任务失败",
        )
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        if not isinstance(data, dict):
            data = {}
        raw_tasks = data.get("tasks")
        tasks: list[OfflineTask] = []
        if isinstance(raw_tasks, list):
            for item in raw_tasks:
                if not isinstance(item, dict):
                    continue
                info_hash = str(item.get("info_hash") or "").strip()
                if not info_hash:
                    continue
                status = _optional_int(item.get("status"))
                if status is None:
                    status = -1
                percent = item.get("percentDone")
                try:
                    percent_done = float(percent) if percent is not None else 0.0
                except (TypeError, ValueError):
                    percent_done = 0.0
                tasks.append(
                    OfflineTask(
                        info_hash=info_hash,
                        name=str(item.get("name") or info_hash).strip() or info_hash,
                        size=max(_optional_int(item.get("size")) or 0, 0),
                        add_time=max(_optional_int(item.get("add_time")) or 0, 0),
                        status=int(status),
                        status_text=str(item.get("status_text") or "").strip(),
                        percent_done=percent_done,
                        url=str(item.get("url") or "").strip(),
                        file_id=str(item.get("file_id") or "").strip(),
                        pick_code=str(item.get("pick_code") or "").strip(),
                        wp_path_id=str(item.get("wp_path_id") or "").strip(),
                        file_category=max(_optional_int(item.get("file_category")) or 0, 0),
                        rate_download=max(_optional_int(item.get("rateDownload")) or 0, 0),
                        left_time=max(_optional_int(item.get("left_time")) or 0, 0),
                    )
                )
        return OfflineTaskPage(
            page=max(_optional_int(data.get("page")) or page_no, 1),
            page_count=max(_optional_int(data.get("page_count")) or 1, 1),
            count=max(_optional_int(data.get("count")) or len(tasks), 0),
            tasks=tuple(tasks),
        )

    def offline_add_urls(
        self,
        access_token: str,
        *,
        urls: list[str],
        wp_path_id: str = "0",
    ) -> tuple[OfflineAddResult, ...]:
        """添加 HTTP/HTTPS/FTP/磁力/电驴链接任务。多条用换行拼接。"""
        cleaned = [item.strip() for item in urls if item and item.strip()]
        if not cleaned:
            raise P115TransportError("请输入下载链接", retryable=False)
        payload = self._auth_post(
            access_token,
            _OFFLINE_ADD_URLS_URL,
            body={
                "urls": "\n".join(cleaned),
                "wp_path_id": str(wp_path_id or "0").strip() or "0",
            },
            fallback="添加云下载任务失败",
        )
        raw = payload.get("data")
        results: list[OfflineAddResult] = []
        items: list[Any]
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            nested = raw.get("list") or raw.get("tasks") or raw.get("result")
            items = nested if isinstance(nested, list) else [raw]
        else:
            items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or item.get("source_url") or "").strip()
            info_hash = str(item.get("info_hash") or item.get("hash") or "").strip()
            name = str(item.get("name") or item.get("file_name") or "").strip()
            err = str(item.get("message") or item.get("error") or item.get("msg") or "").strip()
            state = item.get("state")
            ok = True
            if state is not None:
                ok = bool(state) if not isinstance(state, str) else state.lower() not in {"0", "false", "fail"}
            if err and not info_hash:
                ok = False
            code = _optional_int(item.get("code") or item.get("errno"))
            if code is not None and code != 0:
                ok = False
            results.append(
                OfflineAddResult(
                    url=url,
                    info_hash=info_hash,
                    name=name,
                    ok=ok,
                    message=err,
                )
            )
        if not results:
            # 115 有时只回 code=0 不带明细，视为整批成功
            return tuple(OfflineAddResult(url=u, ok=True) for u in cleaned)
        return tuple(results)

    def offline_del_task(
        self,
        access_token: str,
        *,
        info_hash: str,
        del_source_file: bool = False,
    ) -> None:
        """删除云下载任务；可选同时删除已落盘文件。"""
        digest = info_hash.strip()
        if not digest:
            raise P115TransportError("缺少任务标识", retryable=False)
        self._auth_post(
            access_token,
            _OFFLINE_DEL_TASK_URL,
            body={
                "info_hash": digest,
                "del_source_file": "1" if del_source_file else "0",
            },
            fallback="删除云下载任务失败",
        )

    def _auth_get(
        self,
        access_token: str,
        url: str,
        *,
        params: dict[str, str],
        fallback: str,
    ) -> dict[str, Any]:
        with self._client() as client:
            try:
                response = client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            except httpx.HTTPError as exc:
                raise P115TransportError("无法连接 115，请稍后重试。") from exc
        return self._auth_payload(response, fallback)

    def _auth_post(
        self,
        access_token: str,
        url: str,
        *,
        body: dict[str, Any],
        fallback: str,
    ) -> dict[str, Any]:
        with self._client() as client:
            try:
                response = client.post(
                    url,
                    data=body,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
            except httpx.HTTPError as exc:
                raise P115TransportError("无法连接 115，请稍后重试。") from exc
        return self._auth_payload(response, fallback)

    def _auth_payload(self, response: httpx.Response, fallback: str) -> dict[str, Any]:
        if response.status_code == 401:
            raise P115TransportError("115 授权已失效", retryable=False, unauthorized=True)
        if response.status_code >= 400:
            raise P115TransportError(fallback)
        payload = self._json(response)
        code = _optional_int(payload.get("code"))
        if code in _CODES_UNAUTHORIZED:
            raise P115TransportError("115 授权已失效", retryable=False, unauthorized=True)
        if code != _CODE_OK:
            message = str(payload.get("message") or payload.get("error") or "").strip()
            raise P115TransportError(message or fallback, retryable=False, code=code)
        return payload

    def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        with self._client() as client:
            try:
                response = client.post(
                    url,
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            except httpx.HTTPError as exc:
                raise P115TransportError("无法连接 115，请稍后重试。") from exc
        if response.status_code >= 400:
            raise P115TransportError("115 拒绝了本次请求")
        return self._json(response)

    @staticmethod
    def _data(payload: dict[str, Any], fallback: str) -> dict[str, Any]:
        """取业务数据段。115 用 code == 0 表示成功，其余都是业务错误。"""
        code = _optional_int(payload.get("code"))
        if code != _CODE_OK:
            message = str(payload.get("message") or "").strip()
            raise P115TransportError(message or fallback, retryable=False, code=code)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise P115TransportError(fallback, retryable=False)
        return data

    @staticmethod
    def _tokens(data: dict[str, Any], fallback: str) -> TokenPair:
        access = str(data.get("access_token") or "").strip()
        if not access:
            raise P115TransportError(fallback, retryable=False)
        refresh = str(data.get("refresh_token") or "").strip() or None
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=_optional_int(data.get("expires_in")),
        )

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise P115TransportError("115 返回了无效响应") from exc
        if not isinstance(payload, dict):
            raise P115TransportError("115 返回了无效响应")
        return payload


async def list_dir(path: str) -> list[str]:
    raise NotReady("115 列目录未接入")


async def transfer(source_ref: str, target_dir: str) -> str:
    raise NotReady("115 转存未接入")


async def resolve_direct_url(path: str) -> tuple[str, dict[str, str], int]:
    """返回 (直链, 必需请求头, 有效秒数)。"""
    raise NotReady("115 直链解析未接入")
