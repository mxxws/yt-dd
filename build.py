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
                # 先检查是否已安装
                try:
                    version = subprocess.check_output(
                        [sys.executable, '-m', 'PyInstaller', '--version'],
                        stderr=subprocess.STDOUT
                    ).decode().strip()
                    print(f"✓ PyInstaller 已安装 (版本: {version})")
                    self.update_build_info(pyinstaller_version=version)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print(f"⚠ PyInstaller 未安装或无法访问，正在安装... (尝试 {attempt+1}/{max_retries})")
                
                # 先尝试升级 pip
                print("【步骤 1/2】升级 pip...")
                self.log_file_operation('command', 'pip upgrade', 'started')
                upgrade_result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', 
                    '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'], 
                    check=True, capture_output=True, text=True
                )
                
                if upgrade_result.returncode == 0:
                    print("✓ pip 升级成功")
                else:
                    print("⚠ pip 升级失败，尝试继续安装 PyInstaller")
                
                # 尝试安装 PyInstaller
                print("【步骤 2/2】安装 PyInstaller...")
                self.log_file_operation('command', 'pip install pyinstaller', 'started')
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', 'pyinstaller',
                    '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'],
                    check=True, capture_output=True, text=True
                )
                
                # 验证安装
                version = subprocess.check_output(
                    [sys.executable, '-m', 'PyInstaller', '--version'],
                    stderr=subprocess.STDOUT
                ).decode().strip()
                
                self.update_build_info(pyinstaller_version=version)
                self.log_file_operation('command', 'pip install pyinstaller', 'success', 
                                      {'version': version})
                print(f"✓ PyInstaller 安装成功 (版本: {version})")
                return True
                
            except subprocess.CalledProcessError as e:
                error_msg = f"安装失败 (尝试 {attempt + 1}/{max_retries}): {e.stderr or e.stdout}"
                self.log_error(error_msg, 'pyinstaller_installation_error', {
                    'attempt': attempt + 1,
                    'max_retries': max_retries,
                    'error_output': e.stderr or e.stdout
                })
                print(f"✗ 安装失败 (尝试 {attempt + 1}/{max_retries})")
                print(f"错误信息: {e.stderr or e.stdout}")
                
                if attempt < max_retries - 1:
                    wait_time = 5
                    self.log_warning(f"等待 {wait_time} 秒后重试...", 'retry_waiting')
                    print(f"⌛ 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                continue
                
            except Exception as e:
                self.log_error(str(e), 'unexpected_error', traceback.format_exc())
                print(f"✗ 安装过程出现未预期的错误: {str(e)}")
                return False
        
        print("✗ PyInstaller 安装失败，已达到最大重试次数")
        return False

def run_command(command, logger):
    """运行命令并记录输出"""
    logger.log_file_operation('command', command, 'started')
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,  # 分开捕获 stderr
        universal_newlines=True,
        bufsize=1,  # 行缓冲，可以提高实时性
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
        
        # 允许其他线程执行，提高UI响应性
        time.sleep(0.01)
    
    process.wait()
    status = 'success' if process.returncode == 0 else 'failed'
    logger.log_file_operation('command', command, status, {
        'return_code': process.returncode,
        'output': output,
        'error_output': error_output
    })
    return process.returncode

def check_requirements(logger):
    """检查必要的依赖，并验证版本一致性"""
    required_packages = ['PyQt6', 'yt-dlp', 'moviepy']
    missing_packages = []
    version_mismatch_packages = []
    
    # 读取 requirements.txt 中的版本信息
    req_versions = {}
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '==' in line:
                    package_name, version = line.split('==', 1)
                    req_versions[package_name] = version
    except Exception as e:
        print(f"读取 requirements.txt 失败: {str(e)}")
        logger.log_warning(f"读取 requirements.txt 失败: {str(e)}", 'requirements_read_error')
    
    for package in required_packages:
        try:
            module = __import__(package.replace('-', '_'))
            logger.log_dependency(package, 'installed')
            
            # 检查包版本是否与 requirements.txt 一致
            current_version = None
            if package == 'yt-dlp':
                try:
                    from yt_dlp.version import __version__ as current_version
                except Exception:
                    current_version = None
            else:
                try:
                    current_version = getattr(module, '__version__', None)
                except Exception:
                    current_version = None
            
            # 获取 requirements.txt 中的版本
            req_version = req_versions.get(package)
            
            if current_version and req_version:
                logging.info(f"{package} 版本: {current_version}, requirements.txt: {req_version}")
                print(f"{package} 版本: {current_version}, requirements.txt: {req_version}")
                
                if current_version != req_version:
                    print(f"⚠ 警告: {package} 版本不一致 - 当前: {current_version}, requirements.txt: {req_version}")
                    logger.log_warning(f"{package} 版本不一致 - 当前: {current_version}, requirements.txt: {req_version}", 'version_mismatch')
                    version_mismatch_packages.append((package, current_version, req_version))
            else:
                logging.info(f"已安装: {package}")
        except ImportError:
            missing_packages.append(package)
            logger.log_dependency(package, 'missing')
            logger.log_warning(f"未安装: {package}", 'dependency_missing')
    
    # 如果有版本不一致的包，提示用户运行 main.py 更新 requirements.txt
    if version_mismatch_packages:
        print("\n" + "=" * 70)
        print("【版本警告】检测到以下包的版本与 requirements.txt 不一致:")
        print("=" * 70)
        for package, current_version, req_version in version_mismatch_packages:
            print(f"  - {package}: 当前版本 {current_version}, requirements.txt 版本 {req_version}")
        print("\n请先运行 main.py 更新 requirements.txt 中的版本信息，再运行 build.py 进行打包。")
        print("这样可以确保打包时使用的依赖版本与运行环境一致，避免兼容性问题。")
        print("=" * 70)
    
    return missing_packages



def update_requirement_version(package_name, new_version):
    """更新 requirements.txt 文件中指定包的版本"""
    try:
        # 读取当前的 requirements.txt
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 更新指定包的版本
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{package_name}=="):
                lines[i] = f"{package_name}=={new_version}\n"
                updated = True
                break
        
        # 如果没有找到该包，则添加到文件末尾
        if not updated:
            lines.append(f"{package_name}=={new_version}\n")
        
        # 写回文件
        with open('requirements.txt', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return True
    except Exception as e:
        logging.error(f"更新 requirements.txt 中的 {package_name} 版本失败: {str(e)}")
        return False

def update_dependencies(logger):
    """检查依赖包版本，并提示用户使用 main.py 更新 requirements.txt"""
    logging.info("检查依赖包版本...")
    
    # 检查是否安装了 pip-review
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip_review', '--help'],
            check=True, capture_output=True, text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n" + "=" * 70)
        print("【工具安装】正在安装 pip-review...")
        print("=" * 70)
        try:
            install_result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', 'pip-review', 
                 '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'],
                check=True, capture_output=True, text=True
            )
            logger.log_file_operation('command', 'pip install pip-review', 'success')
            print("✓ pip-review 安装成功")
        except Exception as e:
            logger.log_error("安装 pip-review 失败", "tool_installation_error", str(e))
            print("✗ pip-review 安装失败")
            return False
    
    # 使用pip-review检查可更新的包
    try:
        print("\n" + "=" * 70)
        print("【依赖检查】正在检查依赖包版本...")
        print("=" * 70)
        
        logger.log_file_operation('command', 'pip-review --local', 'started')
        result = subprocess.run(
            [sys.executable, '-m', 'pip_review', '--local'],
            check=True, capture_output=True, text=True
        )
        outdated_packages = result.stdout.strip()
        
        if not outdated_packages or "All packages are up-to-date" in outdated_packages:
            print("✓ 所有依赖包均为最新版本，无需更新")
            logging.info("所有依赖包均为最新版本，无需更新")
            return True
            
        # 显示需要更新的包
        print("\n" + "=" * 70)
        print("【依赖检查】以下包有新版本可用:")
        print("=" * 70)
        
        update_table_header = f"{'包名':<20} {'当前版本':<15} {'最新版本':<15}"
        print(update_table_header)
        print("-" * 50)
        
        outdated_package_list = []
        
        # 解析需要更新的包信息
        for line in outdated_packages.splitlines():
            if " is available" in line:
                # 解析包名和版本
                try:
                    parts = line.split(" is available")
                    if len(parts) >= 1:
                        package_info = parts[0].strip()
                        package_parts = package_info.split()
                        package_name = package_parts[0]
                        
                        # 提取当前版本和可用版本
                        current_version = ""
                        latest_version = ""
                        
                        if len(package_parts) >= 2:
                            current_version = package_parts[1]
                        
                        if " (current: " in line and ")" in line:
                            version_part = line.split(" (current: ")[1].split(")")[0]
                            latest_version = version_part
                        
                        print(f"{package_name:<20} {current_version:<15} {latest_version:<15}")
                        outdated_package_list.append((package_name, current_version, latest_version))
                except Exception as e:
                    print(f"解析包信息失败: {str(e)}")
                    logger.log_warning(f"解析包信息失败: {str(e)}", 'parse_error')
        
        # 自动更新依赖包并同步到requirements.txt
        if outdated_package_list:
            print("\n" + "=" * 70)
            print("【自动更新】检测到有依赖包可以更新，正在自动更新...")
            print("=" * 70)
            
            # 导入依赖检查器
            try:
                # 添加项目根目录到sys.path
                project_root = os.path.dirname(os.path.abspath(__file__))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                
                from core.dependency_checker import DependencyChecker
                
                # 创建依赖检查器
                checker = DependencyChecker()
                
                # 自动更新所有已安装的包
                print("正在更新所有依赖包并同步到requirements.txt...")
                update_results = checker.update_all_packages()
                
                # 显示更新结果
                print("\n" + "=" * 70)
                print("【更新结果】依赖包更新完成")
                print("=" * 70)
                
                update_table_header = f"{'包名':<20} {'旧版本':<15} {'新版本':<15} {'状态':<10}"
                print(update_table_header)
                print("-" * 60)
                
                for package_name, info in update_results.items():
                    old_version = info.get('old_version', 'N/A')
                    new_version = info.get('new_version', 'N/A')
                    updated = info.get('updated', False)
                    status = "✓ 已更新" if updated else "- 无变化"
                    
                    print(f"{package_name:<20} {old_version:<15} {new_version:<15} {status:<10}")
                
                print("\n✓ 所有依赖包已更新，requirements.txt已同步")
                print("=" * 70)
                
            except Exception as e:
                print(f"\n✗ 自动更新依赖包失败: {str(e)}")
                logger.log_error(f"自动更新依赖包失败", "dependency_update_error", str(e))
                print("请手动运行 main.py 更新依赖包并同步requirements.txt")
                traceback.print_exc()
            
            return True
        
    except Exception as e:
        logger.log_error(f"检查依赖包版本失败: {str(e)}", "dependency_check_error")
        print(f"✗ 检查依赖包版本失败: {str(e)}")
        return False
        
    except subprocess.CalledProcessError as e:
        logger.log_error("依赖包检查失败", "dependency_check_error", e.stderr or e.stdout)
        print("\n✗ 依赖包检查失败")
        print(e.stderr or e.stdout)
        return False
    except Exception as e:
        logger.log_error(str(e), "dependency_update_error", traceback.format_exc())
        print(f"\n✗ 依赖更新过程出错: {str(e)}")
        return False

