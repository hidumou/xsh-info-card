# SupSub 金融信息卡片工作台

小红书 / 朋友圈 3:4 竖版（720×960）金融信息卡片生产流水线：
**JSON 数据 → Jinja2 模板 → HTML → PNG**，按周自动轮换风格，统一向 supsub.ai 导流。

## 目录结构

```
xsh-info-card/
├── README.md           本文件
├── info.json           各风格 issue_no 计数器（入 git，保证计数全局一致）
│                       形如 {"research":1,"wsj":1,"bloomberg":1,"minimal":1}
├── topics/             话题 JSON 输入（按 tools/schema.md 撰写）
├── tools/              生成工具链
│   ├── scripts/        build_cards.py / render_png.py
│   ├── templates/      风格模板（research / wsj / bloomberg / minimal）
│   ├── assets/         logo.png 等静态资源
│   ├── schema.md       话题 JSON 字段说明
│   └── README.md       工具用法
└── output/             生成产物
    └── YYYY-MM-DD/
        └── <slug>/     每个话题一个目录，内含 5 张 PNG
```

## 日常工作流

```bash
# 1. 准备 topic JSON（按 tools/schema.md 生成）
#    放到 topics/topic_<name>.json

# 2. 生成 5 张 PNG（自动按周轮换风格）
python3 tools/scripts/build_cards.py topics/topic_<name>.json

# 3. 产物在 output/YYYY-MM-DD/<slug>/
#    - 1-封面.png
#    - 2-摘要.png
#    - 3-要点.png
#    - 4-金句.png
#    - 5-延伸阅读.png
```

## issue_no 机制（info.json）

- `info.json` 是每个风格的独立计数器账本，形如 `{"research":1,"wsj":1,"bloomberg":1,"minimal":1}`，默认 1
- **不按日期计数**：每出一张卡累加 1，持续跨天
- 生成前先读取当前值、写回 +1，作为本次使用的 `issue_no`
- 若生成中途失败，计数器自动回滚到原值（且不产生代码提交）
- `info.json` **需要提交到 git**，以保证下次生成时计数不断档

## 固定品牌元素（模板内已内置）

- 页眉：SupSub Logo + 期号 / 日期
- 页脚上方：`来自关注点 · SupSub · {{ focus_name }} · #{{ issue_no }}`（浅灰小字）
- 页脚：`supsub.ai` + 合规话术 + 页码
- 尾页 CTA：Logo + slogan「把注意力留给有价值的内容」+ supsub.ai

## 模板支持的排版

- `{em}关键词{/em}` → 金色加粗 `<em>`
- `<strong>` → 深蓝加粗
- `<ul><li>` / `<ol><li>` → 自动格式化的无序/有序列表
- `<br>` → 换行

## 要点卡规则

- 3-5 条之间（<3 或 >5 生成器报错）
- 4-5 条时自动收紧字号与间距
