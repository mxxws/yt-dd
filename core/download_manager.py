import os
import time
import threading
import uuid
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from queue import Queue, Empty
from PyQt6.QtCore import QObject, pyqtSignal

from core.downloader import VideoDownloader
from core.logger import Logger, log, log_exception

class TaskStatus(Enum):
    """下载任务状态"""
    WAITING = 1      # 等待下载
    ANALYZING = 2    # 分析中
    DOWNLOADING = 3  # 下载中
    PAUSED = 4       # 已暂停
    COMPLETED = 5    # 已完成
    FAILED = 6       # 失败
    CANCELED = 7     # 已取消

@dataclass
class DownloadTask:
    """下载任务数据类"""
    id: str                      # 任务ID
    url: str                     # 下载URL
    video_format: Optional[str]  # 视频格式ID
    audio_format: Optional[str]  # 音频格式ID
    subtitle_lang: Optional[str] # 字幕语言代码
    save_dir: str                # 保存目录
    status: TaskStatus = TaskStatus.WAITING  # 任务状态
    progress: float = 0.0        # 下载进度 (0-100)
    speed: str = "0.00 MB/s"    # 下载速度
    title: str = ""             # 视频标题
    error_message: str = ""     # 错误信息
    created_at: float = field(default_factory=time.time)  # 创建时间
    output_path: str = ""       # 输出文件路径
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = str(uuid.uuid4())

class DownloadManagerSignals(QObject):
    """下载管理器信号类"""
    task_added = pyqtSignal(str)  # 任务ID
    task_started = pyqtSignal(str)  # 任务ID
    task_paused = pyqtSignal(str)  # 任务ID
    task_resumed = pyqtSignal(str)  # 任务ID
    task_completed = pyqtSignal(str, str)  # 任务ID, 输出路径
    task_failed = pyqtSignal(str, str)  # 任务ID, 错误信息
    task_canceled = pyqtSignal(str)  # 任务ID
    task_removed = pyqtSignal(str)  # 任务ID
    task_progress_updated = pyqtSignal(str, float, str)  # 任务ID, 进度, 速度
    task_info_updated = pyqtSignal(str, str)  # 任务ID, 标题
    all_tasks_completed = pyqtSignal()  # 所有任务完成

