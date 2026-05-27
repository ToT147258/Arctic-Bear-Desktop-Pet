import ctypes
import random
import sys
from datetime import datetime
from math import cos, pi, sin
from pathlib import Path
from ctypes import wintypes

from PySide6.QtCore import QEasingCurve, QEvent, QPointF, QRect, QRectF, QSize, Qt, QPropertyAnimation, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QImage, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.modules.backpack import BackpackPage
from src.modules.chat import ChatPage
from src.modules.growth import GrowthPage
from src.modules.interaction import InteractionPage
from src.modules.notification import NotificationPage
from src.modules.settings import SettingsPage
from src.pet_data import PetDataStore
from src.pet_window import PolarBearPetWindow


WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
PET_TOGGLE_HOTKEY_ID = 0x1472
DEFAULT_PET_TOGGLE_HOTKEY_TEXT = "Ctrl+Alt+B"


def _trim_transparent_pixmap(pixmap, margin=6):
    if pixmap.isNull():
        return pixmap
    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    width = image.width()
    height = image.height()
    left = width
    top = height
    right = -1
    bottom = -1
    for y in range(height):
        for x in range(width):
            if image.pixelColor(x, y).alpha() > 8:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right < left or bottom < top:
        return pixmap
    left = max(0, left - margin)
    top = max(0, top - margin)
    right = min(width - 1, right + margin)
    bottom = min(height - 1, bottom + margin)
    return pixmap.copy(QRect(left, top, right - left + 1, bottom - top + 1))


def _load_first_pixmap(paths, trim=True):
    for path in paths:
        if path.exists():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return _trim_transparent_pixmap(pixmap) if trim else pixmap
    return QPixmap()


def _enum_value(value):
    try:
        return int(value)
    except TypeError:
        return int(value.value)


def _qt_key_to_vk(key):
    key = _enum_value(key)
    key_a = _enum_value(Qt.Key.Key_A)
    key_z = _enum_value(Qt.Key.Key_Z)
    key_0 = _enum_value(Qt.Key.Key_0)
    key_9 = _enum_value(Qt.Key.Key_9)
    key_f1 = _enum_value(Qt.Key.Key_F1)
    key_f24 = _enum_value(Qt.Key.Key_F24)
    if key_a <= key <= key_z or key_0 <= key <= key_9:
        return key
    if key_f1 <= key <= key_f24:
        return 0x70 + (key - key_f1)
    special_keys = {
        Qt.Key.Key_Space: 0x20,
        Qt.Key.Key_Tab: 0x09,
        Qt.Key.Key_Backspace: 0x08,
        Qt.Key.Key_Return: 0x0D,
        Qt.Key.Key_Enter: 0x0D,
        Qt.Key.Key_Escape: 0x1B,
        Qt.Key.Key_Insert: 0x2D,
        Qt.Key.Key_Delete: 0x2E,
        Qt.Key.Key_Home: 0x24,
        Qt.Key.Key_End: 0x23,
        Qt.Key.Key_PageUp: 0x21,
        Qt.Key.Key_PageDown: 0x22,
        Qt.Key.Key_Left: 0x25,
        Qt.Key.Key_Up: 0x26,
        Qt.Key.Key_Right: 0x27,
        Qt.Key.Key_Down: 0x28,
    }
    for qt_key, vk in special_keys.items():
        if key == _enum_value(qt_key):
            return vk
    return None


def _normalized_hotkey_text(hotkey_text):
    sequence = QKeySequence(str(hotkey_text or "").strip())
    if sequence.isEmpty() or sequence.count() != 1:
        return ""
    return sequence.toString(QKeySequence.SequenceFormat.PortableText)


def _windows_hotkey_parts(hotkey_text):
    sequence = QKeySequence(hotkey_text)
    if sequence.isEmpty() or sequence.count() != 1:
        return None
    combination = sequence[0]
    modifiers = combination.keyboardModifiers()
    key = combination.key()
    vk = _qt_key_to_vk(key)
    if vk is None:
        return None
    win_modifiers = 0
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        win_modifiers |= MOD_CONTROL
    if modifiers & Qt.KeyboardModifier.AltModifier:
        win_modifiers |= MOD_ALT
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        win_modifiers |= MOD_SHIFT
    if modifiers & Qt.KeyboardModifier.MetaModifier:
        win_modifiers |= MOD_WIN
    if not win_modifiers:
        return None
    return win_modifiers, vk


class AnimatedDashboardRoot(QWidget):
    def __init__(self):
        super().__init__()
        rng = random.Random(18)
        self._phase = 0.0
        self._flakes = [
            (rng.random(), rng.random(), rng.uniform(0.5, 1.7), rng.uniform(0.18, 0.7))
            for _ in range(34)
        ]
        self.setAttribute(Qt.WA_StaticContents)

    def _tick(self):
        if not self.isVisible():
            return
        self._phase = (self._phase + 0.028) % (pi * 2)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        bg = QLinearGradient(0, 0, rect.width(), rect.height())
        bg.setColorAt(0.0, QColor("#f8fcff"))
        bg.setColorAt(0.38, QColor("#eaf8ff"))
        bg.setColorAt(0.72, QColor("#fff2f8"))
        bg.setColorAt(1.0, QColor("#fff8e7"))
        painter.fillRect(rect, bg)

        self._draw_ribbon(painter, QColor(100, 201, 232, 54), -120, 84, 0.0)
        self._draw_ribbon(painter, QColor(255, 173, 200, 58), -70, 262, 1.7)
        self._draw_ribbon(painter, QColor(255, 211, 116, 42), -180, rect.height() - 146, 3.1)

        painter.setPen(QPen(QColor(255, 255, 255, 160), 2))
        for i, (fx, fy, size, speed) in enumerate(self._flakes):
            x = fx * rect.width() + sin(self._phase * speed + i) * 18
            y = (fy * rect.height() + self._phase * 42 * speed) % max(1, rect.height())
            radius = size * 2.5
            painter.drawLine(QPointF(x - radius, y), QPointF(x + radius, y))
            painter.drawLine(QPointF(x, y - radius), QPointF(x, y + radius))

    def _draw_ribbon(self, painter, color, x_offset, y_base, phase):
        path = QPainterPath()
        width = self.width()
        y_shift = sin(self._phase + phase) * 16
        path.moveTo(x_offset, y_base + y_shift)
        path.cubicTo(width * 0.22, y_base - 80 + y_shift, width * 0.42, y_base + 92, width * 0.68, y_base + 10)
        path.cubicTo(width * 0.88, y_base - 52, width + 80, y_base + 68 + y_shift, width + 160, y_base + 10)
        painter.setPen(QPen(color, 36, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)


class MascotStage(QWidget):
    def __init__(self, asset_root):
        super().__init__()
        self.setObjectName("petStage")
        self._phase = 0.0
        self._pixmap = QPixmap()
        self._scaled_pixmap = QPixmap()
        self._scaled_size = QSize()
        for path in (
            asset_root / "polar-bear-flat-lively.png",
            asset_root / "polar-bear-premium.png",
            asset_root / "polar-bear-realistic.png",
        ):
            if path.exists():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    self._pixmap = pixmap
                    break
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.CoarseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)

    def sizeHint(self):
        return QSize(232, 268)

    def minimumSizeHint(self):
        return QSize(140, 220)

    def _tick(self):
        if not self.isVisible():
            return
        self._phase = (self._phase + 0.056) % (pi * 2)
        self.update()

    def _scaled_bear(self, target_size):
        if self._pixmap.isNull() or target_size.isEmpty():
            return QPixmap()
        if self._scaled_pixmap.isNull() or self._scaled_size != target_size:
            self._scaled_pixmap = self._pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._scaled_size = QSize(target_size)
        return self._scaled_pixmap

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg.setColorAt(0.0, QColor("#ffffff"))
        bg.setColorAt(0.55, QColor("#eaf9ff"))
        bg.setColorAt(1.0, QColor("#fff1f7"))
        painter.setBrush(bg)
        painter.setPen(QPen(QColor("#b7e5f2"), 1.3))
        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(QPen(QColor(255, 173, 200, 170), 2))
        for i in range(7):
            x = rect.left() + 22 + i * 30 + sin(self._phase + i) * 4
            y = rect.top() + 25 + cos(self._phase * 0.8 + i) * 7
            painter.drawLine(QPointF(x - 5, y), QPointF(x + 5, y))
            painter.drawLine(QPointF(x, y - 5), QPointF(x, y + 5))

        painter.setPen(QColor("#ff8ebc"))
        title_font = QFont("Microsoft YaHei UI", 9, QFont.Black)
        painter.setFont(title_font)
        painter.drawText(QRectF(rect.left(), rect.top() + 12, rect.width(), 22), Qt.AlignCenter, "小熊在线")

        if not self._pixmap.isNull():
            bob = sin(self._phase) * 6
            target = QRectF(rect.center().x() - 82, rect.top() + 54 + bob, 164, 176)
            scaled = self._scaled_bear(target.size().toSize())
            image_rect = QRectF(
                rect.center().x() - scaled.width() / 2,
                target.top() + (target.height() - scaled.height()) / 2,
                scaled.width(),
                scaled.height(),
            )
            painter.setBrush(QColor(61, 94, 121, 36))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(rect.center().x() - 56, rect.bottom() - 34, 112, 18))
            painter.drawPixmap(image_rect.toRect(), scaled)

        painter.setPen(QColor("#5f8295"))
        painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.DemiBold))
        painter.drawText(QRectF(rect.left(), rect.bottom() - 32, rect.width(), 20), Qt.AlignCenter, "陪伴值实时同步")


