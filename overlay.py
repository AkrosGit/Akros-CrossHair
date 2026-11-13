# Ventana superpuesta transparente para renderizar la mira en pantalla
import os
import shutil
import sys
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPixmap, QColor
from config_manager import APP_DATA_DIR

IS_WINDOWS = sys.platform == 'win32'
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1

_BUNDLED_CROSSHAIRS_DIR = os.path.join(
    getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))),
    'crosshairs')
if getattr(sys, 'frozen', False):
    CROSSHAIRS_DIR = os.path.join(APP_DATA_DIR, 'crosshairs')
else:
    CROSSHAIRS_DIR = _BUNDLED_CROSSHAIRS_DIR
MIN_SIZE = 8
MAX_SIZE = 400


def prepare_crosshair_assets():
    if os.path.isdir(CROSSHAIRS_DIR):
        return
    os.makedirs(CROSSHAIRS_DIR, exist_ok=True)
    if not getattr(sys, 'frozen', False):
        return
    for filename in os.listdir(_BUNDLED_CROSSHAIRS_DIR):
        if not filename.lower().endswith('.png'):
            continue
        destination = os.path.join(CROSSHAIRS_DIR, filename)
        if not os.path.exists(destination):
            shutil.copy2(os.path.join(_BUNDLED_CROSSHAIRS_DIR, filename), destination)


# Resolucion de la ruta absoluta o relativa de la mira
def resolve_crosshair_path(filename_or_path):
    if not filename_or_path:
        return ''
    if os.path.isabs(filename_or_path) and os.path.exists(filename_or_path):
        return filename_or_path
    full = os.path.join(CROSSHAIRS_DIR, filename_or_path)
    return full if os.path.exists(full) else ''


# Colorea la silueta de la imagen manteniendo sus transparencias
def colorize_pixmap(pix, color_hex):
    if not pix or pix.isNull() or not color_hex or color_hex.lower() in ('none', 'original', ''):
        return pix
    colored = QPixmap(pix.size())
    colored.fill(Qt.transparent)
    colored.setDevicePixelRatio(pix.devicePixelRatio())
    p = QPainter(colored)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    p.drawPixmap(0, 0, pix)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(colored.rect(), QColor(color_hex))
    p.end()
    return colored


# Imagen de la mira escalada con soporte para color personalizado
def load_crosshair_pixmap(path, size, dpr=1.0, color=None):
    if not path:
        return None
    raw = QPixmap(path)
    if raw.isNull():
        return None
    px_size = max(1, int(round(size * dpr)))
    pix = raw.scaled(px_size, px_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pix.setDevicePixelRatio(dpr)
    if color and color.lower() not in ('none', 'original', ''):
        pix = colorize_pixmap(pix, color)
    return pix


# Calculo del origen de la mira respecto a las dimensiones de pantalla
def crosshair_origin(screen_w, screen_h, size, offset_x, offset_y):
    return (screen_w - size) // 2 + offset_x, (screen_h - size) // 2 + offset_y


# Ventana transparente para la mira en pantalla
class CrosshairOverlay(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.pixmap = None
        self.image_path = ''
        self.dpr = 1.0
        self.size_val = max(MIN_SIZE, min(MAX_SIZE, int(config.get('size', 48))))
        self.offset_x = config.get('offset_x', 0)
        self.offset_y = config.get('offset_y', 0)
        self.opacity_val = config.get('opacity', 1.0)
        self.color_val = config.get('color', 'original')
        self.monitor_idx = config.get('monitor_index', 0)

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.apply_win_styles()
        self.load_image(config.get('crosshair_file', 'crosshair.png'))
        self.reposition()

    # Aplicacion de estilos nativos para permitir clics a traves de la ventana
    def apply_win_styles(self):
        if not IS_WINDOWS:
            return
        try:
            hwnd = int(self.winId())
            user = ctypes.windll.user32
            curr = user.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                curr | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
        except Exception:
            pass

    # Posicionamiento prioritario sobre otras ventanas activas
    def keep_on_top(self):
        if not IS_WINDOWS or not self.isVisible():
            return
        try:
            user = ctypes.windll.user32
            user.SetWindowPos.argtypes = [
                wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int, wintypes.UINT
            ]
            user.SetWindowPos(
                wintypes.HWND(int(self.winId())), wintypes.HWND(HWND_TOPMOST), 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
        except Exception:
            pass

    # Monitor actualmente seleccionado
    def current_screen(self):
        screens = QApplication.screens()
        if not screens:
            return None
        return screens[max(0, min(self.monitor_idx, len(screens) - 1))]

    # Carga de la imagen de la mira con escalado suave
    def load_image(self, filename_or_path, color=None):
        if color is not None:
            self.color_val = color
        full_path = resolve_crosshair_path(filename_or_path)
        if not full_path:
            self.image_path = ''
            self.pixmap = None
            self.update()
            return
        self.image_path = full_path
        self.pixmap = load_crosshair_pixmap(full_path, self.size_val, self.dpr, color=self.color_val)
        self.update()

    # Recalculo de posicion exacta respecto al centro del monitor
    def reposition(self):
        screen = self.current_screen()
        if screen is None:
            return
        geo = screen.geometry()

        new_dpr = screen.devicePixelRatio()
        if abs(new_dpr - self.dpr) > 0.01:
            self.dpr = new_dpr
            if self.image_path:
                self.pixmap = load_crosshair_pixmap(self.image_path, self.size_val, self.dpr, color=self.color_val)

        x, y = crosshair_origin(geo.width(), geo.height(), self.size_val, self.offset_x, self.offset_y)
        self.setGeometry(geo.x() + x, geo.y() + y, self.size_val, self.size_val)
        self.update()

    # Ajuste de parametros visuales de la mira
    def update_params(self, size=None, offset_x=None, offset_y=None, opacity=None, monitor_idx=None, image_file=None, color=None):
        resized = False
        recolored = False
        if color is not None and color != self.color_val:
            self.color_val = color
            recolored = True
        if size is not None:
            new_size = max(MIN_SIZE, min(MAX_SIZE, int(size)))
            if new_size != self.size_val:
                self.size_val = new_size
                resized = True
        if offset_x is not None:
            self.offset_x = int(offset_x)
        if offset_y is not None:
            self.offset_y = int(offset_y)
        if opacity is not None:
            self.opacity_val = max(0.05, min(1.0, float(opacity)))
        if monitor_idx is not None:
            self.monitor_idx = int(monitor_idx)

        if image_file is not None:
            self.load_image(image_file, color=self.color_val)
        elif resized or recolored:
            self.load_image(self.image_path, color=self.color_val)

        self.reposition()

    # Restauracion del centro exacto de la pantalla
    def center_on_screen(self):
        self.offset_x = 0
        self.offset_y = 0
        self.reposition()

    # Renderizado de la mira centrada con opacidad aplicada
    def paintEvent(self, event):
        if not self.pixmap or self.pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setOpacity(self.opacity_val)
        w = self.pixmap.width() / self.pixmap.devicePixelRatio()
        h = self.pixmap.height() / self.pixmap.devicePixelRatio()
        painter.drawPixmap(int(round((self.width() - w) / 2)), int(round((self.height() - h) / 2)), self.pixmap)
        painter.end()

        if not self.pixmap or self.pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setOpacity(self.opacity_val)
        w = self.pixmap.width() / self.pixmap.devicePixelRatio()
        h = self.pixmap.height() / self.pixmap.devicePixelRatio()
        painter.drawPixmap(int(round((self.width() - w) / 2)), int(round((self.height() - h) / 2)), self.pixmap)
        painter.end()
