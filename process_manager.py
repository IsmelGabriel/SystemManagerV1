from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QMenu, QAction
from PyQt5.QtCore import QTimer, Qt
import psutil
import ctypes
from ctypes import wintypes
import win32process, win32gui
import os
import subprocess

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
        self.tree.setHeaderLabels(["Nombre", "PID", "CPU %", "RAM %"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)

        # Categorías
        self.apps_item = QTreeWidgetItem(self.tree, ["Aplicaciones"])
        self.bg_item = QTreeWidgetItem(self.tree, ["Procesos en segundo plano"])

        layout.addWidget(self.tree)
        self.setLayout(layout)

        # Diccionario PID -> QTreeWidgetItem
        self.proc_map = {}

        # Inicializar medición de CPU
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.update_processes()

        # Timer cada 1.5 seg
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_processes)
        self.timer.start(1500)

    def update_processes(self):
        current_pids = set()
        foreground_pid = get_foreground_pid()

        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                estado = classify_process(proc, foreground_pid)
                if estado == "Servicio":
                    continue

                pid = proc.info['pid']
                name = proc.info['name']
                exe = proc.info['exe'] or ""
                cpu_percent = proc.cpu_percent(interval=0.0)
                ram_percent = proc.memory_percent()
                current_pids.add(pid)

                if pid in self.proc_map:
                    item = self.proc_map[pid]
                    item.setText(2, f"{cpu_percent:.1f}%")
                    item.setText(3, f"{ram_percent:.1f}%")
                else:
                    item = QTreeWidgetItem([
                        name,
                        str(pid),
                        f"{cpu_percent:.1f}%",
                        f"{ram_percent:.1f}%"
                    ])
                    item.setData(0, Qt.ItemDataRole.UserRole, {
                        "pid": pid,
                        "exe": exe
                    })

                    if estado == "Aplicación":
                        self.apps_item.addChild(item)
                    else:
                        self.bg_item.addChild(item)

                    self.proc_map[pid] = item

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Limpiar procesos cerrados
        for pid in list(self.proc_map.keys()):
            if pid not in current_pids:
                item = self.proc_map.pop(pid)
                parent = item.parent()
                if parent:
                    parent.removeChild(item)

        self.tree.expandAll()

    def open_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item or not item.parent():  # ignorar categorías
            return

        data = item.data(0, 0x0100)
        if not data:
            return

        menu = QMenu(self)

        # Finalizar tarea
        kill_action = QAction("Finalizar tarea", self)
        kill_action.triggered.connect(lambda: self.terminate_process(data["pid"]))
        menu.addAction(kill_action)

        # Propiedades
        if data["exe"] and os.path.exists(data["exe"]):
            prop_action = QAction("Propiedades", self)
            prop_action.triggered.connect(lambda: self.show_properties(data["exe"]))
            menu.addAction(prop_action)

        viewport = self.tree.viewport()
        if viewport is not None:
            menu.exec_(viewport.mapToGlobal(pos))

    def terminate_process(self, pid):
        try:
            p = psutil.Process(pid)
            p.terminate()
        except Exception as e:
            print(f"[ERROR] terminate_process: {e}")

    def show_properties(self, exe_path):
        try:
            subprocess.run(
                ["rundll32.exe", "shell32.dll,ShellExec_RunDLL", exe_path],
                shell=True
            )
        except Exception as e:
            print(f"[ERROR] show_properties: {e}")
