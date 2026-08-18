"""
SystemManagerV1

Autor: Ismel Gabriel
Versión: 1.0
Descripción: Pestaña para la optimización del sistema,
limpieza de temporales y gestión de memoria virtual.
"""

import os
import json
import tempfile
import subprocess
import shutil
import psutil

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QInputDialog,
    QDialog,
    QFormLayout,
    QSpinBox,
    QLabel,
    QDialogButtonBox,
)
from PyQt5.QtCore import QThread, pyqtSignal

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "virtual_memory_config.json")


class TempCleanerWorker(QThread):
    """Hilo para limpiar archivos temporales en segundo plano."""

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def run(self):
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        temp_dirs = [
            tempfile.gettempdir(),
            os.path.join(system_root, "Temp"),
            os.path.expandvars(r"%LocalAppData%\Temp"),
            os.path.expandvars(r"%AppData%\Temp"),
        ]
        total_deleted = 0
        total_failed = 0

        for folder in temp_dirs:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder, topdown=False):
                    for f in files:
                        try:
                            os.remove(os.path.join(root, f))
                            total_deleted += 1
                        except Exception:
                            total_failed += 1
                    for d in dirs:
                        path = os.path.join(root, d)
                        try:
                            shutil.rmtree(path, ignore_errors=True)
                        except Exception:
                            total_failed += 1

        self.log_signal.emit(f"Archivos temporales eliminados: {total_deleted}")
        if total_failed > 0:
            self.log_signal.emit(
                f"No se pudieron eliminar {total_failed} archivos o carpetas (en uso)."
            )
        self.finished_signal.emit()


class RecycleBinCleanerWorker(QThread):
    """Hilo para vaciar la papelera de reciclaje usando la API nativa."""

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def run(self):
        import ctypes
        try:
            # Flags: 1 (Sin confirmación), 2 (Sin progreso), 4 (Sin sonido)
            flags = 1 | 2 | 4
            result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)

            if result == 0:
                self.log_signal.emit("Papelera de reciclaje vaciada correctamente.")
            else:
                self.log_signal.emit("La papelera ya estaba vacía.")
        except Exception as e:
            self.log_signal.emit(f"Error vaciando papelera: {e}")

        self.finished_signal.emit()


