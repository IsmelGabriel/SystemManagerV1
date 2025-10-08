import os
import json
import psutil
import tempfile
import subprocess
import shutil
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit, QMessageBox,
    QInputDialog, QDialog, QFormLayout, QSpinBox, QLabel, QDialogButtonBox
)
from PyQt5.QtCore import Qt

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "virtual_memory_config.json")

class OptimizerTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Registros de optimización...")

        # Botones principales
        btn_temp = QPushButton("🧹 Limpiar temporales")
        btn_mem = QPushButton("💾 Ajustar memoria virtual")
        btn_recycle = QPushButton("🗑️ Vaciar papelera")

        btn_temp.clicked.connect(self.clean_temp_files)
        btn_mem.clicked.connect(self.adjust_virtual_memory)
        btn_recycle.clicked.connect(self.clean_recycle_bin)

        layout.addWidget(btn_temp)
        layout.addWidget(btn_mem)
        layout.addWidget(btn_recycle)
        layout.addWidget(self.log)

        # Cargar configuración previa si existe
        self.last_config = self.load_config()

    # -------------------------------
    # Utilidad: logs
    # -------------------------------
    def log_message(self, message):
        self.log.append(f"[+] {message}")

    # -------------------------------
    # Limpieza de temporales
    # -------------------------------
    def clean_temp_files(self):
        temp_dirs = [
            tempfile.gettempdir(),
            r"C:\Windows\Temp",
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
                        except:
                            total_failed += 1
                    for d in dirs:
                        path = os.path.join(root, d)
                        try:
                            shutil.rmtree(path, ignore_errors=True)
                        except:
                            total_failed += 1

        self.log_message(f"Archivos temporales eliminados: {total_deleted}")
        if total_failed > 0:
            self.log_message(f"No se pudieron eliminar {total_failed} archivos o carpetas (en uso).")


    # -------------------------------
    # Mostrar estado actual de memoria virtual
    # -------------------------------
    def show_current_virtual_memory(self):
        try:
            result = subprocess.run(
                ["wmic", "pagefileset", "list", "/format:list"],
                shell=True, capture_output=True, text=True, encoding="utf-8"
            )
            output = result.stdout.strip()
            if output:
                self.log_message("Configuración actual de memoria virtual:")
                for line in output.splitlines():
                    if line.strip():
                        self.log.append(f"    {line.strip()}")
            else:
                self.log_message("No se pudo obtener información de memoria virtual.")
        except Exception as e:
            self.log_message(f"Error mostrando memoria virtual actual: {e}")

    # -------------------------------
    # Ajuste de memoria virtual
    # -------------------------------
    def adjust_virtual_memory(self):
        try:
            # Mostrar configuración actual primero
            self.show_current_virtual_memory()
            self.log.append(" ")

            modo, ok = QInputDialog.getItem(
                self, "Ajuste de Memoria Virtual",
                "Selecciona el modo:",
                ["Automático (recomendado)", "Manual (personalizado)"],
                0, False
            )

            if not ok:
                return

            # --- MODO AUTOMÁTICO ---
            if "Automático" in modo:
                subprocess.run([
                    "wmic", "computersystem", "where", "name='%computername%'",
                    "set", "AutomaticManagedPagefile=True"
                ], shell=True)
                self.log_message("Memoria virtual configurada en modo automático.")
                return

            # --- MODO MANUAL ---
            drives = [d.device for d in psutil.disk_partitions() if 'fixed' in d.opts.lower()]
            if not drives:
                QMessageBox.warning(self, "Error", "No se detectaron discos fijos.")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("Configuración manual de memoria virtual")
            form = QFormLayout(dialog)

            spinboxes = {}
            for drive in drives:
                drive_letter = drive[0].upper()
                free_mb = psutil.disk_usage(drive_letter + ":\\").free // (1024 * 1024)

                last_values = self.last_config.get(drive_letter, {"min": 1024, "max": 2048})

                form.addRow(QLabel(f"💽 Disco {drive_letter}: (Espacio libre: {free_mb} MB)"))

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

            # Desactivar gestión automática
            subprocess.run([
                "wmic", "computersystem", "where", "name='%computername%'",
                "set", "AutomaticManagedPagefile=False"
            ], shell=True)

            new_config = {}

            for drive_letter, (spin_min, spin_max) in spinboxes.items():
                inicial = spin_min.value()
                maximo = spin_max.value()
                free_space_mb = psutil.disk_usage(drive_letter + ":\\").free // (1024 * 1024)

                if free_space_mb < maximo + 500:
                    self.log_message(f"[AVISO] Espacio insuficiente en {drive_letter}:, ajuste no aplicado.")
                    continue

                subprocess.run([
                    "wmic", "pagefileset", "where", f"name='{drive_letter}\\\\pagefile.sys'",
                    "set", f"InitialSize={inicial},MaximumSize={maximo}"
                ], shell=True)

                new_config[drive_letter] = {"min": inicial, "max": maximo}
                self.log_message(f"Memoria virtual ajustada en {drive_letter}: {inicial}MB → {maximo}MB")

            # Guardar configuración
            self.save_config(new_config)

        except Exception as e:
            self.log_message(f"Error ajustando memoria virtual: {e}")

    # -------------------------------
    # Vaciar papelera
    # -------------------------------
    def clean_recycle_bin(self):
        try:
            ps_script = r"""
            try {
                $drives = Get-PSDrive -PSProvider FileSystem | Select-Object -ExpandProperty Root
                foreach ($d in $drives) {
                    try {
                        Clear-RecycleBin -DriveLetter $d[0] -Force -ErrorAction Stop
                    } catch {
                        # Ignorar errores en discos sin papelera
                    }
                }
            } catch {
                # Ignorar errores globales
            }
            """
            subprocess.run(
                ["powershell", "-Command", ps_script],
                shell=True, capture_output=True, text=True, encoding="utf-8"
            )
            self.log_message("Papelera de reciclaje vaciada correctamente en todas las unidades.")
        except Exception as e:
            self.log_message(f"Error vaciando papelera: {e}")


    # -------------------------------
    # Configuración persistente
    # -------------------------------
    def load_config(self):
        """Carga configuración previa de virtual_memory_config.json"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
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
