# 历史赔率变化数据迁移说明

历史赔率变化数据是 RaceQuant 的核心资产。迁移目标不是只保存最终赔率，而是尽可能保留完整时间序列，用于研究早盘异动、临场资金流、赔率压缩速度和不同投注时间点的回测表现。

## 目标表

历史赔率迁移到 `odds_snapshots`。

核心唯一键：

```text
race_id + bet_type + odds_value + snapshot_at + source
```

说明：组合投注如 `fct`、`qin`、`qpl` 必须保留 `odds_value`，例如 `1-2`。这类记录不能只用单一 `runner_id` 表达。

## 推荐源字段

| 源字段 | 目标字段 | 必需 | 说明 |
|---|---|---:|---|
| 比赛日期 | race_date | 是 | 用于匹配赛事 |
| 马场 | racecourse | 是 | 例如 Sha Tin、Happy Valley |
| 场次 | race_no | 是 | 当日第几场 |
| 马号或组合对象 | odds_value | 是 | 独赢为马号，组合投注为 `1-2` 形式 |
| 马名 | horse_name | 否 | 辅助校验 |
| 投注类型 | bet_type | 是 | win、place 等 |
| 赔率 | odds | 是 | 必须大于 1 |
| 时间戳 | snapshot_at | 是 | 快照时间 |
| 数据来源 | source | 否 | 缺省为 unknown |
| 彩池金额 | pool_size | 否 | 如果可得则保留 |

## 清洗规则

- 赔率为空、非数字或小于等于 1 的记录标记为错误。
- 缺失赛事日期、马场、场次、马号、投注类型、时间戳的记录标记为错误。
- 同一 `race_date + racecourse + race_no + horse_no + bet_type + snapshot_at + source` 重复时，只保留一条。
- 时间统一解析为带时区语义的时间；香港数据默认按 Asia/Hong_Kong 理解，入库前再决定是否转 UTC。
- 马名只作为辅助校验，不作为主匹配键。

## 导入报告

每次迁移必须输出：

- 读取记录数
- 有效记录数
- 错误记录数
- 重复记录数
- 赛事数量
- 快照数量
- 数据来源

## 第一版脚本

迁移入口：

```bash
python scripts/migrate_odds_history.py --input path/to/odds.csv --report reports/odds_migration_report.json
```

第一版脚本先完成文件读取、字段标准化、校验、去重和报告生成。数据库写入会在目标表和样例数据确认后接入。

旧 MySQL 迁移入口：

```bash
python scripts/migrate_legacy_horse_odds.py --output data/processed/legacy_horse_odds.sqlite
```

旧库脚本通过环境变量读取连接信息，避免把密码写入代码。
