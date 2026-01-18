import ctypes
import sys
import psutil
import subprocess
import os
from typing import Tuple

def run_as_admin():
    """
    Ejecuta el programa con privilegios de administrador en windows
    """
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False
    if not is_admin:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

run_as_admin()


def trim_working_set_all():
    """
    Recorta el working set de todos los procesos posibles.
    Retorna (ok, mensaje) con el resultado del barrido.
    """
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    SetProcessWorkingSetSize = kernel32.SetProcessWorkingSetSize
    SetProcessWorkingSetSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
    SetProcessWorkingSetSize.restype = ctypes.c_int

    # Constantes para permisos completos en el proceso
    PROCESS_ALL_ACCESS = 0x001F0FFF

    total = 0
    trimmed = 0
    failed = 0

    for proc in psutil.process_iter(['pid', 'name']):
        pid = proc.info['pid']
        total += 1
        try:
            hproc = ctypes.windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
            if not hproc:
                failed += 1
                continue

            # (-1, -1) => recorte automático del sistema
            result = SetProcessWorkingSetSize(hproc, ctypes.c_size_t(-1), ctypes.c_size_t(-1))
            ctypes.windll.kernel32.CloseHandle(hproc)

            if result != 0:
                trimmed += 1
            else:
                failed += 1

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            failed += 1
        except Exception:
            failed += 1

    mensaje = f"Procesos totales: {total} | Recortados: {trimmed} | Fallidos: {failed}"
    return True, mensaje

# --- Opción B: usar EmptyStandbyList.exe ---
def run_emptystandby(empty_tool_path: str) -> Tuple[bool, str]:
    if not os.path.isfile(empty_tool_path):
        return False, "No se encontró EmptyStandbyList.exe en la ruta indicada."
    try:
        subprocess.run([empty_tool_path, "standbylist"], check=True)
        return True, "Se ejecutó EmptyStandbyList.exe correctamente."
    except subprocess.CalledProcessError as e:
        return False, f"Error al ejecutar la herramienta: {e}"
    except Exception as e:
        return False, str(e)
