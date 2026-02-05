"""Interfaz flotante de monitor de sistema."""
import tkinter as tk
from tkinter import messagebox
import threading
import time
import subprocess
import psutil
from system_utils.memory_cleaner import trim_working_set_all

def exit_app():
    """Cierra el UI flotante."""
    root.destroy()

def right_click(event):
    """Muestra el menú contextual al hacer clic derecho."""
    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label="Limpiar RAM", command=limpiar_memoria)
    menu.add_command(label="Limpiar papelera", command=limpiar_papelera)
    menu.add_command(label="Cerrar monitor", command=exit_app)
    if root.attributes("-topmost"):
        menu.add_command(label="Llevar atras", command=topmost_toggle)
    else:
        menu.add_command(label="Llevar adelante", command=topmost_toggle)
    menu.tk_popup(event.x_root, event.y_root)

def move_window(event):
    """Mueve la ventana al arrastrarla."""
    root.geometry(f'+{event.x_root}+{event.y_root}')

def topmost_toggle():
    """Alterna el estado de 'siempre encima' de la ventana."""
    root.attributes("-topmost", not root.attributes("-topmost"))

root = tk.Tk()
root.title("System Monitor")
root.overrideredirect(True)  # sin barra de título
root.attributes("-topmost", False)  # siempre encima
root.attributes("-alpha", 0.8)  # transparencia
root.geometry("150x20")
root.configure(bg="#0ab1ff")

# --- Etiquetas dinámicas ---
cpu_label = tk.Label(
    root, text="CPU: 0%", fg="red", bg="#0ab1ff",
    anchor="w", font=("Consolas", 8)
)
cpu_label.pack(fill="x", pady=2, side="left")

ram_label = tk.Label(
    root, text="RAM: 0%", fg="red", bg="#0ab1ff",
    anchor="w", font=("Consolas", 8))
ram_label.pack(fill="x", pady=2, side="right")

# --- Eventos de arrastre y clic derecho ---
root.bind("<B1-Motion>", move_window)
root.bind("<Button-3>", right_click)

# --- Botón limpiar ---
def limpiar_memoria():
    """Limpia la memoria RAM y muestra un mensaje con el resultado."""

    # RAM usada antes
    before = psutil.virtual_memory().used

    # Ejecuta la limpieza
    trim_working_set_all()

    # RAM usada después
    after = psutil.virtual_memory().used

    # Calcular diferencia
    freed = before - after
    if freed > 0:
        freed_mb = freed / (1024 * 1024)
        msg = f"Se liberaron {freed_mb:.2f} MB de memoria."
    else:
        msg = "No se liberó memoria."

    messagebox.showinfo("Memory Cleaner", msg)


def actualizar_labels():
    """Función de actualización."""
    while True:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        # disk = psutil.disk_usage('/').percent

        cpu_label.config(text=f"CPU: {cpu:.1f}%")
        ram_label.config(text=f"RAM: {ram:.1f}%")
        # activity_label.config(text=f"Almacenamiento: {disk:.1f}%")

        time.sleep(1)

def limpiar_papelera():
    """Vacía la papelera de reciclaje desde el monitor"""
    try:
        # Verificar si hay elementos
        ps_script = r"""
        $shell = New-Object -ComObject Shell.Application
        $recycleBin = $shell.NameSpace(10)
        $itemCount = $recycleBin.Items().Count
        Write-Output $itemCount
        """
        # pylint: disable=subprocess-run-check
        result = subprocess.run(
            [
                "powershell", "-ExecutionPolicy", "Bypass",
                "-Command", ps_script
            ],
            capture_output=True, text=True, encoding="utf-8"
        )

        item_count = result.stdout.strip()

        if item_count == "0":
            messagebox.showinfo(
                "Papelera", "La papelera de reciclaje ya está vacía."
            )
            return

        # Vaciar la papelera
        subprocess.run(
            [
                "powershell", "-ExecutionPolicy", "Bypass", "-Command",
                "Clear-RecycleBin -Force -Confirm:$false -ErrorAction SilentlyContinue"
            ],
            capture_output=True, text=True, encoding="utf-8"
        )

        messagebox.showinfo(
            "Papelera",
            f"Papelera vaciada correctamente ({item_count} elementos eliminados)."
        )
    # pylint: disable=broad-exception-caught
    except Exception as e:
        messagebox.showerror("Error", f"Error vaciando papelera: {e}")

# --- Hilo aparte para refrescar ---
threading.Thread(target=actualizar_labels, daemon=True).start()

root.mainloop()
