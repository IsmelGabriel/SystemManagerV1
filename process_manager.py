"""
SystemManagerV1

Autor: Ismel Gabriel
Versión: 1.0
Descripción: Pestaña para la gestión, monitorización y terminación de procesos en ejecución.
"""

import os
import ctypes
from ctypes import wintypes
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
    QLineEdit,
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

# Constantes para diálogo de propiedades
SEE_MASK_INVOKEIDLIST = 0x0000000C
SW_SHOWNORMAL = 1


class SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", wintypes.LPVOID),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIcon", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


class CategoryItem(QTreeWidgetItem):
    """Categoría que siempre mantiene 'Aplicaciones' en la parte superior sin importar el ordenamiento."""

    def __lt__(self, other):
        sort_order = self.treeWidget().header().sortIndicatorOrder()
        is_apps_self = "Aplicaciones" in self.text(0)
        is_apps_other = "Aplicaciones" in other.text(0)

        if is_apps_self == is_apps_other:
            return False

        if sort_order == Qt.AscendingOrder:
            return is_apps_self
        else:
            return not is_apps_self


class NumericSortItem(QTreeWidgetItem):
    """Custom QTreeWidgetItem para ordenar números correctamente en lugar de alfabéticamente."""

    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        # Columna 2 = CPU, Columna 3 = RAM
        if column in [2, 3]:
            try:
                # Extraemos el número del texto "15.2%" o "15.2 MB" -> 15.2
                val1 = float(
                    self.text(column).replace("%", "").replace("MB", "").strip()
                )
            except ValueError:
                val1 = 0.0
            try:
                val2 = float(
                    other.text(column).replace("%", "").replace("MB", "").strip()
                )
            except ValueError:
                val2 = 0.0
            return val1 < val2

        # Para texto normal (Nombre, PID)
        return super().__lt__(other)


