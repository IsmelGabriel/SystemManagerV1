"""
SystemManagerV1

Autor: Ismel Gabriel
Versión: 1.0
Descripción: Pestaña principal para monitorizar el uso
general de CPU, RAM, Red y Discos en tiempo real.
"""

import platform
import psutil
import cpuinfo
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit,
    QTabWidget,
    QPushButton,
    QMessageBox,
)
from PyQt5.QtCore import QTimer
from system_utils.memory_cleaner import trim_working_set_all

from process_manager import ProcessTab
from startup_manager import StartupTab
from optimizer_manager import OptimizerTab


class MonitorTab(QWidget):
    """Pestaña de monitorización del sistema."""

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)

        self.stats_layout = QHBoxLayout()

        self.create_basic_layouts()

        self.disk_layouts = {}
        self.disk_bars = {}
        self.create_disk_layouts()

        main_layout.addLayout(self.stats_layout)

        self.specs = QTextEdit()
        self.specs.setReadOnly(True)
        self.specs.setText(self.get_specs())
        main_layout.addWidget(self.specs)

        self.refresh_button = QPushButton("Limpiar memoria")
        self.refresh_button.clicked.connect(self.refresh_memory)

        main_layout.addWidget(self.refresh_button)
        main_layout.addStretch()
        self.setLayout(main_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

    def get_specs(self):
        """Obtiene las especificaciones del sistema."""
        cpu_info = cpuinfo.get_cpu_info()
        discos = psutil.disk_partitions()

        nuc_fisicos = psutil.cpu_count(logical=False)
        nuc_logicos = psutil.cpu_count(logical=True)

        ram_total_gb = round(psutil.virtual_memory().total / (1024**3), 2)

        info = (
            f"Sistema: {platform.system()} {platform.release()}\n"
            f"Versión: {platform.version()}\n"
            f"Nombre del equipo: {platform.node()}\n"
            f"Detalles del CPU: {platform.processor()}\n"
            f"Procesador: {cpu_info['brand_raw']}\n"
            f"Arquitectura: {cpu_info['arch']}\n"
            f"Núcleos: {nuc_fisicos} físicos / {nuc_logicos} lógicos\n"
            f"RAM disponible: {ram_total_gb} GB\n"
        )

        discos_info = []
        for disco in discos:
            try:
                if "fixed" in disco.opts:
                    uso = psutil.disk_usage(disco.mountpoint)
                    total_gb = round(uso.total / (1024**3), 2)
                    usado_gb = round(uso.used / (1024**3), 2)
                    discos_info.append(
                        f"Disco {disco.device.split(':')[0]}: {total_gb} GB "
                        f"(En uso {usado_gb} GB)"
                    )
            except Exception:
                continue

        if discos_info:
            info += "\nDiscos detectados:\n" + "\n".join(discos_info) + "\n"

        return info

    def refresh_memory(self):
        """Llama a la función de limpieza de memoria."""
        before = psutil.virtual_memory().used
        trim_working_set_all()
        after = psutil.virtual_memory().used
        freed = before - after

        if freed > 0:
            freed_mb = freed / (1024 * 1024)
            msg = f"Se liberaron {freed_mb:.2f} MB de memoria."
        else:
            msg = "No se liberó memoria."
        QMessageBox.information(self, "Memory Cleaner", msg)

    def create_basic_layouts(self):
        """Crea los layouts básicos (CPU, RAM, RED)"""
        self.cpu_label = QLabel("CPU")
        self.cpu_bar = QProgressBar()
        cpu_box = QVBoxLayout()
        cpu_box.addWidget(self.cpu_label)
        cpu_box.addWidget(self.cpu_bar)

        self.ram_label = QLabel("RAM")
        self.ram_bar = QProgressBar()
        ram_box = QVBoxLayout()
        ram_box.addWidget(self.ram_label)
        ram_box.addWidget(self.ram_bar)

        self.net_label = QLabel("Red")
        self.net_bar = QProgressBar()
        net_box = QVBoxLayout()
        net_box.addWidget(self.net_label)
        net_box.addWidget(self.net_bar)

        self.stats_layout.addLayout(cpu_box)
        self.stats_layout.addLayout(ram_box)
        self.stats_layout.addLayout(net_box)

    def create_disk_layouts(self):
        """Crea layouts dinámicamente para cada disco"""
        discos = psutil.disk_partitions()

        for disco in discos:
            try:
                if "fixed" in disco.opts:
                    letra = disco.device.split(":")[0]

                    label = QLabel(f"Disco {letra}")
                    bar = QProgressBar()

                    disk_box = QVBoxLayout()
                    disk_box.addWidget(label)
                    disk_box.addWidget(bar)

                    self.disk_layouts[letra] = disk_box
                    self.disk_bars[letra] = bar

                    self.stats_layout.addLayout(disk_box)
            except Exception:
                continue

    def update_stats(self):
        """Actualiza las estadísticas incluyendo todos los discos"""
        self.cpu_bar.setValue(int(psutil.cpu_percent()))
        self.ram_bar.setValue(int(psutil.virtual_memory().percent))

        net_io = psutil.net_io_counters()
        net_activity = (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024)
        self.net_bar.setValue(min(100, int(net_activity % 100)))

        for letra, bar in self.disk_bars.items():
            try:
                uso = psutil.disk_usage(f"{letra}:")
                bar.setValue(int(uso.percent))
            except Exception:
                continue


class MonitorWindow(QTabWidget):
    """Ventana principal con pestañas."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SystemManager v1")
        self.resize(900, 500)

        self.addTab(MonitorTab(), "Monitor")
        self.addTab(ProcessTab(), "Procesos")
        self.addTab(StartupTab(), "Inicio")
        self.addTab(OptimizerTab(), "Optimización")
