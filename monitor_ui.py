import tkinter as tk
from tkinter import messagebox
import psutil
import threading
import time
from system_utils.memory_cleaner import trim_working_set_all

def exit_app():
    print("Saliendo...")
    root.destroy()

def right_click(event):
    print("Clic izquierdo detectado")
    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label="Limpiar RAM", command=lambda: limpiar_memoria())
    menu.add_command(label="Cerrar monitor", command=lambda: exit_app())
    menu.tk_popup(event.x_root, event.y_root)
    
def move_window(event):
    root.geometry(f'+{event.x_root}+{event.y_root}')
    
# -------------------
# Ventana principal
# -------------------
root = tk.Tk()
root.title("System Monitor")
root.overrideredirect(True)  # sin barra de título
root.attributes("-topmost", True)  # siempre encima
root.attributes("-alpha", 0.8)  # transparencia
root.geometry("70x50")
root.configure(bg="#6902f0")

# --- Etiquetas dinámicas ---
cpu_label = tk.Label(root, text="CPU: 0%", fg="red", bg="#6902f0", anchor="w", font=("Consolas", 8))
cpu_label.pack(fill="x", pady=2)

ram_label = tk.Label(root, text="RAM: 0%", fg="red", bg="#6902f0", anchor="w", font=("Consolas", 8))
ram_label.pack(fill="x", pady=2)

"""activity_label = tk.Label(root, text="Almacenamiento 0%", fg="red", bg="black", anchor="w", font=("Consolas", 8))
activity_label.pack(fill="x", pady=2)
"""

# --- Eventos de arrastre y clic derecho ---
root.bind("<B1-Motion>", move_window)
root.bind("<Button-3>", right_click)

# --- Botón limpiar ---
def limpiar_memoria():
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


# --- Función de actualización ---
def actualizar_labels():
    while True:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        # disk = psutil.disk_usage('/').percent

        cpu_label.config(text=f"CPU: {cpu:.1f}%")
        ram_label.config(text=f"RAM: {ram:.1f}%")
        # activity_label.config(text=f"Almacenamiento: {disk:.1f}%")

        time.sleep(1)

# --- Hilo aparte para refrescar ---
threading.Thread(target=actualizar_labels, daemon=True).start()

root.mainloop()
