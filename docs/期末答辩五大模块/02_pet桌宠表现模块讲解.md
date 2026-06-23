# 02 pet 桌宠表现模块讲解

对应代码路径：

```text
src/pet/window.py
```

核心类：

```text
FrameAction
PolarBearPetWindow
```

## 一、模块作用

`pet` 模块负责“北极熊本体”在桌面上的显示、动画和鼠标交互。它是用户最直接看到的部分，也是整个项目最像桌宠的地方。

它主要完成这些事情：

- 创建透明、无边框、置顶的桌宠窗口。
- 加载北极熊 PNG 序列帧动作。
- 播放待机、眨眼、挥手、跳跃、睡觉、左右走、拖拽、贴边等动作。
- 处理单击、双击、拖拽、右键取消动作等鼠标事件。
- 显示聊天气泡和圆形功能选择气泡。
- 支持贴边吸附，让北极熊扒在屏幕边缘。
- 支持右下角圆点待机，让长时间未互动时桌宠收起来。
- 通过锚点对齐、末帧保持、计时器限幅减少瞬移、抖动和掉帧。

> 这个模块不是简单让一张图片移动，而是用真实序列帧驱动北极熊动作。每个动作都封装成一个 `FrameAction`，窗口通过 Qt 定时器切换当前帧，再由 `paintEvent()` 绘制到透明窗口上，所以用户看到的是一个悬浮在桌面的北极熊。

## 二、演示流程

### 1. 演示桌宠启动

演示步骤：

1. 启动程序。
2. 观察北极熊直接出现在桌面上，而不是嵌在控制面板里。
3. 拖动北极熊到任意位置。
4. 说明它是独立的透明悬浮窗口。

讲解重点：

> 北极熊桌宠窗口继承自 `QWidget`，但设置了无边框、置顶和透明背景，所以它看起来像直接站在桌面上。

### 2. 演示动作播放

建议演示：

- 待机/眨眼。
- 挥手。
- 向左走、向右走。
- 跳跃。
- 睡觉。
- 互动反应。

讲解重点：

> 动作播放由 `play_action()` 统一入口控制，真正的逐帧推进由 `_tick()` 完成。这样不管是控制面板按钮、点击桌宠、聊天触发动作，最后都会走同一套动画逻辑。

### 3. 演示鼠标交互

建议演示：

- 单击北极熊，弹出圆形功能气泡。
- 双击北极熊，触发挥手。
- 按住拖拽北极熊。
- 右键取消当前动作或气泡。

讲解重点：

> 这里专门区分了点击和拖拽。鼠标移动距离没有超过 Qt 的拖拽阈值时才算点击，超过以后才进入拖拽状态，避免拖拽时误触发菜单或动作。

### 4. 演示贴边和圆点待机

建议演示：

1. 把北极熊拖到屏幕边缘。
2. 看它切换到贴边动作。
3. 按圆点待机快捷键，北极熊变成右下角小圆点。
4. 拖动圆点或点击圆点召回北极熊。

讲解重点：

> 隐藏和圆点待机是两个不同状态。隐藏是真的看不见；圆点待机是把桌宠收成一个可以移动的小入口，方便快速召回。

## 三、核心代码讲解

下面代码是答辩时建议重点讲的部分。为方便讲解，代码片段保留真实类名、方法名和核心分支，省略了部分 UI 样式、重复绘制细节。

### 1. 动作数据结构：FrameAction

`FrameAction` 是每个动作的配置对象。它把“动作帧、播放间隔、是否循环、移动速度、播放结束后切到哪个动作”等参数放在一起。

```python
@dataclass
class FrameAction:
    name: str
    label: str
    frames: list[QPixmap]
    source_frames: list[QPixmap] = field(default_factory=list)
    frame_paths: list[Path] = field(default_factory=list)
    repeat: int = 1    //播放次数
    interval: int = 80   //每一帧播放间隔（播放速度）
    loop: bool = False    如：idel.loop = True
    move_x: float = 0.0    //当前移动速度
    base_move_x: float = 0.0    //基础移动速度
    next_action: str = "idle"
    next_frame_index: int = 0   //切换下一个动作从第几帧开始播放
    max_cycles: int = 0
    move_every_frames: int = 1     //每隔多少帧移动一次
```

