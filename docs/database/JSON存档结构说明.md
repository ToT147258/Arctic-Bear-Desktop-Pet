# JSON 存档结构说明

本项目实际运行时使用本地 JSON 文件作为轻量数据存储：

```text
data/save.json
```

因此本项目不是 SQLite 数据库项目，也不需要安装或启动数据库服务。`data/save.json` 可以理解为“文件型本地数据库”，由 `src/data/store.py` 中的 `PetDataStore` 统一读写。

## 数据初始化脚本

构建阶段的数据初始化脚本为：

```text
docs/database/init_save_json.py
```

运行方式：

```powershell
python docs/database/init_save_json.py
```

默认生成：

```text
data/save.template.json
```

如果要直接生成运行存档：

```powershell
python docs/database/init_save_json.py data/save.json
```

## JSON 顶层结构

| JSON 字段 | 类型 | 作用 |
|---|---|---|
| `stats` | Object | 宠物状态与成长数值，包括饱食、心情、体力、好感、等级、经验、金币。 |
| `inventory` | Object | 背包库存，保存每种物品数量。 |
| `tasks` | Object | 每日任务完成状态，任务 id 对应布尔值。 |
| `settings` | Object | 系统设置，包括透明度、置顶、气泡、贴边、快捷键和大模型配置。 |
| `active_buffs` | Object | 当前生效的物品增益。 |
| `daily_counts` | Object | 当日行为计数，如投喂、触摸、散步、休息、专注分钟数。 |
| `growth` | Object | 成长相关扩展数据，如好感奖励领取记录。 |
| `focus_session` | Object | 当前专注或休息计时状态。 |
| `course_reminders` | Array | 课程提醒列表。 |
| `chat_history` | Array | 聊天记录列表。 |
| `logs` | Array | 行为日志列表。 |

## 逻辑数据对象

虽然没有使用关系型数据库，但可以按以下逻辑对象理解数据：

| 逻辑对象 | 对应 JSON 字段 |
|---|---|
| 宠物状态表 | `stats` |
| 背包库存表 | `inventory` |
| 每日任务表 | `tasks` |
| 系统设置表 | `settings` |
| Buff 状态表 | `active_buffs` |
| 行为计数表 | `daily_counts` |
| 课程提醒表 | `course_reminders` |
| 聊天记录表 | `chat_history` |
| 行为日志表 | `logs` |
| 专注计时表 | `focus_session` |

## 答辩说明口径

可以这样说明：

> 本项目没有使用 SQLite 或 MySQL，而是使用 `data/save.json` 作为本地文件型数据库。这样做的原因是桌宠属于单机桌面应用，数据量小，JSON 更轻量、更容易部署，也方便老师直接查看存档内容。为了满足系统构建阶段“数据库脚本”的要求，我提供了 `init_save_json.py` 作为 JSON 存档初始化脚本，并提供 JSON 存档结构说明。
