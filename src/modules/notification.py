from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QListWidget, QProgressBar, QPushButton, QVBoxLayout, QWidget


class NotificationPage(QWidget):
    def __init__(self, store, pet_window):
        super().__init__()
        self.store = store
        self.pet_window = pet_window
        self.log_list = None
        self.focus_label = None
        self.focus_bar = None
        self.pause_button = None
        self._build_ui()
        self.store.changed.connect(self.refresh)
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(16)

        title = QLabel("通知日志与应用展示模块")
        title.setObjectName("pageTitle")
        desc = QLabel("这里汇总桌宠互动、投喂、任务、设置变化，也可以在桌宠附近显示短气泡提示。")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(desc)

        action_grid = QGridLayout()
        action_grid.setSpacing(10)
        for index, (label, callback) in enumerate(
            [
                ("显示气泡", self._show_bubble),
                ("写入测试日志", self._write_log),
                ("清空日志", self.store.clear_logs),
                ("打开项目文档", self._open_docs),
            ]
        ):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("moduleAction")
            button.clicked.connect(callback)
            action_grid.addWidget(button, 0, index)
        layout.addLayout(action_grid)

        focus_card = QFrame()
        focus_card.setObjectName("moduleCard")
        focus_layout = QVBoxLayout(focus_card)
        focus_heading = QLabel("专注 / 番茄钟")
        focus_heading.setObjectName("cardTitle")
        self.focus_label = QLabel()
        self.focus_label.setObjectName("pageDescription")
        self.focus_bar = QProgressBar()
        self.focus_bar.setRange(0, 100)
        self.focus_bar.setTextVisible(True)
        self.focus_bar.setObjectName("focusBar")
        focus_actions = QGridLayout()
        focus_actions.setSpacing(10)
        for index, (label, callback) in enumerate(
            [
                ("开始专注 25 分钟", lambda: self._start_focus(25, "专注时间", "focus")),
                ("开始短休 5 分钟", lambda: self._start_focus(5, "短休息", "break")),
                ("暂停 / 继续", self._toggle_focus_pause),
                ("取消计时", self.store.cancel_focus),
            ]
        ):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("moduleAction")
            button.clicked.connect(callback)
            if label == "暂停 / 继续":
                self.pause_button = button
            focus_actions.addWidget(button, 0, index)
        focus_layout.addWidget(focus_heading)
        focus_layout.addWidget(self.focus_label)
        focus_layout.addWidget(self.focus_bar)
        focus_layout.addLayout(focus_actions)
        layout.addWidget(focus_card)

        log_card = QFrame()
        log_card.setObjectName("moduleCard")
        log_layout = QVBoxLayout(log_card)
        heading = QLabel("最近日志")
        heading.setObjectName("cardTitle")
        self.log_list = QListWidget()
        self.log_list.setObjectName("logList")
        log_layout.addWidget(heading)
        log_layout.addWidget(self.log_list)
        layout.addWidget(log_card)
        layout.addStretch()
        self.setStyleSheet(PAGE_STYLE)

    def refresh(self):
        self.log_list.clear()
        for entry in self.store.logs[:30]:
            self.log_list.addItem(entry)
        done, total, text = self.store.focus_progress()
        if total:
            percent = min(100, int(done / total * 100))
            self.focus_bar.setValue(percent)
            self.focus_bar.setFormat(f"{percent}%")
        else:
            self.focus_bar.setValue(0)
            self.focus_bar.setFormat("0%")
        self.focus_label.setText(text)
        session = self.store.focus_session
        self.pause_button.setText("继续计时" if session.get("paused") else "暂停计时")

    def _show_bubble(self):
        message = "今天也照顾得很好。"
        if self.store.settings.get("bubble_on", True):
            self.pet_window.show_bubble(message)
        self.store.add_log("通知", "显示了一条桌宠气泡提示。")

    def _write_log(self):
        self.store.add_log("调试", "手动写入了一条测试日志。")

    def _start_focus(self, minutes, title, mode):
        self.store.start_focus(minutes, title, mode)
        if self.store.settings.get("bubble_on", True):
            self.pet_window.show_bubble(f"{title}开始了。")

    def _toggle_focus_pause(self):
        if not self.store.focus_session.get("active"):
            self.store.start_focus(25, "专注时间", "focus")
            return
        if self.store.focus_session.get("paused"):
            self.store.resume_focus()
        else:
            self.store.pause_focus()

    def _open_docs(self):
        docs_path = Path(__file__).resolve().parents[2] / "docs" / "项目主题及创意.md"
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(docs_path)))
        self.store.add_log("文档", "打开了项目主题及创意文档。")


PAGE_STYLE = """
#pageTitle {
    color: #ffffff;
    font-size: 30px;
    font-weight: 800;
}
#pageDescription {
    color: #b8cbda;
    font-size: 14px;
}
#moduleCard {
    background: #122237;
    border: 1px solid #2a4c68;
    border-radius: 10px;
    padding: 12px;
}
#cardTitle {
    color: #7ee8ff;
    font-size: 18px;
    font-weight: 800;
}
#moduleAction {
    min-height: 38px;
    color: #06111f;
    background: #8df3c8;
    border: 1px solid #8df3c8;
    border-radius: 8px;
    font-weight: 800;
    text-align: center;
}
#moduleAction:hover {
    background: #a9ffe0;
}
#logList {
    color: #dcefff;
    background: #07111f;
    border: 1px solid #284961;
    border-radius: 8px;
    padding: 8px;
}
#focusBar {
    min-height: 22px;
    color: #ffffff;
    background: #07111f;
    border: 1px solid #284961;
    border-radius: 8px;
    text-align: center;
}
#focusBar::chunk {
    background: #8df3c8;
    border-radius: 7px;
}
QLabel {
    color: #d7e7f3;
}
"""
