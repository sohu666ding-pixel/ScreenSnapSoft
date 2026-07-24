import os
import time
import shutil
import hashlib
import ctypes
from ctypes import wintypes
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QTimer, QSize, QPointF, QThread, QFile
from PySide6.QtGui import (QIcon, QPixmap, QPainter, QColor, QAction, QFont,
                           QPen, QPolygonF)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QSplitter, QTreeWidget, QTreeWidgetItem,
    QScrollArea, QFrame, QFileDialog, QDialog, QMessageBox, QSystemTrayIcon,
    QMenu, QSizePolicy, QProgressBar, QTextEdit,
    QSpinBox, QDialogButtonBox, QProgressDialog,
)

# 全局热键相关 Win32 常量
WM_HOTKEY = 0x0312
VK_SPACE = 0x20
MOD_NOREPEAT = 0x4000
HOTKEY_ID = 0xA17C

from .config import Config
from .storage import Storage
from . import capture as capture_mod
from . import thumbs as thumbs_mod
from .pdf_export import merge_to_pdf
from .voice import VoiceController, list_input_devices
from .ai_summary import summarize_image as ai_summarize_image
from . import logger

THUMB_W, THUMB_H = 320, 200

# 科技感深色主题（深蓝 navy + 青色 cyan 点缀）
ACCENT = "#19c2d6"        # 青色主强调
ACCENT2 = "#2b7fff"       # 蓝色次强调
ARROW_YELLOW = "#ffe082"  # 浅黄（缩略图左右箭头）

QSS = """
QWidget { font-family:'Microsoft YaHei','Segoe UI',sans-serif; font-size:12px; color:#dce8f7; }
QMainWindow { background:#0a1830; }
#artTitleBar { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
    stop:0 #071528, stop:0.48 #12365a, stop:1 #081a32);
    border-bottom:1px solid #2b7fff; }
#titleOrnament { color:#7fffd4; font-size:15px; letter-spacing:3px; }
#windowTitleText { color:#f4fbff; font-family:'STKaiti','KaiTi','Microsoft YaHei UI',serif;
    font-size:20px; font-weight:600; letter-spacing:3px; padding:2px 18px;
    background:transparent; }
#artTitleBar QPushButton { background:rgba(10,24,48,0.55); border:1px solid #295680;
    border-radius:5px; color:#dce8f7; font-size:15px; padding:0; }
#artTitleBar QPushButton:hover { background:#1a4670; border-color:#7fd6e6; }
#artTitleBar QPushButton:last-child { color:#ffd0d0; }
#artTitleBar QPushButton:last-child:hover { background:#d13438; color:#ffffff; }

#toolbar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #102a4e, stop:1 #0b1f3a);
           border-bottom:1px solid #1f4a7a; }
#toolbar QLabel { color:#9fc0e6; }

QPushButton { background:#13314f; border:1px solid #295680; border-radius:6px;
              padding:7px 13px; color:#dce8f7; }
QPushButton:hover { background:#1a4670; border-color:#3a7bb5; }
QPushButton:pressed { background:#0f2a40; }
QPushButton#primary { font-weight:600; color:#001018; border:1px solid #19c2d6;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #19c2d6, stop:1 #2b7fff); }
QPushButton#primary:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #34d6e8, stop:1 #4a93ff); }
QPushButton#voice:checked { background:#d13438; color:#ffffff; border:1px solid #ff5a5f; }
QPushButton#hotkey:checked { background:#19c2d6; color:#001018; border:2px solid #7fffd4;
    padding-top:9px; padding-bottom:5px; font-weight:700; }
#brandTitle { color:#ffffff; font-size:18px; font-weight:700; letter-spacing:2px;
    padding:5px 16px; border:1px solid #2b7fff; border-radius:14px;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(25,194,214,70), stop:1 rgba(43,127,255,90)); }
#clockLabel { color:#7fffd4; font-size:13px; font-weight:600; min-width:145px; }

QComboBox, QLineEdit { border:1px solid #2a4f80; border-radius:6px; padding:5px 8px;
    background:#0e2747; color:#eaf2fb; selection-background-color:#19c2d6; }
QComboBox:focus, QLineEdit:focus { border:1px solid #19c2d6; }
QComboBox QAbstractItemView { background:#0e2747; color:#eaf2fb;
    selection-background-color:#19c2d6; selection-color:#001018; border:1px solid #295680; }

#sidebar { background:#0b1f3a; border-right:1px solid #1f4a7a; }
#sideHead { color:#7fd6e6; font-weight:600; padding:8px 12px; border-bottom:1px solid #1f4a7a; }
QTreeWidget { border:none; background:transparent; color:#cfe0f3; }
QTreeWidget::item { height:28px; }
QTreeWidget::item:hover { background:#102e54; }
QTreeWidget::item:selected { background:rgba(25,194,214,0.20); color:#ffffff;
    border-left:3px solid #19c2d6; }

#preview { background:#08111f; }
#previewBar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #0e2747, stop:1 #0a1d36);
    border-bottom:1px solid #1f4a7a; }
#previewName { color:#ffffff; font-weight:600; }
#previewMeta { color:#7fa6cf; }

#thumbsHost { background:#0a1830; border-top:1px solid #1f4a7a; }
#thumbsHead { color:#7fd6e6; padding:6px 12px; border-bottom:1px solid #163a63; }

#statusBar { background:#0b1f3a; border-top:1px solid #1f4a7a; color:#7fa6cf; }
#statusBar QLabel { color:#9fc0e6; }

QScrollBar:horizontal { height:10px; background:transparent; margin:0; }
QScrollBar::handle:horizontal { background:#295680; border-radius:5px; min-width:40px; }
QScrollBar::handle:horizontal:hover { background:#3a7bb5; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }
QScrollBar:vertical { width:10px; background:transparent; margin:0; }
QScrollBar::handle:vertical { background:#295680; border-radius:5px; min-height:40px; }
QScrollBar::handle:vertical:hover { background:#3a7bb5; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }

QSplitter::handle { background:#1f4a7a; }
QSplitter::handle:hover { background:#19c2d6; }

#thumbArrow { border:none; border-radius:0;
    background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #123a63, stop:1 #0c2342); }
#thumbArrow:hover { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1d5891, stop:1 #143a66); }
#thumbArrow:pressed { background:#0a1d36; }

QMenu { background:#0e2747; color:#dce8f7; border:1px solid #295680; }
QMenu::item:selected { background:#19c2d6; color:#001018; }

QDialog { background:#0b1f3a; }
QMessageBox { background:#0b1f3a; }
QMessageBox QLabel { color:#dce8f7; }

#micLevel { background:#0e2747; border:1px solid #295680; border-radius:6px; }
#micLevel::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
    stop:0 #19c2d6, stop:1 #7fffd4); border-radius:5px; }

#summaryBox { background:#0e2747; border:1px solid #19c2d6; border-radius:8px; }
#summaryTitle { background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1a4670, stop:1 #123a63);
    border-top-left-radius:7px; border-top-right-radius:7px; }
#summaryBody { background:#0b1f3a; color:#dce8f7; border:none; padding:8px; font-size:13px; }
#sumBtn { background:#13314f; border:1px solid #295680; border-radius:4px; color:#dce8f7; padding:2px 8px; }
#sumBtn:hover { background:#1a4670; }
#sumClose { background:#d13438; border:1px solid #ff7b7f; color:#ffffff; font-size:16px; font-weight:700; border-radius:6px; }
#sumClose:hover { background:#ff4d52; border-color:#ffffff; }
"""


def make_app_icon():
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#005FB8"))
    p.drawRoundedRect(6, 18, 52, 38, 8, 8)
    p.drawRoundedRect(22, 9, 20, 12, 4, 4)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(23, 24, 18, 18)
    p.setBrush(QColor("#005FB8"))
    p.drawEllipse(28, 29, 8, 8)
    p.end()
    return QIcon(pm)


