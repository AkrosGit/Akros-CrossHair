# Componentes visuales personalizados y controles de interfaz de usuario
import copy
import ctypes
import os
import threading
import time
from PyQt5.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QLayout, QCheckBox, QWidget, QMenu,
    QPushButton, QComboBox, QDialog, QLineEdit, QToolButton, QFileDialog, QSizePolicy
)
from PyQt5.QtCore import Qt, QRect, QRectF, QPoint, QPointF, QSize, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QPainter, QPixmap, QColor, QPen, QFontMetrics, QLinearGradient, QPainterPath, QBrush, QKeySequence
)

from styles import C, THEMES, make_dots_icon, tr
from config_manager import new_preset_id, PRESET_NAME_MAX
from overlay import colorize_pixmap, resolve_crosshair_path
from game_detector import get_running_processes, get_foreground_details
from hotkey_listener import GAMEPAD_BUTTON_NAMES, GAMEPAD_PREFIX, _xinput
from gamepad_input import (
    describe_control,
    format_hotkey as format_sdl_gamepad_hotkey,
    get_pressed_buttons,
    initialize as initialize_gamepad_input,
    parse_hotkey as parse_sdl_gamepad_hotkey,
)


# Determina si una imagen tiene predominancia de tonos oscuros
def image_is_dark(pix):
    if pix is None or pix.isNull():
        return False
    img = pix.toImage().scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    total = weight = 0.0
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            a = c.alphaF()
            if a < 0.05:
                continue
            total += (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) * a
            weight += a
    return weight > 0 and (total / weight) < 140


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


# Distribucion que reparte los elementos en filas y salta de linea segun el ancho disponible
class FlowLayout(QLayout):
    def __init__(self, parent=None, hspacing=10, vspacing=10):
        super().__init__(parent)
        self._items = []
        self._h = hspacing
        self._v = vspacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = area.x(), area.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._h
            if next_x - self._h > area.right() + 1 and line_h > 0:
                x = area.x()
                y += line_h + self._v
                next_x = x + hint.width() + self._h
                line_h = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y() + m.bottom()


# Interruptor visual con animacion de deslizamiento
class ToggleSwitch(QCheckBox):
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 26)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        on = self.isChecked()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C['accent_dark'] if on else C['border_hi']))
        p.drawRoundedRect(QRectF(1, 2, 44, 22), 11, 11)
        p.setBrush(QColor('#FFFFFF' if on else C['muted']))
        x = 24 if on else 4
        p.drawEllipse(QRectF(x, 5, 16, 16))
        if self.hasFocus():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(C['accent']), 1.5))
            p.drawRoundedRect(QRectF(0.5, 1.5, 45, 23), 12, 12)
        p.end()


