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

        # Diccionario para mapear PID -> (QTreeWidgetItem, botón)
        self.proc_map = {}

        # Inicializar medición de CPU (evita todo 0%)
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.update_processes()

        # Timer para actualizar cada 2 segundos
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_processes)
        self.timer.start(1500)

    def update_processes(self):
        current_pids = set()
        foreground_pid = get_foreground_pid()

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                estado = classify_process(proc, foreground_pid)
                if estado == "Servicio":
                    continue

                pid = proc.info['pid']
                name = proc.info['name']
                cpu_percent = proc.cpu_percent(interval=0.0)
                ram_percent = proc.memory_percent()
                current_pids.add(pid)

                # Si ya existe, actualizar valores
                if pid in self.proc_map:
                    item, _ = self.proc_map[pid]
                    item.setText(2, f"{cpu_percent:.1f}%")
                    item.setText(3, f"{ram_percent:.1f}%")
                else:
                    # Crear nuevo nodo
                    item = QTreeWidgetItem([
                        name,
                        str(pid),
                        f"{cpu_percent:.1f}%",
                        f"{ram_percent:.1f}%"
                    ])
                    btn = QPushButton("Terminar")
                    btn.clicked.connect(lambda _, p=proc: p.terminate())
                    self.tree.setItemWidget(item, 4, btn)

                    if estado == "Aplicación":
                        self.apps_item.addChild(item)
                    else:
                        self.bg_item.addChild(item)

                    self.proc_map[pid] = (item, btn)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Eliminar procesos que ya no existen
        for pid in list(self.proc_map.keys()):
            if pid not in current_pids:
                item, _ = self.proc_map.pop(pid)
                parent = item.parent()
                if parent:
                    parent.removeChild(item)

        self.tree.expandAll()
