# Administracion del inicio automatico de la aplicacion en el sistema operativo
import os
import sys

try:
    import winreg
except ImportError:  # Solo existe en Windows
    winreg = None

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
APP_KEY_NAME = 'AkrosCrossHair'


# Comando de ejecucion en segundo plano sin consola
def get_startup_command():
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}" --tray'
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(base_dir, 'main.py')
    py_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(py_dir, 'pythonw.exe')
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    return f'"{pythonw}" "{main_py}" --tray'


# Consulta del estado de inicio automatico con el sistema
def is_startup_enabled():
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_KEY_NAME)
        finally:
            winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False


# Configuracion de arranque automatico en el registro de usuario
def set_startup_enabled(enabled):
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            if enabled:
                winreg.SetValueEx(key, APP_KEY_NAME, 0, winreg.REG_SZ, get_startup_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_KEY_NAME)
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)
        return True
    except Exception:
        return False
