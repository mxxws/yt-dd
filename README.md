# YT-DD - YouTube下载器

一个基于PyQt6和yt-dlp的YouTube视频下载工具，支持下载单个视频或播放列表。

## 功能特点

- 支持从YouTube和其他视频网站下载视频
- 支持下载不同质量和格式的视频
- 支持下载视频播放列表
- 简洁易用的图形界面
- 支持自定义下载保存位置
- 显示下载进度和估计剩余时间

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

1. 将YouTube视频或播放列表的URL粘贴到输入框
2. 选择下载质量和格式
3. 选择保存位置
4. 点击"下载"按钮开始下载
5. 等待下载完成

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

## 贡献指南

欢迎提交问题和功能请求。如果您想贡献代码，请：

1. Fork 这个仓库
2. 创建您的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建一个 Pull Request

## 许可证

此项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。 