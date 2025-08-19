import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

def list_startup_entries() -> dict:
    entries = {}
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
                entries[name] = value
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
    except Exception:
        pass
    return entries

def add_startup_entry(name: str, command: str) -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

def remove_startup_entry(name: str) -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False