def make_chevron_icon(direction, color=ARROW_YELLOW, size=22):
    """绘制向左/向右的箭头(chevron)图标。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidth(3)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    m = size * 0.30
    cx = size / 2
    if direction == "left":
        pts = [(cx + m * 0.6, m), (cx - m * 0.7, cx), (cx + m * 0.6, size - m)]
    else:
        pts = [(cx - m * 0.6, m), (cx + m * 0.7, cx), (cx - m * 0.6, size - m)]
    p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in pts]))
    p.end()
    return QIcon(pm)


def cover_pixmap(path, w, h):
    pm = QPixmap(path)
    if pm.isNull():
        return pm
    scaled = pm.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (scaled.width() - w) // 2)
    y = max(0, (scaled.height() - h) // 2)
    return scaled.copy(x, y, w, h)


class PreviewLabel(QLabel):
    """右侧大图：等比缩放显示，双击切换窗口最大化（需求 3）。"""

    double_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("preview")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(200, 150)
        self._pix = None
        self.clear_image()

    def set_image(self, path):
        self._pix = QPixmap(path)
        self._render()

    def clear_image(self):
        self._pix = None
        self.setText("点击左侧目录或下方缩略图查看大图")
        self.setStyleSheet("color:#888888;")

    def _render(self):
        if not self._pix or self._pix.isNull():
            return
        self.setStyleSheet("")
        self.setPixmap(self._pix.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, e):
        self._render()
        super().resizeEvent(e)

    def mouseDoubleClickEvent(self, e):
        self.double_clicked.emit()


class ThumbCard(QFrame):
    """底部缩略图卡片（320×200 比例），高度可随容器缩放（需求23）。
    可获焦点，支持方向键切换上一张/下一张（需求35）。
    """

    clicked = Signal(str, object)
    nav = Signal(int)            # 方向键导航：-1 上一张 / +1 下一张
    scrub = Signal(str, int)     # 需求37：拖动浏览（起拖路径, 水平像素位移）
    summarize = Signal(str)      # 需求38：双击 → 调 DeepSeek 摘要
    delete_requested = Signal()
    CAP_H = 18

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._selected = False
        self._origin_x = None
        # 需求41：从缓存读 320×200 小图，避免每次解码全屏大图
        self._base = cover_pixmap(thumbs_mod.thumb_for(path), THUMB_W, THUMB_H)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.img = QLabel()
        self.img.setAlignment(Qt.AlignCenter)
        self.img.setStyleSheet("background:#000000;")

        self.cap = QLabel(os.path.basename(path))
        self.cap.setFixedHeight(self.CAP_H)
        self.cap.setStyleSheet("color:#a9c2dd; padding:1px 4px;")
        f = QFont(); f.setPointSize(8); self.cap.setFont(f)

        lay.addWidget(self.img)
        lay.addWidget(self.cap)
        self.set_thumb_height(THUMB_H)
        self.set_selected(False)
        self.setToolTip(os.path.basename(path))

    def set_thumb_height(self, h):
        """按 320:200 比例设置缩略图高度（容器变小则缩略图变小）。"""
        h = max(48, int(h))
        w = int(round(h * THUMB_W / THUMB_H))
        self.img.setFixedSize(w, h)
        self.cap.setFixedWidth(w)
        self.setFixedSize(w, h + self.CAP_H)
        if not self._base.isNull():
            self.img.setPixmap(self._base.scaled(
                w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_selected(self, on):
        self._selected = on
        color = ACCENT if on else "transparent"
        self.setStyleSheet(f"ThumbCard {{ border:2px solid {color}; border-radius:6px; }}")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._origin_x = e.globalPosition().x()   # 需求37：记录起拖位置
        self.setFocus()                 # 点击即获焦，方向键随后可用
        if e.button() == Qt.LeftButton:
            self._origin_x = e.globalPosition().x()
            self.setFocus()
            self.clicked.emit(self.path, e.modifiers())

    def mouseMoveEvent(self, e):
        # 需求37：左键按住左右拖动 → 快速浏览
        if (e.buttons() & Qt.LeftButton) and self._origin_x is not None:
            self.scrub.emit(self.path, int(e.globalPosition().x() - self._origin_x))

    def mouseReleaseEvent(self, e):
        self._origin_x = None

    def mouseDoubleClickEvent(self, e):
        self.summarize.emit(self.path)   # 需求38：双击 → 摘要

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Left, Qt.Key_Up):
            self.nav.emit(-1)
        elif k in (Qt.Key_Right, Qt.Key_Down):
            self.nav.emit(1)
        elif k in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_requested.emit()
        else:
            super().keyPressEvent(e)


class Toast(QWidget):
    """屏幕右下角的轻量提示，N 毫秒后自动消失；主窗口隐藏时也能显示。"""

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._label = QLabel(self)
        self._label.setStyleSheet(
            "background:rgba(28,28,30,238); color:#ffffff; padding:12px 18px;"
            " border-radius:10px; font-size:13px;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._label)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text, msec=2000):
        self._label.setText(text)
        self.adjustSize()
        geo = QApplication.primaryScreen().availableGeometry()
        self.move(geo.right() - self.width() - 24, geo.bottom() - self.height() - 24)
        self.show()
        self.raise_()
        self._timer.start(msec)


class FullscreenViewer(QWidget):
    """无边框全屏图片查看器（需求33）：
    ← / ↑ 上一张，→ / ↓ 下一张（轮询循环）；ESC 或双击退出。
    """

    def __init__(self, paths, index, on_change=None):
        super().__init__(None)
        self.setWindowTitle("全屏查看")
        self.setStyleSheet("background-color:#000000;")
        self.setFocusPolicy(Qt.StrongFocus)
        self._paths = list(paths)
        self._index = index
        self._on_change = on_change
        self._pix = QPixmap()

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet("background:#000000;")

        self._hint = QLabel("", self)
        self._hint.setStyleSheet(
            "color:rgba(255,255,255,190); background:rgba(0,0,0,150);"
            " padding:6px 14px; border-radius:14px;")

        self._load()

    def _load(self):
        if not self._paths:
            return
        self._index %= len(self._paths)            # 轮询循环
        path = self._paths[self._index]
        self._pix = QPixmap(path)
        self._hint.setText(
            f"←/↑ 上一张　·　→/↓ 下一张　·　{self._index + 1}/{len(self._paths)}　"
            f"{os.path.basename(path)}　·　ESC 退出")
        self._hint.adjustSize()
        self._fit()
        self._layout_children()
        if self._on_change:
            self._on_change(path)

    def _step(self, delta):
        if self._paths:
            self._index = (self._index + delta) % len(self._paths)
            self._load()

    def _fit(self):
        if self._pix.isNull():
            self._label.setText("无法加载图片")
            self._label.setStyleSheet("color:#888888; background:#000000;")
            return
        self._label.setStyleSheet("background:#000000;")
        self._label.setPixmap(self._pix.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _layout_children(self):
        self._label.setGeometry(self.rect())
        self._hint.move((self.width() - self._hint.width()) // 2,
                        self.height() - self._hint.height() - 36)
        self._hint.raise_()

    def showEvent(self, e):
        self._fit()
        self._layout_children()
        self.activateWindow()
        self.setFocus()
        super().showEvent(e)

    def resizeEvent(self, e):
        self._fit()
        self._layout_children()
        super().resizeEvent(e)

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Escape:
            self.close()
        elif k in (Qt.Key_Left, Qt.Key_Up):
            self._step(-1)
        elif k in (Qt.Key_Right, Qt.Key_Down):
            self._step(1)
        else:
            super().keyPressEvent(e)

    def mouseDoubleClickEvent(self, e):
        self.close()


class SummaryWorker(QThread):
    """后台执行 OCR + DeepSeek 摘要，避免阻塞界面（需求38）。"""
    done = Signal(str, str)        # 摘要文本, 方式

    def __init__(self, path, api_key, parent=None):
        super().__init__(parent)
        self.path = path
        self.api_key = api_key

    def run(self):
        try:
            text, mode = ai_summarize_image(self.path, self.api_key)
            self.done.emit(text, mode)
        except Exception as e:
            self.done.emit(f"摘要失败：{e}", "异常")


class SummaryBox(QFrame):
    """悬浮在右侧预览区左上角的摘要框（需求39）：400×300，标题左显图片名、
    右侧关闭按钮，内容支持复制。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("summaryBox")
        self.setFixedSize(400, 300)
        v = QVBoxLayout(self)
        v.setContentsMargins(1, 1, 1, 1)
        v.setSpacing(0)

        title = QWidget()
        title.setObjectName("summaryTitle")
        title.setFixedHeight(30)
        th = QHBoxLayout(title)
        th.setContentsMargins(10, 0, 6, 0)
        th.setSpacing(6)
        self.name_label = QLabel("图片摘要")
        self.name_label.setStyleSheet("color:#ffffff; font-weight:600;")
        self.btn_copy = QPushButton("复制")
        self.btn_copy.setObjectName("sumBtn")
        self.btn_copy.setFixedHeight(22)
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("sumClose")
        self.btn_close.setFixedSize(32, 26)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        th.addWidget(self.name_label, 1)
        th.addWidget(self.btn_copy)
        th.addWidget(self.btn_close)

        self.body = QTextEdit()
        self.body.setReadOnly(True)
        self.body.setObjectName("summaryBody")

        v.addWidget(title)
        v.addWidget(self.body, 1)
        self.btn_close.clicked.connect(self.hide)
        self.btn_copy.clicked.connect(self._copy)
        self.hide()

    def _copy(self):
        QApplication.clipboard().setText(self.body.toPlainText())

    def show_for(self, name):
        self.name_label.setText(name)
        self.name_label.setToolTip(name)
        self.body.setPlainText("正在识别图片文字并生成摘要，请稍候…")
        self.move(12, 44)        # 右侧预览区左上角（预览标题栏下方）
        self.show()
        self.raise_()

    def set_text(self, text):
        self.body.setPlainText(text)