class ProcessWorker(QThread):
    """Hilo secundario para escanear procesos sin bloquear la UI."""

    updated_data = pyqtSignal(list, set, float, float)

    def __init__(self):
        super().__init__()
        self.cpu_count = psutil.cpu_count() or 1

    def get_visible_windows(self):
        """Mapea de forma eficiente todos los PIDs que tienen ventana visible (1 sola vez por ciclo)."""
        visible_pids = set()

        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                visible_pids.add(pid)
            return True

        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        return visible_pids

    def run(self):
        tracked_procs = {}
        psutil.cpu_percent(interval=None)  # Calibrar sistema general

        while True:
            process_data = []
            current_pids = set()
            visible_pids = self.get_visible_windows()

            # Recopilar todos primero para saber qué nombres son de "Aplicación"
            raw_processes = []
            apps_names = set()

            for p_info in psutil.process_iter(["pid", "name", "exe", "username"]):
                try:
                    pid = p_info.info.get("pid")
                    name = p_info.info.get("name")
                    if pid is None or name is None:
                        continue
                    exe = p_info.info.get("exe") or ""
                    username = p_info.info.get("username") or ""

                    if pid in visible_pids:
                        apps_names.add(name)

                    raw_processes.append(
                        {"pid": pid, "name": name, "exe": exe, "username": username}
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            for proc_dict in raw_processes:
                pid = proc_dict["pid"]
                name = proc_dict["name"]
                exe = proc_dict["exe"]
                username = proc_dict["username"]

                # Clasificación optimizada y segura
                if username in [
                    "NT AUTHORITY\\SYSTEM",
                    "NT AUTHORITY\\LOCAL SERVICE",
                    "NT AUTHORITY\\NETWORK SERVICE",
                ]:
                    estado = "Servicio"
                # Si cualquier proceso con este nombre tiene ventana, todos son "Aplicación"
                elif name in apps_names:
                    estado = "Aplicación"
                else:
                    estado = "Segundo plano"

                if estado == "Servicio":
                    continue

                # Obtener/Cachear instancia de Process para CPU exacto
                if pid not in tracked_procs:
                    try:
                        p = psutil.Process(pid)
                        p.cpu_percent(interval=None)  # Calibración
                        tracked_procs[pid] = p
                    except Exception:
                        continue

                p = tracked_procs[pid]
                try:
                    cpu_percent = p.cpu_percent(interval=None) / self.cpu_count
                    mem_info = p.memory_info()
                    # Task Manager usa 'private' (Private Working Set) en lugar de 'rss'
                    ram_mb = getattr(mem_info, "private", mem_info.rss) / (1024 * 1024)
                except Exception:
                    continue

                current_pids.add(pid)
                process_data.append(
                    {
                        "pid": pid,
                        "name": name,
                        "exe": exe,
                        "cpu": cpu_percent,
                        "ram": ram_mb,
                        "estado": estado,
                    }
                )

            # Limpiar procesos muertos
            dead_pids = list(set(tracked_procs.keys()) - current_pids)
            for d_pid in dead_pids:
                tracked_procs.pop(d_pid, None)

            try:
                sys_cpu = psutil.cpu_percent(interval=None)
                sys_ram = psutil.virtual_memory().used / (1024**3)  # En GB
            except Exception:
                sys_cpu = 0.0
                sys_ram = 0.0

            self.updated_data.emit(process_data, current_pids, sys_cpu, sys_ram)
            self.msleep(1000)


class ProcessTab(QWidget):
    """Pestaña de gestión de procesos."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # Barra de Búsqueda
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Buscar proceso por nombre...")
        self.search_bar.textChanged.connect(self.filter_processes)
        layout.addWidget(self.search_bar)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nombre", "PID", "CPU", "RAM"])
        self.tree.setSortingEnabled(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)

        self.apps_item = CategoryItem(self.tree, ["Aplicaciones"])
        self.apps_item.setFlags(Qt.ItemFlag.ItemIsEnabled)

        self.bg_item = CategoryItem(self.tree, ["Procesos en segundo plano"])
        self.bg_item.setFlags(Qt.ItemFlag.ItemIsEnabled)

        layout.addWidget(self.tree)
        self.setLayout(layout)

        self.proc_map = {}
        self.group_map = {}

        self.worker = ProcessWorker()
        self.worker.updated_data.connect(self.update_ui)
        self.worker.start()

    def filter_processes(self, text):
        """Oculta o muestra procesos según la búsqueda."""
        search_text = text.lower()
        for pid, item in self.proc_map.items():
            name = item.text(0).lower()
            item.setHidden(bool(search_text and search_text not in name))

        for key, g_item in self.group_map.items():
            name = key[1].lower()
            g_item.setHidden(bool(search_text and search_text not in name))

    def update_ui(self, process_data, current_pids, sys_cpu, sys_ram):
        """Actualiza la lista de procesos visualmente agrupando subprocesos."""
        self.tree.setSortingEnabled(False)

        # 1. Agrupar datos
        groups = {}
        for data in process_data:
            key = (data["estado"], data["name"])
            if key not in groups:
                groups[key] = {"cpu": 0.0, "ram": 0.0, "pids": []}
            groups[key]["cpu"] += data["cpu"]
            groups[key]["ram"] += data["ram"]
            groups[key]["pids"].append(data)

        # Limpiar uso de CPU/RAM de los layouts principales
        self.apps_item.setText(2, "")
        self.apps_item.setText(3, "")
        self.bg_item.setText(2, "")
        self.bg_item.setText(3, "")

        # Actualizar las cabeceras principales con el uso real del sistema
        self.tree.headerItem().setText(2, f"CPU ({sys_cpu:.1f}%)")
        self.tree.headerItem().setText(3, f"RAM ({sys_ram:.1f} GB)")

        search_text = self.search_bar.text().lower()

        # 2. Procesar cada proceso y decidir su padre (Grupo o Categoría principal)
        for data in process_data:
            pid = data["pid"]
            key = (data["estado"], data["name"])
            gdata = groups[key]

            # Decidir el padre real de este proceso
            if len(gdata["pids"]) > 1:
                # Necesita un grupo
                group_pids = [p["pid"] for p in gdata["pids"]]

                if key not in self.group_map:
                    g_item = NumericSortItem(
                        [
                            f"{data['name']} ({len(gdata['pids'])})",
                            "",
                            f"{gdata['cpu']:.1f}%",
                            f"{gdata['ram']:.1f} MB",
                        ]
                    )
                    g_item.setData(0, Qt.UserRole, {"is_group": True, "pids": group_pids, "exe": data["exe"]})
                    parent_cat = (
                        self.apps_item
                        if data["estado"] == "Aplicación"
                        else self.bg_item
                    )
                    parent_cat.addChild(g_item)
                    self.group_map[key] = g_item
                else:
                    g_item = self.group_map[key]
                    g_item.setText(0, f"{data['name']} ({len(gdata['pids'])})")
                    g_item.setText(2, f"{gdata['cpu']:.1f}%")
                    g_item.setText(3, f"{gdata['ram']:.1f} MB")
                    g_item.setData(0, Qt.UserRole, {"is_group": True, "pids": group_pids, "exe": data["exe"]})

                target_parent = self.group_map[key]
            else:
                # No necesita grupo, va directo a la categoría
                target_parent = (
                    self.apps_item if data["estado"] == "Aplicación" else self.bg_item
                )

            # Crear o actualizar el item del proceso
            if pid in self.proc_map:
                item = self.proc_map[pid]
                item.setText(2, f"{data['cpu']:.1f}%")
                item.setText(3, f"{data['ram']:.1f} MB")

                if item.parent() != target_parent:
                    if item.parent():
                        item.parent().removeChild(item)
                    target_parent.addChild(item)
            else:
                item = NumericSortItem(
                    [
                        data["name"],
                        str(pid),
                        f"{data['cpu']:.1f}%",
                        f"{data['ram']:.1f} MB",
                    ]
                )
                item.setData(
                    0,
                    Qt.UserRole,
                    {"pid": pid, "exe": data["exe"], "is_group": False},
                )
                target_parent.addChild(item)
                self.proc_map[pid] = item

            # Ocultar si hay busqueda
            hidden = bool(search_text and search_text not in data["name"].lower())
            item.setHidden(hidden)
            if target_parent in self.group_map.values():
                target_parent.setHidden(hidden)

        # 3. Limpieza de grupos vacíos o que ya no justifican grupo
        for key in list(self.group_map.keys()):
            if key not in groups or len(groups[key]["pids"]) <= 1:
                g_item = self.group_map.pop(key)
                if g_item.parent():
                    g_item.parent().removeChild(g_item)

        # 4. Limpieza de procesos muertos
        for pid in list(self.proc_map.keys()):
            if pid not in current_pids:
                item = self.proc_map.pop(pid)
                if item.parent():
                    item.parent().removeChild(item)

        self.tree.setSortingEnabled(True)

        # Mantenemos las categorias expandidas
        if not self.apps_item.isExpanded():
            self.apps_item.setExpanded(True)
        if not self.bg_item.isExpanded():
            self.bg_item.setExpanded(True)

    def open_context_menu(self, pos):
        """Abre el menu contextual para un proceso."""
        item = self.tree.itemAt(pos)
        if not item or item in (self.apps_item, self.bg_item):
            return

        data = item.data(0, Qt.UserRole)
        if not data:
            return

        is_group = data.get("is_group", False)
        menu = QMenu(self)

        # Finalizar Tarea
        kill_action = QAction("Finalizar tarea", self)
        if is_group:
            pids = data.get("pids", [])
            kill_action.triggered.connect(
                lambda _, group_pids=pids: self.terminate_group(group_pids)
            )
        else:
            kill_action.triggered.connect(
                lambda _, p=data["pid"]: self.terminate_process(p)
            )
        menu.addAction(kill_action)

        menu.addSeparator()

        if is_group:
            # Propiedades Reales para el grupo
            exe_path = data.get("exe")
            if exe_path and os.path.exists(exe_path):
                prop_action = QAction("Propiedades", self)
                prop_action.triggered.connect(
                    lambda _, e=exe_path: self.show_properties(e)
                )
                menu.addAction(prop_action)
            viewport = self.tree.viewport()
            if viewport is not None:
                menu.exec_(viewport.mapToGlobal(pos))
            return

        # Suspender y Prioridades
        try:
            proc = psutil.Process(data["pid"])
            is_suspended = proc.status() == psutil.STATUS_STOPPED
            suspend_action = QAction(
                "Reanudar proceso" if is_suspended else "Suspender proceso", self
            )
            suspend_action.triggered.connect(
                lambda _, p=data["pid"], s=is_suspended: self.toggle_suspend(p, s)
            )
            menu.addAction(suspend_action)

            priority_menu = menu.addMenu("Establecer prioridad")

            prio_high = QAction("Alta", self)
            prio_high.triggered.connect(
                lambda _, p=data["pid"]: self.set_priority(
                    p, psutil.HIGH_PRIORITY_CLASS
                )
            )

            prio_normal = QAction("Normal", self)
            prio_normal.triggered.connect(
                lambda _, p=data["pid"]: self.set_priority(
                    p, psutil.NORMAL_PRIORITY_CLASS
                )
            )

            prio_low = QAction("Baja", self)
            prio_low.triggered.connect(
                lambda _, p=data["pid"]: self.set_priority(
                    p, psutil.IDLE_PRIORITY_CLASS
                )
            )

            priority_menu.addAction(prio_high)
            priority_menu.addAction(prio_normal)
            priority_menu.addAction(prio_low)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        menu.addSeparator()

        # Propiedades Reales
        if data["exe"] and os.path.exists(data["exe"]):
            prop_action = QAction("Propiedades", self)
            prop_action.triggered.connect(
                lambda _, e=data["exe"]: self.show_properties(e)
            )
            menu.addAction(prop_action)

        viewport = self.tree.viewport()
        if viewport is not None:
            menu.exec_(viewport.mapToGlobal(pos))

    def terminate_group(self, pids):
        """Finaliza un grupo completo de procesos."""
        failed = False
        for pid in pids:
            try:
                psutil.Process(pid).terminate()
            except Exception:
                failed = True
        if failed:
            QMessageBox.warning(
                self, "Aviso", "Algunos subprocesos del grupo no se pudieron finalizar."
            )

    def terminate_process(self, pid):
        try:
            psutil.Process(pid).terminate()
        except Exception:
            QMessageBox.critical(
                self, "Error", "No se pudo finalizar el proceso. Acceso denegado."
            )

    def toggle_suspend(self, pid, is_suspended):
        try:
            p = psutil.Process(pid)
            if is_suspended:
                p.resume()
            else:
                p.suspend()
        except Exception:
            QMessageBox.critical(
                self,
                "Error",
                "No tienes permisos para suspender/reanudar este proceso.",
            )

    def set_priority(self, pid, priority_class):
        try:
            psutil.Process(pid).nice(priority_class)
        except Exception:
            QMessageBox.critical(
                self, "Error", "No se pudo cambiar la prioridad. Acceso denegado."
            )

    def show_properties(self, exe_path):
        """Abre la ventana real de propiedades nativa de Windows."""
        try:
            sei = SHELLEXECUTEINFO()
            sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
            sei.fMask = SEE_MASK_INVOKEIDLIST
            sei.lpVerb = "properties"
            sei.lpFile = exe_path
            sei.nShow = SW_SHOWNORMAL
            ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudieron abrir las propiedades: {e}"
            )
