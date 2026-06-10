import json
import math
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QElapsedTimer,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QImage, QImageReader, QLinearGradient, QPainter, QPen, QPixmap, QRadialGradient, QTransform
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
    "edge_left": "贴左边",
    "edge_right": "贴右边",
}


@dataclass
class FrameAction:
    name: str
    label: str
    frames: list[QPixmap]
    source_frames: list[QPixmap] = field(default_factory=list)
    frame_paths: list[Path] = field(default_factory=list)
    repeat: int = 1
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
        self._always_on_top = True

        self.asset_root = Path(__file__).resolve().parents[1] / "assets" / "polar_bear"
        self.role_root = self.asset_root / "role" / "PolarBear"
        self.real_action_root = self.asset_root / "real_actions"
        self.pet_conf_path = self.role_root / "pet_conf.json"
        self._base_window_size = (420, 660)
        self._base_draw_rect = QRectF(30, 118, 360, 520)
        self._walk_visual_padding = 0
        self._top_overlay_padding = 0
        self._side_overlay_padding = 0
        self._content_width = 0
        self._content_height = 0
        self._scale = self._load_pet_scale()
        self._walk_window_move = self._load_walk_window_move()
        self._configure_geometry()

        self._drag_position = QPoint()
        self._press_position = QPoint()
        self._is_dragging = False
        self._drag_hold_frame = None
        self._click_action_token = 0
        self._ignore_next_click_release = False
        self._click_action_delay = max(260, min(650, QApplication.doubleClickInterval() + 50))
        self._actions = {}
        self._transition_action = None
        self._return_transitions = {}
        self._frame_bounds_cache = {}
        self._loaded_frame_cache = {}
        self._action_name = "idle"
        self._frame_index = 0
        self._cycle_count = 0
        self._walk_frame_count = 0
        self._elapsed = 0
        self._move_x_remainder = 0.0
        self._walk_visual_offset_x = 0.0
        self._pose_visual_offset = QPointF(0.0, 0.0)
        self._pose_settle_cooldown_ms = 0
        self._screen_area_cache = None
        self._next_random_action = self._random_idle_delay()
        self._next_roam_action = self._random_roam_delay()
        self._next_corner_hide = self._random_corner_hide_delay()
        self._corner_hidden = False
        self._corner_hide_side = ""
        self._corner_animation = None
        self._corner_dot_mode = False
        self._external_window_motion = False
        self._idle_events_until_sleep = random.randint(2, 4)
        self._random_action_pool = []
        self._bubble_text = ""
        self._bubble_pages = []
        self._bubble_page_index = 0
        self._bubble_token = 0
        self._bubble_is_chat = False
        self._bubble_draw_rect = QRectF()
        self._bubble_layout_side = ""
        self._bubble_layout_width = 0.0
        self._choice_title = ""
        self._choice_options = []
        self._choice_button_rects = []
        self._choice_panel_rect = QRectF()
        self._choice_pressing = False
        self._choice_pressed_key = ""
        self._choice_hover_key = ""
        self._choice_progress = 0.0
        self._choice_phase = 0.0
        self._choice_repaint_elapsed = 0
        self._edge_snap_enabled = True
        self._edge_snap_threshold = 48
        self._edge_stick_side = None
        self._deferred_load_queue = []
        self._deferred_loading = False

        self._fallback_source_pixmap = QPixmap(str(self.asset_root / "polar-bear-realistic.png"))
        self.fallback_pixmap = self._scale_pixmap(self._fallback_source_pixmap)
        self._load_actions()
        self._ensure_action_loaded("idle")
        self._load_random_action_pool()
        self._rebuild_return_transitions()
        self._warm_frame_cache()
        self._start_deferred_action_loading()

        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._timer_interval_for_action(self._current_action()))

    @property
    def mood(self):
        if self._is_dragging:
            return ACTION_LABELS.get("drag", "drag")
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
        enabled = bool(enabled)
        if self._always_on_top == enabled:
            return
        self._always_on_top = enabled
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

    def show_bubble(self, text, duration=2400, chat=False):
        anchor = self.visual_anchor_screen_point() if self.isVisible() else None
        self._clear_choice_state()
        self._bubble_token += 1
        self._bubble_is_chat = bool(chat)
        self._bubble_pages = self._split_bubble_text(text, chat=chat)
        self._bubble_page_index = 0
        self._bubble_text = self._bubble_pages[0] if self._bubble_pages else ""
        self._bubble_draw_rect = QRectF()
        self._bubble_layout_side = ""
        self._bubble_layout_width = 0.0
        if not self._bubble_text:
            self._apply_overlay_padding(0, 0, anchor=anchor)
            return
        self._apply_overlay_padding(0, 0, anchor=anchor)
        self.update()
        self._schedule_bubble_timeout(self._bubble_token, duration)

    def show_choice_bubble(self, title, options):
        normalized = []
        for key, label in options:
            key = str(key or "").strip()
            label = str(label or "").strip()
            if key and label:
                normalized.append((key, label[:12]))
        if not normalized:
            return
        self._bubble_token += 1
        self._bubble_text = ""
        self._bubble_pages = []
        self._bubble_page_index = 0
        self._bubble_is_chat = False
        self._bubble_draw_rect = QRectF()
        self._bubble_layout_side = ""
        self._bubble_layout_width = 0.0
        self._choice_title = str(title or "想做什么？").strip()[:18]
        self._choice_options = normalized[:8]
        self._apply_overlay_padding(0, 0)
        self._choice_button_rects = []
        self._choice_panel_rect = QRectF(self.rect())
        self._choice_pressing = False
        self._choice_pressed_key = ""
        self._choice_hover_key = ""
        self._choice_progress = 0.0
        self._choice_phase = 0.0
        self._choice_repaint_elapsed = 0
        self.update()

    def _clear_choice_state(self):
        self._choice_title = ""
        self._choice_options = []
        self._choice_button_rects = []
        self._choice_panel_rect = QRectF()
        self._choice_pressing = False
        self._choice_pressed_key = ""
        self._choice_hover_key = ""
        self._choice_progress = 0.0
        self._choice_repaint_elapsed = 0

    def _choice_overlay_padding(self, count):
        return max(132, round(250 * self._scale))

    def _choice_side_overlay_padding(self):
        return max(112, round(260 * self._scale))

    def hide_choice_bubble(self):
        if not self._choice_options:
            return
        self._clear_choice_state()
        if not self._bubble_text:
            self._apply_overlay_padding(0, 0)
        self.update()

    def _compact_bubble_text(self, text):
        text = " ".join(str(text or "").split())
        return text

    def _split_bubble_text(self, text, chat=False):
        text = self._compact_bubble_text(text)
        if not text:
            return []
        limit = 56 if self._scale <= 0.55 else 76
        if not chat:
            limit = 70 if self._scale <= 0.55 else 96
        if len(text) <= limit:
            return [text]

        parts = re.findall(r".+?[。！？!?；;，,、]|.+$", text)
        pages = []
        current = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            while len(part) > limit:
                chunk = part[:limit].rstrip()
                part = part[limit:].lstrip()
                if current:
                    pages.append(current)
                    current = ""
                pages.append(chunk)
            if not current:
                current = part
            elif len(current) + len(part) <= limit:
                current += part
            else:
                pages.append(current)
                current = part
        if current:
            pages.append(current)
        return pages

    def _bubble_overlay_padding(self, text):
        base = 214 if self._bubble_is_chat else 170
        lines = max(1, math.ceil(len(text) / (26 if self._scale <= 0.55 else 34)))
        extra = min(3, lines - 1) * 28
        return max(118, round((base + extra) * self._scale))

    def _bubble_side_overlay_padding(self):
        if self._bubble_is_chat:
            return max(170, round(380 * self._scale))
        return max(72, round(170 * self._scale))

    def _schedule_bubble_timeout(self, token, duration):
        timeout = max(1800, int(duration))
        if self._bubble_is_chat:
            timeout = max(6200, min(14000, timeout + len(self._bubble_text) * 70))
        elif len(self._bubble_pages) > 1:
            timeout = max(2800, min(7800, timeout + len(self._bubble_text) * 34))
        QTimer.singleShot(timeout, lambda: self._advance_or_clear_bubble(token, duration))

    def _advance_or_clear_bubble(self, token, duration):
        if token != self._bubble_token:
            return
        if self._bubble_page_index + 1 < len(self._bubble_pages):
            self._bubble_page_index += 1
            self._bubble_text = self._bubble_pages[self._bubble_page_index]
            self.update()
            self._schedule_bubble_timeout(token, duration)
            return
        self._clear_bubble(token=token)

    def _clear_bubble(self, token=None):
        if token is None:
            self._bubble_token += 1
        elif token != self._bubble_token:
            return
        if self._bubble_text:
            self._bubble_text = ""
            self._bubble_pages = []
            self._bubble_page_index = 0
            self._bubble_is_chat = False
            self._bubble_draw_rect = QRectF()
            self._bubble_layout_side = ""
            self._bubble_layout_width = 0.0
            if not self._choice_options:
                self._apply_overlay_padding(0, 0)
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
        base_padding = max(260, round(560 * self._scale))
        self._walk_visual_padding = base_padding + int(self._side_overlay_padding)
        self.setFixedSize(self._content_width + self._walk_visual_padding * 2, self._content_height + self._top_overlay_padding)
        self._pet_draw_rect = QRectF(
            self._walk_visual_padding + round(self._base_draw_rect.x() * self._scale),
            self._top_overlay_padding + round(self._base_draw_rect.y() * self._scale),
            round(self._base_draw_rect.width() * self._scale),
            round(self._base_draw_rect.height() * self._scale),
        )
        self._pet_draw_center = self._pet_draw_rect.center()

    def _set_top_overlay_padding(self, padding):
        self._apply_overlay_padding(self._side_overlay_padding, padding)

    def _set_side_overlay_padding(self, padding):
        self._apply_overlay_padding(padding, self._top_overlay_padding)

    def _apply_overlay_padding(self, side_padding=None, top_padding=None, anchor=None):
        side_padding = self._side_overlay_padding if side_padding is None else max(0, int(side_padding))
        top_padding = self._top_overlay_padding if top_padding is None else max(0, int(top_padding))
        if side_padding == self._side_overlay_padding and top_padding == self._top_overlay_padding:
            return
        if anchor is None and self.isVisible():
            anchor = self.visual_anchor_screen_point()
        updates_enabled = self.updatesEnabled()
        if updates_enabled:
            self.setUpdatesEnabled(False)
        try:
            self._side_overlay_padding = side_padding
            self._top_overlay_padding = top_padding
            self._configure_geometry()
            if anchor is not None:
                self.restore_visual_anchor(anchor)
        finally:
            if updates_enabled:
                self.setUpdatesEnabled(True)
        self.update()

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
            if not action.frames:
                continue
            if action.frame_paths:
                action.frames = []
                action.source_frames = []
            else:
                source_frames = action.source_frames or action.frames
                action.frames = self._scale_frames(source_frames)
        self._frame_bounds_cache.clear()
        self._loaded_frame_cache.clear()
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
        frame_path_cache = {}
        for action_name, action_conf in act_conf.items():
            image_prefix = action_conf.get("images", action_name)
            if image_prefix not in frame_path_cache:
                frame_path_cache[image_prefix] = self._prefixed_frame_paths(action_root, image_prefix)
            frame_paths = frame_path_cache[image_prefix]
            if not frame_paths:
                continue
            act_num = int(action_conf.get("act_num", 1))
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
                frames=[],
                source_frames=[],
                frame_paths=list(frame_paths),
                repeat=max(1, act_num),
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
            "edge_left": "edge_left",
            "edge_right": "edge_right",
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

    def _prefixed_frame_paths(self, action_root, image_prefix):
        frame_pattern = re.compile(rf"^{re.escape(image_prefix)}_(\d+)\.png$", re.IGNORECASE)
        files = []
        for file in action_root.glob(f"{image_prefix}_*.png"):
            match = frame_pattern.match(file.name)
            if match:
                files.append((int(match.group(1)), file))
        return [file for _, file in sorted(files)]

    def _load_prefixed_frames(self, action_root, image_prefix):
        frames = []
        for file in self._prefixed_frame_paths(action_root, image_prefix):
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

    def _target_frame_pixel_size(self, source_size=None):
        logical_size = self._pet_draw_rect.size().toSize()
        dpr = max(1.0, self.devicePixelRatioF())
        bounds = QSize(max(1, round(logical_size.width() * dpr)), max(1, round(logical_size.height() * dpr)))
        if source_size and source_size.isValid():
            return source_size.scaled(bounds, Qt.KeepAspectRatio)
        return bounds

    def _load_scaled_frame_path(self, file):
        reader = QImageReader(str(file))
        target_size = self._target_frame_pixel_size(reader.size())
        if target_size.isValid():
            reader.setScaledSize(target_size)
        image = reader.read()
        if image.isNull():
            return QPixmap()
        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(max(1.0, self.devicePixelRatioF()))
        return pixmap

    def _ensure_action_loaded(self, action_name):
        action = self._actions.get(action_name)
        if not action:
            return None
        if action.frames:
            return action
        if not action.frame_paths:
            return None

        cache_key = tuple(str(file) for file in action.frame_paths)
        scaled_frames = self._loaded_frame_cache.get(cache_key)
        if scaled_frames is None:
            scaled_frames = []
            for file in action.frame_paths:
                pixmap = self._load_scaled_frame_path(file)
                if not pixmap.isNull():
                    scaled_frames.append(pixmap)
            if scaled_frames:
                self._loaded_frame_cache[cache_key] = scaled_frames
        if not scaled_frames:
            return None

        action.source_frames = []
        action.frames = list(scaled_frames) * max(1, int(action.repeat or 1))
        return action

    def _action_has_frames(self, action):
        return bool(action and (action.frames or action.frame_paths))

    def _start_deferred_action_loading(self):
        priorities = [
            "touch",
            "wave",
            "walk_left",
            "walk_right",
            "jump",
            "sleep_prepare",
            "sleep",
        ]
        self._deferred_load_queue = [name for name in priorities if name in self._actions and name != self._action_name]
        self._deferred_loading = bool(self._deferred_load_queue)
        if self._deferred_loading:
            QTimer.singleShot(420, self._load_next_deferred_action)

    def _load_next_deferred_action(self):
        if not self._deferred_load_queue:
            self._deferred_loading = False
            return
        if not self.isVisible() or self._is_dragging or self._action_name not in {"idle", "__transition__"}:
            QTimer.singleShot(360, self._load_next_deferred_action)
            return
        action_name = self._deferred_load_queue.pop(0)
        if action_name != self._action_name:
            self._ensure_action_loaded(action_name)
            self._rebuild_return_transitions()
        delay = 260 if self._deferred_load_queue else 0
        if delay:
            QTimer.singleShot(delay, self._load_next_deferred_action)
        else:
            self._deferred_loading = False

    def _warm_frame_cache(self):
        return

    def _timer_interval_for_action(self, action):
        if not action:
            return 24
        return max(20, min(32, int(max(20, action.interval / 2))))

    def _sync_timer_interval(self, action):
        if not hasattr(self, "_timer"):
            return
        interval = self._timer_interval_for_action(action)
        if self._timer.interval() != interval:
            self._timer.setInterval(interval)

    def _random_idle_delay(self):
        return random.randint(22000, 38000)

    def _random_roam_delay(self):
        return random.randint(5200, 9800)

    def _random_corner_hide_delay(self):
        return random.randint(72000, 128000)

    def _is_corner_animating(self):
        return bool(
            self._corner_animation
            and self._corner_animation.state() == QAbstractAnimation.Running
        )

    def _autonomy_is_paused(self):
        return bool(
            self._is_dragging
            or self._choice_options
            or self._bubble_text
            or self._is_corner_animating()
        )

    def _reset_autonomy_timers(self, roam_delay=None, hide_delay=None):
        self._next_roam_action = int(roam_delay if roam_delay is not None else self._random_roam_delay())
        self._next_random_action = self._random_idle_delay()
        self._next_corner_hide = int(hide_delay if hide_delay is not None else self._random_corner_hide_delay())

    def _load_random_action_pool(self):
        name_map = {
            "default": "idle",
            "left_walk": "walk_left",
            "right_walk": "walk_right",
            "patpat": "wave",
        }
        pet_conf = self._read_pet_conf()
        pool = []
        for group in pet_conf.get("random_act", []):
            try:
                weight = float(group.get("act_prob", 0))
            except (TypeError, ValueError):
                weight = 0
            if weight <= 0:
                continue
            candidates = []
            for action_name in group.get("act_list", []):
                normalized = name_map.get(action_name, action_name)
                if normalized in self._actions:
                    candidates.append(normalized)
            if candidates:
                active_candidates = [name for name in candidates if name != "idle"]
                if active_candidates:
                    candidates = active_candidates
                    weight *= 1.45
                else:
                    weight *= 0.25
                pool.append((weight, candidates))
        self._random_action_pool = pool

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

        delta_ms = min(48, max(1, self._clock.restart()))
        self._elapsed += delta_ms
        if self._pose_settle_cooldown_ms > 0:
            self._pose_settle_cooldown_ms = max(0, self._pose_settle_cooldown_ms - delta_ms)
        should_update = False
        if self._choice_options:
            self._choice_phase = (self._choice_phase + delta_ms / 260.0) % (math.pi * 2)
            if self._choice_progress < 1.0:
                self._choice_progress = min(1.0, self._choice_progress + delta_ms / 180.0)
            self._choice_repaint_elapsed += delta_ms
            if self._choice_repaint_elapsed >= 34 or self._choice_progress < 1.0:
                self._choice_repaint_elapsed = 0
                should_update = True

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

        if self._corner_hidden:
            if self._corner_dot_mode:
                self._choice_phase = (self._choice_phase + delta_ms / 520.0) % (math.pi * 2)
                should_update = True
            if should_update:
                self.update()
            return

        if self._action_name == "idle" and not self._autonomy_is_paused():
            self._next_corner_hide -= delta_ms
            if self._next_corner_hide <= 0:
                self.hide_in_corner()
                return

            self._next_roam_action -= delta_ms
            if self._next_roam_action <= 0:
                self._play_roam_action()
                return

            self._next_random_action -= delta_ms
            if self._next_random_action <= 0:
                self._play_random_action()
                return

        if (
            self._action_name == "idle"
            and not self._bubble_text
            and self._pose_settle_cooldown_ms <= 0
            and self._settle_pose_visual_offset(max_step=2)
        ):
            should_update = True

        if should_update:
            self.update()

    def _current_action(self):
        if self._action_name == "__transition__":
            return self._transition_action
        return self._ensure_action_loaded(self._action_name) or self._ensure_action_loaded("idle")

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
        if self._external_window_motion:
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
        if abs(self._walk_visual_offset_x) < 0.75:
            self._walk_visual_offset_x = 0.0
        elif not moved_x and not force:
            self._walk_visual_offset_x = 0.0

    def _settle_pose_visual_offset(self, max_step=10):
        if (
            self._corner_dot_mode
            or self._external_window_motion
            or self._is_dragging
            or self._choice_options
        ):
            return False
        offset = getattr(self, "_pose_visual_offset", QPointF(0.0, 0.0))
        if abs(offset.x()) < 0.75 and abs(offset.y()) < 0.75:
            if abs(offset.x()) > 0.001 or abs(offset.y()) > 0.001:
                self._pose_visual_offset = QPointF(0.0, 0.0)
                return True
            return False

        def step(value):
            if abs(value) < 0.75:
                return 0
            amount = int(round(value))
            if amount == 0:
                amount = 1 if value > 0 else -1
            return max(-max_step, min(max_step, amount))

        move_x = step(offset.x())
        move_y = step(offset.y())
        if not move_x and not move_y:
            return False
        self.move(self.x() + move_x, self.y() + move_y)
        self._pose_visual_offset -= QPointF(move_x, move_y)
        self._screen_area_cache = None
        return True

    def _play_random_action(self):
        self._next_random_action = self._random_idle_delay()
        if not self._random_action_pool:
            return
        total = sum(weight for weight, _ in self._random_action_pool)
        if total <= 0:
            return
        pick = random.uniform(0, total)
        chosen = "idle"
        for weight, candidates in self._random_action_pool:
            pick -= weight
            if pick <= 0:
                chosen = random.choice(candidates)
                break
        if chosen == "idle":
            return
        self.play_action(chosen)

    def _walk_direction_for_screen_position(self):
        area = self._available_screen_area()
        if not area:
            return random.choice(["walk_left", "walk_right"])
        rect = self._visible_pet_screen_rect(precise=True)
        area_left = area.left()
        area_right = area.left() + area.width()
        center_x = rect.center().x()
        if center_x < area_left + area.width() * 0.26:
            return "walk_right"
        if center_x > area_left + area.width() * 0.74:
            return "walk_left"
        return random.choice(["walk_left", "walk_right"])

    def _play_roam_action(self):
        self._next_roam_action = self._random_roam_delay()
        if self._corner_hidden or self._autonomy_is_paused():
            return
        action_name = self._walk_direction_for_screen_position()
        if action_name not in self._actions:
            action_name = "walk_right" if "walk_right" in self._actions else "walk_left"
        if action_name in self._actions:
            self.play_action(action_name)

    def _animate_window_to(self, target, duration=820, finished=None, external_motion=True):
        target = QPoint(int(target.x()), int(target.y()))
        if self._corner_animation:
            self._corner_animation.stop()
            self._corner_animation = None
            self._external_window_motion = False
        if (self.pos() - target).manhattanLength() <= 2:
            self.move(target)
            self._external_window_motion = False
            if finished:
                finished()
            return
        self._external_window_motion = bool(external_motion)
        animation = QPropertyAnimation(self, b"pos", self)
        animation.setStartValue(self.pos())
        animation.setEndValue(target)
        animation.setDuration(max(160, int(duration)))
        animation.setEasingCurve(QEasingCurve.InOutCubic)

        def clear_animation():
            if self._corner_animation is animation:
                self._corner_animation = None
            self._external_window_motion = False

        animation.finished.connect(clear_animation)
        if finished:
            animation.finished.connect(finished)
        self._corner_animation = animation
        animation.start()

    def _corner_target_position(self, side, visible_ratio=0.18):
        area = self._available_screen_area()
        if not area:
            return QPoint(self.x(), self.y())
        rect = self._visible_pet_screen_rect(precise=True)
        area_left = area.left()
        area_right = area.left() + area.width()
        area_bottom = area.top() + area.height()
        next_x = self.x()
        next_y = self.y()
        if side == "left":
            target_left = area_left - rect.width() * (1.0 - visible_ratio)
            next_x += round(target_left - rect.left())
        else:
            target_right = area_right + rect.width() * (1.0 - visible_ratio)
            next_x += round(target_right - rect.right())
        target_bottom = area_bottom - max(8, round(12 * self._scale))
        next_y += round(target_bottom - rect.bottom())
        return QPoint(int(next_x), int(next_y))

    def _corner_dot_size(self):
        return max(54, min(76, round(92 * self._scale)))

    def _corner_dot_target_position(self, side):
        area = self._available_screen_area()
        size = self._corner_dot_size()
        if not area:
            return QPoint(self.x(), self.y())
        margin = max(10, round(16 * self._scale))
        x = area.left() + margin if side == "left" else area.left() + area.width() - size - margin
        y = area.top() + area.height() - size - margin
        return QPoint(int(x), int(y))

    def _enter_corner_dot_mode(self, side):
        self._corner_dot_mode = True
        self._external_window_motion = False
        self._transition_action = None
        self._action_name = "idle"
        self._frame_index = 0
        self._cycle_count = 0
        self._walk_frame_count = 0
        self._elapsed = 0
        self._move_x_remainder = 0.0
        self._walk_visual_offset_x = 0.0
        self._pose_visual_offset = QPointF(0.0, 0.0)
        size = self._corner_dot_size()
        self.setFixedSize(size, size)
        self.move(self._corner_dot_target_position(side))
        self.update()

    def _leave_corner_dot_mode(self, side):
        if not self._corner_dot_mode:
            return
        self._corner_dot_mode = False
        self._configure_geometry()
        self._walk_visual_offset_x = 0.0
        self._pose_visual_offset = QPointF(0.0, 0.0)
        self.move(self._corner_target_position(side, visible_ratio=0.18))
        self.update()

    def _visible_return_position(self, side):
        area = self._available_screen_area()
        if not area:
            return QPoint(self.x(), self.y())
        rect = self._visible_pet_screen_rect(precise=True)
        area_left = area.left()
        area_right = area.left() + area.width()
        area_top = area.top()
        area_bottom = area.top() + area.height()
        margin = max(18, round(34 * self._scale))
        next_x = self.x()
        next_y = self.y()
        if side == "left":
            next_x += round(area_left + margin - rect.left())
        else:
            next_x += round(area_right - margin - rect.right())
        if rect.bottom() > area_bottom - margin:
            next_y += round(area_bottom - margin - rect.bottom())
        if rect.top() < area_top + margin:
            next_y += round(area_top + margin - rect.top())
        return QPoint(int(next_x), int(next_y))

    def hide_in_corner(self):
        if self._corner_hidden or self._is_dragging or self._choice_options:
            return False
        area = self._available_screen_area()
        if not area:
            return False
        self.hide_choice_bubble()
        self._clear_bubble()
        rect = self._visible_pet_screen_rect(precise=True)
        side = "left" if rect.center().x() <= area.left() + area.width() / 2 else "right"
        self._corner_hidden = True
        self._corner_hide_side = side
        self._next_corner_hide = self._random_corner_hide_delay()
        self._next_roam_action = self._random_roam_delay()
        walk_action = "walk_left" if side == "left" else "walk_right"
        if walk_action in self._actions:
            self.play_action(walk_action, transition=False)
        target = self._corner_target_position(side)

        def finish_hide():
            self._external_window_motion = False
            self._enter_corner_dot_mode(side)
            self._edge_stick_side = side
            self.interaction_requested.emit("corner_hide")

        self._animate_window_to(target, duration=1100, finished=finish_hide, external_motion=True)
        return True

    def reveal_from_corner(self):
        if not self._corner_hidden and not self._is_corner_animating():
            return False
        side = self._corner_hide_side or self._edge_stick_side or "right"
        if self._corner_animation:
            self._corner_animation.stop()
            self._corner_animation = None
        self._external_window_motion = False
        self._corner_hidden = False
        self._corner_hide_side = ""
        self._edge_stick_side = None
        self._leave_corner_dot_mode(side)
        self.play_action("wave" if "wave" in self._actions else "idle", transition=False)
        target = self._visible_return_position(side)

        def finish_reveal():
            self._reset_autonomy_timers(roam_delay=random.randint(4500, 8500), hide_delay=self._random_corner_hide_delay())
            if self.isVisible():
                self.show_bubble("我出来啦。", duration=1600)
            self.interaction_requested.emit("corner_exit")

        self._animate_window_to(target, duration=620, finished=finish_reveal, external_motion=True)
        return True

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
        idle = self._ensure_action_loaded("idle")
        if not idle or not idle.frames:
            return

        for source_name, source_action in self._actions.items():
            if source_name in {"idle", "blink", "sleep_prepare", "edge_left", "edge_right"} or not self._action_has_frames(source_action):
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
        anchor = self.visual_anchor_screen_point() if self.isVisible() else None
        if source_action_name in {"walk_left", "walk_right"}:
            self._walk_visual_offset_x = 0.0
            self._pose_settle_cooldown_ms = max(self._pose_settle_cooldown_ms, 1100)
        self._transition_action = transition
        self._action_name = "__transition__"
        self._sync_timer_interval(transition)
        self._frame_index = 1 if len(transition.frames) > 1 else 0
        self._cycle_count = 0
        self._walk_frame_count = 0
        self._elapsed = max(0, transition.interval - 16)
        self._move_x_remainder = 0.0
        self._pose_visual_offset = QPointF(0.0, 0.0)
        if hasattr(self, "_clock"):
            self._clock.restart()
        if anchor is not None:
            self.align_visual_anchor_inside_window(anchor)
        self.update()
        return True

    def play_action(self, action_name, duration=None, transition=True, start_frame_index=0):
        if action_name not in self._actions:
            return
        if self._is_dragging and action_name != "idle":
            return
        anchor = self.visual_anchor_screen_point() if self.isVisible() else None
        was_edge_side = self._edge_stick_side
        if action_name == "edge_left":
            self._edge_stick_side = "left"
        elif action_name == "edge_right":
            self._edge_stick_side = "right"
        else:
            self._edge_stick_side = None
        reset_walk_visual_offset = self._action_name in {"walk_left", "walk_right"} and action_name != self._action_name
        if transition and action_name == "sleep" and "sleep_prepare" in self._actions:
            action_name = "sleep_prepare"
        action = self._ensure_action_loaded(action_name)
        if not action or not action.frames:
            return
        if transition and action_name == "idle" and self._action_name not in {"idle", "__transition__"}:
            if self._start_return_transition(self._action_name):
                return
        if action_name in {"walk_left", "walk_right"}:
            self._ensure_walk_headroom(action_name)
        self._transition_action = None
        self._action_name = action_name
        self._sync_timer_interval(action)
        self._frame_index = self._start_frame_index(action_name, start_frame_index, action)
        self._cycle_count = 0
        self._walk_frame_count = 0
        self._move_x_remainder = 0.0
        if reset_walk_visual_offset:
            self._walk_visual_offset_x = 0.0
            self._pose_settle_cooldown_ms = max(self._pose_settle_cooldown_ms, 700)
        self._pose_visual_offset = QPointF(0.0, 0.0)
        self._prime_action_timing(action_name, action)
        if hasattr(self, "_clock"):
            self._clock.restart()
        if was_edge_side and action_name not in {"edge_left", "edge_right"}:
            next_x, next_y = self.fit_position_to_visible_screen(self.x(), self.y())
            if next_x != self.x() or next_y != self.y():
                self.move(next_x, next_y)
                anchor = None
        if anchor is not None:
            self.align_visual_anchor_inside_window(anchor)
        self.update()

    def _begin_drag_hold(self):
        self._edge_stick_side = None
        self._commit_walk_visual_offset(force=True)
        frame = self._current_frame()
        self._drag_hold_frame = QPixmap(frame) if frame and not frame.isNull() else None
        self._transition_action = None
        self._action_name = "idle"
        idle = self._ensure_action_loaded("idle")
        if idle and idle.frames:
            self._frame_index = self._idle_return_frame_hint("drag") % len(idle.frames)
        else:
            self._frame_index = 0
        self._cycle_count = 0
        self._walk_frame_count = 0
        self._elapsed = 0
        self._move_x_remainder = 0.0
        self._walk_visual_offset_x = 0.0
        self._pose_visual_offset = QPointF(0.0, 0.0)
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
        anchor = self.visual_anchor_screen_point() if self.isVisible() else None
        if self._action_name == "walk_left":
            next_name = "walk_right"
        elif self._action_name == "walk_right":
            next_name = "walk_left"
        else:
            return False

        current_action = self._current_action()
        next_action = self._ensure_action_loaded(next_name)
        if not current_action or not next_action or not next_action.frames:
            return False

        progress = self._frame_index / max(1, len(current_action.frames))
        self._action_name = next_name
        self._frame_index = min(len(next_action.frames) - 1, int(progress * len(next_action.frames)))
        self._elapsed = min(self._elapsed, max(0, next_action.interval - 1))
        self._walk_frame_count = 0
        self._move_x_remainder = 0.0
        self._walk_visual_offset_x = 0.0
        self._pose_visual_offset = QPointF(0.0, 0.0)
        if anchor is not None:
            self.align_visual_anchor_inside_window(anchor)
        self.update()
        return True

    def _frame_alpha_bounds(self, frame):
        if not frame or frame.isNull():
            return QRectF()
        key = int(frame.cacheKey())
        cached = self._frame_bounds_cache.get(key)
        if cached is not None:
            return QRectF(cached)

        image = frame.toImage().convertToFormat(QImage.Format_Alpha8)
        width = image.width()
        height = image.height()
        left = width
        top = height
        right = -1
        bottom = -1
        bytes_per_line = image.bytesPerLine()
        data = bytes(image.constBits())[: bytes_per_line * height]
        for y in range(height):
            row = data[y * bytes_per_line : y * bytes_per_line + width]
            row_left = None
            for x, alpha in enumerate(row):
                if alpha > 8:
                    row_left = x
                    break
            if row_left is None:
                continue
            row_right = width - 1
            for offset, alpha in enumerate(reversed(row)):
                if alpha > 8:
                    row_right = width - 1 - offset
                    break
            left = min(left, row_left)
            top = min(top, y)
            right = max(right, row_right)
            bottom = max(bottom, y)

        logical_size = frame.deviceIndependentSize()
        if right < left or bottom < top:
            bounds = QRectF(0, 0, logical_size.width(), logical_size.height())
        else:
            dpr = max(1.0, frame.devicePixelRatio())
            bounds = QRectF(
                left / dpr,
                top / dpr,
                (right - left + 1) / dpr,
                (bottom - top + 1) / dpr,
            )
        self._frame_bounds_cache[key] = QRectF(bounds)
        return bounds

    def _frame_draw_rect(self, frame):
        logical_size = frame.deviceIndependentSize()
        return QRectF(
            round(
                self._pet_draw_center.x()
                + self._walk_visual_offset_x
                + self._pose_visual_offset.x()
                - logical_size.width() / 2
            ),
            round(self._pet_draw_center.y() + self._pose_visual_offset.y() - logical_size.height() / 2),
            logical_size.width(),
            logical_size.height(),
        )

    def _visible_pet_rect(self, precise=False):
        if self._corner_dot_mode:
            return QRectF(0, 0, self.width(), self.height())
        frame = self._current_frame()
        if frame and not frame.isNull():
            draw_rect = self._frame_draw_rect(frame)
            if precise:
                bounds = self._frame_alpha_bounds(frame)
                rect = QRectF(
                    draw_rect.left() + bounds.left(),
                    draw_rect.top() + bounds.top(),
                    bounds.width(),
                    bounds.height(),
                )
            else:
                rect = draw_rect
        else:
            rect = QRectF(self._pet_draw_rect)
        pad = max(2, round(5 * self._scale))
        return rect.adjusted(-pad, -pad, pad, pad)

    def _visible_pet_screen_rect(self, window_x=None, window_y=None, precise=False):
        x = self.x() if window_x is None else int(window_x)
        y = self.y() if window_y is None else int(window_y)
        return self._visible_pet_rect(precise=precise).translated(x, y)

    def visual_anchor_screen_point(self, precise=True):
        rect = self._visible_pet_screen_rect(precise=precise)
        return QPointF(rect.center().x(), rect.bottom())

    def restore_visual_anchor(self, anchor, precise=True):
        if anchor is None:
            return
        current = self.visual_anchor_screen_point(precise=precise)
        dx = round(anchor.x() - current.x())
        dy = round(anchor.y() - current.y())
        if dx or dy:
            self.move(self.x() + dx, self.y() + dy)
            self._screen_area_cache = None

    def align_visual_anchor_inside_window(self, anchor, precise=True):
        if anchor is None:
            return
        current = self.visual_anchor_screen_point(precise=precise)
        dx = anchor.x() - current.x()
        dy = anchor.y() - current.y()
        if abs(dx) > 0.5 or abs(dy) > 0.5:
            self._pose_visual_offset += QPointF(dx, dy)

    def fit_position_to_visible_screen(self, x, y, margin=None, precise=False):
        area = self._available_screen_area()
        if not area:
            return int(x), int(y)
        margin = max(2, round(6 * self._scale)) if margin is None else int(margin)
        rect = self._visible_pet_screen_rect(x, y, precise=precise)
        area_left = area.left()
        area_top = area.top()
        area_right = area.left() + area.width()
        area_bottom = area.top() + area.height()
        dx = 0
        dy = 0
        if rect.left() < area_left + margin:
            dx = round(area_left + margin - rect.left())
        elif rect.right() > area_right - margin:
            dx = round(area_right - margin - rect.right())
        if rect.top() < area_top + margin:
            dy = round(area_top + margin - rect.top())
        elif rect.bottom() > area_bottom - margin:
            dy = round(area_bottom - margin - rect.bottom())
        return int(x + dx), int(y + dy)

    def _snap_to_screen_edge(self):
        if not self._edge_snap_enabled:
            self._edge_stick_side = None
            return None
        area = self._available_screen_area()
        if not area:
            self._edge_stick_side = None
            return None
        threshold = max(8, int(self._edge_snap_threshold))
        margin = max(2, round(4 * self._scale))
        rect = self._visible_pet_screen_rect(precise=True)
        area_left = area.left()
        area_top = area.top()
        area_right = area.left() + area.width()
        area_bottom = area.top() + area.height()
        next_x = self.x()
        next_y = self.y()
        snapped_side = None

        if rect.left() <= area_left + threshold:
            next_x += round(area_left - rect.left())
            snapped_side = "left"
        elif rect.right() >= area_right - threshold:
            next_x += round(area_right - rect.right())
            snapped_side = "right"

        if rect.top() <= area_top + threshold:
            next_y += round(area_top + margin - rect.top())
        elif rect.bottom() >= area_bottom - threshold:
            next_y += round(area_bottom - margin - rect.bottom())

        if next_x != self.x() or next_y != self.y():
            self.move(next_x, next_y)
        self._edge_stick_side = snapped_side
        return snapped_side

    def _edge_action_name(self, side):
        if side == "left" and "edge_left" in self._actions:
            return "edge_left"
        if side == "right" and "edge_right" in self._actions:
            return "edge_right"
        return None

    def stick_to_edge(self, side):
        edge_action = self._edge_action_name(side)
        if not edge_action:
            return False
        self.play_action(edge_action, transition=False)
        area = self._available_screen_area()
        if area:
            rect = self._visible_pet_screen_rect(precise=True)
            next_x = self.x()
            if side == "left":
                next_x += round(area.left() - rect.left())
            else:
                next_x += round(area.left() + area.width() - rect.right())
            next_x, next_y = self.fit_position_to_visible_screen(next_x, self.y(), margin=0, precise=True)
            if next_x != self.x() or next_y != self.y():
                self.move(next_x, next_y)
        self._edge_stick_side = side
        return True

    def _move_within_screen(self, dx, dy, turn_on_edge=True):
        area = self._available_screen_area()
        if not area:
            self.move(self.x() + dx, self.y() + dy)
            return dx
        old_x = self.x()
        raw_x = self.x() + dx
        raw_y = self.y() + dy
        next_x, next_y = self.fit_position_to_visible_screen(raw_x, raw_y)
        hit_horizontal_edge = bool(dx and next_x != int(raw_x))
        if turn_on_edge and hit_horizontal_edge and self._action_name in {"walk_left", "walk_right"}:
            self._walk_visual_offset_x = 0.0
            self._turn_walk_direction()
            return 0
        self.move(next_x, next_y)
        return next_x - old_x

    def mousePressEvent(self, event):
        if event.button() in {Qt.LeftButton, Qt.RightButton} and (self._corner_hidden or self._is_corner_animating()):
            self.interaction_requested.emit("pet_press")
            self.reveal_from_corner()
            self._ignore_next_click_release = True
            event.accept()
            return
        if event.button() == Qt.RightButton and (self._choice_options or self._bubble_text):
            self.interaction_requested.emit("pet_press")
            self._reset_autonomy_timers(hide_delay=max(self._next_corner_hide, 65000))
            self.hide_choice_bubble()
            self._clear_bubble()
            if self._action_name not in {"idle", "__transition__"}:
                self.play_action("idle", transition=False)
            self._ignore_next_click_release = True
            event.accept()
            return
        if event.button() == Qt.RightButton and self._action_name not in {"idle", "__transition__"}:
            self.interaction_requested.emit("pet_press")
            self._reset_autonomy_timers(hide_delay=max(self._next_corner_hide, 65000))
            self.play_action("idle", transition=False)
            self._ignore_next_click_release = True
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            self.interaction_requested.emit("pet_press")
            self._reset_autonomy_timers(hide_delay=max(self._next_corner_hide, 65000))
            if self._choice_options:
                self._choice_pressed_key = self._choice_key_at(event.position())
                self._choice_pressing = bool(self._choice_pressed_key)
                if not self._choice_pressing:
                    self.hide_choice_bubble()
                    self._ignore_next_click_release = True
                event.accept()
                return
            self._click_action_token += 1
            self._press_position = event.globalPosition().toPoint()
            self._drag_position = self._press_position - self.frameGeometry().topLeft()
            self._is_dragging = False
            self._drag_hold_frame = None
            event.accept()

    def mouseMoveEvent(self, event):
        if self._choice_options:
            hover_key = self._choice_key_at(event.position())
            if hover_key != self._choice_hover_key:
                self._choice_hover_key = hover_key
                self.update()
            event.accept()
            return
        if event.buttons() & Qt.LeftButton:
            current_position = event.globalPosition().toPoint()
            if not self._is_dragging:
                if (current_position - self._press_position).manhattanLength() < QApplication.startDragDistance():
                    event.accept()
                    return
                self._is_dragging = True
                self._click_action_token += 1
                self._begin_drag_hold()
                self.interaction_requested.emit("drag")
            self.move(current_position - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._choice_options:
                key = self._choice_key_at(event.position()) if self._choice_pressing else ""
                if key != self._choice_pressed_key:
                    key = ""
                self._choice_pressing = False
                self._choice_pressed_key = ""
                if key:
                    self.hide_choice_bubble()
                    self.interaction_requested.emit(f"choice:{key}")
                else:
                    self.hide_choice_bubble()
                event.accept()
                return
            if self._is_dragging:
                self._is_dragging = False
                self._click_action_token += 1
                self._drag_hold_frame = None
                snapped_side = self._snap_to_screen_edge()
                edge_action = self._edge_action_name(snapped_side)
                if edge_action:
                    self.stick_to_edge(snapped_side)
                else:
                    self.play_action("idle", transition=False)
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
        if self._corner_hidden or self._is_corner_animating():
            self.reveal_from_corner()
            event.accept()
            return
        self._reset_autonomy_timers(hide_delay=max(self._next_corner_hide, 65000))
        if self._action_name != "wave":
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
        self.interaction_requested.emit("quick_menu")

    def _choice_key_at(self, point):
        for key, _label, rect in self._choice_button_rects:
            center = rect.center()
            radius = rect.width() / 2
            dx = point.x() - center.x()
            dy = point.y() - center.y()
            if dx * dx + dy * dy <= radius * radius:
                return key
        return ""

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            step = 0.05 if event.angleDelta().y() > 0 else -0.05
            self.set_pet_scale(self._scale + step)
            event.accept()
            return
        super().wheelEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        panel_action = menu.addAction("打开控制面板")
        panel_action.triggered.connect(lambda checked=False: self.interaction_requested.emit("show_panel"))
        hide_action = menu.addAction("隐藏桌宠")
        hide_action.triggered.connect(lambda checked=False: self.interaction_requested.emit("hide_pet"))
        menu.addSeparator()

        action_menu = menu.addMenu("动作")
        for action_name in ("idle", "blink", "touch", "walk_left", "walk_right", "edge_left", "edge_right", "jump", "wave", "sleep"):
            if action_name not in self._actions:
                continue
            action = action_menu.addAction(ACTION_LABELS.get(action_name, action_name))
            action.triggered.connect(lambda checked=False, name=action_name: self._play_menu_action(name))

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
        edge_snap_action = menu.addAction("贴边吸附")
        edge_snap_action.setCheckable(True)
        edge_snap_action.setChecked(self._edge_snap_enabled)
        edge_snap_action.triggered.connect(lambda checked=False: self.set_edge_snap(checked))
        menu.addSeparator()
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(lambda checked=False: self.interaction_requested.emit("quit_app"))
        menu.exec(event.globalPos())

    def _play_menu_action(self, action_name):
        if action_name == "edge_left":
            self.stick_to_edge("left")
        elif action_name == "edge_right":
            self.stick_to_edge("right")
        else:
            self.play_action(action_name)
        self.interaction_requested.emit(action_name)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_clock"):
            self._clock.restart()
        if hasattr(self, "_timer") and not self._timer.isActive():
            self._timer.start(self._timer_interval_for_action(self._current_action()))

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._corner_dot_mode:
            self._draw_corner_dot(painter)
            return
        scale = self._scale
        content_left = self._walk_visual_padding + round(self._walk_visual_offset_x + self._pose_visual_offset.x())

        if not self._is_edge_action():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 82))
            painter.drawEllipse(QRectF(content_left + (self._content_width - 230 * scale) / 2, self.height() - 46 * scale, 230 * scale, 25 * scale))

        frame = self._current_frame()
        if frame:
            self._draw_frame(painter, frame)
        else:
            self._draw_static_hint(painter)

        if self._choice_options:
            self._draw_choice_bubble(painter, content_left)
            return
        if not self._bubble_text:
            return
        self._draw_bubble(painter, content_left)

    def _current_frame(self):
        if self._is_dragging and self._drag_hold_frame and not self._drag_hold_frame.isNull():
            return self._drag_hold_frame
        action = self._current_action()
        if not action or not action.frames:
            return None
        return action.frames[self._frame_index % len(action.frames)]

    def _draw_frame(self, painter, frame):
        painter.drawPixmap(self._frame_draw_rect(frame).topLeft(), frame)

    def _draw_corner_dot(self, painter):
        size = min(self.width(), self.height())
        rect = QRectF(4, 4, size - 8, size - 8)
        pulse = 0.5 + 0.5 * math.sin((self._choice_phase or 0.0) * 0.8)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(32, 82, 104, 58))
        painter.drawEllipse(rect.adjusted(2, 5, -2, 5))

        glow = QRadialGradient(rect.center(), rect.width() * 0.72)
        glow.setColorAt(0.0, QColor(255, 255, 255, 250))
        glow.setColorAt(0.42, QColor(187, 245, 255, 238))
        glow.setColorAt(0.76, QColor(113, 217, 237, 226))
        glow.setColorAt(1.0, QColor(255, 164, 203, 220))
        painter.setPen(QPen(QColor(126, 232, 255, 190 + int(42 * pulse)), max(1, round(2 * self._scale))))
        painter.setBrush(glow)
        painter.drawEllipse(rect)

        highlight = QRectF(rect.left() + rect.width() * 0.24, rect.top() + rect.height() * 0.16, rect.width() * 0.34, rect.height() * 0.18)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 160))
        painter.drawEllipse(highlight)

        paw_color = QColor(36, 86, 111, 190)
        painter.setBrush(paw_color)
        painter.setPen(Qt.NoPen)
        cx = rect.center().x()
        cy = rect.center().y() + rect.height() * 0.10
        pad = rect.width() * 0.065
        painter.drawEllipse(QRectF(cx - pad * 1.55, cy - pad * 0.55, pad * 3.1, pad * 2.35))
        for dx, dy in ((-2.1, -2.1), (-0.7, -2.7), (0.7, -2.7), (2.1, -2.1)):
            painter.drawEllipse(QRectF(cx + dx * pad - pad * 0.52, cy + dy * pad - pad * 0.52, pad * 1.04, pad * 1.04))
        painter.restore()

    def _is_edge_action(self):
        return self._action_name in {"edge_left", "edge_right"}

    def _draw_static_hint(self, painter):
        if not self.fallback_pixmap.isNull():
            self._draw_frame(painter, self.fallback_pixmap)
        painter.setPen(QPen(QColor(126, 232, 255), 1))
        painter.setBrush(QColor(12, 24, 38, 185))
        content_left = self._walk_visual_padding + round(self._walk_visual_offset_x + self._pose_visual_offset.x())
        painter.drawRoundedRect(QRectF(content_left + round(44 * self._scale), self.height() - 76 * self._scale, self._content_width - round(88 * self._scale), 38 * self._scale), 10, 10)
        painter.setPen(QColor(222, 248, 255))
        painter.drawText(
            QRectF(content_left + round(54 * self._scale), self.height() - 72 * self._scale, self._content_width - round(108 * self._scale), 30 * self._scale),
            Qt.AlignCenter | Qt.TextWordWrap,
            "请放入真实动画帧：assets/polar_bear/real_actions",
        )

    def _draw_choice_bubble(self, painter, content_left):
        scale = self._scale
        margin = max(10, round(18 * scale))
        pet_rect = self._visible_pet_rect()
        count = len(self._choice_options)
        button_size = max(56, round(84 * scale))
        title_width = max(150, round(230 * scale))
        title_height = max(34, round(44 * scale))
        center_x = pet_rect.center().x()
        center_y = pet_rect.top() + pet_rect.height() * 0.31
        max_radius_x = max(button_size * 1.25, self.width() / 2 - margin - button_size / 2)
        radius_x = min(max_radius_x, max(button_size * 1.55, pet_rect.width() * 0.68 + button_size * 0.9))
        radius_y = max(button_size * 1.15, min(self.height() * 0.28, pet_rect.height() * 0.30 + button_size * 0.55))
        angle_sets = {
            1: [-90],
            2: [-132, -48],
            3: [-148, -90, -32],
            4: [-156, -108, -58, -10],
            5: [-166, -126, -86, -45, -4],
            6: [-168, -132, -96, -60, -24, 18],
            7: [-172, -138, -104, -70, -36, -2, 38],
            8: [-174, -142, -110, -78, -46, -14, 24, 62],
        }
        angles = angle_sets.get(count, angle_sets[8])
        ease = 1 - pow(1 - self._choice_progress, 3)
        pop_scale = 0.58 + 0.42 * ease
        self._choice_button_rects = []

        painter.save()
        painter.setOpacity(0.65 + 0.35 * ease)
        orbit_rect = QRectF(
            center_x - radius_x - button_size * 0.55,
            center_y - radius_y - button_size * 0.55,
            radius_x * 2 + button_size * 1.1,
            radius_y * 2 + button_size * 1.1,
        )
        halo = QRadialGradient(QPointF(center_x, center_y), max(radius_x, radius_y) + button_size)
        halo.setColorAt(0.0, QColor(255, 255, 255, 12))
        halo.setColorAt(0.56, QColor(126, 232, 255, 28))
        halo.setColorAt(0.82, QColor(255, 173, 200, 24))
        halo.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(orbit_rect)

        pulse = 0.5 + 0.5 * math.sin(self._choice_phase * 0.9)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 92), max(1, round(2.2 * scale))))
        painter.drawEllipse(orbit_rect.adjusted(button_size * 0.18, button_size * 0.18, -button_size * 0.18, -button_size * 0.18))
        painter.setPen(QPen(QColor(126, 232, 255, 74 + int(46 * pulse)), max(1, round(1.4 * scale))))
        painter.drawEllipse(orbit_rect.adjusted(button_size * 0.34, button_size * 0.34, -button_size * 0.34, -button_size * 0.34))

        title_rect = QRectF(
            center_x - title_width / 2,
            max(margin, center_y - radius_y - button_size * 0.94 - title_height),
            title_width,
            title_height,
        )
        title_shadow = QRectF(title_rect).adjusted(0, max(2, round(4 * scale)), 0, max(2, round(4 * scale)))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(53, 106, 135, 34))
        painter.drawRoundedRect(title_shadow, title_height / 2, title_height / 2)
        title_gradient = QLinearGradient(title_rect.topLeft(), title_rect.bottomRight())
        title_gradient.setColorAt(0.0, QColor(255, 255, 255, 244))
        title_gradient.setColorAt(0.48, QColor(227, 250, 255, 232))
        title_gradient.setColorAt(1.0, QColor(255, 229, 241, 228))
        painter.setPen(QPen(QColor(126, 232, 255, 185), 1.4))
        painter.setBrush(title_gradient)
        painter.drawRoundedRect(title_rect, title_height / 2, title_height / 2)
        painter.setPen(QColor("#204a61"))
        painter.setFont(QFont("Microsoft YaHei UI", max(10, round(12.5 * scale)), QFont.Black))
        painter.drawText(title_rect, Qt.AlignCenter, self._choice_title)
        union_rect = QRectF(title_rect).adjusted(-10, -10, 10, 10)

        for index, (key, label) in enumerate(self._choice_options):
            angle = math.radians(angles[index])
            wave = math.sin(self._choice_phase + index * 0.72) * max(1.2, 4.2 * scale)
            cx = center_x + math.cos(angle) * radius_x * pop_scale
            cy = center_y + math.sin(angle) * radius_y * pop_scale + wave
            hovered = key == self._choice_hover_key
            size = button_size * (1.11 if hovered else 1.0)
            rect = QRectF(cx - size / 2, cy - size / 2, size, size)
            rect.moveLeft(max(margin, min(self.width() - margin - rect.width(), rect.left())))
            rect.moveTop(max(margin, min(self.height() - margin - rect.height(), rect.top())))
            self._choice_button_rects.append((key, label, QRectF(rect)))

            connector_alpha = 74 if hovered else 38
            painter.setPen(QPen(QColor(126, 232, 255, connector_alpha), max(1, round(1.1 * scale))))
            painter.drawLine(QPointF(center_x, center_y), rect.center())

            glow = QRadialGradient(rect.center(), rect.width() * 0.82)
            glow.setColorAt(0.0, QColor(255, 255, 255, 0))
            glow.setColorAt(0.55, QColor(126, 232, 255, 54 if hovered else 28))
            glow.setColorAt(1.0, QColor(255, 142, 188, 84 if hovered else 36))
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(rect.adjusted(-10, -10, 10, 10))

            glass = QRadialGradient(
                QPointF(rect.left() + rect.width() * 0.32, rect.top() + rect.height() * 0.24),
                rect.width() * 0.82,
            )
            if hovered:
                glass.setColorAt(0.0, QColor(255, 255, 255, 250))
                glass.setColorAt(0.36, QColor(116, 224, 238, 236))
                glass.setColorAt(0.72, QColor(132, 225, 211, 230))
                glass.setColorAt(1.0, QColor(255, 143, 188, 238))
                border = QColor(255, 255, 255, 238)
                text_color = QColor("#ffffff")
                icon_color = QColor("#ffffff")
            else:
                glass.setColorAt(0.0, QColor(255, 255, 255, 252))
                glass.setColorAt(0.42, QColor(233, 250, 255, 238))
                glass.setColorAt(0.78, QColor(210, 244, 250, 226))
                glass.setColorAt(1.0, QColor(255, 232, 243, 230))
                border = QColor(138, 224, 241, 202)
                text_color = QColor("#24536c")
                icon_color = QColor("#46bcd8")
            painter.setPen(QPen(border, 1.6 if hovered else 1.2))
            painter.setBrush(glass)
            painter.drawEllipse(rect)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 124))
            painter.drawEllipse(
                QRectF(
                    rect.left() + rect.width() * 0.22,
                    rect.top() + rect.height() * 0.12,
                    rect.width() * 0.36,
                    rect.height() * 0.18,
                )
            )

            icon_rect = QRectF(
                rect.left() + rect.width() * 0.30,
                rect.top() + rect.height() * 0.22,
                rect.width() * 0.40,
                rect.height() * 0.30,
            )
            self._draw_choice_icon(painter, icon_rect, key, icon_color, hovered)

            painter.setPen(text_color)
            painter.setFont(QFont("Microsoft YaHei UI", max(8, round(9.2 * scale)), QFont.Black))
            painter.drawText(
                QRectF(rect.left() + 4, rect.top() + rect.height() * 0.56, rect.width() - 8, rect.height() * 0.34),
                Qt.AlignCenter | Qt.TextWordWrap,
                self._choice_display_label(label),
            )
            union_rect = union_rect.united(rect.adjusted(-14, -14, 14, 14))

        self._choice_panel_rect = union_rect
        painter.restore()

    def _choice_display_label(self, label):
        label = str(label or "").replace(" ", "")
        return label if len(label) <= 4 else label[:4]

    def _draw_choice_icon(self, painter, rect, key, color, hovered=False):
        pen_width = max(1.3, rect.width() * 0.09)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        key = str(key)

        if key.startswith("chat"):
            bubble = rect.adjusted(rect.width() * 0.04, rect.height() * 0.08, -rect.width() * 0.04, -rect.height() * 0.14)
            painter.drawRoundedRect(bubble, rect.width() * 0.18, rect.width() * 0.18)
            painter.drawLine(QPointF(bubble.left() + bubble.width() * 0.34, bubble.bottom()), QPointF(bubble.left() + bubble.width() * 0.24, bubble.bottom() + rect.height() * 0.18))
        elif key.startswith("feed") or key == "buy_food":
            bowl = QRectF(rect.left(), rect.top() + rect.height() * 0.38, rect.width(), rect.height() * 0.44)
            painter.drawArc(bowl, 180 * 16, 180 * 16)
            painter.drawLine(QPointF(bowl.left() + bowl.width() * 0.16, bowl.center().y()), QPointF(bowl.right() - bowl.width() * 0.16, bowl.center().y()))
            painter.drawEllipse(QRectF(rect.center().x() - rect.width() * 0.14, rect.top() + rect.height() * 0.10, rect.width() * 0.28, rect.height() * 0.24))
        elif key == "course":
            book = rect.adjusted(rect.width() * 0.08, rect.height() * 0.02, -rect.width() * 0.08, -rect.height() * 0.02)
            painter.drawRoundedRect(book, rect.width() * 0.10, rect.width() * 0.10)
            painter.drawLine(book.center().x(), book.top() + rect.height() * 0.10, book.center().x(), book.bottom() - rect.height() * 0.10)
        elif key == "panel":
            screen = rect.adjusted(rect.width() * 0.04, 0, -rect.width() * 0.04, -rect.height() * 0.12)
            painter.drawRoundedRect(screen, rect.width() * 0.10, rect.width() * 0.10)
            painter.drawLine(screen.left() + screen.width() * 0.20, screen.top() + screen.height() * 0.34, screen.right() - screen.width() * 0.18, screen.top() + screen.height() * 0.34)
            painter.drawLine(screen.left() + screen.width() * 0.20, screen.top() + screen.height() * 0.62, screen.right() - screen.width() * 0.34, screen.top() + screen.height() * 0.62)
        elif key == "back":
            painter.drawLine(QPointF(rect.left() + rect.width() * 0.70, rect.top() + rect.height() * 0.18), QPointF(rect.left() + rect.width() * 0.30, rect.center().y()))
            painter.drawLine(QPointF(rect.left() + rect.width() * 0.30, rect.center().y()), QPointF(rect.left() + rect.width() * 0.70, rect.bottom() - rect.height() * 0.18))
            painter.drawLine(QPointF(rect.left() + rect.width() * 0.36, rect.center().y()), QPointF(rect.right() - rect.width() * 0.16, rect.center().y()))
        elif key == "touch":
            painter.drawEllipse(QRectF(rect.left() + rect.width() * 0.26, rect.top() + rect.height() * 0.08, rect.width() * 0.48, rect.height() * 0.42))
            painter.drawLine(QPointF(rect.center().x(), rect.top() + rect.height() * 0.54), QPointF(rect.center().x(), rect.bottom() - rect.height() * 0.04))
            painter.drawLine(QPointF(rect.left() + rect.width() * 0.18, rect.top() + rect.height() * 0.64), QPointF(rect.right() - rect.width() * 0.18, rect.top() + rect.height() * 0.64))
        else:
            cx = rect.center().x()
            cy = rect.center().y()
            radius_x = rect.width() * 0.34
            radius_y = rect.height() * 0.34
            painter.drawLine(QPointF(cx - radius_x, cy), QPointF(cx + radius_x, cy))
            painter.drawLine(QPointF(cx, cy - radius_y), QPointF(cx, cy + radius_y))
            painter.drawLine(QPointF(cx - radius_x * 0.58, cy - radius_y * 0.58), QPointF(cx + radius_x * 0.58, cy + radius_y * 0.58))
            painter.drawLine(QPointF(cx + radius_x * 0.58, cy - radius_y * 0.58), QPointF(cx - radius_x * 0.58, cy + radius_y * 0.58))
        painter.restore()

    def _draw_bubble(self, painter, content_left):
        scale = self._scale
        margin = max(9, round(16 * scale))
        pet_rect = self._visible_pet_rect()
        gap = max(10, round(20 * scale))
        preferred_width = max(250, round((560 if self._bubble_is_chat else 340) * scale))
        min_width = max(220 if self._bubble_is_chat else 150, round((320 if self._bubble_is_chat else 210) * scale))
        text_margin = max(8, round(10 * scale))
        max_bubble_height = max(108 if self._bubble_is_chat else 82, min(self.height() - margin * 2, round((300 if self._bubble_is_chat else 150) * scale)))
        text_font = QFont("Microsoft YaHei UI", max(9, round(11.4 * scale)), QFont.DemiBold if self._bubble_is_chat else QFont.Normal)
        painter.setFont(text_font)

        def bubble_height(width):
            text_width = max(1, width - text_margin * 2)
            measured = painter.boundingRect(
                QRectF(0, 0, text_width, 1000),
                Qt.AlignCenter | Qt.TextWordWrap,
                self._bubble_text,
            )
            height = max(max(50, round(62 * scale)), math.ceil(measured.height()) + text_margin * 2)
            if self._bubble_is_chat:
                height += max(10, round(14 * scale))
            return min(height, max_bubble_height)

        right_space = self.width() - pet_rect.right() - gap - margin
        left_space = pet_rect.left() - gap - margin
        max_width = max(min_width, self.width() - margin * 2)
        side = self._bubble_layout_side
        width = float(self._bubble_layout_width)
        if not side or width <= 0:
            if self._bubble_is_chat:
                side = "right"
                width = max(min_width, min(preferred_width, max(right_space, min_width)))
            elif right_space >= min_width:
                side = "right"
                width = max(min_width, min(preferred_width, right_space))
            elif left_space >= min_width:
                side = "left"
                width = max(min_width, min(preferred_width, left_space))
            else:
                side = "center"
                width = min(max(min_width, preferred_width), max_width)
            self._bubble_layout_side = side
            self._bubble_layout_width = float(width)
        else:
            width = max(min_width, min(width, max_width))

        if side == "right":
            x = pet_rect.right() + gap
        elif side == "left":
            x = pet_rect.left() - gap - width
        else:
            x = pet_rect.center().x() - width / 2
        x = max(margin, min(self.width() - margin - width, x))
        height = bubble_height(width)
        head_y = pet_rect.top() + pet_rect.height() * (0.02 if self._bubble_is_chat else 0.11)
        y = max(margin, min(self.height() - margin - height, head_y))
        bubble_rect = QRectF(x, y, width, height)
        self._bubble_draw_rect = QRectF(bubble_rect)

        shadow_rect = QRectF(bubble_rect).adjusted(0, max(2, round(5 * scale)), 0, max(2, round(5 * scale)))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(13, 32, 48, 62))
        painter.drawRoundedRect(shadow_rect, max(8, round(13 * scale)), max(8, round(13 * scale)))

        painter.setPen(QPen(QColor(126, 232, 255, 230), max(1, round(2 * scale))))
        gradient = QLinearGradient(bubble_rect.topLeft(), bubble_rect.bottomRight())
        gradient.setColorAt(0.0, QColor(18, 53, 76, 238))
        gradient.setColorAt(0.56, QColor(17, 69, 91, 234))
        gradient.setColorAt(1.0, QColor(26, 80, 96, 230))
        painter.setBrush(gradient)
        painter.drawRoundedRect(bubble_rect, max(8, round(12 * scale)), max(8, round(12 * scale)))
        painter.setPen(QColor(235, 250, 255))
        text_rect = bubble_rect.adjusted(text_margin, round(6 * scale), -text_margin, -round(6 * scale))
        if len(self._bubble_pages) > 1:
            text_rect.adjust(0, 0, 0, -max(13, round(16 * scale)))
        painter.drawText(
            text_rect,
            Qt.AlignCenter | Qt.TextWordWrap,
            self._bubble_text,
        )
        if len(self._bubble_pages) > 1:
            painter.setPen(QColor(171, 232, 245))
            painter.setFont(QFont("Microsoft YaHei UI", max(7, round(8.5 * scale)), QFont.Bold))
            painter.drawText(
                QRectF(
                    bubble_rect.right() - max(42, round(50 * scale)),
                    bubble_rect.bottom() - max(18, round(21 * scale)),
                    max(34, round(42 * scale)),
                    max(14, round(17 * scale)),
                ),
                Qt.AlignRight | Qt.AlignVCenter,
                f"{self._bubble_page_index + 1}/{len(self._bubble_pages)}",
            )
