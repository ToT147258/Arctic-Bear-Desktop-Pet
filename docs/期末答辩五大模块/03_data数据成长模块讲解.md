# 03 data 数据与成长模块讲解

对应代码路径：

```text
src/data/store.py
```

核心类：

```text
PetDataStore
```

相关数据：

```text
DEFAULT_DATA
ITEM_CATALOG
TASK_CATALOG
LEVEL_MILESTONES
AFFECTION_TIERS
data/save.json
```

## 一、模块作用

`data` 模块是整个项目的数据中心。控制面板上看到的状态、背包、金币、等级、好感、课程、聊天记录、任务进度、系统设置，都由这个模块统一管理。

它主要负责：

- 管理北极熊状态：饱食度、心情、体力、好感度。
- 管理成长系统：等级、经验、称号、好感上限、每日好感额度。
- 管理经济系统：金币获取、购买物品、投喂消耗。
- 管理背包系统：食物、道具、库存。
- 管理每日任务：登录、投喂、互动、散步、专注、完整关怀。
- 管理课程提醒和聊天记录。
- 读写本地 JSON 存档。
- 通过 Qt 信号通知界面刷新。

答辩时可以这样讲：

> `data` 模块是项目的业务规则中心。界面只负责展示和按钮点击，真正的数据修改都交给 `PetDataStore`。这样可以避免不同页面各自改数据导致规则混乱，也方便统一保存到 `data/save.json`。

## 二、演示流程

### 1. 演示状态和存档

演示步骤：

1. 打开控制面板首页。
2. 展示心情、饱食、体力、好感、金币、等级。
3. 关闭程序再启动。
4. 展示数据仍然保留。

讲解重点：

> 这些数据不是写死在界面里，而是从本地 `data/save.json` 读取。每次数据变化后会调用 `save()` 写回文件。

### 2. 演示背包和投喂

演示步骤：

1. 打开背包/极地小厨房。
2. 选择食物。
3. 点击投喂或购买。
4. 观察库存、金币、状态和日志变化。

讲解重点：

> 背包页只负责发起操作，真正判断库存够不够、金币够不够、状态怎么变化，都在 `PetDataStore.feed()`、`PetDataStore.buy_item()` 中完成。

### 3. 演示成长等级

演示步骤：

1. 打开“成长等级”侧边栏。
2. 展示等级、经验条、好感条、每日好感上限。
3. 展示每日任务列表。
4. 说明触摸不直接刷好感。

讲解重点：

> 成长系统不是简单点一下就加好感，而是设计了等级上限、每日上限和高门槛任务，避免奖励太容易获得。

### 4. 演示任务和专注计时

演示步骤：

1. 在成长页点击专注任务。
2. 或在课程提醒页启动专注/休息计时。
3. 等待完成后查看金币、经验、日志变化。

讲解重点：

> 项目把“养成”和“学习陪伴”结合起来，用户不是靠疯狂点击刷数值，而是通过陪伴、专注、完整关怀慢慢提升。

## 三、核心代码讲解

### 1. 默认数据结构：DEFAULT_DATA

第一次运行没有存档时，程序会使用 `DEFAULT_DATA` 创建初始数据。

```python
DEFAULT_DATA = {
    "stats": {
        "hunger": 72,
        "mood": 78,
        "energy": 68,
        "affection": 18,
        "level": 1,
        "exp": 0,
        "coins": 32,
    },
    "inventory": {
        "fish": 1,
        "milk": 0,
        "berry_cake": 0,
        "snowball": 0,
        "scarf": 0,
        "ice": 2,
    },
    "tasks": {task_id: False for task_id in TASK_CATALOG},
    "settings": {
        "opacity": 1.0,
        "always_on_top": True,
        "auto_feed": False,
        "bubble_on": True,
        "status_decay": True,
        "edge_snap_enabled": True,
        "edge_snap_threshold": 48,
        "pet_toggle_hotkey": "Ctrl+Alt+B",
        "pet_corner_hotkey": "Ctrl+Alt+M",
        "companion_goal_minutes": 45,
        "llm": deepcopy(LLM_DEFAULT_CONFIG),
    },
    "growth": {
        "affection_rewards": [],
    },
    "course_reminders": [...],
    "chat_history": [],
    "logs": [],
}
```

讲解逻辑：

- `stats`：核心养成数值。
- `inventory`：背包库存。
- `tasks`：每日任务是否完成。
- `settings`：透明度、置顶、快捷键、大模型配置等系统设置。
- `growth`：成长系统扩展数据。
- `course_reminders`：课程提醒。
- `chat_history`：聊天记录。
- `logs`：行为日志。

