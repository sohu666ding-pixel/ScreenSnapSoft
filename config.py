import os
import configparser

from .paths import base_dir

CONFIG_NAME = "config.ini"
SECTION = "capture"
DEFAULTS = {
    "theme": "默认主题",
    "save_dir": "picture",    # 需求16：默认在程序根目录下 picture/；也可填绝对路径
    "mic_device": "",         # 语音输入设备索引；空=系统默认麦克风
    "deepseek_api_key": "",   # 需求38：DeepSeek API Key（截图摘要用）
}


class Config:
    """系统参数：抓拍主题 + 保存位置。存于 exe 同目录的 config.ini。"""

    def __init__(self):
        self.path = os.path.join(base_dir(), CONFIG_NAME)
        self._cp = configparser.ConfigParser()
        self.load()

    def load(self):
        if os.path.exists(self.path):
            self._cp.read(self.path, encoding="utf-8")
        if not self._cp.has_section(SECTION):
            self._cp.add_section(SECTION)
        for k, v in DEFAULTS.items():
            if not self._cp.has_option(SECTION, k):
                self._cp.set(SECTION, k, v)

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            self._cp.write(f)

    @property
    def theme(self):
        return self._cp.get(SECTION, "theme")

    @theme.setter
    def theme(self, value):
        self._cp.set(SECTION, "theme", value)

    @property
    def save_dir(self):
        return self._cp.get(SECTION, "save_dir")

    @save_dir.setter
    def save_dir(self, value):
        self._cp.set(SECTION, "save_dir", value)

    @property
    def mic_device(self):
        """语音输入设备索引（int），空字符串/无效时返回 None=系统默认。"""
        v = self._cp.get(SECTION, "mic_device", fallback="").strip()
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @mic_device.setter
    def mic_device(self, value):
        self._cp.set(SECTION, "mic_device", "" if value is None else str(value))

    @property
    def api_key(self):
        return self._cp.get(SECTION, "deepseek_api_key", fallback="").strip()

    @api_key.setter
    def api_key(self, value):
        self._cp.set(SECTION, "deepseek_api_key", value or "")

    def save_root(self):
        """抓拍根目录的绝对路径（所有主题目录的父目录）。"""
        sd = self.save_dir
        if os.path.isabs(sd):
            return sd
        return os.path.join(base_dir(), sd)
