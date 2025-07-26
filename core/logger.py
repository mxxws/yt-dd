import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

class Logger:
    """统一日志管理器"""
    
    # 日志级别映射
    LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    
    # 单例实例
    _instance = None
    
    @classmethod
    def get_instance(cls, log_dir: Optional[str] = None, 
                    log_level: str = "info", 
                    console_output: bool = True) -> 'Logger':
        """获取Logger单例实例"""
        if cls._instance is None:
            cls._instance = cls(log_dir, log_level, console_output)
        return cls._instance
    
    def __init__(self, log_dir: Optional[str] = None, 
                 log_level: str = "info", 
                 console_output: bool = True):
        """初始化日志管理器
        
        Args:
            log_dir: 日志目录，默认为应用根目录下的logs文件夹
            log_level: 日志级别，可选值：debug, info, warning, error, critical
            console_output: 是否输出到控制台
        """
        # 设置日志目录
        if log_dir is None:
            # 默认在应用根目录下创建logs文件夹
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.log_dir = os.path.join(app_root, "logs")
        else:
            self.log_dir = log_dir
            
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 设置日志级别
        self.log_level = self.LEVELS.get(log_level.lower(), logging.INFO)
        
        # 设置是否输出到控制台
        self.console_output = console_output
        
        # 创建日志记录器
        self.logger = logging.getLogger("yt-dd")
        self.logger.setLevel(self.log_level)
        self.logger.propagate = False  # 避免日志重复
        
        # 清除现有处理器
        for handler in self.logger.handlers[:]:  
            self.logger.removeHandler(handler)
        
        # 添加文件处理器
        self._add_file_handler()
        
        # 添加控制台处理器
        if self.console_output:
            self._add_console_handler()
            
        # 记录启动信息
        self.logger.info(f"日志系统初始化完成，日志级别：{log_level}，日志目录：{self.log_dir}")
    
    def _add_file_handler(self):
        """添加文件处理器"""
        # 生成日志文件名，格式：yt-dd_YYYYMMDD.log
        today = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(self.log_dir, f"yt-dd_{today}.log")
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(self.log_level)
        
        # 设置日志格式
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        
        # 添加到日志记录器
        self.logger.addHandler(file_handler)
    
    def _add_console_handler(self):
        """添加控制台处理器"""
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        
        # 设置日志格式
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] - %(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        
        # 添加到日志记录器
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str, *args, **kwargs):
        """记录调试日志"""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """记录信息日志"""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """记录警告日志"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """记录错误日志"""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """记录严重错误日志"""
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, exc_info=True, **kwargs):
        """记录异常日志"""
        self.logger.exception(message, *args, exc_info=exc_info, **kwargs)
    
    def log_exception(self, e: Exception, message: Optional[str] = None):
        """记录异常详情
        
        Args:
            e: 异常对象
            message: 额外的错误信息
        """
        error_msg = f"{message + ': ' if message else ''}异常类型: {type(e).__name__}, 异常信息: {str(e)}"
        self.logger.error(error_msg)
        self.logger.error(f"异常堆栈: \n{traceback.format_exc()}")
        
        return error_msg

# 创建全局日志实例
log = Logger.get_instance()

# 提供便捷的全局函数
def debug(message: str, *args, **kwargs):
    log.debug(message, *args, **kwargs)

def info(message: str, *args, **kwargs):
    log.info(message, *args, **kwargs)

def warning(message: str, *args, **kwargs):
    log.warning(message, *args, **kwargs)

def error(message: str, *args, **kwargs):
    log.error(message, *args, **kwargs)

def critical(message: str, *args, **kwargs):
    log.critical(message, *args, **kwargs)

def exception(message: str, *args, exc_info=True, **kwargs):
    log.exception(message, *args, exc_info=exc_info, **kwargs)

def log_exception(e: Exception, message: Optional[str] = None):
    return log.log_exception(e, message)