答辩话术：

> 项目没有一开始就上复杂数据库，而是使用 JSON 存储。因为桌宠数据量不大，JSON 更轻量，也方便老师直接打开查看数据表结构。

### 2. 数据中心类：PetDataStore

`PetDataStore` 继承 `QObject`，可以发出数据变化信号。

```python
class PetDataStore(QObject):
    changed = Signal()
    log_added = Signal(str)

    def __init__(self, save_path=None):
        super().__init__()
        root = Path(__file__).resolve().parents[2]
        self.save_path = Path(save_path) if save_path else root / "data" / "save.json"
        self.data = deepcopy(DEFAULT_DATA)
        self.load()
        self._rollover_today()
        if not self.data["tasks"].get("daily_login"):
            self.complete_task("daily_login", silent=True)
            self.add_log("系统", "欢迎回来，今日登录任务已完成。")
```

讲解逻辑：

- `changed`：数据变化后通知所有页面刷新。
- `log_added`：新增日志后可以通知日志区域更新。
- `save_path`：默认保存到项目根目录的 `data/save.json`。
- `load()`：启动时读取存档。
- `_rollover_today()`：判断是否跨天，如果跨天则重置每日任务和每日计数。
- 登录任务只在当天第一次启动时完成。

### 3. 存档读取与合并

读取存档时，不是直接用旧 JSON 覆盖全部数据，而是和 `DEFAULT_DATA` 合并。

```python
def load(self):
    if not self.save_path.exists():
        self._normalize()
        return
    try:
        loaded = json.loads(self.save_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, TypeError):
        loaded = {}
    self.data = self._merged(DEFAULT_DATA, loaded)
    self._normalize()

def _merged(self, base, override):
    result = deepcopy(base)
    if not isinstance(override, dict):
        return result
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = self._merged(result[key], value)
        else:
            result[key] = value
    return result
```

讲解逻辑：

- 旧存档缺字段时，用默认字段补齐。
- 新版本加了功能后，旧用户的存档也能继续用。
- `_normalize()` 会修正异常数据，例如百分比不能小于 0 或超过 100。

答辩话术：

> 这个设计解决了版本升级问题。比如后面新增了圆点待机快捷键或大模型配置，旧存档没有这个字段，也可以通过默认数据自动补齐。

### 4. 安全保存逻辑

保存时先写临时文件，再替换正式存档，减少写入中断导致存档损坏。

```python
def save(self):
    self.save_path.parent.mkdir(parents=True, exist_ok=True)
    self.data["save_version"] = 3
    self.data.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    self.data["updated_at"] = datetime.now().isoformat(timespec="seconds")

    temp_path = self.save_path.with_name(f"{self.save_path.name}.tmp")
    temp_path.write_text(
        json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        temp_path.replace(self.save_path)
    except PermissionError:
        self.save_path.write_text(temp_path.read_text(encoding="utf-8"), encoding="utf-8")
        temp_path.unlink(missing_ok=True)
```

讲解逻辑：

- `ensure_ascii=False`：中文不会被转成 Unicode 编码，方便直接阅读。
- `indent=2`：存档格式美观。
- 先写 `.tmp`：避免保存过程中程序异常造成 `save.json` 半截损坏。
- `save_version`：后续可做数据迁移。

### 5. 等级经验曲线

等级越高，升级需要的经验越多。

```python
def level_exp_required(self, level=None):
    level = max(1, self._safe_int(level or self.stats.get("level", 1), 1))
    return (
        260
        + (level - 1) * 140
        + max(0, level - 8) * 80
        + max(0, level - 18) * 120
    )

def level_progress(self):
    required = self.level_exp_required()
    exp = max(0, self._safe_int(self.stats.get("exp", 0), 0))
    return min(exp, required), required
```

讲解逻辑：

- 1 级也需要 260 经验，不会太快升级。
- 8 级以后额外增加需求。
- 18 级以后再次提高需求。
- `level_progress()` 返回当前经验和升级所需经验，供成长页进度条显示。

答辩话术：

> 我把升级设计成非线性曲线，等级越高越难升，避免用户几分钟就把等级刷满。

### 6. 等级里程碑与好感上限

不同等级会解锁不同称号、好感上限和每日好感额度。

