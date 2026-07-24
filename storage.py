import os

IMAGE_EXTS = (".jpg", ".jpeg", ".png")


class Storage:
    """主题目录管理：每个抓拍主题对应根目录下的一个同名文件夹。"""

    def __init__(self, config):
        self.config = config

    def root(self):
        r = self.config.save_root()
        os.makedirs(r, exist_ok=True)
        return r

    def theme_dir(self, theme):
        return os.path.join(self.root(), theme)

    def ensure_theme(self, theme):
        """设置抓拍主题后自动创建同名目录，返回其路径。"""
        d = self.theme_dir(theme)
        os.makedirs(d, exist_ok=True)
        return d

    def list_themes(self):
        root = self.root()
        return sorted(
            n for n in os.listdir(root)
            if os.path.isdir(os.path.join(root, n))
        )

    def list_shots(self, theme):
        """返回某主题下的图片绝对路径列表，按抓拍时间（修改时间）升序。"""
        d = self.theme_dir(theme)
        if not os.path.isdir(d):
            return []
        files = [
            os.path.join(d, n) for n in os.listdir(d)
            if n.lower().endswith(IMAGE_EXTS)
        ]
        files.sort(key=lambda p: os.path.getmtime(p))
        return files
