
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
