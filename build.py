import os
import sys
import subprocess
import shutil
import time
import logging
import json
from datetime import datetime
from pathlib import Path
import traceback

class BuildLogger:
    """构建日志管理器"""
    def __init__(self):
        self.logs_dir = Path('logs')
        self.builds_dir = self.logs_dir / 'builds'
        self.errors_dir = self.logs_dir / 'errors'
        self.stats_dir = self.logs_dir / 'stats'
        
        # 创建必要的目录
        for dir_path in [self.logs_dir, self.builds_dir, self.errors_dir, self.stats_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # 生成时间戳
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 设置日志文件路径
        self.log_file = self.builds_dir / f'build_{self.timestamp}.log'
        self.error_file = self.errors_dir / f'error_{self.timestamp}.json'
        self.stats_file = self.stats_dir / f'stats_{self.timestamp}.json'
        
        # 初始化统计数据
        self.stats = {
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'duration': None,
            'status': 'running',
            'errors': [],
            'warnings': [],
            'dependencies': {
                'installed': [],
                'missing': []
            },
            'file_operations': [],
            'build_info': {
                'python_version': None,
                'pyinstaller_version': None,
                'exe_size': None,
                'exe_path': None
            }
        }
        
        # 配置日志
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.DEBUG,  # 改为 DEBUG 级别以获取更多信息
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def log_error(self, error_msg, error_type=None, details=None):
        """记录错误"""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type or 'unknown',
            'message': error_msg,
            'details': details
        }
        self.stats['errors'].append(error_data)
        logging.error(f"{error_type or 'ERROR'}: {error_msg}")
        if details:
            logging.error(f"详细信息: {details}")
    
    def log_warning(self, warning_msg, warning_type=None):
        """记录警告"""
        warning_data = {
            'timestamp': datetime.now().isoformat(),
            'type': warning_type or 'unknown',
            'message': warning_msg
        }
        self.stats['warnings'].append(warning_data)
        logging.warning(f"{warning_type or 'WARNING'}: {warning_msg}")
    
    def log_dependency(self, package, status):
        """记录依赖状态"""
        if status == 'installed':
            self.stats['dependencies']['installed'].append(package)
        else:
            self.stats['dependencies']['missing'].append(package)
    
    def log_file_operation(self, operation, path, status, details=None):
        """记录文件操作"""
        operation_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'path': str(path),
            'status': status,
            'details': details
        }
        self.stats['file_operations'].append(operation_data)
    
    def update_build_info(self, **kwargs):
        """更新构建信息"""
        self.stats['build_info'].update(kwargs)
    
    def finalize(self, success=True):
        """完成日志记录"""
        self.stats['end_time'] = datetime.now().isoformat()
        self.stats['duration'] = round(
            (datetime.fromisoformat(self.stats['end_time']) - 
             datetime.fromisoformat(self.stats['start_time'])).total_seconds(),
            2
        )
        self.stats['status'] = 'success' if success else 'failed'
        
        # 保存统计数据
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        # 如果有错误，保存错误信息
        if self.stats['errors']:
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats['errors'], f, ensure_ascii=False, indent=2)
        
        return self.stats

    def install_pyinstaller(self, max_retries=3):
        """安装 PyInstaller，带重试机制"""
        for attempt in range(max_retries):
            try:
                # 先尝试升级 pip
                self.log_file_operation('command', 'pip upgrade', 'started')
                subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                             check=True, capture_output=True, text=True)
                
                # 尝试安装 PyInstaller
                self.log_file_operation('command', 'pip install pyinstaller', 'started')
                result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'],
                                     check=True, capture_output=True, text=True)
                
                # 验证安装
                version = subprocess.check_output([sys.executable, '-m', 'PyInstaller', '--version'],
                                               stderr=subprocess.STDOUT).decode().strip()
                self.update_build_info(pyinstaller_version=version)
                self.log_file_operation('command', 'pip install pyinstaller', 'success', 
                                      {'version': version})
                return True
                
            except subprocess.CalledProcessError as e:
                error_msg = f"安装失败 (尝试 {attempt + 1}/{max_retries}): {e.stderr or e.stdout}"
                self.log_error(error_msg, 'pyinstaller_installation_error', {
                    'attempt': attempt + 1,
                    'max_retries': max_retries,
                    'error_output': e.stderr or e.stdout
                })
                
                if attempt < max_retries - 1:
                    self.log_warning(f"等待 5 秒后重试...", 'retry_waiting')
                    time.sleep(5)
                continue
                
            except Exception as e:
                self.log_error(str(e), 'unexpected_error', traceback.format_exc())
                return False
        
        return False

