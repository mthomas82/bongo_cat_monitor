#!/usr/bin/env python3
"""PNG <-> LVGL RGB565A8 C array for Bongo Cat 64x64 sprites."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

SPRITE_W = 64
SPRITE_H = 64
DATA_SIZE = SPRITE_W * SPRITE_H * 3  # RGB565 + A8 planes

# Hardware palette (plus transparent). Originals are indexed to these.
PALETTE = [
    (0, 0, 0, 0),           # transparent
    (0, 0, 0, 255),         # ink / outline / eyes
    (255, 255, 255, 255),   # fur
    (158, 158, 158, 255),   # keys
    (255, 128, 171, 255),   # pads / click sparks
    (255, 183, 77, 255),    # sleepy Z
]

LAYERS = ("body", "face", "table", "paws", "effects")

SPRITE_CATALOG = [
    ("body", "standardbody1"),
    ("body", "bodyeartwitch"),
    ("face", "stock_face"),
    ("face", "happy_face"),
    ("face", "blink_face"),
    ("face", "sleepy_face"),
    ("face", "excited_face"),
    ("paws", "leftpawdown"),
    ("paws", "rightpawdown"),
    ("paws", "twopawsup"),
    ("table", "table1"),
    ("effects", "left_click_effect"),
    ("effects", "right_click_effect"),
    ("effects", "sleepy1"),
    ("effects", "sleepy2"),
    ("effects", "sleepy3"),
    ("effects", "excited1"),
    ("effects", "excited2"),
]


def repo_root() -> Path:
    here = Path(__file__).resolve().parent
    if here.name == "tools":
        return here.parent
    return here


def png_path(root: Path, layer: str, name: str) -> Path:
    folder = "face" if layer == "face" else layer
    return root / "Sprites" / folder / f"{name}.png"


def c_path(root: Path, layer: str, name: str) -> Path:
    folder = "faces" if layer == "face" else layer
    return root / "animations" / folder / f"{name}.c"


def rgb_to_565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def rgb565_to_rgb(c: int) -> tuple[int, int, int]:
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return (r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)


def nearest_palette(r: int, g: int, b: int, a: int) -> tuple[int, int, int, int]:
    if a < 128:
        return PALETTE[0]
    best = PALETTE[1]
    best_d = 1e18
    for pr, pg, pb, pa in PALETTE[1:]:
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_d:
            best_d = d
            best = (pr, pg, pb, pa)
    return best


def load_rgba(path: Path, quantize: bool = True) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    if im.size != (SPRITE_W, SPRITE_H):
        im = im.resize((SPRITE_W, SPRITE_H), Image.NEAREST)
    if not quantize:
        return im
    px = list(im.getdata())
    out = [
        nearest_palette(r, g, b, a) for (r, g, b, a) in px
    ]
    im.putdata(out)
    return im


def save_indexed_png(im: Image.Image, path: Path) -> None:
    """Write a tiny indexed PNG matching the original sprite style."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba = im.convert("RGBA")
    if rgba.size != (SPRITE_W, SPRITE_H):
        rgba = rgba.resize((SPRITE_W, SPRITE_H), Image.NEAREST)
    pal_rgb = []
    for r, g, b, _a in PALETTE:
        pal_rgb.extend([r, g, b])
    pal_rgb.extend([0, 0, 0] * (256 - len(PALETTE)))
    palette_img = Image.new("P", (1, 1))
    palette_img.putpalette(pal_rgb)
    indexes = []
    for r, g, b, a in rgba.getdata():
        if a < 128:
            indexes.append(0)
            continue
        best_i, best_d = 1, 1e18
        for i, (pr, pg, pb, pa) in enumerate(PALETTE):
            if pa == 0:
                continue
            d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if d < best_d:
                best_d = d
                best_i = i
        indexes.append(best_i)
    out = Image.new("P", (SPRITE_W, SPRITE_H))
    out.putpalette(pal_rgb)
    out.putdata(indexes)
    out.info["transparency"] = 0
    out.save(path, format="PNG", optimize=True, transparency=0)


