# 04 features 功能页面模块讲解

对应代码路径：

```text
src/features/
```

代表文件：

```text
src/features/status.py
src/features/notification.py
src/features/interaction.py
src/features/chat.py
src/features/backpack.py
src/features/growth.py
src/features/settings.py
src/features/common.py
```

核心页面类：

```text
StatusPage
NotificationPage
InteractionPage
ChatPage
BackpackPage
GrowthPage
SettingsPage
ModulePage
```

## 一、模块作用

`features` 模块负责控制面板里的各个功能页面。它相当于把用户能看到、能点击、能操作的功能拆成多个独立页面。

主要页面包括：

- `StatusPage`：宠物状态首页。
- `NotificationPage`：课程提醒和课表识别。
- `InteractionPage`：动作管理和桌宠互动。
- `ChatPage`：聊天互动和大模型陪伴。
- `BackpackPage`：背包、商店、投喂。
- `GrowthPage`：等级、好感、每日任务。
- `SettingsPage`：缩放、透明度、快捷键、大模型配置、存档管理。

答辩时可以这样讲：

> `features` 模块是控制面板的页面层。它不直接负责底层动画，也不直接读写 JSON，而是通过主控模块、数据模块和服务模块完成协作。这样每个页面只关心自己的功能，代码结构更清晰。

## 二、页面之间的协作关系

整体调用关系：

```text
用户点击页面按钮
        ↓
features 页面类
        ↓
PetDataStore 修改数据 / PolarBearPetWindow 播放动作 / services 调用外部能力
        ↓
store.changed 信号通知页面刷新
        ↓
控制面板显示最新状态
```

核心思想：

- 页面负责展示和接收用户操作。
- 数据修改交给 `PetDataStore`。
- 动作播放交给主控传入的 `play_action` 回调。
- OCR 和大模型交给 `services`。
- 页面之间不直接互相乱调，降低耦合。

## 三、演示流程

### 1. 演示宠物状态页

演示：

1. 打开“宠物状态”。
2. 展示饱食、心情、体力、好感、课程提醒、今日行为记录。
3. 点击“打招呼”“摸摸头”“休息建议”等快捷互动。

讲解重点：

> 状态页主要读取 `store.stats` 和课程摘要，把数据可视化成卡片。用户点击快捷互动后，会调用数据层更新状态，再让桌宠播放对应动作。

### 2. 演示课程提醒页

演示：

1. 打开“课程提醒”。
2. 展示当前课程列表和下一节课智能提醒。
3. 手动添加一门课程。
4. 展示课表图片识别入口。

讲解重点：

> 课程页负责用户交互，OCR 识别和文本解析放在 `services/course_ocr.py`。识别成功后，页面调用数据层导入课程。

### 3. 演示动作管理页

演示：

1. 点击“挥手”“向左走”“向右走”“睡觉”“贴边”。
2. 观察桌面上的北极熊执行动作。

讲解重点：

> 动作页自己不播放动画，只把动作名传给主控模块，由主控再调用桌宠窗口的 `play_action()`。

### 4. 演示聊天互动页

演示：

1. 输入一句话。
2. 看聊天记录按正常顺序显示。
3. 北极熊在桌面右上方显示气泡回复。
4. 如果大模型已配置，说明它会走联网模型；否则本地回复兜底。

讲解重点：

> 聊天页通过 `LLMClient` 接入 DeepSeek、ChatGPT/OpenAI、智谱等模型，同时保留本地回复，避免没配置 Key 时功能不可用。

### 5. 演示背包商店页

演示：

1. 打开“外观装扮/背包小厨房”。
2. 点击不同食物卡片。
3. 使用“状态推荐”“一键配餐”“购买当前”“投喂当前”。
4. 展示金币、库存和状态变化。

讲解重点：

> 背包页只负责选择物品和显示物品效果，买东西、投喂、状态变化全部由数据层处理。

### 6. 演示成长页

演示：

1. 打开“成长等级”侧边栏。
2. 展示等级、经验条、好感上限、每日好感额度。
3. 展示任务列表和领取按钮。
4. 说明触摸不能直接刷好感。

讲解重点：

> 成长页把数据层中的升级和好感机制可视化，体现养成系统的困难奖励设计。

