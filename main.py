import sys
import os
import traceback

# 配置详细的导入诊断信息
ENABLE_DETAILED_DEBUG = False  # 设置为 False 以禁用详细诊断
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

# 内置 moviepy.editor 兼容模块
def create_moviepy_editor_module():
    """创建 moviepy.editor 兼容模块
    
    该函数尝试创建一个兼容的 moviepy.editor 模块，通过导入必要的组件。
    为了减少导入警告，只保留了已知有效的导入路径，移除了可能导致警告的路径。
    """
    log_debug("创建内置的 moviepy.editor 兼容模块...")
    
    # 记录导入的模块
    imported_modules = {}

    def safe_import(module_name, fromlist=None, alias=None):
        try:
            if fromlist:
                module = __import__(module_name, fromlist=fromlist)
                for item in fromlist:
                    try:
                        attr = getattr(module, item, None)
                        if attr is not None:
                            # 使用原名或别名
                            target_name = alias.get(item, item) if alias else item
                            imported_modules[target_name] = attr
                            globals()[target_name] = attr
                        else:
                            log_debug(f"警告: {module_name} 中未找到 {item}")
                    except Exception as e:
                        log_debug(f"导入 {module_name}.{item} 时出错: {str(e)}")
                return module
            else:
                module = __import__(module_name)
                imported_modules[module_name] = module
                return module
        except ImportError as e:
            log_debug(f"警告: 无法导入 {module_name}: {str(e)}")
            return None
        except Exception as e:
            log_debug(f"导入 {module_name} 时出现未知错误: {str(e)}")
            return None

    # 创建一个模块对象
    class MoviepyEditorModule:
        pass
    
    moviepy_editor = MoviepyEditorModule()
    
    # 尝试导入基本组件
    try:
        log_debug("开始为 moviepy.editor 创建兼容层...")
        
        # 视频处理相关类
        video_modules = [
            ('moviepy.video.io.VideoFileClip', ['VideoFileClip']),
            ('moviepy.video.VideoClip', ['VideoClip', 'ImageClip', 'ColorClip', 'TextClip'])
        ]
        
        # 音频处理相关类
        audio_modules = [
            ('moviepy.audio.io.AudioFileClip', ['AudioFileClip']),
            ('moviepy.audio.AudioClip', ['AudioClip', 'CompositeAudioClip'])
        ]
        
        # 合成相关类
        compositing_modules = [
            ('moviepy.video.compositing.CompositeVideoClip', ['CompositeVideoClip'])
            # 移除导致警告的路径
            # ('moviepy.video.CompositeVideoClip', ['CompositeVideoClip']),
            # ('moviepy.compositing.CompositeVideoClip', ['CompositeVideoClip'])
        ]
        
        # 连接相关类
        concatenate_modules = [
            ('moviepy.video.compositing.concatenate', ['concatenate_videoclips'])
            # 移除导致警告的路径
            # ('moviepy.video.concatenate', ['concatenate_videoclips']),
            # ('moviepy.compositing.concatenate', ['concatenate_videoclips']),
            # ('moviepy.concatenate', ['concatenate_videoclips'])
        ]
        
        # ffmpeg工具
        ffmpeg_modules = [
            ('moviepy.video.io.ffmpeg_tools', ['ffmpeg_extract_subclip', 'ffmpeg_merge_video_audio'])
            # 移除导致警告的路径
            # ('moviepy.tools.ffmpeg_tools', ['ffmpeg_extract_subclip', 'ffmpeg_merge_video_audio']),
            # ('moviepy.ffmpeg_tools', ['ffmpeg_extract_subclip', 'ffmpeg_merge_video_audio'])
        ]
        
        # 尝试导入所有模块
        all_modules = video_modules + audio_modules + compositing_modules + concatenate_modules + ffmpeg_modules
        
        for module_path, items in all_modules:
            try:
                module = safe_import(module_path, items)
                if module:
                    for item in items:
                        if item in imported_modules:
                            setattr(moviepy_editor, item, imported_modules[item])
            except Exception as e:
                log_debug(f"导入 {module_path} 时出错: {str(e)}")
        
        # 检查导入的组件
        imported_items = [name for name in imported_modules.keys() if isinstance(name, str)]
        log_debug(f"已成功导入的组件: {', '.join(imported_items)}")
        
        # 将导入的组件添加到模块中
        for name, item in imported_modules.items():
            if isinstance(name, str):
                setattr(moviepy_editor, name, item)
        
        # 注册模块
        sys.modules["moviepy.editor"] = moviepy_editor
        return moviepy_editor
        
    except Exception as e:
        log_debug(f"创建 moviepy.editor 兼容模块失败: {str(e)}")
        log_debug(traceback.format_exc())
        return None

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
        
        # 创建内置的 moviepy.editor 兼容模块
        moviepy_editor = create_moviepy_editor_module()
        if moviepy_editor:
            log_debug("成功创建内置的 moviepy.editor 兼容模块")
        else:
            log_debug("创建内置的 moviepy.editor 兼容模块失败，尝试其他方法")
            
            # 尝试直接导入核心类
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


