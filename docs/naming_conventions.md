# 命名规则

## 后端

- API 路由使用复数资源名，例如 `/races`、`/horses`、`/odds-snapshots`。
- Python 模块使用 snake_case。
- Pydantic schema 使用 PascalCase，并按用途添加后缀，例如 `RaceRead`、`RaceCreate`。
- 服务类和量化模块保持业务含义清晰，例如 `odds_migration.py`、`feature_engineering.py`。

## 数据库

- 表名使用 snake_case 复数形式，例如 `races`、`runners`、`odds_snapshots`。
- 主键统一使用 `id`。
- 外键使用 `{entity}_id`，例如 `race_id`、`horse_id`。
- 时间字段使用 UTC 语义，字段名优先使用 `*_at` 或明确业务名，例如 `snapshot_at`。

## 前端

- React 组件使用 PascalCase。
- 页面和 feature 目录使用 kebab-case 或小写复数目录。
- API 类型与后端 schema 对齐，保留业务名，例如 `Race`, `Runner`, `OddsSnapshot`。