def setup_moviepy_dependencies(logger):
    """设置 moviepy 依赖"""
    print("\n" + "=" * 70)
    print("【依赖设置】设置 moviepy 依赖...")
    print("=" * 70)
    
    # 验证 moviepy 是否可用
    try:
        import moviepy
        moviepy_version = getattr(moviepy, "__version__", "未知版本")
        print(f"当前安装的 moviepy 版本: {moviepy_version}")
        
        # 检查 moviepy 包结构
        has_editor = hasattr(moviepy, "editor")
        has_video = hasattr(moviepy, "video")
        has_audio = hasattr(moviepy, "audio")
        
        print(f"包结构检查: editor模块存在: {has_editor}, video模块存在: {has_video}, audio模块存在: {has_audio}")
        
        if has_editor and has_video and has_audio:
            print("✓ moviepy 依赖检查通过")
            return True
        else:
            print("⚠ moviepy 包结构不完整，但将继续构建过程")
            logger.log_warning("moviepy 包结构不完整，可能影响某些功能", "dependency_warning")
            return True
    except ImportError:
        print("✗ 无法导入 moviepy 包，请确保已安装")
        logger.log_error("无法导入 moviepy 包", "dependency_error")
        return False
    except Exception as e:
        print(f"✗ 检查 moviepy 依赖时出错: {str(e)}")
        logger.log_error(f"检查 moviepy 依赖时出错: {str(e)}", "dependency_error")
        return False

