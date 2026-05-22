from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout, QWidget


class ChatPage(QWidget):
    def __init__(self, store, pet_window, play_action):
        super().__init__()
        self.store = store
        self.pet_window = pet_window
        self.play_action = play_action
        self.status_label = None
        self.chat_list = None
        self.input = None
        self._build_ui()
        self.store.changed.connect(self.refresh)
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(16)

        title = QLabel("聊天互动与陪伴反馈")
        title.setObjectName("pageTitle")
        desc = QLabel("和北极熊说说话，桌宠会根据当前状态、课程提醒和互动记录给出轻量回应。")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(desc)

        status_card = QFrame()
        status_card.setObjectName("moduleCard")
        status_layout = QVBoxLayout(status_card)
        heading = QLabel("陪伴状态")
        heading.setObjectName("cardTitle")
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("pageDescription")
        status_layout.addWidget(heading)
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_card)

        quick_grid = QGridLayout()
        quick_grid.setSpacing(10)
        quick_actions = [
            ("打招呼", "你好呀"),
            ("今日安排", "今天有什么提醒"),
            ("鼓励我", "给我一点鼓励"),
            ("摸摸头", "摸摸头"),
            ("饿了吗", "你饿了吗"),
            ("休息建议", "现在要不要休息"),
        ]
        for index, (label, text) in enumerate(quick_actions):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("quickAction")
            button.clicked.connect(lambda checked=False, value=text: self._send_message(value))
            quick_grid.addWidget(button, index // 3, index % 3)
        layout.addLayout(quick_grid)

        chat_card = QFrame()
        chat_card.setObjectName("moduleCard")
        chat_layout = QVBoxLayout(chat_card)
        chat_heading = QLabel("对话记录")
        chat_heading.setObjectName("cardTitle")
        self.chat_list = QListWidget()
        self.chat_list.setObjectName("chatList")
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setObjectName("chatInput")
        self.input.setPlaceholderText("输入想和小熊说的话...")
        self.input.returnPressed.connect(self._send_from_input)
        send = QPushButton("发送")
        send.setCursor(Qt.PointingHandCursor)
        send.setObjectName("moduleAction")
        send.clicked.connect(self._send_from_input)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(send, 0)
        chat_layout.addWidget(chat_heading)
        chat_layout.addWidget(self.chat_list)
        chat_layout.addLayout(input_row)
        layout.addWidget(chat_card)
        layout.addStretch()
        self.setStyleSheet(PAGE_STYLE)

    def refresh(self):
        stats = self.store.stats
        course_title, course_time, course_location = self.store.course_summary()
        self.status_label.setText(
            f"心情 {stats.get('mood', 0)}% / 饱食 {stats.get('hunger', 0)}% / 体力 {stats.get('energy', 0)}%  ·  "
            f"下一条提醒：{course_time}《{course_title}》@ {course_location}"
        )
        self.chat_list.clear()
        for item in self.store.chat_history[:30]:
            speaker = "你" if item.get("role") == "user" else "北极熊"
            self.chat_list.addItem(f"{item.get('time', '--:--')}  {speaker}：{item.get('text', '')}")

    def _send_from_input(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._send_message(text)

    def _send_message(self, text):
        self.store.add_chat_message("user", text)
        reply, action = self._reply_for(text)
        self.store.add_chat_message("bear", reply)
        if action == "touch":
            self.store.touch()
        elif action == "rest":
            self.store.rest()
        if self.store.settings.get("bubble_on", True):
            if not self.pet_window.isVisible():
                self.pet_window.show()
            self.pet_window.show_bubble(reply)
        self.play_action(action if action in {"touch", "wave", "sleep"} else "idle", reply)

    def _reply_for(self, text):
        lowered = text.lower()
        stats = self.store.stats
        course_title, course_time, course_location = self.store.course_summary()
        if "提醒" in text or "课程" in text or "安排" in text:
            return f"下一条提醒是 {course_time}《{course_title}》，地点在 {course_location}。我会陪你记着。", "wave"
        if "饿" in text or "吃" in text:
            if int(stats.get("hunger", 0)) < 55:
                return "我有点想吃极地鱼干了，可以去外观装扮页给我准备一点。", "touch"
            return "现在还不饿，先把鱼干留着，金币也要省一点。", "idle"
        if "累" in text or "休息" in text or int(stats.get("energy", 0)) < 35:
            return "那我们短休一下吧，恢复体力比硬撑更重要。", "sleep"
        if "摸" in text or "pat" in lowered:
            return "收到摸摸头，心情变好啦。", "touch"
        if "鼓励" in text or "加油" in text:
            return "你已经把这个项目一点点做起来了，继续收尾就会越来越像真正的软件。", "wave"
        return "我在这儿呢。你继续做项目，我会帮你看着提醒和状态。", "idle"


PAGE_STYLE = """
#pageTitle {
    color: #284f66;
    font-size: 30px;
    font-weight: 900;
}
#pageDescription {
    color: #5f7c8d;
    font-size: 14px;
}
#moduleCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #edfaff);
    border: 1px solid #c4e5ef;
    border-radius: 8px;
    padding: 12px;
}
#cardTitle {
    color: #ff8ebc;
    font-size: 18px;
    font-weight: 900;
}
#quickAction, #moduleAction {
    min-height: 42px;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #64c9e8, stop:0.55 #85decf, stop:1 #ffadc8);
    border: 1px solid #ffffff;
    border-radius: 14px;
    font-weight: 900;
    text-align: center;
}
#quickAction:hover, #moduleAction:hover {
    background: #ffd374;
}
#chatList {
    color: #31556b;
    background: rgba(255, 255, 255, 220);
    border: 1px solid #c7e4ef;
    border-radius: 8px;
    padding: 8px;
}
#chatList::item {
    min-height: 32px;
    padding: 5px;
}
#chatInput {
    min-height: 38px;
    color: #31556b;
    background: #ffffff;
    border: 1px solid #c7e4ef;
    border-radius: 8px;
    padding: 4px 10px;
}
#chatInput:focus {
    border-color: #64c9e8;
}
QLabel {
    color: #31556b;
}
"""
