---
name: daily-cards
description: 生成当日 3 期金融信息卡片：从 SupSub 信号源挑 3 个主题，每主题随机抽 1 套风格（research / wsj / bloomberg / minimal）渲染 5 张 720×960 竖版 PNG（小红书 / 朋友圈直发尺寸），共 15 张输出到 output 目录。当用户说"跑今日卡片""生成今日卡片""做今天的 3 期""做一期金融卡片""每日打理""daily routine""daily cards"或要求按今日信号产出小红书 / 朋友圈卡片时使用。
disable-model-invocation: true
---

# /daily-cards

把当日 SupSub 关注点信号转成 3 期金融信息卡片，输出到 `output/<YYYY-MM-DD>/<slug>/`。3 话题 × 5 张卡 = 15 张 720×960 PNG。

## 6 步流程

### 第 1 步 · 拉今日信号源

公开免认证，用 curl 或 WebFetch：

```
https://supsub.net/feed/560cf9aa-7e11-4315-876f-8b4cdd5f1607/focuses/711/markdown
```

### 第 2 步 · 挑 3 个视角错开的主题

从信号里挑 3 条最值得做卡片的主线。优先选：

- 有硬数字（金额、百分比、期货价、份额）
- 有一线 CEO / 头部机构 / 监管层源头
- 能串起多条同日信号的结构性话题
- 对中文投资者 / 创业者有明确价值

3 个主题视角错开（硬件 / 模型 / 资金 或 宏观 / 行业 / 公司），不要选 3 条同主题的不同角度。

信号不够 3 条就有多少做多少（最少 1 条）。一条都拼不成 → 跳第 6 步打印「今日无合适主题」并终止。

### 第 3 步 · 写 3 份 topic JSON

每个主题一份，保存到 `topics/topic_<YYYYMMDD>_<slug>.json`。字段定义见 `tools/schema.md`，可参考 `topics/topic_ai_infra_0424.json` 样例。

要点：

- `meta.issue_no` 留空字符串 `""`，脚本会按风格独立递增后覆盖写入
- `meta.date`：`YYYY.MM.DD`，3 个文件同一天
- `meta.kicker_default`：`DAILY BRIEF · 今日信号`
- `meta.focus_name`：`人工智能动态`
- `cover.kpi`：3 个 KPI 格
- `quote`：最有冲击力的一句话 + 说话人身份 + 场合
- `further.groups`：4 个分组，每组 2-3 条
- 高亮用 `{em}...{/em}`，不要写 `<em>`；换行用 `<br>`
- `takeaways.items` 必须 3-5 条；`keywords` 必须 5-10 条

### 第 4 步 · 渲染（每话题随机风格）

首次需装依赖（约 200MB，3-5 分钟）：

```bash
pip install Jinja2 playwright --break-system-packages
playwright install chromium
```

对每个话题各调用一次：

```bash
python3 tools/scripts/build_cards.py topics/topic_<YYYYMMDD>_<slug>.json --style random
```

- 风格统一 `--style random`，**不要** `--style auto`，也不要手选
- 不要传 `--output`，让脚本按 `output/<meta.date>/<slug>/` 自动生成
- 抽到的风格看 stdout 的 `Style: xxx` 一行，记下用于收尾报告
- 渲染失败脚本会自动回滚 `info.json` 对应风格的计数器，不会跳号

### 第 5 步 · 验证

每话题 `output/<YYYY-MM-DD>/<slug>/` 下应有 5 张 PNG，大小 100KB-500KB。任一缺张或 <30KB / >500KB → 该话题算失败，从收尾报告里标 ✗；其他话题照常。

### 第 6 步 · 收尾报告

打印结构化报告：

- 3 个话题的标题、slug、抽到的风格、脚本分配的 `issue_no`
- 每话题 5 张 PNG 渲染状态（✓ / ✗）
- PNG 完整路径列表（用户可直接打开预览）

## 失败处理

- **渲染失败**：`build_cards.py` 自动回滚 `info.json`，无需手动处理
- **playwright 装失败**：retry 一次；再失败报告「playwright 不可用」并终止