### 7. 演示系统设置页

演示：

1. 调整北极熊缩放比例。
2. 修改透明度。
3. 设置隐藏/召回快捷键、圆点待机快捷键。
4. 展示大模型配置和存档导入导出。

讲解重点：

> 设置页改变的不是临时变量，而是写入 `store.settings`，所以下次启动仍然生效。

## 四、核心代码讲解

### 1. 页面统一接收依赖

各页面一般都会接收这些对象：

```python
class InteractionPage(QWidget):
    def __init__(self, pet_window, store, play_action, toggle_pet):
        super().__init__()
        self.pet_window = pet_window
        self.store = store
        self.play_action = play_action
        self.toggle_pet = toggle_pet
        self._build_ui()
```

讲解逻辑：

- `store`：访问和修改数据。
- `pet_window`：需要直接显示桌宠气泡时使用。
- `play_action`：主控传入的动作播放回调。
- `toggle_pet`：显示或隐藏桌宠。

答辩话术：

> 页面不自己创建数据中心，也不自己创建桌宠窗口，而是由主控模块传入依赖。这样整个程序只有一个数据源和一个桌宠实例，不会出现状态不同步。

### 2. 动作管理页：InteractionPage

动作页把按钮和动作名绑定起来。

```python
buttons = [
    ("互动", "touch", self._touch),
    ("挥手", "wave", lambda: self._play("wave", "挥手动作已触发。")),
    ("向左走", "walk_left", self._walk_left),
    ("向右走", "walk_right", self._walk_right),
    ("贴左边", "edge_left", lambda: self._play("edge_left", "扒住左侧边缘。")),
    ("贴右边", "edge_right", lambda: self._play("edge_right", "扒住右侧边缘。")),
    ("跳跃", "jump", lambda: self._play("jump", "跳跃动作已触发。")),
    ("睡觉", "sleep", self._sleep),
    ("显示/隐藏桌宠", "toggle", self.toggle_pet),
    ("回到待机", "idle", lambda: self._play("idle", "已回到待机状态。")),
]
```

每个按钮最终调用统一入口：

```python
def _play(self, action_name, bubble):
    self.play_action(action_name, bubble)

def _touch(self):
    self.store.touch()
    self._play("touch", "温柔互动完成，心情提升；好感需要完整关怀慢慢积累。")

def _walk_left(self):
    self.store.walk()
    self._play("walk_left", "向左走一小段。")

def _sleep(self):
    self.store.rest()
    self._play("sleep", "进入休息状态。")
```

讲解逻辑：

- 用户点按钮后，页面先调用数据层记录行为。
- 再通过 `play_action` 让桌宠执行对应动作。
- 例如走路会增加散步次数，睡觉会调用 `store.rest()` 恢复体力。

答辩话术：

> 动作按钮不是单纯播放动画，它还会写入养成系统。例如散步会计入每日任务，休息会影响体力。

### 3. 背包商店页：BackpackPage

背包页负责展示物品、选择物品、推荐物品和调用数据层购买/使用。

```python
def refresh(self):
    self.coin_label.setText(f"冰原金币  {self.store.stats.get('coins', 0)}")
    for item_id, label in self.count_labels.items():
        label.setText(f"库存：{self.store.inventory.get(item_id, 0)}")
    if self.selected_item_id:
        self._sync_showcase()
```

选中物品后刷新展示区：

```python
def _sync_showcase(self):
    item = ITEM_CATALOG[self.selected_item_id]
    pixmap = self._item_pixmap(item, 300, 218)
    if not pixmap.isNull():
        self.showcase_image.setPixmap(pixmap)
    self.showcase_name.setText(item["name"])
    self.showcase_meta.setText(
        f"{TYPE_LABELS.get(item['type'], item['type'])} · {item['price']} 金币 · 北极熊专属补给"
    )
    self.showcase_stock.setText(
        f"库存 {self.store.inventory.get(self.selected_item_id, 0)} · 可用金币 {self.store.stats.get('coins', 0)}"
    )
    self.showcase_effects.setText(
        f"{self._format_effects(item['effects'])}；{self._format_buff(item)}"
    )
```

