# Selector de colores predefinidos y personalizados para la mira
import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QFrame
)
from PyQt5.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QPropertyAnimation, QEasingCurve, QRegExp
)
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient, QConicalGradient, QPainterPath,
    QRegExpValidator
)

from styles import C, tr

# Lista de colores predefinidos disponibles en el selector
PRESET_COLORS = (
    ('color_original', 'original'),
    ('color_white', '#FFFFFF'),
    ('color_red', '#EF4444'),
    ('color_orange', '#F97316'),
    ('color_yellow', '#FACC15'),
    ('color_green', '#22C55E'),
    ('color_cyan', '#06B6D4'),
    ('color_blue', '#3B82F6'),
    ('color_violet', '#A855F7'),
    ('color_pink', '#EC4899'),
)
COLOR_NAME_KEYS = {v.upper(): key for key, v in PRESET_COLORS}
QWIDGETSIZE_MAX = 16777215


def _is_light(color):
    return (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) > 170


def _normalize(value):
    value = (value or 'original').strip()
    if value.lower() in ('original', 'none', ''):
        return 'original'
    c = QColor(value)
    return c.name().upper() if c.isValid() else 'original'


# Componente circular interactivo para seleccionar una muestra de color
class Swatch(QWidget):
    clicked = pyqtSignal()

    def __init__(self, kind, value, tooltip, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.value = value
        self.selected = False
        self.fill = None
        self._hover = False
        self.setFixedSize(34, 34)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)

    def set_selected(self, selected):
        if selected != self.selected:
            self.selected = selected
            self.update()

    def set_fill(self, color_hex):
        self.fill = color_hex
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        c = QPointF(self.width() / 2.0, self.height() / 2.0)
        r = 11.0 + (1.0 if self._hover and not self.selected else 0.0)

        if self.selected:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(C['accent']), 2))
            p.drawEllipse(c, 15.0, 15.0)
        elif self._hover:
            ring = QColor(C['border_hi'])
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(ring, 1.5))
            p.drawEllipse(c, 14.5, 14.5)

        face = QRectF(c.x() - r, c.y() - r, r * 2, r * 2)
        outline = QPen(QColor(128, 128, 128, 80), 1)

        if self.kind == 'original':
            path = QPainterPath()
            path.addEllipse(face)
            p.save()
            p.setClipPath(path)
            p.fillRect(face, QColor('#E5E7EB'))
            tri = QPainterPath()
            tri.moveTo(face.topRight())
            tri.lineTo(face.bottomRight())
            tri.lineTo(face.bottomLeft())
            tri.closeSubpath()
            p.fillPath(tri, QColor('#475569'))
            p.restore()
            p.setBrush(Qt.NoBrush)
            p.setPen(outline)
            p.drawEllipse(face)
            check_on = QColor('#FFFFFF')
        elif self.kind == 'custom':
            if self.fill:
                col = QColor(self.fill)
                p.setPen(outline)
                p.setBrush(col)
                p.drawEllipse(face)
                check_on = QColor('#111827') if _is_light(col) else QColor('#FFFFFF')
            else:
                grad = QConicalGradient(c, 90)
                for i in range(7):
                    grad.setColorAt(i / 6.0, QColor.fromHsvF((i % 6) / 6.0, 0.85, 1.0))
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(grad))
                p.drawEllipse(face)
                p.setBrush(QColor(C['card']))
                p.drawEllipse(c, 6.2, 6.2)
                pen = QPen(QColor(C['text']), 1.6)
                pen.setCapStyle(Qt.RoundCap)
                p.setPen(pen)
                p.drawLine(QPointF(c.x() - 3, c.y()), QPointF(c.x() + 3, c.y()))
                p.drawLine(QPointF(c.x(), c.y() - 3), QPointF(c.x(), c.y() + 3))
                check_on = None
        else:
            col = QColor(self.value)
            p.setPen(outline)
            p.setBrush(col)
            p.drawEllipse(face)
            check_on = QColor('#111827') if _is_light(col) else QColor('#FFFFFF')

        if self.selected and check_on is not None:
            pen = QPen(check_on, 2.0)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPolyline(QPointF(c.x() - 4.2, c.y() + 0.2), QPointF(c.x() - 1.2, c.y() + 3.2),
                           QPointF(c.x() + 4.4, c.y() - 3.2))
        p.end()


