import sys
from PySide6.QtWidgets import QApplication
from gitpilot.ui.main_window import MainWindow, DARK_STYLE

def run():
    app = QApplication(sys.argv)
    app.setApplicationName("GitPilot")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