def png_to_rgb565a8(im: Image.Image) -> bytes:
    rgba = im.convert("RGBA")
    if rgba.size != (SPRITE_W, SPRITE_H):
        rgba = rgba.resize((SPRITE_W, SPRITE_H), Image.NEAREST)
    color = bytearray()
    alpha = bytearray()
    for r, g, b, a in rgba.getdata():
        if a < 128:
            color.extend((0, 0))
            alpha.append(0)
            continue
        c = rgb_to_565(r, g, b)
        color.append(c & 0xFF)
        color.append((c >> 8) & 0xFF)
        alpha.append(255 if a >= 128 else a)
    return bytes(color) + bytes(alpha)


def rgb565a8_to_image(data: bytes, w: int = SPRITE_W, h: int = SPRITE_H) -> Image.Image:
    need = w * h * 3
    if len(data) < need:
        raise ValueError(f"sprite data too short: {len(data)} < {need}")
    color = data[: w * h * 2]
    alpha = data[w * h * 2 : w * h * 3]
    pixels = []
    for i in range(w * h):
        lo = color[i * 2]
        hi = color[i * 2 + 1]
        r, g, b = rgb565_to_rgb(lo | (hi << 8))
        a = alpha[i]
        pixels.append((r, g, b, a))
    im = Image.new("RGBA", (w, h))
    im.putdata(pixels)
    return im


def parse_c_map(text: str) -> bytes:
    m = re.search(r"uint8_t\s+\w+_map\[\]\s*=\s*\{(.*?)\};", text, re.S)
    if not m:
        raise ValueError("no uint8_t map[] in C sprite")
    nums = [int(x, 16) if x.lower().startswith("0x") else int(x) for x in re.findall(r"0x[0-9a-fA-F]+|\d+", m.group(1))]
    return bytes(nums)


def emit_c(name: str, data: bytes) -> str:
    if len(data) != DATA_SIZE:
        raise ValueError(f"{name}: expected {DATA_SIZE} bytes, got {len(data)}")
    ident = re.sub(r"[^A-Za-z0-9_]", "_", name)
    attr = ident.upper()
    rgb = data[: SPRITE_W * SPRITE_H * 2]
    a8 = data[SPRITE_W * SPRITE_H * 2 :]
    lines = [
        "#ifdef __has_include",
        "    #if __has_include(\"lvgl.h\")",
        "        #ifndef LV_LVGL_H_INCLUDE_SIMPLE",
        "            #define LV_LVGL_H_INCLUDE_SIMPLE",
        "        #endif",
        "    #endif",
        "#endif",
        "",
        "#if defined(LV_LVGL_H_INCLUDE_SIMPLE)",
        "    #include \"lvgl.h\"",
        "#else",
        "    #include \"lvgl/lvgl.h\"",
        "#endif",
        "",
        "",
        "#ifndef LV_ATTRIBUTE_MEM_ALIGN",
        "#define LV_ATTRIBUTE_MEM_ALIGN",
        "#endif",
        "",
        f"#ifndef LV_ATTRIBUTE_IMG_{attr}",
        f"#define LV_ATTRIBUTE_IMG_{attr}",
        "#endif",
        "",
        f"const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_{attr} uint8_t {ident}_map[] = {{",
    ]

    def dump_plane(blob: bytes, row_width: int) -> None:
        for y in range(SPRITE_H):
            row = blob[y * row_width : (y + 1) * row_width]
            hexes = ", ".join(f"0x{b:02x}" for b in row)
            lines.append(f"  {hexes}, ")

    dump_plane(rgb, SPRITE_W * 2)
    dump_plane(a8, SPRITE_W)
    lines.append("")
    lines.append("};")
    lines.append("")
    lines.append(f"const lv_img_dsc_t {ident} = {{")
    lines.append("  {LV_IMG_CF_RGB565A8, 0, 0, 64, 64},  // header: {cf, always_zero, reserved, w, h}")
    lines.append("  12288,                                // data_size")
    pad = " " * max(1, 33 - len(f"  {ident}_map,"))
    lines.append(f"  {ident}_map,{pad}// data")
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def convert_png_file(png: Path, dest_c: Path | None = None, name: str | None = None) -> Path:
    name = name or png.stem
    im = load_rgba(png, quantize=True)
    data = png_to_rgb565a8(im)
    dest = dest_c or png.with_suffix(".c")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(emit_c(name, data))
    return dest


def convert_all(root: Path | None = None) -> list[Path]:
    root = root or repo_root()
    written = []
    for layer, name in SPRITE_CATALOG:
        src = png_path(root, layer, name)
        if not src.exists():
            continue
        written.append(convert_png_file(src, c_path(root, layer, name), name))
    return written
