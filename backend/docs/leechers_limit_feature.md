# 下载用户数限制功能说明

## 功能概述

在筛选规则中新增了 **下载用户数（Leechers）限制** 功能，可以设置最小和最大下载用户数，用于筛选符合条件的种子。

## 使用场景

### 1. 避免冷门种子
设置 **最小下载用户数**，跳过下载人数太少的种子，确保下载速度：
```json
{
  "min_leechers": 5
}
```

### 2. 避免热门种子
设置 **最大下载用户数**，跳过下载人数太多的种子，避免竞争激烈：
```json
{
  "max_leechers": 50
}
```

### 3. 范围筛选
同时设置最小和最大值，筛选下载用户数在特定范围内的种子：
```json
{
  "min_leechers": 5,
  "max_leechers": 30
}
```

## API 使用示例

### 创建带下载用户数限制的规则

```http
POST /api/rules/

{
  "account_id": 1,
  "name": "热度适中的免费种子",
  "is_enabled": true,
  "mode": "normal",
  "free_only": true,
  "min_size": 5.0,
  "max_size": 50.0,
  "min_leechers": 5,      // 最少 5 人下载
  "max_leechers": 30,     // 最多 30 人下载
  "downloader_id": 1,
  "save_path": "/downloads/optimal",
  "tags": ["auto", "optimal"]
}
```

### 更新现有规则

```http
PUT /api/rules/{rule_id}

{
  // ... 其他字段
  "min_leechers": 10,
  "max_leechers": 50
}
```

## 数据库字段

### filter_rules 表新增字段

| 字段名 | 类型 | 说明 | 可空 |
|-------|------|------|------|
| `min_leechers` | INTEGER | 最小下载用户数 | 是 |
| `max_leechers` | INTEGER | 最大下载用户数 | 是 |

## 匹配逻辑

在 `match_torrent()` 函数中，下载用户数检查逻辑如下：

```python
# 下载用户数检查
leechers = torrent.get("leechers", 0)
if rule.min_leechers and leechers < rule.min_leechers:
    return False  # 下载用户数太少
if rule.max_leechers and leechers > rule.max_leechers:
    return False  # 下载用户数太多
```

## 数据来源

下载用户数来自 M-Team API 返回的种子信息：

```json
{
  "status": {
    "seeders": 10,
    "leechers": 15,    // 下载用户数
    "timesCompleted": 50
  }
}
```

## 注意事项

1. **可选配置**：`min_leechers` 和 `max_leechers` 都是可选字段，不设置则不限制
2. **默认值**：如果种子数据中没有 leechers 信息，默认为 0
3. **实时数据**：下载用户数是实时变化的，规则匹配时使用的是当时的数据
4. **与其他条件配合**：下载用户数限制可以与做种数、大小、分类等其他筛选条件配合使用

## 数据库迁移

数据库迁移已集成到 `database.py` 的 `run_migrations()` 函数中，启动后端服务时会自动执行：

```python
migrations = [
    ("filter_rules", "min_leechers", "INTEGER"),
    ("filter_rules", "max_leechers", "INTEGER"),
]
```

重启后端服务即可自动应用迁移，无需手动操作。

## 典型应用示例

### 示例 1：仅下载有人气但不拥挤的种子
```json
{
  "name": "最佳性价比种子",
  "free_only": true,
  "min_seeders": 10,      // 至少 10 个做种
  "min_leechers": 3,      // 至少 3 人在下载（有人气）
  "max_leechers": 20,     // 最多 20 人下载（不拥挤）
  "min_size": 10.0,
  "max_size": 100.0
}
```

### 示例 2：冷门收藏监控
```json
{
  "name": "冷门收藏自动下载",
  "rule_type": "favorite",
  "monitor_favorites": true,
  "free_only": true,
  "max_leechers": 5,      // 下载人数不超过 5（冷门）
  "downloader_id": 1
}
```

### 示例 3：热门种子专属
```json
{
  "name": "热门种子快速下载",
  "free_only": true,
  "min_leechers": 50,     // 至少 50 人下载（热门）
  "min_seeders": 100,     // 至少 100 个做种（高速）
  "downloader_id": 1
}
```
