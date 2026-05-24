# RaceQuant 任务计划

本文件是 RaceQuant 的执行计划。未完成任务使用 `TODO`，已完成任务使用 `DONE`。

## 阶段 0：项目方向与规范

- [DONE] 明确 RaceQuant 是一个香港赛马量化分析系统。
- [DONE] 确定初始技术方向：Python 后端、React 前端、shadcn/ui。
- [DONE] 创建开发规范文档：`docs/development-guidelines.md`。
- [DONE] 创建 UI 设计规范文档：`DESIGN.md`。
- [DONE] 统一 API 路由、数据库表、前端模块的命名规则。
- [DONE] 创建 `README.md`，记录本地开发和启动方式。

## 阶段 1：仓库基础结构

- [DONE] 创建标准项目目录结构。
- [DONE] 创建 `backend/`，用于 Python API 和量化服务。
- [DONE] 创建 `frontend/`，用于 React 前端应用。
- [DONE] 创建 `data/`，用于原始数据、清洗数据、特征数据和外部数据。
- [DONE] 创建 `models/`，用于模型文件、评估报告和实验记录。
- [DONE] 创建 `scripts/`，用于数据迁移、数据导入、模型训练和回测脚本。
- [DONE] 创建 `docker/`，用于后端和前端 Dockerfile。
- [DONE] 创建 `.env.example`。
- [DONE] 创建 `Makefile` 或等价的命令入口。

## 阶段 2：历史赔率变化数据迁移

- [DONE] 定位现有的历史赔率变化数据。
- [DONE] 确认数据来源格式，例如 CSV、Excel、JSON、数据库表或网页抓取文件。
- [DONE] 创建赔率迁移说明文档：`docs/odds_data_migration.md`。
- [DONE] 定义历史赔率数据的源字段到目标字段映射。
- [DONE] 明确赔率数据必需字段：比赛日期、场次、赔率对象、投注类型、赔率、时间戳、数据来源、投注额。
- [DONE] 设计目标表 `odds_snapshots`。
- [DONE] 确定缺失时间戳、重复快照、异常赔率和多来源冲突的处理规则。
- [DONE] 创建迁移脚本：`scripts/migrate_odds_history.py`。
- [DONE] 实现从现有数据源读取赔率历史数据。
- [DONE] 实现字段标准化和时间标准化。
- [DONE] 实现重复赔率快照检测。
- [DONE] 实现缺失赔率对象、无效赛事标识、异常赔率值的校验。
- [DONE] 每次导入后生成迁移报告。
- [DONE] 记录导入汇总指标：赛事数量、快照数量、跳过数量、重复数量、错误数量。
- [DONE] 确认迁移后的赔率数据可以支持按历史投注时间点进行分析和回测。
- [DONE] 完整迁移旧库 `horse_odds` 中 `win`、`fct`、`qin`、`qpl` 四类赔率到本地 SQLite 暂存库。

## 阶段 3：后端基础

- [DONE] 初始化 Python 后端项目。
- [DONE] 添加 FastAPI。
- [DONE] 添加 SQLAlchemy。
- [DONE] 添加 Alembic。
- [DONE] 添加 PostgreSQL 数据库配置。
- [DONE] 添加 pytest。
- [DONE] 创建后端入口文件：`backend/app/main.py`。
- [DONE] 创建配置模块：`backend/app/core/config.py`。
- [DONE] 创建数据库会话模块：`backend/app/db/session.py`。
- [DONE] 在 `backend/app/api/v1` 下创建 API 版本目录。
- [DONE] 添加基础健康检查接口。

## 阶段 4：数据模型

