import os
import re
import winreg
import subprocess
import webbrowser
import shlex
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QMenu, QAction
)
from PyQt5.QtCore import Qt


class StartupTab(QWidget):
    def __init__(self):
        super().__init__()

        self.run_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Usuario actual"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "Todos los usuarios"),
        ]
        self.approved_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
        self.startup_folders = [
            os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup"),
            os.path.join(os.environ["ProgramData"], r"Microsoft\Windows\Start Menu\Programs\Startup")
        ]

        # Layout principal
        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nombre", "Ruta", "Ubicación", "Estado", "Impacto"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        layout.addWidget(self.tree)

        self.refresh()

    # -----------------------------
    # Registro
    # -----------------------------
    def _set_registry_value(self, root, path, name, value, regtype=winreg.REG_BINARY):
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, regtype, value)
                return True
        except Exception as e:
            print(f"[ERROR] set_registry_value: {e}")
            return False

    def get_startup_state(self, name, root):
        try:
            with winreg.OpenKey(root, self.approved_path, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, name)
                if value[0] == 2:   # Habilitado
                    return True
                elif value[0] == 3: # Deshabilitado
                    return False
                else:
                    return True
        except FileNotFoundError:
            return True
        except Exception as e:
            print(f"[WARN] get_startup_state({name}): {e}")
            return True


    def set_startup_state(self, name, root, enable=True):
        data = b"\x02\x00\x00\x00\x00\x00\x00\x00" if enable else b"\x03\x00\x00\x00\x00\x00\x00\x00"
        return self._set_registry_value(root, self.approved_path, name, data, winreg.REG_BINARY)

    def estimate_startup_impact(self, path):
        try:
            size_mb = os.path.getsize(path) / (1024*1024)
            if size_mb > 50:
                return "Alto"
            elif size_mb > 10:
                return "Medio"
            else:
                return "Bajo"
        except:
            return "Ninguno"

    # -----------------------------
    # Tareas programadas
    # -----------------------------
    def get_scheduled_tasks(self):
        tasks = []
        try:
            output = subprocess.check_output(
                ["schtasks", "/query", "/fo", "CSV", "/v"],
                shell=True, text=True, encoding="utf-8", errors="ignore"
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
                    tasks.append({
                        "name": row.get("TaskName", ""),
                        "path": row.get("Task To Run", ""),
                        "location": "Tarea Programada",
                        "enabled": row.get("Status", "").lower() == "ready",
                        "impact": self.estimate_startup_impact(row.get("Task To Run", "")),
                        "root": None
                    })
        except Exception as e:
            print(f"[WARN] get_scheduled_tasks: {e}")
        return tasks

    @staticmethod
    def extract_exe_path(command):
        try:
            if not command:
                return ""
            # Quitar comillas
            cmd = command.strip().strip('"')

            # Expandir variables de entorno (%windir%, %appdata%, etc.)
            cmd = os.path.expandvars(cmd)

            # Si tiene parámetros, quedarnos solo con la parte del .exe
            match = re.match(r'^(.*?\.exe)', cmd, re.IGNORECASE)
            if match:
                return match.group(1)
            return cmd
        except Exception:
            return command


    # -----------------------------
    # Listado de ítems
    # -----------------------------
    def list_items(self):
        items = []

        # Registro
        for root, path, location in self.run_paths:
            try:
                with winreg.OpenKey(root, path) as key:
                    i = 0
                    while True:
                        try:
                            # Get registry value first
                            name, value, _ = winreg.EnumValue(key, i)
                            # Then extract path and name
                            exe_path = os.path.expandvars(self.extract_exe_path(value))
                            exe_name = os.path.basename(exe_path) if exe_path else name
                            state = self.get_startup_state(name, root)
                            
                            items.append({
                                "name": exe_name if exe_name else os.path.basename(name),
                                "path": exe_path,
                                "location": location,
                                "enabled": state,
                                "impact": self.estimate_startup_impact(value),
                                "root": root
                            })
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                continue

        # Carpetas Startup
        for folder in self.startup_folders:
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    full_path = os.path.join(folder, f)
                    items.append({
                        "name": f,
                        "path": full_path,
                        "location": "Carpeta Startup",
                        "enabled": True,
                        "impact": self.estimate_startup_impact(full_path),
                        "root": None
                    })

        # Tareas programadas
        items.extend(self.get_scheduled_tasks())
        return items

    # -----------------------------
    # Habilitar / deshabilitar
    # -----------------------------
    def enable(self, name, path, location, root):
        if location == "Usuario actual":
            run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        elif location == "Todos los usuarios":
            run_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        else:
            return
        self._set_registry_value(root, run_path, name, path, winreg.REG_SZ)
        self.set_startup_state(name, root, True)
        self.refresh()

    def disable(self, name, location, root):
        if location in ["Usuario actual", "Todos los usuarios"]:
            self.set_startup_state(name, root, False)
        self.refresh()

    # -----------------------------
    # Refrescar lista
    # -----------------------------
    def refresh(self):
        self.tree.clear()
        for item in self.list_items():
            row = QTreeWidgetItem([
                item["name"],
                item["path"],
                item["location"],
                "Habilitado" if item["enabled"] else "Deshabilitado"
            ])
            row.setData(0, Qt.ItemDataRole.UserRole, item)  # guardar datos completos
            self.tree.addTopLevelItem(row)

    # -----------------------------
    # Menú contextual
    # -----------------------------
    def open_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return

        data = item.data(0, 0x0100)
        menu = QMenu(self)

        # Acción abrir ubicación
        if os.path.exists(data["path"]):
            open_action = QAction("Abrir ubicación", self)
            def open_location():
                subprocess.Popen(['explorer', f'/select,"{data["path"]}"'])
            open_action.triggered.connect(open_location)
            menu.addAction(open_action)

        # Acción habilitar/deshabilitar
        if data["location"] in ["Usuario actual", "Todos los usuarios"]:
            if data["enabled"]:
                toggle_action = QAction("Deshabilitar", self)
                toggle_action.triggered.connect(lambda: self.disable(data["name"], data["location"], data["root"]))
            else:
                toggle_action = QAction("Habilitar", self)
                toggle_action.triggered.connect(lambda: self.enable(data["name"], data["path"], data["location"], data["root"]))
            menu.addAction(toggle_action)

        viewport = self.tree.viewport()
        if viewport is not None:
            menu.exec_(viewport.mapToGlobal(pos))
