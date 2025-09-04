import winreg

def get_startup_programs():
    locations = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ]

    programs = []
    for root, path in locations:
        try:
            with winreg.OpenKey(root, path) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        programs.append((name, value))
                        i += 1
                    except OSError:
                        break
        except FileNotFoundError:
            pass
    return programs

for name, value in get_startup_programs():
    print(f"{name}: {value}")
