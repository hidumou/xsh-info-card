#!/usr/bin/env python3
"""
remove_watermark.py — 去除 AI 生成图像角落的水印（保留 Alpha 通道）

三种模式：
  1) --box L,T,R,B   指定矩形：设为完全透明（保留透明底）；若原图是不透明纯色底，
                     则用采样到的背景色填充
  2) --auto          扫描角落，替换与背景差异大的像素
  3) --mask-grey     识别灰白水印文字（低饱和 + 适中亮度）

用法：
  python3 remove_watermark.py logo.png
      默认：右下角 box 透明填充

  python3 remove_watermark.py logo.png out.png --box 815,920,1024,1024
      指定水印矩形，透明底会保持透明

  python3 remove_watermark.py logo.png out.png --mask-grey --corner br --pct 0.18
      仅抹去右下 18% 区域的灰白水印文字

依赖：pip install Pillow
"""
from __future__ import annotations
import argparse
import sys
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw


def has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)


def sample_bg_color(img: Image.Image, sample_boxes: list[tuple[int, int, int, int]]) -> tuple:
    """从多个采样矩形里取众数像素作为背景色（保留通道数）。"""
    pixels = []
    for box in sample_boxes:
        pixels.extend(list(img.crop(box).getdata()))
    return Counter(pixels).most_common(1)[0][0]


def corner_box(w: int, h: int, corner: str, pct: float) -> tuple[int, int, int, int]:
    bw = int(w * pct)
    bh = int(h * pct)
    if corner == "br":
        return (w - bw, h - bh, w, h)
    if corner == "bl":
        return (0, h - bh, bw, h)
    if corner == "tr":
        return (w - bw, 0, w, bh)
    return (0, 0, bw, bh)


def other_corner_samples(w: int, h: int, corner: str, pct: float) -> list[tuple[int, int, int, int]]:
    """返回除水印角之外的其余 3 个角落采样区。"""
    bw, bh = int(w * pct * 0.3), int(h * pct * 0.3)
    corners = {
        "tl": (0, 0, bw, bh),
        "tr": (w - bw, 0, w, bh),
        "bl": (0, h - bh, bw, h),
        "br": (w - bw, h - bh, w, h),
    }
    return [v for k, v in corners.items() if k != corner]


def _ensure_rgba(img: Image.Image) -> Image.Image:
    """统一到 RGBA 以便统一处理，保留原有 alpha。"""
    if img.mode == "RGBA":
        return img.copy()
    if img.mode == "LA":
        return img.convert("RGBA")
    if img.mode == "P" and "transparency" in img.info:
        return img.convert("RGBA")
    # no alpha — convert to RGBA with full opaque
    return img.convert("RGBA")


def remove_by_box(img: Image.Image, box: tuple[int, int, int, int], corner: str = "br") -> Image.Image:
    """
    在指定矩形填充：
      - 原图有透明像素（alpha=0）在采样区内占多数 → 透明填充
      - 否则 → 用采样背景色填充
    """
    out = _ensure_rgba(img)
    w, h = out.size
    sample = other_corner_samples(w, h, corner, 0.2)
    bg = sample_bg_color(out, sample)
    fill = (0, 0, 0, 0) if bg[3] == 0 else bg
    ImageDraw.Draw(out).rectangle(box, fill=fill)
    return out


def remove_by_auto(img: Image.Image, corner: str = "br", pct: float = 0.2,
                   threshold: int = 30,
                   protect_colors: list[tuple[int, int, int]] | None = None,
                   protect_threshold: int = 80) -> Image.Image:
    """像素级扫描：与背景色差异大 → 替换为背景（可透明）。主色保护避免误伤 logo。"""
    out = _ensure_rgba(img)
    w, h = out.size
    sample = other_corner_samples(w, h, corner, pct)
    bg = sample_bg_color(out, sample)
    transparent_bg = bg[3] == 0
    fill = (0, 0, 0, 0) if transparent_bg else bg
    x0, y0, x1, y1 = corner_box(w, h, corner, pct)
    px = out.load()
    pc = protect_colors or []
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b, a = px[x, y]
            # 已经是背景（颜色相近且透明度相近）→ 跳过
            if transparent_bg and a < 5:
                continue
            if not transparent_bg and (
                abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) <= threshold and abs(a - bg[3]) < 10
            ):
                continue
            if any(abs(r - c[0]) + abs(g - c[1]) + abs(b - c[2]) < protect_threshold for c in pc):
                continue
            px[x, y] = fill
    return out


def remove_grey_text(img: Image.Image, corner: str = "br", pct: float = 0.2,
                     min_brightness: int = 30,
                     max_saturation: int = 40) -> Image.Image:
    """识别灰白水印文字（低饱和 + 适中亮度）。适合透明底上的灰色水印。"""
    out = _ensure_rgba(img)
    w, h = out.size
    sample = other_corner_samples(w, h, corner, pct)
    bg = sample_bg_color(out, sample)
    fill = (0, 0, 0, 0) if bg[3] == 0 else bg
    x0, y0, x1, y1 = corner_box(w, h, corner, pct)
    px = out.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b, a = px[x, y]
            # 全透明 → 跳过
            if a == 0:
                continue
            brightness = (r + g + b) / 3
            saturation = max(r, g, b) - min(r, g, b)
            if brightness > min_brightness and saturation < max_saturation:
                px[x, y] = fill
    return out


def cli(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="输入图像路径")
    ap.add_argument("output", nargs="?", default=None, help="输出路径（默认 *_clean.png）")
    ap.add_argument("--box", help="手动矩形: left,top,right,bottom（推荐，最稳）")
    ap.add_argument("--auto", action="store_true", help="按像素差异扫描替换")
    ap.add_argument("--mask-grey", action="store_true", help="按灰白色特征识别水印文字")
    ap.add_argument("--corner", default="br", choices=["br", "bl", "tr", "tl"], help="水印角落（默认右下 br）")
    ap.add_argument("--pct", type=float, default=0.2, help="扫描角落占比（默认 0.2）")
    ap.add_argument("--threshold", type=int, default=30, help="auto 模式颜色差阈值")
    ap.add_argument("--min-bright", type=int, default=30, help="mask-grey：最小亮度")
    ap.add_argument("--max-sat", type=int, default=40, help="mask-grey：最大饱和度")
    ap.add_argument("--protect", default="", help='auto 保护色："r,g,b;r,g,b"')
    args = ap.parse_args(argv)

    src = Path(args.input)
    if not src.exists():
        print(f"[err] input not found: {src}", file=sys.stderr)
        return 2
    img = Image.open(src)

    if args.box:
        box = tuple(int(v) for v in args.box.split(","))
        if len(box) != 4:
            print("[err] --box expects 4 ints: left,top,right,bottom", file=sys.stderr)
            return 2
        out = remove_by_box(img, box, corner=args.corner)  # type: ignore[arg-type]
    elif args.mask_grey:
        out = remove_grey_text(img, corner=args.corner, pct=args.pct,
                               min_brightness=args.min_bright, max_saturation=args.max_sat)
    else:
        protect_colors: list[tuple[int, int, int]] = []
        if args.protect:
            for chunk in args.protect.split(";"):
                rgb = tuple(int(v) for v in chunk.split(","))
                if len(rgb) == 3:
                    protect_colors.append(rgb)  # type: ignore[arg-type]
        out = remove_by_auto(img, corner=args.corner, pct=args.pct,
                             threshold=args.threshold, protect_colors=protect_colors)

    dest = Path(args.output) if args.output else src.with_name(src.stem + "_clean.png")
    out.save(dest)
    print(f"saved: {dest}  (mode={out.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
