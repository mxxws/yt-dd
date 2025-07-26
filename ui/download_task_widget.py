from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont

import os
from typing import Dict, Optional
from core.download_manager import DownloadTask, TaskStatus

class TaskItemWidget(QFrame):
    """单个下载任务项组件"""
    
    # 自定义信号
    pause_clicked = pyqtSignal(str)  # 任务ID
    resume_clicked = pyqtSignal(str)  # 任务ID
    cancel_clicked = pyqtSignal(str)  # 任务ID
    remove_clicked = pyqtSignal(str)  # 任务ID
    
    def __init__(self, task: DownloadTask, parent=None):
        super().__init__(parent)
        self.task_id = task.id
        self.status = task.status
        
        # 设置样式
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet("""
            TaskItemWidget {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
                margin: 6px;
                padding: 16px;
            }
            
            TaskItemWidget:hover {
                border: 1px solid #4361EE;
                background-color: #F8F9FE;
            }
            
            QLabel {
                color: #333333;
                font-weight: 400;
            }
            
            QProgressBar {
                border: none;
                background-color: #F0F2FA;
                height: 8px;
                border-radius: 4px;
                text-align: center;
                margin-top: 4px;
                margin-bottom: 4px;
            }
            
            QProgressBar::chunk {
                background-color: #4CC9F0;
                border-radius: 4px;
            }
        """)
        
        # 创建布局
        self._init_ui(task)
    
    def _init_ui(self, task: DownloadTask):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # 标题和状态行
        title_layout = QHBoxLayout()
        
        # 提取视频标题
        video_title = task.title if task.title else (os.path.basename(task.save_dir) if task.save_dir else "未知视频")
        self.title_label = QLabel(video_title)
        self.title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        self.title_label.setToolTip(task.url)
        # 确保标题不会太长
        self.title_label.setMaximumWidth(300)
        self.title_label.setWordWrap(True)
        
        self.status_label = QLabel(self._get_status_text(task.status))
        self.status_label.setStyleSheet(self._get_status_style(task.status))
        
        title_layout.addWidget(self.title_label, 1)  # 1表示伸展因子
        title_layout.addWidget(self.status_label)
        
        # 进度条和速度行
        progress_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(int(task.progress))
        self.progress_bar.setTextVisible(False)
        
        self.speed_label = QLabel(task.speed)
        self.speed_label.setStyleSheet("color: #757575; font-size: 12px;")
        
        progress_layout.addWidget(self.progress_bar, 1)  # 1表示伸展因子
        progress_layout.addWidget(self.speed_label)
        
        # 按钮行
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        
        # 根据状态显示不同的按钮
        if task.status == TaskStatus.DOWNLOADING.value:
            self.pause_button = QPushButton("暂停")
            self.pause_button.setFixedSize(70, 28)
            self.pause_button.setObjectName("task_pause_button")
            self.pause_button.setStyleSheet("""
                QPushButton#task_pause_button {
                    background-color: #4361EE;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-weight: 500;
                    font-size: 12px;
                }
                QPushButton#task_pause_button:hover {
                    background-color: #3A56D4;
                }
                QPushButton#task_pause_button:pressed {
                    background-color: #2A46C4;
                }
            """)
            self.pause_button.clicked.connect(lambda: self.pause_clicked.emit(self.task_id))
            
            self.cancel_button = QPushButton("取消")
            self.cancel_button.setFixedSize(70, 28)
            self.cancel_button.setObjectName("task_cancel_button")
            self.cancel_button.setStyleSheet("""
                QPushButton#task_cancel_button {
                    background-color: #EF476F;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-weight: 500;
                    font-size: 12px;
                }
                QPushButton#task_cancel_button:hover {
                    background-color: #E43065;
                }
                QPushButton#task_cancel_button:pressed {
                    background-color: #D4205B;
                }
            """)
            self.cancel_button.clicked.connect(lambda: self.cancel_clicked.emit(self.task_id))
            
            button_layout.addWidget(self.pause_button)
            button_layout.addWidget(self.cancel_button)
            
        elif task.status == TaskStatus.PAUSED.value:
            self.resume_button = QPushButton("继续")
            self.resume_button.setFixedSize(70, 28)
            self.resume_button.setObjectName("task_resume_button")
            self.resume_button.setStyleSheet("""
                QPushButton#task_resume_button {
                    background-color: #06D6A0;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-weight: 500;
                    font-size: 12px;
                }
                QPushButton#task_resume_button:hover {
                    background-color: #05C190;
                }
                QPushButton#task_resume_button:pressed {
                    background-color: #04AC80;
                }
            """)
            self.resume_button.clicked.connect(lambda: self.resume_clicked.emit(self.task_id))
            
            self.cancel_button = QPushButton("取消")
            self.cancel_button.setFixedSize(70, 28)
            self.cancel_button.setObjectName("task_cancel_button")
            self.cancel_button.setStyleSheet("""
                QPushButton#task_cancel_button {
                    background-color: #EF476F;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-weight: 500;
                    font-size: 12px;
                }
                QPushButton#task_cancel_button:hover {
                    background-color: #E43065;
                }
                QPushButton#task_cancel_button:pressed {
                    background-color: #D4205B;
                }
            """)
            self.cancel_button.clicked.connect(lambda: self.cancel_clicked.emit(self.task_id))
            
            button_layout.addWidget(self.resume_button)
            button_layout.addWidget(self.cancel_button)
            
        elif task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELED.value]:
            self.remove_button = QPushButton("移除")
            self.remove_button.setFixedSize(70, 28)
            self.remove_button.setObjectName("task_remove_button")
            self.remove_button.setStyleSheet("""
                QPushButton#task_remove_button {
                    background-color: #6C757D;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-weight: 500;
                    font-size: 12px;
                }
                QPushButton#task_remove_button:hover {
                    background-color: #5A6268;
                }
                QPushButton#task_remove_button:pressed {
                    background-color: #495057;
                }
            """)
            self.remove_button.clicked.connect(lambda: self.remove_clicked.emit(self.task_id))
            
            # 如果下载失败，显示错误信息
            if task.status == TaskStatus.FAILED.value and task.error_message:
                self.error_label = QLabel(f"错误: {task.error_message}")
                self.error_label.setStyleSheet("color: #F44336; font-size: 12px;")
                main_layout.addWidget(self.error_label)
            
            button_layout.addStretch(1)  # 添加弹性空间
            button_layout.addWidget(self.remove_button)
        
        # 添加所有布局到主布局
        main_layout.addLayout(title_layout)
        main_layout.addLayout(progress_layout)
        main_layout.addLayout(button_layout)
    
    def update_task(self, task: DownloadTask):
        """更新任务信息"""
        # 只有状态变化时才需要重建UI
        if self.status != task.status:
            self.status = task.status
            
            # 保存当前标题，避免重建UI时丢失
            current_title = self.title_label.text()
            if not task.title and current_title:
                task.title = current_title
            
            # 清除现有布局
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # 重新初始化UI
            self._init_ui(task)
        else:
            # 只更新进度和速度
            self.progress_bar.setValue(int(task.progress))
            self.speed_label.setText(task.speed)
            self.status_label.setText(self._get_status_text(task.status))
            self.status_label.setStyleSheet(self._get_status_style(task.status))
    
    def _get_status_text(self, status: int) -> str:
        """获取状态文本"""
        status_map = {
            TaskStatus.WAITING.value: "等待中",
            TaskStatus.ANALYZING.value: "分析中",
            TaskStatus.DOWNLOADING.value: "下载中",
            TaskStatus.PAUSED.value: "已暂停",
            TaskStatus.COMPLETED.value: "已完成",
            TaskStatus.FAILED.value: "下载失败",
            TaskStatus.CANCELED.value: "已取消"
        }
        return status_map.get(status, str(status))
    
    def _get_status_style(self, status: int) -> str:
        """获取状态样式"""
        status_styles = {
            TaskStatus.WAITING.value: "color: #6C757D; background-color: #F0F2F5; padding: 4px 8px; border-radius: 4px; font-size: 12px;",
            TaskStatus.ANALYZING.value: "color: #6C757D; background-color: #F0F2F5; padding: 4px 8px; border-radius: 4px; font-size: 12px;",
            TaskStatus.DOWNLOADING.value: "color: #4361EE; font-weight: bold; background-color: #EFF3FF; padding: 4px 8px; border-radius: 4px; font-size: 12px;",
            TaskStatus.PAUSED.value: "color: #F7B801; font-weight: bold; background-color: #FFF8E6; padding: 4px 8px; border-radius: 4px; font-size: 12px;",
            TaskStatus.COMPLETED.value: "color: #06D6A0; font-weight: bold; background-color: #E6FFF7; padding: 4px 8px; border-radius: 4px; font-size: 12px;",
            TaskStatus.FAILED.value: "color: #EF476F; font-weight: bold; background-color: #FFEDF2; padding: 4px 8px; border-radius: 4px; font-size: 12px;",
            TaskStatus.CANCELED.value: "color: #6C757D; font-weight: bold; background-color: #F0F2F5; padding: 4px 8px; border-radius: 4px; font-size: 12px;"
        }
        return status_styles.get(status, "color: #6C757D; background-color: #F0F2F5; padding: 4px 8px; border-radius: 4px; font-size: 12px;")