讲解逻辑：

- `frames`：缩放后的 `QPixmap` 帧，用于实际绘制。
- `source_frames`：原始帧，缩放比例变化时可以重新生成清晰帧。
- `interval`：每隔多少毫秒切换一帧。
- `loop`：待机、睡觉这类动作可以循环；挥手、跳跃这类动作播放一次。
- `move_x`：走路动作每帧带来的水平移动量。
- `next_action`：非循环动作结束后回到什么动作，通常是 `idle`。

答辩话术：

> 这个结构让动作播放变成配置化。后续如果新增动作，只需要准备序列帧并添加一条配置，不需要重写播放逻辑。

### 2. 桌宠窗口初始化

`PolarBearPetWindow` 是真实桌宠窗口，初始化时会设置透明悬浮窗口、素材路径、动作状态、气泡状态、拖拽状态和定时器。

```python
class PolarBearPetWindow(QWidget):
    interaction_requested = Signal(str)   //发送信号

    def __init__(self):
        super().__init__()   //调用父类初始化，继承QWidget(基础窗口组件)
        self.setWindowTitle("北极熊桌宠")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)   //不让系统填充默认颜色

        self.asset_root = Path(__file__).resolve().parents[2] / "assets" / "polar_bear"
        self.role_root = self.asset_root / "role" / "PolarBear"
        self.real_action_root = self.asset_root / "real_actions"

        self._scale = self._load_pet_scale()     //加载桌宠的缩放比例
        self._configure_geometry()              //窗口的初始位置

        self._actions = {}
        self._action_name = "idle"
        self._frame_index = 0                  //当前动作播放到哪一帧
        self._elapsed = 0                      //时间
        self._move_x_remainder = 0.0

        self._corner_hidden = False           
        self._corner_dot_mode = False
        self._bubble_text = ""                 //保存气泡文字
        self._choice_options = []

        self._load_actions()
        self._timer = QTimer(self)            //设置定时器
        self._timer.timeout.connect(self._tick) 
        self._timer.start(16)
```

讲解逻辑：

- `Qt.FramelessWindowHint`：去掉系统边框。
- `Qt.WindowStaysOnTopHint`：让桌宠一直显示在上层。无论打开什么页面北极熊都能在页面之上
- `Qt.WA_TranslucentBackground`：背景透明，只画北极熊和气泡。
- `_actions` 保存全部动作。
- `_action_name` 和 `_frame_index` 表示当前播放到哪个动作、哪一帧。
- `_timer` 是动画驱动器，定时调用 `_tick()`。

答辩话术：

> 控制面板和桌宠本体不是一个窗口。控制面板是管理界面，`PolarBearPetWindow` 才是真正在桌面上显示和运动的窗口。
>
> 1. 创建一个北极熊桌宠窗口
> 2. 去掉窗口边框
> 3. 设置窗口一直置顶
> 4. 设置透明背景
> 5. 找到北极熊资源文件夹
> 6. 读取缩放比例
> 7. 设置窗口大小和位置
> 8. 初始化当前动作状态
> 9. 初始化隐藏状态、气泡文字、选项列表
> 10. 加载所有动作图片
> 11. 创建定时器
> 12. 每 16ms 调用一次 _tick()
> 13. _tick() 负责更新动画帧、移动位置、重绘桌宠

### 3. 动作加载逻辑

项目兼容两种素材方式：

1. 优先读取旧项目的 `pet_conf.json`、`act_conf.json` 和 `role/action` 目录。
2. 如果旧项目配置不存在，再读取当前项目自己的动作目录。

