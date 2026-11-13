# Ventana principal de la aplicacion que integra navegacion controles y logica
import os
import re
import copy
import time
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QComboBox, QButtonGroup, QScrollArea, QFileDialog,
    QFrame, QMessageBox, QSystemTrayIcon, QMenu, QAction, QStackedWidget, QDialog,
    QInputDialog
)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QImageReader

from config_manager import load_config, new_preset_id, save_config
from overlay import CrosshairOverlay, CROSSHAIRS_DIR, resolve_crosshair_path
from game_detector import match_foreground
from hotkey_listener import HotkeyManager, StateInputWatcher, normalize_hotkey
from startup_manager import is_startup_enabled, set_startup_enabled
from editor_window import CrosshairEditor
from color_picker import ColorPicker
from state_dialogs import StatesDialog
from styles import (
    C, THEMES, make_app_icon, load_app_logo, build_stylesheet, set_theme, get_current_theme,
    make_nav_icon, LANGUAGES, set_language, get_language, tr
)
from widgets import (
    FlowLayout, ToggleSwitch, SettingRow, ModeCard, CrosshairCard, PreviewBox, MonitorMap,
    HotkeyRecorderButton, CrosshairThumb, ThemeCard, PresetCard, PresetDialog,
    describe_values, same_visuals
)

IMAGE_EXTS = ('.png',)
NAV_KEYS = (
    ('nav_crosshairs', 'miras'),
    ('nav_position', 'position'),
    ('nav_presets', 'presets'),
    ('nav_settings', 'settings'),
)
TAB_PRESETS = 2


# Comunicador de senales entre hilos y la interfaz
class SignalBridge(QObject):
    hotkey_triggered = pyqtSignal()
    # Notificacion del identificador de estado y pulsacion detectada
    state_event = pyqtSignal(str, bool)


# Cuadro de dialogo para confirmaciones de usuario
def ask_yes_no(parent, title, text):
    box = QMessageBox(QMessageBox.Question, title, text, QMessageBox.NoButton, parent)
    btn_yes = box.addButton(tr('common_yes'), QMessageBox.YesRole)
    btn_no = box.addButton(tr('common_no'), QMessageBox.NoRole)
    box.setDefaultButton(btn_no)
    box.setEscapeButton(btn_no)
    box.exec_()
    return box.clickedButton() is btn_yes


def make_label(text, name=None, wrap=False):
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    lbl.setWordWrap(wrap)
    return lbl


def make_card(spacing=14, margins=(22, 20, 22, 20)):
    frame = QFrame()
    frame.setObjectName('Card')
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return frame, lay


