# Dialogos para crear editar y gestionar estados alternativos de perfiles
import os
import copy
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox,
    QSlider, QSpinBox, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon

from color_picker import ColorPicker
from config_manager import new_preset_id, STATE_NAME_MAX, MAX_STATES
from hotkey_listener import normalize_hotkey
from overlay import CROSSHAIRS_DIR, MIN_SIZE, MAX_SIZE, resolve_crosshair_path
from styles import C, tr
from widgets import (
    CrosshairThumb, PreviewBox, HotkeyRecorderButton, describe_values, pretty_hotkey, VISUAL_KEYS
)

SCREEN_KEYS = ('size', 'offset_x', 'offset_y', 'opacity', 'color')


def _section(text):
    lbl = QLabel(text)
    lbl.setObjectName('Section')
    return lbl


def _same_hotkey(a, b):
    return bool(a) and bool(b) and normalize_hotkey(a) == normalize_hotkey(b)


# Ventana de edicion para configurar parametros visuales y atajo de un estado
class StateEditDialog(QDialog):
    def __init__(self, parent, state, crosshairs, existing_names=(), reserved=None, screen_editor=None, current_values=None,
                 is_new=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(tr('state_new_title') if is_new else tr('state_edit_title'))
        self.setModal(True)
        self._v = copy.deepcopy(state)
        self._crosshairs = list(crosshairs)
        self._names = {n.lower() for n in existing_names}
        self._reserved = dict(reserved or {})
        self._screen_editor = screen_editor
        self._current = current_values
        self.result_state = None
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 22)
        root.setSpacing(14)

        title = QLabel(tr('state_new_title') if is_new else tr('state_edit_title'))
        title.setObjectName('DialogTitle')
        root.addWidget(title)
        sub = QLabel(tr('state_dialog_description'))
        sub.setObjectName('Muted')
        sub.setWordWrap(True)
        root.addWidget(sub)

        cols = QHBoxLayout()
        cols.setSpacing(26)
        cols.addLayout(self._build_left(), 0)
        cols.addLayout(self._build_right(), 1)
        root.addLayout(cols)

        self.lbl_error = QLabel('')
        self.lbl_error.setObjectName('Error')
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setVisible(False)
        root.addWidget(self.lbl_error)

        buttons = QHBoxLayout()
        buttons.addStretch()
        btn_cancel = QPushButton(tr('common_cancel'))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton(tr('state_save_button'))
        btn_save.setObjectName('Primary')
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(btn_save)
        root.addLayout(buttons)

        self._load_values()
        self.edit_name.setFocus()
        self.edit_name.selectAll()

    # Construccion de los paneles izquierdo y derecho
    def _build_left(self):
        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(_section(tr('state_preview').upper()))
        self.preview = PreviewBox()
        self.preview.setFixedWidth(280)
        left.addWidget(self.preview)

        left.addWidget(_section(tr('state_crosshair').upper()))
        self.combo_crosshair = QComboBox()
        self.combo_crosshair.setIconSize(QSize(22, 22))
        for fn in self._crosshairs:
            pix = QPixmap(os.path.join(CROSSHAIRS_DIR, fn))
            icon = QIcon(pix.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)) if not pix.isNull() else QIcon()
            self.combo_crosshair.addItem(icon, os.path.splitext(fn)[0], fn)
        self.combo_crosshair.currentIndexChanged.connect(self._on_crosshair)
        left.addWidget(self.combo_crosshair)

        left.addSpacing(2)
        left.addWidget(_section(tr('state_color').upper()))
        self.color_picker = ColorPicker(self._v.get('color', 'original'))
        self.color_picker.setFixedWidth(280)
        self.color_picker.colorChanged.connect(self._on_color)
        left.addWidget(self.color_picker)
        left.addStretch()
        return left

    def _build_right(self):
        right = QVBoxLayout()
        right.setSpacing(8)

        right.addWidget(_section(tr('state_name').upper()))
        self.edit_name = QLineEdit()
        self.edit_name.setMaxLength(STATE_NAME_MAX)
        self.edit_name.setPlaceholderText(tr('state_name_placeholder'))
        right.addWidget(self.edit_name)

        right.addSpacing(4)
        right.addWidget(_section(tr('state_size').upper()))
        row = QHBoxLayout()
        self.sld_size = QSlider(Qt.Horizontal)
        self.sld_size.setRange(MIN_SIZE, 300)
        self.sld_size.valueChanged.connect(self._on_size_slider)
        row.addWidget(self.sld_size, 1)
        self.spin_size = QSpinBox()
        self.spin_size.setRange(MIN_SIZE, MAX_SIZE)
        self.spin_size.setSuffix(' px')
        self.spin_size.setFixedWidth(92)
        self.spin_size.valueChanged.connect(self._on_size_spin)
        row.addWidget(self.spin_size)
        right.addLayout(row)

        right.addSpacing(4)
        right.addWidget(_section(tr('state_position').upper()))
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel('X'))
        self.spin_x = QSpinBox()
        self.spin_x.setRange(-5000, 5000)
        self.spin_x.valueChanged.connect(self._on_offset)
        row.addWidget(self.spin_x, 1)
        row.addWidget(QLabel('Y'))
        self.spin_y = QSpinBox()
        self.spin_y.setRange(-5000, 5000)
        self.spin_y.valueChanged.connect(self._on_offset)
        row.addWidget(self.spin_y, 1)
        btn_center = QPushButton(tr('state_center'))
        btn_center.setCursor(Qt.PointingHandCursor)
        btn_center.clicked.connect(lambda: (self.spin_x.setValue(0), self.spin_y.setValue(0)))
        row.addWidget(btn_center)
        right.addLayout(row)

        right.addSpacing(4)
        head = QHBoxLayout()
        head.addWidget(_section(tr('state_opacity').upper()))
        head.addStretch()
        self.lbl_opac = QLabel('')
        self.lbl_opac.setStyleSheet(f'font-weight: 700; color: {C["accent"]};')
        head.addWidget(self.lbl_opac)
        right.addLayout(head)
        self.sld_opac = QSlider(Qt.Horizontal)
        self.sld_opac.setRange(5, 100)
        self.sld_opac.valueChanged.connect(self._on_opacity)
        right.addWidget(self.sld_opac)

        helpers = QHBoxLayout()
        helpers.setSpacing(8)
        if self._screen_editor is not None:
            btn_screen = QPushButton(tr('state_fullscreen_button'))
            btn_screen.setObjectName('Primary')
            btn_screen.setCursor(Qt.PointingHandCursor)
            btn_screen.setToolTip(tr('state_fullscreen_tooltip'))
            btn_screen.clicked.connect(self._open_screen_editor)
            helpers.addWidget(btn_screen)
        if self._current is not None:
            btn_cur = QPushButton(tr('preset_use_current'))
            btn_cur.setCursor(Qt.PointingHandCursor)
            btn_cur.setToolTip(tr('preset_use_current_tooltip'))
            btn_cur.clicked.connect(self._use_current)
            helpers.addWidget(btn_cur)
        helpers.addStretch()
        right.addSpacing(4)
        right.addLayout(helpers)

        right.addSpacing(6)
        right.addWidget(_section(tr('state_hotkey_section').upper()))
        sub_hk = QLabel(tr('state_hotkey_hint'))
        sub_hk.setObjectName('MutedSmall')
        right.addWidget(sub_hk)
        hk = QHBoxLayout()
        self.btn_hotkey = HotkeyRecorderButton(self._v.get('hotkey', ''), allow_empty=True)
        self.btn_hotkey.hotkey_changed.connect(self._on_hotkey)
        hk.addWidget(self.btn_hotkey)
        hk.addStretch()
        right.addLayout(hk)

        self.combo_mode = QComboBox()
        for key in ('hold', 'toggle'):
            self.combo_mode.addItem(tr(f'state_mode_{key}'), key)
        self.combo_mode.currentIndexChanged.connect(self._on_mode)
        right.addWidget(self.combo_mode)
        right.addStretch()
        return right

    # Sincronizacion bidireccional entre valores y controles
    def _load_values(self):
        self._loading = True
        v = self._v
        self.edit_name.setText(v.get('name', ''))
        idx = self.combo_crosshair.findData(v.get('crosshair_file'))
        if idx < 0 and self.combo_crosshair.count():
            idx = 0
            v['crosshair_file'] = self.combo_crosshair.itemData(0)
        self.combo_crosshair.setCurrentIndex(max(0, idx))
        self.sld_size.setValue(min(v['size'], self.sld_size.maximum()))
        self.spin_size.setValue(v['size'])
        self.spin_x.setValue(v['offset_x'])
        self.spin_y.setValue(v['offset_y'])
        self.sld_opac.setValue(int(round(v['opacity'] * 100)))
        self.color_picker.set_color(v.get('color', 'original'))
        mode = v.get('mode', 'hold')
        v['mode'] = mode
        mi = self.combo_mode.findData(mode)
        self.combo_mode.setCurrentIndex(max(0, mi))
        self.btn_hotkey.set_hotkey(v.get('hotkey', ''))
        self._loading = False
        self._refresh_preview()

    def _refresh_preview(self):
        v = self._v
        self.preview.set_image(resolve_crosshair_path(v.get('crosshair_file', '')))
        self.preview.set_color(v.get('color', 'original'))
        self.preview.set_opacity(v.get('opacity', 1.0))
        self.lbl_opac.setText(f"{int(round(v.get('opacity', 1.0) * 100))}%")

    def _on_crosshair(self, _):
        if self._loading:
            return
        self._v['crosshair_file'] = self.combo_crosshair.currentData() or ''
        self._refresh_preview()

    def _on_color(self, color):
        if self._loading:
            return
        self._v['color'] = color or 'original'
        self._refresh_preview()

    def _on_size_slider(self, value):
        if self._loading:
            return
        self._v['size'] = value
        self._loading = True
        self.spin_size.setValue(value)
        self._loading = False

    def _on_size_spin(self, value):
        if self._loading:
            return
        self._v['size'] = value
        self._loading = True
        self.sld_size.setValue(min(value, self.sld_size.maximum()))
        self._loading = False

    def _on_offset(self, _):
        if self._loading:
            return
        self._v['offset_x'] = self.spin_x.value()
        self._v['offset_y'] = self.spin_y.value()

    def _on_opacity(self, value):
        if self._loading:
            return
        self._v['opacity'] = value / 100.0
        self._refresh_preview()

    def _on_hotkey(self, hotkey):
        self._v['hotkey'] = hotkey
        self.lbl_error.setVisible(False)

    def _on_mode(self, _):
        if not self._loading:
            self._v['mode'] = self.combo_mode.currentData()

    def _use_current(self):
        if not self._current:
            return
        for k in VISUAL_KEYS:
            if k in self._current:
                self._v[k] = self._current[k]
        self._load_values()

    # Apertura del editor visual en pantalla completa
    def _open_screen_editor(self):
        values = {
            'size': int(self._v.get('size', 32)),
            'offset_x': int(self._v.get('offset_x', 0)),
            'offset_y': int(self._v.get('offset_y', 0)),
            'opacity': float(self._v.get('opacity', 1.0)),
            'color': self._v.get('color', 'original'),
        }
        self.btn_hotkey.stop_recording()

        main_win = self.window()
        screens = QApplication.screens()
        idx = 0
        if hasattr(main_win, 'config'):
            idx = max(0, min(main_win.config.get('monitor_index', 0), len(screens) - 1))
        screen = screens[idx] if screens else QApplication.primaryScreen()
        image_file = self._v.get('crosshair_file', '')

        self.setWindowOpacity(0.0)
        parent = self.parentWidget()
        if parent:
            parent.setWindowOpacity(0.0)
        if main_win and main_win != self:
            main_win.setWindowOpacity(0.0)

        try:
            shot = None
            try:
                QApplication.processEvents()
                if screen:
                    shot = screen.grabWindow(0)
            except Exception:
                pass

            bg_mode = 'plain'
            guides = True
            if hasattr(main_win, 'config'):
                bg_mode = main_win.config.get('editor_background', 'plain')
                guides = main_win.config.get('editor_guides', True)

            from editor_window import CrosshairEditor
            editor = CrosshairEditor(
                self,
                screen=screen,
                image_path=resolve_crosshair_path(image_file),
                values=values,
                background=shot,
                bg_mode=bg_mode,
                guides=guides,
            )
            editor.present()
            if editor.exec_() == QDialog.Accepted and editor.result_values:
                self._on_screen_saved(editor.result_values)
        finally:
            if main_win and main_win != self:
                main_win.setWindowOpacity(1.0)
            if parent:
                parent.setWindowOpacity(1.0)
            self.setWindowOpacity(1.0)
            self.raise_()
            self.activateWindow()

    def _on_screen_saved(self, values):
        for k in SCREEN_KEYS:
            if k in values:
                self._v[k] = values[k]
        self._load_values()

    # Validacion y almacenamiento de los datos del estado
    def _fail(self, text):
        self.lbl_error.setText(text)
        self.lbl_error.setVisible(True)

    def _on_save(self):
        name = self.edit_name.text().strip()
        if not name:
            return self._fail(tr('state_error_name_required'))
        if name.lower() in self._names:
            return self._fail(tr('state_error_name_exists').format(name=name))
        if not self._v.get('crosshair_file'):
            return self._fail(tr('state_error_crosshair_required'))
        hotkey = (self._v.get('hotkey') or '').strip()
        if not hotkey:
            return self._fail(tr('state_error_hotkey_required'))
        for key, owner in self._reserved.items():
            if _same_hotkey(hotkey, key):
                return self._fail(tr('state_error_hotkey_taken').format(owner=owner))
        self.btn_hotkey.stop_recording()
        mode = self.combo_mode.currentData() or self._v.get('mode', 'hold')
        self.result_state = dict(self._v, name=name, hotkey=hotkey, mode=mode)
        self.accept()


