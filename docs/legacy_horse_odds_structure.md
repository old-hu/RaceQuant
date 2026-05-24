# 旧库 horse_odds 表结构分析

分析日期：2026-05-23

旧库：`digit-ai`

旧表：`horse_odds`

## 总览

- 估算行数：约 25,486,153 行
- 日期范围：2026-01-28 至 2026-05-20
- 本次迁移范围：仅迁移 `odds_type IN ('win', 'fct', 'qin', 'qpl')`
- 旧表只有 `race_date + race_no + odds_type` 复合索引，适合按日期分批迁移，不适合一次性全表扫描。

## 字段

| 字段 | 类型 | 可为空 | 说明 |
|---|---|---:|---|
| id | varchar(36) | 否 | 旧系统主键 |
| create_by | varchar(50) | 是 | 创建人 |
| create_time | datetime | 是 | 创建日期 |
| update_by | varchar(50) | 是 | 更新人 |
| update_time | datetime | 是 | 更新日期 |
| race_date | date | 是 | 开跑日期 |
| race_no | int | 是 | 开跑场次 |
| odds_type | varchar(100) | 是 | 赔率类型 |
| odds_value | varchar(100) | 是 | 赔率对象 |
| odds | double | 是 | 赔率 |
| remark | varchar(200) | 是 | 备注 |
| bet_amount | double | 是 | 投注额或彩池相关金额 |
| sys_org_code | varchar(64) | 是 | 组织编码 |

## 索引

| 索引 | 字段 |
|---|---|
| PRIMARY | id |
| idx_horse_odds_race_date_race_no | race_date, race_no, odds_type |

## 赔率类型样例

| odds_type | remark | odds_value 样例 | 说明 |
|---|---|---|---|
| win | 独赢 | `1` | 单匹马独赢赔率 |
| fct | 二重彩 | `1-2` | 顺序组合投注 |
| qin | 连赢 | `1-6` | 两匹马组合投注 |
| qpl | 位置Q | `1-13` | 两匹马位置组合投注 |

## 迁移策略

- 按 `race_date` 分批读取，利用旧表复合索引的第一列。
- 只读取 `win`、`fct`、`qin`、`qpl`。
- `snapshot_at` 使用 `COALESCE(update_time, create_time)`。
- `odds_value` 原样保留，用于支持组合投注。
- 暂存目标为本地 SQLite：`data/processed/legacy_horse_odds.sqlite`。
- 后续 PostgreSQL 服务就绪后，再从 SQLite 暂存库写入正式表。

