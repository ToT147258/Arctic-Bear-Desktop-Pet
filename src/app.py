import random
from math import cos, pi, sin
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QPropertyAnimation, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
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
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.modules.backpack import BackpackPage
from src.modules.interaction import InteractionPage
from src.modules.notification import NotificationPage
from src.modules.settings import SettingsPage
from src.modules.status import StatusPage
from src.pet_data import PetDataStore
from src.pet_window import PolarBearPetWindow


class AnimatedDashboardRoot(QWidget):
    def __init__(self):
        super().__init__()
        rng = random.Random(18)
        self._phase = 0.0
        self._flakes = [
            (rng.random(), rng.random(), rng.uniform(0.5, 1.7), rng.uniform(0.18, 0.7))
            for _ in range(58)
        ]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _tick(self):
        self._phase = (self._phase + 0.012) % (pi * 2)
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
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def sizeHint(self):
        return QSize(232, 268)

    def _tick(self):
        self._phase = (self._phase + 0.035) % (pi * 2)
        self.update()

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
            bob = sin(self._phase) * 8
            target = QRectF(rect.center().x() - 82, rect.top() + 54 + bob, 164, 176)
            scaled = self._pixmap.scaled(
                target.size().toSize(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
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
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def sizeHint(self):
        return QSize(226, 226)

    def set_data(self, value, caption, note):
        self._target = max(0, min(100, int(value)))
        self._caption = caption
        self._note = note
        self.update()

    def _tick(self):
        self._phase = (self._phase + 0.035) % (pi * 2)
        self._display += (self._target - self._display) * 0.12
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
        self.recent_log_labels = []
        self.tray_icon = None
        self.care_dial = None
        self._glow_targets = []
        self._panel_animations = []
        self._metric_bar_animations = {}
        self._page_transition = None
        self._did_initial_page_show = False
        self._touch_burst_count = 0
        self._touch_burst_timer = QTimer(self)
        self._touch_burst_timer.setSingleShot(True)
        self._touch_burst_timer.timeout.connect(self._reset_touch_burst)
        self._build_ui()
        self._build_tray()
        self._life_timer = QTimer(self)
        self._life_timer.setTimerType(Qt.PreciseTimer)
        self._life_timer.timeout.connect(self._tick_pet_life)
        self._life_timer.start(60000)
        self._focus_timer = QTimer(self)
        self._focus_timer.setTimerType(Qt.PreciseTimer)
        self._focus_timer.timeout.connect(self._tick_focus_session)
        self._focus_timer.start(1000)
        self.store.changed.connect(self._refresh_overview)
        self._show_tick_messages(self.store.tick())
        self._refresh_overview()

    def _build_ui(self):
        root = AnimatedDashboardRoot()
        root.setObjectName("dashboardRoot")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = self._build_sidebar()
        self.stack = QStackedWidget()
        pages = [
            ("总览工作台", self._build_overview_page()),
            ("桌宠交互", InteractionPage(self.pet_window, self.store, self._play_pet_action, self.toggle_pet_window)),
            ("状态成长", StatusPage(self.store, self._play_pet_action)),
            ("背包喂养", BackpackPage(self.store, self._play_pet_action)),
            ("系统设置", SettingsPage(self.store, self.pet_window)),
            ("通知日志", NotificationPage(self.store, self.pet_window)),
        ]

        for index, (name, page) in enumerate(pages):
            button = QPushButton(name)
            button.setCursor(Qt.PointingHandCursor)
            button.setProperty("nav", True)
            button.clicked.connect(lambda checked=False, i=index: self._switch_page(i))
            self.nav_buttons.append(button)
            sidebar.layout().addWidget(button)
            self.stack.addWidget(page)

        sidebar.layout().addStretch()
        layout.addWidget(sidebar, 0)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.setStyleSheet(APP_STYLE)
        self._switch_page(0)
        self._start_panel_animations()

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

        pet_button = QPushButton("显示 / 隐藏桌宠")
        pet_button.setCursor(Qt.PointingHandCursor)
        pet_button.setObjectName("petToggleButton")
        pet_button.clicked.connect(self.toggle_pet_window)
        sidebar_layout.addWidget(pet_button)
        return sidebar

    def _build_overview_page(self):
        page = QWidget()
        page.setObjectName("overviewPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28, 24, 28, 24)
        hero_layout.setSpacing(20)

        hero_text = QVBoxLayout()
        eyebrow = QLabel("POLAR COMPANION")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("北极熊桌宠控制台")
        title.setObjectName("heroTitle")
        desc = QLabel("困难养成曲线已开启：金币更稀缺，好感需要稳定陪伴推进。这里会实时监测桌宠状态、资源压力和今日任务。")
        desc.setWordWrap(True)
        desc.setObjectName("heroDesc")
        hero_text.addWidget(eyebrow)
        hero_text.addWidget(title)
        hero_text.addWidget(desc)
        self.hero_status_label = QLabel()
        self.hero_status_label.setObjectName("heroStatus")
        hero_text.addWidget(self.hero_status_label)

        pet_stage = MascotStage(Path(__file__).resolve().parents[1] / "assets" / "polar_bear")

        actions = QVBoxLayout()
        actions.setSpacing(10)
        show_pet = QPushButton("唤出桌宠")
        show_pet.clicked.connect(self.toggle_pet_window)
        show_pet.setObjectName("primaryAction")
        interact = QPushButton("触发互动")
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
        hero_layout.addWidget(pet_stage, 0)
        hero_layout.addLayout(hero_side, 0)
        layout.addWidget(hero)

        metrics = QGridLayout()
        metrics.setSpacing(14)
        metric_data = [
            ("hunger", "饱食度", "0%", "投喂食物可恢复", 0),
            ("mood", "心情值", "0%", "互动收益已按次数递减", 0),
            ("energy", "体力值", "0%", "睡觉和短休可恢复", 0),
            ("affection", "好感度", "0%", "稀缺成长，阶段突破奖励更少", 0),
        ]
        for index, item in enumerate(metric_data):
            metrics.addWidget(self._metric_card(*item), index // 4, index % 4)
        layout.addLayout(metrics)

        content = QHBoxLayout()
        content.setSpacing(16)
        self.today_summary_label = QLabel()
        self.today_summary_label.setObjectName("panelText")
        self.today_summary_label.setWordWrap(True)
        self.focus_summary_label = QLabel()
        self.focus_summary_label.setObjectName("panelText")
        self.focus_summary_label.setWordWrap(True)
        self.growth_summary_label = QLabel()
        self.growth_summary_label.setObjectName("panelText")
        self.growth_summary_label.setWordWrap(True)
        content.addWidget(self._info_panel("今日概况", [
            self.today_summary_label,
            self.growth_summary_label,
            self.focus_summary_label,
            "状态、任务、背包和专注记录会自动保存",
        ]), 1)
        content.addWidget(self._info_panel("困难养成策略", [
            "每日任务金币下调，商店价格上调",
            "连续摸摸只保留少量早期好感收益",
            "好感突破和升级奖励改为长期目标",
        ]), 1)
        recent_panel = QFrame()
        recent_panel.setObjectName("infoPanel")
        recent_layout = QVBoxLayout(recent_panel)
        recent_heading = QLabel("最近日志")
        recent_heading.setObjectName("panelTitle")
        recent_layout.addWidget(recent_heading)
        for _ in range(4):
            label = QLabel()
            label.setObjectName("panelText")
            label.setWordWrap(True)
            self.recent_log_labels.append(label)
            recent_layout.addWidget(label)
        recent_layout.addStretch()
        content.addWidget(recent_panel, 1)
        layout.addLayout(content)
        layout.addStretch()
        return page

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
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        if page and self._did_initial_page_show:
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
        for i, button in enumerate(self.nav_buttons):
            button.setProperty("active", i == index)
            button.style().unpolish(button)
            button.style().polish(button)

    def _trigger_pet_interaction(self):
        self.store.touch()
        self._register_touch_burst()
        self._play_pet_action("touch", "触发互动，心情提升；好感收益按今日次数递减。")

    def _play_pet_action(self, action_name, bubble=None):
        if not self.pet_window.isVisible():
            self.pet_window.show()
        self.pet_window.raise_()
        self.pet_window.play_action(action_name)
        if bubble and self.store.settings.get("bubble_on", True):
            self.pet_window.show_bubble(bubble)
        self.pet_window.update()

    def _handle_pet_window_interaction(self, action_name):
        if action_name == "touch":
            self.store.touch()
            self._register_touch_burst()
            self._show_bubble("摸摸头，心情变好了。")
        elif action_name == "wave":
            self.store.add_log("互动", "桌宠挥了挥手。")
            self._show_bubble("我在这里。")
        elif action_name in {"walk_left", "walk_right"}:
            self.store.walk()
            self._show_bubble("散步一小段。")
        elif action_name == "sleep":
            self.store.rest()
            self._show_bubble("准备休息一下。")
        elif action_name == "jump":
            self.store.adjust_stats({"mood": 4, "energy": -2})
            self.store.add_log("互动", "触发了跳跃动作。")
        elif action_name == "drag":
            self.store.add_log("互动", "开始拖拽桌宠。")
        elif action_name == "drag_end":
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
                "再摸就要收小鱼了。",
                "收到，陪伴信号很强。",
            ]
        )
        self.store.add_log("互动", "连续点击触发了亲近反馈。")
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
        self.tray_icon.setToolTip("北极熊桌面宠物")

        menu = QMenu()
        show_console = QAction("显示控制台", self)
        show_console.triggered.connect(self._show_console)
        toggle_pet = QAction("显示 / 隐藏桌宠", self)
        toggle_pet.triggered.connect(self.toggle_pet_window)
        feed = QAction("投喂小鱼", self)
        feed.triggered.connect(lambda: self._feed_from_tray("fish"))
        focus = QAction("开始 25 分钟专注", self)
        focus.triggered.connect(self._start_focus_from_tray)
        cancel_focus = QAction("取消专注", self)
        cancel_focus.triggered.connect(self._cancel_focus_from_tray)
        rest = QAction("休息一下", self)
        rest.triggered.connect(self._rest_from_tray)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)

        for action in (show_console, toggle_pet, feed, focus, cancel_focus, rest):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._handle_tray_activated)
        self.tray_icon.show()

    def _show_console(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _handle_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._show_console()

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
                f"Lv.{stats.get('level', 1)} {exp}/{required} EXP / 好感 {affection['title']} / 金币 {stats.get('coins', 0)} / 任务 {done}/{total}"
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
        if self.care_index_label:
            self.care_index_label.setText(str(care_index))
        if self.signal_caption_label:
            if care_index >= 85:
                caption = "状态优秀，适合推进好感阶段"
            elif care_index >= 60:
                caption = "状态稳定，注意资源规划"
            else:
                caption = "状态偏低，优先投喂或休息"
            self.signal_caption_label.setText(caption)
        if self.economy_summary_label:
            self.economy_summary_label.setText(
                f"困难经济：金币 {stats.get('coins', 0)}，好感 {affection['value']}%，今日任务 {done}/{total}。"
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

    def showEvent(self, event):
        super().showEvent(event)
        if not self.pet_window.isVisible():
            self.pet_window.move(self.x() + self.width() - self.pet_window.width() - 24, self.y() + 100)
            self.pet_window.show()

    def closeEvent(self, event):
        self.store.save()
        self.pet_window.close()
        super().closeEvent(event)

    def toggle_pet_window(self):
        if self.pet_window.isVisible():
            self.pet_window.hide()
        else:
            self.pet_window.show()
            self.pet_window.raise_()


APP_STYLE = """
* {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", Arial;
}
QMainWindow {
    background: #f5fbff;
}
#overviewPage {
    background: transparent;
}
#sidebar {
    min-width: 238px;
    max-width: 238px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 226), stop:0.58 rgba(239, 249, 255, 218), stop:1 rgba(255, 246, 250, 218));
    border-right: 1px solid rgba(120, 190, 214, 150);
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
QPushButton[active="true"] {
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #64c9e8, stop:0.55 #85decf, stop:1 #ffb8d1);
    border-color: #ffffff;
    font-weight: 900;
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
    min-width: 156px;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff9fc3, stop:1 #ffc46b);
    border-color: #ffffff;
    border-radius: 8px;
    font-weight: 900;
    text-align: center;
}
#heroAction {
    min-width: 156px;
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
    min-width: 210px;
    max-width: 210px;
    min-height: 246px;
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
#metricCard, #infoPanel {
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
