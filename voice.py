"""离线中文语音识别（Vosk）。

放弃 Windows SAPI（Win11 上中文听写不出文字）。改用 Vosk 离线引擎：
- 用 sounddevice 从麦克风取 16k/单声道 PCM；
- 实时发出音量电平(level)，便于界面显示"是否拾到声音"（区分拾音 vs 识别）；
- 发出临时(partial)与最终(recognized)文字；是否触发抓拍由主窗口对文字做关键词匹配。

模型放在 程序根目录/models/vosk-cn （绿色版随程序分发，离线可用）。
任何依赖/模型/麦克风缺失时优雅降级并给出明确状态提示。
"""
import os
import json
import time
import queue

from PySide6.QtCore import QThread, Signal

from .paths import resource_dir

try:
    import numpy as np
    import sounddevice as sd
    import vosk
    _HAVE_VOSK = True
    _IMPORT_ERR = ""
except Exception as e:                      # pragma: no cover
    _HAVE_VOSK = False
    _IMPORT_ERR = str(e)


def model_dir():
    return os.path.join(resource_dir(), "models", "vosk-cn")


def list_input_devices():
    """返回可用麦克风输入设备 [(index, name), ...]；不可用时返回空表。"""
    if not _HAVE_VOSK:
        return []
    try:
        devices = sd.query_devices()
        return [(i, d["name"]) for i, d in enumerate(devices)
                if d.get("max_input_channels", 0) > 0]
    except Exception:
        return []


class VoiceController(QThread):
    recognized = Signal(str)        # 最终识别文字
    partial = Signal(str)           # 临时（边说边出）文字
    triggered = Signal()            # 命中关键词（立即触发抓拍）
    level = Signal(float)           # 实时音量 0..1（音量条用）
    status = Signal(str, bool)      # 状态消息, 是否正常

    # AGC 自动增益参数（偏保守：避免把背景噪声放大造成误识别）
    _NOISE_GATE = 0.006     # 低于此 RMS 视为静音/噪声，不放大
    _TARGET_RMS = 0.07      # 目标语音电平
    _MAX_GAIN = 5.0         # 最大放大倍数

    # 只用词表里确实存在的词（"抓屏""抓图"不在模型词表，加了会被忽略）
    def __init__(self, keywords=("抓拍", "截屏", "拍照"),
                 device=None, parent=None):
        super().__init__(parent)
        self.keywords = list(keywords)
        self.device = device        # 麦克风设备索引；None=系统默认
        self._running = False
        self._fs = 16000
        self._cooldown = 1.2        # 命中后冷却，避免同句重复触发
        self._last_trigger = 0.0
        self._gain = 1.0            # 平滑后的当前增益

    def stop(self):
        self._running = False
        self.wait(3000)

    def _hit(self, text):
        """文字含关键词且不在冷却期 → 触发，返回是否触发。"""
        compact = text.replace(" ", "")
        if any(k in compact for k in self.keywords):
            now = time.monotonic()
            if now - self._last_trigger > self._cooldown:
                self._last_trigger = now
                self.triggered.emit()
                return True
        return False

    def run(self):
        if not _HAVE_VOSK:
            self.status.emit(f"未安装语音依赖(vosk/sounddevice)：{_IMPORT_ERR}", False)
            return
        md = model_dir()
        if not os.path.isdir(md):
            self.status.emit("未找到离线中文语音模型（models/vosk-cn）", False)
            return

        self.status.emit("正在加载离线语音模型…", True)
        try:
            vosk.SetLogLevel(-1)
            model = vosk.Model(md)
            # 需求30：语法约束 —— 只在关键词与"其它([unk])"之间判断，
            # 大幅降低误识别/误触发（无关语句会判为 [unk]，不会命中）。
            grammar = json.dumps(list(self.keywords) + ["[unk]"], ensure_ascii=False)
            rec = vosk.KaldiRecognizer(model, self._fs, grammar)
        except Exception as e:
            self.status.emit(f"语音模型加载失败：{e}", False)
            return

        q = queue.Queue()

        def _callback(indata, frames, time_info, status_):
            q.put(bytes(indata))

        self._running = True
        try:
            # 需求30：稍大的块 → 解码更稳、错误率更低（略慢一点，可接受）
            with sd.RawInputStream(samplerate=self._fs, blocksize=3200,
                                   dtype="int16", channels=1, device=self.device,
                                   callback=_callback):
                self.status.emit(
                    "语音控制已开启（离线），说“" + self.keywords[0] + "”即可抓拍", True)
                while self._running:
                    try:
                        data = q.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    if arr.size:
                        rms = float(np.sqrt(np.mean(arr ** 2)))
                        # 音量条按"原始"电平显示，反映真实拾音
                        self.level.emit(min(1.0, rms * 8.0))
                        # 自动增益：偏小的语音放大到目标电平（带噪声门限/上限/平滑）
                        target_gain = 1.0
                        if rms > self._NOISE_GATE:
                            target_gain = min(self._MAX_GAIN,
                                              max(1.0, self._TARGET_RMS / rms))
                        self._gain = 0.7 * self._gain + 0.3 * target_gain
                        if self._gain > 1.05:
                            arr = np.clip(arr * self._gain, -1.0, 1.0)
                            data = (arr * 32767.0).astype(np.int16).tobytes()

                    # 需求30：只在"最终结果"匹配关键词才触发（比临时结果更准、更稳）
                    if rec.AcceptWaveform(data):
                        text = json.loads(rec.Result()).get("text", "").replace(" ", "")
                        if text:
                            self.recognized.emit(text)
                            self._hit(text)
                    else:
                        ptext = json.loads(rec.PartialResult()).get("partial", "").replace(" ", "")
                        if ptext:
                            self.partial.emit(ptext)   # 仅显示，不触发
        except Exception as e:
            self.status.emit(f"语音启动失败（麦克风/设备问题）：{e}", False)
        finally:
            self.level.emit(0.0)