```python
def _load_actions(self):
    role_actions = self._load_old_project_role_actions()
    if role_actions:
        self._actions.update(role_actions)
        return

    configs = {
        "idle": {"interval": 90, "loop": True},
        "walk_right": {"interval": 70, "loop": False, "move_x": 4},
        "walk_left": {"interval": 70, "loop": False, "move_x": -4},
        "jump": {"interval": 70, "loop": False},
        "wave": {"interval": 85, "loop": False},
        "blink": {"interval": 50, "loop": False},
        "sleep": {"interval": 120, "loop": True},
        "drag": {"interval": 70, "loop": True},
        "touch": {"interval": 80, "loop": False},
    }

    for name, config in configs.items():
        frames = self._load_action_frames(name)
        if frames:
            self._actions[name] = FrameAction(
                name=name,
                label=ACTION_LABELS.get(name, name),
                frames=self._scale_frames(frames),
                source_frames=frames,
                interval=config["interval"],
                loop=config["loop"],
                move_x=config.get("move_x", 0),
            )
```

如果没有左走动作，但有右走动作，程序会自动镜像生成左走：

```python
if "walk_left" not in self._actions and "walk_right" in self._actions:
    source = self._actions["walk_right"]
    source_frames = source.source_frames or source.frames
    mirrored_frames = [
        frame.transformed(QTransform().scale(-1, 1))
        for frame in source_frames
    ]
    self._actions["walk_left"] = FrameAction(
        name="walk_left",
        label=ACTION_LABELS["walk_left"],
        frames=self._scale_frames(mirrored_frames),
        source_frames=mirrored_frames,
        interval=source.interval,
        loop=source.loop,
        move_x=-abs(source.move_x or 4.0),
    )
```

讲解逻辑：

- `_load_old_project_role_actions()` 是“向旧项目靠拢”的关键。
- `_scale_frames()` 会提前把图片转成当前缩放比例，减少播放时实时缩放导致的卡顿。
- 左走镜像可以节省素材，但如果有真实左走序列帧，会优先使用真实素材。

### 4. 旧项目动作配置读取

旧项目的动作配置通常会有动作名、图片前缀、帧数、刷新间隔、是否移动等字段。本项目把这些转换成统一的 `FrameAction`。

```python
def _load_old_project_role_actions(self):
    pet_conf_path = self.role_root / "pet_conf.json"
    act_conf_path = self.role_root / "act_conf.json"
    action_root = self.role_root / "action"
    if not pet_conf_path.exists() or not act_conf_path.exists() or not action_root.exists():
        return {}

    act_conf = json.loads(act_conf_path.read_text(encoding="utf-8-sig"))
    actions = {}
    for action_name, action_conf in act_conf.items():
        image_prefix = action_conf.get("images", action_name)
        frame_paths = self._prefixed_frame_paths(action_root, image_prefix)
        if not frame_paths:
            continue

        interval = int(float(action_conf.get("frame_refresh", 0.08)) * 1000)
        move_x = 0
        if action_conf.get("need_move"):
            direction = action_conf.get("direction")
            frame_move = float(action_conf.get("frame_move", 4))
            move_x = -frame_move if direction == "left" else frame_move

        actions[action_name] = FrameAction(
            name=action_name,
            label=ACTION_LABELS.get(action_name, action_name),
            frames=[],
            frame_paths=frame_paths,
            interval=max(16, interval),
            loop=bool(action_conf.get("loop")),
            move_x=move_x,
        )
    return actions
```

答辩话术：

> 我没有把旧项目的动作系统直接复制进来，而是把旧项目的动作配置转换成当前项目统一的 `FrameAction`。这样旧素材能用，新功能也能继续扩展。

### 5. 定时器驱动动画：_tick()

`_tick()` 是动画播放的心脏。它根据时间差推进帧，而不是假设每次定时器都刚好准时触发。

```python
def _tick(self):
    if not self.isVisible():
        self._clock.restart()
        return
    if self._is_dragging:
        self._clock.restart()
        return

    action = self._current_action()
    if not action or not action.frames:
        self._clock.restart()
        return

    delta_ms = min(48, max(1, self._clock.restart())) //self._clock.restart() 会返回距离上次调用经过了多少毫秒，然后重新开始计时
    self._elapsed += delta_ms

    if action.move_x:
        move_interval = max(1, action.interval) * max(1, action.move_every_frames)
        self._apply_action_move(action.move_x * delta_ms / move_interval)

    if self._elapsed >= action.interval:
        advanced = int(self._elapsed // action.interval)
        self._elapsed %= action.interval
        for _ in range(advanced):
            self._frame_index += 1
            if self._frame_index >= len(action.frames):
                if action.loop:
                    self._frame_index %= len(action.frames)
                    self._cycle_count += 1
                else:
                    if action.next_action == "idle" and self._start_return_transition(action.name):
                        return
                    self.play_action(action.next_action, transition=False)
                    return
//
    if self._action_name == "idle" and not self._autonomy_is_paused():
        self._next_corner_hide -= delta_ms
        self._next_roam_action -= delta_ms
        if self._next_corner_hide <= 0:
            self.hide_in_corner()
        elif self._next_roam_action <= 0:
            self._play_roam_action()

    self.update()
```

