# Project Agent Instructions

本文件是本项目的系统执行入口。处理任何项目任务前，先按顺序读取：

1. `docs/project-context.md`：长期有效的项目目标、边界和文件职责。
2. `docs/action-board.md`：当前市场状态和最新操作倾向。
3. 根据任务读取 `docs/product-flow.md`、`docs/reading-report.md`、`docs/yupen-guide.md` 或 `data/`。

## 核心规则

- 项目只围绕“猫笔叨文章 + 鱼盆表格 -> 趋势买入方向雷达”迭代。
- 当前唯一专精模型是：趋势买入 = 鱼盆前排 + 站上20日线 + 板块强于大盘。
- 三条件和方向分组的数值口径只以 `docs/product-flow.md` 为准，不在其他文件另设阈值。
- 必须区分文章发布日期、指数鱼盆数据日和板块鱼盆数据日；方向判断以各自鱼盆数据日为准。
- 鱼盆表格图片是排名、偏离率、量比和状态变化的原始证据，不能只根据正文推断表格数据。
- 当前行情结论只能维护在 `docs/action-board.md`，不能复制到项目上下文或方法指南。
- `docs/reading-report.md` 追加历史，`docs/yupen-guide.md` 只在方法认知发生变化时更新。
- 数据不可读取、图片缺失或文章抓取失败时，明确报告缺口，不补造结论。
- Web 是结构化数据的只读展示层，不是项目事实源；只展示已通过项目校验的快照。
- 当前产品不做实时行情、自动交易、泛投资资讯或单只股票操作建议。

## 新文章处理

严格按照 `docs/product-flow.md` 执行。最低完成标准：

1. 正文抓取成功；如果文章含鱼盆表，再抓取鱼盆图片。
2. 有鱼盆表时，分别核对指数表和板块表的数据日；两张表可能不是同一天。
3. 更新链接记录和结构化读表数据；文章明确支持或反对具体方向时，更新文章方向态度表。
4. 依次运行 `python3 scripts/build_index_ranking.py`、`python3 scripts/build_direction_signals.py` 和 `python3 scripts/build_signal_lifecycle.py`，再依据自动信号更新当前操作看板。
5. 向历史报告追加文章总结及前后联系，并用信号生命周期复盘跨日有效性。
6. 只有出现新规则或旧规则被证伪时，才更新鱼盆指南。
7. 运行 `python3 scripts/validate_project.py`，校验 JSON、图片记录、结构化读表数据、派生数据、最新数据日和文档口径一致。
8. 需要更新 Web 时运行 `python3 scripts/build_web_snapshot.py`；校验不通过时不得生成新快照。
