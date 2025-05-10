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

def verify_moviepy_modules(logger):
    """验证 moviepy 及其子模块的可用性"""
    print("\n" + "=" * 70)
    print("【模块验证】检查 moviepy 子模块...")
    print("=" * 70)
    
    # 定义需要检查的 moviepy 子模块
    moviepy_modules = [
        "moviepy.editor",
        "moviepy.video.io.ffmpeg_tools",
        "moviepy.video.VideoClip",
        "moviepy.video.io.VideoFileClip",
        "moviepy.audio.io.AudioFileClip",
        "moviepy.audio.AudioClip"
    ]
    
    all_modules_available = True
    print(f"{'模块名称':<40} {'状态':<10}")
    print("-" * 50)
    
    for module_name in moviepy_modules:
        try:
            __import__(module_name)
            print(f"{module_name:<40} {'✓ 可用':<10}")
        except ImportError as e:
            print(f"{module_name:<40} {'✗ 不可用':<10}")
            logger.log_warning(f"无法导入模块 {module_name}: {str(e)}", 'module_import_error')
            all_modules_available = False
    
    print("-" * 50)
    if all_modules_available:
        print("✓ 所有 moviepy 子模块检查通过")
    else:
        print("⚠ 某些 moviepy 子模块不可用，可能会影响打包结果")
        
    # 尝试创建一个简单的测试对象
    try:
        print("\n测试创建 VideoFileClip 和 AudioFileClip 对象...")
        from moviepy.editor import VideoFileClip, AudioFileClip
        print("✓ VideoFileClip 和 AudioFileClip 类可以成功导入")
    except Exception as e:
        print(f"✗ 无法导入 VideoFileClip 或 AudioFileClip 类: {str(e)}")
        logger.log_warning(f"无法测试 moviepy 核心类: {str(e)}", 'moviepy_test_error')
    
    return all_modules_available

def update_dependencies(logger):
    """检查并更新依赖包，使用清华源，不先卸载再安装"""
    logging.info("检查依赖包版本并更新...")
    
    # 定义不更新的包列表
    exclude_packages = ['moviepy']
    print(f"\n注意: 以下包将不会被更新: {', '.join(exclude_packages)}")
    
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
        print("【依赖更新】以下包需要更新:")
        print("=" * 70)
        
        update_table_header = f"{'包名':<20} {'当前版本':<15} {'最新版本':<15} {'状态':<10}"
        print(update_table_header)
        print("-" * 60)
        
        update_count = 0
        success_count = 0
        skipped_count = 0
        
        # 对每个需要更新的包单独更新
        for line in outdated_packages.splitlines():
            if " is available" in line:
                update_count += 1
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
                        
                        # 检查是否在排除列表中
                        if package_name.lower() in [pkg.lower() for pkg in exclude_packages]:
                            status = "⚠ 已跳过"
                            skipped_count += 1
                            print(f"{package_name:<20} {current_version:<15} {latest_version:<15} {status:<10}")
                            continue
                        
                        # 显示更新信息
                        print(f"{package_name:<20} {current_version:<15} {latest_version:<15} {'更新中...':<10}", end="\r")
                        
                        # 使用清华源更新包
                        update_cmd = [
                            sys.executable, '-m', 'pip', 'install', '--upgrade',
                            f'{package_name}',
                            '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'
                        ]
                        
                        update_result = subprocess.run(update_cmd, capture_output=True, text=True)
                        
                        if update_result.returncode == 0:
                            status = "✓ 成功"
                            success_count += 1
                            logger.log_file_operation('command', f'更新 {package_name}', 'success', 
                                                  {'output': update_result.stdout})
                        else:
                            status = "✗ 失败"
                            logger.log_file_operation('command', f'更新 {package_name}', 'failed', 
                                                  {'error': update_result.stderr})
                            logger.log_warning(f"{package_name} 更新失败: {update_result.stderr}", 'update_error')
                        
                        # 更新显示结果
                        print(f"{package_name:<20} {current_version:<15} {latest_version:<15} {status:<10}")
                except Exception as e:
                    logger.log_error(f"解析包信息失败: {line}", "parsing_error", str(e))
                    print(f"解析错误: {line} - {str(e)}")
        
        # 显示更新摘要
        print("\n" + "-" * 60)
        print(f"更新完成: 总计 {update_count} 个包，{success_count} 个成功，{skipped_count} 个跳过，{update_count - success_count - skipped_count} 个失败")
        print("=" * 50)
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.log_error("依赖包检查失败", "dependency_check_error", e.stderr or e.stdout)
        print("\n✗ 依赖包检查失败")
        print(e.stderr or e.stdout)
        return False
    except Exception as e:
        logger.log_error(str(e), "dependency_update_error", traceback.format_exc())
        print(f"\n✗ 依赖更新过程出错: {str(e)}")
        return False

