# 猫笔叨鱼盆复盘项目

目标：把公众号文章和鱼盆表格整理成可维护的实操复盘系统，而不是理论笔记。

## 入口

1. 当前操作看板：`outputs/maobidao-yupen-action-board.md`，唯一维护当前市场状态、操作倾向、验证点。
2. 历史完整报告：`outputs/maobidao-reading-report.md`，归档全部文章总结、阶段总结、历史鱼盆数据。
3. 鱼盆方法指南：`outputs/maobidao-yupen-guide.md`，沉淀鱼盆模型读法、误区修正和动作规则。
4. 链接处理记录：`outputs/maobidao-link-log.md`，作为抓取脚本的链接来源。
5. 指数排名数据：`outputs/maobidao-yupen-index-ranking.csv`，保存可对比的指数排名数据。

## 更新顺序

新增链接 -> 抓取正文和鱼盆图片 -> 更新指数排名 -> 更新操作看板 -> 归档报告 -> 如有新认知，更新鱼盆指南。

当前行情结论只允许出现在操作看板里。指南可以随文章迭代方法，但不维护当前行情判断。