```python
def level_info(self):
    level = max(1, self._safe_int(self.stats.get("level", 1), 1))
    milestone = self._level_milestone(level)
    next_milestone = next(
        (item for item in LEVEL_MILESTONES if item["level"] > level),
        None,
    )
    return {
        "level": level,
        "title": milestone["title"],
        "affection_cap": milestone["daily_affection_cap"],
        "affection_ceiling": milestone["affection_ceiling"],
        "next_milestone": next_milestone,
        "next_exp": self.level_exp_required(level),
    }

def daily_affection_cap(self, level=None):
    return self._level_milestone(level)["daily_affection_cap"]

def affection_level_ceiling(self, level=None):
    return self._level_milestone(level)["affection_ceiling"]
```

讲解逻辑：

- 等级不是只有数字，还对应称号。
- 好感度受等级上限限制，等级低时不能直接刷满好感。
- 每日好感也有上限，防止一天内无限刷。

答辩话术：

> 这里把“等级”和“好感”关联起来。等级越高，北极熊和用户关系越亲密，才允许更高的好感上限，这样养成过程更有阶段感。

### 7. 好感阶段说明

`affection_info()` 会把数值转换成可读阶段。

```python
def affection_info(self):
    value = self._clamp_percent(self.stats.get("affection", 0))
    tier = self.affection_tier(value)
    next_tier = None
    for candidate in AFFECTION_TIERS:
        if candidate["min"] > value:
            next_tier = candidate
            break
    return {
        "value": value,
        "title": tier["title"],
        "description": tier["description"],
        "next_title": next_tier["title"] if next_tier else "已满级",
        "next_at": next_tier["min"] if next_tier else 100,
        "to_next": max(0, (next_tier["min"] - value) if next_tier else 0),
    }
```

讲解逻辑：

- 界面不是只显示 `好感 35%`，还显示好感阶段。
- 通过 `next_title` 和 `to_next` 告诉用户下一阶段目标。
- 这让成长页更像养成系统，而不是普通数据面板。

### 8. 投喂逻辑

投喂时会检查物品是否存在、是否是食物、库存是否足够，然后调整状态、激活增益、加少量经验、完成任务。

```python
def feed(self, item_id):
    item = ITEM_CATALOG.get(item_id)
    if not item or item["type"] != "food":
        return False, "这个物品不能投喂。"
    if self.inventory.get(item_id, 0) <= 0:
        return False, f"{item['name']}数量不足。"

    self.inventory[item_id] -= 1
    self.data["daily_counts"]["feed"] = (
        self._safe_int(self.data["daily_counts"].get("feed", 0), 0) + 1
    )
    self.adjust_stats(item["effects"])
    self._activate_buff(item_id)
    self.gain_exp(2)
    self.complete_task("feed_once", silent=True)
    self.add_log("投喂", f"投喂了{item['name']}，状态已更新。")
    return True, f"投喂了{item['name']}。"
```

讲解逻辑：

- 投喂不能凭空发生，必须先有库存。
- 投喂会减少库存。
- 食物效果来自 `ITEM_CATALOG`，不是写死在页面里。
- 只给 2 点经验，避免投喂无限刷等级。
- 完成 `feed_once` 每日任务。

### 9. 购买逻辑

购买物品会检查金币是否足够，然后扣金币、加库存、写日志。

```python
def buy_item(self, item_id):
    item = ITEM_CATALOG.get(item_id)
    if not item:
        return False, "商品不存在。"
    price = int(item["price"])
    if self._safe_int(self.stats.get("coins", 0), 0) < price:
        return False, "金币不足。"

    self.stats["coins"] = self._safe_int(self.stats.get("coins", 0), 0) - price
    self.inventory[item_id] = self.inventory.get(item_id, 0) + 1
    self.add_log("商店", f"购买了{item['name']}，花费 {price} 金币。")
    return True, f"购买了{item['name']}。"
```

讲解逻辑：

- 金币不足直接返回失败信息。
- 成功购买才扣金币和加库存。
- 日志会记录购买行为。

答辩话术：

> 购买和投喂都是数据层处理。背包页面只显示按钮，不能绕过数据层直接修改金币或库存。

### 10. 每日任务奖励

任务必须达成条件后才能领取，领取后只奖励一次。

