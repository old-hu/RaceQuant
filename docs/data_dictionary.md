# 数据字典

本文档记录 RaceQuant 第一版核心数据模型。字段会随着历史赔率迁移和香港赛马数据源盘点继续细化。

## races

赛事主表，一行代表一场香港赛马赛事。

| 字段 | 类型 | 可为空 | 说明 |
|---|---|---:|---|
| id | integer | 否 | 主键 |
| race_date | date | 否 | 比赛日期 |
| racecourse | string | 否 | 马场，例如 Sha Tin、Happy Valley |
| race_no | integer | 否 | 当日第几场 |
| distance_m | integer | 是 | 途程，单位米 |
| surface | string | 是 | 草地、泥地等 |
| going | string | 是 | 地况 |
| race_class | string | 是 | 班次 |
| name | string | 是 | 赛事名称 |
| post_time | datetime | 是 | 开跑时间 |

业务唯一键：`race_date + racecourse + race_no`。

## horses

马匹资料表。

| 字段 | 类型 | 可为空 | 说明 |
|---|---|---:|---|
| id | integer | 否 | 主键 |
| hkjc_id | string | 是 | 香港赛马会马匹编号 |
| name_en | string | 是 | 英文马名 |
| name_zh | string | 是 | 中文马名 |
| country | string | 是 | 出生地或来源地 |
| sex | string | 是 | 性别 |
| age | integer | 是 | 年龄 |

## jockeys

骑师资料表。

| 字段 | 类型 | 可为空 | 说明 |
|---|---|---:|---|
| id | integer | 否 | 主键 |
| name_en | string | 是 | 英文名 |
| name_zh | string | 是 | 中文名 |

## trainers

练马师资料表。

| 字段 | 类型 | 可为空 | 说明 |
|---|---|---:|---|
| id | integer | 否 | 主键 |
| name_en | string | 是 | 英文名 |
| name_zh | string | 是 | 中文名 |

## runners

参赛马表，一行代表某场赛事中的一匹参赛马。

| 字段 | 类型 | 可为空 | 说明 |
|---|---|---:|---|
| id | integer | 否 | 主键 |
| race_id | integer | 否 | 关联赛事 |
| horse_id | integer | 是 | 关联马匹 |
| jockey_id | integer | 是 | 关联骑师 |
| trainer_id | integer | 是 | 关联练马师 |
| horse_no | integer | 否 | 马号 |
| draw | integer | 是 | 档位 |
| carried_weight_lbs | integer | 是 | 负磅，单位磅 |
| declared_rating | integer | 是 | 赛前评分 |
| gear | string | 是 | 配备 |
| status | string | 否 | 状态，例如 declared、scratched |

业务唯一键：`race_id + horse_no`。

## odds_snapshots

赔率快照表，一行代表某个时间点某匹马某种投注类型的一次赔率记录。

| 字段 | 类型 | 可为空 | 说明 |
|---|---|---:|---|
| id | integer | 否 | 主键 |
| race_id | integer | 否 | 关联赛事 |
| runner_id | integer | 是 | 关联参赛马；组合投注如 fct、qin、qpl 可为空 |
| bet_type | string | 否 | 投注类型，例如 win、place |
| odds_value | string | 否 | 赔率对象；独赢为马号，组合投注为 `1-2` 形式 |
| odds | decimal | 否 | 赔率 |
| implied_probability | decimal | 是 | 市场隐含概率，通常为 `1 / odds` |
| pool_size | decimal | 是 | 彩池金额，如数据源提供 |
| source | string | 否 | 数据来源 |
| snapshot_at | datetime | 否 | 赔率快照时间 |
| legacy_id | string | 是 | 旧系统记录 ID |
| imported_at | datetime | 否 | 导入时间 |

业务唯一键：`race_id + bet_type + odds_value + snapshot_at + source`。

## results

赛果表。

| 字段 | 类型 | 可为空 | 说明 |
|---|---|---:|---|
| id | integer | 否 | 主键 |
| race_id | integer | 否 | 关联赛事 |
| runner_id | integer | 否 | 关联参赛马 |
| finishing_position | integer | 是 | 完赛名次 |
| beaten_margin | string | 是 | 落后距离 |
| win_dividend | decimal | 是 | 独赢派彩 |
| place_dividend | decimal | 是 | 位置派彩 |

## predictions

模型预测表。

| 字段 | 类型 | 可为空 | 说明 |
|---|---|---:|---|
| id | integer | 否 | 主键 |
| race_id | integer | 否 | 关联赛事 |
| runner_id | integer | 否 | 关联参赛马 |
| model_name | string | 否 | 模型名称 |
| model_version | string | 否 | 模型版本 |
| win_probability | decimal | 是 | 独赢概率 |
| place_probability | decimal | 是 | 位置概率 |
| fair_win_odds | decimal | 是 | 独赢公允赔率 |
| fair_place_odds | decimal | 是 | 位置公允赔率 |
| generated_at | datetime | 否 | 预测生成时间 |

## backtest_runs

回测任务表。

| 字段 | 类型 | 可为空 | 说明 |
|---|---|---:|---|
| id | integer | 否 | 主键 |
| name | string | 否 | 回测名称 |
| strategy_name | string | 否 | 策略名称 |
| started_at | datetime | 否 | 开始时间 |
| finished_at | datetime | 是 | 结束时间 |
| parameters_json | text | 否 | 回测参数 JSON |
| roi | decimal | 是 | 投资回报率 |
| hit_rate | decimal | 是 | 命中率 |
| max_drawdown | decimal | 是 | 最大回撤 |
| bet_count | integer | 是 | 投注次数 |
