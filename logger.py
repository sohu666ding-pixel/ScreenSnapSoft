"""简单日志（需求42）：写到程序同级 logs/ 下，按天一个文件 logYYYYMMDD.txt，
每行格式：时间 | 类型 | 说明。日志失败绝不影响主程序。
"""
import os
from datetime import datetime

from .paths import base_dir


def log_dir():
    d = os.path.join(base_dir(), "logs")
    os.makedirs(d, exist_ok=True)
    return d


def log(log_type, message):
    try:
        now = datetime.now()
        path = os.path.join(log_dir(), f"log{now:%Y%m%d}.txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{now:%Y-%m-%d %H:%M:%S} | {log_type} | {message}\n")
    except Exception:
        pass
