from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget


class NotificationPage(QWidget):
    def __init__(self, store, pet_window):
        super().__init__()
        self.store = store
        self.pet_window = pet_window
        self.log_list = None
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

    def _show_bubble(self):
        message = "今天也照顾得很好。"
        self.pet_window.show_bubble(message)
        self.store.add_log("通知", "显示了一条桌宠气泡提示。")

    def _write_log(self):
        self.store.add_log("调试", "手动写入了一条测试日志。")

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
QLabel {
    color: #d7e7f3;
}
"""
