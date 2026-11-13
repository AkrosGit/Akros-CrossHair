# Modulo para lectura y gestion de mandos de juego
import logging
import re
import threading

from PyQt5.QtCore import QTimer


LOGGER = logging.getLogger(__name__)
SDL_HOTKEY_PREFIX = 'SDL:'
CONTROL_RE = re.compile(r'^(?:b\d+|h\d+[udlr]+)$')


# Formatea los controles del mando en una cadena de texto identificadora
def format_hotkey(guid, controls):
    encoded = ','.join(sorted(set(controls)))
    return f'GP:{SDL_HOTKEY_PREFIX}{guid.lower()}:{encoded}'


# Interpreta la cadena del atajo para extraer los controles del mando
def parse_hotkey(value):
    parts = value.split(':', 2)
    if len(parts) != 3 or parts[0] != SDL_HOTKEY_PREFIX[:-1]:
        return None
    guid = parts[1].strip().lower()
    controls = tuple(sorted(set(parts[2].split(','))))
    if not guid or not controls or any(not CONTROL_RE.fullmatch(control) for control in controls):
        return None
    return guid, controls


# Genera una descripcion legible para los botones y direcciones del mando
def describe_control(control):
    if control.startswith('b'):
        return f'Botón {int(control[1:]) + 1}'
    directions = {'u': 'arriba', 'd': 'abajo', 'l': 'izquierda', 'r': 'derecha'}
    direction = re.sub(r'^h\d+', '', control)
    direction = ' + '.join(directions[letter] for letter in direction)
    return f'Cruceta {direction}'


# Monitor interno que sondea periodicamente el estado de los mandos conectados
class _GamepadMonitor:
    def __init__(self, pygame):
        self._pygame = pygame
        self._lock = threading.Lock()
        self._pressed = frozenset()
        pygame.display.init()
        pygame.display.set_mode((1, 1), pygame.HIDDEN)
        pygame.joystick.init()
        self._joysticks = []
        self._refresh_joysticks()
        self._timer = QTimer()
        self._timer.setInterval(20)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    def _refresh_joysticks(self):
        for joystick in self._joysticks:
            joystick.quit()
        self._joysticks = []
        for index in range(self._pygame.joystick.get_count()):
            joystick = self._pygame.joystick.Joystick(index)
            joystick.init()
            self._joysticks.append(joystick)

    def _poll(self):
        pygame = self._pygame
        pygame.event.pump()
        refresh = False
        for event in pygame.event.get():
            if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                refresh = True
        if refresh:
            self._refresh_joysticks()

        pressed = set()
        try:
            for joystick in self._joysticks:
                guid = joystick.get_guid().lower()
                instance_id = joystick.get_instance_id()
                for index in range(joystick.get_numbuttons()):
                    if joystick.get_button(index):
                        pressed.add((guid, instance_id, f'b{index}'))
                for index in range(joystick.get_numhats()):
                    x, y = joystick.get_hat(index)
                    direction = ('l' if x < 0 else 'r' if x > 0 else '')
                    direction += ('u' if y > 0 else 'd' if y < 0 else '')
                    if direction:
                        pressed.add((guid, instance_id, f'h{index}{direction}'))
        except pygame.error:
            LOGGER.exception('Could not read a connected gamepad.')
            self._refresh_joysticks()
            return
        with self._lock:
            self._pressed = frozenset(pressed)

    def pressed_buttons(self):
        with self._lock:
            return self._pressed


_monitor = None


# Inicializa el subsistema de monitorizacion de mandos
def initialize():
    global _monitor
    if _monitor is None:
        import pygame
        _monitor = _GamepadMonitor(pygame)


# Obtiene el conjunto de botones presionados actualmente
def get_pressed_buttons():
    if _monitor is None:
        return frozenset()
    return _monitor.pressed_buttons()


# Comprueba si una combinacion de controles del mando esta presionada
def is_pressed(guid, controls):
    pressed = get_pressed_buttons()
    instance_ids = {instance_id for device_guid, instance_id, _ in pressed if device_guid == guid}
    return any(all((guid, instance_id, control) in pressed for control in controls)
               for instance_id in instance_ids)

