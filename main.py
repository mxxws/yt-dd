import sys
import os
import traceback

# 配置详细的导入诊断信息
ENABLE_DETAILED_DEBUG = True  # 设置为 True 以启用详细诊断
LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moviepy_import.log")

def log_debug(message):
    """打印调试信息并可选地写入日志文件"""
    if ENABLE_DETAILED_DEBUG:
        print(message)
        try:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except Exception:
            pass  # 忽略日志写入错误

# 清理现有日志文件
if ENABLE_DETAILED_DEBUG:
    try:
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"MoviePy 导入诊断日志 - {os.path.abspath(__file__)}\n")
            f.write("=" * 80 + "\n\n")
    except Exception:
        pass

log_debug("开始 MoviePy 导入处理...")

# 添加moviepy.editor导入兼容处理
try:
    # 尝试常规导入
    log_debug("尝试常规导入 moviepy.editor")
    import moviepy.editor
    log_debug("成功导入 moviepy.editor 模块")
except ImportError as e:
    log_debug(f"无法直接导入 moviepy.editor: {str(e)}，尝试替代方案...")
    try:
        # 记录 moviepy 基本信息
        try:
            import moviepy
            log_debug(f"moviepy 基本包可用: {moviepy.__file__}")
            if hasattr(moviepy, "__version__"):
                log_debug(f"moviepy 版本: {moviepy.__version__}")
            
            # 检查 moviepy 包结构
            has_video = hasattr(moviepy, "video")
            has_audio = hasattr(moviepy, "audio")
            log_debug(f"moviepy 包结构: video={has_video}, audio={has_audio}")
        except Exception as e_info:
            log_debug(f"获取 moviepy 信息错误: {str(e_info)}")
        
        # 在打包环境中，尝试从数据文件导入
        log_debug("尝试从数据文件导入 moviepy_editor.py")
        base_paths = [
            os.path.dirname(os.path.abspath(__file__)),  # 当前脚本目录
            os.path.abspath(os.path.curdir),  # 当前工作目录
            getattr(sys, '_MEIPASS', None)  # PyInstaller 临时目录
        ]
        
        # 移除 None 值
        base_paths = [p for p in base_paths if p is not None]
        
        # 尝试不同路径
        editor_found = False
        for base_path in base_paths:
            moviepy_editor_path = os.path.join(base_path, "moviepy_editor.py")
            log_debug(f"尝试路径: {moviepy_editor_path}")
            
            if os.path.exists(moviepy_editor_path):
                log_debug(f"找到 moviepy_editor.py: {moviepy_editor_path}")
                # 使用 importlib 动态导入
                import importlib.util
                spec = importlib.util.spec_from_file_location("moviepy.editor", moviepy_editor_path)
                moviepy_editor = importlib.util.module_from_spec(spec)
                sys.modules["moviepy.editor"] = moviepy_editor
                spec.loader.exec_module(moviepy_editor)
                log_debug("成功导入替代的 moviepy.editor 模块")
                editor_found = True
                
                # 验证基本类是否可用
                required_classes = ["VideoFileClip", "AudioFileClip"]
                missing_classes = []
                for class_name in required_classes:
                    if not hasattr(moviepy_editor, class_name):
                        missing_classes.append(class_name)
                
                if missing_classes:
                    log_debug(f"警告: 以下类在替代模块中不可用: {', '.join(missing_classes)}")
                    # 尝试直接添加缺失的类
                    try:
                        log_debug("尝试手动添加缺失的类...")
                        
                        # 尝试多种可能的导入路径
                        videofileclip_paths = [
                            'moviepy.video.io.VideoFileClip',
                            'moviepy.video.VideoFileClip'
                        ]
                        
                        audiofileclip_paths = [
                            'moviepy.audio.io.AudioFileClip',
                            'moviepy.audio.AudioFileClip'
                        ]
                        
                        for class_name in missing_classes:
                            if class_name == "VideoFileClip":
                                for path in videofileclip_paths:
                                    try:
                                        log_debug(f"尝试从 {path} 导入 VideoFileClip")
                                        module = __import__(path, fromlist=['VideoFileClip'])
                                        sys.modules["moviepy.editor"].VideoFileClip = module.VideoFileClip
                                        log_debug("已手动添加 VideoFileClip 到 moviepy.editor")
                                        break
                                    except ImportError as path_error:
                                        log_debug(f"路径 {path} 导入失败: {str(path_error)}")
                            
                            elif class_name == "AudioFileClip":
                                for path in audiofileclip_paths:
                                    try:
                                        log_debug(f"尝试从 {path} 导入 AudioFileClip")
                                        module = __import__(path, fromlist=['AudioFileClip'])
                                        sys.modules["moviepy.editor"].AudioFileClip = module.AudioFileClip
                                        log_debug("已手动添加 AudioFileClip 到 moviepy.editor")
                                        break
                                    except ImportError as path_error:
                                        log_debug(f"路径 {path} 导入失败: {str(path_error)}")
                    except Exception as e2:
                        log_debug(f"手动添加缺失类失败: {str(e2)}")
                        log_debug(traceback.format_exc())
                
                # 导入成功，退出循环
                break
            else:
                log_debug(f"路径不存在: {moviepy_editor_path}")
        
        # 如果所有路径都没找到
        if not editor_found:
            log_debug("未找到 moviepy_editor.py 文件，尝试创建最小化替代模块...")
            try:
                # 创建一个简单的替代模块
                log_debug("尝试直接导入核心组件...")
                
                # 尝试直接导入核心类
                from_imports = {
                    "VideoFileClip": [
                        "moviepy.video.io.VideoFileClip",
                        "moviepy.VideoFileClip"
                    ],
                    "AudioFileClip": [
                        "moviepy.audio.io.AudioFileClip",
                        "moviepy.AudioFileClip"
                    ]
                }
                
                # 记录导入的类
                imported_classes = {}
                
                # 尝试每个类的所有可能导入路径
                for class_name, import_paths in from_imports.items():
                    for path in import_paths:
                        try:
                            log_debug(f"尝试从 {path} 导入 {class_name}")
                            module_parts = path.split('.')
                            module_name = '.'.join(module_parts[:-1])
                            class_path = module_parts[-1]
                            
                            if module_name:
                                module = __import__(module_name, fromlist=[class_path])
                                imported_classes[class_name] = getattr(module, class_path)
                                log_debug(f"成功导入 {class_name}")
                                break
                            else:
                                log_debug(f"无效的导入路径: {path}")
                        except ImportError as e_import:
                            log_debug(f"导入路径 {path} 失败: {str(e_import)}")
                        except Exception as e_other:
                            log_debug(f"导入 {path} 时出现其他错误: {str(e_other)}")
                
                # 创建最小化的模块对象
                if imported_classes:
                    class MoviepyEditorModule:
                        pass
                    
                    # 将导入的类添加到模块中
                    moviepy_editor = MoviepyEditorModule()
                    for name, cls in imported_classes.items():
                        setattr(moviepy_editor, name, cls)
                    
                    # 注册模块
                    sys.modules["moviepy.editor"] = moviepy_editor
                    log_debug(f"已创建最小化的 moviepy.editor 替代模块，包含以下类: {', '.join(imported_classes.keys())}")
                else:
                    log_debug("未能导入任何核心类，无法创建最小化替代模块")
            except Exception as e3:
                log_debug(f"创建替代模块失败: {str(e3)}")
                log_debug(traceback.format_exc())
    except Exception as e:
        log_debug(f"替代导入 moviepy.editor 失败: {str(e)}")
        log_debug(traceback.format_exc())
        # 不抛出异常，让程序继续运行，可能某些功能不可用

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize
from ui.main_window import MainWindow


def main():
    """程序主入口，初始化应用程序并显示主窗口"""
    try:
        # 设置标准输出和标准错误为行缓冲模式，确保实时输出
        sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
        sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None
        
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