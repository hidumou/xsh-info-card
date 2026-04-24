# 卡片生产流水线

## 流程

```
  [Claude 从 SupSub Focus 挑信号]
         ↓
  [整理为 topic.json（按 schema.md 格式）]
         ↓
  [build_cards.py → 5 张 HTML]
         ↓
  [render_png.py → 5 张 PNG（可选）]
         ↓
  [发布到小红书/朋友圈 → 导流 supsub.ai]
```

## 目录

```
工具/
├── build_cards.py          # 主生成器：JSON → HTML
├── render_png.py           # HTML → PNG（Playwright）
├── remove_watermark.py     # AI 图水印去除小工具
├── schema.md               # JSON 数据格式完整说明
├── README.md               # 本文件
├── 例子/
│   └── topic_ai_infra_0424.json    # 示例 topic
└── templates/
    └── research/           # 机构研报风（完整实现）
        ├── _base.css
        ├── _header.html.j2
        ├── _footer.html.j2
        ├── _focus_line.html.j2
        ├── cover.html.j2
        ├── abstract.html.j2
        ├── takeaways.html.j2
        ├── quote.html.j2
        └── further.html.j2
```

## 依赖

```bash
pip install Jinja2 --break-system-packages
# 需要 PNG 时再装：
pip install playwright --break-system-packages
playwright install chromium
```

## 命令

```bash
# 生成 HTML，按 ISO 周数自动轮换风格
python3 工具/build_cards.py 工具/例子/topic_xxx.json

# 强制指定风格
python3 工具/build_cards.py topic.json --style research

# 同时导出 PNG
python3 工具/build_cards.py topic.json --png

# 查看风格清单
python3 工具/build_cards.py --list-styles topic.json
```

默认输出到 `信息内容/<slug>/`，其中 `slug` 来自 `topic.json` 顶层的 `slug` 字段。

## JSON 字段约定

见 [`schema.md`](schema.md)。关键要点：

- 顶层：`slug` + `meta` + `cover` / `abstract` / `takeaways` / `quote` / `further`（五张卡，省略即不生成）
- `meta.focus_name` 必填：对应 SupSub 关注点名，显示在每张卡页脚上方
- `takeaways.items` 数量 **3-5 条**，小于 3 或大于 5 会报错；4-5 条时自动收紧排版
- 正文字段支持：
  - `{em}...{/em}` → 金色高亮
  - `<strong>` → 深色加粗
  - `<ul><li>` / `<ol><li>` → 列表
  - `<br>` → 换行

## 风格轮换

按 ISO 周数 mod 6：

| 周数 mod 6 | 风格 key | 显示名 | 状态 |
|---|---|---|---|
| 1 | research | 机构研报风 | ✅ |
| 2 | wsj | 华尔街日报风 | ⏳ 待 Jinja2 化 |
| 3 | bloomberg | 彭博终端风 | ⏳ 待 Jinja2 化 |
| 4 | minimal | 财报极简 | ⏳ 待 Jinja2 化 |
| 5 | cn | 中式研报 | ⏳ 待 Jinja2 化 |
| 0 | quant | 量化数据风 | ⏳ 待 Jinja2 化 |

用 `--style auto` 启用轮换；未实现的风格会报错并列出已有风格。

## 扩展：添加新风格

1. 拷贝 `templates/research/` 为 `templates/<new_style>/`
2. 修改 `_base.css` 里的主色、字体栈、背景
3. 按需调整各卡的独立 CSS（`cover.html.j2` 等文件顶部的 `<style>` 区）
4. header/footer/focus_line 三个 partial 保持结构一致，只改配色
5. 测试：`python3 build_cards.py 例子/topic_xxx.json --style <new_style>`

JSON schema 所有风格共享，无需针对风格改数据格式。

## 其他小工具

- `remove_watermark.py`：去除 AI 生成图右下角水印（支持 box 填充、灰字识别、透明底保留）。用法见脚本内 docstring。
