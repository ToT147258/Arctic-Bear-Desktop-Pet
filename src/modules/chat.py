import threading

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget

from src.llm_client import LLMClient, LLM_PROVIDERS, build_pet_system_prompt


class ChatPage(QWidget):
    response_ready = Signal(str)
    error_ready = Signal(str)
    test_ready = Signal(bool, str)

    def __init__(self, store, pet_window, play_action):
        super().__init__()
        self.store = store
        self.pet_window = pet_window
        self.play_action = play_action
        self.status_label = None
        self.llm_status_label = None
        self.llm_toggle_button = None
        self.llm_test_button = None
        self.chat_scroll = None
        self.chat_messages = None
        self.chat_messages_layout = None
        self.input = None
        self.send_button = None
        self._busy = False
        self._pending_user_text = ""
        self._build_ui()
        self.store.changed.connect(self.refresh)
        self.response_ready.connect(self._on_ai_response)
        self.error_ready.connect(self._on_ai_error)
        self.test_ready.connect(self._on_test_result)
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

        llm_card = QFrame()
        llm_card.setObjectName("moduleCard")
        llm_layout = QVBoxLayout(llm_card)
        llm_heading = QLabel("AI 大模型陪伴")
        llm_heading.setObjectName("cardTitle")
        self.llm_status_label = QLabel()
        self.llm_status_label.setWordWrap(True)
        self.llm_status_label.setObjectName("pageDescription")
        llm_actions = QHBoxLayout()
        self.llm_toggle_button = QPushButton()
        self.llm_toggle_button.setCursor(Qt.PointingHandCursor)
        self.llm_toggle_button.setObjectName("quickAction")
        self.llm_toggle_button.clicked.connect(self._toggle_llm)
        self.llm_test_button = QPushButton("测试连接")
        self.llm_test_button.setCursor(Qt.PointingHandCursor)
        self.llm_test_button.setObjectName("quickAction")
        self.llm_test_button.clicked.connect(self._test_llm)
        llm_actions.addWidget(self.llm_toggle_button)
        llm_actions.addWidget(self.llm_test_button)
        llm_layout.addWidget(llm_heading)
        llm_layout.addWidget(self.llm_status_label)
        llm_layout.addLayout(llm_actions)
        layout.addWidget(llm_card)

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
        chat_card.setObjectName("chatPanel")
        chat_layout = QVBoxLayout(chat_card)
        chat_layout.setContentsMargins(18, 16, 18, 18)
        chat_layout.setSpacing(12)
        chat_heading = QLabel("对话记录")
        chat_heading.setObjectName("cardTitle")
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("chatScroll")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_messages = QWidget()
        self.chat_messages.setObjectName("chatMessages")
        self.chat_messages_layout = QVBoxLayout(self.chat_messages)
        self.chat_messages_layout.setContentsMargins(16, 14, 16, 14)
        self.chat_messages_layout.setSpacing(10)
        self.chat_messages_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_messages)
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.input = QLineEdit()
        self.input.setObjectName("chatInput")
        self.input.setPlaceholderText("输入想和小熊说的话...")
        self.input.returnPressed.connect(self._send_from_input)
        send = QPushButton("发送")
        self.send_button = send
        send.setCursor(Qt.PointingHandCursor)
        send.setObjectName("moduleAction")
        send.clicked.connect(self._send_from_input)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(send, 0)
        chat_layout.addWidget(chat_heading)
        chat_layout.addWidget(self.chat_scroll)
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
        llm = LLMClient(self.store)
        cfg = llm.config
        provider = LLM_PROVIDERS.get(cfg["provider"], LLM_PROVIDERS["deepseek"])
        state = "已启用" if cfg.get("enabled") else "未启用"
        key_state = "已填写 Key" if cfg.get("api_key") else "未填写 Key"
        self.llm_status_label.setText(
            f"联网大模型：{state} · {provider['name']} · {cfg.get('model')} · {key_state}。"
            " 具体 API Key、模型和地址可在“系统设置”的 AI 大模型卡片里修改。"
        )
        self.llm_toggle_button.setText("关闭大模型" if cfg.get("enabled") else "启用大模型")
        self._render_chat_history()

    def _render_chat_history(self):
        if not self.chat_messages_layout:
            return
        while self.chat_messages_layout.count():
            item = self.chat_messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        history = list(reversed(self.store.chat_history[:40]))
        if not history:
            empty = QLabel("小熊在这里等你说话。")
            empty.setAlignment(Qt.AlignCenter)
            empty.setObjectName("emptyChat")
            self.chat_messages_layout.addStretch()
            self.chat_messages_layout.addWidget(empty)
            self.chat_messages_layout.addStretch()
        else:
            for item in history:
                self._add_message_bubble(item)
            self.chat_messages_layout.addStretch()
        QTimer.singleShot(0, self._scroll_chat_to_bottom)

    def _add_message_bubble(self, item):
        role = "user" if item.get("role") == "user" else "bear"
        row = QWidget()
        row.setObjectName("messageRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        bubble = QFrame()
        bubble.setObjectName("chatBubble")
        bubble.setProperty("role", role)
        bubble.setMaximumWidth(720)
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(14, 10, 14, 11)
        bubble_layout.setSpacing(5)

        speaker = "你" if role == "user" else "北极熊"
        meta = QLabel(f"{item.get('time', '--:--')}  {speaker}")
        meta.setObjectName("bubbleMeta")
        meta.setProperty("role", role)
        text = QLabel(str(item.get("text", "")))
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text.setObjectName("bubbleText")
        text.setProperty("role", role)
        bubble_layout.addWidget(meta)
        bubble_layout.addWidget(text)

        if role == "user":
            row_layout.addStretch(1)
            row_layout.addWidget(bubble, 0, Qt.AlignRight)
        else:
            row_layout.addWidget(bubble, 0, Qt.AlignLeft)
            row_layout.addStretch(1)
        self.chat_messages_layout.addWidget(row)

    def _scroll_chat_to_bottom(self):
        if self.chat_scroll:
            bar = self.chat_scroll.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _send_from_input(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._send_message(text)

    def _send_message(self, text):
        if self._busy:
            return
        self.store.add_chat_message("user", text)
        llm = LLMClient(self.store)
        reason = llm.unavailable_reason()
        if reason is None:
            self._pending_user_text = text
            self._busy = True
            self._set_send_enabled(False)
            messages = self._llm_messages()
            threading.Thread(target=self._worker_chat, args=(messages,), daemon=True).start()
            return
        reply, action = self._reply_for(text)
        if llm.config.get("enabled") and reason != "大模型未启用。":
            reply = f"联网大模型暂时不可用（{reason}），我先用本地回应：{reply}"
        self._deliver_reply(reply, action)

    def _worker_chat(self, messages):
        try:
            reply = LLMClient(self.store).chat(
                messages,
                system_prompt=build_pet_system_prompt(self.store),
                timeout=24,
            )
            self.response_ready.emit(reply or "我刚刚有点卡住了，可以再说一次嘛。")
        except Exception as exc:
            self.error_ready.emit(str(exc))

    def _on_ai_response(self, reply):
        action = self._action_for_text(f"{self._pending_user_text} {reply}")
        self._deliver_reply(reply, action)
        self._busy = False
        self._set_send_enabled(True)
        self._pending_user_text = ""

    def _on_ai_error(self, error):
        reply, action = self._reply_for(self._pending_user_text)
        self._deliver_reply(f"联网模型调用失败：{error}。我先用本地模式回答：{reply}", action)
        self._busy = False
        self._set_send_enabled(True)
        self._pending_user_text = ""

    def _llm_messages(self):
        messages = []
        for item in reversed(self.store.chat_history[:10]):
            role = item.get("role")
            if role == "bear":
                role = "assistant"
            elif role != "user":
                continue
            text = str(item.get("text") or "").strip()
            if text:
                messages.append({"role": role, "content": text})
        return messages[-10:]

    def _deliver_reply(self, reply, action):
        self.store.add_chat_message("bear", reply)
        if action == "touch":
            self.store.touch()
        elif action in {"rest", "sleep"}:
            self.store.rest()
        self.play_action(action if action in {"touch", "wave", "sleep"} else "idle", reply)

    def _set_send_enabled(self, enabled):
        if self.send_button:
            self.send_button.setEnabled(enabled)
        if self.input:
            self.input.setEnabled(enabled)

    def _toggle_llm(self):
        client = LLMClient(self.store)
        cfg = client.config
        cfg["enabled"] = not cfg.get("enabled", False)
        self.store.set_llm_config(cfg)

    def _test_llm(self):
        if self.llm_test_button:
            self.llm_test_button.setEnabled(False)
            self.llm_test_button.setText("测试中...")
        threading.Thread(target=self._worker_test_llm, daemon=True).start()

    def _worker_test_llm(self):
        ok, message = LLMClient(self.store).quick_check()
        self.test_ready.emit(ok, message)

    def _on_test_result(self, ok, message):
        if self.llm_test_button:
            self.llm_test_button.setEnabled(True)
            self.llm_test_button.setText("测试连接")
        self.store.add_log("AI", message)
        self.llm_status_label.setText(message)

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
            return "收到摸摸头，心情变好啦；好感要靠完整关怀、专注或礼物慢慢建立。", "touch"
        if "鼓励" in text or "加油" in text:
            return "你已经把这个项目一点点做起来了，继续收尾就会越来越像真正的软件。", "wave"
        return "我在这儿呢。你继续做项目，我会帮你看着提醒和状态。", "idle"

    def _action_for_text(self, text):
        if "休息" in text or "睡" in text or "累" in text:
            return "sleep"
        if "摸" in text or "摸摸" in text or "开心" in text:
            return "touch"
        if "提醒" in text or "课程" in text or "加油" in text or "鼓励" in text:
            return "wave"
        return "idle"


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
#moduleCard, #chatPanel {
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
#moduleAction:disabled, #quickAction:disabled {
    color: #88a3b2;
    background: #e9f4f8;
    border-color: #d3e9f0;
}
#quickAction:hover, #moduleAction:hover {
    background: #ffd374;
}
#chatScroll {
    min-height: 340px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f7fdff, stop:0.46 #ffffff, stop:1 #fff3f8);
    border: 1px solid #bde8f4;
    border-radius: 14px;
}
#chatMessages {
    background: transparent;
}
#emptyChat {
    color: #89a9b8;
    font-size: 15px;
    font-weight: 800;
}
QFrame#chatBubble {
    border-radius: 16px;
}
QFrame#chatBubble[role="bear"] {
    background: rgba(255, 255, 255, 238);
    border: 1px solid #bde8f4;
}
QFrame#chatBubble[role="user"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #62c8e7, stop:0.56 #89dfd1, stop:1 #ffabc8);
    border: 1px solid #ffffff;
}
#bubbleMeta {
    font-size: 12px;
    font-weight: 900;
}
#bubbleMeta[role="bear"] {
    color: #63aabe;
}
#bubbleMeta[role="user"] {
    color: rgba(255, 255, 255, 210);
}
#bubbleText {
    font-size: 15px;
}
#bubbleText[role="bear"] {
    color: #284f66;
}
#bubbleText[role="user"] {
    color: #ffffff;
}
#chatInput {
    min-height: 44px;
    color: #31556b;
    background: #ffffff;
    border: 1px solid #bde8f4;
    border-radius: 16px;
    padding: 4px 14px;
    font-size: 14px;
}
#chatInput:focus {
    border-color: #64c9e8;
}
QScrollBar:vertical {
    width: 10px;
    background: transparent;
    margin: 10px 2px 10px 2px;
}
QScrollBar::handle:vertical {
    background: #bde8f4;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QLabel {
    color: #31556b;
}
"""