- [DONE] 定义 `Race` 模型。
- [DONE] 定义 `Runner` 模型。
- [DONE] 定义 `Horse` 模型。
- [DONE] 定义 `Jockey` 模型。
- [DONE] 定义 `Trainer` 模型。
- [DONE] 定义 `OddsSnapshot` 模型。
- [DONE] 定义 `Result` 模型。
- [DONE] 定义 `Prediction` 模型。
- [DONE] 定义 `BacktestRun` 模型。
- [DONE] 创建第一版 Alembic 数据库迁移。
- [DONE] 创建数据字典文档：`docs/data_dictionary.md`。
- [DONE] 记录所有模型字段、字段类型、是否可为空、数据来源和业务假设。

## 阶段 5：后端 API

- [DONE] 创建赛事列表 API。
- [DONE] 创建赛事详情 API。
- [DONE] 创建单场赛事参赛马列表 API。
- [DONE] 创建马匹资料 API。
- [DONE] 创建马匹历史成绩 API。
- [DONE] 创建赔率快照导入 API 或内部服务。
- [DONE] 创建赔率变化查询 API。
- [DONE] 创建模型预测查询 API。
- [DONE] 创建回测任务 API。
- [DONE] 创建回测结果 API。

## 阶段 6：量化核心

- [DONE] 在 `backend/app/quant/features` 下创建特征工程模块。
- [DONE] 实现近 3 场和近 5 场表现特征。
- [DONE] 实现距离适应性特征。
- [DONE] 实现场地和地况适应性特征。
- [DONE] 实现档位偏差特征。
- [DONE] 实现骑师和练马师统计特征。
- [DONE] 实现升降班特征。
- [DONE] 实现负磅特征。
- [DONE] 实现休赛天数特征。
- [DONE] 实现赔率隐含概率特征。
- [DONE] 建立第一版胜率预测模型。
- [DONE] 建立第一版位置概率预测模型。
- [DONE] 生成不依赖赔率的训练宽表：`data/features/no_odds_training_dataset.csv`。
- [DONE] 使用全量公开元数据重训不依赖赔率的 baseline 模型。
- [DONE] 为结构化赛事库和旧赔率库添加特征生成查询索引。
- [DONE] 添加概率校准。
- [DONE] 根据模型概率计算公允赔率。
- [DONE] 实现 value betting 规则：模型概率、市场隐含概率和安全边际比较。

## 阶段 7：回测系统

- [DONE] 创建回测引擎。
- [DONE] 支持独赢投注回测。
- [DONE] 支持位置投注回测。
- [DONE] 支持固定注码策略。
- [DONE] 支持分数 Kelly 策略。
- [DONE] 计算 ROI。
- [DONE] 计算命中率。
- [DONE] 计算最大回撤。
- [DONE] 计算盈亏因子。
- [DONE] 计算平均赔率。
- [DONE] 计算投注次数。
- [DONE] 生成资金曲线。
- [DONE] 创建投注规则文档：`docs/betting_rules.md`。
- [DONE] 在策略结果可信之前，记录所有回测假设。

## 阶段 8：前端基础

- [DONE] 初始化 React + Vite + TypeScript 前端项目。
- [DONE] 安装 Tailwind CSS。
- [DONE] 安装并配置 shadcn/ui。
- [DONE] 将 `DESIGN.md` 中的设计标准转成 CSS 变量和 Tailwind 主题 token。
- [DONE] 创建黑色画布风格的全局布局。
- [DONE] 创建基础按钮组件。
- [DONE] 创建卡片和面板组件。
- [DONE] 创建赛事和赔率数据表格组件。
- [TODO] 创建图表封装组件。
- [TODO] 创建类型化 API 客户端。

## 阶段 9：前端 MVP 页面

- [DONE] 创建仪表盘页面。
- [DONE] 展示今日赛事或样例赛事列表。
- [DONE] 展示模型状态摘要。
- [DONE] 展示回测摘要卡片。
- [DONE] 创建赛事详情页面。
- [DONE] 展示参赛马、档位、骑师、练马师、负磅和赔率。
- [DONE] 创建历史赔率变化页面。
- [DONE] 展示赔率变化表格。
- [DONE] 按马匹和投注类型展示赔率变化图表。
- [DONE] 创建预测看板页面。
- [DONE] 展示胜率、位置概率、公允赔率、市场赔率和 edge。
- [DONE] 创建回测页面。
- [DONE] 展示 ROI、命中率、最大回撤、资金曲线和投注明细表。

