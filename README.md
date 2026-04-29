# SupSub 金融信息卡片工作台

小红书 / 朋友圈 3:4 竖版（720×960）金融信息卡片生产流水线：
**JSON 数据 → Jinja2 模板 → HTML → PNG**。

## 目录结构

```
xsh-info-card/
├── README.md           本文件
├── info.json           各风格 issue_no 计数器（入 git，保证计数全局一致）
│                       形如 {"research":3,"wsj":5,"bloomberg":5,"minimal":6}
├── topics/             话题 JSON 输入（按 tools/schema.md 撰写）
│   └── topic_YYYYMMDD_<slug>.json
├── tools/              生成工具链
│   ├── README.md       工具用法
│   ├── schema.md       话题 JSON 字段说明
│   ├── scripts/
│   │   ├── build_cards.py   主生成器：JSON → 5 张 PNG（+ keyword.json + zip）
│   │   └── render_png.py    HTML → PNG（Playwright，被 build_cards.py 调用）
│   ├── templates/      4 套风格模板
│   │   ├── research/   机构研报风
│   │   ├── wsj/        华尔街日报风
│   │   ├── bloomberg/  彭博终端风
│   │   └── minimal/    财报极简
│   └── assets/
│       └── logo.png    SupSub logo（注入为 data URI）
└── output/             生成产物
    └── YYYY-MM-DD/
        ├── <slug>/             每个话题一个目录
        │   ├── 1-封面.png
        │   ├── 2-摘要.png
        │   ├── 3-要点.png
        │   ├── 4-金句.png
        │   ├── 5-延伸阅读.png
        │   └── keyword.json    话题关键词（5-10 条）
        └── <slug>.zip          5 张 PNG + keyword.json 的同名打包
```

## 日常工作流

```bash
# 1. 准备 topic JSON（按 tools/schema.md 生成），命名建议：
#    topics/topic_YYYYMMDD_<slug>.json

# 2. 生成 5 张 PNG（自动按 ISO 周轮换风格）
python3 tools/scripts/build_cards.py topics/topic_xxx.json

# 3. 产物落到 output/YYYY-MM-DD/<slug>/，同时打包同级 <slug>.zip

# 常用变体
python3 tools/scripts/build_cards.py topics/topic_xxx.json --style wsj          # 指定风格
python3 tools/scripts/build_cards.py topics/topic_xxx.json --style random       # 随机挑一
python3 tools/scripts/build_cards.py topics/topic_xxx.json --keep-html          # 保留中间 HTML
python3 tools/scripts/build_cards.py topics/topic_xxx.json -o output/custom/    # 自定义输出
python3 tools/scripts/build_cards.py --list-styles topics/topic_xxx.json        # 查看风格清单
```

依赖一次性安装：

```bash
pip install Jinja2 playwright --break-system-packages
playwright install chromium
```

## 卡片风格

四套风格共享一份 JSON schema，无需为风格改数据；按 ISO 周数 `% 4` 自动轮换。
`{em}` 高亮在每套风格里映射到不同重音色（陈年金 / 报纸红 / 磷光绿 / 熔金）。

| `research` 机构研报风 | `wsj` 华尔街日报风 |
|---|---|
| <img src="output/2026-04-27/半导体上行-算力瓶颈/1-封面.png" width="320"> | <img src="output/2026-04-26/deepseek-v4-国产闭环/1-封面.png" width="320"> |
| **`bloomberg` 彭博终端风** | **`minimal` 财报极简** |
| <img src="output/2026-04-27/deepseek-v4-价格战-国产闭环/1-封面.png" width="320"> | <img src="output/2026-04-29/AI存储缺口-量价齐升/1-封面.png" width="320"> |

显式指定 `--style <key>` 不轮换；`--style random` 在写 `info.json` 之前随机挑选，保证计数不串。

## issue_no 机制（info.json）

- `info.json` 每个风格各自维护一个计数器，形如 `{"research":3,"wsj":5,"bloomberg":5,"minimal":6}`
- **不按日期计数**：每出一张卡累加 1，跨天持续
- 生成前先读取当前值、写回 +1，作为本次使用的 `issue_no`（覆盖 topic JSON 里的原值，三位零填充如 `"001"`）
- 生成失败会回滚到原值且不留代码提交，不会跳号
- `info.json` **必须提交到 git**，下次生成才不会断档

## 固定品牌元素（模板内已内置）

- 页眉：SupSub Logo + 期号 / 日期 / 主题 tag
- 页脚上方：`来自关注点 · SupSub · {{ focus_name }} · #{{ issue_no }}`（浅灰小字）
- 页脚：`supsub.ai` + 合规话术 + 页码（如 `1/5`）
- 尾页 CTA：Logo + slogan「把注意力留给有价值的内容」+ supsub.ai

## 模板支持的排版

| 标记 | 渲染结果 |
|---|---|
| `{em}关键词{/em}` | 各风格主重音色加粗 `<em>`（金 / 红 / 磷光绿 / 熔金） |
| `<strong>` | 深色加粗 |
| `<ul><li>` / `<ol><li>` | 自动格式化的无序 / 有序列表 |
| `<br>` | 换行 |

正文字段统一关闭 Jinja2 自动转义，标记原样输出。

## 关键校验规则

- `keywords`：顶层数组 5-10 条，写入 `keyword.json` 与 zip
- `takeaways.items`：3-5 条，少于 3 或多于 5 直接报错；4-5 条时模板自动收紧字号与间距
- `meta.focus_name`：缺省会 warn，但不影响生成（页脚不再展示关注点标签）
- 缺哪张卡的字段，对应 PNG 自动跳过

详细字段约定见 [`tools/schema.md`](tools/schema.md)。

## 每日自动化

每天 09:00 Asia/Shanghai，Claude Code remote routine 会：

1. 从 SupSub 拉当日关注点 markdown
2. 挑 3 条主线生成 3 个 topic JSON
3. 当周风格渲染每个话题 5 张 PNG + keyword.json + zip
4. 直接 commit 到 `main`
