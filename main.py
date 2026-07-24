import sys

from PySide6.QtWidgets import QApplication

from .capture import enable_dpi_awareness
from .main_window import MainWindow, make_app_icon


def main():
    # 必须在创建 QApplication 前设置，确保抓图取到物理像素（需求13）
    enable_dpi_awareness()

    app = QApplication(sys.argv)
    app.setApplicationName("桌面抓图软件")
    # 收进托盘后窗口隐藏，不能因"无窗口"而退出
    app.setQuitOnLastWindowClosed(False)

    icon = make_app_icon()
    app.setWindowIcon(icon)

    window = MainWindow(icon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
