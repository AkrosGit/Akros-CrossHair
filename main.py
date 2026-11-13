# Modulo principal que inicia la aplicacion y configura el entorno general
import sys
import ctypes
import tempfile
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QLockFile, QTranslator, QLibraryInfo

from config_manager import load_config
from styles import build_stylesheet, make_app_icon, set_theme
from overlay import prepare_crosshair_assets


# Habilitacion de soporte para pantallas de alta resolucion
def enable_dpi_awareness():
    if sys.platform != 'win32':
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# Punto de entrada de la aplicacion
def main():
    enable_dpi_awareness()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Akro's CrossHair")

    # Carga de traducciones al espanol para elementos comunes
    translator = QTranslator(app)
    if translator.load('qtbase_es', QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
    app.setStyle('Fusion')
    # Aplicacion del tema visual guardado desde el inicio
    set_theme(load_config().get('theme', 'dark'))
    app.setStyleSheet(build_stylesheet())
    app.setWindowIcon(make_app_icon())
    app.setQuitOnLastWindowClosed(False)

    # Control de instancia unica para evitar duplicados en ejecucion
    lock = QLockFile(os.path.join(tempfile.gettempdir(), 'crosshair_pro.lock'))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None, "Akro's CrossHair",
                                "Akro's CrossHair ya se está ejecutando.\n"
                                'Búscalo junto al reloj de Windows (icono de la mira).')
        return 0

    prepare_crosshair_assets()
    from main_window import MainWindow
    start_in_tray = '--tray' in sys.argv or '--minimized' in sys.argv
    window = MainWindow()
    if not start_in_tray:
        window.show()

    code = app.exec_()
    lock.unlock()
    return code


if __name__ == '__main__':
    sys.exit(main())

