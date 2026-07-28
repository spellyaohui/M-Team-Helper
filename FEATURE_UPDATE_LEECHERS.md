# 功能更新：下载用户数限制

## 更新概述

在筛选规则中新增 **下载用户数（Leechers）限制** 功能，允许用户设置最小和最大下载用户数来筛选种子。

## 更新时间

2026-01-31

## 修改文件列表

### 1. 数据库模型 (models.py)
- **位置**：`mteam-helper/backend/models.py`
- **修改内容**：在 `FilterRule` 模型中添加了两个新字段：
  ```python
  min_leechers = Column(Integer, nullable=True)  # 最小下载用户数
  max_leechers = Column(Integer, nullable=True)  # 最大下载用户数
  ```

### 2. API 接口模型 (routers/rules.py)
- **位置**：`mteam-helper/backend/routers/rules.py`
- **修改内容**：
  - 在 `RuleCreate` 类中添加字段：
    ```python
    min_leechers: Optional[int] = None
    max_leechers: Optional[int] = None
    ```
  - 在 `RuleResponse` 类中添加字段：
    ```python
    min_leechers: Optional[int]
    max_leechers: Optional[int]
    ```
  - 在创建规则函数中添加字段处理
  - 在 `match_torrent()` 函数中添加下载用户数匹配逻辑

### 3. 数据库迁移 (database.py)
- **位置**：`mteam-helper/backend/database.py`
- **修改内容**：在迁移列表中添加新字段：
  ```python
  ("filter_rules", "min_leechers", "INTEGER"),
  ("filter_rules", "max_leechers", "INTEGER"),
  ```

## 功能说明

### 使用场景

1. **避免冷门种子**：设置 `min_leechers` 确保种子有足够的下载人气
2. **避免过热种子**：设置 `max_leechers` 避免竞争过于激烈的种子
3. **精确筛选**：结合做种数、大小等条件，筛选最优质的种子

### API 使用示例

```json
POST /api/rules/
{
  "account_id": 1,
  "name": "热度适中的免费种子",
  "is_enabled": true,
  "free_only": true,
  "min_leechers": 5,
  "max_leechers": 30,
  "downloader_id": 1
}
```

### 匹配逻辑

在种子匹配时，会检查下载用户数是否在设置的范围内：
- 如果 `min_leechers` 设置，种子的下载用户数必须 ≥ 此值
- 如果 `max_leechers` 设置，种子的下载用户数必须 ≤ 此值
- 两个值都是可选的，不设置则不限制

## 数据来源

下载用户数来自 M-Team API 的种子状态信息，已在 `parse_torrent()` 函数中正确解析：
```python
"leechers": int(status.get("leechers", 0))
```

## 部署说明

### 自动迁移
数据库迁移会在后端服务启动时自动执行，无需手动操作。

### 启动步骤
1. 停止后端服务（如果正在运行）
2. 拉取最新代码
3. 启动后端服务：
   ```bash
   cd mteam-helper/backend
   python main.py
   ```
4. 服务启动时会自动添加新字段到数据库

### 验证迁移
启动后端时，在日志中应该看到：
```
[Migration] 已添加列: filter_rules.min_leechers
[Migration] 已添加列: filter_rules.max_leechers
```

## 兼容性说明

### 向后兼容
- 新字段为可选字段（nullable=True），不会影响现有规则
- 现有规则会自动获得这两个字段（值为 NULL）
- 不设置这些字段时，行为与之前完全一致

### 前端更新
前端需要在规则编辑界面添加两个输入框：
- 最小下载用户数（min_leechers）
- 最大下载用户数（max_leechers）

建议使用数字输入框，并提示用户：
- 留空表示不限制
- 仅设置最小值：下载人数 ≥ 此值
- 仅设置最大值：下载人数 ≤ 此值
- 同时设置：下载人数在此范围内

## 测试建议

### 测试用例

1. **创建规则**：测试创建包含下载用户数限制的规则
2. **更新规则**：测试更新现有规则添加下载用户数限制
3. **匹配测试**：测试种子是否正确按下载用户数筛选
4. **边界测试**：测试边界值（0、NULL、负数等）

### 手动测试步骤

1. 创建一个规则，设置 `min_leechers: 5, max_leechers: 30`
2. 观察日志，确认只有下载用户数在 5-30 之间的种子被匹配
3. 修改规则，仅设置 `min_leechers: 10`
4. 确认所有下载用户数 ≥ 10 的种子被匹配

## 相关文档

详细使用说明请参考：
`mteam-helper/backend/docs/leechers_limit_feature.md`

## 注意事项

1. 下载用户数是实时变化的，规则匹配时使用的是当时的值
2. 建议根据实际情况合理设置范围，避免过于严格导致匹配不到种子
3. 可以与其他筛选条件（做种数、大小、分类等）配合使用以达到最佳效果
