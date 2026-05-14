from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget


class SettingsPage(QWidget):
    def __init__(self, store, pet_window):
        super().__init__()
        self.store = store
        self.pet_window = pet_window
        self.scale_value = None
        self.opacity_value = None
        self.scale_slider = None
        self.opacity_slider = None
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

        walk = QCheckBox("走路时移动窗口")
        walk.setObjectName("checkBox")
        walk.setChecked(bool(getattr(self.pet_window, "_walk_window_move", True)))
        walk.toggled.connect(self._toggle_walk_move)
        layout.addWidget(walk)
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
        self.scale_slider.setValue(50)
        self.opacity_slider.setValue(100)


PAGE_STYLE = """
#pageTitle {
    color: #ffffff;
    font-size: 30px;
    font-weight: 800;
}
#pageDescription, #taskItem {
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
#checkBox {
    color: #dcefff;
    font-size: 14px;
}
QSlider::groove:horizontal {
    height: 8px;
    background: #07111f;
    border: 1px solid #284961;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    width: 18px;
    margin: -6px 0;
    background: #8df3c8;
    border-radius: 9px;
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
}
"""
