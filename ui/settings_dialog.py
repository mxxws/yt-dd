import os
import json
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QLineEdit, QComboBox, QCheckBox, QPushButton, QFileDialog,
    QSpinBox, QGroupBox, QFormLayout, QMessageBox, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QIcon

from core.config_manager import ConfigManager
from ui.theme_manager import get_theme_manager

class SettingsDialog(QDialog):
    """设置对话框，用于配置应用程序的各种设置"""
    
    # 设置更改信号
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.theme_manager = get_theme_manager()
        
        self.setWindowTitle("设置")
        self.setMinimumSize(500, 400)
        
        # 初始化UI
        self._init_ui()
        
        # 加载当前设置
        self._load_settings()
    
    def _init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 创建各个选项卡页面
        self.general_tab = self._create_general_tab()
        self.download_tab = self._create_download_tab()
        self.appearance_tab = self._create_appearance_tab()
        self.network_tab = self._create_network_tab()
        
        # 添加选项卡
        self.tab_widget.addTab(self.general_tab, "常规")
        self.tab_widget.addTab(self.download_tab, "下载")
        self.tab_widget.addTab(self.appearance_tab, "外观")
        self.tab_widget.addTab(self.network_tab, "网络")
        
        # 添加到主布局
        main_layout.addWidget(self.tab_widget)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 创建按钮
        self.reset_button = QPushButton("重置")
        self.cancel_button = QPushButton("取消")
        self.save_button = QPushButton("保存")
        
        # 设置默认按钮
        self.save_button.setDefault(True)
        
        # 添加按钮到布局
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        # 添加按钮布局到主布局
        main_layout.addLayout(button_layout)
        
        # 连接信号
        self.reset_button.clicked.connect(self._reset_settings)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self._save_settings)
    
    def _create_general_tab(self) -> QWidget:
        """创建常规选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 创建表单布局
        form_layout = QFormLayout()
        
        # 下载目录
        download_layout = QHBoxLayout()
        self.download_path_edit = QLineEdit()
        self.browse_button = QPushButton("浏览...")
        download_layout.addWidget(self.download_path_edit)
        download_layout.addWidget(self.browse_button)
        form_layout.addRow("下载目录:", download_layout)
        
        # 自动检查更新
        self.auto_update_check = QCheckBox("启动时检查更新")
        form_layout.addRow("", self.auto_update_check)
        
        # 自动打开下载文件夹
        self.auto_open_folder_check = QCheckBox("下载完成后打开文件夹")
        form_layout.addRow("", self.auto_open_folder_check)
        
        # 添加表单布局到主布局
        layout.addLayout(form_layout)
        
        # 连接信号
        self.browse_button.clicked.connect(self._browse_download_path)
        
        # 添加伸缩项
        layout.addStretch()
        
        return tab
    
    def _create_download_tab(self) -> QWidget:
        """创建下载选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 默认格式组
        format_group = QGroupBox("默认格式")
        format_layout = QFormLayout(format_group)
        
        # 默认视频质量
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.addItems(["最佳", "1080p", "720p", "480p", "360p"])
        format_layout.addRow("默认视频质量:", self.video_quality_combo)
        
        # 默认音频质量
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItems(["最佳", "高", "中", "低"])
        format_layout.addRow("默认音频质量:", self.audio_quality_combo)
        
        # 默认字幕语言
        self.subtitle_lang_combo = QComboBox()
        self.subtitle_lang_combo.addItems(["中文", "英文", "自动", "无"])
        format_layout.addRow("默认字幕语言:", self.subtitle_lang_combo)
        
        # 添加格式组到主布局
        layout.addWidget(format_group)
        
        # 下载选项组
        options_group = QGroupBox("下载选项")
        options_layout = QFormLayout(options_group)
        
        # 最大并发下载数
        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 5)
        self.max_concurrent_spin.setValue(2)
        options_layout.addRow("最大并发下载数:", self.max_concurrent_spin)
        
        # 下载重试次数
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(3)
        options_layout.addRow("下载重试次数:", self.retry_spin)
        
        # 使用aria2c
        self.use_aria2c_check = QCheckBox("使用aria2c加速下载")
        options_layout.addRow("", self.use_aria2c_check)
        
        # 添加下载选项组到主布局
        layout.addWidget(options_group)
        
        # 添加伸缩项
        layout.addStretch()
        
        return tab
    
    def _create_appearance_tab(self) -> QWidget:
        """创建外观选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 主题组
        theme_group = QGroupBox("主题")
        theme_layout = QFormLayout(theme_group)
        
        # 主题选择
        self.theme_combo = QComboBox()
        themes = self.theme_manager.get_available_themes()
        for theme_id, theme_name in themes.items():
            self.theme_combo.addItem(theme_name, theme_id)
        theme_layout.addRow("主题:", self.theme_combo)
        
        # 添加主题组到主布局
        layout.addWidget(theme_group)
        
        # 字体组
        font_group = QGroupBox("字体")
        font_layout = QFormLayout(font_group)
        
        # 字体大小
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(8, 16)
        self.font_size_slider.setValue(10)
        self.font_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.font_size_slider.setTickInterval(1)
        
        self.font_size_label = QLabel("10")
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(self.font_size_slider)
        font_size_layout.addWidget(self.font_size_label)
        
        font_layout.addRow("字体大小:", font_size_layout)
        
        # 添加字体组到主布局
        layout.addWidget(font_group)
        
        # 连接信号
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.font_size_slider.valueChanged.connect(self._on_font_size_changed)
        
        # 添加伸缩项
        layout.addStretch()
        
        return tab
    
    def _create_network_tab(self) -> QWidget:
        """创建网络选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 代理组
        proxy_group = QGroupBox("代理设置")
        proxy_layout = QFormLayout(proxy_group)
        
        # 启用代理
        self.proxy_enabled_check = QCheckBox("启用代理")
        proxy_layout.addRow("", self.proxy_enabled_check)
        
        # 代理类型
        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["HTTP", "SOCKS5"])
        proxy_layout.addRow("代理类型:", self.proxy_type_combo)
        
        # 代理主机
        self.proxy_host_edit = QLineEdit()
        proxy_layout.addRow("代理主机:", self.proxy_host_edit)
        
        # 代理端口
        self.proxy_port_edit = QLineEdit()
        self.proxy_port_edit.setInputMask("00000")
        proxy_layout.addRow("代理端口:", self.proxy_port_edit)
        
        # 添加代理组到主布局
        layout.addWidget(proxy_group)
        
        # 连接信号
        self.proxy_enabled_check.toggled.connect(self._on_proxy_enabled_changed)
        
        # 初始禁用代理设置
        self._on_proxy_enabled_changed(False)
        
        # 添加伸缩项
        layout.addStretch()
        
        return tab
    
    def _browse_download_path(self):
        """浏览下载目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择下载目录")
        if directory:
            self.download_path_edit.setText(directory)
    
    def _on_theme_changed(self, index):
        """主题更改处理"""
        theme_id = self.theme_combo.currentData()
        # 这里可以添加主题预览功能
    
    def _on_font_size_changed(self, value):
        """字体大小更改处理"""
        self.font_size_label.setText(str(value))
    
    def _on_proxy_enabled_changed(self, enabled):
        """代理启用状态更改处理"""
        self.proxy_type_combo.setEnabled(enabled)
        self.proxy_host_edit.setEnabled(enabled)
        self.proxy_port_edit.setEnabled(enabled)
    
    def _load_settings(self):
        """加载当前设置"""
        # 常规设置
        self.download_path_edit.setText(self.config_manager.get("download_path", ""))
        self.auto_update_check.setChecked(self.config_manager.get("auto_check_update", True))
        self.auto_open_folder_check.setChecked(self.config_manager.get("auto_open_folder", True))
        
        # 下载设置
        video_quality = self.config_manager.get("default_video_quality", "1080p")
        index = self.video_quality_combo.findText(video_quality)
        if index >= 0:
            self.video_quality_combo.setCurrentIndex(index)
        
        audio_quality = self.config_manager.get("default_audio_quality", "best")
        index = self.audio_quality_combo.findText(audio_quality)
        if index >= 0:
            self.audio_quality_combo.setCurrentIndex(index)
        
        subtitle_lang = self.config_manager.get("default_subtitle_lang", "zh")
        if subtitle_lang == "zh":
            self.subtitle_lang_combo.setCurrentText("中文")
        elif subtitle_lang == "en":
            self.subtitle_lang_combo.setCurrentText("英文")
        elif subtitle_lang == "auto":
            self.subtitle_lang_combo.setCurrentText("自动")
        else:
            self.subtitle_lang_combo.setCurrentText("无")
        
        self.max_concurrent_spin.setValue(self.config_manager.get("max_concurrent_downloads", 2))
        self.retry_spin.setValue(self.config_manager.get("retry_count", 3))
        self.use_aria2c_check.setChecked(self.config_manager.get("use_aria2c", True))
        
        # 外观设置
        theme = self.config_manager.get("theme", "light")
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == theme:
                self.theme_combo.setCurrentIndex(i)
                break
        
        self.font_size_slider.setValue(self.config_manager.get("font_size", 10))
        
        # 网络设置
        proxy = self.config_manager.get("proxy", {})
        self.proxy_enabled_check.setChecked(proxy.get("enabled", False))
        self.proxy_type_combo.setCurrentText(proxy.get("type", "HTTP").upper())
        self.proxy_host_edit.setText(proxy.get("host", ""))
        self.proxy_port_edit.setText(str(proxy.get("port", "")))
        
        # 更新UI状态
        self._on_proxy_enabled_changed(self.proxy_enabled_check.isChecked())
    
    def _save_settings(self):
        """保存设置"""
        # 收集设置
        settings = {}
        
        # 常规设置
        settings["download_path"] = self.download_path_edit.text()
        settings["auto_check_update"] = self.auto_update_check.isChecked()
        settings["auto_open_folder"] = self.auto_open_folder_check.isChecked()
        
        # 下载设置
        settings["default_video_quality"] = self.video_quality_combo.currentText()
        settings["default_audio_quality"] = self.audio_quality_combo.currentText().lower()
        
        subtitle_text = self.subtitle_lang_combo.currentText()
        if subtitle_text == "中文":
            settings["default_subtitle_lang"] = "zh"
        elif subtitle_text == "英文":
            settings["default_subtitle_lang"] = "en"
        elif subtitle_text == "自动":
            settings["default_subtitle_lang"] = "auto"
        else:
            settings["default_subtitle_lang"] = "none"
        
        settings["max_concurrent_downloads"] = self.max_concurrent_spin.value()
        settings["retry_count"] = self.retry_spin.value()
        settings["use_aria2c"] = self.use_aria2c_check.isChecked()
        
        # 外观设置
        settings["theme"] = self.theme_combo.currentData()
        settings["font_size"] = self.font_size_slider.value()
        
        # 网络设置
        settings["proxy"] = {
            "enabled": self.proxy_enabled_check.isChecked(),
            "type": self.proxy_type_combo.currentText().lower(),
            "host": self.proxy_host_edit.text(),
            "port": self.proxy_port_edit.text()
        }
        
        # 保存设置
        self.config_manager.update(settings)
        
        # 应用主题
        self.theme_manager.apply_theme(settings["theme"])
        
        # 发送设置更改信号
        self.settings_changed.emit(settings)
        
        # 关闭对话框
        self.accept()
    
    def _reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self, "确认重置", "确定要重置所有设置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 重置为默认配置
            default_config_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "config", "default_config.json"
            )
            
            if os.path.exists(default_config_file):
                with open(default_config_file, 'r', encoding='utf-8') as f:
                    default_config = json.load(f)
                    self.config_manager.update(default_config)
            
            # 重新加载设置
            self._load_settings()