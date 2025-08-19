import psutil
import time

def get_cpu_usage():
    return psutil.cpu_percent(interval=0)

def get_memory_info():
    mem = psutil.virtual_memory()
    return {
        'total': mem.total,
        'used': mem.used,
        'free': mem.available,
        'percent': mem.percent
    }

def get_network_usage(interval=1):
    net1 = psutil.net_io_counters()
    time.sleep(interval)
    net2 = psutil.net_io_counters()

    download = (net2.bytes_recv - net1.bytes_recv) / interval
    upload = (net2.bytes_sent - net1.bytes_sent) / interval

    return {
        'download': download,  # bytes/sec
        'upload': upload       # bytes/sec
    }
