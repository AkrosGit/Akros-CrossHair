# Deteccion y escucha de atajos globales para teclado raton y mandos
import ctypes
import re
import threading
import time
from ctypes import wintypes

from gamepad_input import initialize as initialize_gamepad_input
from gamepad_input import is_pressed as is_sdl_gamepad_pressed
from gamepad_input import parse_hotkey as parse_sdl_gamepad_hotkey


# Convierte el texto del usuario al formato que entiende la libreria keyboard
def normalize_hotkey(text):
    text = (text or '').strip().lower().replace('_', ' ')
    return re.sub(r'\s*\+\s*', '+', text)


# Nombres legibles de los botones de un mando de Xbox via XInput
GAMEPAD_BUTTON_NAMES = {
    0x0001: 'Pad Arriba',
    0x0002: 'Pad Abajo',
    0x0004: 'Pad Izquierda',
    0x0008: 'Pad Derecha',
    0x0010: 'Start',
    0x0020: 'Back',
    0x0040: 'Stick Izq',
    0x0080: 'Stick Der',
    0x0100: 'LB',
    0x0200: 'RB',
    0x1000: 'A',
    0x2000: 'B',
    0x4000: 'X',
    0x8000: 'Y',
}

GAMEPAD_TRIGGER_NAMES = ('Gatillo Izq', 'Gatillo Der')
GAMEPAD_PREFIX = 'GP:'
TRIGGER_THRESHOLD = 30

MOUSE_BUTTON_VKS = {
    'Mouse Derecho': 0x02,
    'Mouse Central': 0x04,
    'Mouse Boton 4': 0x05,
    'Mouse Boton 5': 0x06,
}


class _XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ('wButtons', wintypes.WORD),
        ('bLeftTrigger', wintypes.BYTE),
        ('bRightTrigger', wintypes.BYTE),
        ('sThumbLX', wintypes.SHORT),
        ('sThumbLY', wintypes.SHORT),
        ('sThumbRX', wintypes.SHORT),
        ('sThumbRY', wintypes.SHORT),
    ]


class _XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ('dwPacketNumber', wintypes.DWORD),
        ('Gamepad', _XINPUT_GAMEPAD),
    ]


def _load_xinput():
    for name in ('xinput1_4', 'xinput1_3', 'xinput9_1_0'):
        try:
            return ctypes.windll.LoadLibrary(name)
        except Exception:
            pass
    return None


_xinput = _load_xinput()


def is_gamepad_hotkey(hotkey_str):
    return (hotkey_str or '').startswith(GAMEPAD_PREFIX)


def parse_gamepad_hotkey(hotkey_str):
    part = hotkey_str[len(GAMEPAD_PREFIX):]
    if part.startswith('SDL:'):
        parsed = parse_sdl_gamepad_hotkey(part)
        return ('sdl', parsed[0], parsed[1]) if parsed else None
    parts = part.split('+')
    if len(parts) == 1 and part in GAMEPAD_TRIGGER_NAMES:
        return part
    mask = 0
    for name in parts:
        button_mask = next((value for value, button_name in GAMEPAD_BUTTON_NAMES.items()
                            if button_name == name), None)
        if button_mask is None:
            if len(parts) == 1:
                try:
                    return int(part, 16)
                except ValueError:
                    return None
            return None
        mask |= button_mask
    return mask or None


class _GamepadWatcher:
    def __init__(self, button_mask_or_trigger, callback):
        self._data = button_mask_or_trigger
        self._callback = callback
        self._stop = threading.Event()
        self._was_pressed = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        state = _XINPUT_STATE()
        while not self._stop.is_set():
            pressed = False
            if isinstance(self._data, tuple) and self._data[0] == 'sdl':
                pressed = is_sdl_gamepad_pressed(self._data[1], self._data[2])
            elif _xinput:
                for i in range(4):
                    res = _xinput.XInputGetState(i, ctypes.byref(state))
                    if res == 0:
                        if self._data == 'Gatillo Izq':
                            pressed = state.Gamepad.bLeftTrigger > TRIGGER_THRESHOLD
                        elif self._data == 'Gatillo Der':
                            pressed = state.Gamepad.bRightTrigger > TRIGGER_THRESHOLD
                        elif isinstance(self._data, int):
                            pressed = (state.Gamepad.wButtons & self._data) == self._data
                        if pressed:
                            break
            if pressed and not self._was_pressed:
                self._callback()
            self._was_pressed = pressed
            time.sleep(0.04)

    def stop(self):
        self._stop.set()


class _MouseWatcher:
    def __init__(self, vk_code, callback):
        self._vk = vk_code
        self._callback = callback
        self._stop = threading.Event()
        self._was_pressed = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        user32 = ctypes.windll.user32
        while not self._stop.is_set():
            state = user32.GetAsyncKeyState(self._vk)
            pressed = bool(state & 0x8000)
            if pressed and not self._was_pressed:
                self._callback()
            self._was_pressed = pressed
            time.sleep(0.04)

    def stop(self):
        self._stop.set()


