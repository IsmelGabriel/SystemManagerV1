import platform
import psutil
import cpuinfo
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTextEdit, QTabWidget, QPushButton, QMessageBox
from PyQt5.QtCore import QTimer
from process_manager import ProcessTab
from startup_manager import StartupTab
from system_utils.memory_cleaner import trim_working_set_all

class MonitorTab(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- Layout general ---
        main_layout = QVBoxLayout(self)

        # --- Layout de los cuadros ---
        grid_layout = QHBoxLayout()
        self.stats_layout = grid_layout
        
        # Crear layouts básicos (CPU, RAM, RED)
        self.create_basic_layouts()

        # Crear layouts de discos dinámicamente
        self.disk_layouts = {}
        self.disk_bars = {}
        self.create_disk_layouts()
        
        main_layout.addLayout(self.stats_layout)

        # --- Especificaciones ---
        self.specs = QTextEdit()
        self.specs.setReadOnly(True)
        self.specs.setText(self.get_specs())
        main_layout.addWidget(self.specs)
        
        # --- Refrescar memoria ---
        self.refresh_button = QPushButton("Limpiar memoria")
        self.refresh_button.clicked.connect(self.refresh_memory)
        
        main_layout.addWidget(self.refresh_button)
        main_layout.addStretch()
        self.setLayout(main_layout)
        

        # --- Timer para actualizar ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)
        
    def get_specs(self):
        cpu_info = cpuinfo.get_cpu_info()
        discos = psutil.disk_partitions()
        
        info = (
            f"Sistema: {platform.system()} {platform.release()}\n"
            f"Versión: {platform.version()}\n"
            f"Nombre del equipo: {platform.node()}\n"
            f"Detalles del CPU: {platform.processor()}\n"
            f"Procesador: {cpu_info['brand_raw']}\n"
            f"Arquitectura: {cpu_info['arch']}\n"
            f"Núcleos: {psutil.cpu_count(logical=False)} físicos, {psutil.cpu_count(logical=True)} lógicos\n"
            f"RAM total: {round(psutil.virtual_memory().total / (1024**3), 2)} GB\n"
        )
        
        discos_info = []
        for disco in discos:
            try:
                if 'fixed' in disco.opts:
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
    
    def update_stats(self):
        """Actualiza las estadísticas incluyendo todos los discos"""
        self.cpu_bar.setValue(int(psutil.cpu_percent()))
        self.ram_bar.setValue(int(psutil.virtual_memory().percent))
        
        # Actualizar red
        net_io = psutil.net_io_counters()
        net_activity = (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024)
        self.net_bar.setValue(min(100, int(net_activity % 100)))
        
        # Actualizar todos los discos
        for letra, bar in self.disk_bars.items():
            try:
                uso = psutil.disk_usage(f"{letra}:")
                bar.setValue(int(uso.percent))
            except Exception:
                continue

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
        # CPU
        self.cpu_label = QLabel("CPU")
        self.cpu_bar = QProgressBar()
        cpu_box = QVBoxLayout()
        cpu_box.addWidget(self.cpu_label)
        cpu_box.addWidget(self.cpu_bar)

        # RAM
        self.ram_label = QLabel("RAM")
        self.ram_bar = QProgressBar()
        ram_box = QVBoxLayout()
        ram_box.addWidget(self.ram_label)
        ram_box.addWidget(self.ram_bar)

        # RED
        self.net_label = QLabel("Red")
        self.net_bar = QProgressBar()
        net_box = QVBoxLayout()
        net_box.addWidget(self.net_label)
        net_box.addWidget(self.net_bar)

        # Agregar layouts básicos
        self.stats_layout.addLayout(cpu_box)
        self.stats_layout.addLayout(ram_box)
        self.stats_layout.addLayout(net_box)

    def create_disk_layouts(self):
        """Crea layouts dinámicamente para cada disco"""
        discos = psutil.disk_partitions()
        
        for disco in discos:
            try:
                if 'fixed' in disco.opts:
                    letra = disco.device.split(':')[0]
                    
                    # Crear elementos para el disco
                    label = QLabel(f"Disco {letra}")
                    bar = QProgressBar()
                    
                    # Crear layout para el disco
                    disk_box = QVBoxLayout()
                    disk_box.addWidget(label)
                    disk_box.addWidget(bar)
                    
                    # Guardar referencias
                    self.disk_layouts[letra] = disk_box
                    self.disk_bars[letra] = bar
                    
                    # Agregar al layout principal
                    self.stats_layout.addLayout(disk_box)
            except Exception:
                continue


# ---- Ventana principal con pestañas ----
class MonitorWindow(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SystemManager v1")
        self.resize(900, 500)

        # Aquí se agregan las pestañas
        self.addTab(MonitorTab(), "Monitor")
        self.addTab(ProcessTab(), "Procesos")
        self.addTab(StartupTab(), "Inicio")
        # self.addTab(RendimientoTab(), "Rendimiento")
