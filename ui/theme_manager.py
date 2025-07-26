import os
import json
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

class ThemeManager:
    """主题管理器，用于管理应用程序的主题和样式"""
    
    # 预定义主题 - 只保留现代白色主题
    THEMES = {
        "light": {
            "name": "浅色主题",
            "style": "Fusion",
            "colors": {
                "window": "#F8F9FE",
                "window_text": "#333333",
                "base": "#FFFFFF",
                "alternate_base": "#F7F7F7",
                "text": "#333333",
                "button": "#E0E0E0",
                "button_text": "#333333",
                "bright_text": "#FFFFFF",
                "highlight": "#4361EE",
                "highlight_text": "#FFFFFF",
                "link": "#4361EE",
                "dark": "#6C757D",
                "mid": "#E0E0E0",
                "mid_light": "#F0F0F0",
                "shadow": "#BDBDBD"
            }
        }
    }
    
    # 单例实例
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'ThemeManager':
        """获取ThemeManager单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化主题管理器"""
        self.app = QApplication.instance()
        self.current_theme = "light"  # 默认主题
        self.custom_styles = {}
        
        # 确保应用程序实例存在
        if not self.app:
            raise RuntimeError("ThemeManager必须在QApplication创建后初始化")
    
    def apply_theme(self, theme_name: str = None) -> bool:
        """应用默认白色主题
        
        Args:
            theme_name: 忽略此参数，始终使用白色主题
            
        Returns:
            bool: 应用成功返回True
        """
        # 忽略传入的主题名称，始终使用白色主题
        theme_name = "light"
        theme = self.THEMES[theme_name]
        self.current_theme = theme_name
        
        # 设置应用程序样式
        self.app.setStyle(theme["style"])
        
        # 创建调色板
        palette = QPalette()
        colors = theme["colors"]
        
        # 设置调色板颜色
        color_roles = {
            QPalette.ColorRole.Window: colors["window"],
            QPalette.ColorRole.WindowText: colors["window_text"],
            QPalette.ColorRole.Base: colors["base"],
            QPalette.ColorRole.AlternateBase: colors["alternate_base"],
            QPalette.ColorRole.Text: colors["text"],
            QPalette.ColorRole.Button: colors["button"],
            QPalette.ColorRole.ButtonText: colors["button_text"],
            QPalette.ColorRole.BrightText: colors["bright_text"],
            QPalette.ColorRole.Highlight: colors["highlight"],
            QPalette.ColorRole.HighlightedText: colors["highlight_text"],
            QPalette.ColorRole.Link: colors["link"],
            QPalette.ColorRole.Dark: colors["dark"],
            QPalette.ColorRole.Mid: colors["mid"],
            QPalette.ColorRole.Midlight: colors["mid_light"],
            QPalette.ColorRole.Shadow: colors["shadow"]
        }
        
        for role, color in color_roles.items():
            palette.setColor(role, QColor(color))
        
        # 应用调色板
        self.app.setPalette(palette)
        
        # 应用自定义样式表
        self.apply_custom_styles()
        
        return True
    
    def get_current_theme(self) -> str:
        """获取当前主题名称"""
        return self.current_theme
    
    def get_available_themes(self) -> Dict[str, str]:
        """获取所有可用主题
        
        Returns:
            Dict[str, str]: 主题ID到主题名称的映射
        """
        return {theme_id: theme["name"] for theme_id, theme in self.THEMES.items()}
    
    def set_custom_style(self, widget_type: str, style: str) -> None:
        """设置自定义样式
        
        Args:
            widget_type: 控件类型，如QPushButton、QLineEdit等
            style: 样式表字符串
        """
        self.custom_styles[widget_type] = style
        self.apply_custom_styles()
    
    def apply_custom_styles(self):
        """应用自定义样式"""
        style_sheet = """
            QToolTip {
                border: 1px solid #E0E0E0;
                background-color: #FFFFFF;
                color: #333333;
                padding: 8px;
                border-radius: 4px;
            }
        """
        
        QApplication.instance().setStyleSheet(style_sheet)
    
    def load_theme_from_file(self, file_path: str) -> bool:
        """从文件加载主题
        
        Args:
            file_path: 主题文件路径，JSON格式
            
        Returns:
            bool: 加载成功返回True，否则返回False
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            # 验证主题数据
            if not self._validate_theme_data(theme_data):
                return False
            
            # 添加到预定义主题
            theme_id = theme_data.get("id", f"custom_{len(self.THEMES)}")
            self.THEMES[theme_id] = theme_data
            
            return True
        except Exception as e:
            print(f"加载主题文件失败: {str(e)}")
            return False
    
    def _validate_theme_data(self, theme_data: Dict[str, Any]) -> bool:
        """验证主题数据格式是否正确
        
        Args:
            theme_data: 主题数据字典
            
        Returns:
            bool: 格式正确返回True，否则返回False
        """
        required_keys = ["name", "style", "colors"]
        for key in required_keys:
            if key not in theme_data:
                return False
        
        required_colors = [
            "window", "window_text", "base", "alternate_base", "text",
            "button", "button_text", "bright_text", "highlight",
            "highlight_text", "link", "dark", "mid", "mid_light", "shadow"
        ]
        
        for color in required_colors:
            if color not in theme_data["colors"]:
                return False
        
        return True

# 创建全局主题管理器实例
def get_theme_manager() -> ThemeManager:
    """获取全局主题管理器实例"""
    return ThemeManager.get_instance()