讲解逻辑：

- `delta_ms = min(48, ...)`：限制单次最大时间差，避免系统卡一下后动画突然跳很多帧。
- `self._elapsed`：累计时间，时间到了才切下一帧。
- `advanced`：如果某一帧延迟了，也能补帧推进，而不是永久慢半拍。
- `action.move_x`：走路动作会同时影响位置。
- 非循环动作结束后走 `next_action`，通常回到待机。
- 待机时会触发自主行为，例如随机走动、长时间未互动进入圆点待机。

答辩话术：

> 这里用了基于真实时间差的动画更新，而不是简单每次 timer 加一帧。这样即使电脑偶尔有卡顿，也能尽量保持动作节奏稳定。

### 6. 动作切换入口：play_action()

所有动作最终都通过 `play_action()` 播放。这个方法负责检查动作是否存在、是否正在拖拽、是否需要睡觉前置动作、是否需要回到待机过渡。

```python
def play_action(self, action_name, duration=None, transition=True, start_frame_index=0):
    if action_name not in self._actions:
        return
    if self._is_dragging and action_name != "idle":
        return

    anchor = self.visual_anchor_screen_point() if self.isVisible() else None

    if transition and action_name == "sleep" and "sleep_prepare" in self._actions:
        action_name = "sleep_prepare"

    action = self._ensure_action_loaded(action_name)
    if not action or not action.frames:
        return

    if transition and action_name == "idle" and self._action_name not in {"idle", "__transition__"}:
        if self._start_return_transition(self._action_name):
            return

    self._transition_action = None
    self._action_name = action_name
    self._sync_timer_interval(action)
    self._frame_index = self._start_frame_index(action_name, start_frame_index, action)
    self._cycle_count = 0
    self._walk_frame_count = 0
    self._move_x_remainder = 0.0

    if hasattr(self, "_clock"):
        self._clock.restart()
    if anchor is not None:
        self.align_visual_anchor_inside_window(anchor)
    self.update()
```

讲解逻辑：

- `if self._is_dragging`：拖拽时不允许被其他动作打断。
- `sleep_prepare`：睡觉前先进入准备睡觉动作，避免直接躺下很突兀。
- `transition=True`：动作回待机时可以走过渡帧，而不是瞬间切回。
- `anchor`：动作切换前记录北极熊视觉锚点，切换后重新对齐，减少瞬移。
- `_clock.restart()`：切换动作时重置计时器，避免第一帧因为上一个动作的残留时间被跳过。

答辩话术：

> 之前动作切换会出现瞬移和抖动，核心原因是不同动作帧的边界盒不一样。这里通过锚点对齐和回待机过渡，让视觉中心尽量保持一致。

### 7. 当前帧获取：解决末帧跳回问题

非循环动作如果播放完立刻取模回第 0 帧，会出现“动作结束瞬间闪一下”。所以当前帧获取里做了循环和非循环的区别。

```python
def _current_frame(self):
    if self._is_dragging and self._drag_hold_frame and not self._drag_hold_frame.isNull():
        return self._drag_hold_frame

    action = self._current_action()
    if not action or not action.frames:
        return None

    if action.loop:
        index = self._frame_index % len(action.frames)
    else:
        index = max(0, min(self._frame_index, len(action.frames) - 1))
    return action.frames[index]
```

讲解逻辑：

- 循环动作可以 `% len(frames)`。
- 非循环动作必须锁在最后一帧，不能回到第 0 帧。
- 拖拽时使用 `_drag_hold_frame`，让拖拽过程不因为动画切换出现穿帮。

答辩话术：