# Fila contenedora con titulo descripcion y control asociado
class SettingRow(QWidget):
    def __init__(self, title, description, control, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(16)
        text = QVBoxLayout()
        text.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet('font-weight: 600; font-size: 13px;')
        d = QLabel(description)
        d.setObjectName('Muted')
        d.setWordWrap(True)
        text.addWidget(t)
        text.addWidget(d)
        lay.addLayout(text, 1)
        lay.addWidget(control, 0, Qt.AlignVCenter)


# Tarjeta de activacion independiente con opciones desplegables
class ModeCard(QFrame):
    toggled = pyqtSignal(str, bool)

    def __init__(self, key, title, description, body=None, enabled=False, parent=None):
        super().__init__(parent)
        self.key = key
        self.setObjectName('ModeCard')
        self.setCursor(Qt.ArrowCursor)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(14)
        texts = QVBoxLayout()
        texts.setSpacing(3)
        t = QLabel(title)
        t.setObjectName('CardTitle')
        d = QLabel(description)
        d.setObjectName('Muted')
        d.setWordWrap(True)
        texts.addWidget(t)
        texts.addWidget(d)
        head.addLayout(texts, 1)
        self.toggle = ToggleSwitch(enabled)
        self.toggle.toggled.connect(self._on_toggled)
        head.addWidget(self.toggle, 0, Qt.AlignTop)
        outer.addLayout(head)

        self.body = body
        if body is not None:
            body.setCursor(Qt.ArrowCursor)
            body_row = QHBoxLayout()
            body_row.setContentsMargins(34, 0, 0, 0)
            body_row.addWidget(body)
            outer.addLayout(body_row)
        self.set_activation_enabled(enabled)

    def _update_enabled_state(self, enabled):
        if self.body is not None:
            self.body.setVisible(enabled)

    def set_activation_enabled(self, enabled):
        self.toggle.blockSignals(True)
        self.toggle.setChecked(enabled)
        self.toggle.blockSignals(False)
        self._update_enabled_state(enabled)

    def _on_toggled(self, enabled):
        self._update_enabled_state(enabled)
        self.toggled.emit(self.key, enabled)


# Miniatura de una mira dentro de la biblioteca
class CrosshairCard(QFrame):
    clicked = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, filename, filepath, selected=False, color='original', parent=None):
        super().__init__(parent)
        self.filename = filename
        self._color = 'original'
        self.setObjectName('CrosshairCard')
        self.setProperty('selected', selected)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(92, 100)
        self.setToolTip(filename)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 9, 6, 8)
        lay.setSpacing(6)

        # Almacenamiento optimizado de imagen reducida para agilizar el recoloreado
        raw = QPixmap(filepath)
        self._base = self._scaled(raw, 40, 2) if not raw.isNull() else QPixmap()
        self._icon = QLabel()
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setFixedSize(60, 52)
        lay.addWidget(self._icon, 0, Qt.AlignHCenter)

        name = os.path.splitext(filename)[0]
        fm = QFontMetrics(self.font())
        lbl = QLabel(fm.elidedText(name, Qt.ElideRight, 76))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f'color: {C["muted"]}; font-size: 11px;')
        lay.addWidget(lbl)
        self.set_color(color, force=True)

        # Boton de cierre para eliminar el elemento seleccionado
        self.btn_delete = QToolButton(self)
        self.btn_delete.setText('×')
        self.btn_delete.setToolTip('Eliminar mira')
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setFocusPolicy(Qt.NoFocus)
        self.btn_delete.setFixedSize(16, 16)
        self._selected = selected
        self._update_delete_style()
        self.btn_delete.move(self.width() - 19, 3)
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.filename))

    def _update_delete_style(self):
        weight = '900' if self._selected else '600'
        color = C['strong'] if self._selected else C['muted']
        self.btn_delete.setStyleSheet(f'''
            QToolButton {{
                background: transparent; border: none;
                color: {color}; font-size: 14px; font-weight: {weight}; padding: 0 0 2px 0;
            }}
            QToolButton:hover, QToolButton:pressed {{
                background: transparent; border: none;
                color: {C['strong']}; font-size: 14px; font-weight: 900;
            }}
        ''')

    # Visualizacion de la miniatura aplicando el tono configurado
    def set_color(self, color, force=False):
        color = color or 'original'
        if color == self._color and not force:
            return
        self._color = color
        pix = self._base
        if not pix.isNull() and color.lower() not in ('none', 'original', ''):
            pix = colorize_pixmap(pix, color)
        self._icon.setPixmap(pix)
        # Adaptacion automatica del color de fondo para mantener contraste
        bg = '#D5DDE8' if image_is_dark(pix) else '#0A0F1A'
        self._icon.setStyleSheet(f'background: {bg}; border-radius: 8px;')

    @staticmethod
    def _scaled(pix, size, dpr):
        out = pix.scaled(size * dpr, size * dpr, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        out.setDevicePixelRatio(dpr)
        return out

    def set_selected(self, selected):
        self._selected = selected
        self.setProperty('selected', selected)
        self._update_delete_style()
        repolish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.filename)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        act = menu.addAction('Eliminar esta mira')
        if menu.exec_(event.globalPos()) == act:
            self.delete_requested.emit(self.filename)


# Vista previa grande de la mira seleccionada sobre un fondo de cuadricula
class PreviewBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(190)
        self._pix = QPixmap()
        self._raw_path = ''
        self._light = False
        self._opacity = 1.0
        self._color = 'original'

    def set_image(self, path):
        self._raw_path = path
        self._reload_pixmap()

    def set_color(self, color):
        self._color = color or 'original'
        self._reload_pixmap()

    def set_opacity(self, value):
        self._opacity = value
        self.update()

    def _reload_pixmap(self):
        if self._raw_path:
            raw = QPixmap(self._raw_path)
            if not raw.isNull():
                if self._color and self._color.lower() not in ('none', 'original', ''):
                    raw = colorize_pixmap(raw, self._color)
                self._pix = raw
                self._light = image_is_dark(self._pix)
            else:
                self._pix = QPixmap()
                self._light = False
        else:
            self._pix = QPixmap()
            self._light = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        p.setClipPath(path)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor('#DCE4EF' if self._light else '#101A2D'))
        grad.setColorAt(1, QColor('#BFCADB' if self._light else '#0A101C'))
        p.fillRect(self.rect(), grad)
        p.setPen(QPen(QColor(0, 0, 0, 16) if self._light else QColor(255, 255, 255, 10), 1))
        step = 20
        for x in range(0, self.width(), step):
            p.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            p.drawLine(0, y, self.width(), y)
        p.setPen(QPen(QColor(2, 132, 199, 90) if self._light else QColor(56, 189, 248, 45), 1, Qt.DashLine))
        p.drawLine(self.width() // 2, 0, self.width() // 2, self.height())
        p.drawLine(0, self.height() // 2, self.width(), self.height() // 2)

        if not self._pix.isNull():
            side = int(min(self.width(), self.height()) * 0.55)
            sz = self._pix.size().scaled(side, side, Qt.KeepAspectRatio)
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.setOpacity(self._opacity)
            p.drawPixmap(QRect((self.width() - sz.width()) // 2, (self.height() - sz.height()) // 2,
                               sz.width(), sz.height()), self._pix)
        p.setClipping(False)
        p.setOpacity(1.0)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(C['border']), 1))
        p.drawRoundedRect(r, 12, 12)
        p.end()