def test_executable(exe_path, logger):
    """测试打包后的可执行文件"""
    print("\n" + "=" * 70)
    print("【测试】正在测试打包后的程序...")
    print("=" * 70)
    
    try:
        # 创建一个子进程运行打包后的程序
        print(f"正在启动: {exe_path}")
        
        # 使用 subprocess 启动应用程序，并等待几秒钟检查是否崩溃
        process = subprocess.Popen(exe_path)
        
        # 等待 5 秒检查程序是否正常运行
        print("等待 5 秒钟检查程序是否正常启动...")
        for i in range(5, 0, -1):
            print(f"⏰ {i}...", end="\r")
            time.sleep(1)
            
            # 检查进程是否仍在运行
            if process.poll() is not None:
                # 仅当返回码不为0时才视为失败
                if process.returncode != 0:
                    print(f"\n✗ 程序启动后异常退出，返回码: {process.returncode}")
                    logger.log_error(f"程序测试失败，返回码: {process.returncode}", "test_error")
                    return False
                else:
                    print(f"\n⚠ 程序正常退出，返回码: {process.returncode}")
                    logger.log_warning(f"程序短暂运行后退出，返回码: {process.returncode}", "test_warning")
                    return True
        
        print("\n✓ 程序已成功启动并持续运行超过 5 秒钟")
        
        # 询问是否关闭测试程序
        print("\n测试继续进行中，请尝试程序功能...")
        user_input = input("是否关闭测试程序? (y/n): ").strip().lower()
        
        if user_input == 'y':
            # 尝试正常终止进程
            process.terminate()
            try:
                process.wait(timeout=3)
                print("✓ 程序已正常关闭")
            except subprocess.TimeoutExpired:
                # 如果超时，则强制结束进程
                process.kill()
                print("⚠ 程序未响应，已强制关闭")
        else:
            print("✓ 测试程序将继续在后台运行")
            
        return True
        
    except Exception as e:
        print(f"✗ 测试过程出错: {str(e)}")
        logger.log_error(f"测试可执行文件时出错: {str(e)}", "test_error")
        return False

