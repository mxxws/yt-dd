# YT-DD - YouTube Downloader

[English](#english) | [中文](#chinese)

<a name="english"></a>
## English

A YouTube video downloader based on PyQt6 and yt-dlp, supporting single video and playlist downloads with high-definition video and subtitle download features.

### Features

- **HD Video Download**: Support for 4K(2160P), 2K(1440P), 1080P, 720P and more
- **Audio Format Options**: Support for MP3, M4A, WAV and other audio formats
- **Subtitle Download**: Automatic subtitle detection and download, multi-language support
- **Batch Download**: Support for playlists and channel downloads
- **Custom Download Settings**:
  - Custom video formats (MP4, MKV, WebM)
  - Custom video quality and encoding
  - Custom download path
  - Custom file naming format
- **Download Management**:
  - Real-time download progress
  - Download speed display
  - Estimated time remaining
  - Pause/Resume download
- **Modern UI**: Built with PyQt6, clean and intuitive interface

### Installation

#### Method 1: Direct Download (Windows)

1. Download the latest release from [Releases](https://github.com/yourusername/yt-dd/releases)
2. Extract to any location
3. Run `yt-dd.exe`

#### Method 2: From Source

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/yt-dd.git
   cd yt-dd
   ```

2. Create virtual environment and install dependencies
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

3. Run the program
   ```bash
   python main.py
   ```

### Usage

1. Paste video URL into the input box (supports YouTube, Bilibili and more)
2. Select download options:
   - Video quality: 4K(2160P), 2K(1440P), 1080P, 720P etc.
   - Video format: MP4, MKV, WebM etc.
   - Subtitle: Choose language
   - Audio only: Choose format
3. Select save location
4. Click "Download" to start
5. Monitor progress in the progress bar

### Building from Source

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Run build script
python build.py
```

The executable will be generated in the `dist` directory.

### Tech Stack

- Python 3.13+
- PyQt6: GUI
- yt-dlp: Video download engine
- PyInstaller: Executable packaging
- FFmpeg: Video processing

### Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<a name="chinese"></a>
## 中文

基于 PyQt6 和 yt-dlp 的 YouTube 视频下载工具，支持单个视频和播放列表下载，提供高清视频和字幕下载功能。

### 功能特点

- **高清视频下载**：支持 4K(2160P)、2K(1440P)、1080P、720P 等多种分辨率
- **音频格式选择**：支持 MP3、M4A、WAV 等多种音频格式
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
- **简洁现代的界面**：采用 PyQt6 构建，界面简洁直观，操作便捷

### 安装方法

#### 方法1：直接使用可执行文件（Windows）

1. 从[Releases](https://github.com/yourusername/yt-dd/releases)页面下载最新版本
2. 解压到任意位置
3. 运行 `yt-dd.exe`

#### 方法2：从源码运行

1. 克隆仓库
   ```bash
   git clone https://github.com/yourusername/yt-dd.git
   cd yt-dd
   ```

2. 创建虚拟环境并安装依赖
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   # 或
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

3. 运行程序
   ```bash
   python main.py
   ```

### 使用方法

1. 将视频URL粘贴到输入框（支持YouTube、Bilibili等多个平台）
2. 选择下载选项：
   - 视频质量：4K(2160P)、2K(1440P)、1080P、720P等
   - 视频格式：MP4、MKV、WebM等
   - 是否下载字幕：选择需要的字幕语言
   - 是否仅下载音频：选择音频格式
3. 选择保存位置
4. 点击"下载"按钮开始下载
5. 在下方进度条查看下载进度和估计剩余时间

### 从源码构建

```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 运行构建脚本
python build.py
```

生成的可执行文件位于 `dist` 目录下。

### 技术栈

- Python 3.13+
- PyQt6：GUI界面
- yt-dlp：视频下载引擎
- PyInstaller：打包为可执行文件
- FFmpeg：视频处理

### 贡献指南

欢迎提交问题和功能请求。如果您想贡献代码，请：

1. Fork 这个仓库
2. 创建您的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建一个 Pull Request

### 许可证

此项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。 