# Area bidimensional para ajustar saturacion y brillo del color
class SVPlane(QWidget):
    changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hue, self.sat, self.val = 0.0, 1.0, 1.0
        self.setFixedHeight(128)
        self.setCursor(Qt.CrossCursor)
        self.setMinimumWidth(120)

    def set_state(self, h, s, v):
        self.hue, self.sat, self.val = h, s, v
        self.update()

    def _pick(self, pos):
        w, h = max(1, self.width() - 1), max(1, self.height() - 1)
        s = min(1.0, max(0.0, pos.x() / w))
        v = min(1.0, max(0.0, 1.0 - pos.y() / h))
        self.sat, self.val = s, v
        self.update()
        self.changed.emit(s, v)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pick(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._pick(event.pos())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 9, 9)
        p.save()
        p.setClipPath(path)
        p.fillRect(rect, QColor.fromHsvF(self.hue, 1.0, 1.0))
        white = QLinearGradient(rect.left(), 0, rect.right(), 0)
        white.setColorAt(0, QColor(255, 255, 255, 255))
        white.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(rect, white)
        black = QLinearGradient(0, rect.top(), 0, rect.bottom())
        black.setColorAt(0, QColor(0, 0, 0, 0))
        black.setColorAt(1, QColor(0, 0, 0, 255))
        p.fillRect(rect, black)
        p.restore()
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(C['border_hi']), 1))
        p.drawRoundedRect(rect, 9, 9)

        x = rect.left() + self.sat * rect.width()
        y = rect.top() + (1.0 - self.val) * rect.height()
        p.setPen(QPen(QColor(0, 0, 0, 120), 3))
        p.drawEllipse(QPointF(x, y), 7, 7)
        p.setPen(QPen(QColor('#FFFFFF'), 2))
        p.setBrush(QColor.fromHsvF(self.hue, self.sat, self.val))
        p.drawEllipse(QPointF(x, y), 7, 7)
        p.end()


