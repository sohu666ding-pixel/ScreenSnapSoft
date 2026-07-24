"""缩略图缓存（需求41）：在程序同目录 .thumbcache 下缓存 320x200 缩略图，
按源文件路径+修改时间为键；命中直接读小图，避免每次解码全屏大图，加速启动。
"""
import os
import hashlib

from PIL import Image

from .paths import base_dir

THUMB_W, THUMB_H = 320, 200


def cache_dir():
    d = os.path.join(base_dir(), ".thumbcache")
    os.makedirs(d, exist_ok=True)
    return d


def thumb_for(src):
    """返回 src 对应的缓存缩略图路径（320x200 JPEG）；不存在/过期则生成。
    任何异常都回退为原图路径，保证不影响显示。"""
    try:
        mtime = int(os.path.getmtime(src))
    except OSError:
        return src
    key = hashlib.md5(f"{os.path.abspath(src)}|{mtime}".encode("utf-8")).hexdigest()
    out = os.path.join(cache_dir(), key + ".jpg")
    if os.path.exists(out):
        return out
    try:
        im = Image.open(src).convert("RGB")
        sw, sh = im.size
        scale = max(THUMB_W / sw, THUMB_H / sh)
        nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
        im = im.resize((nw, nh), Image.LANCZOS)
        left, top = (nw - THUMB_W) // 2, (nh - THUMB_H) // 2
        im = im.crop((left, top, left + THUMB_W, top + THUMB_H))
        im.save(out, "JPEG", quality=82)
        im.close()
        return out
    except Exception:
        return src
