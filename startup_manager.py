import os
import winreg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout
)


class StartupTab(QWidget):
    def __init__(self):
        super().__init__()  # Inicializar QWidget

        self.run_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Usuario actual"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "Todos los usuarios"),
        ]
        self.approved_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
        self.startup_folder = os.path.join(
            os.environ["APPDATA"],
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )

        # Layout principal
        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nombre", "Ruta", "Ubicación", "Estado", "Acciones"])
        layout.addWidget(self.tree)

        self.refresh()

    # ================== Helpers ==================
    def _set_registry_value(self, root, path, name, value, regtype=winreg.REG_BINARY):
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, regtype, value)
                return True
        except Exception as e:
            print(f"[ERROR] set_registry_value: {e}")
            return False

    def _delete_registry_value(self, root, path, name):
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
                return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"[ERROR] delete_registry_value: {e}")
            return False

    def get_startup_state(self, name, root):
        """Revisa en StartupApproved si está habilitado/deshabilitado"""
        try:
            with winreg.OpenKey(root, self.approved_path, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, name)
                return value[0] == 3  # 03 = habilitado, 02 = deshabilitado
        except FileNotFoundError:
            return True
        except Exception:
            return True

    def set_startup_state(self, name, root, enable=True):
        """Actualiza estado en StartupApproved"""
        if enable:
            data = b"\x03\x00\x00\x00\x00\x00\x00\x00"
        else:
            data = b"\x02\x00\x00\x00\x00\x00\x00\x00"
        self._set_registry_value(root, self.approved_path, name, data, winreg.REG_BINARY)

    # ================== Listado ==================
    def list_items(self):
        items = []

        # Registros Run
        for root, path, location in self.run_paths:
            try:
                with winreg.OpenKey(root, path) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            state = self.get_startup_state(name, root)
                            items.append({
                                "name": name,
                                "path": value,
                                "location": location,
                                "enabled": state,
                                "root": root
                            })
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                continue

        # Carpeta Startup
        if os.path.exists(self.startup_folder):
            for f in os.listdir(self.startup_folder):
                full_path = os.path.join(self.startup_folder, f)
                items.append({
                    "name": f,
                    "path": full_path,
                    "location": "Carpeta Startup",
                    "enabled": True,
                    "root": None
                })

        return items

    # ================== Acciones ==================
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

    # ================== GUI ==================
    def refresh(self):
        self.tree.clear()
        for item in self.list_items():
            row = QTreeWidgetItem([
                item["name"],
                item["path"],
                item["location"],
                "Habilitado" if item["enabled"] else "Deshabilitado"
            ])

            # Botones en celda
            btn_layout = QHBoxLayout()
            if item["enabled"]:
                btn = QPushButton("Deshabilitar")
                btn.clicked.connect(lambda _, n=item["name"], l=item["location"], r=item["root"]:
                                    self.disable(n, l, r))
            else:
                btn = QPushButton("Habilitar")
                btn.clicked.connect(lambda _, n=item["name"], p=item["path"], l=item["location"], r=item["root"]:
                                    self.enable(n, p, l, r))

            btn_layout.addWidget(btn)
            self.tree.setItemWidget(row, 4, btn)

            self.tree.addTopLevelItem(row)