def check_dependencies(gui_mode=False):
    """检查依赖包版本并询问用户是否更新
    
    Args:
        gui_mode: 是否在GUI模式下运行，如果是则使用对话框交互
    """
    try:
        from core.dependency_checker import DependencyChecker
        import sys
        
        # 创建依赖检查器
        checker = DependencyChecker()
        
        # 核心包列表
        core_packages = ['PyQt6', 'yt-dlp', 'moviepy']
        
        if gui_mode:
            # GUI模式下使用对话框
            from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QRadioButton, QPushButton, QLabel, QButtonGroup
            
            # 创建自定义对话框
            class DependencyDialog(QDialog):
                def __init__(self, parent=None):
                    super().__init__(parent)
                    self.setWindowTitle("依赖包检查")
                    self.resize(400, 200)
                    self.choice = "3"  # 默认选择
                    
                    layout = QVBoxLayout()
                    
                    # 添加说明标签
                    label = QLabel("是否更新依赖包？这可能需要一些时间。")
                    layout.addWidget(label)
                    
                    # 创建单选按钮组
                    self.btn_group = QButtonGroup(self)
                    
                    # 添加选项
                    rb1 = QRadioButton("更新所有依赖包")
                    rb2 = QRadioButton("仅检查核心依赖包")
                    rb3 = QRadioButton("跳过所有依赖检查，直接启动程序")
                    rb3.setChecked(True)  # 默认选中
                    
                    self.btn_group.addButton(rb1, 1)
                    self.btn_group.addButton(rb2, 2)
                    self.btn_group.addButton(rb3, 3)
                    
                    layout.addWidget(rb1)
                    layout.addWidget(rb2)
                    layout.addWidget(rb3)
                    
                    # 添加确认按钮
                    btn_ok = QPushButton("确定")
                    btn_ok.clicked.connect(self.accept)
                    layout.addWidget(btn_ok)
                    
                    self.setLayout(layout)
                
                def get_choice(self):
                    return str(self.btn_group.checkedId())
            
            # 显示对话框
            dialog = DependencyDialog()
            if dialog.exec():
                choice = dialog.get_choice()
            else:
                choice = "3"  # 如果用户关闭对话框，默认跳过
            
            if choice == "1":
                # 创建进度对话框
                progress_msg = QMessageBox()
                progress_msg.setWindowTitle("依赖包更新")
                progress_msg.setText("正在更新所有依赖包，请稍候...\n\n这可能需要几分钟时间，请耐心等待。")
                progress_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
                progress_msg.show()
                
                # 更新所有依赖包
                update_result = checker.update_all_packages()
                
                # 关闭进度对话框
                progress_msg.close()
                
                # 显示完成消息
                QMessageBox.information(None, "依赖包更新", "所有依赖包更新完成。")
                
            elif choice == "2":
                # 创建子对话框询问是否更新核心依赖包
                sub_dialog = QMessageBox()
                sub_dialog.setWindowTitle("核心依赖包检查")
                sub_dialog.setText("是否更新核心依赖包？")
                update_btn = sub_dialog.addButton("更新", QMessageBox.ButtonRole.YesRole)
                check_btn = sub_dialog.addButton("仅检查", QMessageBox.ButtonRole.NoRole)
                sub_dialog.setDefaultButton(check_btn)
                
                sub_dialog.exec()
                
                if sub_dialog.clickedButton() == update_btn:
                    # 创建进度对话框
                    progress_msg = QMessageBox()
                    progress_msg.setWindowTitle("核心依赖包更新")
                    progress_msg.setText("正在更新核心依赖包，请稍候...")
                    progress_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
                    progress_msg.show()
                    
                    # 更新核心依赖包
                    checker.check_and_update_packages(core_packages)
                    
                    # 关闭进度对话框
                    progress_msg.close()
                    
                    # 显示完成消息
                    QMessageBox.information(None, "核心依赖包更新", "核心依赖包更新完成。")
                else:
                    # 仅检查核心依赖包
                    progress_msg = QMessageBox()
                    progress_msg.setWindowTitle("核心依赖包检查")
                    progress_msg.setText("正在检查核心依赖包，请稍候...")
                    progress_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
                    progress_msg.show()
                    
                    # 检查核心依赖包
                    result = checker.check_packages_only(core_packages)
                    
                    # 关闭进度对话框
                    progress_msg.close()
                    
                    # 构建结果消息
                    result_msg = "核心依赖包检查结果:\n\n"
                    for pkg, info in result.items():
                        if info.get("installed", False):
                            result_msg += f"✓ {pkg}: 已安装 (版本: {info.get('current_version', '未知')})\n"
                        else:
                            result_msg += f"✗ {pkg}: 未安装\n"
                    
                    # 显示结果消息
                    QMessageBox.information(None, "核心依赖包检查", result_msg)
            else:
                print("跳过依赖包检查，直接启动程序...")
        else:
            # 命令行模式下使用控制台交互
            print("\n是否更新所有已安装的依赖包？这可能需要一些时间。")
            print("1. 是，更新所有依赖包")
            print("2. 否，仅检查核心依赖包")
            print("3. 跳过所有依赖检查，直接启动程序")
            
            choice = input("请输入选项 (1/2/3，默认3): ").strip() or "3"
            
            if choice == "1":
                print("\n正在更新所有依赖包，请稍候...")
                update_result = checker.update_all_packages()
                print("\n依赖包更新完成。")
                
            elif choice == "2":
                # 只检查核心包是否已安装
                print("\n检查核心包是否已安装...")
                
                # 询问用户是否更新核心依赖包
                print("是否更新核心依赖包？")
                print("1. 是，更新核心依赖包")
                print("2. 否，仅检查是否已安装")
                
                sub_choice = input("请输入选项 (1/2，默认2): ").strip() or "2"
                
                if sub_choice == "1":
                    print("\n正在更新核心依赖包，请稍候...")
                    checker.check_and_update_packages(core_packages)
                    print("\n核心依赖包更新完成。")
                else:
                    print("\n跳过核心依赖包更新，仅检查是否已安装...")
                    checker.check_packages_only(core_packages)
            else:
                print("\n跳过依赖包检查，直接启动程序...")
        
    except Exception as e:
        if ENABLE_DETAILED_DEBUG:
            print(f"依赖检查过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()
        # 继续启动程序，不因依赖检查失败而中断

def main():
    """程序主入口，初始化应用程序并显示主窗口"""
    try:
        # 设置标准输出和标准错误为行缓冲模式，确保实时输出
        sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
        sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None
        
        # 初始化应用程序对象
        app = QApplication(sys.argv)
        
        # 检查并更新依赖包版本，使用GUI模式
        check_dependencies(gui_mode=True)
        
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