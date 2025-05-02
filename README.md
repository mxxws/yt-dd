# YT-DD - YouTube下载器

一个基于PyQt6和yt-dlp的YouTube视频下载工具，支持下载单个视频或播放列表，提供高清视频和字幕下载功能。

## 功能特点

- **高清视频下载**：支持下载4K(2160P)、2K(1440P)、1080P、720P等多种分辨率视频
- **音频格式选择**：支持MP3、M4A、WAV等多种音频格式下载
- **字幕自动下载**：可自动检测并下载视频字幕，支持多语言字幕选择
- **批量下载功能**：支持播放列表和频道批量下载
- **自定义下载设置**：
  - 自定义视频格式(MP4、MKV、WebM等)
  - 自定义视频质量和编码
  - 自定义下载路径
  - 自定义文件命名格式
- **下载管理功能**：
  - 实时显示下载进度
  - 显示下载速度
  - 显示估计剩余时间
  - 支持暂停/恢复下载
- **简洁现代的界面**：采用PyQt6构建，界面简洁直观，操作便捷

## 安装方法

### 方法1：直接使用可执行文件（Windows）

1. 从[Releases](https://github.com/yourusername/yt-dd/releases)页面下载最新版本的压缩包
2. 解压到任意位置
3. 运行`yt-dd.exe`

### 方法2：从源码运行

1. 克隆仓库
   ```
   git clone https://github.com/yourusername/yt-dd.git
   cd yt-dd
   ```

2. 创建虚拟环境并安装依赖
   ```
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   # 或
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

3. 运行程序
   ```
   python main.py
   ```

## 使用方法

1. 将视频URL粘贴到输入框（支持YouTube、Bilibili等多个平台的链接）
2. 选择下载选项：
   - 视频质量：4K(2160P)、2K(1440P)、1080P、720P等
   - 视频格式：MP4、MKV、WebM等
   - 是否下载字幕：选择需要的字幕语言
   - 是否仅下载音频：选择音频格式
3. 选择保存位置
4. 点击"下载"按钮开始下载
5. 在下方进度条查看下载进度和估计剩余时间

## 视频质量与格式说明

| 质量选项 | 分辨率 | 适用场景 |
|---------|-------|---------|
| 4K | 3840×2160 | 大屏幕观看、高质量视频编辑 |
| 2K | 2560×1440 | 高清显示器、精细视频内容 |
| 1080P | 1920×1080 | 标准高清、日常观看 |
| 720P | 1280×720 | 节省空间、流畅播放 |
| 480P | 854×480 | 流量受限时使用 |

## 字幕下载功能

- 自动检测视频可用字幕
- 支持多语言字幕选择（中文、英文、日文等）
- 支持自动翻译字幕（基于YouTube提供的翻译）
- 支持多种字幕格式：SRT、VTT、TXT等

## 从源码构建可执行文件

```
# 激活虚拟环境
.\venv\Scripts\activate

# 运行构建脚本
python build.py
```

生成的可执行文件位于`dist/yt-dd/`目录下。

## 技术栈

- Python 3.13+
- PyQt6：GUI界面
- yt-dlp：视频下载引擎
- PyInstaller：打包为可执行文件
- FFmpeg：视频处理

## 贡献指南

欢迎提交问题和功能请求。如果您想贡献代码，请：

1. Fork 这个仓库
2. 创建您的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建一个 Pull Request

## 许可证

此项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。 