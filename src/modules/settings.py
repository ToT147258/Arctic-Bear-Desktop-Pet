from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QKeySequenceEdit,
    QSlider,
    QVBoxLayout,
    QWidget,
)


DEFAULT_HOTKEY = "Ctrl+Alt+B"


class SettingsPage(QWidget):
    def __init__(self, store, pet_window, get_hotkey=None, set_hotkey=None):
        super().__init__()
        self.store = store
        self.pet_window = pet_window
        self.get_hotkey = get_hotkey or (lambda: self.store.settings.get("pet_toggle_hotkey", DEFAULT_HOTKEY))
        self.set_hotkey = set_hotkey or self._fallback_set_hotkey
        self.scale_value = None
        self.opacity_value = None
        self.edge_threshold_value = None
        self.click_threshold_value = None
        self.hotkey_value = None
        self.hotkey_editor = None
        self.hotkey_status = None
        self.scale_slider = None
        self.opacity_slider = None
        self.edge_threshold_slider = None
        self.click_threshold_slider = None
        self._build_ui()
        self.store.changed.connect(self.refresh)
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(16)

        title = QLabel("系统设置与存档管理模块")
        title.setObjectName("pageTitle")
        desc = QLabel("这里可以调整桌宠大小、透明度、置顶、走路是否移动窗口，并导出或导入本地 JSON 存档。")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(desc)

        layout.addWidget(self._scale_card())
        layout.addWidget(self._window_card())
        layout.addWidget(self._hotkey_card())
        layout.addWidget(self._save_card())
        layout.addStretch()
        self.setStyleSheet(PAGE_STYLE)

    def _scale_card(self):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        title = QLabel("显示比例")
        title.setObjectName("cardTitle")
        self.scale_value = QLabel()
        self.scale_value.setObjectName("taskItem")
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(40, 100)
        self.scale_slider.setSingleStep(5)
        self.scale_slider.setValue(self.pet_window.scale_percent)
        self.scale_slider.valueChanged.connect(self._preview_scale)
        self.scale_slider.sliderReleased.connect(self._save_scale)
        layout.addWidget(title)
        layout.addWidget(self.scale_value)
        layout.addWidget(self.scale_slider)
        return card

    def _window_card(self):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        title = QLabel("窗口行为")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        self.opacity_value = QLabel()
        self.opacity_value.setObjectName("taskItem")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(60, 100)
        self.opacity_slider.setSingleStep(5)
        self.opacity_slider.setValue(int(float(self.store.settings.get("opacity", 1.0)) * 100))
        self.opacity_slider.valueChanged.connect(self._preview_opacity)
        self.opacity_slider.sliderReleased.connect(self._save_opacity)
        layout.addWidget(self.opacity_value)
        layout.addWidget(self.opacity_slider)

        top = QCheckBox("桌宠始终置顶")
        top.setObjectName("checkBox")
        top.setChecked(bool(self.store.settings.get("always_on_top", True)))
        top.toggled.connect(self._toggle_topmost)
        layout.addWidget(top)

        bubble = QCheckBox("启用桌宠气泡提示")
        bubble.setObjectName("checkBox")
        bubble.setChecked(bool(self.store.settings.get("bubble_on", True)))
        bubble.toggled.connect(self._toggle_bubble)
        layout.addWidget(bubble)

        decay = QCheckBox("状态随时间自然变化")
        decay.setObjectName("checkBox")
        decay.setChecked(bool(self.store.settings.get("status_decay", True)))
        decay.toggled.connect(self._toggle_decay)
        layout.addWidget(decay)

        auto_feed = QCheckBox("饱食度过低时自动投喂")
        auto_feed.setObjectName("checkBox")
        auto_feed.setChecked(bool(self.store.settings.get("auto_feed", True)))
        auto_feed.toggled.connect(self._toggle_auto_feed)
        layout.addWidget(auto_feed)

        walk = QCheckBox("走路时移动窗口")
        walk.setObjectName("checkBox")
        walk.setChecked(bool(getattr(self.pet_window, "_walk_window_move", True)))
        walk.toggled.connect(self._toggle_walk_move)
        layout.addWidget(walk)

        edge = QCheckBox("拖拽结束时贴边吸附")
        edge.setObjectName("checkBox")
        edge.setChecked(bool(self.store.settings.get("edge_snap_enabled", True)))
        edge.toggled.connect(self._toggle_edge_snap)
        layout.addWidget(edge)

        self.edge_threshold_value = QLabel()
        self.edge_threshold_value.setObjectName("taskItem")
        self.edge_threshold_slider = QSlider(Qt.Horizontal)
        self.edge_threshold_slider.setRange(8, 96)
        self.edge_threshold_slider.setSingleStep(4)
        self.edge_threshold_slider.setValue(int(self.store.settings.get("edge_snap_threshold", 48)))
        self.edge_threshold_slider.valueChanged.connect(self._preview_edge_threshold)
        self.edge_threshold_slider.sliderReleased.connect(self._save_edge_threshold)
        layout.addWidget(self.edge_threshold_value)
        layout.addWidget(self.edge_threshold_slider)

        self.click_threshold_value = QLabel()
        self.click_threshold_value.setObjectName("taskItem")
        self.click_threshold_slider = QSlider(Qt.Horizontal)
        self.click_threshold_slider.setRange(3, 12)
        self.click_threshold_slider.setSingleStep(1)
        self.click_threshold_slider.setValue(int(self.store.settings.get("pat_multi_click_talk_threshold", 6)))
        self.click_threshold_slider.valueChanged.connect(self._preview_click_threshold)
        self.click_threshold_slider.sliderReleased.connect(self._save_click_threshold)
        layout.addWidget(self.click_threshold_value)
        layout.addWidget(self.click_threshold_slider)
        return card

    def _hotkey_card(self):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        title = QLabel("桌宠快捷键")
        title.setObjectName("cardTitle")
        desc = QLabel("点击录制框后按下新的组合键，再保存即可。建议使用 Ctrl / Alt / Shift 加字母或功能键。")
        desc.setWordWrap(True)
        desc.setObjectName("taskItem")
        self.hotkey_value = QLabel()
        self.hotkey_value.setObjectName("taskItem")
        self.hotkey_editor = QKeySequenceEdit()
        self.hotkey_editor.setObjectName("hotkeyEditor")
        self.hotkey_editor.setClearButtonEnabled(True)
        self.hotkey_editor.setKeySequence(QKeySequence(self.get_hotkey()))
        self.hotkey_status = QLabel("保存后会立即应用到全局快捷键。")
        self.hotkey_status.setWordWrap(True)
        self.hotkey_status.setObjectName("taskItem")
        row = QHBoxLayout()
        save = QPushButton("保存快捷键")
        save.setCursor(Qt.PointingHandCursor)
        save.setObjectName("moduleAction")
        save.clicked.connect(self._save_hotkey)
        reset = QPushButton("恢复 Ctrl+Alt+B")
        reset.setCursor(Qt.PointingHandCursor)
        reset.setObjectName("moduleAction")
        reset.clicked.connect(self._reset_hotkey)
        row.addWidget(save)
        row.addWidget(reset)
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addWidget(self.hotkey_value)
        layout.addWidget(self.hotkey_editor)
        layout.addWidget(self.hotkey_status)
        layout.addLayout(row)
        return card

    def _save_card(self):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        title = QLabel("存档管理")
        title.setObjectName("cardTitle")
        desc = QLabel("默认存档位置：data/save.json；导出文件会生成在 data/save-export.json。")
        desc.setWordWrap(True)
        desc.setObjectName("taskItem")
        row = QHBoxLayout()
        for label, callback in [
            ("保存设置", self._save_settings),
            ("导出存档", self._export_save),
            ("导入存档", self._import_save),
            ("恢复默认", self._reset_all),
        ]:
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setObjectName("moduleAction")
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addLayout(row)
        return card

    def refresh(self):
        self.scale_value.setText(f"当前比例：{self.pet_window.scale_percent}%")
        opacity = int(float(self.store.settings.get("opacity", 1.0)) * 100)
        self.opacity_value.setText(f"当前透明度：{opacity}%")
        if self.edge_threshold_value:
            self.edge_threshold_value.setText(f"贴边吸附距离：{self.store.settings.get('edge_snap_threshold', 48)} px")
        if self.click_threshold_value:
            self.click_threshold_value.setText(
                f"连续互动气泡阈值：{self.store.settings.get('pat_multi_click_talk_threshold', 6)} 次"
            )
        if self.hotkey_value:
            hotkey = self.get_hotkey() or DEFAULT_HOTKEY
            self.hotkey_value.setText(f"当前显示 / 隐藏快捷键：{hotkey}")

    def _preview_scale(self, value):
        self.scale_value.setText(f"当前比例：{value}%")
        self.pet_window.set_pet_scale(value / 100, persist=False)

    def _save_scale(self):
        self.pet_window.set_pet_scale(self.scale_slider.value() / 100, persist=True)
        self.store.add_log("设置", f"桌宠缩放已设置为 {self.scale_slider.value()}%。")

    def _preview_opacity(self, value):
        self.opacity_value.setText(f"当前透明度：{value}%")
        self.pet_window.setWindowOpacity(value / 100)

    def _save_opacity(self):
        value = self.opacity_slider.value() / 100
        self.pet_window.setWindowOpacity(value)
        self.store.set_setting("opacity", value)

    def _toggle_topmost(self, checked):
        self.pet_window.set_always_on_top(checked)
        self.store.set_setting("always_on_top", bool(checked))

    def _toggle_walk_move(self, checked):
        self.pet_window.set_walk_window_move(bool(checked))
        self.store.add_log("设置", "走路窗口移动已开启。" if checked else "走路窗口移动已关闭。")

    def _toggle_bubble(self, checked):
        self.store.set_setting("bubble_on", bool(checked))

    def _toggle_decay(self, checked):
        self.store.set_setting("status_decay", bool(checked))

    def _toggle_auto_feed(self, checked):
        self.store.set_setting("auto_feed", bool(checked))

    def _toggle_edge_snap(self, checked):
        self.pet_window.set_edge_snap(bool(checked), self.edge_threshold_slider.value())
        self.store.set_setting("edge_snap_enabled", bool(checked))

    def _preview_edge_threshold(self, value):
        self.edge_threshold_value.setText(f"贴边吸附距离：{value} px")
        self.pet_window.set_edge_snap(bool(self.store.settings.get("edge_snap_enabled", True)), value)

    def _save_edge_threshold(self):
        value = int(self.edge_threshold_slider.value())
        self.pet_window.set_edge_snap(bool(self.store.settings.get("edge_snap_enabled", True)), value)
        self.store.set_setting("edge_snap_threshold", value)

    def _preview_click_threshold(self, value):
        self.click_threshold_value.setText(f"连续互动气泡阈值：{value} 次")

    def _save_click_threshold(self):
        self.store.set_setting("pat_multi_click_talk_threshold", int(self.click_threshold_slider.value()))

    def _fallback_set_hotkey(self, hotkey):
        self.store.set_setting("pet_toggle_hotkey", hotkey)
        return True, f"快捷键已保存为 {hotkey}。"

    def _editor_hotkey_text(self):
        sequence = self.hotkey_editor.keySequence()
        if sequence.isEmpty():
            return ""
        return sequence.toString(QKeySequence.SequenceFormat.PortableText)

    def _save_hotkey(self):
        hotkey = self._editor_hotkey_text()
        ok, message = self.set_hotkey(hotkey)
        self.hotkey_status.setText(message)
        if ok:
            current = self.get_hotkey() or hotkey
            self.hotkey_editor.setKeySequence(QKeySequence(current))
            self.refresh()

    def _reset_hotkey(self):
        self.hotkey_editor.setKeySequence(QKeySequence(DEFAULT_HOTKEY))
        self._save_hotkey()

    def _save_settings(self):
        self.store.save()
        self.store.add_log("设置", "当前设置已保存。")

    def _export_save(self):
        export_path = Path(self.store.save_path).with_name("save-export.json")
        self.store.export_to(export_path)

    def _import_save(self):
        export_path = Path(self.store.save_path).with_name("save-export.json")
        self.store.import_from(export_path)

    def _reset_all(self):
        self.store.reset_all()
        self.pet_window.set_pet_scale(0.5)
        self.pet_window.setWindowOpacity(1.0)
        self.pet_window.set_always_on_top(True)
        self.pet_window.set_edge_snap(True, 48)
        self.hotkey_editor.setKeySequence(QKeySequence(DEFAULT_HOTKEY))
        self.set_hotkey(DEFAULT_HOTKEY)
        self.scale_slider.setValue(50)
        self.opacity_slider.setValue(100)
        self.edge_threshold_slider.setValue(48)
        self.click_threshold_slider.setValue(6)


PAGE_STYLE = """
#pageTitle {
    color: #284f66;
    font-size: 30px;
    font-weight: 900;
}
#pageDescription, #taskItem {
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
#checkBox {
    color: #31556b;
    font-size: 14px;
}
QSlider::groove:horizontal {
    height: 8px;
    background: #dceff5;
    border: 1px solid #c7e4ef;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    width: 18px;
    margin: -6px 0;
    background: #ff9fc3;
    border-radius: 9px;
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
QKeySequenceEdit#hotkeyEditor {
    min-height: 38px;
    color: #284f66;
    background: #ffffff;
    border: 1px solid #b8e1ef;
    border-radius: 12px;
    padding: 6px 10px;
}
QLabel {
    color: #31556b;
}
"""