class SidebarMascotCard(QWidget):
    def __init__(self, asset_root):
        super().__init__()
        self.setObjectName("sidebarMascotCard")
        self._phase = 0.0
        self._pixmap = QPixmap()
        self._scaled_pixmap = QPixmap()
        self._scaled_size = QSize()
        for path in (
            asset_root / "polar-bear-flat-lively.png",
            asset_root / "polar-bear-premium.png",
            asset_root / "polar-bear-realistic.png",
        ):
            if path.exists():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    self._pixmap = pixmap
                    break
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.CoarseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(90)

    def sizeHint(self):
        return QSize(202, 136)

    def _tick(self):
        if not self.isVisible():
            return
        self._phase = (self._phase + 0.058) % (pi * 2)
        self.update()

    def _scaled_bear(self, target_size):
        if self._pixmap.isNull() or target_size.isEmpty():
            return QPixmap()
        if self._scaled_pixmap.isNull() or self._scaled_size != target_size:
            self._scaled_pixmap = self._pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._scaled_size = QSize(target_size)
        return self._scaled_pixmap

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg.setColorAt(0.0, QColor("#ffffff"))
        bg.setColorAt(0.56, QColor("#e9fbff"))
        bg.setColorAt(1.0, QColor("#fff1f7"))
        painter.setBrush(bg)
        painter.setPen(QPen(QColor("#a7def0"), 1.2))
        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(QPen(QColor(100, 201, 232, 90), 3, Qt.SolidLine, Qt.RoundCap))
        wave = QPainterPath()
        base_y = rect.top() + 36 + sin(self._phase) * 4
        wave.moveTo(rect.left() + 12, base_y)
        wave.cubicTo(rect.left() + 48, base_y - 18, rect.left() + 78, base_y + 18, rect.left() + 114, base_y)
        painter.drawPath(wave)

        painter.setPen(QColor("#4db7d0"))
        painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Black))
        painter.drawText(QRectF(rect.left() + 14, rect.top() + 16, 94, 18), Qt.AlignLeft | Qt.AlignVCenter, "ARCTIC HUB")
        painter.setPen(QColor("#ff8ebc"))
        painter.setFont(QFont("Microsoft YaHei UI", 12, QFont.Black))
        painter.drawText(QRectF(rect.left() + 14, rect.top() + 42, 98, 26), Qt.AlignLeft | Qt.AlignVCenter, "暖暖陪伴")
        painter.setPen(QColor("#66899b"))
        painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.DemiBold))
        painter.drawText(QRectF(rect.left() + 14, rect.top() + 74, 96, 32), Qt.AlignLeft | Qt.TextWordWrap, "状态、动作、提醒一屏掌握")

        painter.setBrush(QColor(92, 142, 170, 38))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(rect.right() - 92, rect.bottom() - 24, 64, 11))
        if not self._pixmap.isNull():
            bob = sin(self._phase) * 4
            target = QRectF(rect.right() - 100, rect.top() + 25 + bob, 74, 88)
            scaled = self._scaled_bear(target.size().toSize())
            image_rect = QRectF(
                target.center().x() - scaled.width() / 2,
                target.center().y() - scaled.height() / 2,
                scaled.width(),
                scaled.height(),
            )
            painter.drawPixmap(image_rect.toRect(), scaled)

        painter.setPen(QPen(QColor(255, 255, 255, 190), 1.8))
        for x, y, size in ((24, 112, 5), (146, 18, 4), (177, 106, 5)):
            painter.drawLine(QPointF(rect.left() + x - size, rect.top() + y), QPointF(rect.left() + x + size, rect.top() + y))
            painter.drawLine(QPointF(rect.left() + x, rect.top() + y - size), QPointF(rect.left() + x, rect.top() + y + size))


class PremiumMascotStage(QWidget):
    def __init__(self, asset_root):
        super().__init__()
        self.setObjectName("petStage")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._pixmap = _load_first_pixmap(
            (
                asset_root / "role" / "PolarBear" / "action" / "video2252_idle_still_000.png",
                asset_root / "role" / "PolarBear" / "action" / "video2528_idle_seamless_v1_000.png",
                asset_root / "polar-bear-realistic.png",
                asset_root / "polar-bear-premium.png",
            )
        )
        self._scaled_pixmap = QPixmap()
        self._scaled_size = QSize()

    def sizeHint(self):
        return QSize(196, 282)

    def minimumSizeHint(self):
        return QSize(176, 258)

    def _scaled_bear(self, target_size):
        if self._pixmap.isNull() or target_size.isEmpty():
            return QPixmap()
        if self._scaled_pixmap.isNull() or self._scaled_size != target_size:
            self._scaled_pixmap = self._pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._scaled_size = QSize(target_size)
        return self._scaled_pixmap

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg.setColorAt(0.0, QColor("#ffffff"))
        bg.setColorAt(0.58, QColor("#ecfbff"))
        bg.setColorAt(1.0, QColor("#f7f3ff"))
        painter.setBrush(bg)
        painter.setPen(QPen(QColor("#a9e2ef"), 1.4))
        painter.drawRoundedRect(rect, 8, 8)

        glow = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        glow.setColorAt(0.0, QColor(255, 255, 255, 130))
        glow.setColorAt(1.0, QColor(126, 232, 255, 28))
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect.adjusted(8, 8, -8, -8), 8, 8)

        if not self._pixmap.isNull():
            target = QRectF(rect.left() + 22, rect.top() + 22, rect.width() - 44, rect.height() - 64)
            scaled = self._scaled_bear(target.size().toSize())
            image_rect = QRectF(
                rect.center().x() - scaled.width() / 2,
                target.bottom() - scaled.height(),
                scaled.width(),
                scaled.height(),
            )
            painter.setBrush(QColor(54, 92, 118, 34))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(rect.center().x() - 62, rect.bottom() - 42, 124, 18))
            painter.drawPixmap(image_rect.toRect(), scaled)

        pill = QRectF(rect.left() + 26, rect.bottom() - 32, rect.width() - 52, 22)
        painter.setBrush(QColor(255, 255, 255, 190))
        painter.setPen(QPen(QColor("#b9e8f2"), 1))
        painter.drawRoundedRect(pill, 8, 8)
        painter.setBrush(QColor("#74d6e9"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(pill.left() + 10, pill.center().y() - 3, 6, 6))
        painter.setPen(QColor("#52768a"))
        painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.DemiBold))
        painter.drawText(pill.adjusted(20, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, "在线陪伴")


class PremiumSidebarMascotCard(QWidget):
    def __init__(self, asset_root):
        super().__init__()
        self.setObjectName("sidebarMascotCard")
        self._pixmap = _load_first_pixmap(
            (
                asset_root / "role" / "PolarBear" / "action" / "clean_wave_v1_000.png",
                asset_root / "role" / "PolarBear" / "action" / "video2252_idle_still_000.png",
                asset_root / "polar-bear-realistic.png",
            )
        )
        self._scaled_pixmap = QPixmap()
        self._scaled_size = QSize()

    def sizeHint(self):
        return QSize(202, 136)

    def _scaled_bear(self, target_size):
        if self._pixmap.isNull() or target_size.isEmpty():
            return QPixmap()
        if self._scaled_pixmap.isNull() or self._scaled_size != target_size:
            self._scaled_pixmap = self._pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._scaled_size = QSize(target_size)
        return self._scaled_pixmap

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg.setColorAt(0.0, QColor("#ffffff"))
        bg.setColorAt(0.56, QColor("#e9fbff"))
        bg.setColorAt(1.0, QColor("#fff1f7"))
        painter.setBrush(bg)
        painter.setPen(QPen(QColor("#a7def0"), 1.2))
        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(QPen(QColor(100, 201, 232, 90), 3, Qt.SolidLine, Qt.RoundCap))
        wave = QPainterPath()
        base_y = rect.top() + 35
        wave.moveTo(rect.left() + 12, base_y)
        wave.cubicTo(rect.left() + 48, base_y - 18, rect.left() + 78, base_y + 18, rect.left() + 114, base_y)
        painter.drawPath(wave)

        painter.setPen(QColor("#4db7d0"))
        painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Black))
        painter.drawText(QRectF(rect.left() + 14, rect.top() + 16, 94, 18), Qt.AlignLeft | Qt.AlignVCenter, "ARCTIC HUB")
        painter.setPen(QColor("#ff8ebc"))
        painter.setFont(QFont("Microsoft YaHei UI", 12, QFont.Black))
        painter.drawText(QRectF(rect.left() + 14, rect.top() + 42, 98, 26), Qt.AlignLeft | Qt.AlignVCenter, "暖暖陪伴")
        painter.setPen(QColor("#66899b"))
        painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.DemiBold))
        painter.drawText(QRectF(rect.left() + 14, rect.top() + 74, 96, 32), Qt.AlignLeft | Qt.TextWordWrap, "状态、动作、提醒一屏掌握")

        painter.setBrush(QColor(92, 142, 170, 38))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(rect.right() - 92, rect.bottom() - 24, 64, 11))
        if not self._pixmap.isNull():
            target = QRectF(rect.right() - 106, rect.top() + 20, 82, 96)
            scaled = self._scaled_bear(target.size().toSize())
            image_rect = QRectF(
                target.center().x() - scaled.width() / 2,
                target.bottom() - scaled.height(),
                scaled.width(),
                scaled.height(),
            )
            painter.drawPixmap(image_rect.toRect(), scaled)


