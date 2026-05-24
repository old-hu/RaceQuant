# 模型训练流水线

本文档记录 RaceQuant 当前 baseline 模型的训练数据、赔率使用边界、性能指标和查询优化。

## 模型分线

当前 baseline 模型分为两条线：

| 模型线 | `odds_mode` | 说明 |
|---|---|---|
| 不依赖赔率模型 | `none` | 不使用任何赔率特征，适合在没有实时赔率或盘口缺失时生成基础判断。 |
| 赛前赔率模型 | `pre_start_latest` | 使用旧赔率快照中“该场最终赔率快照时间往前 1 分钟”之前可见的最后一笔独赢赔率。 |
| 赛果最终赔率实验 | `result_final` | 只用于复现实验，不应作为默认训练或实盘决策依据。 |

禁止默认用赛果页最终赔率训练可投注模型，因为实盘下注时拿不到最终赔率。

## 不依赖赔率训练宽表

生成脚本：

```bash
python scripts/build_no_odds_training_dataset.py --limit 20000
```

输出文件：

```text
data/features/no_odds_training_dataset.csv
data/features/no_odds_training_dataset.json
```

最近一次生成结果：

| 指标 | 数值 |
|---|---:|
| 行数 | 8970 |
| 档位覆盖率 | 100% |
| 负磅覆盖率 | 100% |
| 马体重覆盖率 | 100% |
| 距离覆盖率 | 100% |
| 场地历史胜率覆盖率 | 80.35% |
| 距离历史胜率覆盖率 | 64.88% |
| 近 3/5 场历史覆盖率 | 84.63% |

主要特征：

- 近 3 场和近 5 场表现。
- 休赛天数。
- 档位和档位分桶。
- 负磅和马体重。
- 骑师历史胜率。
- 练马师历史胜率。
- 距离适应性。
- 场地适应性。

## 训练命令

不依赖赔率模型：

```bash
python scripts/train_baseline_model.py --odds-mode none --limit 20000
```

赛前赔率模型：

```bash
python scripts/train_baseline_model.py --odds-mode pre_start_latest --limit 20000
```

生成预测：

```bash
python scripts/generate_predictions.py --artifact models/baseline/no_odds_20260524_175826.pkl --limit 20000 --write-db
```

## 最新 no-odds baseline

训练时间：2026-05-24。

模型文件：

```text
models/baseline/no_odds_20260524_175826.pkl
models/baseline/no_odds_20260524_175826.json
```

训练样本：8970 行。

| 指标 | 数值 |
|---|---:|
| win_log_loss | 0.2626 |
| win_brier | 0.0712 |
| win_auc | 0.6890 |
| place_log_loss | 0.5112 |
| place_brier | 0.1678 |
| place_auc | 0.6860 |

解释：

- 不依赖赔率模型只使用赛前可得的公开元数据和历史表现特征。
- AUC 约 0.69 说明已经有可用信号，但还不是最终投注模型。
- 后续需要和 `pre_start_latest` 模型一起做回测比较，重点看 ROI、命中率和资金曲线。

## 性能优化

特征生成瓶颈来自逐 runner 查询历史记录、骑师统计、练马师统计和赛前赔率快照。已补充 SQLite 索引。

结构化赛事库索引脚本：

```bash
python scripts/ensure_structured_indexes.py
```

旧赔率库索引脚本：

```bash
python scripts/ensure_odds_indexes.py
```

优化结果：

| 任务 | 优化前 | 优化后 |
|---|---:|---:|
| no-odds 宽表生成 | 86.7 秒 | 8.4 秒 |
| `pre_start_latest` 特征生成 | 未稳定记录 | 14.4 秒 |

关键索引：

- `idx_race_results_horse_history`
- `idx_race_results_jockey_date`
- `idx_race_results_trainer_date`
- `idx_race_metadata_distance`
- `idx_race_metadata_surface`
- `idx_legacy_horse_odds_win_lookup`
- `idx_legacy_horse_odds_final_snapshot`

## 下一步

1. 重新训练 `pre_start_latest` 赛前赔率模型。
2. 对比 `none` 和 `pre_start_latest` 两条模型线的 AUC、ROI、命中率、最大回撤。
3. 将模型版本、训练数据版本和回测版本绑定，避免前端展示混用不同版本。
