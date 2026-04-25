#!/usr/bin/env python3
"""
build_cards.py — 根据 topic.json 生成 5 张卡片 PNG

用法：
  python3 tools/scripts/build_cards.py topics/topic_xxx.json
      自动按当周 ISO 周数轮换风格，输出 PNG 到 output/YYYY-MM-DD/<slug>/

  python3 tools/scripts/build_cards.py topic.json --style research
      指定风格

  python3 tools/scripts/build_cards.py topic.json --style research --output /tmp/demo/
      指定输出目录

  python3 tools/scripts/build_cards.py topic.json --keep-html
      调试用：同时保留中间产物 HTML

依赖：Jinja2 + playwright
  pip install Jinja2 playwright --break-system-packages
  playwright install chromium

issue_no 机制：
  - 每个风格在 info.json 里各自维护一个计数器（不按日期计数）
  - 每次生成前先递增计数器并写回，生成失败则回滚
  - 注入到模板的 meta.issue_no 会被覆盖为三位零填充（如 "001"）

风格清单（按周轮换）：
  research  机构研报风（深蓝 + 金色，衬线）
  wsj       华尔街日报风（衬线 + 米色纸，深红点缀）
  bloomberg 彭博终端风（黑底橙字，等宽字）
  minimal   财报极简（黑白灰，大量留白）
"""
from __future__ import annotations
import argparse
import base64
import json
import random as _random
import re
import sys
import subprocess
import tempfile
import zipfile
from datetime import date as dt_date
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("[err] Jinja2 not installed. Run: pip install Jinja2 --break-system-packages", file=sys.stderr)
    sys.exit(2)

# tools/scripts/build_cards.py 的位置关系：
#   SCRIPT_DIR   = tools/scripts
#   TOOLS_ROOT   = tools
#   PROJECT_ROOT = 项目根
SCRIPT_DIR = Path(__file__).parent
TOOLS_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = TOOLS_ROOT.parent

TEMPLATES_DIR = TOOLS_ROOT / "templates"
LOGO_PATH = TOOLS_ROOT / "assets" / "logo.png"
DEFAULT_OUTPUT_PARENT = PROJECT_ROOT / "output"
INFO_JSON = PROJECT_ROOT / "info.json"


def _logo_data_uri() -> str:
    """把 logo 读成 base64 data URI,避免模板依赖相对路径。"""
    if not LOGO_PATH.exists():
        return ""
    b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"

# 5 张卡片的键名 + 文件名
CARDS = ["cover", "abstract", "takeaways", "quote", "further"]
CARD_FILENAMES = {
    "cover":     "1-封面.html",
    "abstract":  "2-摘要.html",
    "takeaways": "3-要点.html",
    "quote":     "4-金句.html",
    "further":   "5-延伸阅读.html",
}

# 4 种风格
STYLES = ["research", "wsj", "bloomberg", "minimal"]
STYLE_NAMES = {
    "research":  "机构研报风",
    "wsj":       "华尔街日报风",
    "bloomberg": "彭博终端风",
    "minimal":   "财报极简",
}


# --------- helpers ---------

def render_em(text: str) -> str:
    """把 {em}...{/em} 标记翻译成 <em>...</em>。"""
    if not text:
        return ""
    return re.sub(r"\{em\}(.+?)\{/em\}", r"<em>\1</em>", text)


def pick_style(arg: str | None, today: dt_date | None = None) -> str:
    """
    解析风格：
      - 传入合法名 → 用它
      - 传 'random' → 从 STYLES 中随机挑一个（在写 info.json 前完成，保证计数正确）
      - 传 'auto' 或 None → 按 ISO 周数 mod N 轮换
      - 其它 → 报错
    """
    if arg == "random":
        return _random.choice(STYLES)
    if arg and arg != "auto":
        if arg not in STYLES:
            raise SystemExit(f"[err] unknown style '{arg}'. available: {', '.join(STYLES)}, random, auto")
        return arg
    today = today or dt_date.today()
    week = today.isocalendar().week
    return STYLES[week % len(STYLES)]


