import os
import re
import traceback
import time
import json
import functools
import signal
import sys
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass
from pytubefix import YouTube
from pytubefix.cli import on_progress
from moviepy.editor import VideoFileClip, AudioFileClip
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import yt_dlp
import subprocess

# 全局变量，用于跟踪当前的yt-dlp进程
YDL_INSTANCE = None

@dataclass
class FormatInfo:
    """视频/音频格式信息"""
    id: str
    desc: str
    ext: str

@dataclass
class SubtitleInfo:
    """字幕信息"""
    code: str
    name: str

class DownloadSignals(QObject):
    """下载信号类"""
    progress_updated = pyqtSignal(float, str)
    info_loaded = pyqtSignal(list, list, list)
    download_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

def catch_exceptions(func):
    """装饰器: 捕获方法中的异常并发送错误信号"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            error_msg = f"{func.__name__}失败: {str(e)}\n{traceback.format_exc()}"
            if hasattr(self, 'signals') and hasattr(self.signals, 'error_occurred'):
                self.signals.error_occurred.emit(error_msg)
            return None
    return wrapper

class VideoDownloader:
    """视频下载器类"""
    
    def __init__(self):
        """初始化下载器"""
        # 输出yt-dlp版本信息
        try:
            import yt_dlp.version
            print(f"使用 yt-dlp 版本: {yt_dlp.version.__version__}")
        except Exception as e:
            print(f"获取yt-dlp版本信息失败: {str(e)}")
            
        # 读取配置文件
        self.config = self._load_config()
        
        # 设置下载目录
        if self.config and self.config.get("download_path"):
            if self.config["download_path"] == "Downloads":
                self.save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            else:
                self.save_dir = self.config["download_path"]
        else:
            self.save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            
        self.signals = DownloadSignals()
        self.ydl_opts = self._get_default_options()
        self.download_started = False
        self.current_file = ""
        # 进度相关
        self.current_percent = 0  # 当前实际进度
        self.display_percent = 0  # 显示的进度
        self.last_speed = "0.00 MB/s"
        self.last_update_time = 0  # 上次更新时间
        self.update_interval = 0.1  # 更新间隔（秒）
        self.is_merging = False  # 是否正在合并文件
        self.is_canceled = False  # 取消标志
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "default_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"警告: 配置文件不存在: {config_path}")
                return {}
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            return {}
    
    def _get_default_options(self) -> Dict:
        """获取默认下载选项"""
        return {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': {'default': os.path.join(self.save_dir, '%(title)s', '%(title)s.%(ext)s')},
            'progress_hooks': [self._progress_hook],
            'quiet': False,
            'no_warnings': True,
            'extract_flat': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'retries': 15,
            'file_access_retries': 15,
            'fragment_retries': 15,
            'extractor_retries': 5,
            'retry_sleep_functions': {
                'file_access': lambda n: 1 + n,
                'fragment': lambda n: 1 + n,
            },
            'no_color': True,
            'no_call_home': True,
            'no_check_certificate': True,
            'prefer_ffmpeg': True,
            'merge_output_format': 'mp4',
            # 禁用字幕自动下载，我们将在视频下载完成后手动处理
            'writesubtitles': False,
            'writeautomaticsub': False,
            'subtitleslangs': ['all'],
            'skip_download': False,
            'embedsubtitles': False,  # 不将字幕嵌入视频
            'postprocessors': [
                {
                    'key': 'FFmpegVideoRemuxer',
                    'preferedformat': 'mp4',
                },
            ],
            'keepvideo': False,
            'keepfragments': False,
            'clean_infojson': True,
            'writethumbnail': False,
            # 添加以下选项解决网络问题
            'socket_timeout': 30,  # 增加超时时间
            'source_address': '0.0.0.0',
            'force_ipv4': True,
            'sleep_interval': 5,  # 两次请求间隔时间
            'max_sleep_interval': 10,
            'external_downloader': 'aria2c',  # 使用aria2c作为外部下载器
            'external_downloader_args': ['--min-split-size=1M', '--max-connection-per-server=10', '--split=10', '--max-tries=10'],
            'cookies-from-browser': None,  # 可以考虑添加浏览器cookie
        }
    
    def _validate_url(self, url: str) -> bool:
        """验证URL格式"""
        return bool(re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/', url))
    
    def _get_video_formats(self, info: Dict) -> List[FormatInfo]:
        """获取视频格式列表"""
        formats = []
        for fmt in info['formats']:
            if fmt.get('vcodec', 'none') != 'none':
                formats.append(FormatInfo(
                    id=fmt['format_id'],
                    desc=f"{fmt.get('height', '?')}p {fmt.get('ext', '')}",
                    ext=fmt.get('ext', '')
                ))
        return formats
    
    def _get_audio_formats(self, info: Dict) -> List[FormatInfo]:
        """获取音频格式列表"""
        formats = []
        for fmt in info['formats']:
            if fmt.get('acodec', 'none') != 'none' and fmt.get('vcodec', 'none') == 'none':
                formats.append(FormatInfo(
                    id=fmt['format_id'],
                    desc=f"{fmt.get('abr', '?')}kbps {fmt.get('ext', '')}",
                    ext=fmt.get('ext', '')
                ))
        return formats
    
    def _get_subtitle_langs(self, info: Dict) -> List[SubtitleInfo]:
        """获取字幕语言列表"""
        subtitle_langs = []
        
        # 获取原始字幕
        if 'subtitles' in info:
            for lang_code, sub_info in info['subtitles'].items():
                if sub_info:
                    subtitle_langs.append(SubtitleInfo(
                        code=lang_code,
                        name=sub_info[0].get('name', lang_code)
                    ))
        
        # 获取自动生成的字幕（只保留英文和中文）
        if 'automatic_captions' in info:
            for lang_code, sub_info in info['automatic_captions'].items():
                if (lang_code in ['en', 'zh', 'zh-Hans', 'zh-Hant'] and 
                    sub_info and 
                    not any(s.code == lang_code for s in subtitle_langs)):
                    # 统一中文代码
                    if lang_code in ['zh-Hans', 'zh-Hant']:
                        lang_code = 'zh'
                    subtitle_langs.append(SubtitleInfo(
                        code=lang_code,
                        name=f"{sub_info[0].get('name', lang_code)} (自动生成)"
                    ))
        
        # 按语言代码排序
        subtitle_langs.sort(key=lambda x: x.code)
        return subtitle_langs
    
    def get_media_info(self, url: str) -> bool:
        """获取视频元数据"""
        try:
            if not url:
                raise ValueError("URL不能为空")
            
            if not self._validate_url(url):
                raise ValueError("无效的YouTube链接")
            
            # 创建临时选项，不包含postprocessors
            temp_opts = {k: v for k, v in self.ydl_opts.items() if k != 'postprocessors'}
            temp_opts['extract_flat'] = True
            
            with yt_dlp.YoutubeDL(temp_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise ValueError("无法获取视频信息")
                
                # 获取各种格式信息
                video_formats = self._get_video_formats(info)
                audio_formats = self._get_audio_formats(info)
                subtitle_langs = self._get_subtitle_langs(info)
                
                if not video_formats:
                    raise ValueError("未找到可用的视频格式")
                
                if not audio_formats:
                    raise ValueError("未找到可用的音频格式")
                
                # 发送信号
                self.signals.info_loaded.emit(
                    [vars(f) for f in video_formats],
                    [vars(f) for f in audio_formats],
                    [vars(s) for s in subtitle_langs]
                )
                return True
                
        except Exception as e:
            error_msg = f"获取视频信息失败: {str(e)}\n{traceback.format_exc()}"
            self.signals.error_occurred.emit(error_msg)
            return False
    
    def _update_progress(self, current_percent: float) -> float:
        """更新进度显示 - 直接返回实际进度，不再进行平滑处理"""
        self.current_percent = current_percent if not self.is_merging else min(current_percent * 0.9 + 90, 100)
        self.display_percent = self.current_percent
        return self.display_percent

    def _progress_hook(self, d: Dict) -> None:
        """进度回调函数"""
        try:
            # 检查是否已取消
            if self.is_canceled:
                raise Exception("下载已取消")
                
            if d['status'] == 'downloading':
                # 获取下载信息
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                speed = d.get('speed', 0)
                
                # 打印命令行进度信息
                if total and downloaded:
                    percent = (downloaded / total) * 100
                    speed_str = f"{speed/1024/1024:.2f} MB/s" if speed else "计算中..."
                    print(f"\r下载进度: {percent:.1f}% | 速度: {speed_str} | {downloaded/(1024*1024):.1f}MB/{total/(1024*1024):.1f}MB", end="", flush=True)
                
                if total and downloaded:
                    # 计算实际进度百分比
                    current_percent = (downloaded / total) * 100
                    
                    # 获取真实进度（不再平滑处理）
                    real_percent = self._update_progress(current_percent)
                    
                    # 格式化速度显示
                    if speed:
                        speed_str = f"{speed/1024/1024:.2f} MB/s"
                    else:
                        speed_str = self.last_speed
                    
                    # 更新上一次的速度
                    self.last_speed = speed_str
                    
                    # 发送进度更新信号
                    self.signals.progress_updated.emit(real_percent, speed_str)
                    
            elif d['status'] == 'finished':
                # 打印换行以结束进度显示
                print("\n文件下载完成，开始处理...")
                
                # 标记开始合并阶段
                self.is_merging = True
                # 从90%开始处理合并阶段
                self.current_percent = 90
                self.signals.progress_updated.emit(90, "处理中...")
                
            elif d['status'] == 'error':
                error_msg = d.get('error', '下载出错')
                self.signals.error_occurred.emit(error_msg)
                
        except Exception as e:
            error_msg = f"更新进度失败: {str(e)}\n{traceback.format_exc()}"
            self.signals.error_occurred.emit(error_msg)

    def cancel_download(self):
        """取消下载 - 强制终止下载进程"""
        global YDL_INSTANCE
        
        self.is_canceled = True
        print("\n正在终止下载进程...")
        
        # 终止下载进程
        if YDL_INSTANCE:
            try:
                # 对于Windows系统
                if os.name == 'nt':
                    # 创建终止线程
                    def terminator():
                        time.sleep(0.5)  # 稍等片刻让UI响应
                        os._exit(1)  # 强制终止进程
                    
                    threading.Thread(target=terminator, daemon=True).start()
                # 对于类Unix系统
                else:
                    os.kill(os.getpid(), signal.SIGINT)
            except:
                pass
        
        # 通知UI取消完成
        self.signals.error_occurred.emit("下载已取消")

    def download_subtitles(self, url: str, subtitle_lang: Optional[str] = None) -> bool:
        """下载字幕"""
        try:
            if not subtitle_lang:
                return True

            # 获取视频信息以获取标题
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError("无法获取视频信息")
                
                # 创建视频标题对应的文件夹路径
                video_title = info.get('title', 'video')
                # 清理标题中的非法字符
                video_title = re.sub(r'[\\/*?:"<>|]', "", video_title)
                video_dir = os.path.join(self.save_dir, video_title)
                
                # 确保文件夹存在
                os.makedirs(video_dir, exist_ok=True)
                
                # 设置字幕下载选项
                subtitle_opts = self.ydl_opts.copy()
                subtitle_opts.update({
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': [subtitle_lang],
                    'skip_download': True,  # 跳过视频下载
                    'outtmpl': {
                        'default': os.path.join(video_dir, '%(title)s.%(ext)s')
                    }
                })
                
                # 下载字幕
                with yt_dlp.YoutubeDL(subtitle_opts) as ydl:
                    ydl.download([url])
                
                return True
                
        except Exception as e:
            error_msg = f"下载字幕失败: {str(e)}\n{traceback.format_exc()}"
            self.signals.error_occurred.emit(error_msg)
            return False

    def download(self, url: str, video_fmt: str, audio_fmt: str, subtitle_lang: Optional[str] = None) -> bool:
        """下载视频"""
        try:
            if self.is_canceled:
                return False
                
            self.download_started = False
            self.current_percent = 0
            self.display_percent = 0
            self.last_speed = "0.00 MB/s"
            self.last_update_time = 0
            self.is_merging = False
            
            # 获取视频信息
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError("无法获取视频信息")
                
                # 创建视频标题对应的文件夹
                video_title = info.get('title', 'video')
                # 清理标题中的非法字符
                video_title = re.sub(r'[\\/*?:"<>|]', "", video_title)
                video_dir = os.path.join(self.save_dir, video_title)
                os.makedirs(video_dir, exist_ok=True)
                
                # 更新下载选项中的输出路径
                self.ydl_opts['outtmpl'] = {
                    'default': os.path.join(video_dir, '%(title)s.%(ext)s')
                }
                
                # 设置下载格式
                self.ydl_opts['format'] = f'{video_fmt}+{audio_fmt}/best'
                
                # 下载视频
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    ydl.download([url])
                
                # 下载字幕
                if subtitle_lang:
                    self.download_subtitles(url, subtitle_lang)
                
                # 发送完成信号
                self.signals.download_finished.emit("下载完成")
                
                # 打开下载文件夹
                self._open_download_folder()
                
                return True
                
        except Exception as e:
            error_msg = f"下载失败: {str(e)}\n{traceback.format_exc()}"
            self.signals.error_occurred.emit(error_msg)
            return False

    def _open_download_folder(self):
        """打开下载文件所在目录"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.save_dir)
            elif os.name == 'posix':  # macOS 和 Linux
                if os.path.exists('/usr/bin/xdg-open'):  # Linux
                    subprocess.run(['xdg-open', self.save_dir])
                else:  # macOS
                    subprocess.run(['open', self.save_dir])
        except Exception as e:
            self.signals.error_occurred.emit(f"无法打开下载目录: {str(e)}")

    def _merge_av(self, video_path, audio_path, title):
        """合并音视频文件"""
        try:
            if not os.path.exists(video_path) or not os.path.exists(audio_path):
                raise FileNotFoundError("视频或音频文件不存在")
                
            # 清理非法字符
            clean_title = re.sub(r'[\\/*?:"<>|]', "", title)
            output_path = os.path.join(self.save_dir, f"{clean_title}.mp4")
            
            video_clip = VideoFileClip(video_path)
            audio_clip = AudioFileClip(audio_path)
            
            # 对齐时长
            final_duration = min(video_clip.duration, audio_clip.duration)
            final_clip = video_clip.subclip(0, final_duration)
            final_clip = final_clip.set_audio(audio_clip.subclip(0, final_duration))
            
            # 多线程渲染
            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                threads=4,
                logger=None,
                ffmpeg_params=['-preset', 'fast']
            )
            
            return output_path
            
        except Exception as e:
            error_msg = f"合并音视频失败: {str(e)}\n{traceback.format_exc()}"
            self.signals.error_occurred.emit(error_msg)
            return None

    def _get_elapsed_time(self):
        """获取精确计时"""
        return self.start_time.elapsed() / 1000

    def merge_subtitles(self, video_path, subtitle_path, output_path):
        try:
            if not os.path.exists(video_path) or not os.path.exists(subtitle_path):
                raise FileNotFoundError("视频或字幕文件不存在")
                
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', subtitle_path,
                '-c:v', 'copy',
                '-c:a', 'copy',
                '-c:s', 'mov_text',
                output_path
            ]
            
            subprocess.run(cmd, check=True)
            return True
            
        except Exception as e:
            error_msg = f"合并字幕失败: {str(e)}\n{traceback.format_exc()}"
            self.signals.error_occurred.emit(error_msg)
            return False

    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            for file in os.listdir(self.save_dir):
                file_path = os.path.join(self.save_dir, file)
                # 删除除了.mp4和.srt以外的文件
                if os.path.isfile(file_path) and not file.endswith(('.mp4', '.srt')):
                    try:
                        os.remove(file_path)
                    except:
                        pass
        except Exception:
            pass  # 忽略清理过程中的错误