```python
def complete_task(self, task_id, silent=False):
    task = TASK_CATALOG.get(task_id)
    if not task or self.tasks.get(task_id):
        return False
    if not self.task_claimable(task_id):
        if not silent:
            self.add_log("任务", f"「{task['title']}」还没有达到领取条件。")
        return False

    self.tasks[task_id] = True
    self.stats["coins"] = self._safe_int(self.stats.get("coins", 0), 0) + self._safe_int(task["reward"], 0)
    self.gain_exp(task["exp"])

    if not silent:
        self.add_log("任务", f"完成「{task['title']}」，获得 {task['reward']} 金币和 {task['exp']} 经验。")
    else:
        self._commit()
    return True
```

讲解逻辑：

- `self.tasks.get(task_id)` 防止重复领取。
- `task_claimable()` 判断条件是否达成。
- 奖励包含金币和经验。
- `silent=True` 用于操作过程中自动完成任务，不弹太多提示。

### 11. 触摸不直接加好感

为了避免用户狂点北极熊刷好感，普通触摸只提升心情，消耗一点体力。

```python
def touch(self):
    touches = self._safe_int(self.data["daily_counts"].get("touch", 0), 0)
    self.data["daily_counts"]["touch"] = touches + 1

    if touches < 5:
        mood_gain = 2
    else:
        mood_gain = 1

    effects = {"mood": mood_gain, "energy": -1}
    self.adjust_stats(effects)
    self.complete_task("touch_once", silent=True)
    self.add_log("互动", "温柔互动只提升心情；好感需要通过完整关怀、专注或礼物慢慢建立。")
```

讲解逻辑：

- 前 5 次触摸收益稍高，之后收益降低。
- 触摸不直接增加好感。
- 好感需要完整关怀、专注或礼物等更高门槛行为。

答辩话术：

> 这是为了让好感机制更困难、更有过程感，不让用户通过不停点击快速刷满。

### 12. 完整关怀机制

完整关怀要求当天完成多种行为后才能获得好感奖励。

```python
def daily_care(self):
    if self.tasks.get("care_plan"):
        return False, "今天已经完成过关怀计划。"
    counts = self.data.get("daily_counts", {})
    if (
        self._safe_int(counts.get("feed", 0), 0) < 2
        or self._safe_int(counts.get("touch", 0), 0) < 5
        or self._safe_int(counts.get("walk", 0), 0) < 1
        or self._safe_int(counts.get("rest", 0), 0) < 1
        or self._safe_int(self.data.get("companion_seconds", 0), 0) < 1200
    ):
        return False, "完整关怀需要先完成 2 次投喂、5 次温柔互动、1 次散步、1 次休息，并陪伴至少 20 分钟。"

    self.data["daily_counts"]["care"] = 1
    self.adjust_stats({"hunger": 2, "mood": 2, "energy": 1, "affection": 1})
    self.complete_task("care_plan", silent=True)
    self.add_log("关怀", "完成今日关怀计划，四项状态都获得了照顾。")
    return True, "完成今日关怀，状态和好感都提升了。"
```

讲解逻辑：

- 要求投喂、互动、散步、休息、陪伴时间都达到条件。
- 完整关怀每天只能完成一次。
- 好感只加 1，奖励克制。

答辩话术：

> 这就是项目的困难奖励机制。好感不是靠单个动作刷出来，而是要求用户完成一整套陪伴行为。

### 13. 状态自然衰减和陪伴时间

`tick()` 会定期根据时间流逝降低状态、累计陪伴时间，并检查任务。

```python
def tick(self):
    self._rollover_today()
    now_ts = int(datetime.now().timestamp())
    last_tick = self._safe_int(self.data.get("last_tick") or now_ts, now_ts)
    elapsed = max(0, min(now_ts - last_tick, 7200))
    self.data["last_tick"] = now_ts

    messages = []
    messages.extend(self._tick_buffs(now_ts))

    if self.settings.get("status_decay", True):
        effects = {}
        hunger_drop = int(elapsed // 300)
        energy_drop = int(elapsed // 600)
        mood_drop = int(elapsed // 900)
        if hunger_drop and not self._has_buff("hunger_stop"):
            effects["hunger"] = -hunger_drop
        if energy_drop:
            effects["energy"] = -energy_drop
        if mood_drop and not self._has_buff("mood_guard"):
            effects["mood"] = -mood_drop
        if effects:
            self.adjust_stats(effects)

    self.data["companion_seconds"] += elapsed
    if self.data["companion_seconds"] >= self._companion_goal_seconds():
        if self.complete_task("companion", silent=True):
            messages.append("陪伴任务完成，奖励已到账。")

    self._commit()
    return messages
```

讲解逻辑：

