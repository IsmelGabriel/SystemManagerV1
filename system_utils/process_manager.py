import psutil
from typing import List, Dict

def list_processes() -> List[Dict]:
    """
    Devuelve lista de procesos con: pid, name, username, cpu_percent, memory_info.rss
    """
    procs = []
    for p in psutil.process_iter(['pid','name','username','cpu_percent','memory_info']):
        try:
            info = p.info
            mem_rss = info['memory_info'].rss if info.get('memory_info') else 0
            procs.append({
                'pid': info.get('pid'),
                'name': info.get('name'),
                'user': info.get('username'),
                'cpu': p.cpu_percent(interval=0),
                'memory_rss': mem_rss
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    # ordenar por uso de memoria descendente
    procs.sort(key=lambda x: x['memory_rss'], reverse=True)
    return procs

def kill_process(pid: int) -> bool:
    """
    Intenta terminar el proceso. Devuelve True si se terminó, False si falló.
    """
    try:
        p = psutil.Process(pid)
        p.terminate()
        p.wait(timeout=3)
        return True
    except psutil.NoSuchProcess:
        return True
    except Exception:
        try:
            p.kill()
            p.wait(timeout=3)
            return True
        except Exception:
            return False