> 这是解决动作结束抖动的关键点之一。非循环动作结束时保持最后一帧，再交给过渡逻辑回待机，视觉上会自然很多。

### 8. 绘制逻辑：paintEvent()

`paintEvent()` 负责真正把北极熊和气泡画出来。

```python
def paintEvent(self, event):
    painter = QPainter(self)
    painter.setCompositionMode(QPainter.CompositionMode_Source)
    painter.fillRect(self.rect(), Qt.transparent)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    painter.setRenderHint(QPainter.Antialiasing)

    if self._corner_dot_mode:
        self._draw_corner_dot(painter)
        return

    content_left = self._walk_visual_padding + round(
        self._walk_visual_offset_x + self._pose_visual_offset.x()
    )

    if not self._is_edge_action():
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 82))
        painter.drawEllipse(...)

    frame = self._current_frame()
    if frame:
        self._draw_frame(painter, frame)
    else:
        self._draw_static_hint(painter)

    if self._choice_options:
        self._draw_choice_bubble(painter, content_left)
        return
    if self._bubble_text:
        self._draw_bubble(painter, content_left)
```

讲解逻辑：

- 先清空成透明背景。
- 如果是圆点待机，直接画圆点，不画北极熊。
- 普通状态下先画影子，再画当前动作帧。
- 有功能选择时画圆形选择气泡。
- 有聊天内容时画聊天气泡。

答辩话术：

> 这个方法每次动画刷新都会执行。桌宠窗口自身没有背景，真正显示出来的是当前动作帧和气泡，因此能做到悬浮桌面效果。

### 9. 鼠标事件：点击、拖拽和气泡选择

鼠标按下时记录位置，并根据状态决定是点圆点、点气泡、取消动作还是准备拖拽。

```python
def mousePressEvent(self, event):
    if self._corner_dot_mode and event.button() == Qt.LeftButton:
        self.interaction_requested.emit("pet_press")
        self._press_position = event.globalPosition().toPoint()
        self._drag_position = self._press_position - self.frameGeometry().topLeft()
        self._is_dragging = False
        event.accept()
        return

    if event.button() == Qt.RightButton and (self._choice_options or self._bubble_text):
        self.hide_choice_bubble()
        self._clear_bubble()
        if self._action_name not in {"idle", "__transition__"}:
            self.play_action("idle", transition=False)
        event.accept()
        return

    if event.button() == Qt.LeftButton:
        self.interaction_requested.emit("pet_press")
        self._press_position = event.globalPosition().toPoint()
        self._drag_position = self._press_position - self.frameGeometry().topLeft()
        self._is_dragging = False
        event.accept()
```

鼠标移动时，如果超过系统拖拽阈值，才进入拖拽：

```python
def mouseMoveEvent(self, event):
    if event.buttons() & Qt.LeftButton:
        current_position = event.globalPosition().toPoint()
        if not self._is_dragging:
            if (current_position - self._press_position).manhattanLength() < QApplication.startDragDistance():
                event.accept()
                return
            self._is_dragging = True
            self._begin_drag_hold()
            self.interaction_requested.emit("drag")
        self.move(current_position - self._drag_position)
        event.accept()
```

松开鼠标时，根据是否拖拽、是否点到功能气泡，决定触发什么行为：

```python
def mouseReleaseEvent(self, event):
    if event.button() == Qt.LeftButton:
        if self._choice_options:
            key = self._choice_key_at(event.position()) if self._choice_pressing else ""
            if key:
                self.hide_choice_bubble()
                self.interaction_requested.emit(f"choice:{key}")
            event.accept()
            return

        if self._is_dragging:
            self._is_dragging = False
            self._drag_hold_frame = None
            self.interaction_requested.emit("drag_end")
        else:
            self.interaction_requested.emit("pet_click")
```

讲解逻辑：

- `mousePressEvent()` 只做准备，不马上触发普通点击。
- `mouseMoveEvent()` 判断是否进入拖拽。
- `mouseReleaseEvent()` 才最终决定是点击、拖拽结束还是功能选择。

答辩话术：

> 这样可以避免两个点击事件一起触发。例如用户想拖动北极熊时，不会同时触发聊天、喂食或挥手。