def run_command(command, logger):
    """运行命令并记录输出"""
    logger.log_file_operation('command', command, 'started')
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,  # 分开捕获 stderr
        universal_newlines=True,
        shell=True
    )
    
    output = []
    error_output = []
    
    # 使用 select 来同时读取 stdout 和 stderr
    while True:
        # 读取 stdout
        line = process.stdout.readline()
        if line:
            print(line, end='', flush=True)  # 添加 flush=True 确保实时输出
            output.append(line.strip())
            logging.debug(line.strip())  # 使用 debug 级别记录详细输出
        
        # 读取 stderr
        err_line = process.stderr.readline()
        if err_line:
            print(err_line, end='', flush=True, file=sys.stderr)  # 输出到 stderr
            error_output.append(err_line.strip())
            logging.warning(err_line.strip())  # 使用 warning 级别记录错误输出
        
        # 检查进程是否结束
        if line == '' and err_line == '' and process.poll() is not None:
            break
    
    process.wait()
    status = 'success' if process.returncode == 0 else 'failed'
    logger.log_file_operation('command', command, status, {
        'return_code': process.returncode,
        'output': output,
        'error_output': error_output
    })
    return process.returncode

def check_requirements(logger):
    """检查必要的依赖"""
    required_packages = ['PyQt6', 'yt-dlp', 'pytubefix', 'moviepy']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.log_dependency(package, 'installed')
            logging.info(f"已安装: {package}")
        except ImportError:
            missing_packages.append(package)
            logger.log_dependency(package, 'missing')
            logger.log_warning(f"未安装: {package}", 'dependency_missing')
    
    return missing_packages