# Esquema de un monitor que muestra donde queda la mira
class MonitorMap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 170)
        self._sw, self._sh = 1920, 1080
        self._ox = self._oy = 0
        self._size = 48

    def set_state(self, screen_w, screen_h, offset_x, offset_y, size):
        self._sw, self._sh = max(1, screen_w), max(1, screen_h)
        self._ox, self._oy, self._size = offset_x, offset_y, size
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        avail = QRectF(self.rect()).adjusted(8, 8, -8, -30)
        scale = min(avail.width() / self._sw, avail.height() / self._sh)
        rw, rh = self._sw * scale, self._sh * scale
        rect = QRectF(avail.center().x() - rw / 2, avail.top() + (avail.height() - rh) / 2, rw, rh)

        p.setPen(QPen(QColor('#334155'), 2))
        p.setBrush(QColor('#0A101C'))
        p.drawRoundedRect(rect.adjusted(-5, -5, 5, 5), 8, 8)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor('#15233D'))
        grad.setColorAt(1, QColor('#0B1220'))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(rect, 3, 3)

        c = rect.center()
        p.setPen(QPen(QColor(255, 255, 255, 28), 1, Qt.DashLine))
        p.drawLine(QPointF(c.x(), rect.top()), QPointF(c.x(), rect.bottom()))
        p.drawLine(QPointF(rect.left(), c.y()), QPointF(rect.right(), c.y()))

        cx = c.x() + self._ox * scale
        cy = c.y() + self._oy * scale
        cx = max(rect.left(), min(rect.right(), cx))
        cy = max(rect.top(), min(rect.bottom(), cy))
        radius = max(4.0, self._size * scale / 2)
        pen = QPen(QColor(C['accent']), 1.6)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), radius, radius)
        p.drawLine(QPointF(cx - radius - 3, cy), QPointF(cx + radius + 3, cy))
        p.drawLine(QPointF(cx, cy - radius - 3), QPointF(cx, cy + radius + 3))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C['strong']))
        p.drawEllipse(QPointF(cx, cy), 1.8, 1.8)

        p.setPen(QColor(C['muted']))
        f = self.font()
        f.setPixelSize(11)
        p.setFont(f)
        p.drawText(QRectF(0, self.height() - 22, self.width(), 18), Qt.AlignCenter,
                   f'{self._sw} × {self._sh} px')
        p.end()


# Formato legible para representar combinaciones de atajos
def pretty_hotkey(hotkey):
    hotkey = (hotkey or '').replace('_', ' ')
    if hotkey.startswith(GAMEPAD_PREFIX + 'SDL:'):
        parsed = parse_sdl_gamepad_hotkey(hotkey[len(GAMEPAD_PREFIX):])
        if parsed:
            guid, controls = parsed
            buttons = ' + '.join(describe_control(control) for control in controls)
            return f'Mando {guid[:8]} · {buttons}'
    if hotkey.startswith(GAMEPAD_PREFIX):
        return 'Mando · ' + hotkey[len(GAMEPAD_PREFIX):]
    return hotkey


