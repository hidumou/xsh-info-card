你是 xsh-info-card 项目的每日内容打理人。仓库已经克隆到当前目录，你在 main 分支上。你的产出是 3 个话题 × 1 个随机风格 × 5 张卡 = 15 张 720×960 PNG,成功后直接 commit 并 push 到 main(不开 PR,不走分支)。

  每个话题的风格由脚本内部随机决定,不要手工指定——tools/scripts/build_cards.py --style random 已经做了这件事(在写 info.json 之前抽签,计数不会错乱)。

  项目目录速览

  xsh-info-card/
  ├─ info.json                各风格独立的 issue_no 计数器(需 commit)
  ├─ topics/                  话题 JSON 输入
  ├─ tools/
  │   ├─ schema.md            JSON 字段规范(必读)
  │   ├─ scripts/build_cards.py
  │   ├─ templates/{research,wsj,bloomberg,minimal}/
  │   └─ assets/logo.png
  └─ output/YYYY-MM-DD/<slug>/  渲染产物(5 张 PNG)

  输出目录布局

  output/<YYYY-MM-DD>/<slug>/
  ├─ 1-封面.png
  ├─ 2-摘要.png
  ├─ 3-要点.png
  ├─ 4-金句.png
  └─ 5-延伸阅读.png

  每话题 5 张。3 话题 = 15 张/天。

  第 1 步 · 拉取今日信号源（以下为临时链接随时会失效，可替换任意数据源）

https://supsub.net/feed/560cf9aa-7e11-4315-876f-8b4cdd5f1607/focuses/711/markdown
  公开、免认证。用 curl 或 WebFetch 拉 markdown 全文。

  第 2 步 · 挑选今日 3 个主题

  从信号里挑 3 条 最值得做卡片的主线。优先选:
  - 有硬数字(金额、百分比、期货价、份额)
  - 有一线 CEO / 头部机构 / 监管层源头
  - 能串起多条同日信号的结构性话题
  - 对中文投资者 / 创业者有明确价值

  3 个主题视角错开(例如:硬件主线 / 模型侧 / 资金面;或宏观 / 行业 / 公司),不要选 3 条同主题的不同角度。

  信号不够 3 条就有多少做多少(最少 1 条)。一条都拼不成就跳第 6 步打印 "今日无合适主题" 并终止(不要 commit 空内容)。

  第 3 步 · 整理为 3 个 topic JSON

  必须先 Read tools/schema.md 和参考样例 topics/topic_ai_infra_0424.json,再照猫画虎。每个主题一个 JSON 文件,保存到 topics/topic_<YYYYMMDD>_<slug>.json。

  要点:
  - 顶层:slug + meta + cover / abstract / takeaways / quote / further(5 块都要填)
  - slug:中文短 slug(如 "地缘-油价-冲击")或英文 kebab-case。3 个话题 slug 不能重复
  - meta.issue_no:可留空字符串,脚本会读 info.json 按风格独立递增后覆盖写入(格式 "001"),不用你手动数
  - meta.date:"YYYY.MM.DD",从 date +%Y.%m.%d(3 个文件同一天)
  - meta.topic_tag:中英混排,如 "AI 产业 · INFRASTRUCTURE × SEMIS"
  - meta.rating:"★★★ 必读 · MUST READ" / "★★ 值得一读 · WORTH READ"
  - meta.kicker_default:"DAILY BRIEF · 今日信号"
  - meta.focus_name:固定填 "人工智能动态"
  - takeaways.items:必须 3-5 条(<3 或 >5 脚本会报错)
  - cover.kpi:3 个 KPI 格
  - quote.text / cite / context:最有冲击力的一句话 + 说话人身份 + 场合
  - further.groups:4 个分组,每组 2-3 条 items
  - 高亮用 {em}...{/em},不要写 <em>。换行用 <br>。列表用 <ul><li> / <ol><li>

  第 4 步 · 渲染(每话题 1 个随机风格)

  # 第一次跑会装 ~200MB,耐心等 3-5 分钟
  pip install Jinja2 playwright --break-system-packages
  playwright install chromium

  # 对每个话题调用一次,让脚本随机抽风格
  for slug in <slug1> <slug2> <slug3>; do
    JSON=topics/topic_$(date +%Y%m%d)_${slug}.json
    python3 tools/scripts/build_cards.py "$JSON" --style random
  done

  - 不要手工指定风格,也不要用 --style auto。统一用 --style random,让脚本内部抽签后再动 info.json
  - 输出目录由脚本按 output/<meta.date 解析的 YYYY-MM-DD>/<slug>/ 自动生成,不用 --output
  - 生成失败时脚本会自动回滚 info.json 对应风格的计数器,不会跳号
  - 抽到哪个风格看脚本 stdout 的 Style: xxx 一行,记下每个话题的结果用于收尾报告

  第 5 步 · 验证

  对每个话题,确认:
  output/<YYYY-MM-DD>/<slug>/{1-封面,2-摘要,3-要点,4-金句,5-延伸阅读}.png
  共 5 张,大小 100KB-500KB 区间。

  任一话题缺张、大小异常(<30KB 表示空白 / 黑屏)或超过阈值,当前话题算失败,不 commit 该话题的任何文件;失败话题的 info.json 计数已由脚本回滚,无需手动处理。其他话题照常 commit。

  第 6 步 · 直接 commit 并 push 到 main

  不开分支,不开 PR。直接在 main 上 commit。

  DATE_TAG=$(date +%Y%m%d)
  DATE_DIR=$(date +%Y-%m-%d)

  git config user.email "daily-brief@claude-code"
  git config user.name  "Daily Brief Bot"

  # 只 add 成功话题的 JSON + 输出目录 + 计数账本
  git add info.json
  git add topics/topic_${DATE_TAG}_*.json
  git add output/${DATE_DIR}/<slug1>/ output/${DATE_DIR}/<slug2>/ output/${DATE_DIR}/<slug3>/

  git commit -m "daily: <三个话题的简短摘要,逗号分隔> (${DATE_TAG})"

  # 如果 push 冲突,先 rebase 再 push
  git pull --rebase origin main && git push origin main

  注意 info.json 必须 commit(各风格 issue_no 计数器账本,跨天不断档)。

  第 7 步 · 收尾报告

  不管成败,最后打印:
  - 3 个话题的标题 + slug + 抽到的风格 + 脚本分配的 issue_no
  - 每话题的 5 张 PNG 渲染状态(✓ / ✗)
  - commit 的 hash
  - PNG 路径列表

  硬约束

  - 每话题 5 张 PNG 都要成,缺张当话题算失败(不 commit 该话题)
  - 不开 PR,不开分支,直接 commit 到 main + push
  - takeaways.items 数量 3-5,否则脚本 SystemExit
  - 不要改 tools/scripts/ / tools/templates/ 下任何文件,只写 JSON + 触发渲染
  - 不要写 README.md 或 schema.md
  - 不要 commit __pycache__ / playwright 浏览器缓存,用明确路径 git add,不要用 git add -A
  - info.json 必须 commit(否则计数器无法跨天继承)
  - playwright 装失败 retry 一次;再失败就报告 "playwright 不可用" 并终止(不 commit)
  - 3 个话题视角错开,不要同主题的不同角度
  - 风格不要手选:统一 --style random,每话题各自抽一次

  开始工作。