# Deteccion de juegos y procesos activos en primer plano
import os
import re
import sys
import psutil

IS_WINDOWS = sys.platform == 'win32'
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

# Lista de nombres comunes para identificar videojuegos conocidos
GAME_ALIASES = {
    'minecraft': ('javaw', 'minecraft'),
    'counter-strike': ('cs2', 'csgo'),
    'fortnite': ('fortniteclient-win64-shipping',),
    'valorant': ('valorant-win64-shipping',),
    'apex legends': ('r5apex',),
    'overwatch': ('overwatch',),
    'grand theft auto': ('gta5', 'gtav', 'playgtav'),
    'call of duty': ('cod', 'modernwarfare', 'blackops'),
    'rust': ('rustclient',),
    'rainbow six': ('rainbowsix', 'rainbowsix_vulkan'),
}


def _stem(name):
    name = (name or '').strip().lower()
    return name[:-4] if name.endswith('.exe') else name


# Identificacion del proceso y ventana activa en primer plano
def get_foreground_details():
    if not IS_WINDOWS:
        return 0, '', ''
    try:
        user = ctypes.windll.user32
        hwnd = user.GetForegroundWindow()
        if not hwnd:
            return 0, '', ''
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 0:
            return 0, '', ''

        length = user.GetWindowTextLengthW(hwnd)
        title = ''
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

        proc_name = ''
        try:
            proc_name = psutil.Process(pid.value).name()
        except Exception:
            pass

        return pid.value, proc_name, title
    except Exception:
        return 0, '', ''


# Lista de procesos ejecutables en ejecucion
def get_running_processes():
    results = set()
    ignored = {
        'svchost.exe', 'conhost.exe', 'taskhostw.exe', 'runtimebroker.exe',
        'explorer.exe', 'system', 'system idle process', 'registry',
        'smss.exe', 'csrss.exe', 'wininit.exe', 'services.exe', 'lsass.exe',
        'fontdrvhost.exe', 'dwm.exe', 'winlogon.exe', 'sihost.exe'
    }
    for p in psutil.process_iter(['name']):
        try:
            name = p.info['name']
            if name and name.lower().endswith('.exe') and name.lower() not in ignored:
                results.add(name)
        except Exception:
            pass
    return sorted(results, key=lambda s: s.lower())


# Comprobacion de coincidencia entre ventana activa y objetivo buscado
def _target_matches(target_name, proc, title):
    target = (target_name or '').strip().lower()
    if not target:
        return False
    proc_stem = _stem(proc)
    title_low = (title or '').lower()
    t_stem = _stem(target)

    # Evaluacion de coincidencia segun el nombre del archivo ejecutable
    if proc_stem and (proc_stem == t_stem or (len(t_stem) >= 4 and t_stem in proc_stem)):
        return True

    # Evaluacion de coincidencia segun el titulo de la ventana
    if re.search(r'(?<!\w)' + re.escape(t_stem) + r'(?!\w)', title_low):
        return True

    for alias in GAME_ALIASES.get(t_stem, ()):
        if proc_stem == alias or alias in title_low.split():
            return True
    return False


# Consulta de la ventana principal para comparar contra varios objetivos
def match_foreground(targets):
    pid, proc, title = get_foreground_details()
    if pid and pid == os.getpid():
        return True, None
    if not proc and not title:
        return False, None
    for target in targets:
        if _target_matches(target, proc, title):
            return False, target
    return False, None

