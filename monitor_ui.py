"""
SystemManagerV1

Autor: Ismel Gabriel
Versión: 1.0
Descripción: Interfaz flotante translúcida para visualizar
en tiempo real el uso de CPU y RAM.
"""

import sys
import psutil
import subprocess
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QHBoxLayout,
    QMenu,
    QMessageBox,
)
from PyQt5.QtCore import QTimer, Qt, QPoint
from system_utils.memory_cleaner import trim_working_set_all


class FloatingMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.9)
        self.resize(190, 32)
        self.move(20, 20)

        self.setStyleSheet(
            """
            QWidget {
                background-color: rgba(24, 24, 27, 220);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 6px;
            }
            QLabel {
                background-color: transparent;
                border: none;
                color: #e4e4e7;
                font-family: 'Segoe UI', 'San Francisco', sans-serif;
                font-size: 11px;
                font-weight: bold;
                padding: 0px 4px;
            }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)

        self.drag_handle = QLabel("⋮")
        self.drag_handle.setStyleSheet("color: rgba(255,255,255,100); font-size: 14px;")

        self.cpu_label = QLabel("CPU: 0.0%")
        self.ram_label = QLabel("RAM: 0.0%")

        layout.addWidget(self.drag_handle)
        layout.addWidget(self.cpu_label)
        layout.addStretch()
        layout.addWidget(self.ram_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_labels)
        self.timer.start(1000)

        self._old_pos = None

    def update_labels(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        self.cpu_label.setText(
            f'CPU: <span style="color: #4ade80; font-family: Consolas;">{cpu:.1f}%</span>'
        )
        self.ram_label.setText(
            f'RAM: <span style="color: #38bdf8; font-family: Consolas;">{ram:.1f}%</span>'
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPos()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if self._old_pos is not None:
            delta = QPoint(event.globalPos() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self._old_pos = None

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            "background-color: white; color: black; border-radius: 0px; padding: 2px;"
        )

        limpiar_ram_action = menu.addAction("Limpiar RAM")
        limpiar_papelera_action = menu.addAction("Limpiar papelera")
        toggle_topmost_action = menu.addAction(
            "Desanclar de arriba"
            if self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
            else "Anclar arriba"
        )
        cerrar_action = menu.addAction("Cerrar monitor")

        action = menu.exec_(pos)

        if action == limpiar_ram_action:
            self.limpiar_memoria()
        elif action == limpiar_papelera_action:
            self.limpiar_papelera()
        elif action == toggle_topmost_action:
            self.toggle_topmost()
        elif action == cerrar_action:
            self.close()

    def limpiar_memoria(self):
        before = psutil.virtual_memory().used
        trim_working_set_all()
        after = psutil.virtual_memory().used
        freed = before - after
        if freed > 0:
            msg = f"Se liberaron {freed / (1024 * 1024):.2f} MB de memoria."
        else:
            msg = "No se liberó memoria."
        QMessageBox.information(self, "Memory Cleaner", msg)

    def limpiar_papelera(self):
        import ctypes
        try:
            # Flags: 1 (Sin confirmación), 2 (Sin progreso), 4 (Sin sonido)
            flags = 1 | 2 | 4
            result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)

            if result == 0:
                QMessageBox.information(self, "Papelera", "Papelera vaciada correctamente.")
            else:
                QMessageBox.information(self, "Papelera", "La papelera ya estaba vacía o no se pudo vaciar.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error vaciando papelera: {e}")

    def toggle_topmost(self):
        flags = self.windowFlags()
        if flags & Qt.WindowType.WindowStaysOnTopHint:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    monitor = FloatingMonitor()
    monitor.show()
    sys.exit(app.exec_())