def create_moviepy_hook(logger):
    """创建 moviepy 钩子文件，帮助 PyInstaller 正确收集依赖"""
    print("\n" + "=" * 70)
    print("【钩子创建】创建 moviepy 打包钩子...")
    print("=" * 70)
    
    hook_content = """
# PyInstaller hook for moviepy
from PyInstaller.utils.hooks import collect_all

# 收集 moviepy 及其子模块
datas, binaries, hiddenimports = collect_all('moviepy')

# 添加关键子模块
hiddenimports.extend([
    'moviepy.editor',
    'moviepy.video.io.ffmpeg_tools',
    'moviepy.video.VideoClip',
    'moviepy.video.io.VideoFileClip',
    'moviepy.audio.io.AudioFileClip',
    'moviepy.audio.AudioClip',
    'imageio',
    'imageio.plugins',
    'imageio.plugins.ffmpeg',
    'tqdm',
    'proglog',
    'decorator'
])
"""
    
    hook_file = "moviepy_hook.py"
    try:
        with open(hook_file, "w", encoding="utf-8") as f:
            f.write(hook_content)
        print(f"✓ 成功创建 {hook_file}")
        logger.log_file_operation('create', hook_file, 'success')
        return True
    except Exception as e:
        print(f"✗ 创建 {hook_file} 失败: {str(e)}")
        logger.log_error(f"创建 moviepy 钩子文件失败: {str(e)}", "hook_creation_error")
        return False

