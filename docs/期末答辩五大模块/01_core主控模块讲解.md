# 01 core 主控模块详细讲解

对应代码：

```text
main.py
src/core/app.py
```

核心类：

```text
PolarBearPetApp
```

---

## 1. 模块作用

`core` 是整个北极熊桌宠项目的主控模块，也就是系统的大脑。

它负责把项目中其他四个模块连接起来：

```text
core 主控模块
  ├─ pet 桌宠表现模块
  ├─ data 数据成长模块
  ├─ features 功能页面模块
  └─ services 外部服务模块
```

主要职责：

- 启动整个 PySide6 桌面应用。
- 创建主控制面板。
- 创建北极熊桌宠悬浮窗口。
- 加载左侧导航栏和各个功能页面。
- 负责页面切换。
- 负责系统托盘菜单。
- 负责全局快捷键。
- 接收桌宠交互事件，并分发给对应模块。
- 定时刷新状态、课程、时间、任务等信息。

答辩话术：

> `core` 模块是项目的主控中心。它不把所有业务都写在一个文件里，而是负责统一调度。桌宠动画交给 `pet` 模块，状态和存档交给 `data` 模块，页面功能交给 `features` 模块，大模型和 OCR 交给 `services` 模块。

---

## 2. 现场演示

### 2.1 启动项目

演示命令：

```bash
python main.py
```

演示时可以说：

> 程序入口是 `main.py`。它创建 Qt 应用，然后创建主窗口 `PolarBearPetApp`。主窗口启动后，会同时创建控制面板和北极熊桌宠窗口。

### 2.2 展示控制面板

演示步骤：

1. 打开主控制面板。
2. 点击左侧导航栏。
3. 切换“宠物状态”“成长等级”“课程提醒”“聊天互动”“系统设置”等页面。

讲解重点：

> 页面本身不写在 `core` 里，而是放在 `features` 目录。`core` 只负责把这些页面装配到主窗口中。

### 2.3 展示桌宠控制

演示：

- 点击“挥手”按钮，北极熊挥手。
- 点击“睡觉”按钮，北极熊睡觉。
- 点击“显示/隐藏桌宠”，桌宠显示或隐藏。
- 按 `Ctrl+Alt+M`，桌宠进入右下角圆圈待机。

讲解重点：

> 用户点击按钮后，`core` 会调用 `pet` 模块播放动作。这样主控模块和动画模块是分开的。

### 2.4 展示系统托盘和快捷键

演示：

- 系统托盘菜单。
- `Ctrl+Alt+B` 显示/隐藏桌宠。
- `Ctrl+Alt+M` 圆圈待机/召回。

讲解重点：

> 快捷键也是由 `core` 模块注册和分发的。按下快捷键后，系统会调用对应的显示、隐藏或圆圈待机函数。

---

## 3. 重要代码讲解

### 3.1 程序入口 main.py

关键代码：

```python
import sys

from PySide6.QtWidgets import QApplication

from src.core.app import PolarBearPetApp


def main():
    app = QApplication(sys.argv)
    window = PolarBearPetApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

代码逻辑：

1. `QApplication` 是 Qt 应用的基础对象。
2. `PolarBearPetApp` 是项目主窗口。
3. `window.show()` 显示控制面板。
4. `app.exec()` 进入事件循环。

答辩时可以说：

> Qt 程序必须进入事件循环，才能持续响应按钮点击、鼠标拖拽、快捷键和定时器事件。

---

### 3.2 主控类初始化

核心代码摘录：

```python
class PolarBearPetApp(QMainWindow):
    pet_chat_reply_ready = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.store = PetDataStore()
        self.pet_window = PolarBearPetWindow()

        self.pet_window.setWindowOpacity(
            float(self.store.settings.get("opacity", 1.0))
        )
        self.pet_window.set_always_on_top(
            bool(self.store.settings.get("always_on_top", True))
        )
        self.pet_window.set_edge_snap(
            bool(self.store.settings.get("edge_snap_enabled", True)),
            int(self.store.settings.get("edge_snap_threshold", 48)),
        )

        self.pet_window.interaction_requested.connect(
            self._handle_pet_window_interaction
        )

        self._build_ui()
        self._build_tray()
        self._setup_pet_hotkeys()
        QTimer.singleShot(0, self._show_pet_on_startup)