class SettingsDialog(QDialog):
    """系统参数：抓拍主题 + 保存位置（需求 5）。"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("系统参数设置")
        self.setMinimumWidth(460)
        self.new_theme = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        root.addWidget(self._label("抓拍主题（设置后自动在保存位置下创建同名文件夹）"))
        self.theme_edit = QLineEdit()
        self.theme_edit.setPlaceholderText("例如：项目A现场")
        self.theme_edit.setText(config.theme)
        root.addWidget(self.theme_edit)

        root.addWidget(self._label("抓拍保存位置（根目录）"))
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(config.save_dir)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.dir_edit)
        row.addWidget(browse)
        root.addLayout(row)

        root.addWidget(self._label("该主题图片实际保存路径预览"))
        self.preview = QLabel()
        self.preview.setStyleSheet(
            "background:#0e2747; border:1px solid #295680; border-radius:4px;"
            " padding:6px 9px; color:#a9c2dd;")
        self.preview.setWordWrap(True)
        root.addWidget(self.preview)

        hint = self._label("文件名格式：主题名 + 抓拍时间.png，例如 项目A现场_20260528_143052.png")
        root.addWidget(hint)

        root.addWidget(self._label("麦克风设备（语音控制用；选错设备会拾不到声音）"))
        self.mic_combo = QComboBox()
        self.mic_combo.addItem("系统默认麦克风", None)
        for idx, name in list_input_devices():
            self.mic_combo.addItem(f"[{idx}] {name}", idx)
        cur = config.mic_device
        if cur is not None:
            for i in range(self.mic_combo.count()):
                if self.mic_combo.itemData(i) == cur:
                    self.mic_combo.setCurrentIndex(i)
                    break
        root.addWidget(self.mic_combo)

        root.addWidget(self._label("DeepSeek API Key（双击缩略图用 OCR+DeepSeek 生成截图摘要）"))
        self.key_edit = QLineEdit(config.api_key)
        self.key_edit.setPlaceholderText("sk-…（留空则不启用摘要功能）")
        self.key_edit.setEchoMode(QLineEdit.Password)
        root.addWidget(self.key_edit)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("保存并创建目录")
        ok.setObjectName("primary")
        ok.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        root.addLayout(btns)

        self.theme_edit.textChanged.connect(self._update_preview)
        self.dir_edit.textChanged.connect(self._update_preview)
        self._update_preview()

    def _label(self, text):
        lab = QLabel(text)
        lab.setStyleSheet("color:#9fc0e6;")
        return lab

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存位置", self.dir_edit.text())
        if d:
            self.dir_edit.setText(d)

    def _update_preview(self):
        theme = self.theme_edit.text().strip() or "<主题名>"
        self.preview.setText(os.path.join(self.dir_edit.text().strip(), theme) + os.sep)

    def _save(self):
        theme = self.theme_edit.text().strip()
        if not theme:
            QMessageBox.warning(self, "提示", "请填写抓拍主题")
            return
        self.config.save_dir = self.dir_edit.text().strip() or "picture"
        self.config.theme = theme
        self.config.mic_device = self.mic_combo.currentData()   # None 或设备索引
        self.config.api_key = self.key_edit.text().strip()
        self.config.save()
        self.new_theme = theme
        self.accept()


class BatchResizeDialog(QDialog):
    """批量按百分比缩放图片，并显示处理进度。"""

    def __init__(self, source_dir, parent=None):
        super().__init__(parent)
        self.source_dir = source_dir or os.getcwd()
        self.paths = self._scan_paths(self.source_dir)
        self.setWindowTitle("批量调整图片尺寸")
        self.setMinimumWidth(620)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)
        title = QLabel("按比例缩放所选照片")
        title.setStyleSheet("font-size:16px;font-weight:600;color:#ffffff;")
        root.addWidget(title)
        self.info = QLabel(f"已选择 {len(self.paths)} 张照片；横拍和竖拍会保持原比例")
        self.info.setStyleSheet("color:#9fc0e6;")
        root.addWidget(self.info)
        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("照片来源目录"))
        self.source_edit = QLineEdit(self.source_dir)
        src_row.addWidget(self.source_edit, 1)
        src_btn = QPushButton("选择目录")
        src_btn.clicked.connect(self._browse_source)
        src_row.addWidget(src_btn)
        root.addLayout(src_row)
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("修改后保存目录"))
        self.output_edit = QLineEdit(os.path.join(self.source_dir, "resized"))
        out_row.addWidget(self.output_edit, 1)
        out_btn = QPushButton("选择目录")
        out_btn.clicked.connect(self._browse_output)
        out_row.addWidget(out_btn)
        root.addLayout(out_row)
        row = QHBoxLayout()
        row.addWidget(QLabel("缩放比例"))
        self.percent = QSpinBox()
        self.percent.setRange(1, 500)
        self.percent.setValue(50)
        self.percent.setSuffix(" %")
        self.percent.valueChanged.connect(self._update_preview)
        row.addWidget(self.percent)
        row.addStretch(1)
        root.addLayout(row)
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        self.preview.setStyleSheet("background:#0e2747;border:1px solid #295680;border-radius:6px;padding:10px;color:#cfe0f3;")
        root.addWidget(self.preview)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.source_edit.textChanged.connect(self._update_preview)
        self.output_edit.textChanged.connect(self._update_preview)
        self._update_preview()

    def _scan_paths(self, directory):
        if not os.path.isdir(directory):
            return []
        return sorted(
            [os.path.join(directory, n) for n in os.listdir(directory)
             if n.lower().endswith((".png", ".jpg", ".jpeg"))],
            key=lambda p: os.path.getmtime(p))

    def _browse_source(self):
        d = QFileDialog.getExistingDirectory(self, "选择照片来源目录", self.source_edit.text())
        if d:
            self.source_edit.setText(d)
            self.output_edit.setText(os.path.join(d, "resized"))

    def _browse_output(self):
        d = QFileDialog.getExistingDirectory(self, "选择修改后保存目录", self.output_edit.text())
        if d:
            self.output_edit.setText(d)

    def selected_paths(self):
        return self._scan_paths(self.source_edit.text().strip())

    def output_dir(self):
        return self.output_edit.text().strip()

    def _update_preview(self):
        self.paths = self.selected_paths()
        self.info.setText(f"发现 {len(self.paths)} 张照片；横拍和竖拍均保持原比例")
        if not self.paths:
            self.preview.setText("没有可处理的图片")
            return
        pm = QPixmap(self.paths[0])
        if pm.isNull():
            self.preview.setText("无法读取图片分辨率")
            return
        p = self.percent.value() / 100.0
        w, h = max(1, round(pm.width() * p)), max(1, round(pm.height() * p))
        self.preview.setText(
            f"示例：{os.path.basename(self.paths[0])}\n"
            f"原始分辨率：{pm.width()} × {pm.height()} px\n"
            f"调整后分辨率：{w} × {h} px\n"
            "所有照片均按各自原始分辨率同比例调整")

    def percentage(self):
        return self.percent.value()


class PdfMergeDialog(QDialog):
    """PDF 合并来源和输出参数设置。"""

    def __init__(self, source_dir, default_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("合并图片为 PDF")
        self.setMinimumWidth(620)
        self._output_dirty = False
        self._syncing_output = False
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)
        title = QLabel("选择图片目录并生成 PDF")
        title.setStyleSheet("font-size:16px;font-weight:600;color:#ffffff;")
        root.addWidget(title)
        self.info = QLabel()
        self.info.setStyleSheet("color:#9fc0e6;")
        root.addWidget(self.info)

        src = QHBoxLayout()
        src.addWidget(QLabel("图片来源目录"))
        self.source_edit = QLineEdit(source_dir)
        src.addWidget(self.source_edit, 1)
        b1 = QPushButton("选择目录")
        b1.clicked.connect(self._browse_source)
        src.addWidget(b1)
        root.addLayout(src)

        out = QHBoxLayout()
        out.addWidget(QLabel("PDF 输出目录"))
        self.output_edit = QLineEdit(source_dir)
        out.addWidget(self.output_edit, 1)
        b2 = QPushButton("选择目录")
        b2.clicked.connect(self._browse_output)
        out.addWidget(b2)
        root.addLayout(out)

        name = QHBoxLayout()
        name.addWidget(QLabel("PDF 文件名"))
        self.name_edit = QLineEdit(default_name)
        self.name_edit.setPlaceholderText("例如：项目汇总.pdf")
        name.addWidget(self.name_edit, 1)
        root.addLayout(name)

        self.source_edit.textChanged.connect(self._source_changed)
        self.output_edit.textChanged.connect(self._output_changed)
        self.name_edit.textChanged.connect(self._update_info)
        self._update_info()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse_source(self):
        d = QFileDialog.getExistingDirectory(self, "选择图片来源目录", self.source_edit.text())
        if d:
            self.source_edit.setText(d)
    
    def _browse_output(self):
        d = QFileDialog.getExistingDirectory(self, "选择 PDF 输出目录", self.output_edit.text())
        if d:
            self._output_dirty = True
            self.output_edit.setText(d)

    def _source_changed(self, source):
        if not self._output_dirty:
            self._syncing_output = True
            self.output_edit.setText(source)
            self._syncing_output = False
        self._update_info()

    def _output_changed(self, _text):
        if not self._syncing_output:
            self._output_dirty = True
        self._update_info()

    def _paths(self):
        d = self.source_edit.text().strip()
        if not os.path.isdir(d):
            return []
        return sorted(
            [os.path.join(d, n) for n in os.listdir(d)
             if n.lower().endswith((".png", ".jpg", ".jpeg"))],
            key=lambda p: os.path.getmtime(p))

    def _update_info(self):
        self.info.setText(f"当前目录发现 {len(self._paths())} 张图片，按文件修改时间顺序合并")

    def _accept(self):
        if not self._paths():
            QMessageBox.warning(self, "无法合并", "来源目录没有 PNG/JPG 图片")
            return
        if not self.output_edit.text().strip():
            QMessageBox.warning(self, "无法合并", "请填写 PDF 输出目录")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "无法合并", "请填写 PDF 文件名")
            return
        self.accept()

    def selected_paths(self):
        return self._paths()

    def output_path(self):
        name = self.name_edit.text().strip()
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        return os.path.join(self.output_edit.text().strip(), name)


class ArtisticTitleBar(QWidget):
    """自绘的艺术化窗口标题头，替代系统原生标题栏。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self.setFixedHeight(42)
        self.setObjectName("artTitleBar")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 8, 0)
        lay.setSpacing(8)

        ornament = QLabel("◆  ◇")
        ornament.setObjectName("titleOrnament")
        lay.addWidget(ornament)
        lay.addStretch(1)

        title = QLabel("智能屏幕抓拍管理工具")
        title.setObjectName("windowTitleText")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)
        lay.addStretch(1)

        self.min_btn = QPushButton("—")
        self.max_btn = QPushButton("□")
        self.close_btn = QPushButton("×")
        for btn in (self.min_btn, self.max_btn, self.close_btn):
            btn.setFixedSize(34, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            lay.addWidget(btn)
        self.min_btn.clicked.connect(lambda: self.window().showMinimized())
        self.max_btn.clicked.connect(self._toggle_maximize)
        self.close_btn.clicked.connect(lambda: self.window().close())

    def _toggle_maximize(self):
        w = self.window()
        if w.isMaximized():
            w.showNormal()
            self.max_btn.setText("□")
        else:
            w.showMaximized()
            self.max_btn.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()


class MainWindow(QMainWindow):
    # 跨线程：语音识别在后台线程，用信号回到 GUI 线程触发
    voice_trigger = Signal()

    def __init__(self, app_icon):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.app_icon = app_icon
        self.config = Config()
        self.storage = Storage(self.config)
        self.current_theme = self.config.theme
        self.selected_path = None
        self.selected_thumb_paths = set()
        self._thumb_anchor = None
        self.thumb_cards = {}
        self.voice = None
        self._viewer = None
        self._quick_mode = False
        self._sized_once = False
        self._thumb_h = THUMB_H
        self._voice_max_level = 0.0
        self._sum_worker = None
        self._pending_thumbs = []
        self._thumb_index = 0
        self.toast = Toast()
        # 需求41：缩略图增量构建定时器（分批，避免启动卡顿）
        self._thumb_timer = QTimer(self)
        self._thumb_timer.setInterval(0)
        self._thumb_timer.timeout.connect(self._build_thumbs_batch)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        # Win32 全局热键函数签名（64 位下 HWND 必须按指针宽度传递）
        self._user32 = ctypes.windll.user32
        self._user32.RegisterHotKey.argtypes = [
            wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self._user32.RegisterHotKey.restype = wintypes.BOOL
        self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self._user32.UnregisterHotKey.restype = wintypes.BOOL

        self.setWindowTitle("桌面抓图软件")
        self.setWindowIcon(app_icon)
        self.resize(1200, 800)
        self.setStyleSheet(QSS)

        # 需求21：启动时扫描 picture 下已有主题目录
        existing = self.storage.list_themes()
        if existing:
            if self.current_theme not in existing:
                self.current_theme = existing[0]
                self.config.theme = self.current_theme
        else:
            self.storage.ensure_theme(self.current_theme)   # 全新：建默认主题

        self._build_ui()
        self._build_tray()
        self.refresh_all()

    # ---------------- UI 构建 ----------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(ArtisticTitleBar(self))
        outer.addWidget(self._build_toolbar())

        # 上：左右分栏（目录 | 预览）
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        self.splitter.addWidget(self._build_sidebar())
        self.splitter.addWidget(self._build_preview())
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        # 需求20：主区域与下方缩略图区之间垂直拖拉，下方可折叠隐藏
        self.vsplitter = QSplitter(Qt.Vertical)
        self.vsplitter.setHandleWidth(6)
        self.vsplitter.setChildrenCollapsible(True)   # 拖到最小以下可折叠隐藏
        self.vsplitter.addWidget(self.splitter)
        self.vsplitter.addWidget(self._build_thumbs())
        self.vsplitter.setStretchFactor(0, 1)
        self.vsplitter.setStretchFactor(1, 0)
        self.vsplitter.splitterMoved.connect(lambda *_: self._apply_thumb_height())
        outer.addWidget(self.vsplitter, 1)

        outer.addWidget(self._build_statusbar())

    def _build_toolbar(self):
        bar = QWidget()
        bar.setObjectName("toolbar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)

        lay.addWidget(QLabel("抓拍主题"))
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(160)
        self.theme_combo.setEditable(True)               # 需求14：可编辑，直接输入新主题
        self.theme_combo.setInsertPolicy(QComboBox.NoInsert)
        self.theme_combo.lineEdit().setPlaceholderText("输入新主题后回车")
        self.theme_combo.textActivated.connect(self._on_theme_selected)
        self.theme_combo.lineEdit().returnPressed.connect(self._on_theme_entered)
        lay.addWidget(self.theme_combo)

        lay.addWidget(QLabel("保存位置"))
        self.dir_label = QLineEdit(self.config.save_dir)
        self.dir_label.setReadOnly(True)
        self.dir_label.setMinimumWidth(200)
        lay.addWidget(self.dir_label)

        browse = QPushButton("📁 浏览")
        browse.clicked.connect(self._browse_dir)
        lay.addWidget(browse)

        lay.addStretch(1)

        self.btn_hotkey = QPushButton("⌨ 快捷键抓拍")
        self.btn_hotkey.setObjectName("hotkey")
        self.btn_hotkey.setCheckable(True)
        self.btn_hotkey.setToolTip("点击后窗口收起到托盘，按【空格】即可抓屏；还原窗口退出")
        self.btn_hotkey.toggled.connect(self._toggle_hotkey)
        lay.addWidget(self.btn_hotkey)

        self.btn_voice = QPushButton("🎤 语音控制")
        self.btn_voice.setObjectName("voice")
        self.btn_voice.setCheckable(True)
        self.btn_voice.toggled.connect(self._toggle_voice)
        lay.addWidget(self.btn_voice)

        self.btn_pdf = QPushButton("📄 合并为 PDF")
        self.btn_pdf.clicked.connect(self.do_merge_pdf)
        lay.addWidget(self.btn_pdf)

        self.btn_resize = QPushButton("▣ 批量尺寸")
        self.btn_resize.setToolTip("按百分比批量调整当前主题图片尺寸")
        self.btn_resize.clicked.connect(self.open_batch_resize)
        lay.addWidget(self.btn_resize)

        self.btn_settings = QPushButton("⚙️ 设置")
        self.btn_settings.clicked.connect(self.open_settings)
        lay.addWidget(self.btn_settings)

        lay.addSpacing(8)
        self.clock_label = QLabel()
        self.clock_label.setObjectName("clockLabel")
        self.clock_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.clock_label)
        self._update_clock()

        return bar

    def _update_clock(self):
        if hasattr(self, "clock_label"):
            self.clock_label.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))

    def _build_sidebar(self):
        side = QWidget()
        side.setObjectName("sidebar")
        side.setMinimumWidth(150)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        head = QLabel("抓拍目录　·　两级 (主题 / 照片)")
        head.setObjectName("sideHead")
        lay.addWidget(head)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.installEventFilter(self)
        self.tree.itemClicked.connect(self._on_tree_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_menu)
        lay.addWidget(self.tree, 1)
        return side

    def _build_preview(self):
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        bar = QWidget()
        bar.setObjectName("previewBar")
        bar.setFixedHeight(34)
        blay = QHBoxLayout(bar)
        blay.setContentsMargins(14, 0, 14, 0)
        self.pv_name = QLabel("未选择图片")
        self.pv_name.setObjectName("previewName")
        self.pv_meta = QLabel("")
        self.pv_meta.setObjectName("previewMeta")
        blay.addWidget(self.pv_name)
        blay.addWidget(self.pv_meta)
        blay.addStretch(1)
        lay.addWidget(bar)

        self.preview = PreviewLabel()
        self.preview.setFocusPolicy(Qt.StrongFocus)
        self.preview.installEventFilter(self)
        self.preview.double_clicked.connect(self.open_fullscreen)
        self.preview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.preview.customContextMenuRequested.connect(self._on_preview_menu)
        lay.addWidget(self.preview, 1)
        # 需求39：悬浮摘要框，父级为预览容器，浮在左上角
        self.summary_box = SummaryBox(wrap)
        return wrap

    def _selected_tree_paths(self):
        paths = []
        for item in self.tree.selectedItems():
            data = item.data(0, Qt.UserRole)
            if data and data[0] == "shot" and os.path.exists(data[1]):
                paths.append(data[1])
            elif data and data[0] == "theme":
                paths.extend(self.storage.list_shots(data[1]))
        return list(dict.fromkeys(paths))

    def open_batch_resize(self):
        return self._open_batch_resize_new()

    def _open_batch_resize_new(self):
        base = os.path.dirname(self.selected_path) if self.selected_path else self.storage.theme_dir(self.current_theme)
        dlg = BatchResizeDialog(base, self)
        if dlg.exec() != QDialog.Accepted:
            return
        paths = dlg.selected_paths()
        output_dir = dlg.output_dir() or os.path.join(base, "resized")
        if not paths:
            QMessageBox.information(self, "批量调整尺寸", "来源目录没有可处理的图片")
            return
        os.makedirs(output_dir, exist_ok=True)
        percent = dlg.percentage() / 100.0
        progress = QProgressDialog("准备处理…", "取消", 0, len(paths), self)
        progress.setWindowTitle("批量处理进度")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        changed = 0
        logs = [f"来源目录：{dlg.source_edit.text()}", f"输出目录：{output_dir}", f"缩放比例：{dlg.percentage()}%"]
        for i, path in enumerate(paths):
            QApplication.processEvents()
            if progress.wasCanceled():
                logs.append("用户取消了后续处理")
                break
            src = QPixmap(path)
            if src.isNull():
                logs.append(f"跳过：{os.path.basename(path)}")
                progress.setValue(i + 1)
                continue
            w = max(1, round(src.width() * percent))
            h = max(1, round(src.height() * percent))
            target = os.path.join(output_dir, os.path.basename(path))
            ok = src.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(target)
            logs.append(f"{'完成' if ok else '失败'}：{os.path.basename(path)} -> {w}×{h}")
            if ok:
                changed += 1
            progress.setLabelText(logs[-1])
            progress.setValue(i + 1)
        progress.close()
        log_path = os.path.join(output_dir, "resize.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(logs) + f"\n成功：{changed} 张\n")
        QMessageBox.information(self, "批量处理日志", "\n".join(logs[-12:]) + f"\n\n完整日志：{log_path}")
        self._toast(f"已完成 {changed} 张图片的尺寸调整", 2500)

    # 保留旧实现代码作为兼容参考，实际入口由 _open_batch_resize_new 处理。
    def _open_batch_resize_legacy(self):
        base = os.path.dirname(self.selected_path) if self.selected_path else self.storage.theme_dir(self.current_theme)
        paths = self._selected_tree_paths()
        if not paths:
            paths = self.storage.list_shots(self.current_theme)
        if not paths:
            QMessageBox.information(self, "批量调整尺寸", "当前主题没有可处理的图片")
            return
        dlg = BatchResizeDialog(base, self)
        if dlg.exec() != QDialog.Accepted:
            return
        paths = dlg.selected_paths()
        output_dir = dlg.output_dir() or os.path.join(base, "resized")
        if not paths:
            QMessageBox.information(self, "批量调整尺寸", "来源目录没有可处理的图片")
            return
        os.makedirs(output_dir, exist_ok=True)
        percent = dlg.percentage() / 100.0
        progress = QProgressDialog("正在调整图片尺寸…", "取消", 0, len(paths), self)
        progress.setWindowTitle("批量处理进度")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        changed = 0
        logs = [f"来源目录：{base}", f"输出目录：{output_dir}", f"缩放比例：{dlg.percentage()}%"]
        for i, path in enumerate(paths):
            QApplication.processEvents()
            if progress.wasCanceled():
                logs.append("用户取消了后续处理")
                break
            src = QPixmap(path)
            if src.isNull():
                logs.append(f"跳过（无法读取）：{os.path.basename(path)}")
                progress.setValue(i + 1)
                continue
            w = max(1, round(src.width() * percent))
            h = max(1, round(src.height() * percent))
            scaled = src.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            target = os.path.join(output_dir, os.path.basename(path))
            if scaled.save(target):
                changed += 1
                logs.append(f"完成：{os.path.basename(path)} -> {w}×{h}")
            else:
                logs.append(f"失败：{os.path.basename(path)}")
            progress.setLabelText(logs[-1])
            progress.setValue(i + 1)
        progress.close()
        log_path = os.path.join(output_dir, "resize.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(logs) + f"\n成功：{changed} 张\n")
        except OSError:
            log_path = ""
        QMessageBox.information(
            self, "批量处理日志",
            "\n".join(logs[-min(len(logs), 12):]) +
            (f"\n\n完整日志：{log_path}" if log_path else ""))
        if self.selected_path and os.path.exists(self.selected_path):
            self.select_shot(self.selected_path)
        self._toast(f"已完成 {changed} 张图片的尺寸调整", 2500)

    def _delete_paths(self, paths):
        paths = [p for p in dict.fromkeys(paths) if os.path.isfile(p)]
        if not paths:
            return
        if QMessageBox.question(
                self, "删除图片", f"确定删除选中的 {len(paths)} 张图片？此操作不可恢复。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        for path in paths:
            try:
                os.remove(path)
            except OSError:
                pass
        if self.selected_path in paths:
            self.selected_path = None
            self.preview.clear_image()
            self.pv_name.setText("未选择图片")
            self.pv_meta.setText("")
        self.refresh_all()
        self._toast(f"已删除 {len(paths)} 张图片", 1800)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            paths = self._selected_tree_paths()
            if self.selected_path and self.preview.hasFocus():
                paths = [self.selected_path]
            if paths:
                self._delete_paths(paths)
                e.accept()
                return
        super().keyPressEvent(e)

    def eventFilter(self, obj, e):
        if e.type() == e.Type.KeyPress and e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            paths = self._selected_tree_paths()
            if obj is self.preview and self.selected_path:
                paths = [self.selected_path]
            if paths:
                self._delete_paths(paths)
                return True
        return super().eventFilter(obj, e)

    def _make_arrow(self, direction, tip):
        # 需求24：箭头图标 + 顶满整个下方区域高度 + 宽度较窄
        b = QPushButton()
        b.setObjectName("thumbArrow")
        b.setIcon(make_chevron_icon(direction))
        b.setIconSize(QSize(14, 16))
        b.setFixedWidth(14)              # 需求31：箭头块更窄
        b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tip)
        b.clicked.connect(lambda: self._scroll_thumbs(-1 if direction == "left" else 1))
        return b

    def _build_thumbs(self):
        host = QWidget()
        host.setObjectName("thumbsHost")
        # 需求20：默认高度由 vsplitter 设为 320，可拖拉；最大 320、最小 100，更小则折叠隐藏
        host.setMinimumHeight(100)
        host.setMaximumHeight(320)

        # 需求24：箭头块在最外层左右，顶满整个下方区域高度
        outer = QHBoxLayout(host)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.btn_thumb_left = self._make_arrow("left", "向左")
        self.btn_thumb_right = self._make_arrow("right", "向右")

        center = QWidget()
        lay = QVBoxLayout(center)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 需求25：标题栏压低、文字居中固定（不随缩略图容器变长而移动）
        self.thumbs_head = QLabel("缩略图　·　320×200　·　从左到右排列，可横向滚动")
        self.thumbs_head.setObjectName("thumbsHead")
        self.thumbs_head.setAlignment(Qt.AlignCenter)
        self.thumbs_head.setFixedHeight(24)
        lay.addWidget(self.thumbs_head)

        self.thumb_scroll = QScrollArea()
        self.thumb_scroll.setObjectName("thumbScroll")
        self.thumb_scroll.setFrameShape(QFrame.NoFrame)
        self.thumb_scroll.setWidgetResizable(True)
        self.thumb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.thumb_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.thumb_container = QWidget()
        self.thumb_layout = QHBoxLayout(self.thumb_container)
        self.thumb_layout.setContentsMargins(10, 6, 10, 6)
        self.thumb_layout.setSpacing(12)
        self.thumb_layout.addStretch(1)
        self.thumb_scroll.setWidget(self.thumb_container)
        # 让深色背景透出来，避免滚动区默认浅色底
        self.thumb_scroll.viewport().setStyleSheet("background:transparent;")
        self.thumb_container.setStyleSheet("background:transparent;")
        lay.addWidget(self.thumb_scroll, 1)

        outer.addWidget(self.btn_thumb_left)
        outer.addWidget(center, 1)
        outer.addWidget(self.btn_thumb_right)
        return host

    def _scroll_thumbs(self, direction):
        """点击左右滑块横向滚动缩略图（一次约两张）。"""
        sb = self.thumb_scroll.horizontalScrollBar()
        step = (self._thumb_h * THUMB_W // THUMB_H + 12) * 2
        sb.setValue(sb.value() + direction * step)

    def _apply_thumb_height(self):
        """需求23：根据下方容器当前高度，同步缩放所有缩略图。"""
        vp = self.thumb_scroll.viewport().height()
        if vp <= 10:
            return
        img_h = max(48, min(THUMB_H, vp - 12 - ThumbCard.CAP_H))
        if img_h == self._thumb_h:
            return
        self._thumb_h = img_h
        for card in self.thumb_cards.values():
            card.set_thumb_height(img_h)

    def _build_statusbar(self):
        bar = QWidget()
        bar.setObjectName("statusBar")
        bar.setFixedHeight(28)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 14, 0)
        self.st_theme = QLabel()
        self.st_count = QLabel()
        self.st_voice = QLabel()
        # 实时音量条：直观确认麦克风是否拾到声音
        self.st_level = QProgressBar()
        self.st_level.setObjectName("micLevel")
        self.st_level.setFixedSize(90, 12)
        self.st_level.setRange(0, 100)
        self.st_level.setValue(0)
        self.st_level.setTextVisible(False)
        self.st_level.setToolTip("麦克风音量：对着麦克风说话应有跳动")
        self.st_heard = QLabel()        # 需求22：显示听到/识别的文字
        self.st_heard.setStyleSheet("color:#7fd6e6;")
        lay.addWidget(self.st_theme)
        lay.addWidget(self.st_count)
        lay.addWidget(self.st_voice)
        lay.addWidget(self.st_level)
        lay.addWidget(self.st_heard, 1)
        lay.addStretch(0)
        self.st_path = QLabel()
        lay.addWidget(self.st_path)
        return bar

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self.app_icon, self)
        self.tray.setToolTip("桌面抓图软件")
        menu = QMenu()
        act_show = QAction("显示主窗口", self)
        act_show.triggered.connect(self._restore_window)
        act_cap = QAction("立即抓屏", self)
        act_cap.triggered.connect(lambda: self.do_capture(""))
        self.act_exit_quick = QAction("退出快捷抓拍模式", self)
        self.act_exit_quick.setVisible(False)
        self.act_exit_quick.triggered.connect(self.exit_quick_mode)
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self._quit)
        menu.addAction(act_show)
        menu.addAction(act_cap)
        menu.addAction(self.act_exit_quick)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        # 语音识别触发抓拍（来源标记为"语音"）
        self.voice_trigger.connect(lambda: self.do_capture("语音"))

    # ---------------- 数据刷新 ----------------
    def refresh_all(self):
        self._refresh_combo()
        self._refresh_tree()
        self._refresh_thumbs()
        self._refresh_status()
        self.dir_label.setText(self.config.save_dir)

    def _refresh_combo(self):
        themes = self.storage.list_themes()
        if self.current_theme not in themes:
            themes.append(self.current_theme)
            themes.sort()
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItems(themes)
        idx = self.theme_combo.findText(self.current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)

    def _refresh_tree(self):
        self.tree.clear()
        for theme in self.storage.list_themes():
            shots = self.storage.list_shots(theme)
            top = QTreeWidgetItem(self.tree, [f"📁 {theme}  ({len(shots)})"])
            top.setData(0, Qt.UserRole, ("theme", theme))
            for path in shots:
                child = QTreeWidgetItem(top, [f"🖼 {os.path.basename(path)}"])
                child.setData(0, Qt.UserRole, ("shot", path))
            if theme == self.current_theme:
                top.setExpanded(True)
                self.tree.setCurrentItem(top)

    def _refresh_thumbs(self):
        # 停止上一轮未完成的增量构建
        self._thumb_timer.stop()
        # 清空（保留末尾 stretch）
        while self.thumb_layout.count() > 1:
            item = self.thumb_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.thumb_cards = {}

        shots = self.storage.list_shots(self.current_theme)
        self.selected_thumb_paths.intersection_update(shots)
        if self.selected_path in shots and not self.selected_thumb_paths:
            self.selected_thumb_paths.add(self.selected_path)
        self.thumbs_head.setText(
            f"缩略图 — {self.current_theme}　·　320×200　·　从左到右排列，可横向滚动")
        if not shots:
            empty = QLabel("该主题暂无抓拍图片，点击「抓屏」开始")
            empty.setStyleSheet("color:#7fa6cf; padding:20px;")
            self.thumb_layout.insertWidget(0, empty)
            return
        # 需求41：增量分批构建，先让界面出来，缩略图随后逐批填充
        self._pending_thumbs = shots
        self._thumb_index = 0
        self._thumb_timer.start()

    def _build_thumbs_batch(self):
        BATCH = 6
        for _ in range(BATCH):
            if self._thumb_index >= len(self._pending_thumbs):
                self._thumb_timer.stop()
                self._apply_thumb_height()
                for selected in self.selected_thumb_paths:
                    if selected in self.thumb_cards:
                        self.thumb_cards[selected].set_selected(True)
                return
            path = self._pending_thumbs[self._thumb_index]
            self._thumb_index += 1
            card = ThumbCard(path)
            card.set_thumb_height(self._thumb_h)
            card.clicked.connect(self._on_thumb_clicked)
            card.delete_requested.connect(self._delete_selected_thumbs)
            card.nav.connect(self._nav_thumb)          # 需求35：方向键切换
            card.scrub.connect(self._scrub)            # 需求37：拖动浏览
            card.summarize.connect(self.summarize_image)  # 需求38：双击摘要
            if path in self.selected_thumb_paths:
                card.set_selected(True)
            # 插到末尾 stretch 之前
            self.thumb_layout.insertWidget(self.thumb_layout.count() - 1, card)
            self.thumb_cards[path] = card

    def _on_thumb_clicked(self, path, modifiers):
        """处理缩略图的普通、Ctrl、Shift 多选。"""
        shots = self.storage.list_shots(self.current_theme)
        if path not in shots:
            return
        mods = modifiers or Qt.KeyboardModifier.NoModifier
        if mods & Qt.KeyboardModifier.ShiftModifier and self._thumb_anchor in shots:
            a, b = shots.index(self._thumb_anchor), shots.index(path)
            lo, hi = sorted((a, b))
            self.selected_thumb_paths = set(shots[lo:hi + 1])
        elif mods & Qt.KeyboardModifier.ControlModifier:
            if path in self.selected_thumb_paths:
                self.selected_thumb_paths.remove(path)
            else:
                self.selected_thumb_paths.add(path)
            self._thumb_anchor = path
        else:
            self.selected_thumb_paths = {path}
            self._thumb_anchor = path
        self.select_shot(path, preserve_thumb_selection=True)

    def _delete_selected_thumbs(self):
        paths = [p for p in self.selected_thumb_paths if os.path.isfile(p)]
        if not paths and self.selected_path:
            paths = [self.selected_path]
        if paths:
            self._delete_paths(paths)
            self.selected_thumb_paths.difference_update(paths)
            self._thumb_anchor = None

    def _scrub(self, origin_path, dx):
        """需求37：左键按住左右拖动，快速浏览照片（位置式，钳制不轮询）。"""
        shots = self.storage.list_shots(self.current_theme)
        if origin_path not in shots:
            return
        base = shots.index(origin_path)
        idx = base + int(round(dx / 28.0))            # 每约 28px 切一张
        idx = max(0, min(len(shots) - 1, idx))
        path = shots[idx]
        if path != self.selected_path:
            self.select_shot(path)

    def summarize_image(self, path):
        """需求38：双击缩略图 → 免费 OCR 识别 + 整理摘要（有 Key 则用 DeepSeek 增强）。"""
        if not path or not os.path.exists(path):
            return
        self.summary_box.show_for(os.path.basename(path))
        self._sum_path = path
        # 无 Key 也可用：免费本地整理；有 Key 用 DeepSeek。均在后台线程进行。
        self._sum_worker = SummaryWorker(path, self.config.api_key, self)
        self._sum_worker.done.connect(self._on_summary_done)
        self._sum_worker.start()

    def _on_summary_done(self, text, mode):
        self.summary_box.set_text(text)
        logger.log("摘要", f"[{mode}] {os.path.basename(self._sum_path)}")

    def _nav_thumb(self, delta):
        """需求35：在缩略图间按方向键轮询切换，并联动右侧大图。"""
        shots = self.storage.list_shots(self.current_theme)
        if not shots:
            return
        idx = shots.index(self.selected_path) if self.selected_path in shots else 0
        idx = (idx + delta) % len(shots)          # 轮询循环
        path = shots[idx]
        self.select_shot(path)
        card = self.thumb_cards.get(path)
        if card:
            card.setFocus()                        # 焦点跟随，便于连续翻看
            self._scroll_to_card(card)             # 设焦后再居中，确保始终可见

    def _refresh_status(self):
        count = len(self.storage.list_shots(self.current_theme))
        on = self.btn_voice.isChecked()
        self.st_theme.setText(f"主题：{self.current_theme}")
        self.st_count.setText(f"共 {count} 张")
        self.st_voice.setText("● 语音：聆听中…" if on else "○ 语音：关闭")
        self.st_path.setText(
            "保存目录：" + os.path.join(self.config.save_dir, self.current_theme) + os.sep)

    # ---------------- 交互 ----------------
    def switch_theme(self, theme, create=False):
        """切换当前主题；create=True 时先创建同名目录（需求14/5）。"""
        theme = (theme or "").strip()
        if not theme:
            return
        if not create and theme == self.current_theme:
            return
        if create:
            self.storage.ensure_theme(theme)
        self.current_theme = theme
        self.config.theme = theme
        self.config.save()
        self.selected_path = None
        self.preview.clear_image()
        self.pv_name.setText("未选择图片")
        self.pv_meta.setText("")
        self.refresh_all()

    def _on_theme_selected(self, text):
        # 从下拉中选了已有主题
        self.switch_theme(text, create=False)

    def _on_theme_entered(self):
        # 在可编辑框里输入新主题并回车 → 创建并切换为最新主题
        text = self.theme_combo.currentText().strip()
        if not text:
            return
        is_new = text not in self.storage.list_themes()
        self.switch_theme(text, create=True)
        if is_new:
            self._toast(f"已创建并切换到主题【{text}】", 2000)

    def _on_tree_clicked(self, item, _col):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        kind, value = data
        if kind == "theme":
            if value != self.current_theme:
                self.current_theme = value
                self.config.theme = value
                self.config.save()
                self._refresh_combo()
                self._refresh_thumbs()
                self._refresh_status()
            item.setExpanded(not item.isExpanded())
        else:
            self.current_theme = os.path.basename(os.path.dirname(value))
            self.select_shot(value)

    def _on_tree_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        kind, value = data
        menu = QMenu(self)
        if kind == "shot":
            act_view = menu.addAction("查看")
            act_reveal = menu.addAction("打开所在文件夹")
            menu.addSeparator()
            act_del = menu.addAction("删除图片")
            selected_paths = self._selected_tree_paths()
            if len(selected_paths) > 1:
                act_del.setText(f"删除选中图片 ({len(selected_paths)})")
            chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if chosen == act_view:
                self.current_theme = os.path.basename(os.path.dirname(value))
                self.select_shot(value)
            elif chosen == act_reveal:
                self._reveal(os.path.dirname(value))
            elif chosen == act_del:
                self._delete_paths(selected_paths or [value])
        else:
            act_refresh = menu.addAction("刷新目录")        # 需求34
            act_open = menu.addAction("打开主题文件夹")
            chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
            if chosen == act_refresh:
                self._refresh_dir()
            elif chosen == act_open:
                self._reveal(self.storage.theme_dir(value))

    def _refresh_dir(self):
        """需求34：重新读取 picture 目录下的目录与文件并刷新界面。"""
        cur = self.selected_path
        self.refresh_all()
        # 刷新后若原选中图片仍在，恢复其选中与预览
        if cur and os.path.exists(cur) and cur in self.thumb_cards:
            self.select_shot(cur)
        self._toast("已刷新目录", 1500)

    def _delete_shot(self, path):
        name = os.path.basename(path)
        if QMessageBox.question(
                self, "删除图片",
                f"确定删除该图片？此操作不可恢复。\n\n{name}",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            os.remove(path)
        except OSError as e:
            QMessageBox.warning(self, "删除失败", str(e))
            return
        if self.selected_path == path:
            self.selected_path = None
            self.preview.clear_image()
            self.pv_name.setText("未选择图片")
            self.pv_meta.setText("")
        self._refresh_tree()
        self._refresh_thumbs()
        self._refresh_status()

    def _reveal(self, folder):
        try:
            os.startfile(folder)
        except OSError as e:
            QMessageBox.warning(self, "打开失败", str(e))

    def select_shot(self, path, preserve_thumb_selection=False):
        self.selected_path = path
        if not preserve_thumb_selection:
            self.selected_thumb_paths = {path}
            self._thumb_anchor = path
        self.preview.set_image(path)
        self.pv_name.setText(os.path.basename(path))
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            self.pv_meta.setText(
                f"抓拍时间：{mtime:%Y-%m-%d %H:%M:%S}　·　主题：{self.current_theme}")
        except OSError:
            self.pv_meta.setText("")
        for p, card in self.thumb_cards.items():
            card.set_selected(p in self.selected_thumb_paths)
        self._scroll_to_card(self.thumb_cards.get(path))

    def _scroll_to_card(self, card):
        """把选中的缩略图滚动到下方容器中居中位置，保持可见。"""
        if not card:
            return
        sb = self.thumb_scroll.horizontalScrollBar()
        vp = self.thumb_scroll.viewport().width()
        target = card.x() - (vp - card.width()) // 2     # 居中
        sb.setValue(max(sb.minimum(), min(sb.maximum(), target)))

    def do_capture(self, source=""):
        """全屏抓拍并保存。source 用于提示来源：语音 / 快捷键 / 空。"""
        # 抓拍前隐藏上一次的成功提示并等屏幕刷新，避免被拍进截图（快速连拍）
        if self.toast.isVisible():
            self.toast.hide()
            QApplication.processEvents()
            time.sleep(0.05)
        try:
            theme_dir = self.storage.ensure_theme(self.current_theme)
            previous = self.storage.list_shots(self.current_theme)
            previous = previous[-1] if previous else None
            path = capture_mod.capture_fullscreen(self.current_theme, theme_dir)
        except Exception as e:
            self._toast(f"抓拍失败：{e}", 3000)
            return
        # 连续抓拍时对比文件内容，完全相同则删除新文件，不产生重复记录。
        if previous and os.path.exists(previous):
            try:
                def _sha256(p):
                    h = hashlib.sha256()
                    with open(p, "rb") as f:
                        for chunk in iter(lambda: f.read(1024 * 1024), b""):
                            h.update(chunk)
                    return h.digest()
                if _sha256(previous) == _sha256(path):
                    removed = False
                    # 先用 Python 删除，失败时用 Qt 的 QFile 兜底（Windows 偶发文件句柄延迟释放）。
                    for _ in range(3):
                        try:
                            if os.path.exists(path):
                                os.unlink(path)
                            if not os.path.exists(path):
                                removed = True
                                break
                        except OSError:
                            QApplication.processEvents()
                            time.sleep(0.08)
                    if not removed:
                        removed = QFile.remove(path)
                    self._refresh_tree()
                    self._refresh_thumbs()
                    self._refresh_status()
                    if removed and not os.path.exists(path):
                        self._toast("本次抓拍与上一张完全相同，重复文件已删除", 2500)
                    else:
                        self._toast("检测到重复抓拍，但文件删除失败，请检查文件权限", 3500)
                    return
            except (OSError, IOError):
                self._toast("检测重复抓拍时读取文件失败，本次文件已保留", 3000)
                return
        self._refresh_tree()
        self._refresh_thumbs()
        self._refresh_status()
        if self.isVisible():
            self.select_shot(path)
        # 需求32：成功提示停留 500ms
        prefix = (source + "抓拍") if source else "抓拍"
        self._toast(f"{prefix}【{os.path.basename(path)}】文件成功", 500)
        logger.log("抓拍", f"[{source or '手动'}] 主题={self.current_theme} 文件={os.path.basename(path)}")

    def do_merge_pdf(self):
        return self._do_merge_pdf_new()

    def _do_merge_pdf_new(self):
        source_dir = os.path.dirname(self.selected_path) if self.selected_path else self.storage.theme_dir(self.current_theme)
        dlg = PdfMergeDialog(source_dir, f"{self.current_theme}.pdf", self)
        if dlg.exec() != QDialog.Accepted:
            return
        shots = dlg.selected_paths()
        out = dlg.output_path()
        try:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            merge_to_pdf(shots, out)
        except Exception as e:
            QMessageBox.warning(self, "合并失败", str(e))
            return
        QMessageBox.information(self, "已生成 PDF", f"已将 {len(shots)} 张图片合并为：\n{out}")
        logger.log("合并PDF", f"来源={os.path.dirname(shots[0])} 共{len(shots)}页 -> {out}")
        return

    def _do_merge_pdf_legacy(self):
        shots = self.storage.list_shots(self.current_theme)
        if not shots:
            QMessageBox.information(self, "提示", "当前主题没有图片可合并")
            return
        out = os.path.join(self.storage.theme_dir(self.current_theme),
                           f"{self.current_theme}.pdf")
        try:
            merge_to_pdf(shots, out)
        except Exception as e:
            QMessageBox.warning(self, "合并失败", str(e))
            return
        QMessageBox.information(
            self, "已生成 PDF", f"已将 {len(shots)} 张图片合并为：\n{out}")
        logger.log("合并PDF", f"主题={self.current_theme} 共{len(shots)}页 -> {os.path.basename(out)}")

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存位置", self.config.save_root())
        if not d:
            return
        self.config.save_dir = d
        self.config.save()
        self.storage.ensure_theme(self.current_theme)
        self.refresh_all()

    def open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec() == QDialog.Accepted and dlg.new_theme:
            self.storage.ensure_theme(dlg.new_theme)
            self.current_theme = dlg.new_theme
            self.refresh_all()
            self.tray.showMessage(
                "已创建主题目录",
                os.path.join(self.config.save_dir, dlg.new_theme) + os.sep,
                self.app_icon, 2500)

    def _toggle_voice(self, on):
        if on:
            self._voice_max_level = 0.0
            self.voice = VoiceController(device=self.config.mic_device)
            self.voice.recognized.connect(self._on_voice_recognized)
            self.voice.partial.connect(self._on_voice_partial)
            self.voice.triggered.connect(lambda: self.do_capture("语音"))
            self.voice.level.connect(self._on_voice_level)
            self.voice.status.connect(self._on_voice_status)
            self.voice.start()
            # 需求25：开启数秒后若一直没声音 → 提示更换麦克风设备
            QTimer.singleShot(5000, self._check_voice_audio)
        else:
            if self.voice:
                self.voice.stop()
                self.voice = None
            self.st_heard.setText("")
            self.st_level.setValue(0)
        self._refresh_status()

    def _on_voice_level(self, v):
        v = max(0.0, min(1.0, v))
        self.st_level.setValue(int(v * 100))
        if v > self._voice_max_level:
            self._voice_max_level = v

    def _check_voice_audio(self):
        # 开启语音后若 5 秒内音量条几乎没动，多半是麦克风设备选错/被静音
        if self.voice and self.btn_voice.isChecked() and self._voice_max_level < 0.02:
            self.st_heard.setText("⚠️ 没听到声音，请到「设置」更换麦克风设备")
            self._toast("⚠️ 没听到麦克风声音：请到「设置 → 麦克风设备」更换设备", 4000)

    def _on_voice_partial(self, text):
        # 需求22：边说边显示，确认拾音正常
        self.st_heard.setText("🎙 聆听：" + text[-24:])

    def _on_voice_recognized(self, text):
        # 仅显示最终文字；关键词触发已在识别线程对"临时结果"即时完成（更快）
        self.st_heard.setText("🎙 识别：" + text[-24:])

    def _on_voice_status(self, msg, ok):
        if not ok:
            self.btn_voice.blockSignals(True)
            self.btn_voice.setChecked(False)
            self.btn_voice.blockSignals(False)
            QMessageBox.warning(self, "语音控制", msg)
        else:
            self.tray.showMessage("语音控制", msg, self.app_icon, 2500)
        self._refresh_status()

    def _toast(self, text, msec=2000):
        self.toast.show_message(text, msec)

    # ---------------- 预览区右键：复制 / 另存为（需求27）----------------
    def _on_preview_menu(self, pos):
        path = self.selected_path
        if not path or not os.path.exists(path):
            return
        menu = QMenu(self)
        act_copy = menu.addAction("复制图片（可粘贴给 AI）")
        act_save = menu.addAction("另存为…")
        act_del = menu.addAction("删除当前图片")
        chosen = menu.exec(self.preview.mapToGlobal(pos))
        if chosen == act_copy:
            pm = QPixmap(path)
            if pm.isNull():
                self._toast("复制失败：图片无法读取", 2500)
                return
            QApplication.clipboard().setPixmap(pm)
            self._toast("✅ 图片已复制到剪贴板，可直接粘贴给 AI", 2500)
        elif chosen == act_save:
            dst, _ = QFileDialog.getSaveFileName(
                self, "另存为", os.path.basename(path),
                "PNG 图片 (*.png);;JPEG 图片 (*.jpg)")
            if not dst:
                return
            try:
                ext = os.path.splitext(dst)[1].lower()
                if ext in (".png", ""):     # 同为 PNG → 直接复制，保持无损
                    if not ext:
                        dst += ".png"
                    shutil.copyfile(path, dst)
                else:                       # 转换为其它格式
                    QPixmap(path).save(dst)
                self._toast(f"✅ 已另存为：{os.path.basename(dst)}", 2500)
            except Exception as e:
                QMessageBox.warning(self, "另存失败", str(e))
        elif chosen == act_del:
            self._delete_paths([path])

    # ---------------- 快捷键抓拍（需求11）----------------
    def _toggle_hotkey(self, on):
        if on:
            self.enter_quick_mode()
            if not self._quick_mode:
                self.btn_hotkey.blockSignals(True)
                self.btn_hotkey.setChecked(False)
                self.btn_hotkey.blockSignals(False)
        else:
            self.exit_quick_mode()

    def enter_quick_mode(self):
        """注册全局空格热键，并把窗口收起到托盘。"""
        if self._quick_mode:
            return
        hwnd = int(self.winId())
        if not self._user32.RegisterHotKey(hwnd, HOTKEY_ID, MOD_NOREPEAT, VK_SPACE):
            QMessageBox.warning(
                self, "快捷键抓拍", "注册全局【空格】热键失败，可能已被其它程序占用。")
            return
        self._quick_mode = True
        self.btn_hotkey.blockSignals(True)
        self.btn_hotkey.setChecked(True)
        self.btn_hotkey.blockSignals(False)
        self.act_exit_quick.setVisible(True)
        self.tray.setToolTip("桌面抓图软件 · 空格快捷抓拍中")
        self.hide()
        self._toast("已进入【空格快捷抓拍】：按空格键抓屏；双击托盘图标还原窗口可退出", 3500)

    def exit_quick_mode(self):
        if not self._quick_mode:
            return
        try:
            self._user32.UnregisterHotKey(int(self.winId()), HOTKEY_ID)
        except Exception:
            pass
        self._quick_mode = False
        self.btn_hotkey.blockSignals(True)
        self.btn_hotkey.setChecked(False)
        self.btn_hotkey.blockSignals(False)
        self.act_exit_quick.setVisible(False)
        self.tray.setToolTip("桌面抓图软件")

    def nativeEvent(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self.do_capture("快捷键")
                return True, 0
        return super().nativeEvent(eventType, message)

    # ---------------- 窗口/托盘行为 ----------------
    def open_fullscreen(self):
        if not self.selected_path or not os.path.exists(self.selected_path):
            return
        # 需求33：带上当前主题的整张图片列表，支持方向键轮询切换
        shots = self.storage.list_shots(self.current_theme)
        if self.selected_path in shots:
            idx = shots.index(self.selected_path)
        else:
            shots, idx = [self.selected_path], 0
        self._viewer = FullscreenViewer(shots, idx, on_change=self.select_shot)
        self._viewer.showFullScreen()

    def showEvent(self, e):
        super().showEvent(e)
        # 首次显示后，把下方缩略图区设为默认高度 320（需求20）
        if not self._sized_once:
            self._sized_once = True
            def _init_sizes():
                self.vsplitter.setSizes([max(100, self.vsplitter.height() - 320), 320])
                self._apply_thumb_height()
            QTimer.singleShot(0, _init_sizes)

    def changeEvent(self, e):
        # 最小化时收进托盘（需求 3：最小化到任务栏/通知区域）
        if e.type() == e.Type.WindowStateChange and self.isMinimized():
            e.ignore()
            self.hide()
            self.tray.showMessage(
                "已最小化到托盘", "双击托盘图标可恢复窗口", self.app_icon, 1500)
            return
        super().changeEvent(e)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self._restore_window()

    def _restore_window(self):
        self.exit_quick_mode()       # 还原窗口即退出空格快捷抓拍模式
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit(self):
        self.exit_quick_mode()
        if self.voice:
            self.voice.stop()
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, e):
        self._quit()
        e.accept()
