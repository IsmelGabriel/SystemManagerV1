"""
SystemManagerV1

Autor: Ismel Gabriel
Versión: 1.0
Descripción: Pestaña para gestionar las aplicaciones
que se inician automáticamente con Windows.
"""

import os
import re
import winreg
import subprocess
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QAction,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class StartupWorker(QThread):
    """Hilo secundario para cargar la lista de inicio sin bloquear la UI."""

    items_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.run_paths = [
            (
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                "Usuario actual",
            ),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                "Todos los usuarios",
            ),
        ]
        self.approved_path = [
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
        ]
        self.startup_folders = [
            os.path.join(
                os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup"
            ),
            os.path.join(
                os.environ["ProgramData"],
                r"Microsoft\Windows\Start Menu\Programs\Startup",
            ),
        ]

    def get_startup_state(self, name, root):
        """Obtiene el estado de inicio (habilitado/deshabilitado)."""
        try:
            with winreg.OpenKey(root, self.approved_path[0], 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, name)
                if value[0] == 2:
                    return True
                elif value[0] == 3:
                    return False
                else:
                    return True
        except FileNotFoundError:
            return True
        except Exception:
            return True

    def estimate_startup_impact(self, path):
        """Estima el impacto en el inicio según el tamaño del ejecutable."""
        try:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > 50:
                return "Alto"
            elif size_mb > 10:
                return "Medio"
            else:
                return "Bajo"
        except Exception:
            return "Ninguno"

    def get_scheduled_tasks(self):
        """Obtiene las tareas programadas que se inician al iniciar sesión."""
        tasks = []
        try:
            output = subprocess.check_output(
                ["schtasks", "/query", "/fo", "CSV", "/v"],
                shell=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            lines = output.splitlines()
            if not lines:
                return tasks

            headers = [h.strip('"') for h in lines[0].split(",")]
            for line in lines[1:]:
                cols = [c.strip('"') for c in line.split(",")]
                if len(cols) != len(headers):
                    continue
                row = dict(zip(headers, cols))

                if "Logon" in row.get("Schedule Type", ""):
                    tasks.append(
                        {
                            "name": row.get("TaskName", ""),
                            "path": row.get("Task To Run", ""),
                            "location": "Tarea Programada",
                            "enabled": row.get("Status", "").lower() == "ready",
                            "impact": self.estimate_startup_impact(
                                row.get("Task To Run", "")
                            ),
                            "root": None,
                        }
                    )
        except Exception as e:
            self.error_occurred.emit(
                f"No se pudieron obtener las tareas programadas: {e}"
            )
        return tasks

    @staticmethod
    def extract_exe_path(command):
        """Extrae la ruta del ejecutable de un comando."""
        try:
            if not command:
                return ""
            cmd = command.strip().strip('"')
            cmd = os.path.expandvars(cmd)
            match = re.match(r"^(.*?\.exe)", cmd, re.IGNORECASE)
            if match:
                return match.group(1)
            return cmd
        except Exception:
            return command

    def run(self):
        """Ejecución del hilo para listar los elementos."""
        items = []

        for root, path, location in self.run_paths:
            try:
                with winreg.OpenKey(root, path) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            exe_path = os.path.expandvars(self.extract_exe_path(value))
                            exe_name = os.path.basename(exe_path) if exe_path else name
                            state = self.get_startup_state(name, root)

                            items.append(
                                {
                                    "name": (
                                        exe_name if exe_name else os.path.basename(name)
                                    ),
                                    "path": exe_path,
                                    "location": location,
                                    "enabled": state,
                                    "impact": self.estimate_startup_impact(exe_path),
                                    "root": root,
                                }
                            )
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                continue

        for folder in self.startup_folders:
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    full_path = os.path.join(folder, f)
                    items.append(
                        {
                            "name": f,
                            "path": full_path,
                            "location": "Carpeta Startup",
                            "enabled": True,
                            "impact": self.estimate_startup_impact(full_path),
                            "root": None,
                        }
                    )

        items.extend(self.get_scheduled_tasks())

        self.items_loaded.emit(items)


class StartupTab(QWidget):
    """Pestaña de gestión de aplicaciones de inicio."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nombre", "Ruta", "Ubicación", "Estado", "Impacto"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        layout.addWidget(self.tree)

        self.worker = None
        self.refresh()

    def _set_registry_value(self, root, path, name, value, regtype=winreg.REG_BINARY):
        """Establece un valor en el registro de Windows."""
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, regtype, value)
                return True
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo modificar el registro: {e}"
            )
            return False

    def set_startup_state(self, name, root, enable=True):
        """Establece el estado de inicio (habilitado/deshabilitado)."""
        approved_path = (
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
        )
        data = (
            b"\x02\x00\x00\x00\x00\x00\x00\x00"
            if enable
            else b"\x03\x00\x00\x00\x00\x00\x00\x00"
        )
        return self._set_registry_value(
            root, approved_path, name, data, winreg.REG_BINARY
        )

    def enable_startup(self, name, path, location, root):
        """Habilita una aplicación de inicio."""
        if location == "Usuario actual":
            run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        elif location == "Todos los usuarios":
            run_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        else:
            return
        self._set_registry_value(root, run_path, name, path, winreg.REG_SZ)
        self.set_startup_state(name, root, True)
        self.refresh()

    def disable_startup(self, name, location, root):
        """Deshabilita una aplicación de inicio."""
        if location in ["Usuario actual", "Todos los usuarios"]:
            self.set_startup_state(name, root, False)
        self.refresh()

    def refresh(self):
        """Inicia el worker para cargar los ítems sin bloquear la UI."""
        self.tree.clear()

        loading_item = QTreeWidgetItem(
            ["Cargando aplicaciones de inicio...", "", "", "", ""]
        )
        self.tree.addTopLevelItem(loading_item)

        self.worker = StartupWorker()
        self.worker.items_loaded.connect(self.populate_tree)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.start()

    def populate_tree(self, items):
        """Rellena el QTreeWidget con los datos obtenidos por el worker."""
        self.tree.clear()
        for item in items:
            row = QTreeWidgetItem(
                [
                    item["name"],
                    item["path"],
                    item["location"],
                    "Habilitado" if item["enabled"] else "Deshabilitado",
                    item["impact"],
                ]
            )
            row.setData(0, Qt.ItemDataRole.UserRole, item)
            self.tree.addTopLevelItem(row)

    def show_error(self, message):
        """Muestra un mensaje de error si el worker falla en algo."""
        QMessageBox.warning(self, "Advertencia", message)

    def open_context_menu(self, pos):
        """Abre el menú contextual para un ítem de inicio."""
        item = self.tree.itemAt(pos)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)

        if os.path.exists(data["path"]):
            open_action = QAction("Abrir ubicación", self)

            def open_location():
                subprocess.Popen(["explorer", f'/select,"{data["path"]}"'])

            open_action.triggered.connect(open_location)
            menu.addAction(open_action)

        if data["location"] in ["Usuario actual", "Todos los usuarios"]:
            if data["enabled"]:
                toggle_action = QAction("Deshabilitar", self)
                toggle_action.triggered.connect(
                    lambda: self.disable_startup(
                        data["name"], data["location"], data["root"]
                    )
                )
            else:
                toggle_action = QAction("Habilitar", self)
                toggle_action.triggered.connect(
                    lambda: self.enable_startup(
                        data["name"], data["path"], data["location"], data["root"]
                    )
                )
            menu.addAction(toggle_action)

        viewport = self.tree.viewport()
        if viewport is not None:
            menu.exec_(viewport.mapToGlobal(pos))
