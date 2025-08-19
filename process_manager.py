from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton
import psutil
import ctypes
from ctypes import wintypes
import win32process, win32gui
from PyQt5.QtCore import QTimer

user32 = ctypes.windll.user32

def get_foreground_pid():
    hwnd = user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value

def has_visible_window(pid):
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
            if win_pid == pid:
                windows.append(hwnd)
        return True
    windows = []
    win32gui.EnumWindows(callback, windows)
    return len(windows) > 0

def classify_process(proc, foreground_pid):
    try:
        if proc.username() in ["NT AUTHORITY\\SYSTEM", "NT AUTHORITY\\LOCAL SERVICE", "NT AUTHORITY\\NETWORK SERVICE"]:
            return "Servicio"
        if has_visible_window(proc.pid):
            return "Aplicación"
        return "Segundo plano"
    except:
        return "Desconocido"


class ProcessTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nombre", "PID", "CPU %", "RAM %", "Acción"])

        # Categorías
        self.apps_item = QTreeWidgetItem(self.tree, ["Aplicaciones"])
        self.bg_item = QTreeWidgetItem(self.tree, ["Procesos en segundo plano"])

        layout.addWidget(self.tree)
        self.setLayout(layout)

        # Inicializar medición de CPU (evita que todo salga 0%)
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.update_processes()

        # Timer para actualizar cada 2 segundos
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_processes)
        self.timer.start(2000)  # 2000 ms = 2 seg

    def update_processes(self):
        self.apps_item.takeChildren()
        self.bg_item.takeChildren()

        foreground_pid = get_foreground_pid()

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                estado = classify_process(proc, foreground_pid)
                if estado == "Servicio":
                    continue

                cpu_percent = proc.cpu_percent(interval=None)  # ya normalizado
                item = QTreeWidgetItem([
                    proc.info['name'],
                    str(proc.info['pid']),
                    f"{cpu_percent:.1f}%",   # CPU %
                    f"{proc.memory_percent():.1f}%"  # RAM %
                ])

                # Botón terminar
                btn = QPushButton("Terminar")
                btn.clicked.connect(lambda _, p=proc: p.terminate())
                self.tree.setItemWidget(item, 4, btn)

                if estado == "Aplicación":
                    self.apps_item.addChild(item)
                else:
                    self.bg_item.addChild(item)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