```

代码逻辑：

1. `self.store = PetDataStore()` 创建数据中心。
2. `self.pet_window = PolarBearPetWindow()` 创建桌宠悬浮窗。
3. 根据设置恢复透明度、置顶、贴边功能。
4. 连接桌宠窗口信号 `interaction_requested`。
5. 构建 UI、托盘、快捷键。
6. 启动后自动显示桌宠。

答辩时可以说：

> 主控模块初始化时会把数据层和桌宠表现层都创建好，并通过信号槽连接起来。这样桌宠点击、拖拽、动作完成等事件可以被主控统一处理。

---

### 3.3 页面装配逻辑

核心代码摘录：

```python
pages = [
    ("宠物状态", self._build_overview_page, True),
    ("成长等级", lambda: self._scroll_module_page(
        GrowthPage(self.store, self._play_pet_action)
    ), False),
    ("课程提醒", lambda: self._scroll_module_page(
        NotificationPage(self.store, self.pet_window)
    ), False),
    ("动作管理", lambda: self._scroll_module_page(
        InteractionPage(
            self.pet_window,
            self.store,
            self._play_pet_action,
            self.toggle_pet_window,
        )
    ), False),
    ("聊天互动", lambda: self._scroll_module_page(
        ChatPage(self.store, self.pet_window, self._play_pet_action)
    ), False),
    ("外观装扮", lambda: BackpackPage(self.store, self._play_pet_action), False),
    ("系统设置", lambda: self._scroll_module_page(
        SettingsPage(
            self.store,
            self.pet_window,
            self.current_pet_hotkey,
            self.set_pet_toggle_hotkey,
            self.current_pet_corner_hotkey,
            self.set_pet_corner_hotkey,
        )
    ), False),
]
```

代码逻辑：

1. 每个元组代表一个导航页面。
2. 页面类来自 `features` 模块。
3. `self.store` 传给页面，让页面可以读取和修改数据。
4. `self.pet_window` 传给页面，让页面可以控制桌宠。
5. `self._play_pet_action` 作为回调函数传入页面。

答辩重点：

> 这里体现了模块化设计。页面类不在主控里实现，主控只负责装配和切换。

---

### 3.4 动作分发逻辑

核心代码摘录：

```python
def _play_pet_action(self, action_name, bubble=None):
    panel_visible = self.isVisible()
    self._pause_pet_overlay_sync(3200 if bubble else 1200)
    self.show_pet_window(activate=not panel_visible, sync_overlay=False)

    if action_name == "edge_left":
        self.pet_window.stick_to_edge("left")
    elif action_name == "edge_right":
        self.pet_window.stick_to_edge("right")
    else:
        self.pet_window.play_action(action_name)

    if bubble and self.store.settings.get("bubble_on", True):
        self.pet_window.show_bubble(bubble)
    self.pet_window.update()
```

代码逻辑：

1. 确保桌宠窗口显示。
2. 如果是贴边动作，调用 `stick_to_edge()`。
3. 普通动作调用 `play_action()`。
4. 如果有提示文字，显示桌宠气泡。
5. 最后刷新桌宠窗口。

答辩话术：

> 控制面板里的动作按钮不会直接操作动画帧，而是调用主控的 `_play_pet_action()`，再由主控调用 `pet` 模块。这样页面、主控、桌宠表现三层是分开的。

---

### 3.5 桌宠交互事件处理

核心代码摘录：

```python
def _handle_pet_window_interaction(self, action_name):
    if action_name == "pet_press":
        self._pause_pet_overlay_sync(1400)
        return

    if action_name.startswith("choice:"):
        self._handle_pet_choice(action_name.split(":", 1)[1])
        return

    if action_name == "quick_menu":
        self._show_pet_quick_menu()
        return

    if action_name == "show_panel":
        self._show_console()
        return

    if action_name == "hide_pet":
        self.hide_pet_window()
        return

    if action_name == "touch":
        self.store.touch()
        self._register_touch_burst()
        self._show_bubble("心情变好了")

    elif action_name in {"walk_left", "walk_right"}:
        self.store.walk()
        self._show_bubble("散步一小段")

    elif action_name == "sleep":
        self.store.rest()
        self._show_bubble("准备休息一下")
```

代码逻辑：

1. 桌宠窗口只发出动作名或事件名。
2. 主控模块根据事件名决定处理方式。
3. 有些事件打开菜单，有些事件修改数据，有些事件显示气泡。
4. 数据修改交给 `PetDataStore`。

答辩重点：

> 这里是典型的事件分发逻辑。桌宠窗口不直接改数据，而是把事件交给主控。主控再根据事件调用数据层。

---

### 3.6 快捷键注册逻辑

核心代码摘录：

```python
def _setup_pet_hotkeys(self):
    self._set_local_pet_shortcut(self._pet_hotkey_text)
    self._set_local_pet_corner_shortcut(self._pet_corner_hotkey_text)
    self._register_global_pet_hotkey()
    self._register_global_corner_hotkey()
    self._sync_hotkey_labels()