# Fila de un estado dentro de la lista
class _StateRow(QFrame):
    def __init__(self, state, on_edit=None, on_delete=None, base=False, parent=None):
        super().__init__(parent)
        self.setObjectName('Tile')
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(14)
        thumb = CrosshairThumb(54)
        thumb.set_values(state)
        lay.addWidget(thumb, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(3)
        name = QLabel(state['name'])
        name.setObjectName('PresetName')
        col.addWidget(name)
        if base:
            meta = QLabel(tr('state_base_description'))
            meta.setObjectName('MutedSmall')
        else:
            how = tr('state_mode_hold_short' if state.get('mode', 'hold') == 'hold'
                     else 'state_mode_toggle_short')
            btn = pretty_hotkey(state.get('hotkey')) or tr('state_no_hotkey')
            meta = QLabel(f'{btn}  ·  {how}')
            meta.setObjectName('MetaOn')
        col.addWidget(meta)
        summary = QLabel(describe_values(state))
        summary.setTextFormat(Qt.RichText)
        summary.setObjectName('Muted')
        col.addWidget(summary)
        lay.addLayout(col, 1)

        if not base:
            btn_edit = QPushButton(tr('preset_edit'))
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.clicked.connect(on_edit)
            lay.addWidget(btn_edit)
            btn_del = QPushButton(tr('preset_delete'))
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.clicked.connect(on_delete)
            lay.addWidget(btn_del)


# Dialogo con todos los estados de un preset
class StatesDialog(QDialog):
    def __init__(self, parent, preset, crosshairs, current_values=None, reserved=None, screen_editor=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(tr('state_list_title'))
        self.setModal(True)
        self.setMinimumWidth(640)
        self._preset = preset
        self._states = copy.deepcopy(preset.get('states', []))
        self._crosshairs = list(crosshairs)
        self._current = current_values
        self._reserved = dict(reserved or {})
        self._screen_editor = screen_editor
        self.result_states = None

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 22)
        root.setSpacing(14)

        title = QLabel(tr('state_list_heading').format(name=preset['name']))
        title.setObjectName('DialogTitle')
        root.addWidget(title)
        sub = QLabel(tr('state_list_description'))
        sub.setObjectName('Muted')
        sub.setWordWrap(True)
        root.addWidget(sub)

        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumHeight(330)
        scroll.setWidget(self.list_host)
        root.addWidget(scroll, 1)

        add_row = QHBoxLayout()
        self.btn_add = QPushButton(tr('state_add'))
        self.btn_add.setObjectName('Primary')
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setFixedHeight(38)
        self.btn_add.clicked.connect(self._add)
        add_row.addWidget(self.btn_add)
        self.lbl_limit = QLabel(tr('state_max_count').format(max=MAX_STATES))
        self.lbl_limit.setObjectName('MutedSmall')
        add_row.addWidget(self.lbl_limit)
        add_row.addStretch()
        root.addLayout(add_row)

        buttons = QHBoxLayout()
        buttons.addStretch()
        btn_cancel = QPushButton(tr('common_cancel'))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton(tr('common_save'))
        btn_save.setObjectName('Primary')
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(btn_save)
        root.addLayout(buttons)

        self._refresh()
        self.resize(680, 600)

    def _refresh(self):
        while self.list_layout.count():
            widget = self.list_layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        base = dict(self._preset, name=tr('state_base_name'))
        self.list_layout.addWidget(_StateRow(base, base=True))
        for i, st in enumerate(self._states):
            self.list_layout.addWidget(_StateRow(st, on_edit=lambda _=False, i=i: self._edit(i),
                                                 on_delete=lambda _=False, i=i: self._delete(i)))
        if not self._states:
            empty = QLabel(tr('state_empty'))
            empty.setObjectName('Muted')
            empty.setWordWrap(True)
            empty.setContentsMargins(4, 6, 4, 0)
            self.list_layout.addWidget(empty)
        self.list_layout.addStretch()
        full = len(self._states) >= MAX_STATES
        self.btn_add.setEnabled(not full)
        self.lbl_limit.setVisible(full)

    def _reserved_for(self, skip=None):
        reserved = dict(self._reserved)
        for i, st in enumerate(self._states):
            if i != skip and st.get('hotkey'):
                reserved[normalize_hotkey(st['hotkey'])] = tr('state_reserved').format(name=st['name'])
        return reserved

    def _names_except(self, skip=None):
        names = [tr('state_base_name')]
        names += [st['name'] for i, st in enumerate(self._states) if i != skip]
        return names

    def _unique_name(self, base):
        taken = {n.lower() for n in self._names_except()}
        name, n = base, 2
        while name.lower() in taken:
            name = f'{base} {n}'
            n += 1
        return name

    def _add(self):
        first = not self._states
        default_name = self._unique_name(tr('state_default_aiming' if first
                                            else 'state_default_name'))
        default_mode = 'hold' if first else 'toggle'
        state = {k: self._preset.get(k, 0) for k in VISUAL_KEYS}
        state.update(id=new_preset_id(), name=default_name, hotkey='', mode=default_mode)

        dlg = StateEditDialog(self, state, self._crosshairs, self._names_except(), self._reserved_for(),
                              self._screen_editor, self._current, is_new=True)
        if dlg.exec_() == QDialog.Accepted and dlg.result_state:
            self._states.append(dlg.result_state)
            self._refresh()

    def _edit(self, i):
        dlg = StateEditDialog(self, self._states[i], self._crosshairs, self._names_except(i), self._reserved_for(i),
                              self._screen_editor, self._current)
        if dlg.exec_() == QDialog.Accepted and dlg.result_state:
            self._states[i] = dlg.result_state
            self._refresh()

    def _delete(self, i):
        del self._states[i]
        self._refresh()

    def _on_save(self):
        self.result_states = list(self._states)
        self.accept()
