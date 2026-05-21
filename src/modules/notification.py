from pathlib import Path

from PySide6.QtCore import QTime, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from src.course_ocr import WEEKDAY_NAMES, detect_ocr_status, parse_timetable_text, recognize_timetable_image


class NotificationPage(QWidget):
    def __init__(self, store, pet_window):
        super().__init__()
        self.store = store
        self.pet_window = pet_window
        self.course_list = None
        self.log_list = None
        self.focus_label = None
        self.focus_bar = None
        self.pause_button = None
        self.course_title_input = None
        self.course_day_input = None
        self.course_time_input = None
        self.course_location_input = None
        self.course_note_input = None
        self.next_course_label = None
        self.schedule_table = None
        self.ocr_status_label = None
        self.ocr_text_input = None
        self._build_ui()
        self._refresh_ocr_status()
        self.store.changed.connect(self.refresh)
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(16)

        title = QLabel("课程提醒与消息中心")
        title.setObjectName("pageTitle")
        desc = QLabel("管理今日课程、地点和提醒气泡；需要专注时也可以从这里启动番茄钟。")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(desc)

        layout.addWidget(self._build_smart_card())
        layout.addWidget(self._build_schedule_preview_card())
        layout.addWidget(self._build_ocr_card())
        layout.addWidget(self._build_course_card())
        layout.addWidget(self._build_focus_card())
        layout.addWidget(self._build_log_card())
        layout.addStretch()
        self.setStyleSheet(PAGE_STYLE)

    def _build_smart_card(self):
        card = QFrame()
        card.setObjectName("smartCourseCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)
        text_block = QVBoxLayout()
        kicker = QLabel("SMART COURSE ASSISTANT")
        kicker.setObjectName("smartKicker")
        title = QLabel("下一节课智能提醒")
        title.setObjectName("smartTitle")
        self.next_course_label = QLabel()
        self.next_course_label.setWordWrap(True)
        self.next_course_label.setObjectName("smartText")
        text_block.addWidget(kicker)
        text_block.addWidget(title)
        text_block.addWidget(self.next_course_label)
        action = QPushButton("立即提醒")
        action.setCursor(Qt.PointingHandCursor)
        action.setObjectName("moduleAction")
        action.clicked.connect(self._trigger_course)
        layout.addLayout(text_block, 1)
        layout.addWidget(action, 0)
        return card

    def _build_schedule_preview_card(self):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        heading = QLabel("我的课表预览")
        heading.setObjectName("cardTitle")
        self.schedule_table = QTableWidget(5, 7)
        self.schedule_table.setObjectName("scheduleTable")
        self.schedule_table.setHorizontalHeaderLabels(WEEKDAY_NAMES)
        self.schedule_table.setVerticalHeaderLabels([
            "08:20\n第一大节",
            "10:20\n第二大节",
            "14:10\n第三大节",
            "16:00\n第四大节",
            "19:10\n第五大节",
        ])
        self.schedule_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.schedule_table.setSelectionMode(QTableWidget.NoSelection)
        self.schedule_table.setWordWrap(True)
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.schedule_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.schedule_table.verticalHeader().setMinimumWidth(86)
        self.schedule_table.setMinimumHeight(360)
        layout.addWidget(heading)
        layout.addWidget(self.schedule_table)
        return card

    def _build_course_card(self):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        heading = QLabel("今日课程")
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)

        form = QGridLayout()
        form.setSpacing(10)
        self.course_title_input = QLineEdit()
        self.course_title_input.setPlaceholderText("课程名称，例如：高等数学 / 项目自习")
        self.course_title_input.setObjectName("formInput")
        self.course_day_input = QComboBox()
        self.course_day_input.addItems(["每天", *WEEKDAY_NAMES])
        self.course_day_input.setObjectName("formInput")
        self.course_time_input = QTimeEdit()
        self.course_time_input.setDisplayFormat("HH:mm")
        self.course_time_input.setTime(QTime.currentTime().addSecs(3600))
        self.course_time_input.setObjectName("formInput")
        self.course_location_input = QLineEdit()
        self.course_location_input.setPlaceholderText("地点，例如：教学楼 A301")
        self.course_location_input.setObjectName("formInput")
        self.course_note_input = QLineEdit()
        self.course_note_input.setPlaceholderText("备注，例如：提前带教材 / 交作业")
        self.course_note_input.setObjectName("formInput")
        form.addWidget(self.course_title_input, 0, 0)
        form.addWidget(self.course_day_input, 0, 1)
        form.addWidget(self.course_time_input, 0, 2)
        form.addWidget(self.course_location_input, 1, 0)
        form.addWidget(self.course_note_input, 1, 1, 1, 2)
        layout.addLayout(form)

        action_grid = QGridLayout()
        action_grid.setSpacing(10)
        actions = [
            ("添加课程", self._add_course),
            ("触发提醒气泡", self._trigger_course),
            ("删除选中", self._delete_selected_course),
            ("清空课表", self._clear_courses),
        ]
        for index, (label, callback) in enumerate(actions):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("moduleAction" if index != 2 else "secondaryAction")
            button.clicked.connect(callback)
            action_grid.addWidget(button, index // 2, index % 2)
        layout.addLayout(action_grid)

        self.course_list = QListWidget()
        self.course_list.setObjectName("courseList")
        layout.addWidget(self.course_list)
        return card

    def _build_ocr_card(self):
        card = QFrame()
        card.setObjectName("ocrCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        heading = QLabel("课表照片智能识别")
        heading.setObjectName("cardTitle")
        tip = QLabel("选择一张清晰、正向、无遮挡的课表图片。识别成功后会自动解析星期、时间、课程名和地点；如果电脑还没装 OCR，可以把识别文字粘贴进文本框再解析。")
        tip.setWordWrap(True)
        tip.setObjectName("pageDescription")
        self.ocr_status_label = QLabel("等待导入课表照片。")
        self.ocr_status_label.setWordWrap(True)
        self.ocr_status_label.setObjectName("ocrStatus")
        self.ocr_text_input = QPlainTextEdit()
        self.ocr_text_input.setObjectName("ocrText")
        self.ocr_text_input.setPlaceholderText("OCR 识别出的课表文字会显示在这里，也可以手动粘贴文本后点击“解析文本导入”。")
        self.ocr_text_input.setMaximumHeight(150)
        actions = QGridLayout()
        actions.setSpacing(10)
        buttons = [
            ("导入课表照片", self._import_timetable_image),
            ("解析文本导入", self._parse_ocr_text),
            ("替换为识别结果", self._replace_with_ocr_text),
            ("检测 OCR 环境", self._refresh_ocr_status),
        ]
        for index, (label, callback) in enumerate(buttons):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("moduleAction" if index != 2 else "secondaryAction")
            button.clicked.connect(callback)
            actions.addWidget(button, index // 2, index % 2)
        layout.addWidget(heading)
        layout.addWidget(tip)
        layout.addWidget(self.ocr_status_label)
        layout.addWidget(self.ocr_text_input)
        layout.addLayout(actions)
        return card

    def _build_focus_card(self):
        focus_card = QFrame()
        focus_card.setObjectName("moduleCard")
        focus_layout = QVBoxLayout(focus_card)
        focus_layout.setSpacing(10)
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
            focus_actions.addWidget(button, index // 2, index % 2)
        focus_layout.addWidget(focus_heading)
        focus_layout.addWidget(self.focus_label)
        focus_layout.addWidget(self.focus_bar)
        focus_layout.addLayout(focus_actions)
        return focus_card

    def _build_log_card(self):
        log_card = QFrame()
        log_card.setObjectName("moduleCard")
        log_layout = QVBoxLayout(log_card)
        heading = QLabel("最近通知日志")
        heading.setObjectName("cardTitle")
        self.log_list = QListWidget()
        self.log_list.setObjectName("logList")
        clear_button = QPushButton("清空日志")
        clear_button.setCursor(Qt.PointingHandCursor)
        clear_button.setObjectName("secondaryAction")
        clear_button.clicked.connect(self.store.clear_logs)
        log_layout.addWidget(heading)
        log_layout.addWidget(self.log_list)
        log_layout.addWidget(clear_button)
        return log_card

    def refresh(self):
        self._refresh_courses()
        self._refresh_schedule_table()
        self._refresh_smart_summary()
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

    def _refresh_courses(self):
        self.course_list.clear()
        for course in self.store.course_reminders:
            title = course.get("title", "未命名课程")
            time_text = course.get("time", "00:00")
            location = course.get("location", "未设置地点")
            note = course.get("note", "提前准备一下")
            day = course.get("day", "每天")
            source = "识别导入" if course.get("source") == "ocr" else "手动"
            self.course_list.addItem(f"{day} {time_text}  {title}  @ {location}  · {source}\n{note}")

    def _refresh_schedule_table(self):
        if not self.schedule_table:
            return
        slot_rows = {
            "08:20": 0,
            "08:00": 0,
            "10:20": 1,
            "10:10": 1,
            "14:10": 2,
            "14:00": 2,
            "16:00": 3,
            "16:10": 3,
            "19:10": 4,
            "19:00": 4,
        }
        day_cols = {day: index for index, day in enumerate(WEEKDAY_NAMES)}
        cells = {}
        for course in self.store.course_reminders:
            day = course.get("day", "每天")
            time_text = str(course.get("time", "00:00"))[:5]
            if day not in day_cols or time_text not in slot_rows:
                continue
            key = (slot_rows[time_text], day_cols[day])
            title = course.get("title", "未命名课程")
            location = course.get("location", "待确认地点")
            entry = f"{title}\n@ {location}"
            cells.setdefault(key, []).append(entry)
        for row in range(self.schedule_table.rowCount()):
            for col in range(self.schedule_table.columnCount()):
                text = "\n\n".join(cells.get((row, col), []))
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self.schedule_table.setItem(row, col, item)
        self.schedule_table.resizeRowsToContents()

    def _refresh_smart_summary(self):
        course = self.store.next_course_reminder()
        if not course:
            self.next_course_label.setText("还没有课程提醒。可以手动添加，或者导入一张课表照片自动识别。")
            return
        minutes = int(course.get("minutes_left", 0))
        if minutes <= 15:
            urgency = "马上就要开始了，建议现在准备。"
        elif minutes <= 60:
            urgency = f"还有 {minutes} 分钟，适合提前收拾资料。"
        else:
            urgency = "时间还充裕，我会继续帮你盯着。"
        self.next_course_label.setText(
            f"{course.get('next_at_text', course.get('time', '00:00'))} · 《{course.get('title', '课程')}》\n"
            f"地点：{course.get('location', '未设置地点')} · {urgency}"
        )

    def _add_course(self):
        self.store.add_course_reminder(
            self.course_title_input.text(),
            self.course_time_input.time().toString("HH:mm"),
            self.course_location_input.text(),
            self.course_note_input.text(),
            self.course_day_input.currentText(),
        )
        self.course_title_input.clear()
        self.course_location_input.clear()
        self.course_note_input.clear()

    def _delete_selected_course(self):
        row = self.course_list.currentRow()
        self.store.remove_course_reminder(row)

    def _clear_courses(self):
        self.store.clear_course_reminders()

    def _import_timetable_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择课表照片",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
        )
        if not file_path:
            return
        text, message = recognize_timetable_image(file_path)
        self.ocr_status_label.setText(message)
        if text:
            self.ocr_text_input.setPlainText(text)
            self._parse_ocr_text()

    def _parse_ocr_text(self):
        text = self.ocr_text_input.toPlainText()
        courses = parse_timetable_text(text)
        if not courses:
            self.ocr_status_label.setText("没有解析出课程。建议保留每行包含：星期 + 时间/节次 + 课程名 + 地点。")
            return
        added = self.store.import_course_reminders(courses, replace=False)
        self.ocr_status_label.setText(f"解析到 {len(courses)} 条课程，新增导入 {added} 条。")

    def _replace_with_ocr_text(self):
        text = self.ocr_text_input.toPlainText()
        courses = parse_timetable_text(text)
        if not courses:
            self.ocr_status_label.setText("没有解析出课程，未替换当前课表。")
            return
        added = self.store.import_course_reminders(courses, replace=True)
        self.ocr_status_label.setText(f"已用识别结果替换当前课表，共导入 {added} 条。")

    def _refresh_ocr_status(self):
        status = detect_ocr_status()
        self.ocr_status_label.setText(status["message"])

    def _trigger_course(self):
        message = self.store.trigger_course_bubble()
        if self.store.settings.get("bubble_on", True):
            self.pet_window.show_bubble(message)

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
    color: #284f66;
    font-size: 30px;
    font-weight: 900;
}
#pageDescription {
    color: #5f7c8d;
    font-size: 14px;
}
#smartCourseCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffffff, stop:0.48 #eaf9ff, stop:1 #fff3f8);
    border: 1px solid #b9e6f2;
    border-radius: 8px;
}
#smartKicker {
    color: #61b8d0;
    font-size: 12px;
    font-weight: 900;
}
#smartTitle {
    color: #284f66;
    font-size: 26px;
    font-weight: 900;
}
#smartText {
    color: #31556b;
    font-size: 15px;
    font-weight: 800;
}
#moduleCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #edfaff);
    border: 1px solid #c4e5ef;
    border-radius: 8px;
    padding: 12px;
}
#ocrCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffffff, stop:0.58 #effcff, stop:1 #fff8e7);
    border: 1px solid #b9e6f2;
    border-radius: 8px;
    padding: 12px;
}
#cardTitle {
    color: #ff8ebc;
    font-size: 18px;
    font-weight: 900;
}
#formInput {
    min-height: 36px;
    color: #31556b;
    background: rgba(255, 255, 255, 220);
    border: 1px solid #c7e4ef;
    border-radius: 8px;
    padding: 4px 10px;
    selection-background-color: #ffadc8;
}
#formInput:focus {
    border-color: #64c9e8;
    background: #ffffff;
}
#ocrStatus {
    color: #31556b;
    background: #ffffff;
    border: 1px solid #ffd1df;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 13px;
    font-weight: 800;
}
#ocrText {
    color: #31556b;
    background: rgba(255, 255, 255, 230);
    border: 1px solid #c7e4ef;
    border-radius: 8px;
    padding: 8px;
    font-size: 13px;
}
#ocrText:focus {
    border-color: #64c9e8;
}
#moduleAction, #secondaryAction {
    min-height: 38px;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #64c9e8, stop:1 #ffadc8);
    border: 1px solid #ffffff;
    border-radius: 14px;
    font-weight: 900;
    text-align: center;
}
#secondaryAction {
    color: #31556b;
    background: #ffffff;
    border-color: #c7e4ef;
}
#moduleAction:hover {
    background: #ffd374;
}
#secondaryAction:hover {
    background: #fff4fa;
    border-color: #ffadc8;
}
#courseList, #logList {
    color: #31556b;
    background: rgba(255, 255, 255, 220);
    border: 1px solid #c7e4ef;
    border-radius: 8px;
    padding: 8px;
}
#scheduleTable {
    color: #31556b;
    background: rgba(255, 255, 255, 228);
    border: 1px solid #c7e4ef;
    border-radius: 8px;
    gridline-color: #d8edf4;
    font-size: 12px;
}
#scheduleTable::item {
    padding: 6px;
}
QHeaderView::section {
    color: #284f66;
    background: #eaf9ff;
    border: 1px solid #c7e4ef;
    padding: 6px;
    font-weight: 900;
}
#courseList::item, #logList::item {
    min-height: 34px;
    padding: 5px;
}
#courseList::item:selected, #logList::item:selected {
    color: #284f66;
    background: #eaf9ff;
}
#focusBar {
    min-height: 22px;
    color: #294f66;
    background: #dceff5;
    border: 1px solid #c7e4ef;
    border-radius: 11px;
    text-align: center;
    font-weight: 800;
}
#focusBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffabc8, stop:0.52 #8de1d0, stop:1 #63c7e7);
    border-radius: 10px;
}
QLabel {
    color: #31556b;
}
"""
