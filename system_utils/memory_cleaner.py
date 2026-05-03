"""
SystemManagerV1

Autor: Ismel Gabriel
Versión: 1.0
Descripción: Módulo de utilidades del sistema para limpiar
la memoria RAM y reducir el working set de procesos.
"""

import os
import ctypes
import sys
import subprocess
from typing import Tuple
import psutil


def trim_working_set_all():
    """
    Recorta el working set de todos los procesos posibles.
    Retorna (ok, mensaje) con el resultado del barrido.
    """
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    SetProcessWorkingSetSize = kernel32.SetProcessWorkingSetSize
    SetProcessWorkingSetSize.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_size_t,
    ]
    SetProcessWorkingSetSize.restype = ctypes.c_int

    PROCESS_ALL_ACCESS = 0x001F0FFF

    total = 0
    trimmed = 0
    failed = 0

    for proc in psutil.process_iter(["pid", "name"]):
        pid = proc.info["pid"]
        total += 1
        try:
            hproc = ctypes.windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
            if not hproc:
                failed += 1
                continue

            result = SetProcessWorkingSetSize(
                hproc, ctypes.c_size_t(-1), ctypes.c_size_t(-1)
            )
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


def run_emptystandby(empty_tool_path: str) -> Tuple[bool, str]:
    """Ejecuta EmptyStandbyList.exe para limpiar la memoria standby."""
    if not os.path.isfile(empty_tool_path):
        return False, "No se encontró EmptyStandbyList.exe en la ruta indicada."
    try:
        subprocess.run(
            [empty_tool_path, "standbylist"],
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True, "Se ejecutó EmptyStandbyList.exe correctamente."
    except subprocess.CalledProcessError as e:
        return False, f"Error al ejecutar la herramienta: {e}"
    except Exception as e:
        return False, str(e)
