"""截图摘要（需求38）：用 Windows 自带 OCR（免费、离线）识别截图文字，
再"组织"成要点摘要。

两种组织方式：
- 免费本地整理（默认，无需 API Key）：分行清洗 + 提取日期/时间/金额等关键信息。
- DeepSeek 增强（可选）：填了 API Key 则调用 DeepSeek 生成更智能的摘要，失败回退本地整理。

DeepSeek 官方 API 为纯文本模型，无法直接识图，故必须先 OCR 再总结。
"""
import os
import re
import json
import asyncio
import urllib.request

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

_CJK = r"一-鿿　-〿＀-￯"


def _clean_line(s):
    s = re.sub(r"\s+", " ", s).strip()
    # 去掉中文字符之间的空格（Windows OCR 中文常逐字加空格），保留英文词间空格
    s = re.sub(rf"(?<=[{_CJK}])\s+(?=[{_CJK}])", "", s)
    return s


def ocr_image(path):
    """用 Windows 自带 OCR 识别图片文字（按行返回），返回 (文字, 错误说明)。"""
    try:
        from winsdk.windows.media.ocr import OcrEngine
        from winsdk.windows.globalization import Language
        from winsdk.windows.storage import StorageFile, FileAccessMode
        from winsdk.windows.graphics.imaging import BitmapDecoder
    except Exception:
        return "", "系统 OCR 组件不可用，请安装 Windows 中文 OCR 语言包后重试"

    async def _run():
        f = await StorageFile.get_file_from_path_async(os.path.abspath(path))
        s = await f.open_async(FileAccessMode.READ)
        dec = await BitmapDecoder.create_async(s)
        bmp = await dec.get_software_bitmap_async()
        eng = OcrEngine.try_create_from_user_profile_languages()
        if eng is None:
            for tag in ("zh-Hans-CN", "zh-Hans", "en-US"):
                try:
                    eng = OcrEngine.try_create_from_language(Language(tag))
                except Exception:
                    eng = None
                if eng is not None:
                    break
        if eng is None:
            return None
        res = await eng.recognize_async(bmp)
        return [ln.text for ln in res.lines]

    try:
        lines = asyncio.run(_run())
    except Exception as e:
        return "", f"OCR 失败：{e}"
    if lines is None:
        return "", "系统未安装可用的 OCR 语言（需中文 OCR 语言包）"
    cleaned = [c for c in (_clean_line(x) for x in lines) if c]
    return "\n".join(cleaned), ""


def local_summarize(text):
    """免费本地整理：分行 + 提取关键信息，无需联网/Key。"""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return "（未从图片中识别到文字）"

    # 归一化：全角标点→半角、合并被 OCR 拆开的数字（"1 1"→"11"），提升关键信息提取稳健性
    trans = {"：": ":", "．": ".", "，": ",", "－": "-", "—": "-", "–": "-",
             "　": " ", "／": "/", "％": "%"}
    norm = "".join(trans.get(c, c) for c in text)
    norm = re.sub(r"(?<=\d)\s+(?=\d)", "", norm)
    dates = re.findall(r"\d{4}\s*[-/.年月一—–]\s*\d{1,2}\s*[-/.年月日一—–]\s*\d{1,2}\s*日?", text)
    dates = [re.sub(r"\s+", "", x) for x in dates]
    # 时间：容忍数字被 OCR 拆开、全角冒号与空格
    times = [re.sub(r"\s+", "", t).replace("：", ":")
             for t in re.findall(r"\d(?:\s*\d)?\s*[:：]\s*\d(?:\s*\d)?", text)]
    amounts = re.findall(r"(?:￥|¥|\$)?\s*[\d][\d,]*(?:\.\d+)?\s*(?:元|万元|万|亿|%|RMB)", norm)

    def uniq(seq):
        return list(dict.fromkeys(x.strip() for x in seq if x.strip()))

    out = [f"【免费本地整理 · 识别到 {len(lines)} 行文字】", ""]
    out += [f"· {l}" for l in lines[:50]]
    if len(lines) > 50:
        out.append(f"…（其余 {len(lines) - 50} 行省略）")

    key = []
    if dates:
        key.append("日期：" + "、".join(uniq(dates)))
    if times:
        key.append("时间：" + "、".join(uniq(times)))
    if amounts:
        key.append("金额/数值：" + "、".join(uniq(amounts)))
    if key:
        out += ["", "【关键信息】"] + [f"· {k}" for k in key]
    out += ["", "（提示：在「设置」填入 DeepSeek API Key 可获得更智能的摘要）"]
    return "\n".join(out)


def deepseek_summarize(text, api_key, timeout=60):
    text = (text or "").strip()
    if not text:
        return "（未从图片中识别到文字，无法生成摘要）"
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content":
             "你是中文助手。下面是从一张屏幕截图用 OCR 提取的文字，可能有少量识别错误。"
             "请用中文输出该截图内容的简洁要点摘要（3-6 条），不要逐字复述。"},
            {"role": "user", "content": text[:6000]},
        ],
        "temperature": 0.3,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_URL, data=data, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        obj = json.loads(r.read().decode("utf-8"))
    return obj["choices"][0]["message"]["content"].strip()


def summarize_image(path, api_key=""):
    """OCR → 组织摘要。返回 (摘要文本, 方式)。方式用于日志：
    免费本地 / DeepSeek / DeepSeek失败转免费本地 / OCR失败。"""
    text, err = ocr_image(path)
    if err:
        return f"[OCR 不可用] {err}", "OCR失败"
    if not (api_key or "").strip():
        return local_summarize(text), "免费本地"
    try:
        return "【DeepSeek 摘要】\n" + deepseek_summarize(text, api_key), "DeepSeek"
    except Exception as e:
        return (f"[DeepSeek 调用失败，已改用免费本地整理]\n原因：{e}\n\n"
                + local_summarize(text)), "DeepSeek失败转免费本地"
