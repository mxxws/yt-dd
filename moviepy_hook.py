
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
