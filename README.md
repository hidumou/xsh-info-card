# SupSub 金融信息卡片工作台

小红书 / 朋友圈 3:4 竖版（720×960）金融信息卡片生产流水线：
**JSON 数据 → Jinja2 模板 → HTML → PNG**，按周自动轮换风格，统一向 supsub.ai 导流。

## 日常工作流

```bash
# 1. 准备 topic JSON（我按 schema.md 生成）
#    放到 工具/例子/topic_<name>.json

# 2. 生成 HTML + PNG
python3 工具/build_cards.py 工具/例子/topic_<name>.json --png

# 3. 输出到 信息内容/<slug>/
#    - 1-封面.png / .html
#    - 2-摘要.png / .html
#    - 3-要点.png / .html
#    - 4-金句.png / .html
#    - 5-延伸阅读.png / .html
```

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