```

显示/隐藏快捷键：

```python
def _set_local_pet_shortcut(self, hotkey_text):
    if self._local_pet_shortcut is None:
        self._local_pet_shortcut = QShortcut(QKeySequence(hotkey_text), self)
        self._local_pet_shortcut.setContext(Qt.ApplicationShortcut)
        self._local_pet_shortcut.activated.connect(self.toggle_pet_window)
    else:
        self._local_pet_shortcut.setKey(QKeySequence(hotkey_text))
```

圆圈待机快捷键：

```python
def _set_local_pet_corner_shortcut(self, hotkey_text):
    if self._local_pet_corner_shortcut is None:
        self._local_pet_corner_shortcut = QShortcut(QKeySequence(hotkey_text), self)
        self._local_pet_corner_shortcut.setContext(Qt.ApplicationShortcut)
        self._local_pet_corner_shortcut.activated.connect(
            self.toggle_pet_corner_standby
        )
    else:
        self._local_pet_corner_shortcut.setKey(QKeySequence(hotkey_text))
```

答辩讲法：

> 项目中有两套快捷键：`Ctrl+Alt+B` 负责真正隐藏和召回，`Ctrl+Alt+M` 负责右下角圆圈待机和召回。它们是两个独立功能，所以代码里也分别注册。

---

### 3.7 Windows 全局快捷键处理

核心代码摘录：

```python
def nativeEvent(self, event_type, message):
    if sys.platform.startswith("win"):
        msg = wintypes.MSG.from_address(int(message))
        if msg and msg.message == WM_HOTKEY:
            hotkey_id = int(msg.wParam)
            if hotkey_id == PET_TOGGLE_HOTKEY_ID:
                self.toggle_pet_window()
                return True, 0
            if hotkey_id == PET_CORNER_HOTKEY_ID:
                self.toggle_pet_corner_standby()
                return True, 0
    return False, 0
```

代码逻辑：

1. Windows 全局快捷键触发后，会进入 `nativeEvent()`。
2. 通过 `hotkey_id` 判断是哪一个快捷键。
3. 调用对应的显示/隐藏或圆圈待机函数。

答辩重点：

> 这部分使得即使控制面板没有获得焦点，也可以通过快捷键控制桌宠。

---

### 3.8 圆圈待机逻辑

核心代码摘录：

```python
def toggle_pet_corner_standby(self):
    if self._pet_user_hidden and not self.pet_window.isVisible():
        self._cancel_pet_corner_animation()

    if getattr(self.pet_window, "_corner_hidden", False) or getattr(
        self.pet_window, "_is_corner_animating", lambda: False
    )():
        self.show_pet_window(restore=False, activate=False, sync_overlay=False)
        return

    if not self.pet_window.isVisible():
        self.show_pet_window(restore=True, activate=False, sync_overlay=False)

    self._pet_user_hidden = False
    self._pause_pet_overlay_sync(2600)
    self.pet_window.hide_choice_bubble()

    if not self.pet_window.hide_in_corner():
        self.pet_window._clear_bubble()
        self.pet_window.hide_in_corner()
```

代码逻辑：

1. 如果桌宠已经在角落或动画中，就召回。
2. 如果桌宠当前不可见，先显示。
3. 清理气泡和选择菜单。
4. 调用 `pet_window.hide_in_corner()` 进入右下角圆圈状态。

答辩重点：

> 这里区分了“隐藏”和“圆圈待机”。隐藏是桌宠完全不见；圆圈待机是收纳到右下角小圆点，方便快速召回。

---

## 4. 老师可能问的问题

### Q1：为什么要有 core 模块？

答：

> 因为项目功能比较多，如果所有逻辑都写在主窗口里，会非常混乱。`core` 只做启动、调度和事件分发，具体动画、数据、页面和服务分别交给其他模块。

### Q2：为什么用信号槽？

答：

> 因为这是 Qt 推荐的事件通信方式。桌宠窗口发生点击或拖拽时，只发出信号，主控模块决定如何处理，这样降低耦合。

### Q3：快捷键为什么分两套？

答：

> 因为隐藏和圆圈待机是两个不同概念。隐藏是完全不可见，圆圈待机是收纳状态。拆成两个快捷键更符合用户操作习惯。

---

## 5. 本模块总结

可以这样收尾：

> `core` 模块负责项目整体调度，是应用启动、页面组织、快捷键、托盘和桌宠事件分发的中心。通过它，其他四个模块被统一连接成一个完整桌宠系统。

