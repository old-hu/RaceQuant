# 旧库 horse_odds 迁移结果

执行日期：2026-05-23

## 迁移范围

旧库：`digit-ai`

旧表：`horse_odds`

迁移条件：

```sql
odds_type IN ('win', 'fct', 'qin', 'qpl')
```

未迁移其他赔率类型。

## 目标位置

本地暂存 SQLite：

```text
data/processed/legacy_horse_odds.sqlite
```

迁移报告：

```text
data/reports/legacy_horse_odds_migration_report.json
```

说明：`data/processed` 和 `data/reports` 下的数据产物已被 `.gitignore` 忽略，不进入 Git。

## 迁移结果

| 指标 | 数值 |
|---|---:|
| 处理比赛日期数 | 30 |
| 插入总行数 | 20,757,621 |
| 重复跳过行数 | 0 |
| SQLite 文件大小 | 约 5.19GB |
| 最早比赛日期 | 2026-02-01 |
| 最晚比赛日期 | 2026-05-20 |

## 按 odds_type 分布

| odds_type | 行数 | 说明 |
|---|---:|---|
| win | 817,725 | 独赢 |
| fct | 9,995,954 | 二重彩 |
| qin | 4,976,363 | 连赢 |
| qpl | 4,967,579 | 位置Q |

## 暂存表结构

表名：`legacy_horse_odds`

| 字段 | 说明 |
|---|---|
| legacy_id | 旧表 `id` |
| race_date | 比赛日期 |
| race_no | 场次 |
| odds_type | 赔率类型 |
| odds_value | 赔率对象，独赢为马号，组合投注为 `1-2` 形式 |
| odds | 赔率 |
| implied_probability | 简单隐含概率，`1 / odds` |
| bet_amount | 旧表投注额字段 |
| remark | 旧表备注 |
| snapshot_at | `COALESCE(update_time, create_time)` |
| create_time | 旧表创建时间 |
| update_time | 旧表更新时间 |
| source | 固定为 `digit-ai.horse_odds` |

## 后续处理

- PostgreSQL 服务就绪后，再从 SQLite 暂存库写入正式业务表。
- `win` 可以映射到单匹参赛马。
- `fct`、`qin`、`qpl` 是组合投注，必须保留 `odds_value`，不能强行映射到单一 `runner_id`。
- 后续需要结合赛事基础数据补齐马场、参赛马、骑师、练马师等实体关系。

