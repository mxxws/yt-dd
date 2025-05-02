import os
import re
import traceback
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QPushButton, QLabel,
    QProgressBar, QFileDialog, QMessageBox, QTextEdit,
    QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QElapsedTimer, QTimer, QPropertyAnimation, QSize
from PyQt6.QtGui import QFont, QIcon
from core.downloader import VideoDownloader

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
        self.downloader = VideoDownloader()
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
        
        self._init_ui()
        self._connect_signals()
        self._set_style()

    def _init_ui(self):
        self.setWindowTitle("yt-dd")
        self.setMinimumSize(800, 600)
        
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
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # URL输入区域
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入YouTube视频链接")
        self.parse_button = QPushButton("粘贴并解析")
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
        save_layout.addWidget(QLabel("保存位置:"))
        save_layout.addWidget(self.save_path_input)
        save_layout.addWidget(self.browse_button)
        layout.addLayout(save_layout)
        
        # 进度显示区域
        progress_layout = QVBoxLayout()
        self.analysis_label = QLabel("就绪")
        self.analysis_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar = QProgressBar()
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
        self.cancel_button = QPushButton("取消下载")
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def _set_style(self):
        # 设置整体样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
            
            QWidget {
                font-family: "Microsoft YaHei", "微软雅黑";
                color: #333333;
            }
            
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background-color: #1E88E5;
            }
            
            QPushButton:pressed {
                background-color: #1976D2;
            }
            
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
            
            QLineEdit {
                border: 1px solid #DDDDDD;
                border-radius: 4px;
                padding: 8px 12px;
                background: white;
                selection-background-color: #E3F2FD;
                font-size: 13px;
            }
            
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
            
            QComboBox {
                border: 1px solid #DDDDDD;
                border-radius: 4px;
                padding: 8px 12px;
                background: white;
                font-size: 13px;
                min-width: 150px;
            }
            
            QComboBox:focus {
                border: 1px solid #2196F3;
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
                background-color: #F5F5F5;
                height: 8px;
                border-radius: 4px;
            }
            
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
            
            QLabel {
                color: #424242;
                font-size: 13px;
            }
            
            QTextEdit {
                border: 1px solid #DDDDDD;
                border-radius: 4px;
                padding: 8px;
                background: white;
                font-size: 13px;
            }
            
            QTextEdit:focus {
                border: 1px solid #2196F3;
            }
            
            #status_label {
                color: #2196F3;
                font-weight: 500;
                font-size: 14px;
            }
            
            #speed_label {
                color: #757575;
                font-size: 13px;
            }
            
            #analysis_label {
                color: #757575;
                font-size: 13px;
            }
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

        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        
        # 设置窗口动画
        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.start()

    def _connect_signals(self):
        # 修改URL输入信号连接
        self.url_input.textChanged.connect(self._on_url_changed)
        self.browse_button.clicked.connect(self.browse_save_path)
        self.download_button.clicked.connect(self._start_download)
        self.cancel_button.clicked.connect(self._cancel_download)
        
        # 确保进度更新信号正确连接
        self.downloader.signals.progress_updated.connect(self._update_progress)
        self.downloader.signals.info_loaded.connect(self._update_formats)
        self.downloader.signals.download_finished.connect(self._on_download_complete)
        self.downloader.signals.error_occurred.connect(self._on_error)

    def _on_url_changed(self):
        """处理URL输入变化"""
        # 重置并启动延时器
        self.url_input_timer.stop()
        self.url_input_timer.start(800)  # 800ms后触发分析
        
        # 更新UI状态
        self.analysis_label.setText("准备分析...")
        self.resolution_combo.clear()
        self.audio_combo.clear()
        self.subtitle_combo.clear()

    def _delayed_analysis(self):
        """延迟执行分析"""
        url = self.url_input.text().strip()
        if re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/', url):
            self.analysis_label.setText("正在分析视频信息...")
            self.analysis_timer.start(100)
            self._load_media_info()
        else:
            self.analysis_label.setText("请输入有效的YouTube链接")

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

    def _load_media_info(self):
        try:
            url = self.url_input.text().strip()
            self.log_text.append(f"正在解析视频信息: {url}")
            self.downloader.get_media_info(url)
        except Exception as e:
            error_msg = f"解析视频信息失败: {str(e)}\n{traceback.format_exc()}"
            self.log_text.append(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
        finally:
            self.analysis_timer.stop()

    def _update_formats(self, video_formats, audio_formats, subtitle_langs):
        try:
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
            self.log_text.append("下载完成")
            
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

    def _cancel_download(self):
        """取消下载"""
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