# Boton interactivo para registrar atajos de teclado raton y mandos
class HotkeyRecorderButton(QPushButton):
    hotkey_changed = pyqtSignal(str)
    _gamepad_signal = pyqtSignal(str)

    def __init__(self, current_hotkey='F2', parent=None, allow_empty=False):
        super().__init__(parent)
        self.recording = False
        self.allow_empty = allow_empty
        self.current_hotkey = current_hotkey or ('' if allow_empty else 'F2')
        self._pending_key_parts = []
        self._key_chord_timer = QTimer(self)
        self._key_chord_timer.setSingleShot(True)
        self._key_chord_timer.setInterval(250)
        self._key_chord_timer.timeout.connect(self._commit_pending_key)
        self._gamepad_thread = None
        self._gamepad_stop = threading.Event()
        self._gamepad_signal.connect(self._on_gamepad_button, Qt.QueuedConnection)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.clicked.connect(self.toggle_recording)
        self.update_display()

    # Formato visual del boton segun el estado
    def update_display(self):
        if self.recording:
            self.setText('Presiona una tecla o combinación de teclas o botones del mando')
            self.setStyleSheet(f'''
                QPushButton {{
                    background-color: {C['input']};
                    border: 2px solid {C['accent']};
                    border-radius: 6px;
                    color: {C['accent']};
                    font-weight: bold;
                    padding: 8px 18px;
                    font-size: 13px;
                }}
            ''')
        else:
            if self.current_hotkey:
                self.setText(pretty_hotkey(self.current_hotkey))
            else:
                self.setText('Sin asignar')
            self.setStyleSheet(f'''
                QPushButton {{
                    background-color: {C['card']};
                    border: 1px solid {C['border']};
                    border-radius: 6px;
                    color: {C['strong']};
                    font-weight: bold;
                    padding: 8px 18px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    border-color: {C['accent']};
                    background-color: {C['card_hi']};
                }}
            ''')

    def set_hotkey(self, text):
        self._key_chord_timer.stop()
        self._pending_key_parts = []
        self.current_hotkey = text or ('' if self.allow_empty else 'F2')
        self.recording = False
        self._stop_gamepad_scan()
        self.update_display()

    def toggle_recording(self):
        if self.recording:
            if self._pending_key_parts:
                self._commit_pending_key()
            else:
                self.stop_recording()
            return
        self.recording = True
        self.update_display()
        self.setFocus()
        self._start_gamepad_scan()

    def stop_recording(self):
        if self.recording:
            if self._pending_key_parts:
                self._commit_pending_key()
            else:
                self._finish_recording(None)

    def _finish_recording(self, hotkey):
        self._key_chord_timer.stop()
        self._pending_key_parts = []
        self.recording = False
        self._stop_gamepad_scan()
        if hotkey:
            self.current_hotkey = hotkey
            self.update_display()
            self.hotkey_changed.emit(hotkey)
        else:
            self.update_display()

    def _commit_pending_key(self):
        if not self.recording or not self._pending_key_parts:
            return
        self._finish_recording('+'.join(self._pending_key_parts))

    def _start_gamepad_scan(self):
        initialize_gamepad_input()
        self._gamepad_stop.clear()

        def _scan():
            from ctypes import wintypes
            class _GP(ctypes.Structure):
                _fields_ = [
                    ('wButtons', wintypes.WORD),
                    ('bLeftTrigger', wintypes.BYTE),
                    ('bRightTrigger', wintypes.BYTE),
                    ('sThumbLX', wintypes.SHORT),
                    ('sThumbLY', wintypes.SHORT),
                    ('sThumbRX', wintypes.SHORT),
                    ('sThumbRY', wintypes.SHORT),
                ]

            class _ST(ctypes.Structure):
                _fields_ = [('dwPacketNumber', wintypes.DWORD), ('Gamepad', _GP)]

            st = _ST()
            previous_sdl = set()
            candidates = {}
            prev = [0] * 4
            candidate_masks = [0] * 4
            candidate_started = [None] * 4
            user32 = getattr(ctypes.windll, 'user32', None)
            mouse_vks = ((0x02, 'Mouse Derecho'), (0x04, 'Mouse Central'),
                         (0x05, 'Mouse Boton 4'), (0x06, 'Mouse Boton 5'))
            lt_was = [0] * 4
            rt_was = [0] * 4

            def _emit_pad_hotkey(mask):
                names = [name for button_mask, name in GAMEPAD_BUTTON_NAMES.items()
                         if mask & button_mask]
                if names:
                    self._gamepad_signal.emit(GAMEPAD_PREFIX + '+'.join(names))
                    return True
                return False

            while not self._gamepad_stop.is_set():
                current_sdl = get_pressed_buttons()
                newly_pressed = current_sdl - previous_sdl
                previous_sdl = current_sdl
                now = time.monotonic()
                for device, (controls, _) in list(candidates.items()):
                    guid = device[0]
                    held = {control for device_guid, device_id, control in current_sdl
                            if (device_guid, device_id) == device}
                    if not controls.issubset(held):
                        self._gamepad_signal.emit(format_sdl_gamepad_hotkey(guid, controls))
                        return
                for guid, instance_id, control in newly_pressed:
                    device = (guid, instance_id)
                    candidate = candidates.get(device)
                    if candidate and now - candidate[1] <= 0.25:
                        candidate[0].add(control)
                    else:
                        candidates[device] = ({control}, now)
                for (guid, _), (controls, started) in list(candidates.items()):
                    if len(controls) >= 2 or now - started >= 0.25:
                        self._gamepad_signal.emit(format_sdl_gamepad_hotkey(guid, controls))
                        return

                if _xinput:
                    for i in range(4):
                        connected = _xinput.XInputGetState(i, ctypes.byref(st)) == 0
                        btns = st.Gamepad.wButtons if connected else 0
                        newly = btns & ~prev[i]
                        prev[i] = btns

                        candidate = candidate_masks[i]
                        started = candidate_started[i]
                        if candidate and (btns & candidate) != candidate:
                            candidate = 0
                            started = None
                        if newly:
                            if candidate and started is not None and time.monotonic() - started <= 0.25:
                                candidate |= newly
                            else:
                                candidate = newly
                                started = time.monotonic()
                        if candidate and (candidate & (candidate - 1)):
                            if _emit_pad_hotkey(candidate):
                                return
                        if candidate and started is not None and time.monotonic() - started >= 0.25:
                            if _emit_pad_hotkey(candidate):
                                return
                            candidate = 0
                            started = None
                        candidate_masks[i] = candidate
                        candidate_started[i] = started

                        if connected:
                            lt = st.Gamepad.bLeftTrigger
                            rt = st.Gamepad.bRightTrigger
                            if lt > 30 and lt_was[i] <= 30:
                                self._gamepad_signal.emit(GAMEPAD_PREFIX + 'Gatillo Izq')
                                return
                            if rt > 30 and rt_was[i] <= 30:
                                self._gamepad_signal.emit(GAMEPAD_PREFIX + 'Gatillo Der')
                                return
                            lt_was[i], rt_was[i] = lt, rt
                if user32:
                    for vk, mname in mouse_vks:
                        if user32.GetAsyncKeyState(vk) & 0x8000:
                            self._gamepad_signal.emit(mname)
                            return
                time.sleep(0.04)

        self._gamepad_thread = threading.Thread(target=_scan, daemon=True)
        self._gamepad_thread.start()

    def _stop_gamepad_scan(self):
        self._gamepad_stop.set()

    def _on_gamepad_button(self, hotkey):
        if not self.recording:
            return
        self._finish_recording(hotkey)

    def focusOutEvent(self, event):
        self.stop_recording()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if not self.recording:
            super().keyPressEvent(event)
            return

        if event.isAutoRepeat():
            event.accept()
            return

        key = event.key()
        if key == Qt.Key_Escape:
            self._key_chord_timer.stop()
            self._pending_key_parts = []
            self.stop_recording()
            event.accept()
            return

        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            event.accept()
            return

        mods = event.modifiers()
        parts = []
        if mods & Qt.ControlModifier:
            parts.append('Ctrl')
        if mods & Qt.AltModifier:
            parts.append('Alt')
        if mods & Qt.ShiftModifier:
            parts.append('Shift')
        if mods & Qt.MetaModifier:
            parts.append('Win')

        named_keys = {
            Qt.Key_F1: 'F1', Qt.Key_F2: 'F2', Qt.Key_F3: 'F3', Qt.Key_F4: 'F4',
            Qt.Key_F5: 'F5', Qt.Key_F6: 'F6', Qt.Key_F7: 'F7', Qt.Key_F8: 'F8',
            Qt.Key_F9: 'F9', Qt.Key_F10: 'F10', Qt.Key_F11: 'F11', Qt.Key_F12: 'F12',
            Qt.Key_Insert: 'Insert', Qt.Key_Delete: 'Delete',
            Qt.Key_Home: 'Home', Qt.Key_End: 'End',
            Qt.Key_PageUp: 'Page Up', Qt.Key_PageDown: 'Page Down',
            Qt.Key_Space: 'Space', Qt.Key_Tab: 'Tab', Qt.Key_CapsLock: 'CapsLock',
            Qt.Key_Print: 'PrintScreen', Qt.Key_ScrollLock: 'ScrollLock',
            Qt.Key_Pause: 'Pause', Qt.Key_NumLock: 'NumLock',
            Qt.Key_Up: 'Up', Qt.Key_Down: 'Down', Qt.Key_Left: 'Left', Qt.Key_Right: 'Right'
        }

        if key in named_keys:
            key_name = named_keys[key]
        elif 0x20 <= key <= 0x7e:
            key_name = chr(key).upper()
        else:
            key_name = QKeySequence(key).toString()

        if key_name and key_name not in ('Ctrl', 'Alt', 'Shift', 'Meta', 'Win'):
            chord_parts = parts + [key_name]
            if self._pending_key_parts:
                for part in chord_parts:
                    if part not in self._pending_key_parts:
                        self._pending_key_parts.append(part)
                self._commit_pending_key()
            else:
                self._pending_key_parts = chord_parts
                self._key_chord_timer.start()

        event.accept()


