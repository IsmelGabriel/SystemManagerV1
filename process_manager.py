"""
SystemManagerV1

Autor: Ismel Gabriel
Versión: 1.0
Descripción: Pestaña para la gestión y terminación de procesos en ejecución.
"""

import os
import ctypes
from ctypes import wintypes
import subprocess
import psutil
import win32process
import win32gui
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QAction,
    QMessageBox,
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

user32 = ctypes.windll.user32


def get_foreground_pid():
    """Obtiene el PID del proceso que tiene la ventana en primer plano."""
    hwnd = user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def has_visible_window(pid):
    """Determina si un proceso tiene una ventana visible."""

    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
            if win_pid == pid:
                windows.append(hwnd)
        return True

    windows = []
    win32gui.EnumWindows(callback, windows)
    return len(windows) > 0


def classify_process(proc):
    """Clasifica un proceso como 'Aplicación', 'Segundo plano' o 'Servicio'."""
    try:
        if proc.username() in [
            "NT AUTHORITY\\SYSTEM",
            "NT AUTHORITY\\LOCAL SERVICE",
            "NT AUTHORITY\\NETWORK SERVICE",
        ]:
            return "Servicio"
        if has_visible_window(proc.pid):
            return "Aplicación"
        return "Segundo plano"
    except Exception:
        return "Desconocido"


class ProcessWorker(QThread):
    """Hilo secundario para escanear procesos sin bloquear la UI."""

    updated_data = pyqtSignal(list, set)

    def run(self):
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        while True:
            process_data = []
            current_pids = set()

            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    estado = classify_process(proc)
                    if estado == "Servicio":
                        continue

                    pid = proc.info["pid"]
                    name = proc.info["name"]
                    exe = proc.info["exe"] or ""
                    cpu_percent = proc.cpu_percent(interval=0.0)
                    ram_percent = proc.memory_percent()

                    current_pids.add(pid)
                    process_data.append(
                        {
                            "pid": pid,
                            "name": name,
                            "exe": exe,
                            "cpu": cpu_percent,
                            "ram": ram_percent,
                            "estado": estado,
                        }
                    )

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            self.updated_data.emit(process_data, current_pids)
            self.msleep(1500)


class ProcessTab(QWidget):
    """Pestaña de gestión de procesos."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nombre", "PID", "CPU %", "RAM %"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)

        self.apps_item = QTreeWidgetItem(self.tree, ["Aplicaciones"])
        self.bg_item = QTreeWidgetItem(self.tree, ["Procesos en segundo plano"])

        layout.addWidget(self.tree)
        self.setLayout(layout)

        self.proc_map = {}

        self.worker = ProcessWorker()
        self.worker.updated_data.connect(self.update_ui)
        self.worker.start()

    def update_ui(self, process_data, current_pids):
        """Actualiza la lista de procesos visualmente usando los datos del hilo."""
        for data in process_data:
            pid = data["pid"]

            if pid in self.proc_map:
                item = self.proc_map[pid]
                item.setText(2, f"{data['cpu']:.1f}%")
                item.setText(3, f"{data['ram']:.1f}%")
            else:
                item = QTreeWidgetItem(
                    [
                        data["name"],
                        str(pid),
                        f"{data['cpu']:.1f}%",
                        f"{data['ram']:.1f}%",
                    ]
                )
                item.setData(
                    0, Qt.ItemDataRole.UserRole, {"pid": pid, "exe": data["exe"]}
                )

                if data["estado"] == "Aplicación":
                    self.apps_item.addChild(item)
                else:
                    self.bg_item.addChild(item)

                self.proc_map[pid] = item

        for pid in list(self.proc_map.keys()):
            if pid not in current_pids:
                item = self.proc_map.pop(pid)
                parent = item.parent()
                if parent:
                    parent.removeChild(item)

        self.tree.expandAll()

    def open_context_menu(self, pos):
        """Abre el menú contextual para un proceso."""
        item = self.tree.itemAt(pos)
        if not item or not item.parent():
            return

        data = item.data(0, 0x0100)
        if not data:
            return

        menu = QMenu(self)

        kill_action = QAction("Finalizar tarea", self)
        kill_action.triggered.connect(lambda: self.terminate_process(data["pid"]))
        menu.addAction(kill_action)

        if data["exe"] and os.path.exists(data["exe"]):
            prop_action = QAction("Propiedades", self)
            prop_action.triggered.connect(lambda: self.show_properties(data["exe"]))
            menu.addAction(prop_action)

        viewport = self.tree.viewport()
        if viewport is not None:
            menu.exec_(viewport.mapToGlobal(pos))

    def terminate_process(self, pid):
        """Finaliza un proceso dado su PID."""
        try:
            p = psutil.Process(pid)
            p.terminate()
        except Exception:
            QMessageBox.critical(self, "Error", "No se pudo finalizar el proceso")

    def show_properties(self, exe_path):
        """Muestra las propiedades del ejecutable dado su ruta."""
        try:
            subprocess.run(
                ["rundll32.exe", "shell32.dll,ShellExec_RunDLL", exe_path], shell=True
            )
        except Exception:
            QMessageBox.critical(
                self, "Error", "No se pudieron mostrar las propiedades"
            )
