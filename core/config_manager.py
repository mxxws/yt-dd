import os
import json
from typing import Dict, Any

class ConfigManager:
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.default_config_file = os.path.join(self.config_dir, "default_config.json")
        self._ensure_config_exists()
        self.config = self.load_config()

    def _ensure_config_exists(self):
        """确保配置文件存在"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        if not os.path.exists(self.config_file):
            # 如果用户配置不存在，复制默认配置
            if os.path.exists(self.default_config_file):
                with open(self.default_config_file, 'r', encoding='utf-8') as f:
                    default_config = json.load(f)
            else:
                default_config = {
                    "download_path": "",
                    "default_video_quality": "1080p",
                    "default_audio_quality": "best",
                    "default_subtitle_lang": "zh",
                    "theme": "fusion",
                    "auto_check_update": True,
                    "proxy": {
                        "enabled": False,
                        "type": "http",
                        "host": "",
                        "port": ""
                    }
                }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)

    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {}

    def save_config(self) -> bool:
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        self.config[key] = value
        return self.save_config()

    def update(self, config_dict: Dict[str, Any]) -> bool:
        """批量更新配置"""
        self.config.update(config_dict)
        return self.save_config() 