VISUAL_KEYS = ('crosshair_file', 'size', 'offset_x', 'offset_y', 'opacity', 'color')


# Generacion de descripcion textual con los parametros de la mira
def describe_values(v):
    name = os.path.splitext(v.get('crosshair_file', ''))[0] or tr('lbl_no_crosshair')
    col = v.get('color', 'original')
    dot = (f'<span style="color:{col};">●</span>' if col != 'original'
           else f'<span style="color:{C["muted"]};">◐</span>')
    return (f'{name}  ·  {v.get("size", 48)} px  ·  {int(round(v.get("opacity", 1.0) * 100))}%  ·  '
            f'X {v.get("offset_x", 0):+d}  Y {v.get("offset_y", 0):+d}  ·  {dot}')


# Compara los ajustes visuales de dos configuraciones
def same_visuals(a, b):
    return (a.get('crosshair_file') == b.get('crosshair_file')
            and a.get('size') == b.get('size')
            and a.get('offset_x') == b.get('offset_x')
            and a.get('offset_y') == b.get('offset_y')
            and round(float(a.get('opacity', 1)), 2) == round(float(b.get('opacity', 1)), 2)
            and str(a.get('color', 'original')).upper() == str(b.get('color', 'original')).upper())


# Miniatura cuadrada de una mira con su color y opacidad
class CrosshairThumb(QWidget):
    def __init__(self, side=64, parent=None):
        super().__init__(parent)
        self.setFixedSize(side, side)
        self._pix = QPixmap()
        self._light = False
        self._opacity = 1.0

    def set_values(self, values):
        path = resolve_crosshair_path(values.get('crosshair_file', ''))
        raw = QPixmap(path) if path else QPixmap()
        color = values.get('color', 'original')
        if not raw.isNull() and color and color.lower() != 'original':
            raw = colorize_pixmap(raw, color)
        self._pix = raw
        self._light = image_is_dark(raw)
        self._opacity = max(0.35, float(values.get('opacity', 1.0)))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 10, 10)
        p.setClipPath(path)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor('#DCE4EF' if self._light else '#101A2D'))
        grad.setColorAt(1, QColor('#BFCADB' if self._light else '#0A101C'))
        p.fillRect(self.rect(), grad)
        if not self._pix.isNull():
            side = int(min(self.width(), self.height()) * 0.62)
            sz = self._pix.size().scaled(side, side, Qt.KeepAspectRatio)
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.setOpacity(self._opacity)
            p.drawPixmap(QRect((self.width() - sz.width()) // 2, (self.height() - sz.height()) // 2,
                               sz.width(), sz.height()), self._pix)
        p.setClipping(False)
        p.setOpacity(1.0)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(C['border']), 1))
        p.drawRoundedRect(r, 10, 10)
        p.end()


