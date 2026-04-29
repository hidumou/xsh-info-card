# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

一条 **金融信息卡片自动产线**：JSON → Jinja2 模板 → HTML → PNG，按周/随机轮换 4 套风格（research / wsj / bloomberg / minimal），每天产出 3 期 × 5 张 720×960 竖版 PNG。业务背景见 [`README.md`](README.md)。

## 数据规范

写或修改 topic JSON 前必读 [`tools/schema.md`](tools/schema.md)。硬约束：

## 内容标记

正文字段统一用以下标记，**不要直接写 `<em>`**：

| 标记 | 说明 |
|---|---|
| `{em}关键词{/em}` | 高亮（各风格映射不同重音色：陈年金 / 报纸红 / 磷光绿 / 熔金） |
| `<br>` | 换行（Jinja2 关闭了 autoescape） |
| `<ul><li>` / `<ol><li>` | 列表 |
| `<strong>` | 深色加粗 |

## 文件命名

- topic JSON：`topics/topic_YYYYMMDD_<slug>.json`，`<slug>` 可中文短词或 ASCII kebab-case
- 同日多个 slug 不能重复
- 输出 PNG 文件名固定：`1-封面.png` / `2-摘要.png` / `3-要点.png` / `4-金句.png` / `5-延伸阅读.png`

## info.json 是账本

`info.json` 是 4 套风格各自的累计期号账本（不按日期），**必须 commit**，否则计数跨天断档。`build_cards.py` 在渲染前预占号、失败自动回滚 —— **别手工改**。

## 不要碰
- 已生成的 `output/` 历史目录：不清理、不覆盖
