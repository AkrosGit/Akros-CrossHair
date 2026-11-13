# Editor interactivo a pantalla completa para calibrar la mira visualmente
from PyQt5.QtWidgets import (
    QDialog, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QSlider,
    QSpinBox, QPushButton, QComboBox, QShortcut, QApplication
)
from PyQt5.QtCore import Qt, QRectF, QPoint, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QKeySequence, QFontMetrics, QPixmap

from overlay import load_crosshair_pixmap, crosshair_origin, MIN_SIZE, MAX_SIZE
from widgets import ToggleSwitch, image_is_dark
from styles import C, tr

# Distancia minima en pixeles para acoplar la mira al centro
SNAP_DISTANCE = 4


# Barra superior utilizada para arrastrar el panel flotante
class _PanelGrip(QLabel):
    def __init__(self, panel, parent=None):
        super().__init__(tr('editor_title'), parent)
        self._panel = panel
        self.setObjectName('EditorTitle')
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip(tr('editor_drag_tooltip'))
        self._start_global = QPoint()
        self._start_pos = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_global = event.globalPos()
            self._start_pos = self._panel.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            target = self._start_pos + (event.globalPos() - self._start_global)
            parent = self._panel.parentWidget()
            x = max(0, min(parent.width() - self._panel.width(), target.x()))
            y = max(0, min(parent.height() - self._panel.height(), target.y()))
            self._panel.move(x, y)
            parent.panel_moved_by_user = True


