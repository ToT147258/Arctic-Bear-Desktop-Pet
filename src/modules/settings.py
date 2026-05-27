import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QKeySequenceEdit,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.llm_client import LLMClient, LLM_PROVIDERS, normalize_llm_config


DEFAULT_HOTKEY = "Ctrl+Alt+B"


class SettingsPage(QWidget):
    llm_test_ready = Signal(bool, str)

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
        self.llm_enabled = None
        self.llm_provider = None
        self.llm_model = None
        self.llm_api_url = None
        self.llm_api_key = None
        self.llm_auto_talk = None
        self.llm_status = None
        self.llm_test_button = None
        self._updating_llm_controls = False
        self._build_ui()
        self.store.changed.connect(self.refresh)
        self.llm_test_ready.connect(self._on_llm_test_result)
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
        layout.addWidget(self._llm_card())
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

    def _llm_card(self):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        title = QLabel("AI 大模型")
        title.setObjectName("cardTitle")
        desc = QLabel("支持 DeepSeek、ChatGPT/OpenAI、智谱 GLM、通义千问、Kimi 和自定义 OpenAI 兼容接口。配置后聊天页会优先使用联网大模型。")
        desc.setWordWrap(True)
        desc.setObjectName("taskItem")

        self.llm_enabled = QCheckBox("启用联网大模型聊天")
        self.llm_enabled.setObjectName("checkBox")
        self.llm_auto_talk = QCheckBox("允许桌宠主动使用大模型生成轻量陪伴语")
        self.llm_auto_talk.setObjectName("checkBox")

        form = QGridLayout()
        form.setSpacing(8)
        self.llm_provider = QComboBox()
        self.llm_provider.setObjectName("settingCombo")
        for key, provider in LLM_PROVIDERS.items():
            self.llm_provider.addItem(provider["name"], key)
        self.llm_provider.currentIndexChanged.connect(self._llm_provider_changed)

        self.llm_model = QComboBox()
        self.llm_model.setObjectName("settingCombo")
        self.llm_model.setEditable(True)

        self.llm_api_url = QLineEdit()
        self.llm_api_url.setObjectName("settingInput")
        self.llm_api_url.setPlaceholderText("https://api.deepseek.com")
        self.llm_api_key = QLineEdit()
        self.llm_api_key.setObjectName("settingInput")
        self.llm_api_key.setEchoMode(QLineEdit.Password)
        self.llm_api_key.setPlaceholderText("输入 API Key，本地保存到 data/save.json")

        form.addWidget(QLabel("服务商"), 0, 0)
        form.addWidget(self.llm_provider, 0, 1)
        form.addWidget(QLabel("模型"), 0, 2)
        form.addWidget(self.llm_model, 0, 3)
        form.addWidget(QLabel("API 地址"), 1, 0)
        form.addWidget(self.llm_api_url, 1, 1, 1, 3)
        form.addWidget(QLabel("API Key"), 2, 0)
        form.addWidget(self.llm_api_key, 2, 1, 1, 3)

        self.llm_status = QLabel()
        self.llm_status.setWordWrap(True)
        self.llm_status.setObjectName("taskItem")
        actions = QHBoxLayout()
        save = QPushButton("保存 AI 配置")
        save.setCursor(Qt.PointingHandCursor)
        save.setObjectName("moduleAction")
        save.clicked.connect(self._save_llm_config)
        self.llm_test_button = QPushButton("测试连接")
        self.llm_test_button.setCursor(Qt.PointingHandCursor)
        self.llm_test_button.setObjectName("moduleAction")
        self.llm_test_button.clicked.connect(self._test_llm_connection)
        actions.addWidget(save)
        actions.addWidget(self.llm_test_button)

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addWidget(self.llm_enabled)
        layout.addWidget(self.llm_auto_talk)
        layout.addLayout(form)
        layout.addWidget(self.llm_status)
        layout.addLayout(actions)
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
        self._refresh_llm_controls()

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

    def _refresh_llm_controls(self):
        if not self.llm_provider:
            return
        editing = any(
            widget and widget.hasFocus()
            for widget in (self.llm_provider, self.llm_model, self.llm_api_url, self.llm_api_key)
        )
        if editing:
            return
        cfg = normalize_llm_config(self.store.settings.get("llm", {}))
        self._updating_llm_controls = True
        self.llm_enabled.setChecked(bool(cfg.get("enabled")))
        self.llm_auto_talk.setChecked(bool(cfg.get("auto_talk")))
        index = self.llm_provider.findData(cfg["provider"])
        self.llm_provider.setCurrentIndex(max(0, index))
        self._load_llm_models(cfg["provider"], cfg.get("model", ""))
        self.llm_api_url.setText(cfg.get("api_url", ""))
        self.llm_api_key.setText(cfg.get("api_key", ""))
        provider_name = LLM_PROVIDERS.get(cfg["provider"], LLM_PROVIDERS["deepseek"])["name"]
        state = "已启用" if cfg.get("enabled") else "未启用"
        key_state = "已填写 Key" if cfg.get("api_key") else "未填写 Key"
        self.llm_status.setText(f"当前：{state} · {provider_name} · {cfg.get('model')} · {key_state}")
        self._updating_llm_controls = False

    def _load_llm_models(self, provider_key, current_model=""):
        self.llm_model.clear()
        models = LLM_PROVIDERS.get(provider_key, {}).get("models", [])
        self.llm_model.addItems(models)
        if current_model:
            if self.llm_model.findText(current_model) < 0:
                self.llm_model.addItem(current_model)
            self.llm_model.setCurrentText(current_model)
        elif models:
            self.llm_model.setCurrentText(models[0])

    def _llm_provider_changed(self, *_):
        if self._updating_llm_controls:
            return
        provider_key = self.llm_provider.currentData() or "deepseek"
        provider = LLM_PROVIDERS.get(provider_key, LLM_PROVIDERS["deepseek"])
        models = provider.get("models", [])
        self._load_llm_models(provider_key, models[0] if models else "")
        self.llm_api_url.setText(provider.get("default_url", ""))

    def _current_llm_config(self):
        return normalize_llm_config(
            {
                "enabled": self.llm_enabled.isChecked(),
                "provider": self.llm_provider.currentData() or "deepseek",
                "model": self.llm_model.currentText().strip(),
                "api_url": self.llm_api_url.text().strip(),
                "api_key": self.llm_api_key.text().strip(),
                "auto_talk": self.llm_auto_talk.isChecked(),
            }
        )

    def _save_llm_config(self):
        self.store.set_llm_config(self._current_llm_config())
        self.llm_status.setText("AI 大模型配置已保存。")

    def _test_llm_connection(self):
        self.store.set_llm_config(self._current_llm_config())
        if self.llm_test_button:
            self.llm_test_button.setEnabled(False)
            self.llm_test_button.setText("测试中...")
        threading.Thread(target=self._worker_test_llm, daemon=True).start()

    def _worker_test_llm(self):
        ok, message = LLMClient(self.store).quick_check()
        self.llm_test_ready.emit(ok, message)

    def _on_llm_test_result(self, ok, message):
        if self.llm_test_button:
            self.llm_test_button.setEnabled(True)
            self.llm_test_button.setText("测试连接")
        self.store.add_log("AI", message)
        self.llm_status.setText(message)

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
        self._refresh_llm_controls()


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
QComboBox#settingCombo, QLineEdit#settingInput {
    min-height: 38px;
    color: #284f66;
    background: #ffffff;
    border: 1px solid #b8e1ef;
    border-radius: 12px;
    padding: 6px 10px;
}
#moduleAction:disabled {
    color: #88a3b2;
    background: #e9f4f8;
    border-color: #d3e9f0;
}
QLabel {
    color: #31556b;
}
"""
