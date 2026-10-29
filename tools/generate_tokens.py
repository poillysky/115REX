"""从 packages/design-tokens/tokens.json 生成两端常量。

用法（仓库根目录）：
    python tools/generate_tokens.py

生成物：
    apps/web/src/core/theme/tokens.generated.ts
    apps/web/src/core/theme/tokens.generated.css
    apps/app/lib/core/theme/design_tokens.dart

规则：色值与尺寸只在 tokens.json 里定义。生成物不要手改，改了会被下一次生成覆盖。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "packages" / "design-tokens" / "tokens.json"
WEB_THEME_DIR = ROOT / "apps" / "web" / "src" / "core" / "theme"
APP_THEME_DIR = ROOT / "apps" / "app" / "lib" / "core" / "theme"

HEADER = "由 tools/generate_tokens.py 从 packages/design-tokens/tokens.json 生成，不要手改。"


def camel(name: str) -> str:
    return name


def kebab(name: str) -> str:
    out = []
    for ch in name:
        if ch.isupper():
            out.append("-")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out)


def load() -> dict:
    with SOURCE.open(encoding="utf-8") as fp:
        return json.load(fp)


def gen_ts(tokens: dict) -> str:
    lines = [f"// {HEADER}", ""]

    light, dark = tokens["color"]["light"], tokens["color"]["dark"]
    lines.append("export const colorLight = {")
    lines += [f"  {k}: '{v}'," for k, v in light.items()]
    lines.append("} as const;")
    lines.append("")
    lines.append("export const colorDark: Record<keyof typeof colorLight, string> = {")
    lines += [f"  {k}: '{v}'," for k, v in dark.items()]
    lines.append("};")
    lines.append("")
    lines.append("export type ColorRole = keyof typeof colorLight;")
    lines.append("")

    themed = tokens["theme"]
    lines.append("/** 主题变体：只覆盖品牌三色，其余角色沿用深浅基准。 */")
    lines.append("export const themeAccents = {")
    for key, item in themed.items():
        lines.append(f"  {key}: {{")
        lines.append(f"    label: '{item['label']}',")
        lines.append(f"    light: {json.dumps(item['light'], ensure_ascii=False)},")
        lines.append(f"    dark: {json.dumps(item['dark'], ensure_ascii=False)},")
        lines.append("  },")
    lines.append("} as const;")
    lines.append("")
    lines.append("export type ThemeAccent = keyof typeof themeAccents;")
    lines.append("")
    lines.append("export type ThemeMode = 'light' | 'dark';")
    lines.append("")

    for group, tname in (("space", "space"), ("radius", "radius"), ("duration", "duration"), ("fontSize", "fontSize"), ("fontWeight", "fontWeight"), ("letterSpacing", "letterSpacing")):
        lines.append(f"export const {tname} = {{")
        lines += [f"  {k}: {v}," for k, v in tokens[group].items()]
        lines.append("} as const;")
        lines.append("")

    lines.append("export const tokens = { colorLight, colorDark, themeAccents, space, radius, duration, fontSize, fontWeight, letterSpacing } as const;")
    lines.append("")
    return "\n".join(lines)


def _gradient_soft(tokens: dict, mode: str) -> str:
    colors = tokens["color"][mode]
    return f"linear-gradient(180deg, {colors['primarySubtle']}, {colors['surface']})"


# 海报品牌渐变停靠点（docs/02 §3.1.1）；深色降低亮度并提高紫端占比。
BRAND_GRADIENT_LIGHT = ("#25C4FF", "#168BFF", "#315BFF", "#8B35F6")
BRAND_GRADIENT_DARK = ("#1AA8E0", "#2A78E8", "#4A5AE8", "#9A55F0")


def _brand_gradient(mode: str) -> tuple[str, tuple[str, str, str, str]]:
    stops = BRAND_GRADIENT_LIGHT if mode == "light" else BRAND_GRADIENT_DARK
    g1, g2, g3, g4 = stops
    css = (
        f"linear-gradient(135deg, {g1} 0%, {g2} 36%, {g3} 67%, {g4} 100%)"
    )
    return css, stops


def gen_css(tokens: dict) -> str:
    """主题靠 <html> 上的 data-theme / data-accent 切换，系统偏好只在首屏首次访问时由 JS 采纳。

    输出顺序：先基准色板（data-theme），再各强调色变体（data-accent），最后尺寸与字阶。
    变体只写品牌三色，其余角色沿用基准，避免每个组合重复几十行。
    """
    lines = [f"/* {HEADER} */", ""]
    lines.append("/* 主题切换的唯一入口（docs/02 §3.4）：data-theme=light|dark，data-accent=<主题 key> */")
    lines.append(":root {" + " color-scheme: light; }")
    lines.append(":root[data-theme='dark'] {" + " color-scheme: dark; }")
    lines.append("")

    def block(selector: str, colors: dict, only: tuple[str, ...] | None = None) -> None:
        lines.append(f"{selector} {{")
        for k, v in colors.items():
            if only is not None and k not in only:
                continue
            lines.append(f"  --color-{kebab(k)}: {v};")
        lines.append("}")

    block(":root,\n:root[data-theme='light']", tokens["color"]["light"])
    block(":root[data-theme='dark']", tokens["color"]["dark"])
    lines.append("")

    accent_roles = ("primary", "primarySubtle", "onPrimary")
    for key, item in tokens["theme"].items():
        # default 就是上面的浅色 / 深色基准，不再重复输出一份
        if key == "default":
            continue
        for mode in ("light", "dark"):
            block(f":root[data-theme='{mode}'][data-accent='{key}']", item[mode], accent_roles)
            lines.append("")
    lines.append("")

    brand_css, brand_stops = _brand_gradient("light")
    lines.append(":root {")
    lines.append(f"  --gradient-brand-soft: {_gradient_soft(tokens, 'light')}; /* taste-skill-ignore：仅供登录整屏，docs/02 §3.1.1 */")
    lines.append(f"  --gradient-brand: {brand_css}; /* taste-skill-ignore：品牌位唯一渐变，docs/02 §3.1.1 */")
    for i, stop in enumerate(brand_stops, start=1):
        lines.append(f"  --brand-g{i}: {stop};")
    for k, v in tokens["space"].items():
        lines.append(f"  --{kebab(k)}: {v}px;")
    for k, v in tokens["radius"].items():
        lines.append(f"  --{kebab(k)}: {v}px;")
    for k, v in tokens["duration"].items():
        lines.append(f"  --duration-{k}: {v}ms;")
    for k, v in tokens["fontSize"].items():
        lines.append(f"  --font-{k}-size: {v}px;")
    for k, v in tokens["fontWeight"].items():
        lines.append(f"  --font-{k}-weight: {v};")
    for k, v in tokens["letterSpacing"].items():
        lines.append(f"  --font-{k}-tracking: {v / 16}em;")
    lines.append("}")
    lines.append("")

    dark_brand_css, dark_brand_stops = _brand_gradient("dark")
    lines.append(":root[data-theme='dark'] {")
    lines.append(f"  --gradient-brand-soft: {_gradient_soft(tokens, 'dark')}; /* taste-skill-ignore：仅供登录整屏，docs/02 §3.1.1 */")
    lines.append(f"  --gradient-brand: {dark_brand_css}; /* taste-skill-ignore：品牌位唯一渐变，docs/02 §3.1.1 */")
    for i, stop in enumerate(dark_brand_stops, start=1):
        lines.append(f"  --brand-g{i}: {stop};")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def gen_dart(tokens: dict) -> str:
    lines = [f"// {HEADER}", "", "import 'dart:ui';", ""]

    for suffix, key in (("Light", "light"), ("Dark", "dark")):
        lines.append(f"abstract final class AppColors{suffix} {{")
        for k, v in tokens["color"][key].items():
            lines.append(f"  static const Color {k} = Color(0xFF{v[1:].upper()});")
        lines.append("}")
        lines.append("")

    for group, cls, kind in (
        ("space", "AppSpace", "double"),
        ("radius", "AppRadius", "double"),
        ("duration", "AppDuration", "int"),
        ("letterSpacing", "AppTracking", "double"),
    ):
        lines.append(f"abstract final class {cls} {{")
        for k, v in tokens[group].items():
            if kind == "double":
                lines.append(f"  static const double {k} = {float(v)};")
            else:
                lines.append(f"  static const int {k} = {v};")
        lines.append("}")
        lines.append("")

    lines.append("abstract final class AppFontSize {")
    for k, v in tokens["fontSize"].items():
        lines.append(f"  static const double {k} = {float(v)};")
    lines.append("}")
    lines.append("")

    lines.append("abstract final class AppFontWeight {")
    for k, v in tokens["fontWeight"].items():
        lines.append(f"  static const FontWeight {k} = FontWeight.w{v};")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    tokens = load()
    WEB_THEME_DIR.mkdir(parents=True, exist_ok=True)
    APP_THEME_DIR.mkdir(parents=True, exist_ok=True)

    targets = [
        (WEB_THEME_DIR / "tokens.generated.ts", gen_ts(tokens)),
        (WEB_THEME_DIR / "tokens.generated.css", gen_css(tokens)),
        (APP_THEME_DIR / "design_tokens.dart", gen_dart(tokens)),
    ]
    for path, content in targets:
        path.write_text(content, encoding="utf-8")
        print(f"generated {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