# Editor a pantalla completa sobre captura de pantalla
class CrosshairEditor(QDialog):
    saved = pyqtSignal(dict)
    closed = pyqtSignal()

    BG_CHOICES = (
        ('editor_bg_screenshot', 'screenshot'),
        ('editor_bg_plain', 'plain'),
        ('editor_bg_grid', 'grid'),
    )

    def __init__(self, parent=None, screen=None, image_path='', values=None, background=None, bg_mode='screenshot', guides=True):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Akro's CrossHair")
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.result_values = None

        if screen is None:
            screen = QApplication.primaryScreen()
        self._screen = screen
        geo = screen.geometry()
        self._sw, self._sh = geo.width(), geo.height()
        self._shot = background if (background is not None and not background.isNull()) else None
        self._dpr = screen.devicePixelRatio()
        self._image_path = image_path

        if values is None:
            values = {'size': 32, 'offset_x': 0, 'offset_y': 0, 'opacity': 1.0, 'color': 'original'}
        self.size_val = max(MIN_SIZE, min(MAX_SIZE, int(values.get('size', 32))))
        self.ox = int(values.get('offset_x', 0))
        self.oy = int(values.get('offset_y', 0))
        self.opacity = float(values.get('opacity', 1.0))
        self.color = values.get('color', 'original')
        self.bg_mode = bg_mode if (bg_mode != 'screenshot' or self._shot) else 'plain'
        # Una mira oscura se ve sobre fondo claro y una clara sobre fondo oscuro
        self._light_bg = image_is_dark(QPixmap(image_path)) if image_path else False
        self.show_guides = guides

        self._pix = None
        self._dragging = False
        self._done = False
        self.panel_moved_by_user = False

        self._build_panel()
        self._rebuild_pixmap()
        self._sync_ranges()
        self._sync_widgets()

        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.cancel)
        QShortcut(QKeySequence('Ctrl+S'), self, activated=self.save)

    # Construccion de los controles del panel flotante
    def _build_panel(self):
        self.panel = QFrame(self)
        self.panel.setObjectName('EditorPanel')
        self.panel.setCursor(Qt.ArrowCursor)
        self.panel.setFixedWidth(max(560, min(760, self._sw - 40)))
        root = QVBoxLayout(self.panel)
        root.setContentsMargins(20, 14, 20, 16)
        root.setSpacing(12)

        head = QHBoxLayout()
        head.addWidget(_PanelGrip(self.panel, self.panel))
        head.addSpacing(10)
        head.addStretch()
        self.lbl_live = QLabel('')
        self.lbl_live.setObjectName('Muted')
        head.addWidget(self.lbl_live)
        root.addLayout(head)

        grid = QGridLayout()
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(10)

        # Tamano
        grid.addWidget(self._caption(tr('editor_size')), 0, 0)
        self.sld_size = QSlider(Qt.Horizontal)
        self.sld_size.setRange(MIN_SIZE, 300)
        self.sld_size.valueChanged.connect(self._on_size_ui)
        self.sld_size.sliderReleased.connect(self.setFocus)
        grid.addWidget(self.sld_size, 1, 0)
        self.spin_size = QSpinBox()
        self.spin_size.setRange(MIN_SIZE, MAX_SIZE)
        self.spin_size.setSuffix(' px')
        self.spin_size.valueChanged.connect(self._on_size_ui)
        grid.addWidget(self.spin_size, 1, 1)

        # Opacidad
        grid.addWidget(self._caption(tr('editor_opacity')), 0, 2)
        self.sld_opac = QSlider(Qt.Horizontal)
        self.sld_opac.setRange(10, 100)
        self.sld_opac.valueChanged.connect(self._on_opacity_ui)
        self.sld_opac.sliderReleased.connect(self.setFocus)
        grid.addWidget(self.sld_opac, 1, 2)
        self.lbl_opac = QLabel('')
        self.lbl_opac.setMinimumWidth(44)
        self.lbl_opac.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.lbl_opac, 1, 3)

        # Posicion
        pos = QHBoxLayout()
        pos.setSpacing(8)
        pos.addWidget(self._caption(tr('editor_position')))
        pos.addSpacing(4)
        pos.addWidget(QLabel('X'))
        self.spin_x = QSpinBox()
        self.spin_x.valueChanged.connect(self._on_offset_ui)
        pos.addWidget(self.spin_x)
        pos.addWidget(QLabel('Y'))
        self.spin_y = QSpinBox()
        self.spin_y.valueChanged.connect(self._on_offset_ui)
        pos.addWidget(self.spin_y)
        btn_center = QPushButton(tr('editor_center'))
        btn_center.setToolTip('C')
        btn_center.clicked.connect(self.center)
        pos.addWidget(btn_center)
        pos.addStretch()

        # Vista
        view = QHBoxLayout()
        view.setSpacing(10)
        view.addWidget(self._caption(tr('editor_background')))
        self.combo_bg = QComboBox()
        for label_key, key in self.BG_CHOICES:
            self.combo_bg.addItem(tr(label_key), key)
        if self._shot is None:
            self.combo_bg.model().item(0).setEnabled(False)
        self.combo_bg.currentIndexChanged.connect(self._on_bg_ui)
        view.addWidget(self.combo_bg)
        view.addSpacing(8)
        self.tgl_guides = ToggleSwitch(self.show_guides)
        self.tgl_guides.toggled.connect(self._on_guides_ui)
        view.addWidget(self.tgl_guides)
        view.addWidget(QLabel(tr('editor_guides')))
        view.addStretch()

        for w in (self.sld_size, self.sld_opac, self.spin_size, self.spin_x, self.spin_y,
                  self.combo_bg, btn_center, self.tgl_guides):
            w.setFocusPolicy(Qt.ClickFocus)

        # Fila inferior con botones de accion principal
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addLayout(pos)
        actions.addStretch()

        btn_cancel = QPushButton(tr('editor_cancel'))
        btn_cancel.setObjectName('Ghost')
        btn_cancel.setToolTip(tr('editor_cancel_tooltip'))
        btn_cancel.setFocusPolicy(Qt.ClickFocus)
        btn_cancel.clicked.connect(self.cancel)
        btn_save = QPushButton(tr('editor_save_exit'))
        btn_save.setObjectName('Primary')
        btn_save.setToolTip(tr('editor_save_tooltip'))
        btn_save.setFocusPolicy(Qt.ClickFocus)
        btn_save.clicked.connect(self.save)
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_save)

        root.addLayout(grid)
        root.addLayout(view)
        root.addLayout(actions)

        keys = QHBoxLayout()
        keys.setSpacing(5)
        for key, text_key in (
            (tr('editor_hint_arrows'), 'editor_hint_move'),
            ('+ −', 'editor_hint_size'),
            ('C', 'editor_hint_center'),
            ('G', 'editor_hint_guides'),
            ('B', 'editor_hint_background'),
            ('Enter', 'editor_hint_save'),
            ('Esc', 'editor_hint_cancel'),
        ):
            k = QLabel(key)
            k.setObjectName('Kbd')
            t = QLabel(tr(text_key))
            t.setObjectName('MutedSmall')
            keys.addWidget(k)
            keys.addWidget(t)
            keys.addSpacing(8)
        keys.addStretch()
        root.addLayout(keys)

        self.panel.adjustSize()

    @staticmethod
    def _caption(text):
        lbl = QLabel(text.upper())
        lbl.setObjectName('MetricLabel')
        return lbl

    # Calculos geometricos y conversion de coordenadas
    def _origin(self):
        return crosshair_origin(self._sw, self._sh, self.size_val, self.ox, self.oy)

    def _offset_limits(self):
        base_x = (self._sw - self.size_val) // 2
        base_y = (self._sh - self.size_val) // 2
        return (-base_x, self._sw - self.size_val - base_x,
                -base_y, self._sh - self.size_val - base_y)

    def _sync_ranges(self):
        x0, x1, y0, y1 = self._offset_limits()
        for spin, lo, hi in ((self.spin_x, x0, x1), (self.spin_y, y0, y1)):
            spin.blockSignals(True)
            spin.setRange(lo, hi)
            spin.blockSignals(False)
        self.ox = max(x0, min(x1, self.ox))
        self.oy = max(y0, min(y1, self.oy))

    def _rebuild_pixmap(self):
        self._pix = load_crosshair_pixmap(self._image_path, self.size_val, self._dpr, color=self.color)

    def _sync_widgets(self):
        for w, v in ((self.sld_size, self.size_val), (self.spin_size, self.size_val),
                     (self.spin_x, self.ox), (self.spin_y, self.oy),
                     (self.sld_opac, int(round(self.opacity * 100)))):
            w.blockSignals(True)
            w.setValue(v)
            w.blockSignals(False)
        self.lbl_opac.setText(f'{int(round(self.opacity * 100))}%')
        idx = self.combo_bg.findData(self.bg_mode)
        self.combo_bg.blockSignals(True)
        self.combo_bg.setCurrentIndex(max(0, idx))
        self.combo_bg.blockSignals(False)
        self.lbl_live.setText(f'X {self.ox:+d}   Y {self.oy:+d}   ·   {self.size_val} px')
        self.update()

    # Gestion de cambios recibidos desde los controles del panel
    def _set_size(self, value):
        value = max(MIN_SIZE, min(MAX_SIZE, int(value)))
        if value == self.size_val:
            return
        self.size_val = value
        self._rebuild_pixmap()
        self._sync_ranges()
        self._sync_widgets()

    def _on_size_ui(self, value):
        self._set_size(value)

    def _on_opacity_ui(self, value):
        self.opacity = value / 100.0
        self._sync_widgets()

    def _on_offset_ui(self, _):
        self.ox = self.spin_x.value()
        self.oy = self.spin_y.value()
        self._sync_widgets()

    def _on_bg_ui(self, _):
        self.bg_mode = self.combo_bg.currentData()
        self.update()

    def _on_guides_ui(self, checked):
        self.show_guides = checked
        self.update()

    def center(self):
        self.ox = self.oy = 0
        self._sync_widgets()

    def _move_offset(self, dx, dy):
        x0, x1, y0, y1 = self._offset_limits()
        self.ox = max(x0, min(x1, self.ox + dx))
        self.oy = max(y0, min(y1, self.oy + dy))
        self._sync_widgets()

    def _cycle_background(self):
        keys = [k for _, k in self.BG_CHOICES if not (k == 'screenshot' and self._shot is None)]
        nxt = keys[(keys.index(self.bg_mode) + 1) % len(keys)] if self.bg_mode in keys else keys[0]
        self.bg_mode = nxt
        self._sync_widgets()

    # Metodos del ciclo de vida de la ventana del editor
    def present(self):
        geo = self._screen.geometry()
        self.move(geo.topLeft())
        self.showFullScreen()
        self._place_panel()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def _place_panel(self):
        if self.panel_moved_by_user:
            return
        self.panel.adjustSize()
        self.panel.move((self.width() - self.panel.width()) // 2,
                        self.height() - self.panel.height() - 28)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_panel()

    def save(self):
        if self._done:
            return
        self._done = True
        self.result_values = {
            'size': self.size_val,
            'offset_x': self.ox,
            'offset_y': self.oy,
            'opacity': self.opacity,
            'color': self.color,
            'editor_background': self.bg_mode,
            'editor_guides': self.show_guides,
        }
        self.saved.emit(self.result_values)
        self.accept()

    def cancel(self):
        if self._done:
            return
        self._done = True
        self.reject()

    def closeEvent(self, event):
        self._done = True
        super().closeEvent(event)
        self.closed.emit()

    # Procesamiento de eventos de teclado y raton
    def _drag_to(self, pos):
        base_x = (self._sw - self.size_val) // 2
        base_y = (self._sh - self.size_val) // 2
        ox = int(round(pos.x() - self.size_val / 2.0)) - base_x
        oy = int(round(pos.y() - self.size_val / 2.0)) - base_y
        if not (QApplication.keyboardModifiers() & Qt.AltModifier):
            if abs(ox) <= SNAP_DISTANCE:
                ox = 0
            if abs(oy) <= SNAP_DISTANCE:
                oy = 0
        x0, x1, y0, y1 = self._offset_limits()
        self.ox = max(x0, min(x1, ox))
        self.oy = max(y0, min(y1, oy))
        self._sync_widgets()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setFocus()
            self._dragging = True
            self._drag_to(event.pos())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._drag_to(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = 1 if (event.modifiers() & Qt.ControlModifier) else 2
        if event.modifiers() & Qt.ShiftModifier:
            step = 10
        self._set_size(self.size_val + (step if delta > 0 else -step))

    def keyPressEvent(self, event):
        key = event.key()
        step = 10 if (event.modifiers() & Qt.ShiftModifier) else 1
        if key == Qt.Key_Left:
            self._move_offset(-step, 0)
        elif key == Qt.Key_Right:
            self._move_offset(step, 0)
        elif key == Qt.Key_Up:
            self._move_offset(0, -step)
        elif key == Qt.Key_Down:
            self._move_offset(0, step)
        elif key in (Qt.Key_Plus, Qt.Key_Equal):
            self._set_size(self.size_val + step)
        elif key in (Qt.Key_Minus, Qt.Key_Underscore):
            self._set_size(self.size_val - step)
        elif key == Qt.Key_C:
            self.center()
        elif key == Qt.Key_G:
            self.tgl_guides.setChecked(not self.show_guides)
        elif key == Qt.Key_B:
            self._cycle_background()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self.save()
        elif key == Qt.Key_Escape:
            self.cancel()
        else:
            super().keyPressEvent(event)

    # Rutina de renderizado de fondo y guias visuales
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()

        if self.bg_mode == 'screenshot' and self._shot is not None:
            p.drawPixmap(self.rect(), self._shot)
        else:
            p.fillRect(self.rect(), QColor('#D5DDE8') if self._light_bg else QColor('#0B0F19'))
            if self.bg_mode == 'grid':
                tone = 0 if self._light_bg else 255
                p.setPen(QPen(QColor(tone, tone, tone, 22 if self._light_bg else 14), 1))
                for x in range(0, w, 50):
                    p.drawLine(x, 0, x, h)
                for y in range(0, h, 50):
                    p.drawLine(0, y, w, y)
                p.setPen(QPen(QColor(tone, tone, tone, 45 if self._light_bg else 30), 1))
                for x in range(0, w, 250):
                    p.drawLine(x, 0, x, h)
                for y in range(0, h, 250):
                    p.drawLine(0, y, w, y)

        tl_x, tl_y = self._origin()
        cx = tl_x + self.size_val / 2.0
        cy = tl_y + self.size_val / 2.0

        if self.show_guides:
            # Centro real de la pantalla
            centre_tone = 0 if (self._light_bg and self.bg_mode != 'screenshot') else 255
            p.setPen(QPen(QColor(centre_tone, centre_tone, centre_tone, 90), 1, Qt.DashLine))
            p.drawLine(QPointF(w / 2.0, 0), QPointF(w / 2.0, h))
            p.drawLine(QPointF(0, h / 2.0), QPointF(w, h / 2.0))
            # Ejes que pasan por la mira
            p.setPen(QPen(QColor(56, 189, 248, 150), 1))
            p.drawLine(QPointF(cx, 0), QPointF(cx, h))
            p.drawLine(QPointF(0, cy), QPointF(w, cy))
            # Area ocupada por la mira
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(56, 189, 248, 200), 1, Qt.DotLine))
            p.drawRect(QRectF(tl_x - 0.5, tl_y - 0.5, self.size_val + 1, self.size_val + 1))

        if self._pix is not None and not self._pix.isNull():
            pw = self._pix.width() / self._pix.devicePixelRatio()
            ph = self._pix.height() / self._pix.devicePixelRatio()
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.setOpacity(self.opacity)
            p.drawPixmap(int(round(tl_x + (self.size_val - pw) / 2)),
                         int(round(tl_y + (self.size_val - ph) / 2)), self._pix)
            p.setOpacity(1.0)
        else:
            p.setPen(QPen(QColor(C['warn']), 2))
            p.drawRect(QRectF(tl_x, tl_y, self.size_val, self.size_val))

        if self.show_guides:
            self._draw_badge(p, tl_x, tl_y)

    def _draw_badge(self, p, tl_x, tl_y):
        text = f'X {self.ox:+d}   Y {self.oy:+d}   ·   {self.size_val} px'
        f = p.font()
        f.setPixelSize(12)
        f.setBold(True)
        p.setFont(f)
        fm = QFontMetrics(f)
        bw, bh = fm.horizontalAdvance(text) + 20, 24
        bx = tl_x + self.size_val / 2.0 - bw / 2.0
        by = tl_y + self.size_val + 10
        if by + bh > self.height() - 8:
            by = tl_y - bh - 10
        bx = max(8, min(self.width() - bw - 8, bx))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(8, 12, 20, 225))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 8, 8)
        p.setPen(QColor(C['strong']))
        p.drawText(QRectF(bx, by, bw, bh), Qt.AlignCenter, text)

