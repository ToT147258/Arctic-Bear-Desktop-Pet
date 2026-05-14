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
    color: #ffffff;
    font-size: 30px;
    font-weight: 800;
}
#pageDescription {
    color: #b8cbda;
    font-size: 15px;
    line-height: 1.5;
}
#sectionTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
    margin-top: 8px;
}
#highlightCard, #moduleCard {
    background: #122237;
    border: 1px solid #2a4c68;
    border-radius: 10px;
    padding: 12px;
}
#highlightName {
    color: #9edff0;
    font-size: 13px;
    font-weight: 800;
}
#highlightValue {
    color: #ffffff;
    font-size: 24px;
    font-weight: 900;
}
#highlightNote, #taskItem {
    color: #b9ccdc;
    font-size: 13px;
}
#cardTitle {
    color: #7ee8ff;
    font-size: 17px;
    font-weight: 700;
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
QLabel {
    color: #d7e7f3;
    font-size: 14px;
}
"""
