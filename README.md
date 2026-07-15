# 猫笔叨鱼盆复盘项目

目标：把公众号文章和鱼盆表格整理成趋势买入方向雷达，而不是泛投资资讯系统。

当前只专精一种买法：趋势买入 = 鱼盆前排 + 站上20日线 + 板块强于大盘。

Web V1 已恢复为只读方向雷达。它只消费校验后的结构化快照，不是新的项目事实源。

## 当前产品迭代重点

1. 趋势买入条件是否足够清晰、可执行。
2. 方向池是否能直接给出主攻、试探、趋势保持、等待、回避。
3. 每次新增文章和鱼盆表格是否能稳定更新当前判断。

## 入口

1. 项目级上下文：`docs/project-context.md`，维护长期有效的项目目标、边界、文件职责和执行约束。
2. 当前操作看板：`docs/action-board.md`，唯一维护当前市场状态、方向池、操作倾向和验证点。
3. 历史完整报告：`docs/reading-report.md`，归档全部文章总结、阶段总结、历史鱼盆数据。
4. 鱼盆方法指南：`docs/yupen-guide.md`，沉淀鱼盆模型读法、误区修正和动作规则。
5. 产品流转流程：`docs/product-flow.md`，说明从新文章到趋势复盘的完整流转。

系统执行入口为根目录 `AGENTS.md`。它规定项目任务的读取顺序和最低完成标准。

## 系统文件

1. 链接处理记录：`data/maobidao-link-log.md`，作为抓取脚本的链接来源。
2. 指数排名数据：`data/yupen-index-ranking.csv`，由完整读表数据自动生成可对比的指数排名序列。
3. 完整读表数据：`data/yupen-observations.csv`，统一保存最新指数和板块字段。
4. 文章方向态度：`data/article-direction-stances.csv`，只记录明确支持或明确反对，未记录即中性。
5. 方向信号快照：`data/direction-signals.csv`，由结构化观测和文章态度自动生成。
6. 信号生命周期：`data/signal-episodes.csv`，由方向信号自动生成，用于统计主攻确认、结束和假突破。
7. 文章缓存：`data/maobidao_articles.json`。
8. 鱼盆图片记录：`data/yupen_image_records.json`。
9. 鱼盆图片：`data/yupen-images/`。
10. 抓取、规则和校验脚本：`scripts/`。
11. 自动测试：`tests/`。

## 更新顺序

新增链接 -> 抓取正文 -> 有鱼盆表时抓图并分别核对数据日、标记图片已确认 -> 更新结构化数据和文章态度 -> 生成指数排名、方向信号和信号生命周期 -> 更新操作看板 -> 归档报告 -> 如有新认知，更新鱼盆指南。

每次更新依次运行：

```bash
python3 scripts/build_index_ranking.py
python3 scripts/build_direction_signals.py
python3 scripts/build_signal_lifecycle.py
python3 scripts/validate_project.py
```

存在未人工确认的鱼盆图片、过期派生数据或文档漂移时，校验必须失败。

当前行情结论只允许出现在操作看板里。指南可以随文章迭代方法，但不维护当前行情判断。

## Web V1

Web 展示当前市场摘要、五组方向池、按日期排名变化、三条件与增强证据、文章态度、下一验证点、鱼盆原图和信号生命周期。

本地运行：

```bash
cd web
npm run dev
```

`dev` 和 `build` 都会先运行项目校验并生成 `web/public/data/project-snapshot.json`。校验失败时不会发布新快照。

第一版不做实时行情、数据库、自动交易、投资建议。

方向池规格以 `docs/product-flow.md` 和 `docs/action-board.md` 为准。

## GitHub Pages 发布

推送 `main` 分支后，`.github/workflows/deploy-pages.yml` 会自动执行项目测试、校验、快照构建和 GitHub Pages 部署。`web/dist` 与生成后的 Web 快照不提交到仓库。

后续新增文章仍按“更新项目事实 -> 运行校验 -> 提交并推送 `main`”执行；校验失败时，工作流不会发布新版本。
