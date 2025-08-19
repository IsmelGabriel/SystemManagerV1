import sys
import ctypes
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox
from monitor_manager import MonitorWindow

def run_as_admin():
    """Reinicia el script actual con privilegios de administrador."""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
        except Exception as e:
            print(f"No se pudo solicitar permisos de administrador: {e}")
        sys.exit()

def open_monitor_ui():
    """Abre la interfaz flotante de monitor."""
    try: 
        subprocess.Popen(["python", "monitor_ui.py"])
    except Exception as e:
        print(f"Error al abrir monitor_ui.py: {e}")
        QMessageBox.critical(None, "Error", f"No se pudo abrir la interfaz: {e}")   

if __name__ == "__main__":
    run_as_admin()
    open_monitor_ui()
    app = QApplication(sys.argv)
    window = MonitorWindow()
    window.show()
    sys.exit(app.exec_())
