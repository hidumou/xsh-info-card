# 卡片生产流水线

## 流程

```
  [Claude 从 SupSub Focus 挑信号]
         ↓
  [整理为 topics/topic_<name>.json（按 schema.md 格式）]
         ↓
  [build_cards.py → 5 张 PNG（默认只出 PNG，不留 HTML）]
         ↓
  [发布到小红书/朋友圈 → 导流 supsub.ai]
```

## 目录

```
tools/
├── README.md              本文件
├── schema.md              JSON 数据格式完整说明
├── scripts/
│   ├── build_cards.py     主生成器：JSON → PNG（内部用 Jinja2 渲 HTML + Playwright 截图）
│   └── render_png.py      HTML → PNG（Playwright，供 build_cards.py 调用，也可独立用）
├── assets/
│   └── logo.png           SupSub logo，build_cards.py 读成 data URI 注入模板
└── templates/
    ├── research/          机构研报风（Foreign Affairs / HBR 质感）
    ├── wsj/               华尔街日报风（1890s 活版铅印大报）
    ├── bloomberg/         彭博终端风（CRT 任务控制台）
    └── minimal/           财报极简（Kinfolk / Muji 编辑风）
```

话题输入在项目根的 `topics/`，输出到项目根的 `output/YYYY-MM-DD/<slug>/`。

## 依赖

```bash
pip install Jinja2 playwright --break-system-packages
playwright install chromium
```

## 命令

```bash
# 按 ISO 周数自动轮换风格，渲染 5 张 PNG 到 output/YYYY-MM-DD/<slug>/
python3 tools/scripts/build_cards.py topics/topic_xxx.json

# 随机挑一个风格（在写 info.json 前完成，计数不会错乱）
python3 tools/scripts/build_cards.py topics/topic_xxx.json --style random

# 指定风格，输出到自定义目录
python3 tools/scripts/build_cards.py topics/topic_xxx.json --style research --output output/custom/

# 调试时保留中间产物 HTML
python3 tools/scripts/build_cards.py topics/topic_xxx.json --keep-html

# 查看风格清单
python3 tools/scripts/build_cards.py --list-styles topics/topic_xxx.json
```

## 风格

| key | 名称 | 设计 DNA |
|---|---|---|
| research | 机构研报风 | Fraunces + EB Garamond，❦ 花饰分隔，陈年金 + 暗酒红 + 米色纸 |
| wsj | 华尔街日报风 | Playfair Display + IM Fell，drop cap，纸纹网点，报纸红/黑 |
| bloomberg | 彭博终端风 | JetBrains Mono，CRT 扫描线，磷光发光，ASCII 盒线 |
| minimal | 财报极简 | Fraunces opsz 极变，熔金重音，0.5px 发丝线，6px 节律 |

自动轮换规则：ISO 周数 mod 4 → research / wsj / bloomberg / minimal。用 `--style <key>` 显式指定则不轮换；`--style random` 则随机挑一个（挑选发生在读写 `info.json` 之前，保证计数不串）。

## issue_no 机制

- 项目根 `info.json` 按风格各自计数，默认 1，不按日期
- 每次生成前计数器 +1 并写回作为本次 `issue_no`（覆盖 topic JSON 里的原值，格式 `"001"`）
- 生成失败自动回滚（且不产生代码提交），不会跳号
- `info.json` 需提交到 git，以保证计数全局一致

## JSON 字段约定

见 [`schema.md`](schema.md)。关键要点：

- 顶层：`slug` + `meta` + `cover` / `abstract` / `takeaways` / `quote` / `further`（五张卡，省略即不生成）
- `meta.focus_name` 必填：对应 SupSub 关注点名，显示在每张卡页脚上方
- `meta.issue_no` 会被 `info.json` 覆盖，topic JSON 里可省略
- `takeaways.items` 数量 **3-5 条**，小于 3 或大于 5 会报错；4-5 条时自动收紧排版
- 正文字段支持：
  - `{em}...{/em}` → 金色/朱砂红高亮（按风格不同）
  - `<strong>` → 深色加粗
  - `<ul><li>` / `<ol><li>` → 列表
  - `<br>` → 换行

JSON schema 所有风格共享，无需针对风格改数据格式。

## 每日自动化

每天 09:00 Asia/Shanghai，Claude Code remote routine 会：
1. 从 SupSub 拉当日关注点 markdown
2. 挑 3 条主线生成 3 个 topic JSON
3. 每个话题渲染 4 套风格 × 5 张 = 20 张 PNG
4. 直接 commit 到 `main`

路由管理：https://claude.ai/code/routines/trig_017EghofernGGz385Ako2Foo