根据最低状态推荐物品：

```python
def _recommended_item_id(self):
    stats = self.store.stats
    lowest_key = min(
        ("hunger", "mood", "energy", "affection"),
        key=lambda key: int(stats.get(key, 0)),
    )
    if lowest_key == "hunger":
        return "fish" if self.store.stats.get("coins", 0) >= ITEM_CATALOG["fish"]["price"] else "ice"
    if lowest_key == "energy":
        return "milk"
    if lowest_key == "mood":
        return "berry_cake" if self.store.stats.get("coins", 0) >= ITEM_CATALOG["berry_cake"]["price"] else "snowball"
    return "scarf" if self.store.stats.get("coins", 0) >= ITEM_CATALOG["scarf"]["price"] else "berry_cake"
```

使用和购买：

```python
def _use_item(self, item_id):
    ok, message = self.store.use_item(item_id)
    if ok:
        action = "touch" if ITEM_CATALOG[item_id]["type"] == "food" else "wave"
        self.play_action(action, message)
    else:
        self.play_action("idle", message)

def _buy_item(self, item_id):
    ok, message = self.store.buy_item(item_id)
    self.play_action("idle", message)
```

讲解逻辑：

- 背包页自己不扣金币，也不改库存。
- `_recommended_item_id()` 体现智能推荐：根据当前最低状态推荐食物或道具。
- `_use_item()` 调用 `store.use_item()` 后，再触发桌宠反馈动作。

答辩话术：

> 这里体现了“页面层”和“数据层”分离。页面只负责用户体验，物品规则和奖励规则都在数据层统一处理。

### 4. 聊天互动页：ChatPage

聊天页支持联网大模型，也支持本地兜底回复。

```python
def _send_message(self, text):
    if self._busy:
        return
    self.store.add_chat_message("user", text)
    llm = LLMClient(self.store)
    reason = llm.unavailable_reason()
    if reason is None:
        self._pending_user_text = text
        self._busy = True
        self._set_send_enabled(False)
        messages = self._llm_messages()
        threading.Thread(target=self._worker_chat, args=(messages,), daemon=True).start()
        return

    reply, action = self._reply_for(text)
    if llm.config.get("enabled") and reason != "大模型未启用。":
        reply = f"联网大模型暂时不可用（{reason}），我先用本地回应：{reply}"
    self._deliver_reply(reply, action)
```

调用大模型放到后台线程，避免界面卡死：

```python
def _worker_chat(self, messages):
    try:
        reply = LLMClient(self.store).chat(
            messages,
            system_prompt=build_pet_system_prompt(self.store),
            timeout=24,
        )
        self.response_ready.emit(reply or "我刚刚有点卡住了，可以再说一次嘛。")
    except Exception as exc:
        self.error_ready.emit(str(exc))
```

收到回复后更新聊天记录、桌宠动作和气泡：

```python
def _deliver_reply(self, reply, action):
    self.store.add_chat_message("bear", reply)
    if action == "touch":
        self.store.touch()
    elif action in {"rest", "sleep"}:
        self.store.rest()

    self.play_action(action if action in {"touch", "wave", "sleep"} else "idle", None)
    if reply and self.store.settings.get("bubble_on", True):
        self.pet_window.show_bubble(reply, duration=7200, chat=True)
```

讲解逻辑：

- `_busy` 防止用户连续发送导致并发混乱。
- 大模型网络请求放到线程里，保持 UI 响应。
- `response_ready`、`error_ready` 通过 Qt 信号回到主线程更新界面。
- 如果大模型不可用，走本地回复，不让功能直接失败。
- 回复会同步到桌宠气泡，增强桌宠陪伴感。

答辩话术：

> 聊天页面不是简单文本框，它把聊天记录、AI 模型、桌宠动作和气泡反馈连在一起。用户会感觉是在和桌面上的北极熊交流。

### 5. 成长等级页：GrowthPage

成长页把数据层的等级、经验、好感、每日任务可视化。