### 10. 圆点待机和召回

圆点待机用于长时间不互动时降低干扰，也可以通过快捷键主动进入。

```python
def hide_in_corner(self):
    if self._corner_hidden:
        return
    self._corner_hidden = True
    self._corner_dot_mode = True
    self._action_name = "idle"
    self._frame_index = 0
    self.resize(self._corner_dot_size, self._corner_dot_size)
    self.move(self._corner_dot_position())
    self.show()
    self.update()

def reveal_from_corner(self):
    if not self._corner_hidden:
        return
    self._corner_hidden = False
    self._corner_dot_mode = False
    self._configure_geometry()
    self.play_action("idle", transition=False)
    self.show()
```

讲解逻辑：

- `_corner_hidden` 表示处于收起状态。
- `_corner_dot_mode` 表示绘制模式切换为圆点。
- 圆点仍然是同一个窗口，所以可以拖动和点击召回。
- 召回后重新配置桌宠窗口尺寸并回到待机。

答辩话术：

> 这个功能和普通隐藏不同。普通隐藏是窗口不可见，圆点待机是把桌宠缩成一个可互动入口，提升桌面使用体验。

## 四、这个模块解决过的关键问题

### 1. 解决“动作像图片平移”的问题

解决方式：

- 使用真实 PNG 序列帧。
- 每个动作单独加载帧。
- `_tick()` 按帧推进。
- `paintEvent()` 绘制当前帧。

### 2. 解决“动作结束瞬移”的问题

解决方式：

- 切动作前记录视觉锚点。
- 切动作后调用 `align_visual_anchor_inside_window()` 对齐。
- 非循环动作结束时保持最后一帧。
- 回待机时使用过渡动作，不直接跳回。

### 3. 解决“拖拽穿帮”的问题

解决方式：

- 拖拽开始时保存当前帧 `_drag_hold_frame`。
- 拖拽过程中不继续推进动作帧。
- 鼠标释放后再恢复正常动作。

### 4. 解决“点击和拖拽冲突”的问题

解决方式：

- 鼠标按下只记录位置。
- 移动距离超过 `QApplication.startDragDistance()` 才算拖拽。
- 松开时再判断普通点击或拖拽结束。

### 5. 解决“待机太单调”的问题

解决方式：

- 待机动作保持轻微眨眼。
- `_tick()` 中加入随机自主行为。
- 长时间未互动自动进入圆点待机。
- 用户点击圆点或快捷键可召回。

## 五、老师可能追问

### 问：为什么不用视频直接播放？

答：

> 因为桌宠需要透明背景、鼠标穿透感、动作可中断、可拖拽、可贴边、可根据状态切换动作。视频播放不适合频繁中断和透明悬浮窗口控制，所以我使用 PNG 序列帧，更容易和 Qt 绘制、交互事件结合。

### 问：为什么动作切换会出现卡顿或瞬移？

答：

> 不同动作帧的透明区域和主体位置不完全一致。如果直接从一个动作第一帧切到另一个动作第一帧，视觉中心会变，所以看起来像瞬移。项目里通过视觉锚点对齐、末帧保持和回待机过渡来减少这个问题。

### 问：为什么要有 `FrameAction`？

答：

> 如果没有这个结构，每个动作都要写一套播放逻辑。封装成 `FrameAction` 后，动作名、帧列表、间隔、循环、移动量都统一管理，新增动作更方便。

### 问：桌宠窗口为什么能透明悬浮？

答：

> 主要靠 Qt 的窗口标志和属性：`FramelessWindowHint` 去掉边框，`WindowStaysOnTopHint` 置顶，`WA_TranslucentBackground` 开启透明背景，然后在 `paintEvent()` 里只绘制北极熊和气泡。

## 六、答辩总结

可以这样收尾：

> `pet` 模块是项目的视觉交互核心。它用透明悬浮窗口加真实 PNG 序列帧实现北极熊桌宠，通过 `FrameAction` 管理动作，通过 `_tick()` 推进动画，通过鼠标事件处理拖拽、点击和气泡选择，并加入贴边、圆点待机、动作过渡等细节，让桌宠从“图片展示”变成真正可互动的桌面宠物。