## 阶段 10：测试与质量

- [DONE] 添加后端单元测试，覆盖特征计算。
- [TODO] 添加后端单元测试，覆盖赔率隐含概率。
- [TODO] 添加后端单元测试，覆盖 value betting 规则。
- [DONE] 添加后端单元测试，覆盖回测指标。
- [DONE] 添加核心接口 API 测试。
- [TODO] 添加前端组件冒烟测试。
- [DONE] 添加数据迁移和数据导入校验。
- [DONE] 添加重复赛事和重复 runner 检查。
- [TODO] 添加重复赔率快照检查。
- [TODO] 添加 Docker Compose，用于本地启动后端、前端和数据库。
- [TODO] 添加 lint 和 format 命令。

## 阶段 12：公开数据局部爬取

- [DONE] 创建排位 / 参赛马局部爬取脚本。
- [DONE] 创建历史赛果局部爬取脚本。
- [DONE] 创建马匹历史表现局部爬取脚本。
- [DONE] 创建统一 HKJC 爬虫客户端。
- [DONE] 保存原始 HTML 到 `data/raw/hkjc`。
- [DONE] 保存通用解析 JSON 到 `data/raw/hkjc`。
- [DONE] 创建定时更新脚本。
- [DONE] 支持只运行一次的局部更新模式。
- [DONE] 编写数据爬取计划文档：`docs/scraping_plan.md`。
- [DONE] 验证排位、赛果、马匹历史三个入口可以局部爬取。
- [DONE] 创建赛程 / 赛日总览局部爬取脚本。
- [DONE] 创建完整排位入口局部爬取脚本。
- [DONE] 创建派彩结果局部爬取脚本。
- [DONE] 创建赛事临场变更局部爬取脚本。
- [DONE] 将赛程、完整排位、派彩结果、临场变更接入定时更新脚本。
- [DONE] 在前端数据板块展示赛程、完整排位、派彩结果、临场变更分类。
- [DONE] 将定时器升级为 `local-sample`、`daily-update`、`backfill-history` 三种模式。
- [DONE] 支持按日期范围、马场列表和场次数量分批回填公开数据。
- [DONE] 从旧赔率库赛日生成历史全量爬取队列。
- [DONE] 创建每 5 秒领取一个未完成赛日的历史全量爬取工人。
- [DONE] 已爬取赛日按 `done` 状态跳过，不重复爬取。
- [DONE] 将历史赛果和派彩结果解析为强结构化数据并落入本地 SQLite。
- [DONE] 将结构化赛果和派彩导出到前端页面展示。
- [DONE] 将排位页面解析为强结构化参赛马字段。
- [DONE] 将赛果页面解析为强结构化赛果字段。
- [DONE] 将马匹历史页面解析为强结构化历史表现字段。
- [DONE] 将派彩结果页面解析为强结构化派彩字段并写入数据库。
- [DONE] 将赛程 / 赛日总览解析为强结构化赛事字段并写入数据库。
- [DONE] 将临场变更解析为强结构化变更事件并写入数据库。
- [TODO] 将强结构化爬取结果写入正式数据库。

## 阶段 11：第一轮执行冲刺

- [DONE] 搭建真实项目目录结构。
- [DONE] 初始化后端骨架。
- [DONE] 初始化前端骨架。
- [DONE] 创建第一版数据库模型。
- [DONE] 准备样例数据。
- [DONE] 迁移一小部分历史赔率变化样例数据。
- [DONE] 完整迁移指定类型的历史赔率变化数据。
- [DONE] 构建赔率变化 API。
- [DONE] 构建赔率变化前端页面。
- [DONE] 验证系统可以端到端展示迁移后的历史赔率变化数据。