def load_topic(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "meta" not in data:
        raise SystemExit("[err] topic JSON missing 'meta' section")
    _validate(data)
    return data


def _validate(data: dict) -> None:
    """Schema sanity checks. Warns or errors on common mistakes."""
    warnings: list[str] = []
    errors: list[str] = []

    if "takeaways" in data:
        items = data["takeaways"].get("items", [])
        n = len(items)
        if n < 3:
            errors.append(f"takeaways.items 需要至少 3 条（当前 {n} 条）")
        elif n > 5:
            errors.append(f"takeaways.items 最多 5 条（当前 {n} 条）")

    keywords = data.get("keywords")
    if not isinstance(keywords, list):
        errors.append("keywords 必须是数组（顶层字段，如 [\"k1\", \"k2\", ...]）")
    else:
        n = len(keywords)
        if n < 5:
            errors.append(f"keywords 需要至少 5 条（当前 {n} 条）")
        elif n > 10:
            errors.append(f"keywords 最多 10 条（当前 {n} 条）")

    if not data["meta"].get("focus_name"):
        warnings.append("meta.focus_name 未设置 → 不会显示关注点标签（推荐加上，避免每条都写媒体源）")

    for w in warnings:
        print(f"[warn] {w}")
    if errors:
        for e in errors:
            print(f"[err]  {e}")
        raise SystemExit(2)


# --------- info.json：按风格独立计数的 issue_no ---------

def _load_info() -> dict:
    if not INFO_JSON.exists():
        return {}
    try:
        return json.loads(INFO_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"[err] info.json 解析失败: {e}")


def _save_info(info: dict) -> None:
    INFO_JSON.write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def reserve_issue_no(style: str) -> int:
    """
    预分配本次生成使用的 issue_no：读取 info.json 中该风格的当前计数（默认 1），
    将其 + 1 写回。返回分配出去的原计数值 —— 调用方把它作为 issue_no 用，
    也用它作为回滚目标。
    """
    info = _load_info()
    current = int(info.get(style, 1))
    info[style] = current + 1
    _save_info(info)
    return current


def rollback_issue_no(style: str, old_value: int) -> None:
    """将 info.json 中 style 的计数复原到 old_value。"""
    info = _load_info()
    info[style] = old_value
    _save_info(info)


def _format_date_for_path(meta_date: str | None) -> str:
    """把 meta.date 规整成 YYYY-MM-DD 目录名；取不到就用今天。"""
    if meta_date:
        m = re.match(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", meta_date.strip())
        if m:
            y, mo, d = m.groups()
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    return dt_date.today().isoformat()


# --------- 渲染 ---------

def _render_html(topic: dict, style: str, html_dir: Path) -> list[tuple[str, Path]]:
    """把每张卡渲染为 HTML，写入指定目录。返回 [(card_key, html_path), ...]。"""
    style_dir = TEMPLATES_DIR / style
    if not style_dir.exists():
        available = ", ".join(sorted(d.name for d in TEMPLATES_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")))
        raise SystemExit(f"[err] style '{style}' has no templates yet. Available: {available}\n"
                         f"       To add it, create {style_dir}/ with 5 .html.j2 files. See templates/research/ as reference.")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,        # 内容里允许 <br> / <strong> 等
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["em"] = render_em
    logo_uri = _logo_data_uri()

    html_dir.mkdir(parents=True, exist_ok=True)
    written: list[tuple[str, Path]] = []

    for idx, card in enumerate(CARDS, start=1):
        if card not in topic:
            print(f"  - skip {card} (no data in JSON)")
            continue
        tmpl_path = f"{style}/{card}.html.j2"
        template = env.get_template(tmpl_path)
        html = template.render(
            meta=topic["meta"],
            data=topic[card],
            page_no=idx,
            total_pages=len(CARDS),
            style=style,
            style_name=STYLE_NAMES[style],
            logo_uri=logo_uri,
        )
        out = html_dir / CARD_FILENAMES[card]
        out.write_text(html, encoding="utf-8")
        written.append((card, out))
    return written


def build(topic: dict, style: str, output_dir: Path, keep_html: bool = False) -> list[Path]:
    """渲染 5 张卡为 PNG 到 output_dir。默认不保留 HTML；传 keep_html=True 才保留。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    if keep_html:
        html_pairs = _render_html(topic, style, output_dir)
        for _, f in html_pairs:
            try:
                rel = f.relative_to(PROJECT_ROOT)
            except ValueError:
                rel = f
            print(f"  ✓ {rel}")
        _png_export(html_pairs, output_dir)
        return [output_dir / f"{Path(CARD_FILENAMES[k]).stem}.png" for k, _ in html_pairs]

    # 默认：HTML 只是中间产物，写入临时目录，渲完 PNG 就丢
    with tempfile.TemporaryDirectory(prefix="xsh-cards-") as tmp:
        html_pairs = _render_html(topic, style, Path(tmp))
        _png_export(html_pairs, output_dir)
    return [output_dir / f"{Path(CARD_FILENAMES[k]).stem}.png" for k, _ in html_pairs]


def _png_export(html_pairs: list[tuple[str, Path]], png_dir: Path) -> None:
    """把每个 HTML 渲染成 PNG，输出到 png_dir。"""
    renderer = SCRIPT_DIR / "render_png.py"
    if not renderer.exists():
        raise SystemExit("[err] render_png.py not found")
    for card, html_path in html_pairs:
        png_out = png_dir / f"{Path(CARD_FILENAMES[card]).stem}.png"
        subprocess.run(
            [sys.executable, str(renderer), str(html_path), "--out", str(png_out)],
            check=True,
        )


def _make_zip(files: list[Path], zip_path: Path) -> None:
    """把渲染好的产物打包成 zip（只保留 basename，便于直接分享一份卡包）。"""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f.name)


def _write_keyword_json(keywords: list[str], out_path: Path) -> None:
    """把 topic.keywords 写成 keyword.json，与 5 张 PNG 同目录。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"keywords": list(keywords)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# --------- CLI ---------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("topic", help="topic JSON 文件路径")
    ap.add_argument("--style", default="auto", help="风格名 / 'auto'（按周轮换）/ 'random'（随机）")
    ap.add_argument("--output", "-o", help="输出目录（默认 output/YYYY-MM-DD/<slug>/）")
    ap.add_argument("--keep-html", action="store_true", help="保留中间产物 HTML（默认只输出 PNG）")
    ap.add_argument("--list-styles", action="store_true", help="列出所有风格")
    args = ap.parse_args()

    if args.list_styles:
        for s in STYLES:
            has = (TEMPLATES_DIR / s).exists()
            mark = "✓" if has else "○"
            print(f"  {mark} {s:<12}{STYLE_NAMES[s]}" + ("" if has else "  (待实现)"))
        return 0

    topic_path = Path(args.topic)
    if not topic_path.exists():
        print(f"[err] topic file not found: {topic_path}", file=sys.stderr)
        return 2

    topic = load_topic(topic_path)
    style = pick_style(args.style)
    print(f"Style: {style}  ({STYLE_NAMES[style]})")

    # 预分配 issue_no 并注入 meta；失败时需回滚到这个值
    issue_no = reserve_issue_no(style)
    topic["meta"]["issue_no"] = f"{issue_no:03d}"
    print(f"Issue: #{topic['meta']['issue_no']}  ({style} 计数器)")

    try:
        slug = topic.get("slug") or topic["meta"].get("slug") or topic_path.stem
        if args.output:
            output_dir = Path(args.output)
        else:
            date_dir = _format_date_for_path(topic["meta"].get("date"))
            output_dir = DEFAULT_OUTPUT_PARENT / date_dir / slug
        print(f"Output: {output_dir}\n")

        files = build(topic, style, output_dir, keep_html=args.keep_html)
        keyword_path = output_dir / "keyword.json"
        _write_keyword_json(topic["keywords"], keyword_path)
        zip_path = output_dir.parent / f"{slug}.zip"
        _make_zip(files + [keyword_path], zip_path)
    except BaseException:
        rollback_issue_no(style, issue_no)
        print(f"[err] 生成失败，已回滚 info.json: {style} -> {issue_no}", file=sys.stderr)
        raise

    for f in files + [keyword_path, zip_path]:
        try:
            rel = f.relative_to(PROJECT_ROOT)
        except ValueError:
            rel = f
        print(f"  ✓ {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
