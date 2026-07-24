import os
import ctypes
from datetime import datetime

import mss
from PIL import Image


def enable_dpi_awareness():
    """让进程按真实物理像素工作，避免高 DPI 缩放下抓图被拉伸变模糊（需求13）。

    须在创建任何窗口/QApplication 之前调用。多级降级以兼容老系统。
    """
    try:
        # PROCESS_PER_MONITOR_DPI_AWARE_V2 = -4
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _unique_path(theme_dir, theme, ext):
    """主题_时间.ext；同一秒内多次抓拍时追加 _2/_3… 避免互相覆盖。"""
    base = f"{theme}_{_timestamp()}"
    path = os.path.join(theme_dir, base + ext)
    i = 2
    while os.path.exists(path):
        path = os.path.join(theme_dir, f"{base}_{i}{ext}")
        i += 1
    return path


def capture_fullscreen(theme, theme_dir):
    """用 mss 抓取整个虚拟桌面（所有显示器）的物理像素，存无损 PNG（需求13）。

    文件名： 主题_时间.png（需求 4）。
    PNG 为无损压缩：屏幕文字/细线像素级清晰、无 JPEG 的发虚与彩边；
    界面截图大量纯色区域使其体积通常比高质量 JPEG 更小。
    返回保存的绝对路径。
    """
    with mss.mss() as sct:
        monitor = sct.monitors[0]   # [0] = 拼合所有显示器的整个虚拟屏幕
        shot = sct.grab(monitor)
    img = Image.frombytes("RGB", shot.size, shot.rgb)

    path = _unique_path(theme_dir, theme, ".png")
    img.save(path, "PNG", optimize=True)
    return path