def main():
    logger = BuildLogger()
    success = False
    
    try:
        logging.info("=" * 50)
        logging.info("开始构建 yt-dd...")
        logging.info("=" * 50)
        
        # 检查Python环境
        if run_command("python --version", logger) != 0:
            logger.log_error("未找到Python", "environment_error", 
                           "请确保已安装Python并添加到PATH中")
            return
        
        # 获取Python版本
        python_version = subprocess.check_output("python --version", shell=True).decode().strip()
        logger.update_build_info(python_version=python_version)
        
        # 检查必要的依赖
        logging.info("检查必要的依赖...")
        missing_packages = check_requirements(logger)
        if missing_packages:
            logger.log_warning(f"缺少以下依赖: {', '.join(missing_packages)}", 'dependencies_missing')
            logging.info("正在安装依赖...")
            if run_command("pip install -r requirements.txt", logger) != 0:
                logger.log_error("安装依赖失败", "dependency_installation_error")
                return
        
        # 安装PyInstaller
        logging.info("检查PyInstaller...")
        if not logger.install_pyinstaller():
            logger.log_error("安装PyInstaller失败，请检查网络连接或手动安装", 
                           "pyinstaller_installation_error")
            return
        
        # 清理旧的构建文件
        logging.info("清理旧的构建文件...")
        for path in ['build', 'dist']:
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                    logger.log_file_operation('delete', path, 'success')
                    logging.info(f"已删除: {path}")
                except Exception as e:
                    logger.log_file_operation('delete', path, 'failed', str(e))
                    logger.log_warning(f"无法删除 {path}: {str(e)}", 'file_operation_error')
        
        # 使用PyInstaller打包应用
        logging.info("正在打包应用程序...")
        print("\n" + "=" * 50)
        print("开始打包 yt-dd")
        print("=" * 50)
        print("打包过程包括以下步骤：")
        print("1. 收集依赖文件")
        print("2. 编译Python代码")
        print("3. 打包资源文件")
        print("4. 创建可执行文件")
        print("=" * 50)
        
        # 记录开始时间
        build_start_time = time.time()
        
        pyinstaller_cmd = (
            f'{sys.executable} -m PyInstaller --clean --noconfirm '
            '--name "yt-dd" '
            '--windowed '
            '--icon "assets/icon-256-256.ico" '
            '--add-data "assets;assets" '
            '--add-data "config;config" '
            '--hidden-import "PyQt6" '
            '--hidden-import "yt_dlp" '
            '--hidden-import "pytubefix" '
            '--hidden-import "moviepy" '
            '--log-level DEBUG '  # 使用 DEBUG 级别获取更多信息
            '"main.py"'
        )
        
        try:
            print("\n正在执行 PyInstaller 命令：")
            print(f"{pyinstaller_cmd}\n")
            print("=" * 50)
            print("开始构建过程，下面是实时日志输出：")
            print("=" * 50)
            
            # 添加日志文件输出
            log_out_path = os.path.join('logs', f'pyinstaller_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            log_dir = os.path.dirname(log_out_path)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # 使用这种方式可以直接在控制台输出
            with open(log_out_path, 'w', encoding='utf-8') as log_file:
                process = subprocess.Popen(
                    pyinstaller_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                )
                
                print(f"[INFO] 正在构建，完整日志将保存到: {log_out_path}")
                
                for line in iter(process.stdout.readline, ''):
                    print(line.rstrip())
                    log_file.write(line)
                    log_file.flush()
                    
                process.stdout.close()
                return_code = process.wait()
            
            # 计算总用时
            build_end_time = time.time()
            build_duration = build_end_time - build_start_time
            minutes = int(build_duration // 60)
            seconds = int(build_duration % 60)
            
            print("\n" + "=" * 50)
            print(f"PyInstaller 进程已结束，返回码: {return_code}")
            print(f"总用时: {minutes}分{seconds}秒")
            print(f"完整日志位置: {os.path.abspath(log_out_path)}")
            print("=" * 50)
            
            if return_code != 0:
                error_msg = f"PyInstaller打包失败 (返回码: {return_code})"
                logger.log_error(error_msg, "build_error", {
                    'return_code': return_code,
                    'build_duration': build_duration,
                    'log_file': os.path.abspath(log_out_path)
                })
                return
                
        except Exception as e:
            logger.log_error(str(e), "build_error", traceback.format_exc())
            return
        
        # 检查生成的文件
        exe_path = os.path.join('dist', 'yt-dd', 'yt-dd.exe')
        if os.path.exists(exe_path):
            file_size = round(os.path.getsize(exe_path) / (1024*1024), 2)
            logger.update_build_info(
                exe_size=f"{file_size} MB",
                exe_path=os.path.abspath(exe_path)
            )
            logging.info(f"可执行文件大小: {file_size} MB")
            logging.info(f"可执行文件位置: {os.path.abspath(exe_path)}")
        else:
            logger.log_error("未找到生成的可执行文件", "file_not_found")
        
        success = True
        
    except Exception as e:
        logger.log_error(str(e), "unexpected_error", traceback.format_exc())
    
    finally:
        # 完成日志记录
        stats = logger.finalize(success)
        
        # 显示结果
        print("\n" + "=" * 50)
        print(f"打包{'成功' if success else '失败'}！")
        if success:
            print(f"可执行文件位于: {stats['build_info']['exe_path']}")
        print(f"构建日志位于: {logger.log_file}")
        if stats['errors']:
            print(f"错误日志位于: {logger.error_file}")
        print(f"构建统计位于: {logger.stats_file}")
        print("=" * 50)
        
        input("\n按回车键退出...")

if __name__ == "__main__":
    main() 