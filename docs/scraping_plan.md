# 数据爬取计划

本文档记录 RaceQuant 第一版局部爬取策略。当前只做小范围、可重复、可定时的公开数据采集，不做全量高频抓取。

## 第一版爬取范围

### 1. 排位 / 参赛马页面

脚本：

```bash
python scripts/scrape_race_cards.py --race-date 2026-05-20 --racecourse HV --race-no 1
```

目标：

- 赛日
- 马场
- 场次
- 参赛马列表
- 马号
- 马名
- 档位
- 骑师
- 练马师
- 负磅
- 评分
- 配备

### 2. 历史赛果页面

脚本：

```bash
python scripts/scrape_results.py --race-date 2026-05-20 --racecourse HV --race-no 1
```

目标：

- 完赛名次
- 马号
- 马名
- 骑师
- 练马师
- 完成时间
- 落后距离
- 派彩
- 赛后赔率

### 3. 马匹历史表现页面

脚本：

```bash
python scripts/scrape_horse_history.py --horse-no E123
```

目标：

- 马匹基础信息
- 历史出赛记录
- 途程
- 场地
- 地况
- 负磅
- 档位
- 名次
- 完成时间
- 马匹体重

### 4. 赛程 / 赛日总览页面

脚本：

```bash
python scripts/scrape_race_meeting.py --race-date 2026-05-20 --racecourse HV
```

目标：

- 赛日
- 马场
- 场次数量
- 开跑时间
- 赛事名称
- 途程
- 场地类型

### 5. 完整排位入口页面

脚本：

```bash
python scripts/scrape_entries.py --race-date 2026-05-20 --racecourse HV
```

目标：

- 全日排位入口
- 参赛马入口链接
- 骑师 / 练马师入口
- 后续用于补充强结构化参赛马字段

### 6. 派彩结果页面

脚本：

```bash
python scripts/scrape_dividends.py --race-date 2026-05-20
```

目标：

- 场次
- 彩池
- 中奖组合
- 派彩金额
- 用于回测结算和不同投注类型收益核验

### 7. 临场变更页面

脚本：

```bash
python scripts/scrape_changes.py --race-date 2026-05-20
```

目标：

- 退出马
- 骑师更换
- 负磅变更
- 配备变更
- 场地状态变更

## 输出位置

所有原始页面和解析 JSON 保存在：

```text
data/raw/hkjc/
```

每次爬取会保存：

- 原始 HTML
- 通用表格解析 JSON
- `latest.json` 元信息

说明：`data/raw` 已被 `.gitignore` 忽略，默认不提交原始数据。

## 定时更新

只运行一次：

```bash
python scripts/schedule_scrapers.py --once --mode local-sample --race-date 2026-05-20 --racecourse HV --race-nos 1,2 --horse-nos E123,E456
```

每 60 分钟定时更新：

```bash
python scripts/schedule_scrapers.py --mode local-sample --race-date 2026-05-20 --racecourse HV --race-nos 1,2 --horse-nos E123,E456 --interval-minutes 60
```

定时器使用 APScheduler，常驻运行时会立即执行一次，然后按间隔重复。

每日更新指定赛日：

```bash
python scripts/schedule_scrapers.py --mode daily-update --race-date 2026-05-20 --racecourses HV,ST --max-race-no 12 --interval-minutes 60
```

按日期范围分批回填历史：

```bash
python scripts/schedule_scrapers.py --once --mode backfill-history --start-date 2026-05-01 --end-date 2026-05-20 --racecourses HV,ST --max-race-no 12
```

模式说明：

- `local-sample`：小范围验证，必须传 `--race-date`，可指定单个马场、场次和马匹。
- `daily-update`：每日更新，按指定赛日或当天日期，同时尝试 `HV,ST` 两个马场和 1 到 `--max-race-no` 的场次。
- `backfill-history`：历史回填，按日期范围、马场列表、场次范围生成批量任务。
- 目前回填会保守地逐个日期 / 马场 / 场次尝试；无赛事日期也会写入报告，后续会在“赛程发现”稳定后过滤掉无赛事日期。

## 当前限制

- 第一版先保存原始 HTML 和通用表格 JSON，不直接入正式数据库。
- 页面字段解析会在样本稳定后再做强结构化映射。
- 赔率变化已有旧库迁移结果，实时赔率增量爬取后续单独设计。
- 爬取频率必须保守，避免对公开网站造成压力。