class DownloadTaskWidget(QWidget):
    """下载任务列表组件"""
    
    # 自定义信号
    task_pause_requested = pyqtSignal(str)  # 任务ID
    task_resume_requested = pyqtSignal(str)  # 任务ID
    task_cancel_requested = pyqtSignal(str)  # 任务ID
    task_remove_requested = pyqtSignal(str)  # 任务ID
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_widgets: Dict[str, TaskItemWidget] = {}
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            QScrollBar:vertical {
                border: none;
                background: #F8F9FE;
                width: 10px;
                margin: 0px;
            }
            
            QScrollBar::handle:vertical {
                background: #D0D6F9;
                min-height: 30px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #4361EE;
            }
            
            QScrollBar::handle:vertical:pressed {
                background: #3A56D4;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # 创建内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch(1)  # 添加弹性空间，使任务项靠上对齐
        
        # 设置滚动区域的内容
        self.scroll_area.setWidget(self.content_widget)
        
        # 添加到主布局
        main_layout.addWidget(self.scroll_area)
    
    def add_task(self, task_id: str, title: str):
        """添加任务"""
        # 创建任务对象
        task = DownloadTask(
            id=task_id,
            url="",  # 这里不需要URL，因为只是用于显示
            video_format=None,
            audio_format=None,
            subtitle_lang=None,
            save_dir="",
            title=title
        )
        
        # 创建任务项组件
        task_widget = TaskItemWidget(task)
        
        # 连接信号
        task_widget.pause_clicked.connect(self.task_pause_requested)
        task_widget.resume_clicked.connect(self.task_resume_requested)
        task_widget.cancel_clicked.connect(self.task_cancel_requested)
        task_widget.remove_clicked.connect(self.task_remove_requested)
        
        # 添加到布局
        self.content_layout.insertWidget(0, task_widget)  # 插入到顶部
        
        # 保存引用
        self.task_widgets[task_id] = task_widget
    
    def update_task(self, task_id: str, status: int, progress: float, speed: str):
        """更新任务"""
        if task_id in self.task_widgets:
            # 获取当前任务组件中的标题
            current_title = self.task_widgets[task_id].title_label.text()
            
            # 创建临时任务对象用于更新，保留标题信息
            task = DownloadTask(
                id=task_id,
                url="",  # 这里不需要URL，因为只是用于显示
                video_format=None,
                audio_format=None,
                subtitle_lang=None,
                save_dir="",
                status=status,
                progress=progress,
                speed=speed,
                title=current_title  # 保留原有标题
            )
            self.task_widgets[task_id].update_task(task)
    
    def remove_task(self, task_id: str):
        """移除任务"""
        if task_id in self.task_widgets:
            # 从布局中移除
            widget = self.task_widgets[task_id]
            self.content_layout.removeWidget(widget)
            widget.deleteLater()
            
            # 从字典中移除
            del self.task_widgets[task_id]
    
    def clear_tasks(self):
        """清除所有任务"""
        for task_id, widget in list(self.task_widgets.items()):
            self.remove_task(task_id)