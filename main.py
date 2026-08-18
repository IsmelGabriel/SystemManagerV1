"""
SystemManagerV1

Autor: Ismel Gabriel
Versión: 1.0
Descripción: Script principal que inicializa la aplicación y
verifica los privilegios de administrador.
"""

import sys
import ctypes
from PyQt5.QtWidgets import QApplication, QMessageBox
from monitor_manager import MonitorWindow
from monitor_ui import FloatingMonitor


def run_as_admin():
    """Reinicia el script actual con privilegios de administrador."""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
        except Exception as e:
            message = f"No se pudo obtener privilegios de administrador: {e}"
            QMessageBox.critical(None, "Error", message)
        sys.exit()


if __name__ == "__main__":
    run_as_admin()
    app = QApplication(sys.argv)

    window = MonitorWindow()
    window.show()

    monitor = FloatingMonitor()
    monitor.show()

    sys.exit(app.exec_())
