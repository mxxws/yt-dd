import os
import re
import traceback
import uuid
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QPushButton, QLabel,
    QProgressBar, QFileDialog, QMessageBox, QTextEdit,
    QApplication, QTabWidget, QSplitter, QToolBar, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QElapsedTimer, QTimer, QPropertyAnimation, QSize
from PyQt6.QtGui import QFont, QIcon, QAction
from core.downloader import VideoDownloader
from core.download_manager import DownloadManager, DownloadTask, TaskStatus
from ui.download_task_widget import DownloadTaskWidget
from ui.theme_manager import get_theme_manager

class DownloadThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, downloader, url, video_fmt, audio_fmt, subtitle_lang=None):
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.video_fmt = video_fmt
        self.audio_fmt = audio_fmt
        self.subtitle_lang = subtitle_lang
        self.is_canceled = False

    def run(self):
        try:
            success = self.downloader.download(self.url, self.video_fmt, self.audio_fmt, self.subtitle_lang)
            if self.is_canceled:
                self.error.emit("下载已取消")
            elif success:
                self.finished.emit("下载完成")
            else:
                self.error.emit("下载失败")
        except Exception as e:
            error_msg = f"下载线程错误: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)
            
    def cancel(self):
        """取消下载"""
        self.is_canceled = True
        # 通知下载器进程停止下载
        if hasattr(self.downloader, 'cancel_download'):
            self.downloader.cancel_download()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 初始化下载管理器
        self.download_manager = DownloadManager()
        
        # 初始化单个下载器（用于分析视频信息）
        self.downloader = VideoDownloader()
        
        # 初始化主题管理器
        self.theme_manager = get_theme_manager()
        
        # 互斥锁和定时器
        self.mutex = QMutex()
        self.timer = QElapsedTimer()
        self.analysis_timer = QTimer()
        self.analysis_timer.timeout.connect(self._check_analysis_status)
        
        # 添加用于延迟分析的定时器
        self.url_input_timer = QTimer()
        self.url_input_timer.setSingleShot(True)  # 设置为单次触发
        self.url_input_timer.timeout.connect(self._delayed_analysis)
        
        # 进度相关
        self.current_progress = 0
        
        # 当前分析的视频信息
        self.current_video_formats = []
        self.current_audio_formats = []
        self.current_subtitle_langs = []
        
        self._init_ui()
        self._create_toolbar()
        self._connect_signals()
        self._set_style()
        



        # 应用默认主题
        self.theme_manager.apply_theme()  # 已修改为只使用默认主题

    def _init_ui(self):
        self.setWindowTitle("yt-dd - YouTube视频下载器")
        self.setMinimumSize(900, 700)
        
        # 设置窗口图标（添加多个尺寸）
        window_icon = QIcon()
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        
        # 添加不同尺寸的图标
        icon_sizes = {
            "icon-32-32.ico": 32,
            "icon-48-48.ico": 48,
            "icon-256-256.ico": 256
        }
        
        for icon_file, size in icon_sizes.items():
            icon_path = os.path.join(assets_dir, icon_file)
            if os.path.exists(icon_path):
                window_icon.addFile(icon_path, size=QSize(size, size))
        
        # 强化图标设置 - 确保任务栏图标正确显示
        self.setWindowIcon(window_icon)
        
        # 获取全局应用实例并设置应用图标（影响任务栏）
        app = QApplication.instance()
        if app:
            app.setWindowIcon(window_icon)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        
        # 创建单任务下载界面
        self._init_single_task_ui()
        
        # 添加单任务下载界面到主布局
        main_layout.addWidget(self.single_task_tab)
        
    def _init_single_task_ui(self):
        """初始化单任务下载界面"""
        self.single_task_tab = QWidget()
        layout = QVBoxLayout(self.single_task_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # URL输入区域
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入YouTube视频链接")
        self.parse_button = QPushButton("粘贴并解析")
        self.parse_button.setObjectName("parse_button")
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.parse_button)
        layout.addLayout(url_layout)
        
        # 格式选择区域
        format_layout = QHBoxLayout()
        self.resolution_combo = QComboBox()
        self.resolution_combo.setPlaceholderText("选择视频分辨率")
        self.audio_combo = QComboBox()
        self.audio_combo.setPlaceholderText("选择音频质量")
        self.subtitle_combo = QComboBox()
        self.subtitle_combo.setPlaceholderText("选择字幕语言")
        self.subtitle_combo.setEnabled(True)  # 启用字幕选择
        format_layout.addWidget(QLabel("分辨率:"))
        format_layout.addWidget(self.resolution_combo)
        format_layout.addWidget(QLabel("音频:"))
        format_layout.addWidget(self.audio_combo)
        format_layout.addWidget(QLabel("字幕:"))
        format_layout.addWidget(self.subtitle_combo)
        layout.addLayout(format_layout)
        
        # 保存位置区域
        save_layout = QHBoxLayout()
        self.save_path_input = QLineEdit()
        self.save_path_input.setReadOnly(True)
        self.save_path_input.setText(self.downloader.save_dir)
        self.browse_button = QPushButton("浏览")
        self.browse_button.setObjectName("browse_button")
        save_layout.addWidget(QLabel("保存位置:"))
        save_layout.addWidget(self.save_path_input)
        save_layout.addWidget(self.browse_button)
        layout.addLayout(save_layout)
        
        # 进度显示区域
        progress_layout = QVBoxLayout()
        self.analysis_label = QLabel("就绪")
        self.analysis_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar = QProgressBar()
        
        # 进度条设置优化 - 使进度条更加平滑和实时
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        
        self.speed_label = QLabel("速度: 0 MB/s")
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.analysis_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.speed_label)
        progress_layout.addWidget(self.status_label)
        layout.addLayout(progress_layout)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # 控制按钮区域
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("开始下载")
        self.download_button.setObjectName("download_button")
        self.cancel_button = QPushButton("取消下载")
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
    # 多任务下载功能已移除

    def _set_style(self):
        # 设置整体样式
        self.setStyleSheet("""
            /* 全局样式 */
            QMainWindow {
                background-color: #FFFFFF;
            }
            
            QWidget {
                font-family: "Microsoft YaHei", "微软雅黑";
                color: #333333;
            }
            
            QPushButton {
                background-color: #4361EE;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background-color: #3A56D4;
            }
            
            QPushButton:pressed {
                background-color: #2E4BBB;
            }
            
            QPushButton:disabled {
                background-color: #B8C0E0;
            }
            
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 10px 14px;
                background: white;
                selection-background-color: #E7EAFC;
                font-size: 13px;
            }
            
            QLineEdit:focus {
                border: 1px solid #4361EE;
            }
            
            QComboBox {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 10px 14px;
                background: white;
                font-size: 13px;
                min-width: 150px;
            }
            
            QComboBox:focus {
                border: 1px solid #4361EE;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
            
            QProgressBar {
                border: none;
                background-color: #F0F2FA;
                height: 10px;
                border-radius: 5px;
                margin-top: 4px;
                margin-bottom: 4px;
            }
            
            QProgressBar::chunk {
                background-color: #4CC9F0;
                border-radius: 5px;
            }
            
            QLabel {
                color: #333333;
                font-size: 13px;
                font-weight: 400;
            }
            
            QTextEdit {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 10px;
                background: white;
                font-size: 13px;
                line-height: 1.5;
            }
            
            QTextEdit:focus {
                border: 1px solid #4361EE;
            }
            
            #status_label {
                color: #4361EE;
                font-weight: 600;
                font-size: 14px;
            }
            
            #speed_label {
                color: #4CC9F0;
                font-size: 13px;
                font-weight: 500;
            }
            
            #analysis_label {
                color: #555555;
                font-size: 13px;
            }
            
            /* 多任务下载界面样式已移除 */
            
            /* 多任务按钮样式已移除 */
            
            /* 单任务下载界面按钮样式 */
            #download_button {
                background-color: #06D6A0;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            
            #download_button:hover {
                background-color: #05C190;
            }
            
            #download_button:pressed {
                background-color: #04AC80;
            }
            
            #cancel_button {
                background-color: #EF476F;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            
            #cancel_button:hover {
                background-color: #E43065;
            }
            
            #cancel_button:pressed {
                background-color: #D4205B;
            }
            
            #browse_button, #multi_parse_button, #parse_button {
                background-color: #4361EE;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            
            #browse_button:hover, #multi_parse_button:hover, #parse_button:hover {
                background-color: #3A56D4;
            }
            
            #browse_button:pressed, #multi_parse_button:pressed, #parse_button:pressed {
                background-color: #2A46C4;
            }
            
            /* 多任务按钮样式选择器已移除 */
        """)

        # 设置布局间距
        main_widget = self.centralWidget()
        layout = main_widget.layout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 设置字体
        self.url_input.setFont(QFont("Microsoft YaHei", 13))
        self.status_label.setObjectName("status_label")
        self.speed_label.setObjectName("speed_label")
        self.analysis_label.setObjectName("analysis_label")
        
        # 多任务下载界面按钮对象名称设置已移除

        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        
        # 设置窗口动画
        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.start()

    def _create_toolbar(self):
        """创建工具栏"""
        # 创建工具栏
        self.toolbar = QToolBar("主工具栏")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # 工具栏已简化，移除了主题切换功能
        
    # 主题切换功能已移除
    
    def _connect_signals(self):
        # 单任务下载界面信号连接
        self.url_input.textChanged.connect(self._on_url_changed)
        self.browse_button.clicked.connect(self.browse_save_path)
        self.download_button.clicked.connect(self._start_download)
        self.cancel_button.clicked.connect(self._cancel_download)
        
        # 确保进度更新信号正确连接
        self.downloader.signals.progress_updated.connect(self._update_progress)
        self.downloader.signals.info_loaded.connect(self._update_formats)
        self.downloader.signals.error_occurred.connect(self._on_error)

    def _on_url_changed(self):
        """处理单任务URL输入变化"""
        # 重置并启动延时器
        self.url_input_timer.stop()
        self.url_input_timer.start(800)  # 800ms后触发分析
        
        # 更新UI状态
        self.analysis_label.setText("准备分析...")
        self.resolution_combo.clear()
        self.audio_combo.clear()
        self.subtitle_combo.clear()
        
    # 多任务URL输入变化处理函数已移除

    def _delayed_analysis(self):
        """延迟执行单任务分析"""
        url = self.url_input.text().strip()
        if re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/', url):
            self.analysis_label.setText("正在分析视频信息...")
            self.analysis_timer.start(100)
            self._load_media_info(url)
        else:
            self.analysis_label.setText("请输入有效的YouTube链接")
            
    # 多任务URL解析函数已移除

    def _validate_url(self):
        """URL验证已被_on_url_changed替代，保留此方法为空以兼容可能的调用"""
        pass

    def _check_analysis_status(self):
        if not self.mutex.tryLock():
            return
        try:
            self.analysis_label.setText("正在分析视频信息...")
        finally:
            self.mutex.unlock()

    def _load_media_info(self, url):
        try:
            self.log_text.append(f"正在解析视频信息: {url}")
            
            # 保存当前解析的URL
            self.current_url = url
            
            # 获取视频信息
            self.downloader.get_media_info(url)
        except Exception as e:
            error_msg = f"解析视频信息失败: {str(e)}\n{traceback.format_exc()}"
            self.log_text.append(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
        finally:
            self.analysis_timer.stop()

    def _update_formats(self, video_formats, audio_formats, subtitle_langs):
        try:
            # 保存当前视频信息
            self.current_video_formats = video_formats
            self.current_audio_formats = audio_formats
            self.current_subtitle_langs = subtitle_langs
            
            # 更新UI
            self.resolution_combo.clear()
            self.audio_combo.clear()
            self.subtitle_combo.clear()
            
            # 视频格式排序
            for fmt in sorted(video_formats, 
                            key=lambda x: int(x['desc'].split('p')[0]), 
                            reverse=True):
                self.resolution_combo.addItem(fmt['desc'], fmt['id'])
            
            # 音频格式排序
            for fmt in sorted(audio_formats, 
                            key=lambda x: float(x['desc'].split('k')[0]), 
                            reverse=True):
                self.audio_combo.addItem(fmt['desc'], fmt['id'])
            
            # 添加字幕选项
            self.subtitle_combo.addItem("无字幕", None)
            for sub in subtitle_langs:
                self.subtitle_combo.addItem(sub['name'], sub['code'])
                
            self.analysis_label.setText("视频信息分析完成")
            self.log_text.append("视频信息分析完成")
                
        except Exception as e:
            error_msg = f"更新格式列表失败: {str(e)}\n{traceback.format_exc()}"
            self.log_text.append(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def browse_save_path(self):
        try:
            directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
            if directory:
                self.save_path_input.setText(directory)
                self.downloader.save_dir = directory
                self.log_text.append(f"保存目录已设置为: {directory}")
        except Exception as e:
            error_msg = f"选择保存目录失败: {str(e)}\n{traceback.format_exc()}"
            self.log_text.append(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            
    # 多任务保存路径浏览函数已移除

    def _start_download(self):
        """开始下载"""
        try:
            if self.mutex.tryLock():
                url = self.url_input.text().strip()
                if not url:
                    QMessageBox.critical(self, "错误", "请输入有效链接")
                    self.mutex.unlock()
                    return
                
                video_fmt = self.resolution_combo.currentData()
                audio_fmt = self.audio_combo.currentData()
                subtitle_lang = self.subtitle_combo.currentData()
                
                if not video_fmt or not audio_fmt:
                    QMessageBox.critical(self, "错误", "请选择视频和音频格式")
                    self.mutex.unlock()
                    return
                
                # 重置进度条和状态
                self.progress_bar.setValue(0)
                self.status_label.setText("准备下载...")
                self.speed_label.setText("下载速度: 0.00 MB/s")
                self.log_text.append(f"开始下载: {url}")
                
                # 禁用相关按钮
                self.download_button.setEnabled(False)
                self.cancel_button.setEnabled(True)
                self.url_input.setEnabled(False)
                self.resolution_combo.setEnabled(False)
                self.audio_combo.setEnabled(False)
                self.subtitle_combo.setEnabled(False)
                
                # 启动下载线程
                self.thread = DownloadThread(self.downloader, url, video_fmt, audio_fmt, subtitle_lang)
                self.thread.finished.connect(self._on_download_complete)
                self.thread.error.connect(self._on_error)
                self.thread.start()
                
        except Exception as e:
            error_msg = f"启动下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_text.append(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            self.mutex.unlock()

    def _update_progress(self, percent, speed):
        """更新下载进度和速度 - 直接显示实时进度"""
        try:
            # 直接设置进度条值
            self.progress_bar.setValue(int(percent))
            self.current_progress = int(percent)
            
            # 更新速度标签
            self.speed_label.setText(f"下载速度: {speed}")
            
            # 更新状态标签
            if percent < 100:
                if speed == "准备下载...":
                    self.status_label.setText("准备下载...")
                elif speed == "处理中...":
                    self.status_label.setText("处理中...")
                else:
                    self.status_label.setText(f"正在下载: {percent:.1f}%")
            else:
                self.status_label.setText("下载完成")
            
            # 确保UI即时更新
            QApplication.processEvents()
            
        except Exception as e:
            error_msg = f"更新进度失败: {str(e)}\n{traceback.format_exc()}"
            self.log_text.append(error_msg)

    def _on_download_complete(self, msg):
        """下载完成处理"""
        try:
            # 确保进度条显示100%
            self.progress_bar.setValue(100)
            self.current_progress = 100
            
            # 恢复按钮状态
            self.download_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.url_input.setEnabled(True)
            self.resolution_combo.setEnabled(True)
            self.audio_combo.setEnabled(True)
            self.subtitle_combo.setEnabled(True)
            
            # 更新状态
            self.status_label.setText("下载完成")
            
            # 添加下载完成的日志记录
            self.log_text.append(msg)
            
            # 解锁互斥锁
            self.mutex.unlock()
            
        except Exception as e:
            error_msg = f"处理完成消息失败: {str(e)}\n{traceback.format_exc()}"
            self.log_text.append(error_msg)

    def _on_error(self, msg):
        """错误处理"""
        try:
            # 恢复按钮状态
            self.download_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.url_input.setEnabled(True)
            self.resolution_combo.setEnabled(True)
            self.audio_combo.setEnabled(True)
            self.subtitle_combo.setEnabled(True)
            
            # 更新状态
            self.status_label.setText("下载失败")
            self.log_text.append(f"错误: {msg}")
            
            if "无法获取视频信息" in msg or "下载失败" in msg:
                QMessageBox.critical(self, "错误", f"下载失败: {msg}")
            elif "下载已取消" in msg:
                self.status_label.setText("下载已取消")
                self.log_text.append("下载已取消")
            
            # 解锁互斥锁
            self.mutex.unlock()
            
        except Exception as e:
            error_msg = f"处理错误消息失败: {str(e)}\n{traceback.format_exc()}"
            self.log_text.append(error_msg)
            
    # 多任务下载相关事件处理函数已移除

    def _cancel_download(self):
        """取消单任务下载"""
        try:
            if hasattr(self, 'thread') and self.thread.isRunning():
                # 在日志中显示取消消息
                self.log_text.append("正在取消下载...")
                # 调用线程的取消方法
                self.thread.cancel()
                # 更新UI状态
                self.status_label.setText("正在取消...")
                self.cancel_button.setEnabled(False)
        except Exception as e:
            error_msg = f"取消下载失败: {str(e)}\n{traceback.format_exc()}"
            self.log_text.append(error_msg)
            
    # 多任务下载相关操作函数已移除