# Administrador de atajos globales de teclado raton y mando
class HotkeyManager:
    def __init__(self, callback):
        self.callback = callback
        self.current_hotkey = ''
        self.hook = None
        self._gamepad_watcher = None
        self._mouse_watcher = None
        self.lock = threading.RLock()

    # Registro de combinacion de teclas o boton de mando
    def set_hotkey(self, hotkey_str):
        with self.lock:
            self.clear_hotkey()
            if not hotkey_str:
                return True
            if is_gamepad_hotkey(hotkey_str):
                data = parse_gamepad_hotkey(hotkey_str)
                if isinstance(data, tuple) and data[0] == 'sdl':
                    initialize_gamepad_input()
                    self._gamepad_watcher = _GamepadWatcher(data, self.callback)
                    self.current_hotkey = hotkey_str
                    return True
                if data is not None and _xinput:
                    self._gamepad_watcher = _GamepadWatcher(data, self.callback)
                    self.current_hotkey = hotkey_str
                    return True
                return False
            if hotkey_str in MOUSE_BUTTON_VKS:
                vk = MOUSE_BUTTON_VKS[hotkey_str]
                self._mouse_watcher = _MouseWatcher(vk, self.callback)
                self.current_hotkey = hotkey_str
                return True
            hotkey = normalize_hotkey(hotkey_str)
            if not hotkey:
                return True
            try:
                import keyboard
                self.hook = keyboard.add_hotkey(hotkey, self.callback)
                self.current_hotkey = hotkey
                return True
            except Exception:
                self.hook = None
                self.current_hotkey = ''
                return False

    # Eliminacion del atajo actual
    def clear_hotkey(self):
        with self.lock:
            if self._gamepad_watcher is not None:
                self._gamepad_watcher.stop()
                self._gamepad_watcher = None
            if self._mouse_watcher is not None:
                self._mouse_watcher.stop()
                self._mouse_watcher = None
            if self.hook is not None:
                try:
                    import keyboard
                    keyboard.remove_hotkey(self.hook)
                except Exception:
                    pass
                self.hook = None
            self.current_hotkey = ''


# Monitor de estados para alternar o mantener segun los botones configurados
class StateInputWatcher:
    POLL_SECONDS = 0.02

    def __init__(self, callback):
        self._callback = callback
        self._lock = threading.RLock()
        self._bindings = {}
        self._stop = threading.Event()
        self._thread = None

    # Registro de botones asignados a cada estado configurado
    def set_bindings(self, items):
        result, bindings = {}, {}
        for state_id, hotkey_str in items:
            parsed = self._parse(hotkey_str)
            result[state_id] = parsed is not None
            if parsed is not None:
                bindings[state_id] = [parsed[0], parsed[1], False]
        with self._lock:
            released = [sid for sid, b in self._bindings.items() if b[2] and sid not in bindings]
            self._bindings = bindings
        # Un boton retirado mientras estaba pulsado no debe dejar el estado atascado
        for sid in released:
            self._callback(sid, False)
        if bindings:
            self._ensure_thread()
        return result

    def clear(self):
        self.set_bindings([])

    def stop(self):
        self._stop.set()

    @staticmethod
    def _parse(hotkey_str):
        if not hotkey_str:
            return None
        if is_gamepad_hotkey(hotkey_str):
            data = parse_gamepad_hotkey(hotkey_str)
            if isinstance(data, tuple) and data[0] == 'sdl':
                initialize_gamepad_input()
                return ('sdl', (data[1], data[2]))
            if data is None or not _xinput:
                return None
            if data in GAMEPAD_TRIGGER_NAMES:
                return ('trigger', data)
            return ('pad', data)
        if hotkey_str in MOUSE_BUTTON_VKS:
            return ('mouse', MOUSE_BUTTON_VKS[hotkey_str])
        text = normalize_hotkey(hotkey_str)
        if not text:
            return None
        try:
            import keyboard
            keyboard.parse_hotkey(text)
            return ('key', text)
        except Exception:
            return None

    def _ensure_thread(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    # Comprobacion del estado de pulsacion de un control
    def _is_pressed(self, kind, data, pad_state):
        try:
            if kind == 'pad':
                pads = pad_state.get('pads', [])
                if pads:
                    return any((buttons & data) == data for buttons in pads)
                buttons = pad_state.get('btns', 0)
                return bool(data) and (buttons & data) == data
            if kind == 'sdl':
                return is_sdl_gamepad_pressed(data[0], data[1])
            if kind == 'trigger':
                if data == 'Gatillo Izq':
                    return pad_state.get('lt', 0) > TRIGGER_THRESHOLD
                return pad_state.get('rt', 0) > TRIGGER_THRESHOLD
            if kind == 'mouse':
                user32 = getattr(ctypes.windll, 'user32', None)
                return bool(user32.GetAsyncKeyState(data) & 0x8000) if user32 else False
            import keyboard
            return keyboard.is_pressed(data)
        except Exception:
            return False

    @staticmethod
    def _read_pad_state():
        result = {'btns': 0, 'lt': 0, 'rt': 0, 'pads': []}
        if not _xinput:
            return result
        state = _XINPUT_STATE()
        for i in range(4):
            if _xinput.XInputGetState(i, ctypes.byref(state)) == 0:
                buttons = state.Gamepad.wButtons
                result['btns'] |= buttons
                result['pads'].append(buttons)
                if state.Gamepad.bLeftTrigger > result['lt']:
                    result['lt'] = state.Gamepad.bLeftTrigger
                if state.Gamepad.bRightTrigger > result['rt']:
                    result['rt'] = state.Gamepad.bRightTrigger
        return result

    def _run(self):
        while not self._stop.is_set():
            with self._lock:
                items = list(self._bindings.items())
            if not items:
                time.sleep(0.1)
                continue
            needs_pad = any(b[0] in ('pad', 'trigger') for _, b in items)
            pad_state = self._read_pad_state() if needs_pad else {'btns': 0, 'lt': 0, 'rt': 0}
            for state_id, binding in items:
                pressed = self._is_pressed(binding[0], binding[1], pad_state)
                if pressed != binding[2]:
                    binding[2] = pressed
                    try:
                        self._callback(state_id, pressed)
                    except Exception:
                        pass
            time.sleep(self.POLL_SECONDS)
