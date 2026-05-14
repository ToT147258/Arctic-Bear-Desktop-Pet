import json
import math
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QElapsedTimer, QTimer, Signal
from PySide6.QtGui import QColor, QImageReader, QPainter, QPen, QPixmap, QTransform
from PySide6.QtWidgets import QApplication, QMenu, QWidget


ACTION_LABELS = {
    "idle": "待机",
    "walk_left": "向左走",
    "walk_right": "向右走",
    "jump": "跳跃",
    "wave": "挥手",
    "blink": "眨眼",
    "sleep": "睡觉",
    "sleep_prepare": "准备睡觉",
    "drag": "拖拽",
    "touch": "互动",
}


@dataclass
class FrameAction:
    name: str
    label: str
    frames: list[QPixmap]
    source_frames: list[QPixmap] = field(default_factory=list)
    interval: int = 80
    loop: bool = False
    move_x: float = 0.0
    base_move_x: float = 0.0
    next_action: str = "idle"
    next_frame_index: int = 0
    max_cycles: int = 0
    move_every_frames: int = 1


def natural_key(path):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", Path(path).stem)]


class PolarBearPetWindow(QWidget):
    """严格真实序列帧桌宠窗口。

    这里只播放真实 GIF/WebP/PNG 序列帧。没有逐帧素材时只显示高清静态图，
    不再用单张图片位移、旋转、缩放来伪装动画。
    """

    interaction_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("北极熊桌宠")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        self.asset_root = Path(__file__).resolve().parents[1] / "assets" / "polar_bear"
        self.role_root = self.asset_root / "role" / "PolarBear"
        self.real_action_root = self.asset_root / "real_actions"
        self.pet_conf_path = self.role_root / "pet_conf.json"
        self._base_window_size = (420, 600)
        self._base_draw_rect = QRectF(30, 60, 360, 520)
        self._walk_visual_padding = 0
        self._content_width = 0
        self._content_height = 0
        self._scale = self._load_pet_scale()
        self._walk_window_move = self._load_walk_window_move()
        self._configure_geometry()

        self._drag_position = QPoint()
        self._press_position = QPoint()
        self._is_dragging = False
        self._click_action_token = 0
        self._ignore_next_click_release = False
        self._click_action_delay = 0
        self._actions = {}
        self._transition_action = None
        self._return_transitions = {}
        self._action_name = "idle"
        self._frame_index = 0
        self._cycle_count = 0
        self._walk_frame_count = 0
        self._elapsed = 0
        self._move_x_remainder = 0.0
        self._walk_visual_offset_x = 0.0
        self._screen_area_cache = None
        self._next_random_action = self._random_idle_delay()
        self._idle_events_until_sleep = random.randint(2, 4)
        self._bubble_text = ""
        self._edge_snap_enabled = True
        self._edge_snap_threshold = 48

        self._fallback_source_pixmap = QPixmap(str(self.asset_root / "polar-bear-realistic.png"))
        self.fallback_pixmap = self._scale_pixmap(self._fallback_source_pixmap)
        self._load_actions()
        self._rebuild_return_transitions()
        self._warm_frame_cache()

        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(10)

    @property
    def mood(self):
        action = self._current_action()
        if action:
            return action.label
        return "缺少真实动画帧"

    @property
    def scale_percent(self):
        return int(round(self._scale * 100))

    def _read_pet_conf(self):
        try:
            if self.pet_conf_path.exists():
                return json.loads(self.pet_conf_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, TypeError):
            return {}
        return {}

    def _load_pet_scale(self):
        pet_conf = self._read_pet_conf()
        return self._clamp_scale(pet_conf.get("scale", 0.5))

    def _load_walk_window_move(self):
        pet_conf = self._read_pet_conf()
        return bool(pet_conf.get("walk_window_move", True))

    def _save_pet_scale(self):
        pet_conf = self._read_pet_conf()
        pet_conf["scale"] = self._scale
        self.pet_conf_path.write_text(json.dumps(pet_conf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _save_walk_window_move(self):
        pet_conf = self._read_pet_conf()
        pet_conf["walk_window_move"] = self._walk_window_move
        self.pet_conf_path.write_text(json.dumps(pet_conf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def set_walk_window_move(self, enabled):
        if not enabled:
            self._commit_walk_visual_offset(force=True)
        self._walk_window_move = bool(enabled)
        for name, action in self._actions.items():
            if name == "walk_left":
                action.move_x = -float(action.base_move_x or 2.0) if self._walk_window_move else 0.0
            elif name == "walk_right":
                action.move_x = float(action.base_move_x or 2.0) if self._walk_window_move else 0.0
        self._save_walk_window_move()

    def set_always_on_top(self, enabled):
        visible = self.isVisible()
        flags = Qt.FramelessWindowHint | Qt.Tool
        if enabled:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        if visible:
            self.show()
            self.raise_()

    def set_edge_snap(self, enabled, threshold=None):
        self._edge_snap_enabled = bool(enabled)
        if threshold is not None:
            self._edge_snap_threshold = max(8, int(threshold))

    def show_bubble(self, text, duration=2400):
        self._bubble_text = str(text)
        self.update()
        QTimer.singleShot(duration, self._clear_bubble)

    def _clear_bubble(self):
        if self._bubble_text:
            self._bubble_text = ""
            self.update()

    def _clamp_scale(self, value):
        try:
            scale = float(value)
        except (TypeError, ValueError):
            scale = 0.5
        return max(0.4, min(1.0, round(scale, 2)))

    def _configure_geometry(self):
        base_width, base_height = self._base_window_size
        self._content_width = round(base_width * self._scale)
        self._content_height = round(base_height * self._scale)
        self._walk_visual_padding = max(180, round(260 * self._scale))
        self.setFixedSize(self._content_width + self._walk_visual_padding * 2, self._content_height)
        self._pet_draw_rect = QRectF(
            self._walk_visual_padding + round(self._base_draw_rect.x() * self._scale),
            round(self._base_draw_rect.y() * self._scale),
            round(self._base_draw_rect.width() * self._scale),
            round(self._base_draw_rect.height() * self._scale),
        )
        self._pet_draw_center = self._pet_draw_rect.center()

    def set_pet_scale(self, scale, persist=True):
        next_scale = self._clamp_scale(scale)
        if abs(next_scale - self._scale) < 0.001:
            return

        self._commit_walk_visual_offset(force=True)
        self._walk_visual_offset_x = 0.0
        old_center = self.frameGeometry().center()
        self._scale = next_scale
        self._configure_geometry()
        self._screen_area_cache = None
        self._rescale_pixmaps()
        self.move(old_center - QPoint(self.width() // 2, self.height() // 2))
        self._move_within_screen(0, 0)
        if persist:
            self._save_pet_scale()
        self.update()

    def _rescale_pixmaps(self):
        self.fallback_pixmap = self._scale_pixmap(self._fallback_source_pixmap)
        for action in self._actions.values():
            source_frames = action.source_frames or action.frames
            action.frames = self._scale_frames(source_frames)
        self._rebuild_return_transitions()
        self._warm_frame_cache()
        current_action = self._current_action()
        if current_action and current_action.frames:
            self._frame_index %= len(current_action.frames)
        else:
            self._frame_index = 0

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

        if "walk_left" not in self._actions and "walk_right" in self._actions:
            source = self._actions["walk_right"]
            source_frames = source.source_frames or source.frames
            mirrored_frames = [frame.transformed(QTransform().scale(-1, 1)) for frame in source_frames]
            self._actions["walk_left"] = FrameAction(
                name="walk_left",
                label=ACTION_LABELS["walk_left"],
                frames=self._scale_frames(mirrored_frames),
                source_frames=mirrored_frames,
                interval=source.interval,
                loop=source.loop,
                move_x=-abs(source.move_x or 4.0),
            )

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
            source_frames = self._load_prefixed_frames(action_root, image_prefix)
            if not source_frames:
                continue
            source_frames = source_frames * int(action_conf.get("act_num", 1))
            interval = int(float(action_conf.get("frame_refresh", 0.08)) * 1000)
            move_x = 0
            if action_conf.get("need_move"):
                direction = action_conf.get("direction")
                frame_move = float(action_conf.get("frame_move", 4))
                if direction == "left":
                    move_x = -frame_move
                elif direction == "right":
                    move_x = frame_move
            if action_name in {"left_walk", "right_walk"} and not self._walk_window_move:
                move_x = 0
            actions[action_name] = FrameAction(
                name=action_name,
                label=ACTION_LABELS.get(action_name, action_name),
                frames=self._scale_frames(source_frames),
                source_frames=source_frames,
                interval=interval,
                loop=bool(action_conf.get("loop", action_name == "default")),
                move_x=move_x,
                base_move_x=abs(float(action_conf.get("frame_move", 0))),
                next_action=action_conf.get("next_action", "idle"),
                max_cycles=int(action_conf.get("max_cycles", 0)),
                move_every_frames=int(action_conf.get("move_every_frames", 1)),
            )

        name_map = {
            "default": "idle",
            "left_walk": "walk_left",
            "right_walk": "walk_right",
            "jump": "jump",
            "wave": "wave",
            "blink": "blink",
            "sleep": "sleep",
            "sleep_prepare": "sleep_prepare",
            "drag": "drag",
            "touch": "touch",
        }
        normalized = {}
        for source_name, target_name in name_map.items():
            if source_name in actions:
                action = actions[source_name]
                action.name = target_name
                action.label = ACTION_LABELS.get(target_name, action.label)
                normalized[target_name] = action
        return normalized

    def _load_prefixed_frames(self, action_root, image_prefix):
        frame_pattern = re.compile(rf"^{re.escape(image_prefix)}_(\d+)\.png$", re.IGNORECASE)
        files = []
        for file in action_root.iterdir():
            match = frame_pattern.match(file.name)
            if match:
                files.append((int(match.group(1)), file))
        files = [file for _, file in sorted(files)]
        frames = []
        for file in files:
            pixmap = QPixmap(str(file))
            if not pixmap.isNull():
                frames.append(pixmap)
        return frames

    def _load_action_frames(self, action_name):
        for suffix in ("gif", "webp"):
            media = self.real_action_root / f"{action_name}.{suffix}"
            if media.exists():
                frames = self._read_animated_image(media)
                if frames:
                    return frames

        frame_dir = self.real_action_root / action_name
        if not frame_dir.exists():
            return []

        files = []
        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            files.extend(frame_dir.glob(pattern))
        files = sorted(files, key=natural_key)

        frames = []
        for file in files:
            pixmap = QPixmap(str(file))
            if not pixmap.isNull():
                frames.append(pixmap)
        return frames

    def _read_animated_image(self, media_path):
        reader = QImageReader(str(media_path))
        frames = []
        while True:
            image = reader.read()
            if image.isNull():
                break
            frames.append(QPixmap.fromImage(image))
            if not reader.supportsAnimation():
                break
        return frames

    def _scale_pixmap(self, pixmap):
        if pixmap.isNull():
            return pixmap
        logical_size = self._pet_draw_rect.size().toSize()
        dpr = max(1.0, self.devicePixelRatioF())
        target_size = QSize(max(1, round(logical_size.width() * dpr)), max(1, round(logical_size.height() * dpr)))
        if pixmap.size() == target_size and abs(pixmap.devicePixelRatio() - dpr) < 0.01:
            return pixmap
        scaled = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled.setDevicePixelRatio(dpr)
        return scaled

    def _scale_frames(self, frames):
        return [self._scale_pixmap(frame) for frame in frames]

    def _warm_frame_cache(self):
        warm_frames = []
        for action in self._actions.values():
            warm_frames.extend(action.frames)
        if self._transition_action:
            warm_frames.extend(self._transition_action.frames)

        scratch = QPixmap()
        painter = None
        last_size = None
        last_dpr = 1.0
        for frame in warm_frames:
            if frame.isNull():
                continue
            size = frame.size()
            dpr = frame.devicePixelRatio()
            if size != last_size or abs(dpr - last_dpr) > 0.01:
                if painter:
                    painter.end()
                scratch = QPixmap(size)
                scratch.setDevicePixelRatio(dpr)
                scratch.fill(Qt.transparent)
                painter = QPainter(scratch)
                last_size = size
                last_dpr = dpr
            else:
                painter.setCompositionMode(QPainter.CompositionMode_Source)
                painter.fillRect(scratch.rect(), Qt.transparent)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, frame)
        if painter:
            painter.end()

    def _random_idle_delay(self):
        return random.randint(30000, 50000)

    def _tick(self):
        action = self._current_action()
        if not action:
            self.update()
            return

        delta_ms = min(80, max(1, self._clock.restart()))
        self._elapsed += delta_ms
        should_update = False

        if action.move_x:
            move_interval = max(1, action.interval) * max(1, action.move_every_frames)
            self._apply_action_move(action.move_x * delta_ms / move_interval)
            should_update = True

        if self._elapsed >= action.interval:
            advanced = int(self._elapsed // action.interval)
            self._elapsed %= action.interval
            for _ in range(advanced):
                self._frame_index += 1
                if self._frame_index >= len(action.frames):
                    if action.loop:
                        self._frame_index %= len(action.frames)
                        self._cycle_count += 1
                        if action.max_cycles and self._cycle_count >= action.max_cycles:
                            if action.next_action == "idle" and self._start_return_transition(action.name):
                                return
                            self.play_action(action.next_action, transition=False)
                            return
                    else:
                        if self._action_name == "__transition__":
                            self.play_action(action.next_action, transition=False, start_frame_index=action.next_frame_index)
                        else:
                            if action.next_action == "idle" and self._start_return_transition(action.name):
                                return
                            self.play_action(action.next_action, transition=False)
                        return
            should_update = True

        if self._action_name == "idle":
            self._next_random_action -= delta_ms
            if self._next_random_action <= 0:
                self._play_random_action()
                return

        if should_update:
            self.update()

    def _current_action(self):
        if self._action_name == "__transition__":
            return self._transition_action
        return self._actions.get(self._action_name) or self._actions.get("idle")

    def _start_frame_index(self, action_name, requested_index, action):
        if requested_index:
            return requested_index % len(action.frames) if action.frames else 0
        start_frames = {
            "walk_left": 1,
            "walk_right": 1,
            "wave": 1,
            "jump": 1,
            "touch": 4,
            "drag": 1,
            "sleep_prepare": 1,
        }
        return min(start_frames.get(action_name, 0), max(0, len(action.frames) - 1))

    def _prime_action_timing(self, action_name, action):
        if action_name == "idle" or not action or len(action.frames) < 2:
            self._elapsed = 0
            return
        self._elapsed = max(0, action.interval - 16)

    def _apply_action_move(self, dx):
        if not dx:
            return
        if self._action_name in {"walk_left", "walk_right"} and self._walk_window_move:
            self._walk_visual_offset_x += dx
            if abs(self._walk_visual_offset_x) > self._walk_visual_safe_offset():
                self._commit_walk_visual_offset(force=True)
            return

        self._move_x_remainder += dx
        move_x = math.trunc(self._move_x_remainder)
        self._move_x_remainder -= move_x
        if move_x:
            self._move_within_screen(move_x, 0)

    def _commit_walk_visual_offset(self, force=False):
        if abs(getattr(self, "_walk_visual_offset_x", 0.0)) < 0.001:
            return
        if not force:
            return

        commit_x = round(self._walk_visual_offset_x)
        if not commit_x:
            if force:
                self._walk_visual_offset_x = 0.0
            return

        moved_x = self._move_within_screen(commit_x, 0, turn_on_edge=not force)
        if moved_x:
            self._walk_visual_offset_x -= moved_x
        if force or not moved_x:
            self._walk_visual_offset_x = 0.0

    def _play_random_action(self):
        self._idle_events_until_sleep -= 1
        if self._idle_events_until_sleep <= 0 and "sleep" in self._actions:
            self.play_action("sleep")
            self._idle_events_until_sleep = random.randint(2, 4)
            self._next_random_action = self._random_idle_delay()
            return

        self._next_random_action = self._random_idle_delay()

    def _blend_pixmaps(self, left, right, ratio):
        blended = QPixmap(left.size())
        blended.setDevicePixelRatio(left.devicePixelRatio())
        blended.fill(Qt.transparent)
        painter = QPainter(blended)
        painter.drawPixmap(0, 0, left)
        painter.setOpacity(ratio)
        painter.drawPixmap(0, 0, right)
        painter.end()
        return blended

    def _step_frames(self, frames, start, count):
        if not frames:
            return []
        return [frames[(start + offset) % len(frames)] for offset in range(count)]

    def _idle_return_frame_hint(self, source_action_name):
        hints = {
            "walk_left": 47,
            "walk_right": 13,
            "wave": 17,
            "jump": 48,
            "touch": 13,
            "sleep": 51,
            "sleep_prepare": 51,
            "drag": 55,
        }
        return hints.get(source_action_name, 0)

    def _walk_visual_safe_offset(self):
        return max(24, self._walk_visual_padding - round(18 * self._scale))

    def _ensure_walk_headroom(self, action_name):
        action = self._actions.get(action_name)
        if not action or not action.move_x or not self._walk_window_move:
            return
        expected_move = action.move_x * len(action.frames) / max(1, action.move_every_frames)
        if abs(self._walk_visual_offset_x + expected_move) > self._walk_visual_safe_offset():
            self._commit_walk_visual_offset(force=True)

    def _rebuild_return_transitions(self):
        self._return_transitions = {}
        idle = self._actions.get("idle")
        if not idle or not idle.frames:
            return

        for source_name, source_action in self._actions.items():
            if source_name in {"idle", "blink", "sleep_prepare"} or not source_action.frames:
                continue
            target_frame_index = self._idle_return_frame_hint(source_name) % len(idle.frames)
            frames = self._step_frames(idle.frames, target_frame_index, 7)
            self._return_transitions[source_name] = FrameAction(
                name="__transition__",
                label=idle.label,
                frames=frames,
                interval=40,
                loop=False,
                next_action="idle",
                next_frame_index=(target_frame_index + 6) % len(idle.frames),
            )

    def _start_return_transition(self, source_action_name):
        transition = self._return_transitions.get(source_action_name)
        if not transition:
            return False
        self._transition_action = transition
        self._action_name = "__transition__"
        self._frame_index = 1 if len(transition.frames) > 1 else 0
        self._cycle_count = 0
        self._walk_frame_count = 0
        self._elapsed = max(0, transition.interval - 16)
        self._move_x_remainder = 0.0
        if hasattr(self, "_clock"):
            self._clock.restart()
        self.update()
        return True

    def play_action(self, action_name, duration=None, transition=True, start_frame_index=0):
        if action_name not in self._actions:
            return
        if transition and action_name == "sleep" and "sleep_prepare" in self._actions:
            action_name = "sleep_prepare"
        if transition and action_name == "idle" and self._action_name not in {"idle", "__transition__"}:
            if self._start_return_transition(self._action_name):
                return
        if action_name in {"walk_left", "walk_right"}:
            self._ensure_walk_headroom(action_name)
        self._transition_action = None
        self._action_name = action_name
        action = self._actions[action_name]
        self._frame_index = self._start_frame_index(action_name, start_frame_index, action)
        self._cycle_count = 0
        self._walk_frame_count = 0
        self._move_x_remainder = 0.0
        self._prime_action_timing(action_name, action)
        if hasattr(self, "_clock"):
            self._clock.restart()
        self.update()

    def _available_screen_area(self):
        center = self.frameGeometry().center()
        if self._screen_area_cache is None or not self._screen_area_cache.adjusted(-80, -80, 80, 80).contains(center):
            screen = QApplication.screenAt(center) or QApplication.primaryScreen()
            self._screen_area_cache = screen.availableGeometry() if screen else None
        return self._screen_area_cache

    def _turn_walk_direction(self):
        if self._action_name == "walk_left":
            next_name = "walk_right"
        elif self._action_name == "walk_right":
            next_name = "walk_left"
        else:
            return False

        current_action = self._current_action()
        next_action = self._actions.get(next_name)
        if not current_action or not next_action or not next_action.frames:
            return False

        progress = self._frame_index / max(1, len(current_action.frames))
        self._action_name = next_name
        self._frame_index = min(len(next_action.frames) - 1, int(progress * len(next_action.frames)))
        self._elapsed = min(self._elapsed, max(0, next_action.interval - 1))
        self._walk_frame_count = 0
        self._move_x_remainder = 0.0
        self._walk_visual_offset_x = 0.0
        self.update()
        return True

    def _snap_to_screen_edge(self):
        if not self._edge_snap_enabled:
            return
        area = self._available_screen_area()
        if not area:
            return
        threshold = max(8, int(self._edge_snap_threshold))
        next_x = self.x()
        next_y = self.y()

        if abs(self.x() - area.left()) <= threshold:
            next_x = area.left()
        elif abs((area.right() - self.width()) - self.x()) <= threshold:
            next_x = area.right() - self.width()

        if abs(self.y() - area.top()) <= threshold:
            next_y = area.top()
        elif abs((area.bottom() - self.height()) - self.y()) <= threshold:
            next_y = area.bottom() - self.height()

        if next_x != self.x() or next_y != self.y():
            self.move(next_x, next_y)

    def _move_within_screen(self, dx, dy, turn_on_edge=True):
        area = self._available_screen_area()
        if not area:
            self.move(self.x() + dx, self.y() + dy)
            return dx
        old_x = self.x()
        next_x = max(area.left(), min(self.x() + dx, area.right() - self.width()))
        next_y = max(area.top(), min(self.y() + dy, area.bottom() - self.height()))
        hit_horizontal_edge = dx and next_x in (area.left(), area.right() - self.width())
        if turn_on_edge and hit_horizontal_edge and self._action_name in {"walk_left", "walk_right"}:
            self._walk_visual_offset_x = 0.0
            self._turn_walk_direction()
            return 0
        self.move(next_x, next_y)
        return next_x - old_x

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._click_action_token += 1
            self._press_position = event.globalPosition().toPoint()
            self._drag_position = self._press_position - self.frameGeometry().topLeft()
            self._is_dragging = False
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            current_position = event.globalPosition().toPoint()
            if not self._is_dragging:
                if (current_position - self._press_position).manhattanLength() < QApplication.startDragDistance():
                    event.accept()
                    return
                self._is_dragging = True
                self._click_action_token += 1
                self.play_action("drag")
                self.interaction_requested.emit("drag")
            self.move(current_position - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._is_dragging:
                self._is_dragging = False
                self._click_action_token += 1
                self._snap_to_screen_edge()
                self.play_action("idle")
                self.interaction_requested.emit("drag_end")
            elif self._ignore_next_click_release:
                self._ignore_next_click_release = False
                self._click_action_token += 1
            else:
                self._schedule_click_action()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        self._click_action_token += 1
        self._ignore_next_click_release = True
        self.play_action("wave")
        self.interaction_requested.emit("wave")
        event.accept()

    def _schedule_click_action(self):
        self._click_action_token += 1
        token = self._click_action_token
        if self._click_action_delay <= 0:
            self._play_click_action(token)
        else:
            QTimer.singleShot(self._click_action_delay, lambda: self._play_click_action(token))

    def _play_click_action(self, token):
        if token != self._click_action_token or self._is_dragging:
            return
        self.play_action("touch" if "touch" in self._actions else "wave", transition=False)
        self.interaction_requested.emit("touch" if "touch" in self._actions else "wave")

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            step = 0.05 if event.angleDelta().y() > 0 else -0.05
            self.set_pet_scale(self._scale + step)
            event.accept()
            return
        super().wheelEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        scale_menu = menu.addMenu(f"缩放比例：{self.scale_percent}%")
        for scale in (0.4, 0.5, 0.6, 0.75, 0.9, 1.0):
            action = scale_menu.addAction(f"{int(scale * 100)}%")
            action.setCheckable(True)
            action.setChecked(abs(self._scale - scale) < 0.01)
            action.triggered.connect(lambda checked=False, value=scale: self.set_pet_scale(value))
        menu.addSeparator()
        walk_move_action = menu.addAction("走路时移动窗口")
        walk_move_action.setCheckable(True)
        walk_move_action.setChecked(self._walk_window_move)
        walk_move_action.triggered.connect(lambda checked=False: self.set_walk_window_move(checked))
        menu.addSeparator()
        for action_name in ("idle", "blink", "touch", "walk_left", "walk_right", "jump", "wave", "sleep"):
            if action_name not in self._actions:
                continue
            action = menu.addAction(ACTION_LABELS.get(action_name, action_name))
            action.triggered.connect(lambda checked=False, name=action_name: self._play_menu_action(name))
        menu.exec(event.globalPos())

    def _play_menu_action(self, action_name):
        self.play_action(action_name)
        self.interaction_requested.emit(action_name)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.Antialiasing)
        scale = self._scale
        content_left = self._walk_visual_padding + round(self._walk_visual_offset_x)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 82))
        painter.drawEllipse(QRectF(content_left + (self._content_width - 230 * scale) / 2, self.height() - 46 * scale, 230 * scale, 25 * scale))

        frame = self._current_frame()
        if frame:
            self._draw_frame(painter, frame)
        else:
            self._draw_static_hint(painter)

        painter.setPen(QPen(QColor(126, 232, 255), max(1, round(2 * scale))))
        painter.setBrush(QColor(12, 24, 38, 220))
        header_rect = QRectF(content_left + round(48 * scale), round(10 * scale), self._content_width - round(96 * scale), max(24, round(34 * scale)))
        painter.drawRoundedRect(header_rect, max(8, round(12 * scale)), max(8, round(12 * scale)))
        painter.setPen(QColor(222, 248, 255))
        painter.drawText(header_rect, Qt.AlignCenter, f"北极熊 · {self.mood} · {self.scale_percent}%")

        if self._bubble_text:
            self._draw_bubble(painter, content_left, header_rect)

    def _current_frame(self):
        action = self._current_action()
        if not action or not action.frames:
            return None
        return action.frames[self._frame_index % len(action.frames)]

    def _draw_frame(self, painter, frame):
        logical_size = frame.deviceIndependentSize()
        x = round(self._pet_draw_center.x() + self._walk_visual_offset_x - logical_size.width() / 2)
        y = round(self._pet_draw_center.y() - logical_size.height() / 2)
        painter.drawPixmap(x, y, frame)

    def _draw_static_hint(self, painter):
        if not self.fallback_pixmap.isNull():
            self._draw_frame(painter, self.fallback_pixmap)
        painter.setPen(QPen(QColor(126, 232, 255), 1))
        painter.setBrush(QColor(12, 24, 38, 185))
        content_left = self._walk_visual_padding + round(self._walk_visual_offset_x)
        painter.drawRoundedRect(QRectF(content_left + round(44 * self._scale), self.height() - 76 * self._scale, self._content_width - round(88 * self._scale), 38 * self._scale), 10, 10)
        painter.setPen(QColor(222, 248, 255))
        painter.drawText(
            QRectF(content_left + round(54 * self._scale), self.height() - 72 * self._scale, self._content_width - round(108 * self._scale), 30 * self._scale),
            Qt.AlignCenter | Qt.TextWordWrap,
            "请放入真实动画帧：assets/polar_bear/real_actions",
        )

    def _draw_bubble(self, painter, content_left, header_rect):
        scale = self._scale
        margin = max(6, round(12 * scale))
        left_space = max(0, content_left)
        right_space = max(0, self.width() - (content_left + self._content_width))
        preferred_width = max(150, round(240 * scale))
        side_space = max(left_space, right_space)
        bubble_width = min(preferred_width, max(0, side_space - margin * 2))

        if bubble_width >= max(120, round(150 * scale)):
            if left_space >= right_space:
                bubble_x = max(margin, content_left - margin - bubble_width)
            else:
                bubble_x = min(
                    self.width() - bubble_width - margin,
                    content_left + self._content_width + margin,
                )
        else:
            bubble_width = max(120, self._content_width - round(48 * scale))
            bubble_x = content_left + (self._content_width - bubble_width) / 2

        text_margin = max(8, round(10 * scale))
        text_width = max(1, bubble_width - text_margin * 2)
        measured = painter.boundingRect(
            QRectF(0, 0, text_width, 1000),
            Qt.AlignCenter | Qt.TextWordWrap,
            self._bubble_text,
        )
        bubble_height = max(max(38, round(48 * scale)), math.ceil(measured.height()) + text_margin * 2)
        bubble_height = min(bubble_height, max(76, round(96 * scale)))
        top_y = header_rect.bottom() + max(8, round(12 * scale))
        bottom_limit = self.height() - bubble_height - max(14, round(72 * scale))
        bubble_y = max(max(4, round(8 * scale)), min(top_y, bottom_limit))

        bubble_rect = QRectF(
            bubble_x,
            bubble_y,
            bubble_width,
            bubble_height,
        )
        painter.setPen(QPen(QColor(126, 232, 255), max(1, round(2 * scale))))
        painter.setBrush(QColor(12, 24, 38, 228))
        painter.drawRoundedRect(bubble_rect, max(8, round(12 * scale)), max(8, round(12 * scale)))
        painter.setPen(QColor(235, 250, 255))
        painter.drawText(
            bubble_rect.adjusted(text_margin, 0, -text_margin, 0),
            Qt.AlignCenter | Qt.TextWordWrap,
            self._bubble_text,
        )
