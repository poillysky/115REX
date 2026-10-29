"""Prepare Bangumi / Fanart plugin card icons from official sources."""
from __future__ import annotations

import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "src" / "assets" / "plugin-icons"
ROOT.mkdir(parents=True, exist_ok=True)

FANART_URL = (
    "https://raw.githubusercontent.com/jellyfin/jellyfin-ux/master/"
    "plugins/repository/jellyfin-plugin-fanart.png"
)
BANGUMI_URL = "https://avatars.githubusercontent.com/bangumi?s=256"


def punch_near_color(im: Image.Image, sample: tuple[int, int, int], tol: int = 18) -> int:
    px = im.load()
    cr, cg, cb = sample
    changed = 0
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            r, g, b, a = px[x, y]
            if abs(r - cr) < tol and abs(g - cg) < tol and abs(b - cb) < tol:
                px[x, y] = (0, 0, 0, 0)
                changed += 1
    return changed


def prep_fanart() -> None:
    tmp = ROOT / "_jf.png"
    urllib.request.urlretrieve(FANART_URL, tmp)
    src = Image.open(tmp).convert("RGBA")
    # Jellyfin SVG canvas 508x285.75 → raster 1920x1080; circle ~ (128, 143)
    sx = 1920 / 508
    cx = int(128 * sx)
    cy = int(143 * (1080 / 285.75))
    r = int(140 * 0.26458 * 0.87865 * sx)
    pad = int(r * 0.18)
    side = 2 * (r + pad)
    left = max(0, cx - side // 2)
    top = max(0, cy - side // 2)
    crop = src.crop((left, top, left + side, top + side)).resize(
        (256, 256), Image.Resampling.LANCZOS
    )
    # Keep only the white circle mark; clear dark banner background.
    xs: list[int] = []
    ys: list[int] = []
    cp = crop.load()
    for y in range(256):
        for x in range(256):
            rr, g, b, a = cp[x, y]
            if a > 200 and rr > 200 and g > 200 and b > 200:
                xs.append(x)
                ys.append(y)
    circle_x = (min(xs) + max(xs)) / 2
    circle_y = (min(ys) + max(ys)) / 2
    circle_r = ((max(xs) - min(xs)) / 2 + (max(ys) - min(ys)) / 2) / 2 + 2
    out = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    op = out.load()
    for y in range(256):
        for x in range(256):
            if (x - circle_x) ** 2 + (y - circle_y) ** 2 <= circle_r * circle_r:
                op[x, y] = cp[x, y]
    dest = ROOT / "fanart.png"
    out.save(dest)
    tmp.unlink(missing_ok=True)
    print(f"fanart -> {dest} ({dest.stat().st_size} bytes) crop=({cx},{cy},{r})")


def prep_bangumi() -> None:
    dest = ROOT / "bangumi.png"
    urllib.request.urlretrieve(BANGUMI_URL, dest)
    im = Image.open(dest).convert("RGBA")
    corner = im.getpixel((2, 2))
    if corner[0] > 180 and corner[1] > 180 and corner[2] > 180:
        n = punch_near_color(im, corner[:3])
        im.save(dest)
        print(f"bangumi -> {dest} punched {n} gray px")
    else:
        print(f"bangumi -> {dest} kept as-is corner={corner}")


if __name__ == "__main__":
    prep_bangumi()
    prep_fanart()
