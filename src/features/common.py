from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ModulePage(QWidget):
    def __init__(self, title, description, highlights=None, tasks=None, actions=None):
        super().__init__()
        highlights = highlights or []
        tasks = tasks or []
        actions = actions or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(16)

        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        desc_label = QLabel(description)
        desc_label.setObjectName("pageDescription")
        desc_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)

        if highlights:
            grid = QGridLayout()
            grid.setSpacing(12)
            for index, item in enumerate(highlights):
                grid.addWidget(self._highlight_card(*item), index // 3, index % 3)
            layout.addLayout(grid)

        if tasks:
            section = QLabel("模块任务")
            section.setObjectName("sectionTitle")
            layout.addWidget(section)
            for task in tasks:
                layout.addWidget(self._task_card(task))

        if actions:
            section = QLabel("演示操作")
            section.setObjectName("sectionTitle")
            layout.addWidget(section)
            action_grid = QGridLayout()
            action_grid.setSpacing(10)
            for index, action in enumerate(actions):
                button = QPushButton(action)
                button.setCursor(Qt.PointingHandCursor)
                button.setObjectName("moduleAction")
                action_grid.addWidget(button, index // 3, index % 3)
            layout.addLayout(action_grid)

        layout.addStretch()
        self.setStyleSheet(PAGE_STYLE)

    def _highlight_card(self, name, value, note):
        card = QFrame()
        card.setObjectName("highlightCard")
        layout = QVBoxLayout(card)
        title = QLabel(name)
        title.setObjectName("highlightName")
        number = QLabel(value)
        number.setObjectName("highlightValue")
        desc = QLabel(note)
        desc.setObjectName("highlightNote")
        desc.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(number)
        layout.addWidget(desc)
        return card

    def _task_card(self, task):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        header = QLabel(f"{task['status']}  {task['title']}")
        header.setObjectName("cardTitle")
        desc = QLabel(task["description"])
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignTop)
        layout.addWidget(header)
        layout.addWidget(desc)

        for item in task.get("items", []):
            row = QLabel(f"- {item}")
            row.setWordWrap(True)
            row.setObjectName("taskItem")
            layout.addWidget(row)
        return card


PAGE_STYLE = """
#pageTitle {
    color: #284f66;
    font-size: 30px;
    font-weight: 900;
}
#pageDescription {
    color: #5f7c8d;
    font-size: 15px;
    line-height: 1.5;
}
#sectionTitle {
    color: #2d566d;
    font-size: 18px;
    font-weight: 900;
    margin-top: 8px;
}
#highlightCard, #moduleCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #edfaff);
    border: 1px solid #c4e5ef;
    border-radius: 8px;
    padding: 12px;
}
#highlightName {
    color: #61b8d0;
    font-size: 13px;
    font-weight: 900;
}
#highlightValue {
    color: #294f66;
    font-size: 24px;
    font-weight: 900;
}
#highlightNote, #taskItem {
    color: #5e7887;
    font-size: 13px;
}
#cardTitle {
    color: #ff8ebc;
    font-size: 17px;
    font-weight: 900;
}
#moduleAction {
    min-height: 38px;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #64c9e8, stop:1 #ffadc8);
    border: 1px solid #ffffff;
    border-radius: 14px;
    font-weight: 900;
    text-align: center;
}
#moduleAction:hover {
    background: #ffd374;
}
QLabel {
    color: #31556b;
    font-size: 14px;
}
"""