# Tarjeta interactiva para previsualizar y seleccionar un tema visual
class ThemeCard(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, key, selected=False, parent=None):
        super().__init__(parent)
        self.key = key
        self.selected = selected
        self._hover = False
        self.setFixedHeight(142)
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tr('theme_tooltip').format(theme=tr(f'theme_{key}').lower()))

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit(self.key)

    def paintEvent(self, event):
        t = THEMES[self.key]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        outer = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        border = QColor(C['accent']) if self.selected else QColor(C['border_hi'] if self._hover else C['border'])
        p.setPen(QPen(border, 2 if self.selected else 1))
        p.setBrush(QColor(C['input']))
        p.drawRoundedRect(outer, 12, 12)

        # Maqueta de ventana
        win = QRectF(outer.left() + 12, outer.top() + 12, outer.width() - 24, outer.height() - 54)
        clip = QPainterPath()
        clip.addRoundedRect(win, 8, 8)
        p.save()
        p.setClipPath(clip)
        p.fillRect(win, QColor(t['bg']))
        side_w = win.width() * 0.27
        p.fillRect(QRectF(win.left(), win.top(), side_w, win.height()), QColor(t['side']))
        p.setPen(Qt.NoPen)
        for i in range(4):
            y = win.top() + 12 + i * 11
            p.setBrush(QColor(t['accent']) if i == 0 else QColor(t['muted']))
            p.setOpacity(1.0 if i == 0 else 0.55)
            p.drawRoundedRect(QRectF(win.left() + 8, y, side_w - 16, 4.5), 2.2, 2.2)
        p.setOpacity(1.0)
        cx = win.left() + side_w + 10
        cw = win.right() - cx - 10
        p.setBrush(QColor(t['strong']))
        p.setOpacity(0.85)
        p.drawRoundedRect(QRectF(cx, win.top() + 9, cw * 0.45, 6), 3, 3)
        p.setOpacity(1.0)
        for i in range(2):
            card = QRectF(cx, win.top() + 22 + i * 24, cw, 19)
            p.setBrush(QColor(t['card']))
            p.setPen(QPen(QColor(t['border']), 1))
            p.drawRoundedRect(card, 4, 4)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(t['muted']))
            p.setOpacity(0.6)
            p.drawRoundedRect(QRectF(card.left() + 6, card.top() + 7.5, cw * 0.38, 4), 2, 2)
            p.setOpacity(1.0)
            p.setBrush(QColor(t['accent_dark']))
            p.drawRoundedRect(QRectF(card.right() - 24, card.top() + 5, 18, 9), 4.5, 4.5)
        p.restore()
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(t['border_hi']), 1))
        p.drawRoundedRect(win, 8, 8)

        # Etiqueta y marca de seleccion
        f = self.font()
        f.setPixelSize(13)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(C['strong']))
        p.drawText(QRectF(outer.left() + 14, outer.bottom() - 34, outer.width() - 60, 26),
                   Qt.AlignVCenter | Qt.AlignLeft, tr(f'theme_{self.key}'))
        rc = QPointF(outer.right() - 22, outer.bottom() - 21)
        p.setBrush(QColor(C['accent']) if self.selected else Qt.NoBrush)
        p.setPen(QPen(QColor(C['accent'] if self.selected else C['border_hi']), 1.6))
        p.drawEllipse(rc, 8, 8)
        if self.selected:
            pen = QPen(QColor('#FFFFFF'), 1.8)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.drawPolyline(QPointF(rc.x() - 3.6, rc.y() + 0.2), QPointF(rc.x() - 1, rc.y() + 2.8),
                           QPointF(rc.x() + 3.6, rc.y() - 2.6))
        p.end()