```python
def refresh(self):
    stats = self.store.stats
    level = self.store.level_info()
    exp, required = self.store.level_progress()
    affection = self.store.affection_info()
    daily_cap = self.store.daily_affection_cap()
    daily_gain = int(self.store.data.get("daily_counts", {}).get("affection_gain", 0))
    ceiling = max(1, int(level["affection_ceiling"]))
    companion_seconds, companion_goal = self.store.companion_progress()

    self.level_label.setText(f"Lv.{level['level']}")
    self.title_label.setText(
        f"「{level['title']}」\n金币 {stats.get('coins', 0)} · 好感 {affection['value']}% · 陪伴 {self.store.data.get('days', 1)} 天"
    )
    self._set_bar(self.exp_bar, exp, required, f"升级经验 {exp}/{required} EXP")
    self._set_bar(self.affection_bar, affection["value"], ceiling, f"好感上限 {affection['value']}/{ceiling}%")
    self._set_bar(self.daily_affection_bar, daily_gain, daily_cap, f"今日好感 {daily_gain}/{daily_cap}")
    self._set_bar(
        self.companion_bar,
        companion_seconds // 60,
        max(1, companion_goal // 60),
        f"今日陪伴 {companion_seconds // 60}/{max(1, companion_goal // 60)} 分钟",
    )
```

成长规则说明：

```python
self.rule_label["body"].setText(
    "普通触摸只提升心情，不直接增加好感。\n"
    "好感受等级上限和每日上限双重限制。\n"
    "金币主要来自高门槛任务和少量升级奖励，不能快速刷。"
)
```

任务领取逻辑：

```python
def _claim_task(self, task_id):
    ok = self.store.complete_task(task_id)
    message = "奖励已领取。" if ok else "这个任务还没达到领取条件。"
    self.play_action("wave" if ok else "idle", message)

def _daily_care(self):
    ok, message = self.store.daily_care()
    self.play_action("touch" if ok else "idle", message)
```

讲解逻辑：

- 成长页不计算等级规则，只调用数据层方法。
- 经验、好感、每日好感、陪伴时间都用进度条展示。
- 点击领取任务时，调用 `store.complete_task()`。
- 完整关怀调用 `store.daily_care()`。

答辩话术：

> 成长页把抽象的养成规则变成可视化目标，用户能明确知道下一级需要多少经验、今天还能获得多少好感、任务是否可领取。

### 6. 课程提醒页：NotificationPage

课程页支持手动添加课程，也支持课表图片 OCR。

导入图片：

```python
def _import_timetable_image(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self,
        "选择课表照片",
        "",
        "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
    )
    if not file_path:
        return
    text, message = recognize_timetable_image(file_path)
    self.ocr_status_label.setText(message)
    if text:
        self.ocr_text_input.setPlainText(text)
        self._parse_ocr_text()
```

解析文字并导入课程：

```python
def _parse_ocr_text(self):
    text = self.ocr_text_input.toPlainText()
    courses = parse_timetable_text(text)
    if not courses:
        self.ocr_status_label.setText("没有解析出课程。建议保留每行包含：星期 + 时间/节次 + 课程名 + 地点。")
        return
    added = self.store.import_course_reminders(courses, replace=False)
    self.ocr_status_label.setText(f"解析到 {len(courses)} 条课程，新增导入 {added} 条。")
```

触发课程提醒气泡：

```python
def _trigger_course(self):
    message = self.store.trigger_course_bubble()
    if self.store.settings.get("bubble_on", True):
        self.pet_window.show_bubble(message)
```

讲解逻辑：

- 文件选择由页面完成。
- 图片 OCR 交给 `recognize_timetable_image()`。
- 文本解析交给 `parse_timetable_text()`。
- 课程保存交给 `store.import_course_reminders()`。
- 提醒气泡由 `pet_window.show_bubble()` 显示到桌宠旁边。

答辩话术：

> 课表识别是一个完整流程：图片输入、OCR 识别、文本清洗、课程结构化、写入本地课程提醒。

### 7. 设置页：SettingsPage

设置页负责用户可调配置，包括快捷键和大模型。

保存隐藏/召回快捷键：

```python
def _save_hotkey(self):
    hotkey = self._editor_hotkey_text()
    ok, message = self.set_hotkey(hotkey)
    self.hotkey_status.setText(message)
    if ok:
        current = self.get_hotkey() or hotkey
        self.hotkey_editor.setKeySequence(QKeySequence(current))
        self.refresh()
```