# Control deslizante para seleccionar el tono espectral
class HueSlider(QWidget):
    changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hue = 0.0
        self.setFixedHeight(22)
        self.setCursor(Qt.PointingHandCursor)

    def set_hue(self, h):
        self.hue = h
        self.update()

    def _pick(self, pos):
        span = max(1, self.width() - 16)
        self.hue = min(0.999, max(0.0, (pos.x() - 8) / span))
        self.update()
        self.changed.emit(self.hue)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pick(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._pick(event.pos())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        bar = QRectF(8, self.height() / 2.0 - 5, self.width() - 16, 10)
        grad = QLinearGradient(bar.left(), 0, bar.right(), 0)
        for i in range(13):
            grad.setColorAt(i / 12.0, QColor.fromHsvF(min(i / 12.0, 0.999), 1.0, 1.0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(bar, 5, 5)
        x = bar.left() + self.hue * bar.width()
        p.setPen(QPen(QColor(0, 0, 0, 110), 3))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(x, bar.center().y()), 8, 8)
        p.setPen(QPen(QColor('#FFFFFF'), 2))
        p.setBrush(QColor.fromHsvF(self.hue, 1.0, 1.0))
        p.drawEllipse(QPointF(x, bar.center().y()), 8, 8)
        p.end()


# Componente integral de seleccion de color con panel expandible
class ColorPicker(QWidget):
    colorChanged = pyqtSignal(str)

    COLUMNS = 6

    def __init__(self, color='original', parent=None):
        super().__init__(parent)
        self._color = _normalize(color)
        self._h, self._s, self._v = 0.0, 1.0, 1.0
        self._expanded = False
        self._building = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(2)
        grid.setVerticalSpacing(4)
        self.swatches = []
        for i, (name_key, value) in enumerate(PRESET_COLORS):
            kind = 'original' if value == 'original' else 'color'
            tip = tr('color_original_tip') if value == 'original' else tr(name_key)
            sw = Swatch(kind, value, tip)
            sw.clicked.connect(lambda v=value: self._choose_preset(v))
            self.swatches.append(sw)
            grid.addWidget(sw, i // self.COLUMNS, i % self.COLUMNS)
        n = len(PRESET_COLORS)
        self.custom_swatch = Swatch('custom', None, tr('color_custom'))
        self.custom_swatch.clicked.connect(self.toggle_panel)
        grid.addWidget(self.custom_swatch, n // self.COLUMNS, n % self.COLUMNS)
        grid.setColumnStretch(self.COLUMNS, 1)
        root.addLayout(grid)

        # Lectura del color actual
        self.readout = QFrame()
        self.readout.setObjectName('Tile')
        rl = QHBoxLayout(self.readout)
        rl.setContentsMargins(10, 8, 12, 8)
        rl.setSpacing(10)
        self.chip = QLabel()
        self.chip.setFixedSize(20, 20)
        rl.addWidget(self.chip)
        self.lbl_name = QLabel('')
        self.lbl_name.setStyleSheet('font-weight: 600;')
        rl.addWidget(self.lbl_name)
        rl.addStretch()
        self.lbl_hex = QLabel('')
        self.lbl_hex.setObjectName('Muted')
        rl.addWidget(self.lbl_hex)
        root.addWidget(self.readout)

        # Panel desplegable del editor
        self.panel = QWidget()
        pl = QVBoxLayout(self.panel)
        pl.setContentsMargins(0, 2, 0, 2)
        pl.setSpacing(10)
        self.plane = SVPlane()
        self.plane.changed.connect(self._on_plane)
        pl.addWidget(self.plane)
        self.hue_slider = HueSlider()
        self.hue_slider.changed.connect(self._on_hue)
        pl.addWidget(self.hue_slider)
        hex_row = QHBoxLayout()
        hex_row.setSpacing(8)
        cap = QLabel('HEX')
        cap.setObjectName('MetricLabel')
        hex_row.addWidget(cap)
        self.hex_input = QLineEdit()
        self.hex_input.setObjectName('HexInput')
        self.hex_input.setMaxLength(7)
        self.hex_input.setPlaceholderText('#RRGGBB')
        self.hex_input.setValidator(QRegExpValidator(QRegExp('^#?[0-9A-Fa-f]{0,6}$')))
        self.hex_input.textEdited.connect(self._on_hex_edited)
        self.hex_input.editingFinished.connect(self._sync_hex_text)
        hex_row.addWidget(self.hex_input, 1)
        pl.addLayout(hex_row)
        self.panel.setMaximumHeight(0)
        self.panel.setVisible(False)
        root.addWidget(self.panel)

        self._anim = QPropertyAnimation(self.panel, b'maximumHeight', self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_anim_finished)

        self.set_color(self._color)

    # Metodos publicos de consulta y modificacion
    def color(self):
        return self._color

    def set_color(self, color):
        self._color = _normalize(color)
        if self._color != 'original':
            qc = QColor(self._color)
            h, s, v, _ = qc.getHsvF()
            if h >= 0:
                self._h = h
            self._s, self._v = s, v
        self._refresh()

    # Controladores de eventos e interaccion del usuario
    def _emit(self):
        self.colorChanged.emit(self._color)

    def _choose_preset(self, value):
        self.set_color(value)
        self._emit()

    def toggle_panel(self):
        self._expanded = not self._expanded
        self._anim.stop()
        if self._expanded:
            if self._color == 'original':
                # Asignacion de tono inicial visible al abrir el editor por primera vez
                self._h, self._s, self._v = 0.55, 0.85, 1.0
                self._apply_hsv(emit=True)
            self.panel.setVisible(True)
            target = self.panel.layout().sizeHint().height() + 4
            self._anim.setStartValue(self.panel.maximumHeight())
            self._anim.setEndValue(target)
        else:
            self._anim.setStartValue(self.panel.height())
            self._anim.setEndValue(0)
        self._anim.start()
        self.custom_swatch.update()

    def _on_anim_finished(self):
        if self._expanded:
            self.panel.setMaximumHeight(QWIDGETSIZE_MAX)
        else:
            self.panel.setVisible(False)

    def _on_plane(self, s, v):
        self._s, self._v = s, v
        self._apply_hsv(emit=True)

    def _on_hue(self, h):
        self._h = h
        self._apply_hsv(emit=True)

    def _apply_hsv(self, emit):
        self._color = QColor.fromHsvF(self._h, self._s, self._v).name().upper()
        self._refresh()
        if emit:
            self._emit()

    def _on_hex_edited(self, text):
        text = text.strip()
        if not text.startswith('#'):
            text = '#' + text
        if re.fullmatch(r'#[0-9A-Fa-f]{6}', text):
            self.set_color(text)
            self._emit()

    def _sync_hex_text(self):
        self.hex_input.setText('' if self._color == 'original' else self._color)

    # Actualizacion visual de componentes e indicadores graficos
    def _refresh(self):
        col = self._color
        is_preset = False
        for sw in self.swatches:
            on = sw.value.upper() == col.upper() if col != 'original' else sw.value == 'original'
            sw.set_selected(on)
            is_preset = is_preset or on
        custom_on = col != 'original' and not is_preset
        self.custom_swatch.set_fill(col if custom_on else None)
        self.custom_swatch.set_selected(custom_on)

        if col == 'original':
            self.chip.setStyleSheet(f'border-radius: 10px; border: 1px solid {C["border_hi"]};'
                                    f'background: qlineargradient(x1:0,y1:0,x2:1,y2:1,'
                                    f'stop:0 #E5E7EB, stop:0.5 #E5E7EB, stop:0.51 #475569, stop:1 #475569);')
            self.lbl_name.setText(tr('color_original'))
            self.lbl_hex.setText(tr('color_no_tint'))
        else:
            self.chip.setStyleSheet(f'border-radius: 10px; border: 1px solid {C["border_hi"]}; background: {col};')
            self.lbl_name.setText(tr(COLOR_NAME_KEYS.get(col.upper(), 'color_custom')))
            self.lbl_hex.setText(col)

        self.plane.set_state(self._h, self._s, self._v)
        self.hue_slider.set_hue(self._h)
        if not self.hex_input.hasFocus():
            self._sync_hex_text()
