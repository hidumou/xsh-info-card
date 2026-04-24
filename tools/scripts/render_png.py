#!/usr/bin/env python3
"""
render_png.py — HTML 卡片截图导出为 PNG

依赖：  pip install playwright --break-system-packages && playwright install chromium

用法：
  python3 render_png.py cover.html
      截图单个 HTML → 同目录 cover.png

  python3 render_png.py 信息内容/懦夫博弈/
      批量截图目录下所有 .html

  python3 render_png.py cover.html --scale 3
      导出高清版本（device scale 3x）

  python3 render_png.py cover.html --out /tmp/a.png
      指定输出路径

默认输出 720×960 的卡片区域（.card 元素），@ 2x 物理像素。
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path


CARD_W, CARD_H = 720, 960


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print(
            "[err] playwright not installed.\n"
            "     pip install playwright --break-system-packages\n"
            "     playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(2)


def render_one(html_path: Path, out_path: Path, scale: int = 2) -> None:
    from playwright.sync_api import sync_playwright

    url = html_path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": CARD_W, "height": CARD_H + 120},
            device_scale_factor=scale,
        )
        page = ctx.new_page()
        # 1) DOM 加载完
        page.goto(url, wait_until="domcontentloaded")
        # 2) 等所有网络请求静默（含图片）
        page.wait_for_load_state("networkidle")
        # 3) 等 Web 字体完全加载并应用 —— 关键：避免 FOUT 截图
        #    document.fonts.ready 是浏览器原生 API，确保 @import url() 加载的字体就绪
        page.evaluate("document.fonts.ready")
        # 4) 强制等待字体集合状态为 loaded（兜底）
        page.wait_for_function("document.fonts && document.fonts.status === 'loaded'", timeout=10000)
        # 5) 再给 200ms 让浏览器完成最终的 layout/paint
        page.wait_for_timeout(200)
        card = page.locator(".card").first
        card.screenshot(path=str(out_path), omit_background=False)
        browser.close()
    print(f"  ✓ {out_path}")


def resolve_outputs(inputs: list[Path], out_arg: str | None) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for inp in inputs:
        if inp.is_dir():
            for html in sorted(inp.glob("*.html")):
                pairs.append((html, html.with_suffix(".png")))
        elif inp.suffix.lower() == ".html":
            out = Path(out_arg) if out_arg else inp.with_suffix(".png")
            pairs.append((inp, out))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="HTML 文件或目录")
    ap.add_argument("--out", help="输出路径（仅当输入为单个 HTML 时生效）")
    ap.add_argument("--scale", type=int, default=2, help="device scale factor（默认 2x）")
    args = ap.parse_args()

    ensure_playwright()

    pairs = resolve_outputs([Path(p) for p in args.inputs], args.out)
    if not pairs:
        print("[err] no HTML files found", file=sys.stderr)
        return 2

    for html, png in pairs:
        render_one(html, png, scale=args.scale)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