def create_moviepy_editor_file(logger):
    """创建 moviepy_editor.py 文件来解决 moviepy.editor 导入问题"""
    print("\n" + "=" * 70)
    print("【文件创建】准备创建 moviepy.editor 兼容文件...")
    print("=" * 70)
    
    # 获取当前 moviepy 版本
    try:
        import moviepy
        moviepy_version = getattr(moviepy, "__version__", "未知版本")
        print(f"当前安装的 moviepy 版本: {moviepy_version}")
        
        # 检查 moviepy 包结构，以便更好地生成兼容代码
        has_editor = hasattr(moviepy, "editor")
        has_video = hasattr(moviepy, "video")
        has_audio = hasattr(moviepy, "audio")
        
        print(f"包结构检查: editor模块存在: {has_editor}, video模块存在: {has_video}, audio模块存在: {has_audio}")
        
        # 检查视频和音频模块路径
        video_paths = []
        audio_paths = []
        
        if has_video:
            # 检查视频处理相关模块
            try:
                import inspect
                import moviepy.video
                video_paths = [name for name, _ in inspect.getmembers(moviepy.video, inspect.ismodule)]
                print(f"检测到的video子模块: {', '.join(video_paths)}")
            except Exception as e:
                print(f"检查video子模块时出错: {str(e)}")
        
        if has_audio:
            # 检查音频处理相关模块
            try:
                import moviepy.audio
                audio_paths = [name for name, _ in inspect.getmembers(moviepy.audio, inspect.ismodule)]
                print(f"检测到的audio子模块: {', '.join(audio_paths)}")
            except Exception as e:
                print(f"检查audio子模块时出错: {str(e)}")
                
    except ImportError:
        moviepy_version = "未知版本"
        has_editor = False
        has_video = False
        has_audio = False
        video_paths = []
        audio_paths = []
        print("无法导入 moviepy 包，请确保已安装")
    
    # 根据检测到的包结构生成更智能的兼容代码
    editor_content = """
# 此文件用于解决 PyInstaller 打包 moviepy.editor 的问题
# 直接导入所有 moviepy.editor 中的组件
import sys
import os
import importlib
import traceback

# 记录当前导入的模块
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
                        setattr(sys.modules[__name__], target_name, attr)
                    else:
                        print(f"警告: {module_name} 中未找到 {item}")
                except Exception as e:
                    print(f"导入 {module_name}.{item} 时出错: {str(e)}")
            return module
        else:
            module = __import__(module_name)
            imported_modules[module_name] = module
            return module
    except ImportError as e:
        print(f"警告: 无法导入 {module_name}: {str(e)}")
        return None
    except Exception as e:
        print(f"导入 {module_name} 时出现未知错误: {str(e)}")
        return None

# 尝试导入基本组件
try:
    print("开始为 moviepy.editor 创建兼容层...")
    
    # 视频处理相关类
    safe_import('moviepy.video.io.VideoFileClip', ['VideoFileClip'])
    safe_import('moviepy.video.VideoClip', ['VideoClip', 'ImageClip', 'ColorClip', 'TextClip'])
    
    # 音频处理相关类
    safe_import('moviepy.audio.io.AudioFileClip', ['AudioFileClip']) 
    safe_import('moviepy.audio.AudioClip', ['AudioClip', 'CompositeAudioClip'])
    
    # 合成相关类
    # 尝试不同可能的导入路径
    video_compositing_paths = [
        'moviepy.video.compositing.CompositeVideoClip',
        'moviepy.video.CompositeVideoClip',
        'moviepy.compositing.CompositeVideoClip'
    ]
    
    for path in video_compositing_paths:
        if 'CompositeVideoClip' not in imported_modules:
            safe_import(path, ['CompositeVideoClip'])
    
    # 连接相关类
    concatenate_paths = [
        'moviepy.video.compositing.concatenate',
        'moviepy.video.concatenate',
        'moviepy.compositing.concatenate',
        'moviepy.concatenate'
    ]
    
    for path in concatenate_paths:
        if 'concatenate_videoclips' not in imported_modules:
            safe_import(path, ['concatenate_videoclips'])
    
    # 导入ffmpeg工具
    ffmpeg_paths = [
        'moviepy.video.io.ffmpeg_tools',
        'moviepy.tools.ffmpeg_tools',
        'moviepy.ffmpeg_tools'
    ]
    
    for path in ffmpeg_paths:
        safe_import(path, ['ffmpeg_extract_subclip', 'ffmpeg_merge_video_audio'])
            
    # 检查导入的组件
    print("已成功导入的组件:")
    for name in sorted(imported_modules.keys()):
        print(f"  - {name}")
    
    # 如果缺少关键组件，尝试手动创建
    if 'VideoFileClip' not in imported_modules or 'AudioFileClip' not in imported_modules:
        print("警告: 缺少关键组件，尝试手动创建替代实现...")
        
        # 这里可以添加简单的替代实现，如果需要的话
        
except Exception as e:
    print(f"加载 moviepy 组件时出错: {str(e)}")
    traceback.print_exc()
"""
    
    editor_file = "moviepy_editor.py"
    try:
        with open(editor_file, "w", encoding="utf-8") as f:
            f.write(editor_content)
        print(f"✓ 成功创建 {editor_file}")
        logger.log_file_operation('create', editor_file, 'success')
        
        # 尝试导入这个文件来验证
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("moviepy_editor", editor_file)
            moviepy_editor = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(moviepy_editor)
            
            # 验证导入的模块
            imported_count = len(getattr(moviepy_editor, 'imported_modules', {}))
            print(f"✓ 测试导入成功，成功导入了 {imported_count} 个组件")
            
            # 特别检查关键类
            for key_class in ['VideoFileClip', 'AudioFileClip']:
                if hasattr(moviepy_editor, key_class):
                    print(f"  ✓ 关键类 {key_class} 可用")
                else:
                    print(f"  ✗ 关键类 {key_class} 不可用")
            
            return True
        except Exception as e:
            print(f"⚠ 测试导入出现一些警告 (可能不影响运行): {str(e)}")
            logger.log_warning(f"测试导入 moviepy_editor.py 出现警告: {str(e)}", "import_warning")
            return True  # 仍然返回True，因为文件已创建
            
    except Exception as e:
        print(f"✗ 创建 {editor_file} 失败: {str(e)}")
        logger.log_error(f"创建 moviepy_editor.py 文件失败: {str(e)}", "editor_creation_error")
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
                else:
                    print(f"{package:<20} {'✗ 失败':<10}")
                    logger.log_error(f"安装依赖 {package} 失败", "dependency_installation_error")
                    return
            
            print("-" * 30)
            print(f"✓ 所有缺失依赖安装完成")
        else:
            print("✓ 所有必要依赖已安装")
            
        # 验证 moviepy 子模块
        verify_moviepy_modules(logger)
        
        # 创建 moviepy 钩子文件
        create_moviepy_hook(logger)
        
        # 创建 moviepy_editor.py 兼容文件
        create_moviepy_editor_file(logger)
        
        # 更新依赖包
        print("\n" + "=" * 70)
        print("【依赖更新】检查并更新依赖包...")
        print("=" * 70)
        print("使用清华源进行更新，单独更新每个包（不卸载再安装）")
        
        if not update_dependencies(logger):
            logger.log_warning("依赖包更新过程出现问题，但将继续构建过程", "dependency_update_warning")
            print("⚠ 依赖包更新过程出现问题，但将继续构建过程")
        
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
            '--add-data "moviepy_editor.py;." '  # 添加moviepy_editor.py作为数据文件
            '--hidden-import "PyQt6" '
            '--hidden-import "yt_dlp" '
            '--hidden-import "pytubefix" '
            '--hidden-import "moviepy" '
            '--hidden-import "moviepy.editor" '
            '--hidden-import "moviepy.video.io.ffmpeg_tools" '
            '--hidden-import "moviepy.video.VideoClip" '
            '--hidden-import "moviepy.video.io.VideoFileClip" '
            '--hidden-import "moviepy.audio.io.AudioFileClip" '
            '--hidden-import "moviepy.audio.AudioClip" '
            '--hidden-import "imageio" '
            '--hidden-import "imageio.plugins" '
            '--hidden-import "imageio.plugins.ffmpeg" '
            '--hidden-import "tqdm" '
            '--hidden-import "proglog" '
            '--hidden-import "decorator" '
            '--collect-submodules "moviepy" '  # 收集所有子模块
            '--collect-data "moviepy" '  # 收集所有数据文件
            '--additional-hooks-dir="." '  # 使用当前目录中的钩子文件
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