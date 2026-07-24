import os
import sys


def base_dir():
    """用户数据目录。绿色版打包后取 exe 所在目录；开发时取项目根目录。

    config.ini 与 picture 目录都放在这里（用户可写），保证 copy 后即用。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_dir():
    """只读资源目录（如 Vosk 模型）。

    打包后 PyInstaller 把 --add-data 的资源放进 sys._MEIPASS(_internal)，
    开发时与项目根目录一致。
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