# Ventana de configuracion y control general
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        set_theme(self.config.get('theme', 'dark'))
        set_language(self.config.get('language', 'es'))
        QApplication.instance().setStyleSheet(build_stylesheet())
        self.overlay = CrosshairOverlay(self.config)
        self.cards = {}
        self.preset_cards = {}
        self.editor = None
        self.editing = False
        self._restore_window = True
        self._tray_hint_shown = False
        self._last_hotkey = 0.0
        self._tick = 0
        self._last_auto_target = None
        # Ultimo perfil cargado para desambiguar perfiles identicos
        self.active_preset_id = None
        # estado del preset que esta aplicado ahora mismo
        self.active_state_id = None
        # Devoluciones de llamada para el editor abierto desde estados
        self._external_editor = None
        self._bound_sig = None
        self.app_icon = make_app_icon()

        self.bridge = SignalBridge()
        self.bridge.hotkey_triggered.connect(self.on_hotkey_pressed)
        self.hotkey_mgr = HotkeyManager(self.bridge.hotkey_triggered.emit)
        self.state_watcher = StateInputWatcher(self.bridge.state_event.emit)
        self.bridge.state_event.connect(self.on_state_event, Qt.QueuedConnection)
        self.hotkey_ok = True
        if self.config.get('manual_enabled', True):
            self.hotkey_ok = self.hotkey_mgr.set_hotkey(self.config.get('hotkey', 'F2'))

        # Temporizador para diferir el guardado en disco y evitar escrituras continuas
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(lambda: save_config(self.config))

        # Temporizador para modo automatico de deteccion de juegos
        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self.on_tick)
        self.auto_timer.start(500)

        self.init_tray()
        self.init_ui()
        self.ensure_valid_crosshair()
        self.refresh_gallery()
        self.refresh_presets()
        self._normalize_startup_state()
        self.apply_visibility()
        self.refresh_all()

    def persist(self):
        self._save_timer.start()

    # Gestion de la bandeja del sistema y sus opciones
    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("Akro's CrossHair")

        menu = QMenu()
        act_show = QAction(tr('tray_show'), self)
        act_show.triggered.connect(self.show_and_activate)
        menu.addAction(act_show)

        act_edit = QAction(tr('tray_edit'), self)
        act_edit.triggered.connect(self.open_editor)
        menu.addAction(act_edit)

        self.act_toggle = QAction(tr('tray_hide'), self)
        self.act_toggle.triggered.connect(self.toggle_active_state)
        menu.addAction(self.act_toggle)

        menu.addSeparator()
        act_exit = QAction("Akro's CrossHair", self)
        act_exit.triggered.connect(self.force_exit)
        menu.addAction(act_exit)

        self.tray_menu = menu
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_and_activate()

    def show_and_activate(self):
        self.show()
        self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self.raise_()
        self.activateWindow()

    def force_exit(self):
        self.auto_timer.stop()
        self._save_timer.stop()
        save_config(self.config)
        self.hotkey_mgr.clear_hotkey()
        self.state_watcher.stop()
        if self.editor is not None:
            self.editor.cancel()
        self.overlay.close()
        self.tray_icon.hide()
        QApplication.quit()

    def init_ui(self):
        self.setWindowTitle("Akro's CrossHair")
        self.setWindowIcon(self.app_icon)
        self.setMinimumSize(980, 640)
        self.resize(1080, 720)
        self.statusBar().setSizeGripEnabled(False)
        self._build_central(0)

    # Construccion y montaje de la interfaz grafica principal
    def _build_central(self, index=0):
        if hasattr(self, 'btn_hotkey'):
            self.btn_hotkey.stop_recording()
        central = QWidget()
        central.setObjectName('Root')
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self.build_sidebar())

        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_page_crosshairs())
        self.stack.addWidget(self.build_page_position())
        self.stack.addWidget(self.build_page_presets())
        self.stack.addWidget(self.build_page_settings())
        root.addWidget(self.stack, 1)

        # Reemplazo seguro del contenido visual previo
        self.setCentralWidget(central)
        self.switch_to_tab(index)

    def build_sidebar(self):
        side = QFrame()
        side.setObjectName('Sidebar')
        side.setFixedWidth(230)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 22, 0, 18)
        lay.setSpacing(0)

        brand = QHBoxLayout()
        brand.setContentsMargins(20, 0, 20, 0)
        brand.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(self._hidpi(load_app_logo(), 38))
        brand.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(make_label("Akro's CrossHair", 'AppTitle'))
        brand.addLayout(names)
        brand.addStretch()
        lay.addLayout(brand)
        lay.addSpacing(26)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = []
        for i, (key, icon_kind) in enumerate(NAV_KEYS):
            btn = QPushButton(tr(key))
            btn.setObjectName('Nav')
            btn.setCheckable(True)
            btn.setIcon(make_nav_icon(icon_kind))
            btn.setIconSize(QSize(20, 20))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self.stack.setCurrentIndex(idx))
            self.nav_group.addButton(btn)
            self.nav_buttons.append(btn)
            lay.addWidget(btn)
        lay.addStretch()

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(16, 0, 16, 0)
        self.btn_toggle_crosshair = QPushButton()
        self.btn_toggle_crosshair.setObjectName('Primary')
        self.btn_toggle_crosshair.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_crosshair.setFixedHeight(42)
        self.btn_toggle_crosshair.clicked.connect(
            lambda checked=False: self.toggle_active_state())
        toggle_row.addWidget(self.btn_toggle_crosshair)
        lay.addLayout(toggle_row)
        self.update_active_button()

        return side

    @staticmethod
    def _hidpi(pix, size):
        out = pix.scaled(size * 2, size * 2, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        out.setDevicePixelRatio(2)
        return out

    # Estructura general de las paginas con encabezado y area desplazable
    def make_page(self, title, subtitle):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        page = QWidget()
        page.setObjectName('Root')
        lay = QVBoxLayout(page)
        lay.setContentsMargins(34, 30, 34, 26)
        lay.setSpacing(6)
        lay.addWidget(make_label(title, 'PageTitle'))
        if subtitle:
            lay.addWidget(make_label(subtitle, 'PageSub', wrap=True))
        lay.addSpacing(14)
        body = QVBoxLayout()
        body.setSpacing(16)
        lay.addLayout(body)
        lay.addStretch()
        scroll.setWidget(page)
        return scroll, body

    def build_page_crosshairs(self):
        page, body = self.make_page(tr('page_crosshairs_title'), tr('page_crosshairs_sub'))
        row = QHBoxLayout()
        row.setSpacing(16)

        lib, lib_lay = make_card()
        head = QHBoxLayout()
        head.addWidget(make_label(tr('lbl_library'), 'CardTitle'))
        self.lbl_count = make_label('', 'Muted')
        head.addWidget(self.lbl_count)
        head.addStretch()
        btn_add = QPushButton(tr('btn_add_crosshair'))
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self.import_custom_crosshair)
        head.addWidget(btn_add)
        lib_lay.addLayout(head)

        self.gallery_widget = QWidget()
        self.gallery_layout = FlowLayout(self.gallery_widget, 10, 10)
        lib_lay.addWidget(self.gallery_widget)
        self.lbl_empty = make_label(tr('lbl_no_crosshairs'), 'Muted', wrap=True)
        lib_lay.addWidget(self.lbl_empty)
        lib_lay.addStretch()
        row.addWidget(lib, 1)

        right, right_lay = make_card(spacing=12)
        right.setFixedWidth(304)
        right_lay.addWidget(make_label(tr('lbl_preview'), 'CardTitle'))
        self.preview = PreviewBox()
        right_lay.addWidget(self.preview)
        self.lbl_mira_name = make_label('', 'Muted')
        self.lbl_mira_name.setAlignment(Qt.AlignCenter)
        right_lay.addWidget(self.lbl_mira_name)
        right_lay.addSpacing(6)

        opac_head = QHBoxLayout()
        opac_head.addWidget(make_label(tr('lbl_opacity'), 'MetricLabel'))
        opac_head.addStretch()
        self.lbl_opac_val = QLabel('')
        self.lbl_opac_val.setStyleSheet(f'font-weight: 700; color: {C["accent"]};')
        opac_head.addWidget(self.lbl_opac_val)
        right_lay.addLayout(opac_head)
        self.opac_slider = QSlider(Qt.Horizontal)
        self.opac_slider.setRange(10, 100)
        self.opac_slider.setValue(int(round(self.config.get('opacity', 1.0) * 100)))
        self.opac_slider.valueChanged.connect(self.on_opacity_changed)
        right_lay.addWidget(self.opac_slider)

        right_lay.addSpacing(8)
        right_lay.addWidget(make_label(tr('lbl_color'), 'MetricLabel'))
        self.color_picker = ColorPicker(self.config.get('color', 'original'))
        self.color_picker.colorChanged.connect(self.set_crosshair_color)
        right_lay.addWidget(self.color_picker)

        right_lay.addStretch()
        row.addWidget(right, 0, Qt.AlignTop)

        body.addLayout(row)
        return page

    # Pagina de configuracion de tamano y posicion
    def build_page_position(self):
        page, body = self.make_page(tr('page_position_title'), tr('page_position_sub'))
        hero, hero_lay = make_card(spacing=0, margins=(26, 24, 26, 24))
        hero_row = QHBoxLayout()
        hero_row.setSpacing(28)

        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(make_label(tr('lbl_fullscreen_editor'), 'CardTitle'))
        left.addSpacing(8)
        btn_editor = QPushButton(tr('btn_open_editor'))
        btn_editor.setObjectName('Primary')
        btn_editor.setCursor(Qt.PointingHandCursor)
        btn_editor.setFixedHeight(46)
        btn_editor.clicked.connect(self.open_editor)
        left.addWidget(btn_editor)
        left.addStretch()
        hero_row.addLayout(left, 1)

        self.monitor_map = MonitorMap()
        hero_row.addWidget(self.monitor_map, 0)
        hero_lay.addLayout(hero_row)
        body.addWidget(hero)

        summary, sum_lay = make_card(spacing=14)
        top = QHBoxLayout()
        top.addWidget(make_label(tr('lbl_current_values'), 'CardTitle'))
        top.addStretch()
        btn_center = QPushButton(tr('btn_center'))
        btn_center.setCursor(Qt.PointingHandCursor)
        btn_center.clicked.connect(self.reset_to_center)
        top.addWidget(btn_center)
        sum_lay.addLayout(top)

        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.metric_size = self._metric_tile(tr('lbl_size'))
        self.metric_pos = self._metric_tile(tr('lbl_offset'))
        self.metric_opac = self._metric_tile(tr('lbl_opac_metric'))
        for tile in (self.metric_size, self.metric_pos, self.metric_opac):
            tiles.addWidget(tile[0])
        sum_lay.addLayout(tiles)
        body.addWidget(summary)

        mon, mon_lay = make_card(spacing=10)
        mon_lay.addWidget(make_label(tr('lbl_monitor'), 'CardTitle'))
        mon_lay.addWidget(make_label(tr('lbl_monitor_desc'), 'Muted'))
        self.combo_monitors = QComboBox()
        self.populate_monitors()
        self.combo_monitors.currentIndexChanged.connect(self.on_monitor_changed)
        mon_lay.addWidget(self.combo_monitors)
        body.addWidget(mon)
        return page

    def _metric_tile(self, caption):
        tile = QFrame()
        tile.setObjectName('Tile')
        lay = QVBoxLayout(tile)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        lay.addWidget(make_label(caption, 'MetricLabel'))
        value = make_label('', 'Metric')
        lay.addWidget(value)
        return tile, value

    # Pagina de gestion y administracion de perfiles
    def build_page_presets(self):
        page, body = self.make_page(tr('page_presets_title'), tr('page_presets_sub'))

        cur, cur_lay = make_card(spacing=0, margins=(22, 18, 22, 18))
        row = QHBoxLayout()
        row.setSpacing(18)
        self.current_thumb = CrosshairThumb(76)
        row.addWidget(self.current_thumb, 0, Qt.AlignVCenter)
        txt = QVBoxLayout()
        txt.setSpacing(4)
        txt.addWidget(make_label(tr('lbl_current_config'), 'MetricLabel'))
        self.lbl_current_name = make_label('', 'CardTitle')
        txt.addWidget(self.lbl_current_name)
        self.lbl_current_summary = make_label('', 'Muted')
        self.lbl_current_summary.setTextFormat(Qt.RichText)
        txt.addWidget(self.lbl_current_summary)
        row.addLayout(txt, 1)
        btn_new = QPushButton(tr('btn_save_preset'))
        btn_new.setObjectName('Primary')
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.setFixedHeight(42)
        btn_new.clicked.connect(lambda checked=False: self.new_preset())
        row.addWidget(btn_new, 0, Qt.AlignVCenter)
        cur_lay.addLayout(row)
        body.addWidget(cur)

        lst, lst_lay = make_card(spacing=14)
        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(make_label(tr('lbl_your_presets'), 'CardTitle'))
        self.lbl_preset_count = make_label('', 'Muted')
        head.addWidget(self.lbl_preset_count)
        head.addStretch()
        btn_new_grp = QPushButton(tr('btn_new_group'))
        btn_new_grp.setCursor(Qt.PointingHandCursor)
        btn_new_grp.clicked.connect(self.create_group)
        head.addWidget(btn_new_grp)
        lst_lay.addLayout(head)

        self.presets_container = QWidget()
        self.presets_layout = QVBoxLayout(self.presets_container)
        self.presets_layout.setContentsMargins(0, 0, 0, 0)
        self.presets_layout.setSpacing(10)
        lst_lay.addWidget(self.presets_container)

        self.empty_state = QFrame()
        self.empty_state.setObjectName('EmptyState')
        el = QVBoxLayout(self.empty_state)
        el.setContentsMargins(24, 28, 24, 28)
        el.setSpacing(6)
        t = make_label(tr('lbl_no_presets_title'), 'CardTitle')
        t.setAlignment(Qt.AlignCenter)
        el.addWidget(t)
        d = make_label(tr('lbl_no_presets_desc'), 'Muted', wrap=True)
        d.setAlignment(Qt.AlignCenter)
        el.addWidget(d)
        lst_lay.addWidget(self.empty_state)
        body.addWidget(lst)
        return page

    # Seccion de modos de activacion manual y automatica
    def build_activation_section(self):
        section = QVBoxLayout()
        section.setSpacing(10)
        section.addWidget(make_label(tr('lbl_activation'), 'CardTitle'))
        section.addWidget(make_label(tr('lbl_activation_desc'), 'Muted'))
        section.addSpacing(2)

        manual_body = QWidget()
        mb = QVBoxLayout(manual_body)
        mb.setContentsMargins(0, 0, 0, 0)
        mb.setSpacing(8)
        mb.addWidget(make_label(tr('lbl_manual_hotkey'), 'Muted'))
        hk_row = QHBoxLayout()
        self.btn_hotkey = HotkeyRecorderButton(self.config.get('hotkey', 'F2'))
        self.btn_hotkey.hotkey_changed.connect(self.on_hotkey_changed)
        hk_row.addWidget(self.btn_hotkey)
        hk_row.addStretch()
        mb.addLayout(hk_row)
        self.lbl_hotkey_status = make_label('', 'Status', wrap=True)
        self.lbl_hotkey_status.setVisible(False)
        mb.addWidget(self.lbl_hotkey_status)

        auto_body = QWidget()
        ab = QVBoxLayout(auto_body)
        ab.setContentsMargins(0, 0, 0, 0)
        ab.setSpacing(10)
        ab.addWidget(make_label(tr('lbl_auto_desc'), 'Muted', wrap=True))
        btn_go_profiles = QPushButton(tr('btn_manage_presets'))
        btn_go_profiles.setObjectName('Primary')
        btn_go_profiles.setCursor(Qt.PointingHandCursor)
        btn_go_profiles.clicked.connect(lambda: self.switch_to_tab(TAB_PRESETS))
        btn_go_row = QHBoxLayout()
        btn_go_row.addWidget(btn_go_profiles)
        btn_go_row.addStretch()
        ab.addLayout(btn_go_row)

        self.mode_cards = {
            'manual': ModeCard(
                'manual', tr('mode_manual_title'), tr('mode_manual_desc'), manual_body,
                enabled=self.config.get('manual_enabled', True)),
            'auto': ModeCard(
                'auto', tr('mode_auto_title'), tr('mode_auto_desc'), auto_body,
                enabled=self.config.get('auto_enabled', False)),
        }
        for card in self.mode_cards.values():
            card.toggled.connect(self.on_activation_toggled)
            section.addWidget(card)
        return section

    def build_page_settings(self):
        page, body = self.make_page(tr('page_settings_title'), '')

        look, look_lay = make_card(spacing=14)
        look_lay.addWidget(make_label(tr('lbl_appearance'), 'CardTitle'))
        themes = QHBoxLayout()
        themes.setSpacing(14)
        current = get_current_theme()
        for key in ('dark', 'gray', 'light'):
            tc = ThemeCard(key, key == current)
            tc.clicked.connect(self.on_theme_selected)
            themes.addWidget(tc)
        look_lay.addLayout(themes)
        body.addWidget(look)

        body.addLayout(self.build_activation_section())
        body.addSpacing(6)

        card, lay = make_card(spacing=6)
        lay.addWidget(make_label(tr('lbl_background'), 'CardTitle'))
        lay.addSpacing(4)

        self.chk_tray = ToggleSwitch(self.config.get('close_to_tray', True))
        self.chk_tray.toggled.connect(self.on_tray_toggle)
        lay.addWidget(SettingRow(tr('lbl_tray'), tr('lbl_tray_desc'), self.chk_tray))
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f'background: {C["border"]};')
        lay.addWidget(line)
        self.chk_startup = ToggleSwitch(is_startup_enabled())
        self.chk_startup.toggled.connect(self.on_startup_toggle)
        lay.addWidget(SettingRow(tr('lbl_startup'), tr('lbl_startup_desc'), self.chk_startup))
        body.addWidget(card)

        # Language selector
        lang_card, lang_lay = make_card(spacing=14)
        lang_lay.addWidget(make_label(tr('lbl_language'), 'CardTitle'))
        lang_lay.addWidget(make_label(tr('lbl_language_desc'), 'Muted'))
        self.combo_language = QComboBox()
        for code, native_name in LANGUAGES:
            self.combo_language.addItem(native_name, code)
        self.combo_language.setCurrentIndex(
            max(0, self.combo_language.findData(get_language())))
        self.combo_language.currentIndexChanged.connect(self.on_language_index_changed)
        lang_lay.addWidget(self.combo_language)
        body.addWidget(lang_card)

        return page

    def refresh_all(self):
        self.update_tray_action()
        self.update_summary()
        self.update_mode_cards()
        self.update_hotkey_labels()
        self.update_preview()

    def update_tray_action(self):
        on = self.config.get('manual_active', True)
        self.act_toggle.setText(tr('tray_hide') if on else tr('tray_show_crosshair'))
        self.update_active_button()

    def update_active_button(self):
        if hasattr(self, 'btn_toggle_crosshair'):
            key = 'btn_disable_crosshair' if self.config.get('manual_active', True) else 'btn_enable_crosshair'
            self.btn_toggle_crosshair.setText(tr(key))

    def update_summary(self):
        size = self.config.get('size', 48)
        ox, oy = self.config.get('offset_x', 0), self.config.get('offset_y', 0)
        self.metric_size[1].setText(f'{size} px')
        self.metric_pos[1].setText(f'X {ox:+d} · Y {oy:+d}')
        self.metric_opac[1].setText(f"{int(round(self.config.get('opacity', 1.0) * 100))}%")
        sw, sh = self.current_screen_size()
        self.monitor_map.set_state(sw, sh, ox, oy, size)
        self.update_preset_state()

    def update_mode_cards(self):
        self.mode_cards['manual'].set_activation_enabled(
            self.config.get('manual_enabled', True))
        self.mode_cards['auto'].set_activation_enabled(
            self.config.get('auto_enabled', False))

    def update_hotkey_labels(self):
        manual_enabled = self.config.get('manual_enabled', True)
        hotkey = self.config.get('hotkey', 'F2')
        if hasattr(self, 'btn_hotkey'):
            self.btn_hotkey.set_hotkey(hotkey)
        self.lbl_hotkey_status.setText(
            '' if (not manual_enabled or self.hotkey_ok) else tr('hotkey_error'))
        self.lbl_hotkey_status.setVisible(bool(self.lbl_hotkey_status.text()))

    def update_preview(self):
        name = self.config.get('crosshair_file', '')
        self.preview.set_image(resolve_crosshair_path(name))
        self.preview.set_color(self.config.get('color', 'original'))
        self.preview.set_opacity(self.config.get('opacity', 1.0))
        self.lbl_mira_name.setText(os.path.splitext(name)[0] if name else tr('lbl_no_crosshair'))
        self.lbl_opac_val.setText(f"{int(round(self.config.get('opacity', 1.0) * 100))}%")
        self.update_color_ui()
        self.update_gallery_color()
        self.update_preset_state()

    def update_color_ui(self):
        if hasattr(self, 'color_picker'):
            self.color_picker.set_color(self.config.get('color', 'original'))

    def set_crosshair_color(self, color_hex):
        color_hex = color_hex or 'original'
        self.config['color'] = color_hex
        self._remember_current_crosshair()
        self.overlay.update_params(color=color_hex)
        self.preview.set_color(color_hex)
        self.update_gallery_color()
        self.update_summary()
        self.persist()

    # Todas las miras de la biblioteca se muestran con el color que se está probando
    def update_gallery_color(self):
        color = self.config.get('color', 'original')
        for card in self.cards.values():
            card.set_color(color)

    # Valores visuales que usa la mira ahora mismo
    def current_values(self):
        return {
            'crosshair_file': self.config.get('crosshair_file', ''),
            'size': self.config.get('size', 48),
            'offset_x': self.config.get('offset_x', 0),
            'offset_y': self.config.get('offset_y', 0),
            'opacity': self.config.get('opacity', 1.0),
            'color': self.config.get('color', 'original'),
        }

    # Almacenamiento temporal de ajustes para la mira seleccionada
    def _remember_current_crosshair(self):
        cur = self.config.get('crosshair_file')
        if cur:
            vals = self.current_values()
            vals.pop('crosshair_file')
            self.config.setdefault('crosshair_configs', {})[cur] = vals

    def current_screen_size(self):
        screens = QApplication.screens()
        if not screens:
            return 1920, 1080
        idx = max(0, min(self.config.get('monitor_index', 0), len(screens) - 1))
        geo = screens[idx].geometry()
        return geo.width(), geo.height()

    def notify(self, text, ms=3500):
        self.statusBar().showMessage(text, ms)

    # Lanzamiento y gestion del editor en pantalla completa
    def open_editor(self):
        if self.editing:
            return
        self.editing = True
        self._restore_window = self.isVisible()
        self.hide()
        self.overlay.hide()
        QTimer.singleShot(300, self._launch_editor)  # Espera a que la ventana desaparezca antes de capturar

    def _launch_editor(self, values=None, image_file=None):
        try:
            screens = QApplication.screens()
            idx = max(0, min(self.config.get('monitor_index', 0), len(screens) - 1))
            screen = screens[idx]
            try:
                if self._external_editor is None:
                    self.hide()
                self.overlay.hide()
                QApplication.processEvents()
                shot = screen.grabWindow(0)
            except Exception:
                shot = None

            if values is None:
                values = {k: self.config[k] for k in ('size', 'offset_x', 'offset_y', 'opacity', 'color')}
            if image_file is None:
                image_file = self.config.get('crosshair_file', '')
            self.editor = CrosshairEditor(
                self,
                screen=screen,
                image_path=resolve_crosshair_path(image_file),
                values=values,
                background=shot,
                bg_mode=self.config.get('editor_background', 'screenshot'),
                guides=self.config.get('editor_guides', True),
            )
            self.editor.present()
            if self.editor.exec_() == QDialog.Accepted and self.editor.result_values:
                self.on_editor_saved(self.editor.result_values)
            self.on_editor_closed()
        except Exception as e:
            self.editor = None
            self.on_editor_closed()
            QMessageBox.warning(self, "Akro's CrossHair", f'No se pudo abrir el editor:\n{e}')

    # Apertura del editor para calibrar los valores de un estado
    def edit_values_on_screen(self, values, image_file, on_saved, on_closed):
        if self.editing:
            return False
        self._external_editor = (on_saved, on_closed)
        self.editing = True
        self._restore_window = False
        self.setWindowOpacity(0.0)
        self.overlay.hide()
        QTimer.singleShot(300, lambda: self._launch_editor(values, image_file))
        return True

    def on_editor_saved(self, values):
        if self._external_editor is not None:
            for key in ('editor_background', 'editor_guides'):
                if key in values:
                    self.config[key] = values[key]
            self.persist()
            self._external_editor[0](values)
            return
        self.config.update(values)
        self._remember_current_crosshair()
        self.overlay.update_params(size=values['size'], offset_x=values['offset_x'],
                                   offset_y=values['offset_y'], opacity=values['opacity'],
                                   color=values.get('color'))
        self.opac_slider.blockSignals(True)
        self.opac_slider.setValue(int(round(values['opacity'] * 100)))
        self.opac_slider.blockSignals(False)
        self.persist()
        self.update_summary()
        self.update_preview()
        self.notify('Tamaño y posición guardados')

    def on_editor_closed(self):
        self.editor = None
        self.editing = False
        external, self._external_editor = self._external_editor, None
        self.setWindowOpacity(1.0)
        if self._restore_window:
            self.show_and_activate()
        if external is not None:
            external[1]()
        else:
            self.apply_visibility()

    def toggle_active_state(self):
        self.config['manual_active'] = not self.config.get('manual_active', True)
        self.persist()
        self.update_tray_action()
        self.apply_visibility()

    # Reaccion al presionar el atajo global
    def on_hotkey_pressed(self):
        now = time.monotonic()
        if now - self._last_hotkey < 0.25:  # Evita rebotes si la tecla se mantiene pulsada
            return
        self._last_hotkey = now
        if self.config.get('manual_enabled', True):
            self.config['manual_active'] = not self.config.get('manual_active', True)
            self.persist()
            self.update_tray_action()
            self.apply_visibility()

    def on_tick(self):
        self._tick += 1
        self.check_auto_activation()
        if self._tick % 4 == 0 and not self.editing:
            self.overlay.keep_on_top()

    # Aplica el perfil correspondiente a la aplicacion activa en primer plano
    def detect_auto_preset(self):
        autos = [p for p in self.config.get('presets', []) if p['auto_apply'] and p['app']]
        if not autos:
            self._last_auto_target = None
            return None
        is_self, target = match_foreground([p['app'] for p in autos])
        # Preservacion de ajustes manuales mientras la ventana de la aplicacion esta activa
        if is_self:
            return None
        if target is None:
            self._last_auto_target = None
            return None
        preset = next(p for p in autos if p['app'] == target)
        if target != self._last_auto_target:
            self._last_auto_target = target
            self.apply_preset(preset)
        return preset

    # Visibilidad de la mira segun la aplicacion detectada
    def check_auto_activation(self):
        self.apply_visibility()

    # Determinacion de visibilidad segun el modo manual o automatico coincidente
    def apply_visibility(self):
        if self.editing:
            self.overlay.hide()
            return
        manual_visible = self.config.get('manual_active', True)
        auto_visible = (
            self.config.get('auto_enabled', False)
            and self.detect_auto_preset() is not None
        )
        if manual_visible or auto_visible:
            self.overlay.show()
        else:
            self.overlay.hide()

    def on_activation_toggled(self, mode, enabled):
        config_key = f'{mode}_enabled'
        if self.config.get(config_key, False) == enabled:
            return
        self.config[config_key] = enabled
        if mode == 'manual':
            if enabled:
                self.hotkey_ok = self.hotkey_mgr.set_hotkey(self.config.get('hotkey', 'F2'))
            else:
                self.hotkey_mgr.clear_hotkey()
                self.hotkey_ok = True
        self.persist()
        self.update_mode_cards()
        self.update_hotkey_labels()
        self.apply_visibility()

    def on_hotkey_changed(self, key_str):
        key_str = key_str.strip()
        self.config['hotkey'] = key_str
        self.persist()
        if self.config.get('manual_enabled', True):
            self.hotkey_ok = self.hotkey_mgr.set_hotkey(key_str)
        self.update_hotkey_labels()

    def on_opacity_changed(self, val):
        opac = val / 100.0
        self.config['opacity'] = opac
        self._remember_current_crosshair()
        self.overlay.update_params(opacity=opac)
        self.persist()
        self.update_summary()
        self.update_preview()

    def reset_to_center(self):
        self.config['offset_x'] = 0
        self.config['offset_y'] = 0
        self._remember_current_crosshair()
        self.overlay.center_on_screen()
        self.persist()
        self.update_summary()
        self.notify('Mira centrada en la pantalla')

    def on_monitor_changed(self, idx):
        if idx < 0:
            return
        self.config['monitor_index'] = idx
        self.overlay.update_params(monitor_idx=idx)
        self.persist()
        self.update_summary()

    def populate_monitors(self):
        self.combo_monitors.blockSignals(True)
        self.combo_monitors.clear()
        screens = QApplication.screens()
        for i, s in enumerate(screens):
            geo = s.geometry()
            tag = ' (principal)' if s == QApplication.primaryScreen() else ''
            self.combo_monitors.addItem(f'Monitor {i + 1} · {geo.width()}×{geo.height()}{tag}')
        idx = min(self.config.get('monitor_index', 0), len(screens) - 1)
        self.combo_monitors.setCurrentIndex(max(0, idx))
        self.combo_monitors.blockSignals(False)

    # Metodos para crear aplicar duplicar y gestionar perfiles
    def _preset_by_id(self, pid):
        return next((p for p in self.config.get('presets', []) if p['id'] == pid), None)

    def _defer(self, fn):
        QTimer.singleShot(0, fn)

    def refresh_presets(self):
        if not hasattr(self, 'presets_layout'):
            return
        while self.presets_layout.count():
            item = self.presets_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.preset_cards.clear()
        presets = self.config.get('presets', [])
        groups = self.config.get('preset_groups', ['General'])
        if not groups:
            groups = ['General']
            self.config['preset_groups'] = groups

        for p in presets:
            grp = p.get('group', 'General')
            if grp not in groups:
                groups.append(grp)

        for grp in groups:
            grp_presets = [p for p in presets if p.get('group', 'General') == grp]

            group_frame = QFrame()
            group_frame.setObjectName('Tile')
            gf_lay = QVBoxLayout(group_frame)
            gf_lay.setContentsMargins(14, 12, 14, 14)
            gf_lay.setSpacing(10)

            gh = QHBoxLayout()
            gh.setSpacing(10)
            lbl_title = QLabel(grp)
            lbl_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {C['strong']};")
            gh.addWidget(lbl_title)

            lbl_count = QLabel(f"({len(grp_presets)})")
            lbl_count.setStyleSheet(f"color: {C['muted']}; font-size: 12px;")
            gh.addWidget(lbl_count)
            gh.addStretch()

            btn_add_p = QPushButton(tr('preset_add_button'))
            btn_add_p.setCursor(Qt.PointingHandCursor)
            btn_add_p.setStyleSheet("padding: 4px 10px; font-size: 11px;")
            btn_add_p.clicked.connect(lambda checked=False, g=grp: self.new_preset(default_group=g))
            gh.addWidget(btn_add_p)

            btn_ren = QPushButton(tr('group_rename'))
            btn_ren.setCursor(Qt.PointingHandCursor)
            btn_ren.setStyleSheet("padding: 4px 10px; font-size: 11px;")
            btn_ren.clicked.connect(lambda checked=False, g=grp: self.rename_group(g))
            gh.addWidget(btn_ren)

            if len(groups) > 1:
                btn_del = QPushButton(tr('group_delete'))
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setStyleSheet(f"padding: 4px 10px; font-size: 11px; color: {C['danger']};")
                btn_del.clicked.connect(lambda checked=False, g=grp: self.delete_group(g))
                gh.addWidget(btn_del)

            gf_lay.addLayout(gh)

            for p in grp_presets:
                card = PresetCard(p, groups=groups)
                card.apply_requested.connect(self.apply_preset_by_id)
                card.edit_requested.connect(self.edit_preset)
                card.update_requested.connect(self.update_preset_from_current)
                card.duplicate_requested.connect(self.duplicate_preset)
                card.delete_requested.connect(self.delete_preset)
                card.auto_toggled.connect(self.set_preset_auto)
                card.states_requested.connect(self.edit_states)
                card.move_group_requested.connect(self.move_preset_group)
                gf_lay.addWidget(card)
                self.preset_cards[p['id']] = card

            self.presets_layout.addWidget(group_frame)

        n = len(presets)
        count_key = 'preset_count_one' if n == 1 else 'preset_count_many'
        self.lbl_preset_count.setText(
            '' if not n else tr(count_key).format(count=n))
        self.presets_container.setVisible(bool(n or len(groups) > 0))
        self.empty_state.setVisible(not n and len(groups) <= 1)
        self.update_preset_state()

    # Perfil en uso y variantes dinamicas activadas por control
    @staticmethod
    def _preset_matches(p, cur):
        return same_visuals(p, cur) or any(same_visuals(st, cur) for st in p.get('states', []))

    # Consulta del perfil cuyos ajustes estan activos en pantalla
    def current_preset(self):
        cur = self.current_values()
        active = self._preset_by_id(self.active_preset_id) if self.active_preset_id else None
        if active is not None and self._preset_matches(active, cur):
            return active
        return next((p for p in self.config.get('presets', []) if same_visuals(p, cur)), None)

    # Identificacion del estado o variante aplicado actualmente
    def current_state(self, preset):
        if preset is None or self.active_state_id is None:
            return None
        cur = self.current_values()
        st = next((x for x in preset.get('states', []) if x['id'] == self.active_state_id), None)
        return st if st is not None and same_visuals(st, cur) else None

    # Actualizacion del perfil activo y refresco de su tarjeta visual
    def update_preset_state(self):
        if not hasattr(self, 'current_thumb'):
            return
        cur = self.current_values()
        match = self.current_preset()
        for p in self.config.get('presets', []):
            card = self.preset_cards.get(p['id'])
            if card is not None:
                card.set_in_use(match is not None and p['id'] == match['id'])
        state = self.current_state(match)
        self.current_thumb.set_values(cur)
        if match is None:
            self.lbl_current_name.setText(tr('preset_current_unsaved'))
        elif state is not None:
            self.lbl_current_name.setText(
                tr('preset_current_state').format(preset=match['name'], state=state['name']))
        else:
            self.lbl_current_name.setText(tr('preset_current').format(name=match['name']))
        self.lbl_current_summary.setText(describe_values(cur))
        self.sync_state_bindings(match)

    # Registro de atajos para los estados del perfil en uso
    def sync_state_bindings(self, preset):
        usable = [st for st in (preset.get('states', []) if preset else []) if st.get('hotkey')]
        sig = (preset.get('id') if (usable and preset) else None,
               tuple((st.get('id', ''), st.get('hotkey', ''), st.get('mode', 'hold')) for st in usable))
        if sig == self._bound_sig:
            return
        self._bound_sig = sig
        if not usable:
            self.state_watcher.clear()
            return
        ok = self.state_watcher.set_bindings([(st.get('id', ''), st.get('hotkey', '')) for st in usable])
        bad = [st.get('name', tr('state_default_name')) for st in usable if not ok.get(st.get('id', ''))]
        if bad:
            self.notify(tr('state_binding_error').format(names=', '.join(bad)), 7000)

    def _input_blocked(self):
        recording = hasattr(self, 'btn_hotkey') and self.btn_hotkey.recording
        return self.editing or recording or QApplication.activeModalWidget() is not None

    # Notificacion de cambio de estado recibida desde el hilo de vigilancia
    def on_state_event(self, state_id, pressed):
        preset = self.current_preset()
        if preset is None:
            return
        st = next((x for x in preset.get('states', []) if x.get('id') == state_id), None)
        if st is None:
            return
        active = self.current_state(preset)
        is_active = active is not None and active.get('id') == st.get('id')
        if st.get('mode', 'hold') == 'hold':
            if pressed and not is_active and not self._input_blocked():
                self.enter_state(preset, st)
            elif not pressed and is_active:
                self.leave_state(preset)
        elif pressed and not self._input_blocked():
            if is_active:
                self.leave_state(preset)
            else:
                self.enter_state(preset, st)

    def enter_state(self, preset, state):
        self.active_preset_id = preset.get('id')
        self.active_state_id = state.get('id')
        self._apply_values(state, persist=False)

    def leave_state(self, preset):
        self.active_preset_id = preset.get('id')
        self.active_state_id = None
        self._apply_values(preset, persist=False)

    # Restauracion de la mira principal al iniciar si habia un estado activo
    def _normalize_startup_state(self):
        cur = self.current_values()
        presets = self.config.get('presets', [])
        if any(same_visuals(p, cur) for p in presets):
            return
        for p in presets:
            if any(same_visuals(st, cur) for st in p.get('states', [])):
                self.apply_preset(p)
                return

    def edit_states(self, pid):
        p = self._preset_by_id(pid)
        if p is None:
            return
        reserved = {}
        if self.config.get('manual_enabled', True) and self.config.get('hotkey'):
            reserved[normalize_hotkey(self.config['hotkey'])] = tr('state_reserved_global_hotkey')
        dlg = StatesDialog(self, p, self.list_crosshairs(), self.current_values(), reserved, self.edit_values_on_screen)
        if dlg.exec_() == QDialog.Accepted and dlg.result_states is not None:
            p['states'] = dlg.result_states
            self._bound_sig = None
            self.persist()
            self.sync_state_bindings(p)
            self._defer(self.refresh_presets)
            n = len(p['states'])
            self.notify(tr('states_saved').format(name=p['name']) + (f' ({n})' if n else ''))

    def _unique_name(self, base):
        names = {p['name'].lower() for p in self.config.get('presets', [])}
        if base.lower() not in names:
            return base
        n = 2
        while f'{base} ({n})'.lower() in names:
            n += 1
        return f'{base} ({n})'

    def create_group(self):
        name, ok = QInputDialog.getText(self, tr('dialog_new_group_title'), tr('dialog_new_group_prompt'))
        if ok and name and name.strip():
            name = name.strip()
            groups = self.config.setdefault('preset_groups', ['General'])
            if name in groups:
                QMessageBox.warning(
                    self, "Akro's CrossHair", tr('group_exists').format(name=name))
                return
            groups.append(name)
            self.persist()
            self.refresh_presets()
            self.notify(tr('group_created').format(name=name))

    def rename_group(self, old_name):
        new_name, ok = QInputDialog.getText(self, tr('dialog_rename_group_title'), tr('dialog_rename_group_prompt'), text=old_name)
        if ok and new_name and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            groups = self.config.setdefault('preset_groups', ['General'])
            if new_name in groups:
                QMessageBox.warning(
                    self, "Akro's CrossHair", tr('group_name_exists').format(name=new_name))
                return
            idx = groups.index(old_name)
            groups[idx] = new_name
            for p in self.config.get('presets', []):
                if p.get('group', 'General') == old_name:
                    p['group'] = new_name
            self.persist()
            self.refresh_presets()
            self.notify(tr('group_renamed').format(name=new_name))

    def delete_group(self, group_name):
        if not ask_yes_no(
                self, tr('group_delete'), tr('group_delete_question').format(name=group_name)):
            return
        groups = self.config.setdefault('preset_groups', ['General'])
        if group_name in groups:
            groups.remove(group_name)
        if 'General' not in groups:
            groups.insert(0, 'General')
        for p in self.config.get('presets', []):
            if p.get('group') == group_name:
                p['group'] = 'General'
        self.persist()
        self.refresh_presets()
        self.notify(tr('group_deleted').format(name=group_name))

    def move_preset_group(self, pid, target_group):
        p = self._preset_by_id(pid)
        if p is None:
            return
        p['group'] = target_group
        self.persist()
        self.refresh_presets()
        self.notify(tr('preset_moved').format(name=p['name'], group=target_group))

    def new_preset(self, default_group='General'):
        presets = self.config.setdefault('presets', [])
        groups = self.config.get('preset_groups', ['General'])
        dlg = PresetDialog(self, self.current_values(), existing=presets,
                           default_name=self._unique_name(
                               f'{tr("preset_default_name")} {len(presets) + 1}'),
                           groups=groups, default_group=default_group)
        if dlg.exec_() == QDialog.Accepted and dlg.result_preset:
            presets.append(dlg.result_preset)
            self._last_auto_target = None
            self.persist()
            self.refresh_presets()
            self.notify(tr('preset_saved').format(name=dlg.result_preset['name']))

    def edit_preset(self, pid, enable_auto=False):
        p = self._preset_by_id(pid)
        if p is None:
            return
        others = [x for x in self.config['presets'] if x['id'] != pid]
        groups = self.config.get('preset_groups', ['General'])
        dlg = PresetDialog(self, self.current_values(), preset=p, existing=others, enable_auto=enable_auto, groups=groups)
        if dlg.exec_() == QDialog.Accepted and dlg.result_preset:
            idx = self.config['presets'].index(p)
            self.config['presets'][idx] = dlg.result_preset
            self._last_auto_target = None
            self.persist()
            self.refresh_presets()
            self.notify(tr('preset_updated').format(name=dlg.result_preset['name']))

    def update_preset_from_current(self, pid):
        p = self._preset_by_id(pid)
        if p is None:
            return
        p.update(self.current_values())
        self.persist()
        self._defer(self.refresh_presets)
        self.notify(tr('preset_updated_current').format(name=p['name']))

    def duplicate_preset(self, pid):
        p = self._preset_by_id(pid)
        if p is None:
            return
        clone = copy.deepcopy(p)
        clone.update(id=new_preset_id(),
                     name=self._unique_name(f'{p["name"]} {tr("preset_copy_suffix")}'),
                     auto_apply=False)
        self.config['presets'].append(clone)
        self.persist()
        self._defer(self.refresh_presets)
        self.notify(tr('preset_duplicated').format(name=clone['name']))

    def delete_preset(self, pid):
        p = self._preset_by_id(pid)
        if p is None:
            return
        if not ask_yes_no(self, tr('preset_delete_title'),
                          tr('preset_delete_question').format(name=p['name'], warning=tr('common_undo_warning'))):
            return
        self.config['presets'].remove(p)
        self._last_auto_target = None
        self.persist()
        self._defer(self.refresh_presets)
        self.notify(tr('preset_deleted').format(name=p['name']))

    def apply_preset_by_id(self, pid):
        p = self._preset_by_id(pid)
        if p is not None:
            self.apply_preset(p)
            self.notify(tr('preset_applied').format(name=p['name']))

    # Conmutacion de aplicacion automatica desde una tarjeta de perfil
    def set_preset_auto(self, pid, on):
        p = self._preset_by_id(pid)
        if p is None:
            return
        if on:
            if not p['app']:  # Hace falta saber a que aplicacion asociarlo
                self._defer(lambda: (self.refresh_presets(), self.edit_preset(pid, enable_auto=True)))
                return
            clash = next((x for x in self.config['presets']
                          if x['id'] != pid and x['auto_apply'] and x['app'].lower() == p['app'].lower()), None)
            if clash:
                QMessageBox.information(
                    self, "Akro's CrossHair",
                    tr('preset_auto_conflict').format(name=clash['name'], app=p['app']))
                self._defer(self.refresh_presets)
                return
        p['auto_apply'] = on
        self._last_auto_target = None
        self.persist()
        self._defer(self.refresh_presets)
        key = 'preset_auto_enabled' if on else 'preset_auto_disabled'
        self.notify(tr(key).format(name=p['name']))

    # Carga de un perfil en la mira y en la interfaz grafica
    def apply_preset(self, p):
        self.active_preset_id = p['id']
        self.active_state_id = None
        self._apply_values(p)

    # Aplicacion de parametros visuales a la mira y sincronizacion con la ventana
    def _apply_values(self, p, persist=True):
        mira = p.get('crosshair_file') or self.config.get('crosshair_file', '')
        if not resolve_crosshair_path(mira):
            mira = self.config.get('crosshair_file', '')
        sz = p.get('size', self.config.get('size', 48))
        ox = p.get('offset_x', self.config.get('offset_x', 0))
        oy = p.get('offset_y', self.config.get('offset_y', 0))
        op = p.get('opacity', self.config.get('opacity', 1.0))
        col = p.get('color', self.config.get('color', 'original'))
        self.config.update({
            'crosshair_file': mira, 'size': sz, 'offset_x': ox,
            'offset_y': oy, 'opacity': op, 'color': col,
        })
        self.overlay.update_params(image_file=mira, size=sz, offset_x=ox,
                                   offset_y=oy, opacity=op, color=col)
        if hasattr(self, 'opac_slider'):
            self.opac_slider.blockSignals(True)
            self.opac_slider.setValue(int(round(op * 100)))
            self.opac_slider.blockSignals(False)
        for fn, card in self.cards.items():
            card.set_selected(fn == mira)
        self.update_preview()
        self.update_summary()
        if persist:
            self.persist()

    def switch_to_tab(self, index):
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)
            self.stack.setCurrentIndex(index)

    # Opciones de configuracion general y preferencias
    def on_tray_toggle(self, checked):
        self.config['close_to_tray'] = checked
        self.persist()

    def on_startup_toggle(self, checked):
        if set_startup_enabled(checked):
            self.config['start_with_windows'] = checked
            self.persist()
            self.notify('Inicio con Windows ' + ('activado' if checked else 'desactivado'))
        else:
            self.chk_startup.blockSignals(True)
            self.chk_startup.setChecked(not checked)
            self.chk_startup.blockSignals(False)
            QMessageBox.warning(self, "Akro's CrossHair", 'No se pudo cambiar el inicio automático de Windows.')

    def on_theme_selected(self, key):
        if key != get_current_theme():
            self._defer(lambda: self.apply_theme(key))

    # Cambia el tema y reconstruye la interfaz con los nuevos colores
    def apply_theme(self, name):
        if name not in THEMES:
            return
        index = self.stack.currentIndex()
        self.setUpdatesEnabled(False)
        try:
            set_theme(name)
            self.config['theme'] = name
            QApplication.instance().setStyleSheet(build_stylesheet())
            self._build_central(index)
            self.refresh_gallery()
            self.refresh_presets()
            self.refresh_all()
        finally:
            self.setUpdatesEnabled(True)
        self.persist()
        self.notify(tr('theme_applied').format(theme=tr(f'theme_{name}').lower()))

    def on_language_selected(self, code):
        if code == self.config.get('language', 'es'):
            return
        self._defer(lambda: self.apply_language(code))

    def on_language_index_changed(self, index):
        if index >= 0:
            self.on_language_selected(self.combo_language.itemData(index))

    def apply_language(self, code):
        index = self.stack.currentIndex()
        self.setUpdatesEnabled(False)
        try:
            set_language(code)
            self.config['language'] = code
            self._build_central(index)
            self.refresh_gallery()
            self.refresh_presets()
            self.refresh_all()
        finally:
            self.setUpdatesEnabled(True)
        self.persist()

    # Gestion de la coleccion de miras y carga de archivos
    def list_crosshairs(self):
        os.makedirs(CROSSHAIRS_DIR, exist_ok=True)
        def _nat(name):
            parts = re.split(r'(\d+)', name.lower())
            return [int(p) if p.isdigit() else p for p in parts]
        return [f for f in sorted(os.listdir(CROSSHAIRS_DIR), key=_nat) if f.lower().endswith(IMAGE_EXTS)]

    # Seleccion de la primera mira disponible si la guardada no existe
    def ensure_valid_crosshair(self):
        if resolve_crosshair_path(self.config.get('crosshair_file', '')):
            return
        files = self.list_crosshairs()
        if files:
            self.config['crosshair_file'] = files[0]
            self.overlay.update_params(image_file=files[0])
            self.persist()

    def refresh_gallery(self):
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()

        files = self.list_crosshairs()
        selected = self.config.get('crosshair_file', '')
        for fn in files:
            card = CrosshairCard(fn, os.path.join(CROSSHAIRS_DIR, fn), fn == selected,
                            color=self.config.get('color', 'original'))
            card.clicked.connect(self.select_crosshair)
            card.delete_requested.connect(self.delete_crosshair)
            self.gallery_layout.addWidget(card)
            self.cards[fn] = card
        self.lbl_count.setText(f'{len(files)} disponibles')
        self.lbl_empty.setVisible(not files)
        self.gallery_widget.updateGeometry()

    def select_crosshair(self, filename):
        self.config['crosshair_file'] = filename
        self.persist()
        for fn, card in self.cards.items():
            card.set_selected(fn == filename)
        self.overlay.update_params(
            image_file=filename,
            size=self.config['size'],
            offset_x=self.config['offset_x'],
            offset_y=self.config['offset_y'],
            opacity=self.config['opacity'],
            color=self.config['color']
        )
        if hasattr(self, 'opac_slider'):
            self.opac_slider.blockSignals(True)
            self.opac_slider.setValue(int(round(self.config['opacity'] * 100)))
            self.opac_slider.blockSignals(False)
        self.update_preview()
        self.update_summary()

    def import_custom_crosshair(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Seleccionar imagen de mira', '',
            'Imágenes PNG (*.png)')
        if not path:
            return
        if not path.lower().endswith(IMAGE_EXTS):
            QMessageBox.warning(self, "Akro's CrossHair", 'Solo se admiten imágenes en formato PNG (.png).')
            return
        # Validacion del formato y cabecera de la imagen seleccionada
        reader = QImageReader(path)
        if bytes(reader.format()).lower() != b'png' or QPixmap(path).isNull():
            QMessageBox.warning(self, "Akro's CrossHair",
                                'No se pudo leer esa imagen. Comprueba que sea un archivo PNG válido.')
            return
        try:
            os.makedirs(CROSSHAIRS_DIR, exist_ok=True)
            base, ext = os.path.splitext(os.path.basename(path))
            dest_name, n = base + ext, 2
            while os.path.exists(os.path.join(CROSSHAIRS_DIR, dest_name)):
                dest_name = f'{base} ({n}){ext}'  # Nunca pisa una mira existente
                n += 1
            shutil.copy2(path, os.path.join(CROSSHAIRS_DIR, dest_name))
            self.refresh_gallery()
            self.select_crosshair(dest_name)
            self.notify(f'Mira añadida: {dest_name}')
        except Exception as e:
            QMessageBox.warning(self, "Akro's CrossHair", f'No se pudo importar la imagen:\n{e}')

    def delete_crosshair(self, filename):
        if not ask_yes_no(self, 'Eliminar mira',
                          f'¿Eliminar «{filename}» de la biblioteca?\nEsta acción no se puede deshacer.'):
            return
        try:
            os.remove(os.path.join(CROSSHAIRS_DIR, filename))
        except Exception as e:
            QMessageBox.warning(self, "Akro's CrossHair", f'No se pudo eliminar:\n{e}')
            return
        remaining = self.list_crosshairs()
        if self.config.get('crosshair_file') == filename:
            self.config['crosshair_file'] = remaining[0] if remaining else ''
            self.overlay.update_params(image_file=self.config['crosshair_file'])
        self.refresh_gallery()
        self.update_preview()
        self.persist()
        self.notify('Mira eliminada')

    # Eventos de cierre y liberacion de recursos
    def closeEvent(self, event):
        if self.config.get('close_to_tray', True) and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray_icon.showMessage(
                    "Akro's CrossHair", 'Sigue activa junto al reloj. Haz clic en el icono para abrirla.',
                    QSystemTrayIcon.Information, 2500)
        else:
            self.force_exit()
            event.accept()