- 饱食、体力、心情会随时间自然下降。
- 有增益时可以阻止某些下降。
- 陪伴时间累积到目标后完成任务。
- `elapsed` 最大限制为 7200 秒，避免长时间关闭程序后一次扣太多状态。

### 14. 专注计时奖励

专注完成后才给少量金币、经验和状态变化。

```python
def tick_focus(self):
    session = self.focus_session
    if not session.get("active"):
        return None

    remaining = self._sync_focus_remaining()
    if remaining > 0:
        self._commit()
        return None

    title = session.get("title") or "专注"
    total_minutes = max(1, self._safe_int(session.get("total_seconds", 0), 0) // 60)
    self.data["focus_session"] = deepcopy(DEFAULT_DATA["focus_session"])

    self.data["daily_counts"]["focus"] += 1
    self.data["daily_counts"]["focus_minutes"] += total_minutes
    effects = {"mood": 3, "energy": -6}
    if total_minutes >= 25:
        effects["affection"] = 1
    self.adjust_stats(effects)
    self.complete_task("focus_once", silent=True)
    self.stats["coins"] += 1
    self.gain_exp(2)
    self.add_log("专注", f"「{title}」完成，奖励已到账。")
```

讲解逻辑：

- 专注没结束不给奖励。
- 25 分钟以上才可能加好感。
- 金币只加 1，避免奖励泛滥。
- 专注会消耗体力，符合真实逻辑。

### 15. 设置保存

系统设置也通过数据层保存。

```python
def set_setting(self, key, value):
    self.settings[key] = value
    labels = {
        "opacity": "透明度",
        "always_on_top": "置顶",
        "pet_toggle_hotkey": "桌宠快捷键",
        "pet_corner_hotkey": "圆圈待机快捷键",
    }
    self.add_log("设置", f"{labels.get(key, key)} 已更新。")
```

讲解逻辑：

- 快捷键、透明度、置顶等都写进 `settings`。
- 下次启动时从 `save.json` 读取，所以设置会持久化。

## 四、数据表设计说明

虽然项目使用 JSON，不使用传统数据库，但可以按“数据表”理解：

| 数据表/对象 | 主要字段 | 作用 |
|---|---|---|
| `stats` | `hunger`、`mood`、`energy`、`affection`、`level`、`exp`、`coins` | 宠物状态和成长核心数值 |
| `inventory` | `fish`、`milk`、`berry_cake`、`snowball`、`scarf`、`ice` | 背包库存 |
| `tasks` | 每个任务 id 对应 `True/False` | 每日任务完成状态 |
| `settings` | `opacity`、`always_on_top`、快捷键、`llm` | 系统设置 |
| `course_reminders` | `title`、`time`、`location`、`day`、`note` | 课程提醒 |
| `chat_history` | `role`、`text`、`time` | 聊天记录 |
| `logs` | 日志文本 | 行为记录 |
| `focus_session` | `active`、`remaining_seconds`、`title` | 专注计时状态 |

答辩话术：

> 这里可以把 JSON 看成轻量数据库。每个顶层 key 就相当于一张表或一个数据对象。

## 五、老师可能追问

### 问：为什么不用数据库？

答：

> 桌宠项目数据量小，主要是本地个人数据。JSON 更轻量、可读性强、部署简单，也方便调试和答辩展示。如果后续做多用户或云同步，再迁移到 SQLite 或服务器数据库。

### 问：如何保证存档不会乱？

答：

> 数据修改集中在 `PetDataStore`，页面不能直接乱改 JSON。保存时先写临时文件再替换正式文件，同时启动时会把旧存档和默认结构合并，缺失字段会自动补齐。

### 问：为什么触摸不直接加好感？

答：

> 因为如果触摸直接加好感，用户可以一直点击快速刷满。现在普通触摸只加心情，好感需要完整关怀、专注或任务奖励，并受等级上限和每日上限控制，更符合养成系统的平衡。

### 问：金币为什么设置得比较难获得？

答：

> 金币主要来自每日任务、专注和升级奖励，而且每次奖励都很少。这样用户需要持续互动和学习陪伴，不能短时间刷满背包，养成过程更有长期性。

## 六、答辩总结

可以这样收尾：

> `data` 模块是北极熊桌宠的数据和成长中心。它用 `PetDataStore` 统一管理状态、背包、金币、等级、好感、任务、课程、聊天和设置，并保存到 `data/save.json`。同时它设计了经验曲线、等级里程碑、好感上限、每日任务和专注奖励，让项目不只是界面展示，而是一个有长期养成逻辑的桌宠系统。