def main():
    logger = BuildLogger()
    success = False
    
    try:
        print("\n" + "=" * 70)
        print("                     开始构建 yt-dd 应用程序")
        print("=" * 70)
        
        # 检查Python环境
        print("\n【环境检查】检查 Python 环境...")
        if run_command("python --version", logger) != 0:
            logger.log_error("未找到Python", "environment_error", 
                           "请确保已安装Python并添加到PATH中")
            print("✗ Python 环境检查失败！请确保已安装 Python 并添加到 PATH 中")
            return
        
        # 获取Python版本
        python_version = subprocess.check_output("python --version", shell=True).decode().strip()
        logger.update_build_info(python_version=python_version)
        print(f"✓ Python 环境检查通过! ({python_version})")
        
        # 检查必要的依赖
        print("\n" + "=" * 70)
        print("【依赖检查】检查必要的依赖包...")
        print("=" * 70)
        
        required_packages = ['PyQt6', 'yt-dlp', 'pytubefix', 'moviepy']
        print(f"必要依赖包: {', '.join(required_packages)}")
        print("-" * 70)
        
        missing_packages = check_requirements(logger)
        if missing_packages:
            logger.log_warning(f"缺少以下必要依赖: {', '.join(missing_packages)}", 'dependencies_missing')
            
            print("\n" + "=" * 70)
            print(f"【依赖安装】正在安装 {len(missing_packages)} 个缺失的依赖包...")
            print("=" * 70)
            
            # 创建表格标题
            print(f"{'包名':<20} {'状态':<10}")
            print("-" * 30)
            
            # 使用清华源安装缺失的依赖
            for package in missing_packages:
                print(f"{package:<20} {'安装中...':<10}", end="\r")
                result = run_command(f"pip install {package} -i https://pypi.tuna.tsinghua.edu.cn/simple", logger)
                
                if result == 0:
                    print(f"{package:<20} {'✓ 成功':<10}")
                    
                    # 如果安装的是 yt-dlp，提示用户运行 main.py 更新 requirements.txt
                    if package == 'yt-dlp':
                        try:
                            # 获取当前版本
                            import yt_dlp.version
                            from yt_dlp.version import __version__ as yt_dlp_version
                            print(f"已安装 yt-dlp 版本: {yt_dlp_version}")
                            print("⚠ 注意: 请在安装完成后运行 main.py 以同步更新 requirements.txt 中的版本信息")
                            logger.log_warning("请运行 main.py 同步更新 requirements.txt 中的版本信息", 'version_sync_reminder')
                        except ImportError:
                            print("⚠ 无法导入 yt_dlp.version 模块")
                            logger.log_warning("无法导入 yt_dlp.version 模块", 'import_error')
                else:
                    print(f"{package:<20} {'✗ 失败':<10}")
                    logger.log_error(f"安装依赖 {package} 失败", "dependency_installation_error")
                    return
            
            print("-" * 30)
            print(f"✓ 所有缺失依赖安装完成")
        else:
            print("✓ 所有必要依赖已安装")
            
        # 验证 moviepy 依赖
        if not setup_moviepy_dependencies(logger):
            print("警告: moviepy 依赖验证失败，但将继续构建过程")
            logger.log_warning("moviepy 依赖验证失败", "dependency_warning")
        
        # 检查依赖包版本
        print("\n" + "=" * 70)
        print("【依赖检查】检查依赖包版本...")
        print("=" * 70)
        
        update_dependencies(logger)
        
        # 提示用户确认是否继续
        print("\n" + "=" * 70)
        print("【确认】是否继续构建过程?")
        print("=" * 70)
        print("如果上面显示有依赖包版本不一致，建议先运行 main.py 更新 requirements.txt 后再构建")
        confirm = input("是否继续构建? (y/n): ").strip().lower()
        if confirm != 'y':
            print("构建过程已取消")
            return
        
        # 安装PyInstaller
        print("\n" + "=" * 70)
        print("【环境准备】检查 PyInstaller...")
        print("=" * 70)
        if not logger.install_pyinstaller():
            logger.log_error("安装PyInstaller失败，请检查网络连接或手动安装", 
                           "pyinstaller_installation_error")
            return
        
        # 清理旧的构建文件
        print("\n" + "=" * 70)
        print("【清理】清理旧的构建文件...")
        print("=" * 70)
        
        for path in ['build', 'dist']:
            if os.path.exists(path):
                try:
                    print(f"正在删除: {path} 目录...", end="\r")
                    shutil.rmtree(path)
                    logger.log_file_operation('delete', path, 'success')
                    print(f"✓ 已成功删除: {path:<10}")
                except Exception as e:
                    logger.log_file_operation('delete', path, 'failed', str(e))
                    logger.log_warning(f"无法删除 {path}: {str(e)}", 'file_operation_error')
                    print(f"✗ 无法删除 {path}: {str(e)}")
            else:
                print(f"ℹ {path} 目录不存在，无需清理")
        
        # 使用PyInstaller打包应用
        print("\n" + "=" * 70)
        print("               【打包】正在打包应用程序...")
        print("=" * 70)
        print("\n📋 打包过程包括以下步骤：")
        print("  1. 收集依赖文件")
        print("  2. 编译Python代码")
        print("  3. 打包资源文件")
        print("  4. 创建可执行文件")
        print("\n⌛ 打包过程可能需要几分钟时间，请耐心等待...\n")
        
        # 记录开始时间
        build_start_time = time.time()
        
        # 构建命令并显示
        pyinstaller_cmd = (
            f'{sys.executable} -m PyInstaller --clean --noconfirm --onefile '
            '--name "yt-dd" '
            '--windowed '
            '--icon "assets/icon-256-256.ico" '
            '--add-data "assets;assets" '
            '--add-data "config;config" '
            '--hidden-import "PyQt6" '
            '--hidden-import "PyQt6.QtCore" '
            '--hidden-import "PyQt6.QtGui" '
            '--hidden-import "PyQt6.QtWidgets" '
            '--hidden-import "yt_dlp" '
            '--hidden-import "pytubefix" '
            '--hidden-import "moviepy" '
            '--hidden-import "moviepy.editor" '
            '--hidden-import "moviepy.video.io.ffmpeg_tools" '
            '--hidden-import "moviepy.video.VideoClip" '
            '--hidden-import "moviepy.video.io.VideoFileClip" '
            '--hidden-import "moviepy.audio.io.AudioFileClip" '
            '--hidden-import "moviepy.audio.AudioClip" '
            '--hidden-import "moviepy.video.compositing.CompositeVideoClip" '
            '--hidden-import "moviepy.video.compositing.concatenate" '
            '--hidden-import "imageio" '
            '--hidden-import "imageio.plugins" '
            '--hidden-import "imageio.plugins.ffmpeg" '
            '--hidden-import "tqdm" '
            '--hidden-import "proglog" '
            '--hidden-import "decorator" '
            '--collect-submodules "moviepy" '  # 收集所有子模块
            '--collect-data "moviepy" '  # 收集所有数据文件
            '--log-level DEBUG '  # 使用 DEBUG 级别获取更多信息
            '"main.py"'
        )
        
        print("=" * 70)
        print("【执行命令】")
        print(f"{pyinstaller_cmd}")
        print("=" * 70 + "\n")
        
        try:
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
                
                print(f"⏳ 正在构建，完整日志将保存到: {log_out_path}")
                print("\n--- 构建日志开始 ---\n")
                
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
            
            print("\n--- 构建日志结束 ---\n")
            
            print("\n" + "=" * 70)
            print("【构建结果】")
            print("=" * 70)
            print(f"返回码: {return_code} {'(成功)' if return_code == 0 else '(失败)'}")
            print(f"总用时: {minutes}分{seconds}秒")
            print(f"完整日志位置: {os.path.abspath(log_out_path)}")
            print("=" * 70)
            
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
            print(f"\n✗ 构建过程出现异常: {str(e)}")
            return
        
        # 检查生成的文件
        print("\n" + "=" * 70)
        print("【检查结果】")
        print("=" * 70)
        
        exe_path = os.path.join('dist', 'yt-dd.exe')
        if os.path.exists(exe_path):
            file_size = round(os.path.getsize(exe_path) / (1024*1024), 2)
            logger.update_build_info(
                exe_size=f"{file_size} MB",
                exe_path=os.path.abspath(exe_path)
            )
            print(f"✅ 构建成功!")
            print(f"📦 可执行文件大小: {file_size} MB")
            print(f"📁 可执行文件位置: {os.path.abspath(exe_path)}")
            
            # 询问是否立即测试可执行文件
            user_input = input("\n是否立即测试生成的可执行文件? (y/n): ").strip().lower()
            if user_input == 'y':
                test_executable(os.path.abspath(exe_path), logger)
            
        else:
            logger.log_error("未找到生成的可执行文件", "file_not_found")
            print("❌ 未找到生成的可执行文件!")
        
        success = True
        
    except Exception as e:
        logger.log_error(str(e), "unexpected_error", traceback.format_exc())
        print(f"\n❌ 构建过程出现未预期的错误: {str(e)}")
    
    finally:
        # 完成日志记录
        stats = logger.finalize(success)
        
        # 显示结果
        print("\n" + "=" * 70)
        print("【构建摘要】")
        print("=" * 70)
        if success:
            print(f"✅ 打包成功！")
            print(f"📁 可执行文件位于: {stats['build_info']['exe_path']}")
        else:
            print(f"❌ 打包失败！")
        
        print(f"📝 构建日志位于: {logger.log_file}")
        if stats['errors']:
            print(f"⚠️ 错误日志位于: {logger.error_file}")
        print(f"📊 构建统计位于: {logger.stats_file}")
        print("=" * 70)
        
        print("\n感谢使用 yt-dd 打包工具！")
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()