class CareIndexDial(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("careDial")
        self._target = 0
        self._display = 0.0
        self._caption = ""
        self._note = ""
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.CoarseTimer)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._tick)

    def sizeHint(self):
        return QSize(226, 226)

    def minimumSizeHint(self):
        return QSize(150, 210)

    def set_data(self, value, caption, note):
        self._target = max(0, min(100, int(value)))
        self._caption = caption
        self._note = note
        if abs(self._target - self._display) > 0.15 and not self._timer.isActive():
            self._timer.start()
        self.update()

    def _tick(self):
        if not self.isVisible():
            self._display = float(self._target)
            self._timer.stop()
            return
        diff = self._target - self._display
        if abs(diff) <= 0.15:
            self._display = float(self._target)
            self._timer.stop()
        else:
            self._display += diff * 0.24
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg.setColorAt(0.0, QColor("#ffffff"))
        bg.setColorAt(0.62, QColor("#f1fffb"))
        bg.setColorAt(1.0, QColor("#fff4fa"))
        painter.setBrush(bg)
        painter.setPen(QPen(QColor("#bfe9f1"), 1.3))
        painter.drawRoundedRect(rect, 8, 8)

        ring = QRectF(rect.center().x() - 60, rect.top() + 24, 120, 120)
        painter.setPen(QPen(QColor("#d9edf4"), 12, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(ring, 0, 360 * 16)
        progress_color = QColor("#64c9e8") if self._display < 62 else QColor("#ff9fc3")
        painter.setPen(QPen(progress_color, 12, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(ring, 90 * 16, -int(360 * 16 * self._display / 100))

        painter.setPen(QColor("#284f66"))
        painter.setFont(QFont("Microsoft YaHei UI", 30, QFont.Black))
        painter.drawText(ring, Qt.AlignCenter, str(int(round(self._display))))
        painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.Black))
        painter.setPen(QColor("#62b8d0"))
        painter.drawText(QRectF(rect.left(), rect.top() + 12, rect.width(), 18), Qt.AlignCenter, "CARE INDEX")
        painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        painter.setPen(QColor("#ff8ebc"))
        painter.drawText(QRectF(rect.left() + 14, rect.top() + 151, rect.width() - 28, 24), Qt.AlignCenter, self._caption)
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.setPen(QColor("#5f788a"))
        painter.drawText(QRectF(rect.left() + 15, rect.top() + 174, rect.width() - 30, 42), Qt.AlignTop | Qt.AlignHCenter | Qt.TextWordWrap, self._note)


class PolarBearPetApp(QMainWindow):
    """北极熊桌宠桌面应用主窗口。"""

    def __init__(self):
        super().__init__()
        app = QApplication.instance()
        if app:
            app.setFont(QFont("Microsoft YaHei UI", 10))
        self.setWindowTitle("北极熊桌面宠物系统")
        self.resize(1180, 760)
        self.setMinimumSize(760, 560)
        self.store = PetDataStore()
        self.pet_window = PolarBearPetWindow()
        self.pet_window.setWindowOpacity(float(self.store.settings.get("opacity", 1.0)))
        self.pet_window.set_always_on_top(bool(self.store.settings.get("always_on_top", True)))
        self.pet_window.set_edge_snap(
            bool(self.store.settings.get("edge_snap_enabled", True)),
            int(self.store.settings.get("edge_snap_threshold", 48)),
        )
        self.pet_window.interaction_requested.connect(self._handle_pet_window_interaction)
        self.nav_buttons = []
        self.metric_value_labels = {}
        self.metric_bars = {}
        self.hero_status_label = None
        self.focus_summary_label = None
        self.today_summary_label = None
        self.growth_summary_label = None
        self.care_index_label = None
        self.signal_caption_label = None
        self.economy_summary_label = None
        self.current_action_label = None
        self.today_reminder_label = None
        self.online_status_label = None
        self.pet_toggle_button = None
        self.hero_show_pet_button = None
        self.tray_show_pet_action = None
        self.tray_toggle_pet_action = None
        self.top_time_label = None
        self.clock_label = None
        self.course_title_label = None
        self.course_time_label = None
        self.course_location_label = None
        self.course_message_label = None
        self._sidebar_scroll = None
        self._overview_page = None
        self._right_panel = None
        self._pet_stage = None
        self.recent_log_labels = []
        self.tray_icon = None
        self.care_dial = None
        self._glow_targets = []
        self._panel_animations = []
        self._metric_bar_animations = {}
        self._page_transition = None
        self._page_factories = {}
        self._did_initial_page_show = False
        self._pet_user_hidden = False
        self._pet_topmost_suspended = False
        self._pet_hotkey_text = (
            _normalized_hotkey_text(self.store.settings.get("pet_toggle_hotkey"))
            or DEFAULT_PET_TOGGLE_HOTKEY_TEXT
        )
        self._global_hotkey_registered = False
        self._local_pet_shortcut = None
        self._touch_burst_count = 0
        self._touch_burst_timer = QTimer(self)
        self._touch_burst_timer.setSingleShot(True)
        self._touch_burst_timer.timeout.connect(self._reset_touch_burst)
        self._build_ui()
        self._build_tray()
        self._setup_pet_hotkeys()
        self._life_timer = QTimer(self)
        self._life_timer.setTimerType(Qt.PreciseTimer)
        self._life_timer.timeout.connect(self._tick_pet_life)
        self._life_timer.start(60000)
        self._focus_timer = QTimer(self)
        self._focus_timer.setTimerType(Qt.PreciseTimer)
        self._focus_timer.timeout.connect(self._tick_focus_session)
        self._focus_timer.start(1000)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock_labels)
        self._clock_timer.start(1000)
        self.store.changed.connect(self._refresh_overview)
        self._show_tick_messages(self.store.tick())
        self._refresh_overview()
        self._update_clock_labels()
        QTimer.singleShot(0, self._show_pet_on_startup)

    def _build_ui(self):
        root = AnimatedDashboardRoot()
        root.setObjectName("dashboardRoot")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = self._build_sidebar()
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setObjectName("sidebarScroll")
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sidebar_scroll.setFrameShape(QFrame.NoFrame)
        sidebar_scroll.setWidget(sidebar)
        self._sidebar_scroll = sidebar_scroll
        self.stack = QStackedWidget()
        self.stack.setMinimumSize(0, 0)
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pages = [
            ("宠物状态", self._build_overview_page, True),
            ("成长等级", lambda: self._scroll_module_page(GrowthPage(self.store, self._play_pet_action)), False),
            ("课程提醒", lambda: self._scroll_module_page(NotificationPage(self.store, self.pet_window)), False),
            (
                "动作管理",
                lambda: self._scroll_module_page(
                    InteractionPage(self.pet_window, self.store, self._play_pet_action, self.toggle_pet_window)
                ),
                False,
            ),
            ("聊天互动", lambda: self._scroll_module_page(ChatPage(self.store, self.pet_window, self._play_pet_action)), False),
            ("外观装扮", lambda: BackpackPage(self.store, self._play_pet_action), False),
            (
                "系统设置",
                lambda: self._scroll_module_page(
                    SettingsPage(
                        self.store,
                        self.pet_window,
                        self.current_pet_hotkey,
                        self.set_pet_toggle_hotkey,
                    )
                ),
                False,
            ),
        ]

        for index, (name, factory, eager) in enumerate(pages):
            button = QPushButton(name)
            button.setCursor(Qt.PointingHandCursor)
            button.setProperty("nav", True)
            button.clicked.connect(lambda checked=False, i=index: self._switch_page(i))
            self.nav_buttons.append(button)
            sidebar.layout().addWidget(button)
            if eager:
                page = factory()
            else:
                page = self._lazy_module_placeholder(name)
                self._page_factories[index] = factory
            self.stack.addWidget(page)

        sidebar.layout().addStretch()
        layout.addWidget(sidebar_scroll, 0)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.setStyleSheet(APP_STYLE)
        self._switch_page(0)
        self._start_panel_animations()
        self._sync_responsive_layout()

    def _scroll_module_page(self, page):
        scroll = QScrollArea()
        scroll.setObjectName("modulePageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumSize(0, 0)
        scroll.viewport().setAutoFillBackground(False)
        page.setAutoFillBackground(False)
        page.setProperty("moduleScrollContent", True)
        page.setMinimumHeight(page.minimumSizeHint().height())
        scroll.setWidget(page)
        return scroll

    def _lazy_module_placeholder(self, name):
        placeholder = QFrame()
        placeholder.setObjectName("lazyModulePlaceholder")
        layout = QVBoxLayout(placeholder)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(10)
        title = QLabel(f"{name}正在准备")
        title.setObjectName("pageTitle")
        note = QLabel("第一次打开时会加载对应模块资源，之后切换会直接复用。")
        note.setObjectName("pageDescription")
        note.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addStretch()
        return placeholder

    def _ensure_stack_page(self, index):
        factory = self._page_factories.get(index)
        if not factory:
            return
        old_widget = self.stack.widget(index)
        page = factory()
        self.stack.removeWidget(old_widget)
        old_widget.deleteLater()
        self.stack.insertWidget(index, page)
        self._page_factories[index] = None

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 22, 18, 22)
        sidebar_layout.setSpacing(12)

        title = QLabel("PolarBear")
        title.setObjectName("brandTitle")
        subtitle = QLabel("桌面宠物应用")
        subtitle.setObjectName("brandSubTitle")
        status = QLabel("实时陪伴控制台")
        status.setObjectName("brandStatus")
        sidebar_layout.addWidget(title)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addWidget(status)

        mascot = PremiumSidebarMascotCard(Path(__file__).resolve().parents[1] / "assets" / "polar_bear")
        sidebar_layout.addWidget(mascot)
        self._apply_soft_shadow(mascot, 22, 0, 7, QColor(100, 201, 232, 42))

        pet_button = QPushButton()
        self.pet_toggle_button = pet_button
        pet_button.setCursor(Qt.PointingHandCursor)
        pet_button.setObjectName("petToggleButton")
        pet_button.clicked.connect(self.toggle_pet_window)
        sidebar_layout.addWidget(pet_button)
        return sidebar

    def _build_overview_page(self):
        scroll = QScrollArea()
        scroll.setObjectName("overviewScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumSize(0, 0)

        page = QWidget()
        page.setObjectName("overviewPage")
        self._overview_page = page
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        top_bar = QFrame()
        top_bar.setObjectName("topTitleBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(22, 14, 18, 14)
        top_layout.setSpacing(12)
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title = QLabel("北极熊桌宠控制面板")
        title.setObjectName("mainTitle")
        subtitle = QLabel("Dreamy Arctic Pet Hub · 可爱桌宠管理中心")
        subtitle.setObjectName("mainSubtitle")
        subtitle.setWordWrap(True)
        subtitle.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        self.top_time_label = QLabel()
        self.top_time_label.setObjectName("topTime")
        self.top_time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_layout.addLayout(title_block, 1)
        top_layout.addWidget(self.top_time_label, 0)
        layout.addWidget(top_bar)
        self._apply_soft_shadow(top_bar, 26, 0, 8, QColor(100, 201, 232, 42))

        dashboard = QHBoxLayout()
        dashboard.setSpacing(14)

        main_column = QVBoxLayout()
        main_column.setSpacing(14)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(18)

        hero_text = QVBoxLayout()
        eyebrow = QLabel("POLAR COMPANION CENTER")
        eyebrow.setObjectName("eyebrow")
        hero_title = QLabel("和小熊一起管理今天")
        hero_title.setObjectName("heroTitle")
        hero_title.setWordWrap(True)
        hero_title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        desc = QLabel("明亮通透的冰雪童话控制中心，集中查看状态、课程提醒、动作触发和桌宠日志。")
        desc.setWordWrap(True)
        desc.setObjectName("heroDesc")
        desc.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        hero_text.addWidget(eyebrow)
        hero_text.addWidget(hero_title)
        hero_text.addWidget(desc)
        self.hero_status_label = QLabel()
        self.hero_status_label.setObjectName("heroStatus")
        self.hero_status_label.setWordWrap(True)
        self.hero_status_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        hero_text.addWidget(self.hero_status_label)

        pet_stage = PremiumMascotStage(Path(__file__).resolve().parents[1] / "assets" / "polar_bear")
        self._pet_stage = pet_stage

        actions = QVBoxLayout()
        actions.setSpacing(10)
        show_pet = QPushButton()
        self.hero_show_pet_button = show_pet
        show_pet.clicked.connect(self.show_pet_window)
        show_pet.setObjectName("primaryAction")
        interact = QPushButton("互动反应")
        interact.setObjectName("heroAction")
        interact.clicked.connect(self._trigger_pet_interaction)
        focus = QPushButton("开始专注")
        focus.setObjectName("heroAction")
        focus.clicked.connect(self._start_focus_from_tray)
        actions.addWidget(show_pet)
        actions.addWidget(interact)
        actions.addWidget(focus)
        actions.addStretch()

        self.care_dial = CareIndexDial()

        hero_side = QVBoxLayout()
        hero_side.setSpacing(14)
        hero_side.addWidget(self.care_dial)
        hero_side.addLayout(actions)

        hero_layout.addLayout(hero_text, 1)
        hero_layout.addWidget(pet_stage, 0, Qt.AlignVCenter)
        hero_layout.addLayout(hero_side, 0)
        main_column.addWidget(hero)
        self._apply_soft_shadow(hero, 30, 0, 10, QColor(255, 173, 200, 52))

        metrics = QGridLayout()
        metrics.setSpacing(12)
        metric_data = [
            ("mood", "心情值", "0%", "轻触互动可提升心情", 0),
            ("hunger", "饱食度", "0%", "投喂鱼干和热牛奶恢复", 0),
            ("energy", "活跃度", "0%", "睡觉和短休可恢复", 0),
        ]
        for index, item in enumerate(metric_data):
            metrics.addWidget(self._metric_card(*item), index // 3, index % 3)
        self.current_action_label = QLabel("待机 · 眨眼微动")
        metrics.addWidget(
            self._mini_status_card("当前动作", self.current_action_label, "动作系统待命中", "action"),
            1,
            1,
        )
        self.today_reminder_label = QLabel("今日提醒 · 待检查")
        metrics.addWidget(
            self._mini_status_card("今日提醒", self.today_reminder_label, "课程和通知会同步显示", "reminder"),
            1,
            2,
        )
        self.online_status_label = QLabel("在线 · 运行稳定")
        metrics.addWidget(
            self._mini_status_card("桌宠连接", self.online_status_label, "窗口与控制台已连接", "online"),
            1,
            0,
        )
        main_column.addLayout(metrics)

        action_panel = QFrame()
        action_panel.setObjectName("actionDock")
        action_layout = QVBoxLayout(action_panel)
        action_layout.setContentsMargins(18, 14, 18, 16)
        action_layout.setSpacing(12)
        action_title = QLabel("动作控制")
        action_title.setObjectName("sectionHeading")
        action_grid = QGridLayout()
        action_grid.setSpacing(10)
        action_items = [
            ("挥手", "wave", "挥手动作已触发。", None),
            ("睡觉", "sleep", "准备休息一下。", "rest"),
            ("左走", "walk_left", "向左走一小段。", "walk"),
            ("右走", "walk_right", "向右走一小段。", "walk"),
            ("贴左边", "edge_left", "扒住左侧边缘。", None),
            ("贴右边", "edge_right", "扒住右侧边缘。", None),
            ("跳跃", "jump", "跳跃动作已触发。", "jump"),
            ("互动反应", "touch", "温柔互动，心情提升；好感需要关怀任务慢慢建立。", "touch"),
        ]
        for index, (label, action_name, bubble, update) in enumerate(action_items):
            button = QPushButton(label)
            button.setObjectName("actionPillButton")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, a=action_name, b=bubble, u=update: self._run_dashboard_action(a, b, u))
            action_grid.addWidget(button, index // 3, index % 3)
        action_layout.addWidget(action_title)
        action_layout.addLayout(action_grid)
        main_column.addWidget(action_panel)
        self._apply_soft_shadow(action_panel, 22, 0, 8, QColor(100, 201, 232, 38))

        dashboard.addLayout(main_column, 1)

        right_panel = QFrame()
        right_panel.setObjectName("rightReminderPanel")
        self._right_panel = right_panel
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(12)
        right_title = QLabel("今日提醒")
        right_title.setObjectName("rightPanelTitle")
        right_layout.addWidget(right_title)
        self.course_title_label = QLabel("暂无课程数据 · 可在提醒模块中添加")
        self.course_time_label = QLabel("下一节课时间待同步")
        self.course_location_label = QLabel("地点未设置 · 点击课程提醒维护")
        self.course_message_label = QLabel("桌宠会用气泡提醒重要事项")
        right_layout.addWidget(self._reminder_block("今日课程", self.course_title_label, "课程提醒"))
        right_layout.addWidget(self._reminder_block("上课时间", self.course_time_label, "时间提醒"))
        right_layout.addWidget(self._reminder_block("地点提醒", self.course_location_label, "位置"))
        right_layout.addWidget(self._reminder_block("消息通知", self.course_message_label, "通知"))
        log_title = QLabel("桌宠互动日志")
        log_title.setObjectName("rightPanelTitle")
        right_layout.addWidget(log_title)
        for _ in range(4):
            label = QLabel()
            label.setObjectName("logBubble")
            label.setWordWrap(True)
            self.recent_log_labels.append(label)
            right_layout.addWidget(label)
        right_layout.addStretch()
        dashboard.addWidget(right_panel, 0)
        self._apply_soft_shadow(right_panel, 28, 0, 10, QColor(100, 201, 232, 42))

        layout.addLayout(dashboard, 1)

        footer = QFrame()
        footer.setObjectName("statusFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 16, 8)
        footer_layout.setSpacing(18)
        self.clock_label = QLabel()
        self.clock_label.setObjectName("footerText")
        connection = QLabel("连接状态 · 已连接")
        connection.setObjectName("footerText")
        connection.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        runtime = QLabel("桌宠运行状态 · 正常运行")
        runtime.setObjectName("footerText")
        runtime.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        render = QLabel("动画背景 · 开启")
        render.setObjectName("footerText")
        render.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        footer_layout.addWidget(self.clock_label)
        footer_layout.addStretch()
        footer_layout.addWidget(connection)
        footer_layout.addWidget(runtime)
        footer_layout.addWidget(render)
        layout.addWidget(footer)
        self._apply_soft_shadow(footer, 18, 0, 5, QColor(255, 173, 200, 34))

        self.today_summary_label = QLabel()
        self.today_summary_label.setObjectName("panelText")
        self.today_summary_label.setWordWrap(True)
        self.focus_summary_label = QLabel()
        self.focus_summary_label.setObjectName("panelText")
        self.focus_summary_label.setWordWrap(True)
        self.growth_summary_label = QLabel()
        self.growth_summary_label.setObjectName("panelText")
        self.growth_summary_label.setWordWrap(True)
        scroll.setWidget(page)
        return scroll

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_responsive_layout()

    def _sync_responsive_layout(self):
        if not getattr(self, "_sidebar_scroll", None):
            return
        width = self.width()
        compact = width < 980
        tiny = width < 840

        sidebar_width = 224 if compact else 238
        self._sidebar_scroll.setFixedWidth(sidebar_width)

        if self._right_panel:
            self._right_panel.setVisible(not compact)
        if self._pet_stage:
            self._pet_stage.setVisible(not tiny)
        if self.care_dial:
            self.care_dial.setVisible(width >= 880)
        if self.top_time_label:
            self.top_time_label.setVisible(not tiny)
        if self._overview_page:
            self._overview_page.setMinimumWidth(0 if compact else 860)

    def _apply_soft_shadow(self, widget, blur, offset_x, offset_y, color):
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setOffset(offset_x, offset_y)
        effect.setColor(color)
        widget.setGraphicsEffect(effect)

    def _metric_card(self, key, name, value, note, progress):
        card = QFrame()
        card.setObjectName("metricCard")
        card.setProperty("tone", key)
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        title = QLabel(name)
        title.setObjectName("metricName")
        number = QLabel(value)
        number.setObjectName("metricValue")
        self.metric_value_labels[key] = number
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(progress)
        bar.setTextVisible(False)
        bar.setObjectName("metricBar")
        self.metric_bars[key] = bar
        desc = QLabel(note)
        desc.setObjectName("metricNote")
        desc.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(number)
        layout.addWidget(bar)
        layout.addWidget(desc)
        return card

    def _mini_status_card(self, title, value_label, note, tone):
        card = QFrame()
        card.setObjectName("miniStatusCard")
        card.setProperty("tone", tone)
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("metricName")
        value_label.setObjectName("miniStatusValue")
        value_label.setWordWrap(True)
        desc = QLabel(note)
        desc.setObjectName("metricNote")
        desc.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(value_label)
        layout.addWidget(desc)
        return card

    def _reminder_block(self, title, text, tag):
        block = QFrame()
        block.setObjectName("reminderBlock")
        layout = QVBoxLayout(block)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("reminderTitle")
        tag_label = QLabel(tag)
        tag_label.setObjectName("reminderTag")
        row.addWidget(title_label, 1)
        row.addWidget(tag_label, 0)
        body = text if isinstance(text, QLabel) else QLabel(text)
        body.setObjectName("reminderText")
        body.setWordWrap(True)
        layout.addLayout(row)
        layout.addWidget(body)
        return block

    def _run_dashboard_action(self, action_name, bubble, update=None):
        if update == "walk":
            self.store.walk()
        elif update == "rest":
            self.store.rest()
        elif update == "touch":
            self.store.touch()
            self._register_touch_burst()
        elif update == "jump":
            self.store.adjust_stats({"mood": 4, "energy": -2})
            self.store.add_log("互动", "从控制面板触发跳跃动作。")
        elif action_name == "wave":
            self.store.add_log("互动", "从控制面板触发挥手动作。")
        if self.current_action_label:
            self.current_action_label.setText(f"{bubble.replace('。', '')}")
        self._play_pet_action(action_name, bubble)

    def _update_clock_labels(self):
        now = datetime.now()
        top_text = now.strftime("%m月%d日  %H:%M")
        footer_text = now.strftime("当前时间 · %Y-%m-%d %H:%M:%S")
        if self.top_time_label:
            self.top_time_label.setText(top_text)
        if self.clock_label:
            self.clock_label.setText(footer_text)

    def _start_panel_animations(self):
        self._glow_targets.clear()

    def _animate_progress_value(self, key, bar, value):
        value = max(0, min(100, int(value)))
        if bar.value() == value:
            return
        animation = QPropertyAnimation(bar, b"value", self)
        animation.setStartValue(bar.value())
        animation.setEndValue(value)
        animation.setDuration(520)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start()
        self._metric_bar_animations[key] = animation

    def _info_panel(self, title, rows):
        panel = QFrame()
        panel.setObjectName("infoPanel")
        layout = QVBoxLayout(panel)
        heading = QLabel(title)
        heading.setObjectName("panelTitle")
        layout.addWidget(heading)
        for row in rows:
            if isinstance(row, QLabel):
                layout.addWidget(row)
            else:
                label = QLabel(f"- {row}")
                label.setWordWrap(True)
                label.setObjectName("panelText")
                layout.addWidget(label)
        layout.addStretch()
        return panel

    def _switch_page(self, index):
        self._ensure_stack_page(index)
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        if page and self._did_initial_page_show and not isinstance(page, QScrollArea):
            effect = QGraphicsOpacityEffect(page)
            effect.setOpacity(0.0)
            page.setGraphicsEffect(effect)
            self._page_transition = QPropertyAnimation(effect, b"opacity", self)
            self._page_transition.setStartValue(0.0)
            self._page_transition.setEndValue(1.0)
            self._page_transition.setDuration(220)
            self._page_transition.setEasingCurve(QEasingCurve.OutCubic)
            self._page_transition.start()
        elif page:
            page.setGraphicsEffect(None)
            self._did_initial_page_show = True
        if page and isinstance(page, QScrollArea):
            page.setGraphicsEffect(None)
            self._did_initial_page_show = True
        for i, button in enumerate(self.nav_buttons):
            button.setProperty("active", i == index)
            button.style().unpolish(button)
            button.style().polish(button)

    def _trigger_pet_interaction(self):
        self.store.touch()
        self._register_touch_burst()
        self._play_pet_action("touch", "触发互动，心情提升；普通触摸不再直接增加好感。")

    def _play_pet_action(self, action_name, bubble=None):
        panel_active = self.isVisible() and self.isActiveWindow()
        self.show_pet_window(activate=not panel_active)
        if action_name == "edge_left":
            self.pet_window.stick_to_edge("left")
        elif action_name == "edge_right":
            self.pet_window.stick_to_edge("right")
        else:
            self.pet_window.play_action(action_name)
        if bubble and self.store.settings.get("bubble_on", True):
            self.pet_window.show_bubble(bubble)
        if panel_active:
            self._sync_pet_overlay_for_panel()
        self.pet_window.update()

    def _handle_pet_window_interaction(self, action_name):
        if action_name == "show_panel":
            self._show_console()
            return
        if action_name == "hide_pet":
            self.hide_pet_window()
            return
        if action_name == "quit_app":
            QApplication.instance().quit()
            return
        if action_name == "touch":
            self.store.touch()
            self._register_touch_burst()
            self._show_bubble("心情变好了，好感要靠完整关怀慢慢积累。")
        elif action_name == "wave":
            self.store.add_log("互动", "桌宠挥了挥手。")
            self._show_bubble("我在这里。")
        elif action_name in {"walk_left", "walk_right"}:
            self.store.walk()
            self._show_bubble("散步一小段。")
        elif action_name in {"edge_left", "edge_right"}:
            self.store.add_log("互动", "桌宠贴边吸附，切换到扒墙动作。")
            self._show_bubble("贴边吸附成功。")
        elif action_name == "sleep":
            self.store.rest()
            self._show_bubble("准备休息一下。")
        elif action_name == "jump":
            self.store.adjust_stats({"mood": 4, "energy": -2})
            self.store.add_log("互动", "触发了跳跃动作。")
        elif action_name == "drag":
            self.store.add_log("互动", "开始拖拽桌宠。")
        elif action_name == "drag_end":
            self._save_pet_position()
            self.store.add_log("互动", "拖拽结束，位置已更新。")

    def _register_touch_burst(self):
        self._touch_burst_count += 1
        self._touch_burst_timer.start(2500)
        threshold = int(self.store.settings.get("pat_multi_click_talk_threshold", 6))
        if self._touch_burst_count < threshold:
            return
        self._touch_burst_count = 0
        message = random.choice(
            [
                "我在，我在，别急。",
                "今天的互动量达标了。",
                "再摸就要收极地鱼干了。",
                "收到，陪伴信号很强。",
            ]
        )
        self.store.add_log("互动", "连续点击触发了亲近反馈，但不会直接刷好感。")
        self._show_bubble(message)

    def _reset_touch_burst(self):
        self._touch_burst_count = 0

    def _show_bubble(self, message):
        if message and self.store.settings.get("bubble_on", True):
            self.pet_window.show_bubble(message)

    def _tick_pet_life(self):
        self._show_tick_messages(self.store.tick())

    def _tick_focus_session(self):
        message = self.store.tick_focus()
        if message:
            self._play_pet_action("wave", message)

    def _show_tick_messages(self, messages):
        for message in messages[:1]:
            self._show_bubble(message)

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "polar_bear" / "polar-bear-realistic.png"
        self.tray_icon = QSystemTrayIcon(QIcon(str(icon_path)), self)

        menu = QMenu()
        show_console = QAction("显示控制台", self)
        show_console.triggered.connect(self._show_console)
        show_pet = QAction(self)
        self.tray_show_pet_action = show_pet
        show_pet.triggered.connect(self.show_pet_window)
        toggle_pet = QAction(self)
        self.tray_toggle_pet_action = toggle_pet
        toggle_pet.triggered.connect(self.toggle_pet_window)
        hide_pet = QAction("隐藏桌宠", self)
        hide_pet.triggered.connect(self.hide_pet_window)
        feed = QAction("投喂极地鱼干", self)
        feed.triggered.connect(lambda: self._feed_from_tray("fish"))
        focus = QAction("开始 25 分钟专注", self)
        focus.triggered.connect(self._start_focus_from_tray)
        cancel_focus = QAction("取消专注", self)
        cancel_focus.triggered.connect(self._cancel_focus_from_tray)
        rest = QAction("休息一下", self)
        rest.triggered.connect(self._rest_from_tray)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)

        for action in (show_console, show_pet, toggle_pet, hide_pet, feed, focus, cancel_focus, rest):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._handle_tray_activated)
        self.tray_icon.show()

    def _setup_pet_hotkeys(self):
        self._set_local_pet_shortcut(self._pet_hotkey_text)
        self._register_global_pet_hotkey()
        self._sync_hotkey_labels()

    def _set_local_pet_shortcut(self, hotkey_text):
        if self._local_pet_shortcut is None:
            self._local_pet_shortcut = QShortcut(QKeySequence(hotkey_text), self)
            self._local_pet_shortcut.setContext(Qt.ApplicationShortcut)
            self._local_pet_shortcut.activated.connect(self.toggle_pet_window)
        else:
            self._local_pet_shortcut.setKey(QKeySequence(hotkey_text))

    def _register_global_pet_hotkey(self):
        self._unregister_global_pet_hotkey()
        self._global_hotkey_registered = False
        if not sys.platform.startswith("win"):
            return True
        parts = _windows_hotkey_parts(self._pet_hotkey_text)
        if not parts:
            return False
        modifiers, vk = parts
        try:
            hwnd = wintypes.HWND(int(self.winId()))
            ok = ctypes.windll.user32.RegisterHotKey(hwnd, PET_TOGGLE_HOTKEY_ID, modifiers | MOD_NOREPEAT, vk)
            if not ok:
                ok = ctypes.windll.user32.RegisterHotKey(hwnd, PET_TOGGLE_HOTKEY_ID, modifiers, vk)
        except (AttributeError, OSError, TypeError, ValueError):
            ok = False
        self._global_hotkey_registered = bool(ok)
        return self._global_hotkey_registered

    def _unregister_global_pet_hotkey(self):
        if not self._global_hotkey_registered or not sys.platform.startswith("win"):
            return
        try:
            ctypes.windll.user32.UnregisterHotKey(wintypes.HWND(int(self.winId())), PET_TOGGLE_HOTKEY_ID)
        except (AttributeError, OSError, TypeError, ValueError):
            pass
        self._global_hotkey_registered = False

    def _sync_hotkey_labels(self):
        hotkey = self._pet_hotkey_text
        if self.pet_toggle_button:
            self.pet_toggle_button.setText(f"显示 / 隐藏桌宠  {hotkey}")
        if self.hero_show_pet_button:
            self.hero_show_pet_button.setText(f"唤出桌宠  {hotkey}")
        if self.tray_icon:
            self.tray_icon.setToolTip(f"北极熊桌面宠物\n{hotkey} 显示/隐藏")
        if self.tray_show_pet_action:
            self.tray_show_pet_action.setText(f"唤出桌宠  {hotkey}")
        if self.tray_toggle_pet_action:
            self.tray_toggle_pet_action.setText(f"显示 / 隐藏桌宠  {hotkey}")

    def current_pet_hotkey(self):
        return self._pet_hotkey_text

    def set_pet_toggle_hotkey(self, hotkey_text):
        normalized = _normalized_hotkey_text(hotkey_text)
        if not normalized:
            return False, "快捷键无效：请至少包含 Ctrl / Alt / Shift / Win 中的一个修饰键。"
        if not _windows_hotkey_parts(normalized):
            return False, "快捷键无效：暂不支持这个按键，请换成字母、数字、方向键或 F1-F24。"

        old_hotkey = self._pet_hotkey_text
        self._pet_hotkey_text = normalized
        self._set_local_pet_shortcut(normalized)
        ok = self._register_global_pet_hotkey()
        if sys.platform.startswith("win") and not ok:
            self._pet_hotkey_text = old_hotkey
            self._set_local_pet_shortcut(old_hotkey)
            self._register_global_pet_hotkey()
            self._sync_hotkey_labels()
            return False, f"{normalized} 注册失败，可能已经被其他软件占用。"

        self.store.set_setting("pet_toggle_hotkey", normalized)
        self._sync_hotkey_labels()
        return True, f"快捷键已更新为 {normalized}。"

    def nativeEvent(self, event_type, message):
        if sys.platform.startswith("win"):
            try:
                msg = wintypes.MSG.from_address(int(message))
            except (TypeError, ValueError):
                msg = None
            if msg and msg.message == WM_HOTKEY and int(msg.wParam) == PET_TOGGLE_HOTKEY_ID:
                self.toggle_pet_window()
                return True, 0
        return False, 0

    def _show_console(self):
        self.show()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(0, self._sync_pet_overlay_for_panel)

    def _handle_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.pet_window.isVisible():
                self._show_console()
            else:
                self.show_pet_window()

    def _feed_from_tray(self, item_id):
        ok, message = self.store.feed(item_id)
        self._play_pet_action("touch" if ok else "idle", message)

    def _rest_from_tray(self):
        self.store.rest()
        self._play_pet_action("sleep", "进入休息状态。")

    def _start_focus_from_tray(self):
        self.store.start_focus(25, "托盘专注", "focus")
        self._play_pet_action("idle", "专注计时已经开始。")

    def _cancel_focus_from_tray(self):
        self.store.cancel_focus()
        self._play_pet_action("idle", "专注计时已取消。")

    def _refresh_overview(self):
        stats = self.store.stats
        for key in ("hunger", "mood", "energy", "affection"):
            label = self.metric_value_labels.get(key)
            if label:
                label.setText(f"{stats.get(key, 0)}%")
            bar = self.metric_bars.get(key)
            if bar:
                self._animate_progress_value(key, bar, int(stats.get(key, 0)))
        done = sum(1 for value in self.store.tasks.values() if value)
        total = len(self.store.tasks)
        seconds, goal = self.store.companion_progress()
        focus_done, focus_total, focus_text = self.store.focus_progress()
        exp, required = self.store.level_progress()
        affection = self.store.affection_info()
        level = self.store.level_info()
        care_index = int(
            (
                int(stats.get("hunger", 0))
                + int(stats.get("mood", 0))
                + int(stats.get("energy", 0))
                + int(stats.get("affection", 0))
            )
            / 4
        )
        if self.hero_status_label:
            self.hero_status_label.setText(
                f"Lv.{level['level']}「{level['title']}」 {exp}/{required} EXP / 好感上限 {level['affection_ceiling']}% / 金币 {stats.get('coins', 0)} / 任务 {done}/{total}"
            )
        if care_index >= 85:
            dial_caption = "状态很好"
        elif care_index >= 60:
            dial_caption = "稳定养成中"
        else:
            dial_caption = "需要照顾"
        dial_note = f"金币 {stats.get('coins', 0)} / 好感 {affection['value']}% / 任务 {done}/{total}"
        if self.care_dial:
            self.care_dial.set_data(care_index, dial_caption, dial_note)
        course_title, course_time, course_location = self.store.course_summary()
        if self.today_reminder_label:
            self.today_reminder_label.setText(f"{course_time} · {course_title}")
        if self.course_title_label:
            self.course_title_label.setText(course_title)
        if self.course_time_label:
            self.course_time_label.setText(course_time)
        if self.course_location_label:
            self.course_location_label.setText(course_location)
        if self.course_message_label:
            self.course_message_label.setText(f"今日任务 {done}/{total} · 课程提醒会同步到桌宠气泡")
        if self.online_status_label:
            self.online_status_label.setText("在线 · 运行稳定")
        if self.care_index_label:
            self.care_index_label.setText(str(care_index))
        if self.signal_caption_label:
            if care_index >= 85:
                caption = "状态优秀，可通过完整关怀推进好感"
            elif care_index >= 60:
                caption = "状态稳定，注意资源规划"
            else:
                caption = "状态偏低，优先投喂或休息"
            self.signal_caption_label.setText(caption)
        if self.economy_summary_label:
            self.economy_summary_label.setText(
                f"困难经济：金币 {stats.get('coins', 0)}，好感 {affection['value']}%/{level['affection_ceiling']}%，今日任务 {done}/{total}。"
            )
        if self.today_summary_label:
            self.today_summary_label.setText(
                f"陪伴 {seconds // 60}/{max(1, goal // 60)} 分钟，今日任务完成 {done}/{total}。"
            )
        if self.growth_summary_label:
            if affection["to_next"]:
                affection_text = f"距离「{affection['next_title']}」还差 {affection['to_next']} 点好感。"
            else:
                affection_text = "好感已达最高阶段。"
            self.growth_summary_label.setText(f"成长：{self.store.growth_summary()} {affection_text}")
        if self.focus_summary_label:
            if focus_total:
                percent = min(100, int(focus_done / focus_total * 100))
                self.focus_summary_label.setText(f"专注：{focus_text}，进度 {percent}%。")
            else:
                self.focus_summary_label.setText("专注：暂无计时，可从首页、通知页或托盘开始。")
        for index, label in enumerate(self.recent_log_labels):
            text = self.store.logs[index] if index < len(self.store.logs) else "暂无更多日志"
            label.setText(f"- {text}")

    def _screen_area_for_pet(self):
        screen = QApplication.screenAt(self.pet_window.frameGeometry().center()) or QApplication.primaryScreen()
        return screen.availableGeometry() if screen else None

    def _clamped_pet_position(self, x, y):
        if hasattr(self.pet_window, "fit_position_to_visible_screen"):
            return self.pet_window.fit_position_to_visible_screen(x, y)
        area = self._screen_area_for_pet()
        if not area:
            return int(x), int(y)
        x = max(area.left(), min(int(x), area.right() - self.pet_window.width()))
        y = max(area.top(), min(int(y), area.bottom() - self.pet_window.height()))
        return x, y

    def _default_pet_position(self):
        area = QApplication.primaryScreen().availableGeometry() if QApplication.primaryScreen() else None
        if not area:
            return 80, 80
        x = area.right() - self.pet_window.width() - 72
        y = area.bottom() - self.pet_window.height() - 96
        return self._clamped_pet_position(x, y)

    def _restore_pet_position(self):
        settings = self.store.settings
        try:
            x = int(settings.get("pet_window_x"))
            y = int(settings.get("pet_window_y"))
        except (TypeError, ValueError):
            x, y = self._default_pet_position()
        else:
            x, y = self._clamped_pet_position(x, y)
        self.pet_window.move(x, y)

    def _save_pet_position(self):
        self.store.settings["pet_window_x"] = int(self.pet_window.x())
        self.store.settings["pet_window_y"] = int(self.pet_window.y())

    def _show_pet_on_startup(self):
        self.show_pet_window(restore=True)

    def _pet_overlaps_panel(self):
        if not self.isVisible() or not self.pet_window.isVisible():
            return False
        panel_rect = self.frameGeometry().adjusted(-8, -8, 8, 8)
        pet_rect = self.pet_window.frameGeometry()
        return panel_rect.intersects(pet_rect)

    def _suspend_pet_overlay_for_panel(self):
        if not bool(self.store.settings.get("always_on_top", True)):
            return
        if not self.pet_window.isVisible():
            return
        self._pet_topmost_suspended = True
        self.pet_window.set_always_on_top(False)
        self.pet_window.lower()
        self.raise_()

    def _restore_pet_overlay_after_panel(self):
        if not self._pet_topmost_suspended:
            return
        self._pet_topmost_suspended = False
        if bool(self.store.settings.get("always_on_top", True)):
            self.pet_window.set_always_on_top(True)

    def _sync_pet_overlay_for_panel(self):
        if self.isVisible() and self.isActiveWindow() and self._pet_overlaps_panel():
            self._suspend_pet_overlay_for_panel()
        elif self.isVisible() and self.isActiveWindow() and self._pet_topmost_suspended:
            self._restore_pet_overlay_after_panel()
        elif not self.isActiveWindow():
            self._restore_pet_overlay_after_panel()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                QTimer.singleShot(0, self._sync_pet_overlay_for_panel)
            else:
                QTimer.singleShot(160, self._sync_pet_overlay_for_panel)

    def show_pet_window(self, checked=False, restore=True, activate=True):
        was_visible = self.pet_window.isVisible()
        if restore and not was_visible:
            self._restore_pet_position()
        if self.pet_window.isMinimized():
            self.pet_window.showNormal()
        self.pet_window.show()
        if activate:
            self._restore_pet_overlay_after_panel()
            self.pet_window.raise_()
            self.pet_window.activateWindow()
        else:
            self._sync_pet_overlay_for_panel()
        self.pet_window.update()
        self._pet_user_hidden = False

    def hide_pet_window(self, checked=False):
        if self.pet_window.isVisible():
            self._save_pet_position()
        self.pet_window.hide()
        self._pet_user_hidden = True

    def closeEvent(self, event):
        self._unregister_global_pet_hotkey()
        self._save_pet_position()
        self.store.save()
        self.pet_window.close()
        super().closeEvent(event)

    def toggle_pet_window(self):
        if self.pet_window.isVisible() and not self._pet_user_hidden:
            self.hide_pet_window()
        else:
            self.show_pet_window()


APP_STYLE = """
* {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", Arial;
}
QMainWindow {
    background: #f5fbff;
}
QScrollArea#overviewScroll {
    background: transparent;
    border: 0;
}
QScrollArea#overviewScroll > QWidget {
    background: transparent;
}
QScrollArea#modulePageScroll {
    background: transparent;
    border: 0;
}
QScrollArea#modulePageScroll > QWidget {
    background: transparent;
}
QWidget[moduleScrollContent="true"] {
    background: transparent;
}
QScrollArea#sidebarScroll {
    min-width: 220px;
    max-width: 238px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 226), stop:0.58 rgba(239, 249, 255, 218), stop:1 rgba(255, 246, 250, 218));
    border: 0;
    border-right: 1px solid rgba(120, 190, 214, 150);
}
QScrollArea#sidebarScroll > QWidget {
    background: transparent;
}
#overviewPage {
    background: transparent;
}
#lazyModulePlaceholder {
    background: transparent;
}
#lazyModulePlaceholder #pageTitle {
    color: #23506a;
    font-size: 28px;
    font-weight: 900;
}
#lazyModulePlaceholder #pageDescription {
    color: #668497;
    font-size: 14px;
}
#topTitleBar, #actionDock, #rightReminderPanel, #statusFooter {
    background: rgba(255, 255, 255, 210);
    border: 1px solid rgba(160, 220, 238, 180);
    border-radius: 8px;
}
#mainTitle {
    color: #244f66;
    font-size: 26px;
    font-weight: 900;
}
#mainSubtitle {
    color: #6a8da0;
    font-size: 13px;
    font-weight: 800;
}
#topTime {
    min-width: 126px;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #64c9e8, stop:1 #ffadc8);
    border: 1px solid rgba(255, 255, 255, 210);
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 900;
}
#sidebar {
    min-width: 198px;
    max-width: 238px;
    background: transparent;
}
#brandTitle {
    color: #25546b;
    font-size: 30px;
    font-weight: 900;
    margin-bottom: 2px;
}
#brandSubTitle {
    color: #668497;
    font-size: 14px;
    font-weight: 700;
}
#brandStatus {
    color: #2c5263;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffffff, stop:0.55 #e9fbff, stop:1 #fff1f7);
    border: 1px solid #9bdced;
    border-radius: 8px;
    padding: 8px 10px;
    margin-top: 8px;
    margin-bottom: 12px;
    font-weight: 800;
}
#sidebarMascotCard {
    min-height: 136px;
    max-height: 136px;
}
QPushButton {
    min-height: 40px;
    color: #416074;
    background: rgba(255, 255, 255, 210);
    border: 1px solid #c5e3ee;
    border-radius: 8px;
    text-align: left;
    padding-left: 13px;
    padding-right: 13px;
    font-weight: 800;
}
QPushButton:hover {
    color: #263f55;
    background: #ffffff;
    border-color: #80cfe6;
}
QPushButton[nav="true"] {
    min-height: 42px;
    color: #426277;
    background: rgba(255, 255, 255, 185);
    border: 1px solid rgba(172, 222, 238, 205);
    border-left: 4px solid rgba(100, 201, 232, 140);
    border-radius: 8px;
    text-align: left;
    padding-left: 16px;
    font-weight: 900;
}
QPushButton[nav="true"]:hover {
    color: #244f66;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffffff, stop:0.58 #eaffff, stop:1 #fff2f8);
    border-color: #8bd8eb;
    border-left-color: #ff9fc3;
}
QPushButton[active="true"] {
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #64c9e8, stop:0.55 #85decf, stop:1 #ffb8d1);
    border-color: #ffffff;
    font-weight: 900;
}
QPushButton[nav="true"][active="true"] {
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #64c9e8, stop:0.5 #85decf, stop:1 #ffadc8);
    border-color: rgba(255, 255, 255, 220);
    border-left: 4px solid #ffd374;
    text-align: left;
    padding-left: 16px;
}
#petToggleButton {
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #55bddf, stop:1 #ffadc8);
    border-color: rgba(255, 255, 255, 210);
    font-weight: 900;
    text-align: center;
}
#primaryAction {
    min-width: 108px;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff9fc3, stop:1 #ffc46b);
    border-color: #ffffff;
    border-radius: 8px;
    font-weight: 900;
    text-align: center;
}
#heroAction {
    min-width: 108px;
    color: #31526a;
    background: rgba(255, 255, 255, 210);
    border-color: #bde9f2;
    border-radius: 8px;
    font-weight: 800;
    text-align: center;
}
#heroPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255, 255, 255, 232), stop:0.5 rgba(238, 251, 255, 222), stop:1 rgba(255, 242, 248, 225));
    border: 1px solid rgba(145, 216, 236, 180);
    border-radius: 8px;
}
#petStage {
    min-width: 176px;
    max-width: 196px;
    min-height: 258px;
    max-height: 282px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:0.56 #eaf9ff, stop:1 #fff4fa);
    border: 1px solid #c7eaf3;
    border-radius: 8px;
}
#sparkleText {
    color: #ff8dbc;
    font-size: 12px;
    font-weight: 900;
}
#petPreviewImage {
    min-height: 178px;
}
#petStageNote {
    color: #5f8295;
    font-size: 12px;
    font-weight: 800;
}
#signalPanel {
    min-width: 210px;
    max-width: 230px;
    background: rgba(255, 255, 255, 205);
    border: 1px solid #bbe8f0;
    border-radius: 8px;
}
#signalHeading {
    color: #6c8fa1;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 0px;
}
#signalValue {
    color: #25546b;
    font-size: 56px;
    font-weight: 900;
}
#signalCaption {
    color: #ff8ebc;
    font-size: 13px;
    font-weight: 800;
}
#signalNote {
    color: #658092;
    font-size: 13px;
}
#metricCard, #miniStatusCard, #infoPanel {
    background: rgba(255, 255, 255, 215);
    border: 1px solid #c4e5ef;
    border-radius: 8px;
}
#metricCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #edfaff);
}
#metricCard[tone="mood"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fff8fc, stop:1 #ffeaf3);
}
#metricCard[tone="energy"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fffdf4, stop:1 #fff0c9);
}
#metricCard[tone="affection"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f4fff9, stop:1 #dff7ee);
}
#miniStatusCard[tone="action"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #f3edff);
}
#miniStatusCard[tone="reminder"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fffdf4, stop:1 #fff0c9);
}
#miniStatusCard[tone="online"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f4fff9, stop:1 #dff7ee);
}
#miniStatusValue {
    color: #294f66;
    font-size: 20px;
    font-weight: 900;
}
#sectionHeading, #rightPanelTitle {
    color: #284f66;
    font-size: 18px;
    font-weight: 900;
}
#actionPillButton {
    min-width: 76px;
    min-height: 48px;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #64c9e8, stop:0.55 #85decf, stop:1 #ffadc8);
    border: 1px solid rgba(255, 255, 255, 220);
    border-radius: 8px;
    text-align: center;
    font-size: 15px;
    font-weight: 900;
}
#actionPillButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffadc8, stop:1 #ffd374);
}
#rightReminderPanel {
    min-width: 210px;
    max-width: 300px;
}
#reminderBlock {
    background: rgba(255, 255, 255, 205);
    border: 1px solid rgba(198, 232, 243, 210);
    border-radius: 8px;
}
#reminderTitle {
    color: #284f66;
    font-size: 14px;
    font-weight: 900;
}
#reminderTag {
    color: #ffffff;
    background: #ffadc8;
    border-radius: 7px;
    padding: 3px 7px;
    font-size: 11px;
    font-weight: 900;
}
#reminderText, #footerText {
    color: #5f7c8d;
    font-size: 13px;
    font-weight: 700;
}
#logBubble {
    color: #45687b;
    background: rgba(255, 255, 255, 190);
    border: 1px solid rgba(194, 229, 239, 180);
    border-radius: 8px;
    padding: 7px 9px;
    font-size: 12px;
}
#eyebrow {
    color: #50b9d2;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0px;
}
#heroTitle {
    color: #244f66;
    font-size: 32px;
    font-weight: 900;
}
#heroDesc {
    color: #5f7c8c;
    font-size: 14px;
}
#heroStatus {
    color: #3d6276;
    background: #ffffff;
    border: 1px solid #ffd1df;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 13px;
    font-weight: 800;
}
#panelText, #metricNote {
    color: #5e7887;
    font-size: 14px;
}
#metricName {
    color: #668da1;
    font-size: 13px;
    font-weight: 800;
}
#metricValue {
    color: #294f66;
    font-size: 27px;
    font-weight: 900;
}
#metricBar {
    min-height: 8px;
    max-height: 8px;
    background: #dceff5;
    border: 1px solid #c7e4ef;
    border-radius: 4px;
}
#metricBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffabc8, stop:0.45 #ffd374, stop:0.72 #8de1d0, stop:1 #63c7e7);
    border-radius: 3px;
}
#panelTitle {
    color: #2c5369;
    font-size: 18px;
    font-weight: 800;
}
QStackedWidget {
    background: transparent;
}
QLabel {
    color: #31556b;
}
"""