保存圆点待机快捷键：

```python
def _save_corner_hotkey(self):
    hotkey = self._corner_editor_hotkey_text()
    ok, message = self.set_corner_hotkey(hotkey)
    self.corner_hotkey_status.setText(message)
    if ok:
        current = self.get_corner_hotkey() or hotkey
        self.corner_hotkey_editor.setKeySequence(QKeySequence(current))
        self.refresh()
```

刷新大模型配置显示：

```python
def _refresh_llm_controls(self):
    cfg = normalize_llm_config(self.store.settings.get("llm", {}))
    self._updating_llm_controls = True
    self.llm_enabled.setChecked(bool(cfg.get("enabled")))
    self.llm_auto_talk.setChecked(bool(cfg.get("auto_talk")))

    index = self.llm_provider.findData(cfg["provider"])
    self.llm_provider.setCurrentIndex(max(0, index))
    self._load_llm_models(cfg["provider"], cfg.get("model", ""))
    self.llm_api_url.setText(cfg.get("api_url", ""))
    self.llm_api_key.setText(cfg.get("api_key", ""))

    provider_name = LLM_PROVIDERS.get(cfg["provider"], LLM_PROVIDERS["deepseek"])["name"]
    state = "已启用" if cfg.get("enabled") else "未启用"
    key_state = "已填写 Key" if cfg.get("api_key") else "未填写 Key"
    self.llm_status.setText(f"当前：{state} · {provider_name} · {cfg.get('model')} · {key_state}")
    self._updating_llm_controls = False
```

讲解逻辑：

- 快捷键由 `QKeySequenceEdit` 获取用户输入。
- 保存后写入数据层设置。
- 大模型配置通过 `normalize_llm_config()` 标准化后显示。
- 支持服务商、模型名、API 地址、Key、是否启用等配置。

答辩话术：

> 设置页让用户可以不改代码就配置桌宠行为，例如调整缩放、修改快捷键、切换大模型服务商。

## 五、页面模块的设计优点

### 1. 代码更清晰

如果所有页面都写在 `main.py`，文件会非常大，维护困难。拆分后每个页面负责一个功能。

```text
features/backpack.py      背包商店
features/chat.py          聊天互动
features/growth.py        成长等级
features/interaction.py   动作管理
features/notification.py  课程提醒
features/settings.py      系统设置
features/status.py        状态首页
```

### 2. 便于答辩展示

每个页面都能单独讲：

- 这个页面做什么。
- 用户怎么操作。
- 点击按钮后调用哪个数据方法或服务方法。
- 最后桌宠如何反馈。

### 3. 便于后续扩展

如果以后新增“成就系统”或“装扮系统”，只需要新增一个页面文件，并在主控里注册，不需要大改其他页面。

## 六、老师可能追问

### 问：为什么要拆这么多页面文件？

答：

> 因为每个页面功能差别很大。如果都写在一个文件里，代码会很乱。拆分后背包、聊天、成长、设置都能独立维护，主控模块只负责注册和切换页面。

### 问：页面直接修改数据了吗？

答：

> 页面不会直接改 JSON 文件，而是调用 `PetDataStore` 的方法。这样数据规则统一在数据层，页面只负责交互和展示。

### 问：聊天页为什么要用线程？

答：

> 大模型请求是网络请求，可能比较慢。如果放在主线程，整个界面会卡住。所以聊天页开后台线程请求模型，再通过 Qt 信号把结果发回界面。

### 问：课程 OCR 为什么不直接写在页面里？

答：

> OCR 识别和课程解析属于工具能力，和页面 UI 不是一类逻辑。拆到 `services` 后，页面更干净，以后换 OCR 方案也不用大改页面。

## 七、答辩总结

可以这样收尾：

> `features` 模块是控制面板的功能页面层。它把状态、课程、动作、聊天、背包、成长、设置拆分为独立页面，每个页面负责用户交互，通过 `PetDataStore` 修改数据，通过 `play_action` 驱动桌宠动作，通过 `services` 调用大模型和 OCR。这样的结构让项目从一个单文件脚本变成了清晰的多模块桌宠应用。
