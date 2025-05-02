import sys
import os
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize
from ui.main_window import MainWindow


def main():
    """程序主入口，初始化应用程序并显示主窗口"""
    try:
        # 初始化应用程序对象
        app = QApplication(sys.argv)
        
        # 设置应用程序样式为Fusion
        app.setStyle('Fusion')
        
        # 加载多尺寸应用图标
        app_icon = QIcon()
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        
        # 图标尺寸映射字典
        icon_sizes = {
            "icon-32-32.ico": 32,
            "icon-48-48.ico": 48,
            "icon-256-256.ico": 256
        }
        
        # 添加各尺寸图标至应用
        for icon_file, size in icon_sizes.items():
            icon_path = os.path.join(assets_dir, icon_file)
            if os.path.exists(icon_path):
                app_icon.addFile(icon_path, size=QSize(size, size))
        
        # 增强图标设置 - 确保在Windows任务栏正确显示
        app.setWindowIcon(app_icon)
        
        # 创建并显示主窗口
        main_window = MainWindow()
        main_window.setWindowIcon(app_icon)  # 确保主窗口也设置了相同的图标
        main_window.show()
        
        # 运行应用程序事件循环
        sys.exit(app.exec())
        
    except Exception as e:
        # 捕获并显示启动阶段的异常
        error_message = f"程序启动时发生错误:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_message)
        
        # 当应用已初始化时，显示错误对话框
        if 'app' in locals():
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("程序错误")
            error_dialog.setText("程序启动时发生错误:")
            error_dialog.setDetailedText(error_message)
            error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            error_dialog.exec()
        sys.exit(1)


if __name__ == '__main__':
    main()