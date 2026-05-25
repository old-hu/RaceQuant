# RaceQuant 任务计划

本文档记录 RaceQuant 当前的建设目标、已完成能力和剩余工作。状态使用 `DONE` / `TODO` / `WAITING`。

## 系统最终目的

RaceQuant 是一个面向香港赛马的量化分析系统，目标是把官方赛程、排位、赛果、派彩、马匹历史、赔率历史和模型结果串成可重复的数据流水线，用于：

- 构建尽可能完整、可审计的历史赛马数据库。
- 训练不依赖赛后赔率泄漏的赛前预测模型。
- 输出胜率、位置概率、公允赔率、市场 implied probability、edge 和投注候选。
- 支持带交易成本、滑点、限额和投注规则的回测。
- 通过前端看板展示数据质量、模型版本、预测结果、赔率变化和回测结果。

## 当前数据状态

- [DONE] 官方赛日发现已完成，覆盖 `1996-01-01` 至 `2026-05-24`。
- [WAITING] 官方历史赛果和派彩回填仍在 worker 中运行，训练任务需等待 `scrape_jobs` 中 `pending` / `running` / `failed` 全部归零。
- [DONE] 已把无官方赛果的历史任务标记为 `skipped_no_official_result`，避免 worker 卡在不存在的赛日。
- [DONE] 已接入马匹历史回填，worker 会按发现到的参赛马匹补齐 `horse_profiles` 和 `horse_form_records`。
- [DONE] 已增加 `scripts/train_when_ready.py`，数据完整后自动执行 raw rebuild、no-odds 训练、预测生成、ranking 评估和前端 JSON 导出。

## 数据流水线

- [DONE] 官方赛日发现脚本：`scripts/discover_official_race_days.py`。
- [DONE] 官方历史 worker：`scripts/run_historical_scrape_worker.py`。
- [DONE] 马匹历史批量回填：`scripts/scrape_discovered_horse_histories.py`。
- [DONE] 本地结构化 SQLite 构建：`scripts/build_local_data.py`。
- [DONE] 正式库同步脚本：`scripts/sync_structured_sqlite_to_formal_db.py`。
- [DONE] 数据审计脚本：`scripts/audit_structured_data.py`。
- [DONE] 前端数据导出脚本已接入结构化 races、entries、results、dividends、horse profiles、horse form records、scrape summary 和 scrape jobs。

## 模型与回测

- [DONE] 生成不依赖赔率的训练宽表：`data/features/no_odds_training_dataset.csv`。
- [DONE] baseline 模型支持 `odds_mode`、训练数据版本、特征版本和数据构建版本记录。
- [DONE] 特征版本升级到 `runner_features_v2_horse_form`，加入官方马匹历史表现特征。
- [DONE] 增加 no-odds ranking 评估：`scripts/evaluate_no_odds_ranking.py`。
- [DONE] 默认研究口径禁止使用赛果最终赔率作为实盘赛前特征。
- [DONE] 回测支持交易成本、滑点、注额上限、赔率成交失败和盘口停牌假设。
- [WAITING] 等官方历史 worker 完成后，自动重训 no-odds baseline 并重新导出预测、ranking 评估和前端 JSON。

## 前端

- [DONE] 仪表盘、数据源、采集任务、赔率、模型和回测页面已可展示当前导出数据。
- [DONE] 数据完整性面板显示官方回填进度、活跃任务、跳过赛日、马匹历史覆盖和赔率库状态。
- [DONE] 前端文案已去除主要示例数据表述，页面以真实导出 JSON 为主。
- [DONE] 增加类型化 API 客户端。
- [DONE] 增加图表封装组件。
- [DONE] 增加前端 smoke test，覆盖 6 个主要路由。

## 开发、交付与质量

- [DONE] README 已重写，记录项目目标、本地启动、数据流水线、训练和 Docker Compose。
- [DONE] 增加 `docker-compose.yml`，以及 backend / frontend Dockerfile。
- [DONE] 增加 `.dockerignore`。
- [DONE] 增加统一质量检查脚本：`scripts/quality_check.py`。
- [DONE] Makefile 增加 `lint`、`format`、`build-frontend`、`smoke-frontend`、`quality`、`docker-up`、`docker-down` 和 `train-when-ready`。
- [DONE] 后端测试、前端 lint、前端 build、前端 smoke 已纳入一键质量检查。
- [DONE] 增加数据训练 readiness 报告：`scripts/audit_data_readiness.py`。
- [DONE] 增加采集任务诊断报告：`scripts/diagnose_scrape_jobs.py`。
- [DONE] 增强 no-odds ranking 评估，支持分年份、赛道、距离段和概率校准分箱。

## 当前剩余任务

- [WAITING] 等官方历史数据 worker 完成全部真实官方赛日回填。
- [WAITING] 数据完整后由定时器或手动运行 `scripts/train_when_ready.py` 触发重训和导出。
- [TODO] 完整历史赔率库仍需后续恢复或重新迁移，尤其是 `win`、`fct`、`qin`、`qpl` 全量赔率快照。该项已按用户要求暂时后置，不阻塞 no-odds 模型训练。

## 当前验证结果

- [DONE] `python scripts/quality_check.py` 通过。
- [DONE] 后端测试：31 passed。
- [DONE] 前端 lint：通过。
- [DONE] 前端生产构建：通过。
- [DONE] 前端 smoke：6 个主要路由通过。
- [DONE] `python scripts/audit_data_readiness.py` 可生成 `data/reports/data_readiness_latest.json`。
- [DONE] `python scripts/diagnose_scrape_jobs.py` 可生成 `data/reports/scrape_job_diagnostics_latest.json`。
- [DONE] `python scripts/evaluate_no_odds_ranking.py --artifact-json models/baseline/no_odds_20260525_004102.json` 可生成增强版 ranking 报告。
- [WAITING] Docker Compose 文件已添加，但当前机器未安装 Docker CLI，因此未在本机执行 `docker compose` 验证。