class VirtualMemoryInfoWorker(QThread):
    """Hilo para obtener la información de la memoria virtual."""

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def run(self):
        try:
            result = subprocess.run(
                ["wmic", "pagefileset", "list", "/format:list"],
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            output = result.stdout.strip()
            if output:
                self.log_signal.emit("Configuración actual de memoria virtual:")
                for line in output.splitlines():
                    if line.strip():
                        self.log_signal.emit(f"    {line.strip()}")
            else:
                self.log_signal.emit(
                    "No se pudo obtener información de memoria virtual."
                )
        except Exception as e:
            self.log_signal.emit(f"Error mostrando memoria virtual actual: {e}")
        self.finished_signal.emit()


class OptimizerTab(QWidget):
    """Pestaña de optimización del sistema."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Registros de optimización...")

        self.btn_temp = QPushButton("Limpiar archivos temporales")
        self.btn_mem = QPushButton("Ajustar memoria virtual")
        self.btn_recycle = QPushButton("Vaciar papelera")

        self.btn_temp.clicked.connect(self.clean_temp_files)
        self.btn_mem.clicked.connect(self.adjust_virtual_memory)
        self.btn_recycle.clicked.connect(self.clean_recycle_bin)

        layout.addWidget(self.btn_temp)
        layout.addWidget(self.btn_mem)
        layout.addWidget(self.btn_recycle)
        layout.addWidget(self.log)

        self.last_config = self.load_config()

        self.temp_worker = None
        self.recycle_worker = None
        self.vm_info_worker = None

    def log_message(self, message):
        """Agrega un mensaje al log."""
        self.log.append(f"[+] {message}")

    def clean_temp_files(self):
        """Inicia el worker de limpieza de temporales"""
        self.btn_temp.setEnabled(False)
        self.log_message("Iniciando limpieza de temporales...")

        self.temp_worker = TempCleanerWorker()
        self.temp_worker.log_signal.connect(self.log_message)
        self.temp_worker.finished_signal.connect(lambda: self.btn_temp.setEnabled(True))
        self.temp_worker.start()

    def clean_recycle_bin(self):
        """Inicia el worker de limpieza de la papelera"""
        self.btn_recycle.setEnabled(False)
        self.log_message("Analizando papelera de reciclaje...")

        self.recycle_worker = RecycleBinCleanerWorker()
        self.recycle_worker.log_signal.connect(self.log_message)
        self.recycle_worker.finished_signal.connect(
            lambda: self.btn_recycle.setEnabled(True)
        )
        self.recycle_worker.start()

    def show_current_virtual_memory(self):
        """Inicia el worker de información de memoria virtual"""
        self.log_message("Obteniendo información de memoria virtual...")
        self.vm_info_worker = VirtualMemoryInfoWorker()
        self.vm_info_worker.log_signal.connect(self.log_message)
        self.vm_info_worker.start()

    def adjust_virtual_memory(self):
        """Ajuste de memoria virtual del sistema."""
        self.show_current_virtual_memory()

        modo, ok = QInputDialog.getItem(
            self,
            "Ajuste de Memoria Virtual",
            "Selecciona el modo:",
            ["Automático (recomendado)", "Manual (personalizado)"],
            0,
            False,
        )

        if not ok:
            return

        if "Automático" in modo:
            subprocess.run(
                [
                    "wmic",
                    "computersystem",
                    "where",
                    "name='%computername%'",
                    "set",
                    "AutomaticManagedPagefile=True",
                ],
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self.log_message("Memoria virtual configurada en modo automático.")
            return

        drives = [
            d.device for d in psutil.disk_partitions() if "fixed" in d.opts.lower()
        ]
        if not drives:
            QMessageBox.warning(self, "Error", "No se detectaron discos fijos.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Configuración manual de memoria virtual")
        form = QFormLayout(dialog)

        spinboxes = {}
        for drive in drives:
            drive_letter = drive[0].upper()
            try:
                free_mb = psutil.disk_usage(drive_letter + ":\\").free // (1024 * 1024)
            except Exception:
                continue

            last_values = self.last_config.get(drive_letter, {"min": 1024, "max": 2048})

            form.addRow(
                QLabel(f"💽 Disco {drive_letter}: (Espacio libre: {free_mb} MB)")
            )

            spin_min = QSpinBox()
            spin_min.setRange(256, max(512, free_mb // 2))
            spin_min.setValue(last_values["min"])

            spin_max = QSpinBox()
            spin_max.setRange(512, max(1024, free_mb - 500))
            spin_max.setValue(last_values["max"])

            form.addRow("Inicial (MB):", spin_min)
            form.addRow("Máximo (MB):", spin_max)
            form.addRow(QLabel(" "))

            spinboxes[drive_letter] = (spin_min, spin_max)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addWidget(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return

        subprocess.run(
            [
                "wmic",
                "computersystem",
                "where",
                "name='%computername%'",
                "set",
                "AutomaticManagedPagefile=False",
            ],
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        new_config = {}

        for drive_letter, (spin_min, spin_max) in spinboxes.items():
            inicial = spin_min.value()
            maximo = spin_max.value()
            try:
                free_space_mb = psutil.disk_usage(drive_letter + ":\\").free // (
                    1024 * 1024
                )
            except Exception:
                free_space_mb = 0

            if free_space_mb < maximo + 500:
                self.log_message(
                    f"[AVISO] Espacio insuficiente en {drive_letter}: ajuste no aplicado."
                )
                continue

            subprocess.run(
                [
                    "wmic",
                    "pagefileset",
                    "where",
                    f"name='{drive_letter}\\\\pagefile.sys'",
                    "set",
                    f"InitialSize={inicial},MaximumSize={maximo}",
                ],
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            new_config[drive_letter] = {"min": inicial, "max": maximo}
            self.log_message(
                f"Memoria virtual ajustada en {drive_letter}: {inicial}MB → {maximo}MB"
            )

        self.save_config(new_config)

    def load_config(self):
        """Carga configuración previa de virtual_memory_config.json"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self, data):
        """Guarda nueva configuración de memoria virtual"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.log_message("Configuración guardada correctamente.")
        except Exception as e:
            self.log_message(f"Error guardando configuración: {e}")