class DownloadManager:
    """下载管理器，负责管理多个下载任务"""
    
    def __init__(self, max_concurrent: int = 2):
        """初始化下载管理器
        
        Args:
            max_concurrent: 最大并发下载数
        """
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, DownloadTask] = {}  # 任务字典
        self.active_tasks: List[str] = []  # 活动任务列表
        self.waiting_queue: Queue = Queue()  # 等待队列
        self.downloader_map: Dict[str, VideoDownloader] = {}  # 下载器映射
        self.lock = threading.RLock()  # 线程锁
        self.signals = DownloadManagerSignals()  # 信号对象
        self.running = True  # 运行标志
        
        # 启动任务处理线程
        self.process_thread = threading.Thread(target=self._process_tasks, daemon=True)
        self.process_thread.start()
    
    def add_task(self, url: str, video_format: str, audio_format: str, 
                 subtitle_lang: Optional[str], save_dir: str) -> str:
        """添加下载任务
        
        Args:
            url: 视频URL
            video_format: 视频格式ID
            audio_format: 音频格式ID
            subtitle_lang: 字幕语言代码
            save_dir: 保存目录
            
        Returns:
            str: 任务ID
        """
        with self.lock:
            # 创建任务
            task = DownloadTask(
                id="",  # 自动生成ID
                url=url,
                video_format=video_format,
                audio_format=audio_format,
                subtitle_lang=subtitle_lang,
                save_dir=save_dir
            )
            
            # 添加到任务字典
            self.tasks[task.id] = task
            
            # 创建下载器
            downloader = VideoDownloader()
            downloader.save_dir = save_dir
            
            # 连接信号
            downloader.signals.progress_updated.connect(
                lambda percent, speed, task_id=task.id: 
                self._on_progress_updated(task_id, percent, speed)
            )
            downloader.signals.download_finished.connect(
                lambda output_path, task_id=task.id: 
                self._on_download_finished(task_id, output_path)
            )
            downloader.signals.error_occurred.connect(
                lambda error_msg, task_id=task.id: 
                self._on_error_occurred(task_id, error_msg)
            )
            downloader.signals.info_loaded.connect(
                lambda video_formats, audio_formats, subtitle_langs, task_id=task.id:
                self._on_info_loaded(task_id, video_formats, audio_formats, subtitle_langs)
            )
            
            # 保存下载器
            self.downloader_map[task.id] = downloader
            
            # 添加到等待队列
            self.waiting_queue.put(task.id)
            
            # 发送任务添加信号
            self.signals.task_added.emit(task.id)
            
            log.info(f"添加下载任务: {url}, ID: {task.id}")
            
            return task.id
    
    def pause_task(self, task_id: str) -> bool:
        """暂停下载任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # 只有下载中的任务可以暂停
            if task.status != TaskStatus.DOWNLOADING:
                return False
            
            # 更新任务状态
            task.status = TaskStatus.PAUSED
            
            # 取消下载
            if task_id in self.downloader_map:
                self.downloader_map[task_id].cancel_download()
            
            # 从活动任务列表中移除
            if task_id in self.active_tasks:
                self.active_tasks.remove(task_id)
            
            # 发送任务暂停信号
            self.signals.task_paused.emit(task_id)
            
            log.info(f"暂停下载任务: {task_id}")
            
            return True
    
    def resume_task(self, task_id: str) -> bool:
        """恢复下载任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # 只有暂停的任务可以恢复
            if task.status != TaskStatus.PAUSED:
                return False
            
            # 更新任务状态
            task.status = TaskStatus.WAITING
            
            # 添加到等待队列
            self.waiting_queue.put(task_id)
            
            # 发送任务恢复信号
            self.signals.task_resumed.emit(task_id)
            
            log.info(f"恢复下载任务: {task_id}")
            
            return True
    
    def cancel_task(self, task_id: str) -> bool:
        """取消下载任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # 已完成或已取消的任务不能取消
            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELED]:
                return False
            
            # 更新任务状态
            task.status = TaskStatus.CANCELED
            
            # 取消下载
            if task_id in self.downloader_map:
                self.downloader_map[task_id].cancel_download()
            
            # 从活动任务列表中移除
            if task_id in self.active_tasks:
                self.active_tasks.remove(task_id)
            
            # 发送任务取消信号
            self.signals.task_canceled.emit(task_id)
            
            log.info(f"取消下载任务: {task_id}")
            
            return True
    
    def remove_task(self, task_id: str) -> bool:
        """移除下载任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 操作成功返回True，否则返回False
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # 下载中的任务需要先取消
            if task.status == TaskStatus.DOWNLOADING:
                self.cancel_task(task_id)
            
            # 从任务字典中移除
            del self.tasks[task_id]
            
            # 从下载器映射中移除
            if task_id in self.downloader_map:
                del self.downloader_map[task_id]
            
            # 发送任务移除信号
            self.signals.task_removed.emit(task_id)
            
            log.info(f"移除下载任务: {task_id}")
            
            return True
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[DownloadTask]: 任务对象，不存在返回None
        """
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, DownloadTask]:
        """获取所有任务
        
        Returns:
            Dict[str, DownloadTask]: 任务字典
        """
        with self.lock:
            return self.tasks.copy()
    
    def _process_tasks(self):
        """处理下载任务的线程函数"""
        while self.running:
            try:
                # 检查是否可以启动新任务
                with self.lock:
                    can_start = len(self.active_tasks) < self.max_concurrent
                
                if can_start:
                    try:
                        # 从等待队列获取任务ID（非阻塞）
                        task_id = self.waiting_queue.get(block=False)
                        
                        with self.lock:
                            if task_id in self.tasks and self.tasks[task_id].status == TaskStatus.WAITING:
                                # 启动下载线程
                                thread = threading.Thread(
                                    target=self._download_task,
                                    args=(task_id,),
                                    daemon=True
                                )
                                thread.start()
                                
                                # 添加到活动任务列表
                                self.active_tasks.append(task_id)
                                
                                # 更新任务状态
                                self.tasks[task_id].status = TaskStatus.ANALYZING
                                
                                # 发送任务开始信号
                                self.signals.task_started.emit(task_id)
                                
                                log.info(f"开始下载任务: {task_id}")
                            else:
                                # 任务可能已被取消或移除
                                self.waiting_queue.task_done()
                    except Empty:
                        # 等待队列为空
                        pass
                
                # 检查是否所有任务都已完成
                with self.lock:
                    active_count = len(self.active_tasks)
                    waiting_count = self.waiting_queue.qsize()
                    
                    if active_count == 0 and waiting_count == 0 and self.tasks:
                        # 检查是否有非完成、失败或取消的任务
                        has_incomplete = False
                        for task in self.tasks.values():
                            if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED]:
                                has_incomplete = True
                                break
                        
                        if not has_incomplete:
                            # 发送所有任务完成信号
                            self.signals.all_tasks_completed.emit()
                            log.info("所有下载任务已完成")
                
                # 避免CPU占用过高
                time.sleep(0.1)
            except Exception as e:
                log_exception(e, "处理下载任务时出错")
    
    def _download_task(self, task_id: str):
        """下载任务的线程函数
        
        Args:
            task_id: 任务ID
        """
        try:
            with self.lock:
                if task_id not in self.tasks or task_id not in self.downloader_map:
                    return
                
                task = self.tasks[task_id]
                downloader = self.downloader_map[task_id]
            
            # 更新任务状态
            with self.lock:
                task.status = TaskStatus.DOWNLOADING
            
            # 执行下载
            output_path = downloader.download(
                task.url,
                task.video_format,
                task.audio_format,
                task.subtitle_lang
            )
            
            # 下载成功
            with self.lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.status = TaskStatus.COMPLETED
                    task.progress = 100.0
                    task.output_path = output_path
                    
                    # 从活动任务列表中移除
                    if task_id in self.active_tasks:
                        self.active_tasks.remove(task_id)
                    
                    # 发送任务完成信号
                    self.signals.task_completed.emit(task_id, output_path)
                    
                    log.info(f"下载任务完成: {task_id}, 输出路径: {output_path}")
                    
                    # 标记队列任务完成
                    self.waiting_queue.task_done()
        except Exception as e:
            error_msg = log_exception(e, f"下载任务 {task_id} 失败")
            
            with self.lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    
                    # 从活动任务列表中移除
                    if task_id in self.active_tasks:
                        self.active_tasks.remove(task_id)
                    
                    # 发送任务失败信号
                    self.signals.task_failed.emit(task_id, str(e))
                    
                    # 标记队列任务完成
                    self.waiting_queue.task_done()
    
    def _on_progress_updated(self, task_id: str, percent: float, speed: str):
        """进度更新回调
        
        Args:
            task_id: 任务ID
            percent: 进度百分比
            speed: 下载速度
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.progress = percent
                task.speed = speed
                
                # 发送进度更新信号
                self.signals.task_progress_updated.emit(task_id, percent, speed)
    
    def _on_download_finished(self, task_id: str, output_path: str):
        """下载完成回调
        
        Args:
            task_id: 任务ID
            output_path: 输出文件路径
        """
        # 由_download_task函数处理
        pass
    
    def _on_error_occurred(self, task_id: str, error_msg: str):
        """错误发生回调
        
        Args:
            task_id: 任务ID
            error_msg: 错误信息
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.FAILED
                task.error_message = error_msg
                
                # 从活动任务列表中移除
                if task_id in self.active_tasks:
                    self.active_tasks.remove(task_id)
                
                # 发送任务失败信号
                self.signals.task_failed.emit(task_id, error_msg)
                
                log.error(f"下载任务 {task_id} 失败: {error_msg}")
                
                # 标记队列任务完成
                self.waiting_queue.task_done()
    
    def _on_info_loaded(self, task_id: str, video_formats: List[Dict], 
                       audio_formats: List[Dict], subtitle_langs: List[Dict]):
        """信息加载回调
        
        Args:
            task_id: 任务ID
            video_formats: 视频格式列表
            audio_formats: 音频格式列表
            subtitle_langs: 字幕语言列表
        """
        with self.lock:
            if task_id in self.tasks and task_id in self.downloader_map:
                task = self.tasks[task_id]
                downloader = self.downloader_map[task_id]
                
                # 获取视频标题
                if hasattr(downloader, 'video_title') and downloader.video_title:
                    task.title = downloader.video_title
                    
                    # 发送信息更新信号
                    self.signals.task_info_updated.emit(task_id, task.title)
    
    def start_all_tasks(self):
        """开始所有等待中的任务"""
        log.info("开始所有等待中的任务")
        
        with self.lock:
            # 获取所有任务
            tasks = self.tasks.copy()
            
            # 找出所有等待中的任务
            waiting_tasks = [task_id for task_id, task in tasks.items() 
                            if task.status == TaskStatus.WAITING.value]
            
            # 将所有等待中的任务添加到等待队列
            for task_id in waiting_tasks:
                if task_id not in self.waiting_queue.queue:
                    self.waiting_queue.put(task_id)
                    log.info(f"任务 {task_id} 已添加到等待队列")
    
    def pause_all_tasks(self):
        """暂停所有下载中的任务"""
        log.info("暂停所有下载中的任务")
        
        with self.lock:
            # 获取所有任务
            tasks = self.tasks.copy()
            
            # 找出所有下载中的任务
            active_tasks = list(self.active_tasks)
            
            # 暂停所有下载中的任务
            for task_id in active_tasks:
                self.pause_task(task_id)
    
    def shutdown(self):
        """关闭下载管理器"""
        log.info("正在关闭下载管理器...")
        
        # 停止运行
        self.running = False
        
        # 取消所有活动任务
        with self.lock:
            for task_id in list(self.active_tasks):
                self.cancel_task(task_id)
        
        # 等待处理线程结束
        if self.process_thread.is_alive():
            self.process_thread.join(timeout=2.0)
        
        log.info("下载管理器已关闭")