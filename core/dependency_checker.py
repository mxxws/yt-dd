import os
import sys
import subprocess
import importlib
import logging
import traceback
from typing import Dict, List, Tuple, Optional

class DependencyChecker:
    """
    依赖检查器，用于检查和更新依赖包版本
    """
    def __init__(self, requirements_file: str = 'requirements.txt'):
        """
        初始化依赖检查器
        
        Args:
            requirements_file: requirements.txt 文件路径
        """
        self.requirements_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), requirements_file)
        self.logger = logging.getLogger('dependency_checker')
        
    def check_package_version(self, package_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        检查指定包的版本是否与 requirements.txt 中的版本一致
        
        Args:
            package_name: 包名
            
        Returns:
            (是否一致, 当前版本, requirements.txt中的版本)
        """
        # 获取当前环境中的版本
        current_version = None
        try:
            # 直接使用pip命令获取版本，避免导入模块可能引起的错误
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', package_name],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith('Version:'):
                        current_version = line.split(':', 1)[1].strip()
                        break
                        
            # 如果pip命令无法获取版本，尝试导入模块获取版本
            if current_version is None:
                # 处理包名中的连字符
                module_name = package_name.replace('-', '_')
                # 尝试导入版本信息
                if module_name == 'yt_dlp':
                    import yt_dlp.version
                    current_version = yt_dlp.version.__version__
                else:
                    try:
                        # 对于其他包，尝试获取 __version__ 属性
                        module = importlib.import_module(module_name)
                        current_version = getattr(module, '__version__', None)
                    except (ImportError, AttributeError) as e:
                        print(f"获取 {package_name} 版本失败: {str(e)}")
                        self.logger.warning(f"获取 {package_name} 版本失败: {str(e)}")
        except subprocess.SubprocessError as e:
            print(f"获取 {package_name} 版本失败: {str(e)}")
            self.logger.warning(f"获取 {package_name} 版本失败: {str(e)}")
            return False, None, None
            
        # 获取 requirements.txt 中的版本
        req_version = None
        try:
            if os.path.exists(self.requirements_file):
                with open(self.requirements_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith(f"{package_name}=="):
                            req_version = line.strip().split('==')[1]
                            break
        except Exception as e:
            self.logger.warning(f"读取 requirements.txt 中的 {package_name} 版本失败: {str(e)}")
            return False, current_version, None
            
        # 比较版本
        if current_version and req_version:
            return current_version == req_version, current_version, req_version
        return False, current_version, req_version
    
    def update_requirement_version(self, package_name: str, version: str) -> bool:
        """
        更新requirements.txt中指定包的版本
        
        Args:
            package_name: 包名
            version: 新版本号
            
        Returns:
            是否更新成功
        """
        try:
            if not os.path.exists(self.requirements_file):
                # 如果文件不存在，创建新文件
                with open(self.requirements_file, 'w', encoding='utf-8') as f:
                    f.write(f"{package_name}=={version}\n")
                print(f"已创建requirements.txt并添加 {package_name}=={version}")
                self.logger.info(f"已创建requirements.txt并添加 {package_name}=={version}")
                return True
            
            # 读取当前的requirements.txt
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 查找并更新指定包的版本
            found = False
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    continue
                    
                if line_stripped.startswith(f"{package_name}=="):
                    old_version = line_stripped.split('==')[1] if '==' in line_stripped else "未知版本"
                    lines[i] = f"{package_name}=={version}\n"
                    found = True
                    print(f"已更新requirements.txt: {package_name} {old_version} -> {version}")
                    self.logger.info(f"已更新requirements.txt: {package_name} {old_version} -> {version}")
                    break
            
            # 如果没有找到指定的包，添加到文件末尾
            if not found:
                lines.append(f"{package_name}=={version}\n")
                print(f"已添加到requirements.txt: {package_name}=={version}")
                self.logger.info(f"已添加到requirements.txt: {package_name}=={version}")
            
            # 写回文件
            with open(self.requirements_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
        except Exception as e:
            print(f"更新requirements.txt中{package_name}版本失败: {str(e)}")
            self.logger.error(f"更新requirements.txt中{package_name}版本失败: {str(e)}")
            return False
    
    def update_package(self, package_name: str) -> bool:
        """
        使用pip更新指定的包到最新版本
        
        Args:
            package_name: 包名
            
        Returns:
            是否更新成功
        """
        try:
            print(f"正在更新 {package_name} 到最新版本...")
            self.logger.info(f"正在更新 {package_name} 到最新版本...")
            # 使用清华源更新包
            cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', package_name, 
                   '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple']
            print(f"执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            print(f"命令执行结果: {result.returncode}")
            print(f"输出: {result.stdout[:200]}..." if len(result.stdout) > 200 else f"输出: {result.stdout}")
            
            if result.returncode == 0:
                # 获取更新后的版本
                _, new_version, _ = self.check_package_version(package_name)
                print(f"更新后的版本: {new_version}")
                
                if new_version:
                    # 更新requirements.txt
                    self.update_requirement_version(package_name, new_version)
                    print(f"{package_name} 已更新到最新版本: {new_version}")
                    self.logger.info(f"{package_name} 已更新到最新版本: {new_version}")
                    return True
            else:
                print(f"更新 {package_name} 失败: {result.stderr[:200]}..." if len(result.stderr) > 200 else f"更新 {package_name} 失败: {result.stderr}")
                self.logger.error(f"更新 {package_name} 失败: {result.stderr}")
                
            return False
        except Exception as e:
            print(f"更新 {package_name} 时出错: {str(e)}")
            self.logger.error(f"更新 {package_name} 时出错: {str(e)}")
            return False
    
    def update_all_packages(self) -> Dict[str, Dict]:
        """
        使用pip自动更新所有已安装的包到最新版本，并更新requirements.txt
        
        Returns:
            包状态字典 {包名: {"old_version": 更新前版本, "new_version": 更新后版本, "updated": 是否已更新}}
        """
        result = {}
        try:
            self.logger.info("开始更新所有包...")
            print("开始更新所有包...")
            
            # 获取当前环境中已安装的包
            cmd = [sys.executable, '-m', 'pip', 'list', '--format=json']
            list_result = subprocess.run(cmd, capture_output=True, text=True)
            
            if list_result.returncode != 0:
                self.logger.error(f"获取已安装包列表失败: {list_result.stderr}")
                print(f"获取已安装包列表失败: {list_result.stderr}")
                return result
            
            # 解析JSON输出
            import json
            try:
                installed_packages = json.loads(list_result.stdout)
                installed_dict = {pkg["name"]: pkg["version"] for pkg in installed_packages}
            except json.JSONDecodeError:
                self.logger.error("解析pip list输出失败")
                print("解析pip list输出失败")
                return result
            
            # 读取requirements.txt文件中的包列表
            if not os.path.exists(self.requirements_file):
                self.logger.error(f"requirements.txt 文件不存在: {self.requirements_file}")
                print(f"requirements.txt 文件不存在: {self.requirements_file}")
                return result
                
            # 读取requirements.txt中的包
            req_packages = {}
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('==')
                        if len(parts) == 2:
                            req_packages[parts[0]] = parts[1]
            
            # 项目实际使用的包列表
            project_packages = [
                'PyQt6', 'PyQt6-Qt6', 'PyQt6_sip', 'yt-dlp', 'moviepy', 'ffmpeg-python',
                'requests', 'tqdm', 'numpy', 'pillow', 'imageio', 'imageio-ffmpeg',
                'pyinstaller', 'pyinstaller-hooks-contrib'
            ]
            
            # 更新每个包
            for package_name in project_packages:
                if package_name not in installed_dict:
                    print(f"跳过 {package_name}，因为它未安装")
                    self.logger.info(f"跳过 {package_name}，因为它未安装")
                    continue
                
                current_version = installed_dict[package_name]
                old_version = req_packages.get(package_name, "未指定")
                
                if not package_name or package_name in ['pip', 'setuptools', 'wheel']:
                    continue  # 跳过基础包
                
                # 跳过pytubefix包，因为它会导致错误
                if package_name == 'pytubefix':
                    print(f"跳过 {package_name} 更新，因为它可能导致错误")
                    self.logger.info(f"跳过 {package_name} 更新，因为它可能导致错误")
                    continue
                
                result[package_name] = {
                    "old_version": old_version,
                    "new_version": current_version,
                    "updated": False
                }
                
                # 更新包
                print(f"正在更新 {package_name} 从 {current_version} 到最新版本...")
                self.logger.info(f"正在更新 {package_name} 从 {current_version} 到最新版本...")
                
                try:
                    # 使用pip更新包，添加清华源以加快下载速度
                    update_cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', package_name,
                                 '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple']
                    update_result = subprocess.run(update_cmd, capture_output=True, text=True)
                    
                    if update_result.returncode == 0:
                        # 获取更新后的版本
                        _, new_version, _ = self.check_package_version(package_name)
                        
                        if new_version and new_version != current_version:
                            # 更新requirements.txt
                            self.update_requirement_version(package_name, new_version)
                            result[package_name]["new_version"] = new_version
                            result[package_name]["updated"] = True
                            print(f"{package_name} 已更新: {current_version} -> {new_version}")
                            self.logger.info(f"{package_name} 已更新: {current_version} -> {new_version}")
                        else:
                            # 即使版本没变，也更新requirements.txt以确保一致性
                            if current_version != old_version:
                                self.update_requirement_version(package_name, current_version)
                                result[package_name]["updated"] = True
                            print(f"{package_name} 已是最新版本: {current_version}")
                            self.logger.info(f"{package_name} 已是最新版本: {current_version}")
                    else:
                        print(f"更新 {package_name} 失败: {update_result.stderr[:200]}" + ("..." if len(update_result.stderr) > 200 else ""))
                        self.logger.error(f"更新 {package_name} 失败: {update_result.stderr}")
                except Exception as e:
                    print(f"更新 {package_name} 时出错: {str(e)}")
                    self.logger.error(f"更新 {package_name} 时出错: {str(e)}")
            
            # 清理requirements.txt中未使用的包
            self.clean_requirements(project_packages)
            
            print("所有包更新完成")
            self.logger.info("所有包更新完成")
            
        except Exception as e:
            print(f"更新所有包时出错: {str(e)}")
            self.logger.error(f"更新所有包时出错: {str(e)}")
            traceback.print_exc()
        
        return result
        
    def clean_requirements(self, keep_packages: List[str]) -> bool:
        """
        清理requirements.txt文件，只保留指定的包
        
        Args:
            keep_packages: 需要保留的包名列表
            
        Returns:
            是否清理成功
        """
        try:
            # 添加基础包到保留列表
            keep_packages = keep_packages + ['pip', 'setuptools', 'wheel']
            
            # 读取当前的requirements.txt
            if not os.path.exists(self.requirements_file):
                self.logger.warning(f"requirements.txt 文件不存在: {self.requirements_file}")
                return False
                
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 筛选需要保留的行
            kept_lines = []
            removed_packages = []
            
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    kept_lines.append(line)  # 保留空行和注释
                    continue
                    
                parts = line_stripped.split('==')
                if len(parts) != 2:
                    kept_lines.append(line)  # 保留格式不符合的行
                    continue
                    
                package_name = parts[0]
                if package_name in keep_packages:
                    kept_lines.append(line)  # 保留指定的包
                else:
                    removed_packages.append(package_name)  # 记录被移除的包
            
            # 写回文件
            with open(self.requirements_file, 'w', encoding='utf-8') as f:
                f.writelines(kept_lines)
            
            if removed_packages:
                removed_str = ", ".join(removed_packages)
                print(f"已从requirements.txt中移除未使用的包: {removed_str}")
                self.logger.info(f"已从requirements.txt中移除未使用的包: {removed_str}")
            
            return True
        except Exception as e:
            print(f"清理requirements.txt失败: {str(e)}")
            self.logger.error(f"清理requirements.txt失败: {str(e)}")
            return False
    
    def check_packages_only(self, packages: List[str]) -> Dict[str, Dict]:
        """
        仅检查指定包是否已安装，不进行更新
        
        Args:
            packages: 包名列表
            
        Returns:
            包状态字典 {包名: {"installed": 是否已安装, "current_version": 当前版本}}
        """
        result = {}
        for package in packages:
            try:
                # 检查包是否已安装
                _, current_version, _ = self.check_package_version(package)
                installed = current_version is not None
                
                result[package] = {
                    "installed": installed,
                    "current_version": current_version
                }
                
                if installed:
                    print(f"✓ {package} 已安装，版本: {current_version}")
                    self.logger.info(f"{package} 已安装，版本: {current_version}")
                else:
                    print(f"✗ {package} 未安装")
                    self.logger.warning(f"{package} 未安装")
                    
            except Exception as e:
                print(f"检查 {package} 时出错: {str(e)}")
                self.logger.error(f"检查 {package} 时出错: {str(e)}")
                result[package] = {
                    "installed": False,
                    "current_version": None,
                    "error": str(e)
                }
                
        return result
        
    def check_and_update_packages(self, packages: List[str]) -> Dict[str, Dict]:
        """
        检查并更新指定包的版本
        
        Args:
            packages: 包名列表
            
        Returns:
            包状态字典 {包名: {"current_version": 当前版本, "req_version": requirements.txt中的版本, "updated": 是否已更新}}
        """
        result = {}
        for package in packages:
            is_consistent, current_version, req_version = self.check_package_version(package)
            
            result[package] = {
                "current_version": current_version,
                "req_version": req_version,
                "updated": False
            }
            
            # 对于yt-dlp，检查版本并记录，但不尝试更新（因为yt-dlp使用未来日期作为版本号）
            if package == 'yt-dlp' and current_version:
                print(f"检查 {package} 版本: {current_version}")
                
                # yt-dlp使用未来日期作为版本号（如2025.06.30），这是正常的，不需要更新
                # 只有当版本格式不符合YYYY.MM.DD时才尝试更新
                try:
                    # 检查版本号是否为日期格式（YYYY.MM.DD）
                    version_parts = current_version.split('.')
                    if len(version_parts) == 3 and len(version_parts[0]) == 4:
                        # 尝试将版本号解析为年月日
                        year = int(version_parts[0])
                        month = int(version_parts[1])
                        day = int(version_parts[2])
                        
                        # 如果能成功解析为日期格式，则认为版本号正确
                        print(f"{package} 版本 {current_version} 格式正确（使用日期格式）")
                        self.logger.info(f"{package} 版本 {current_version} 格式正确（使用日期格式）")
                    else:
                        # 如果不是日期格式，尝试更新
                        print(f"{package} 版本 {current_version} 不是标准的日期格式，尝试更新")
                        self.logger.warning(f"{package} 版本 {current_version} 不是标准的日期格式，尝试更新")
                        updated = self.update_package(package)
                        result[package]["updated"] = updated
                        if updated:
                            _, new_version, _ = self.check_package_version(package)
                            result[package]["current_version"] = new_version
                except (ValueError, IndexError) as e:
                    # 如果版本号格式不正确，尝试更新
                    print(f"解析 {package} 版本号出错: {str(e)}，尝试更新")
                    self.logger.warning(f"解析 {package} 版本号出错: {str(e)}，尝试更新")
                    updated = self.update_package(package)
                    result[package]["updated"] = updated
                    if updated:
                        _, new_version, _ = self.check_package_version(package)
                        result[package]["current_version"] = new_version
            
            # 如果版本不一致且当前版本存在，则更新 requirements.txt
            elif not is_consistent and current_version:
                updated = self.update_requirement_version(package, current_version)
                result[package]["updated"] = updated
                if updated:
                    self.logger.info(f"已更新 {package} 版本: {req_version or '未指定'} -> {current_version}")
        
        return result