# Tarjeta representativa de un perfil con sus datos y acciones
class PresetCard(QFrame):
    apply_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    update_requested = pyqtSignal(str)
    duplicate_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    auto_toggled = pyqtSignal(str, bool)
    states_requested = pyqtSignal(str)
    move_group_requested = pyqtSignal(str, str)

    def __init__(self, preset, groups=None, parent=None):
        super().__init__(parent)
        self.preset_id = preset['id']
        self._groups = list(groups or [])
        self._group = preset.get('group', 'General')
        self.setObjectName('PresetCard')
        self.setProperty('inuse', False)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 12, 12)
        lay.setSpacing(14)

        self.thumb = CrosshairThumb(66)
        self.thumb.set_values(preset)
        lay.addWidget(self.thumb, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(4)
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        self.lbl_name = QLabel(preset['name'])
        self.lbl_name.setObjectName('PresetName')
        name_row.addWidget(self.lbl_name)
        self.badge = QLabel(tr('lbl_applied'))
        self.badge.setObjectName('Badge')
        self.badge.setVisible(False)
        name_row.addWidget(self.badge)
        name_row.addStretch()
        col.addLayout(name_row)
        lbl_sum = QLabel(describe_values(preset))
        lbl_sum.setTextFormat(Qt.RichText)
        lbl_sum.setObjectName('Muted')
        col.addWidget(lbl_sum)
        if preset['auto_apply'] and preset['app']:
            meta = QLabel(tr('preset_auto_applies').format(app=preset['app']))
            meta.setObjectName('MetaOn')
        else:
            meta = QLabel(tr('preset_no_automation'))
            meta.setObjectName('MutedSmall')
        col.addWidget(meta)
        lay.addLayout(col, 1)

        auto_col = QVBoxLayout()
        auto_col.setSpacing(3)
        self.switch = ToggleSwitch(bool(preset['auto_apply']))
        self.switch.setToolTip(tr('preset_auto_tooltip'))
        self.switch.toggled.connect(lambda on: self.auto_toggled.emit(self.preset_id, on))
        auto_col.addWidget(self.switch, 0, Qt.AlignHCenter)
        cap = QLabel(tr('lbl_automatic'))
        cap.setObjectName('MutedSmall')
        cap.setAlignment(Qt.AlignCenter)
        auto_col.addWidget(cap)
        lay.addLayout(auto_col)

        self.btn_apply = QPushButton(tr('btn_apply'))
        self.btn_apply.setObjectName('Primary')
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.setFixedWidth(92)
        self.btn_apply.clicked.connect(lambda: self.apply_requested.emit(self.preset_id))
        lay.addWidget(self.btn_apply)

        more = QToolButton()
        more.setObjectName('IconBtn')
        more.setIcon(make_dots_icon())
        more.setIconSize(QSize(20, 20))
        more.setCursor(Qt.PointingHandCursor)
        more.setPopupMode(QToolButton.InstantPopup)
        more.setToolTip(tr('more_options'))
        menu = QMenu(more)
        menu.addAction(tr('preset_edit'), lambda: self.edit_requested.emit(self.preset_id))
        menu.addAction(tr('preset_states'), lambda: self.states_requested.emit(self.preset_id))
        menu.addAction(tr('preset_update_current'), lambda: self.update_requested.emit(self.preset_id))
        menu.addAction(tr('preset_duplicate'), lambda: self.duplicate_requested.emit(self.preset_id))

        other_groups = [g for g in self._groups if g != self._group]
        if other_groups:
            menu.addSeparator()
            move_menu = menu.addMenu(tr('group_move_to'))
            for g in other_groups:
                move_menu.addAction(g, lambda checked=False, target=g: self.move_group_requested.emit(self.preset_id, target))

        menu.addSeparator()
        menu.addAction(tr('preset_delete'), lambda: self.delete_requested.emit(self.preset_id))
        more.setMenu(menu)
        lay.addWidget(more)

    def set_in_use(self, in_use):
        if bool(self.property('inuse')) == in_use:
            return
        self.setProperty('inuse', in_use)
        self.badge.setVisible(in_use)
        self.btn_apply.setText(tr('lbl_applied') if in_use else tr('btn_apply'))
        self.btn_apply.setEnabled(not in_use)
        repolish(self)


# Dialogo para crear o editar un preset
class PresetDialog(QDialog):
    def __init__(self, parent, current_values, preset=None, existing=(), default_name='', enable_auto=False, groups=None, default_group='General'):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._editing = preset is not None
        self.setWindowTitle(tr('preset_edit_title') if self._editing else tr('preset_new_title'))
        self.setModal(True)
        self.setMinimumWidth(520)
        self._existing = list(existing)
        self._current = {k: current_values[k] for k in VISUAL_KEYS}
        source = preset if self._editing else current_values
        self._values = {k: source[k] for k in VISUAL_KEYS}
        self._id = preset['id'] if self._editing else new_preset_id()
        self._states = copy.deepcopy(preset.get('states', [])) if self._editing else []
        self.result_preset = None
        self._countdown = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_countdown)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 24, 26, 22)
        lay.setSpacing(16)

        title = QLabel(tr('preset_edit_title') if self._editing else tr('preset_save_title'))
        title.setObjectName('DialogTitle')
        lay.addWidget(title)
        sub = QLabel(tr('preset_save_description') if not self._editing
                     else tr('preset_edit_description'))
        sub.setObjectName('Muted')
        sub.setWordWrap(True)
        lay.addWidget(sub)

        # Ajustes que se guardaran
        snap = QFrame()
        snap.setObjectName('Tile')
        sl = QHBoxLayout(snap)
        sl.setContentsMargins(12, 12, 14, 12)
        sl.setSpacing(14)
        self.thumb = CrosshairThumb(60)
        sl.addWidget(self.thumb)
        st = QVBoxLayout()
        st.setSpacing(3)
        cap = QLabel(tr('preset_settings_heading').upper())
        cap.setObjectName('MetricLabel')
        st.addWidget(cap)
        self.lbl_summary = QLabel('')
        self.lbl_summary.setTextFormat(Qt.RichText)
        self.lbl_summary.setWordWrap(True)
        st.addWidget(self.lbl_summary)
        sl.addLayout(st, 1)
        if self._editing:
            btn_cur = QPushButton(tr('preset_use_current'))
            btn_cur.setCursor(Qt.PointingHandCursor)
            btn_cur.setToolTip(tr('preset_use_current_tooltip'))
            btn_cur.clicked.connect(self._use_current)
            sl.addWidget(btn_cur)
        lay.addWidget(snap)
        self._refresh_snapshot()

        # Nombre
        lay.addWidget(self._section(tr('preset_name_heading').upper()))
        self.edit_name = QLineEdit(preset['name'] if self._editing else default_name)
        self.edit_name.setMaxLength(PRESET_NAME_MAX)
        self.edit_name.setPlaceholderText(tr('preset_name_placeholder'))
        lay.addWidget(self.edit_name)

        # Grupo
        self._groups = list(groups or ['General'])
        curr_grp = preset.get('group', default_group) if self._editing else default_group
        if curr_grp not in self._groups:
            self._groups.append(curr_grp)
        lay.addWidget(self._section(tr('lbl_group').upper()))
        self.combo_group = QComboBox()
        self.combo_group.setEditable(True)
        self.combo_group.addItems(self._groups)
        self.combo_group.setCurrentText(curr_grp)
        lay.addWidget(self.combo_group)

        # Aplicacion automatica
        lay.addWidget(self._section(tr('preset_automation_heading').upper()))
        self.switch_auto = ToggleSwitch(enable_auto or (self._editing and bool(preset['auto_apply'])))
        self.switch_auto.toggled.connect(self._on_auto_toggled)
        lay.addWidget(SettingRow(tr('preset_auto_label'),
                                 tr('preset_auto_description'),
                                 self.switch_auto))

        self.app_box = QWidget()
        al = QVBoxLayout(self.app_box)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(8)
        self.combo_app = QComboBox()
        self.combo_app.setEditable(True)
        self.combo_app.addItems(get_running_processes())
        self.combo_app.lineEdit().setPlaceholderText(tr('preset_app_placeholder'))
        self.combo_app.setCurrentText(preset['app'] if self._editing else '')
        al.addWidget(self.combo_app)
        brow = QHBoxLayout()
        brow.setSpacing(8)
        self.btn_detect = QPushButton(tr('preset_detect_button'))
        self.btn_detect.setCursor(Qt.PointingHandCursor)
        self.btn_detect.clicked.connect(self._start_detect)
        brow.addWidget(self.btn_detect)
        btn_browse = QPushButton(tr('common_browse'))
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.clicked.connect(self._browse)
        brow.addWidget(btn_browse)
        brow.addStretch()
        al.addLayout(brow)
        self.lbl_detect = QLabel('')
        self.lbl_detect.setObjectName('Status')
        self.lbl_detect.setWordWrap(True)
        self.lbl_detect.setVisible(False)
        al.addWidget(self.lbl_detect)
        lay.addWidget(self.app_box)
        self._on_auto_toggled(self.switch_auto.isChecked())

        self.lbl_error = QLabel('')
        self.lbl_error.setObjectName('Error')
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setVisible(False)
        lay.addWidget(self.lbl_error)

        lay.addSpacing(4)
        buttons = QHBoxLayout()
        buttons.addStretch()
        btn_cancel = QPushButton(tr('common_cancel'))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton(tr('preset_save_changes') if self._editing
                               else tr('preset_save_button'))
        btn_save.setObjectName('Primary')
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(btn_save)
        lay.addLayout(buttons)

        self.edit_name.setFocus()
        self.edit_name.selectAll()

    @staticmethod
    def _section(text):
        lbl = QLabel(text)
        lbl.setObjectName('Section')
        return lbl

    def _refresh_snapshot(self):
        self.thumb.set_values(self._values)
        self.lbl_summary.setText(describe_values(self._values))

    def _use_current(self):
        self._values = dict(self._current)
        self._refresh_snapshot()

    def _on_auto_toggled(self, on):
        self.app_box.setEnabled(on)
        self.app_box.setStyleSheet('' if on else 'QWidget { color: %s; }' % C['off'])

    def _browse(self):
        start = os.path.expandvars('%LOCALAPPDATA%')
        if '%' in start:
            start = ''
        path, _ = QFileDialog.getOpenFileName(
            self, tr('preset_select_executable'), start, tr('preset_executable_filter'))
        if path:
            self.combo_app.setCurrentText(os.path.basename(path))

    # Cuenta atras para que cambies a la aplicacion y se lea cual es
    def _start_detect(self):
        self._countdown = 5
        self.btn_detect.setEnabled(False)
        self.lbl_detect.setText(
            tr('preset_detect_countdown').format(seconds=self._countdown))
        self.lbl_detect.setVisible(True)
        self._timer.start(1000)

    def _on_countdown(self):
        self._countdown -= 1
        if self._countdown > 0:
            self.lbl_detect.setText(
                tr('preset_detect_countdown').format(seconds=self._countdown))
            return
        self._timer.stop()
        self.btn_detect.setEnabled(True)
        pid, proc, title = get_foreground_details()
        if pid == os.getpid() or not (proc or title):
            self.lbl_detect.setText(tr('preset_detect_none'))
        else:
            self.combo_app.setCurrentText(proc or title)
            self.lbl_detect.setText(tr('preset_detected').format(app=proc or title))
        self.raise_()
        self.activateWindow()

    def _fail(self, text):
        self.lbl_error.setText(text)
        self.lbl_error.setVisible(True)

    def _on_save(self):
        name = self.edit_name.text().strip()
        if not name:
            return self._fail(tr('preset_error_name_required'))
        if any(p['name'].lower() == name.lower() for p in self._existing):
            return self._fail(tr('preset_error_name_exists').format(name=name))
        auto = self.switch_auto.isChecked()
        app = self.combo_app.currentText().strip()
        if auto and not app:
            return self._fail(tr('preset_error_app_required'))
        if auto:
            for p in self._existing:
                if p['auto_apply'] and p['app'].strip().lower() == app.lower():
                    return self._fail(
                        tr('preset_error_app_exists').format(name=p['name']))
        grp = self.combo_group.currentText().strip() or 'General'
        self.result_preset = {'id': self._id, 'name': name, 'group': grp, **self._values,
                              'app': app, 'auto_apply': auto and bool(app), 'states': self._states}
        self.accept()
