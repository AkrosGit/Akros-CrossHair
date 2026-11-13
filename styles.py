# Definicion de temas visuales hojas de estilo traducciones e iconos
import os
import sys
import tempfile
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QIcon

THEMES = {
    'dark': {
        'bg': '#0B0F19',
        'side': '#090C14',
        'card': '#111827',
        'card_hi': '#162033',
        'nav_active': '#111827',
        'border': '#1F2A3C',
        'border_hi': '#2B3A52',
        'input': '#0B1220',
        'text': '#E5E7EB',
        'strong': '#F8FAFC',
        'muted': '#8B98AD',
        'accent': '#38BDF8',
        'accent_dark': '#0284C7',
        'accent_hover': '#0EA5E9',
        'success': '#10B981',
        'warn': '#F59E0B',
        'danger': '#EF4444',
        'off': '#64748B',
    },
    'gray': {
        'bg': '#1E2027',
        'side': '#17191F',
        'card': '#272930',
        'card_hi': '#2F3340',
        'nav_active': '#272930',
        'border': '#3A3D47',
        'border_hi': '#4A4E5A',
        'input': '#1A1D24',
        'text': '#D8DCE6',
        'strong': '#F0F3F8',
        'muted': '#8E95A3',
        'accent': '#38BDF8',
        'accent_dark': '#0284C7',
        'accent_hover': '#0EA5E9',
        'success': '#10B981',
        'warn': '#F59E0B',
        'danger': '#EF4444',
        'off': '#64748B',
    },
    'light': {
        'bg': '#F2F4F8',
        'side': '#FFFFFF',
        'card': '#FFFFFF',
        'card_hi': '#F6F8FB',
        'nav_active': '#E8F2FA',
        'border': '#E2E6ED',
        'border_hi': '#C9D0DB',
        'input': '#F1F4F8',
        'text': '#374151',
        'strong': '#0F172A',
        'muted': '#6B7280',
        'accent': '#0284C7',
        'accent_dark': '#0369A1',
        'accent_hover': '#0EA5E9',
        'success': '#059669',
        'warn': '#D97706',
        'danger': '#DC2626',
        'off': '#94A3B8',
    },
}

# Tema activo por defecto
C = dict(THEMES['dark'])
_current_theme = 'dark'


def set_theme(name):
    global _current_theme
    C.clear()
    C.update(THEMES[name])
    _current_theme = name


def get_current_theme():
    return _current_theme


# Nombres de idiomas disponibles para la interfaz
LANGUAGES = [
    ('es', 'Español'),
    ('en', 'English'),
    ('pt', 'Português'),
    ('fr', 'Français'),
]

TRANSLATIONS = {
    'es': {
        'nav_crosshairs': 'Miras',
        'nav_position': 'Tamaño y posición',
        'nav_presets': 'Presets',
        'nav_settings': 'Configuración',
        'page_crosshairs_title': 'Miras',
        'page_crosshairs_sub': 'Elige el diseño que quieres ver en pantalla. Puedes añadir tus propias imágenes en formato PNG.',
        'page_position_title': 'Tamaño y posición',
        'page_position_sub': 'Ajusta la mira con precisión viéndola a pantalla completa, sobre una captura de tu juego.',
        'page_presets_title': 'Presets',
        'page_presets_sub': 'Guarda tu mira con el nombre que quieras, deja que se cargue sola al abrir una aplicación y añade estados que cambian la mira al pulsar un botón.',
        'page_settings_title': 'Configuración',
        'lbl_library': 'Biblioteca',
        'btn_add_crosshair': 'Añadir mira',
        'lbl_no_crosshairs': 'No hay miras todavía. Pulsa «Añadir mira» para importar una imagen.',
        'lbl_preview': 'Vista previa',
        'lbl_opacity': 'OPACIDAD',
        'lbl_color': 'COLOR DE LA MIRA',
        'lbl_no_crosshair': 'Sin mira seleccionada',
        'lbl_fullscreen_editor': 'Editor a pantalla completa',
        'btn_open_editor': 'Abrir editor a pantalla completa',
        'lbl_current_values': 'Valores actuales',
        'btn_center': 'Centrar mira',
        'lbl_size': 'TAMAÑO',
        'lbl_offset': 'DESPLAZAMIENTO',
        'lbl_opac_metric': 'OPACIDAD',
        'lbl_monitor': 'Monitor de juego',
        'lbl_monitor_desc': 'La mira se dibuja centrada en el monitor que elijas.',
        'lbl_current_config': 'CONFIGURACIÓN ACTUAL',
        'btn_save_preset': 'Guardar como preset',
        'lbl_your_presets': 'Tus presets',
        'lbl_no_presets_title': 'Todavía no tienes presets',
        'lbl_no_presets_desc': 'Ajusta tu mira como más te guste y pulsa «Guardar como preset». Podrás volver a ella con un clic o hacer que se cargue sola con tu juego.',
        'btn_apply': 'Aplicar',
        'lbl_applied': 'Aplicado',
        'lbl_automatic': 'Automático',
        'lbl_appearance': 'Apariencia',
        'lbl_activation': 'Activación',
        'lbl_activation_desc': 'Activa el atajo, la detección automática o ambos.',
        'lbl_manual_hotkey': 'Tecla o botón de mando para mostrar u ocultar la mira',
        'lbl_auto_desc': 'La mira solo se muestra cuando una aplicación con preset automático está en primer plano, y carga ese preset.',
        'btn_manage_presets': 'Gestionar presets',
        'mode_manual_title': 'Atajo de teclado o mando',
        'mode_manual_desc': 'Muestra u oculta la mira cuando pulsas una tecla o botón de mando.',
        'mode_auto_title': 'Automático al abrir un juego',
        'mode_auto_desc': 'Aparece sola, con su preset, cuando la aplicación está en primer plano.',
        'lbl_background': 'Segundo plano',
        'lbl_tray': 'Seguir activa al cerrar la ventana',
        'lbl_tray_desc': 'La app se minimiza junto al reloj y la mira sigue funcionando.',
        'lbl_startup': 'Iniciar con Windows',
        'lbl_startup_desc': 'Se abre en segundo plano al encender el equipo.',
        'lbl_language': 'Idioma',
        'lbl_language_desc': 'Cambia el idioma de toda la interfaz.',
        'tray_show': 'Abrir panel de control',
        'tray_edit': 'Editar tamaño y posición',
        'tray_hide': 'Ocultar mira',
        'tray_show_crosshair': 'Mostrar mira',
        'btn_enable_crosshair': 'Activar mira',
        'btn_disable_crosshair': 'Desactivar mira',
        'hotkey_error': 'No se pudo registrar ese atajo. Prueba con otra tecla o ejecuta la app como administrador.',
        'theme_dark': 'Oscuro',
        'theme_gray': 'Gris',
        'theme_light': 'Claro',
        'theme_tooltip': 'Tema {theme}',
        'theme_applied': 'Tema {theme} aplicado',
        'color_original': 'Original',
        'color_original_tip': 'Original (sin teñir la imagen)',
        'color_white': 'Blanco',
        'color_red': 'Rojo',
        'color_orange': 'Naranja',
        'color_yellow': 'Amarillo',
        'color_green': 'Verde',
        'color_cyan': 'Cian',
        'color_blue': 'Azul',
        'color_violet': 'Violeta',
        'color_pink': 'Rosa',
        'color_custom': 'Personalizado',
        'color_no_tint': 'sin teñir',
        'editor_title': 'Editor de mira',
        'editor_drag_tooltip': 'Arrastra para mover este panel',
        'editor_size': 'Tamaño',
        'editor_opacity': 'Opacidad',
        'editor_position': 'Posición',
        'editor_center': 'Centrar',
        'editor_background': 'Fondo',
        'editor_bg_screenshot': 'Captura de pantalla',
        'editor_bg_plain': 'Fondo liso',
        'editor_bg_grid': 'Cuadrícula',
        'editor_guides': 'Guías',
        'editor_cancel': 'Cancelar',
        'editor_cancel_tooltip': 'Descarta los cambios (Esc)',
        'editor_save_exit': 'Guardar y salir',
        'editor_save_tooltip': 'Aplica los cambios (Enter)',
        'editor_hint_arrows': 'Flechas',
        'editor_hint_move': 'mover (Shift ×10)',
        'editor_hint_size': 'tamaño',
        'editor_hint_center': 'centrar',
        'editor_hint_guides': 'guías',
        'editor_hint_background': 'fondo',
        'editor_hint_save': 'guardar',
        'editor_hint_cancel': 'cancelar',
        'btn_new_group': 'Nuevo grupo',
        'group_rename': 'Renombrar grupo',
        'group_delete': 'Eliminar grupo',
        'group_move_to': 'Mover a grupo',
        'lbl_group': 'Grupo',
        'dialog_new_group_title': 'Nuevo grupo',
        'dialog_new_group_prompt': 'Nombre del grupo:',
        'dialog_rename_group_title': 'Renombrar grupo',
        'dialog_rename_group_prompt': 'Nuevo nombre del grupo:',
        'common_cancel': 'Cancelar',
        'common_save': 'Guardar',
        'common_yes': 'Sí',
        'common_no': 'No',
        'common_browse': 'Examinar',
        'common_undo_warning': 'Esta acción no se puede deshacer.',
        'preset_auto_applies': 'Se aplica sola al abrir {app}',
        'preset_no_automation': 'Sin aplicación automática',
        'preset_auto_tooltip': 'Aplicar este preset automáticamente al abrir su aplicación',
        'more_options': 'Más opciones',
        'preset_edit': 'Editar',
        'preset_states': 'Estados de la mira',
        'preset_update_current': 'Actualizar con los ajustes actuales',
        'preset_duplicate': 'Duplicar',
        'preset_delete': 'Eliminar',
        'preset_edit_title': 'Editar preset',
        'preset_new_title': 'Nuevo preset',
        'preset_save_title': 'Guardar como preset',
        'preset_save_description': 'Se guardan la mira, el tamaño, la posición, la opacidad y el color.',
        'preset_edit_description': 'Cambia el nombre o la aplicación asociada.',
        'preset_settings_heading': 'Ajustes del preset',
        'preset_use_current': 'Usar los actuales',
        'preset_use_current_tooltip': 'Reemplaza los ajustes de este preset por los que tienes ahora en pantalla',
        'preset_name_heading': 'Nombre',
        'preset_name_placeholder': 'Ej. Valorant · competitivo',
        'preset_automation_heading': 'Automatización',
        'preset_auto_label': 'Aplicar al abrir una aplicación',
        'preset_auto_description': 'Cuando esa aplicación esté en primer plano, se carga este preset solo.',
        'preset_app_placeholder': 'Nombre del juego, proceso (.exe) o título de ventana',
        'preset_detect_button': 'Detectar aplicación abierta',
        'preset_select_executable': 'Seleccionar ejecutable',
        'preset_executable_filter': 'Ejecutables (*.exe)',
        'preset_detect_countdown': 'Cambia ahora a tu juego o aplicación {seconds} s',
        'preset_detect_none': 'No se detectó ninguna aplicación. Inténtalo de nuevo y haz clic en su ventana.',
        'preset_detected': 'Detectada: {app}',
        'preset_save_changes': 'Guardar cambios',
        'preset_save_button': 'Guardar preset',
        'preset_error_name_required': 'Ponle un nombre al preset.',
        'preset_error_name_exists': 'Ya existe un preset llamado «{name}». Elige otro nombre.',
        'preset_error_app_required': 'Indica la aplicación que activará este preset, o desactiva la automatización.',
        'preset_error_app_exists': 'El preset «{name}» ya se aplica automáticamente a esa aplicación.',
        'preset_add_button': '+ Preset',
        'preset_count_one': '{count} guardado',
        'preset_count_many': '{count} guardados',
        'preset_current_unsaved': 'Ajustes sin guardar como preset',
        'preset_current_state': 'Preset «{preset}» · estado «{state}»',
        'preset_current': 'Preset «{name}»',
        'preset_default_name': 'Preset',
        'preset_saved': 'Preset «{name}» guardado',
        'preset_updated': 'Preset «{name}» actualizado',
        'preset_updated_current': 'Preset «{name}» actualizado con los ajustes actuales',
        'preset_copy_suffix': '(copia)',
        'preset_duplicated': 'Preset duplicado como «{name}»',
        'preset_delete_title': 'Eliminar preset',
        'preset_delete_question': '¿Eliminar el preset «{name}»?\n{warning}',
        'preset_deleted': 'Preset «{name}» eliminado',
        'preset_applied': 'Preset «{name}» aplicado',
        'preset_moved': 'Preset «{name}» movido a «{group}»',
        'preset_auto_conflict': 'El preset «{name}» ya se aplica automáticamente a {app}.\nDesactívalo primero si quieres usar este.',
        'preset_auto_enabled': 'Aplicación automática activada para «{name}»',
        'preset_auto_disabled': 'Aplicación automática desactivada para «{name}»',
        'group_exists': 'El grupo «{name}» ya existe.',
        'group_created': 'Grupo «{name}» creado',
        'group_name_exists': 'Ya existe un grupo llamado «{name}».',
        'group_renamed': 'Grupo renombrado a «{name}»',
        'group_delete_question': '¿Eliminar el grupo «{name}»?\nLos presets de este grupo se moverán a «General».',
        'group_deleted': 'Grupo «{name}» eliminado',
        'states_saved': 'Estados de «{name}» guardados',
        'state_binding_error': 'No se pudo registrar el botón de: {names}. Prueba con otro botón o ejecuta la app como administrador.',
        'state_reserved_global_hotkey': 'el atajo para mostrar u ocultar la mira',
        'state_new_title': 'Nuevo estado',
        'state_edit_title': 'Editar estado',
        'state_dialog_description': 'Elige cómo se verá la mira en este estado y qué botón lo activa.',
        'state_save_button': 'Guardar estado',
        'state_preview': 'Vista previa',
        'state_crosshair': 'Mira',
        'state_color': 'Color',
        'state_name': 'Nombre',
        'state_name_placeholder': 'Ej. Apuntando',
        'state_size': 'Tamaño',
        'state_position': 'Posición respecto al centro',
        'state_center': 'Centrar',
        'state_opacity': 'Opacidad',
        'state_fullscreen_button': 'Ajustar en pantalla completa',
        'state_fullscreen_tooltip': 'Abre el editor para colocar y escalar la mira de este estado',
        'state_hotkey_section': 'Botón que activa este estado',
        'state_hotkey_hint': 'Presiona para asignar cualquier gatillo, botón de mando, ratón o teclado',
        'state_mode_hold': 'Mantener: activo solo mientras lo mantienes pulsado',
        'state_mode_toggle': 'Alternar: una pulsación lo activa y otra vuelve atrás',
        'state_error_name_required': 'Ponle un nombre al estado.',
        'state_error_name_exists': 'Ya existe un estado llamado «{name}». Elige otro nombre.',
        'state_error_crosshair_required': 'Elige una mira para este estado.',
        'state_error_hotkey_required': 'Elige el botón que activará este estado.',
        'state_error_hotkey_taken': 'Ese botón ya lo usa {owner}. Elige otro.',
        'state_mode_hold_short': 'mantener',
        'state_mode_toggle_short': 'alternar',
        'state_no_hotkey': 'sin botón asignado',
        'state_base_name': 'Principal',
        'state_base_description': 'Es la mira de siempre: se ve por defecto y a ella se vuelve.',
        'state_list_title': 'Estados de la mira',
        'state_list_heading': 'Estados de «{name}»',
        'state_list_description': 'Mientras este preset esté en uso, pulsa el botón de un estado para cambiar la mira: por ejemplo «sin apuntar» y «apuntando», o una mira distinta en cada perspectiva. Cada estado guarda su propia mira, tamaño, posición, opacidad y color.',
        'state_add': 'Añadir estado',
        'state_max_count': 'Máximo {max} estados por preset.',
        'state_empty': 'Todavía no hay estados. Añade uno, por ejemplo «Apuntando» con el botón derecho del ratón en modo «Mantener».',
        'state_reserved': 'el estado «{name}»',
        'state_default_aiming': 'Apuntando',
        'state_default_name': 'Estado',
    },
    'en': {
        'nav_crosshairs': 'Crosshairs',
        'nav_position': 'Size && Position',
        'nav_presets': 'Presets',
        'nav_settings': 'Settings',
        'page_crosshairs_title': 'Crosshairs',
        'page_crosshairs_sub': 'Choose the design you want to see on screen. You can add your own PNG images.',
        'page_position_title': 'Size && Position',
        'page_position_sub': 'Adjust the crosshair precisely by viewing it full-screen, over a capture of your game.',
        'page_presets_title': 'Presets',
        'page_presets_sub': 'Save your crosshair with any name, let it load automatically when an app opens, and add states that change the crosshair at the press of a button.',
        'page_settings_title': 'Settings',
        'lbl_library': 'Library',
        'btn_add_crosshair': 'Add crosshair',
        'lbl_no_crosshairs': 'No crosshairs yet. Click «Add crosshair» to import an image.',
        'lbl_preview': 'Preview',
        'lbl_opacity': 'OPACITY',
        'lbl_color': 'CROSSHAIR COLOR',
        'lbl_no_crosshair': 'No crosshair selected',
        'lbl_fullscreen_editor': 'Full-screen editor',
        'btn_open_editor': 'Open full-screen editor',
        'lbl_current_values': 'Current values',
        'btn_center': 'Center crosshair',
        'lbl_size': 'SIZE',
        'lbl_offset': 'OFFSET',
        'lbl_opac_metric': 'OPACITY',
        'lbl_monitor': 'Game monitor',
        'lbl_monitor_desc': 'The crosshair is drawn centred on the monitor you choose.',
        'lbl_current_config': 'CURRENT SETTINGS',
        'btn_save_preset': 'Save as preset',
        'lbl_your_presets': 'Your presets',
        'lbl_no_presets_title': 'No presets yet',
        'lbl_no_presets_desc': 'Set up your crosshair however you like and click «Save as preset». You can return to it with one click or have it load automatically with your game.',
        'btn_apply': 'Apply',
        'lbl_applied': 'Applied',
        'lbl_automatic': 'Automatic',
        'lbl_appearance': 'Appearance',
        'lbl_activation': 'Activation',
        'lbl_activation_desc': 'Enable the shortcut, automatic detection, or both.',
        'lbl_manual_hotkey': 'Key or controller button to show or hide the crosshair',
        'lbl_auto_desc': 'The crosshair only appears when an app with an automatic preset is in the foreground and loads that preset.',
        'btn_manage_presets': 'Manage presets',
        'mode_manual_title': 'Keyboard or controller shortcut',
        'mode_manual_desc': 'Shows or hides the crosshair when you press a key or controller button.',
        'mode_auto_title': 'Automatic when a game opens',
        'mode_auto_desc': 'Appears on its own, with its preset, when the application is in the foreground.',
        'lbl_background': 'Background',
        'lbl_tray': 'Keep running when the window is closed',
        'lbl_tray_desc': 'The app minimises to the system tray and the crosshair keeps working.',
        'lbl_startup': 'Start with Windows',
        'lbl_startup_desc': 'Opens in the background when the computer starts.',
        'lbl_language': 'Language',
        'lbl_language_desc': 'Change the language of the entire interface.',
        'tray_show': 'Open control panel',
        'tray_edit': 'Edit size and position',
        'tray_hide': 'Hide crosshair',
        'tray_show_crosshair': 'Show crosshair',
        'btn_enable_crosshair': 'Enable crosshair',
        'btn_disable_crosshair': 'Disable crosshair',
        'hotkey_error': 'Could not register that shortcut. Try another key or run the app as administrator.',
        'theme_dark': 'Dark',
        'theme_gray': 'Gray',
        'theme_light': 'Light',
        'theme_tooltip': 'Theme: {theme}',
        'theme_applied': 'Applied {theme} theme',
        'color_original': 'Original',
        'color_original_tip': 'Original (untinted)',
        'color_white': 'White',
        'color_red': 'Red',
        'color_orange': 'Orange',
        'color_yellow': 'Yellow',
        'color_green': 'Green',
        'color_cyan': 'Cyan',
        'color_blue': 'Blue',
        'color_violet': 'Violet',
        'color_pink': 'Pink',
        'color_custom': 'Custom',
        'color_no_tint': 'untinted',
        'editor_title': 'Crosshair editor',
        'editor_drag_tooltip': 'Drag to move this panel',
        'editor_size': 'Size',
        'editor_opacity': 'Opacity',
        'editor_position': 'Position',
        'editor_center': 'Center',
        'editor_background': 'Background',
        'editor_bg_screenshot': 'Screenshot',
        'editor_bg_plain': 'Solid color',
        'editor_bg_grid': 'Grid',
        'editor_guides': 'Guides',
        'editor_cancel': 'Cancel',
        'editor_cancel_tooltip': 'Discard changes (Esc)',
        'editor_save_exit': 'Save and exit',
        'editor_save_tooltip': 'Apply changes (Enter)',
        'editor_hint_arrows': 'Arrows',
        'editor_hint_move': 'move (Shift ×10)',
        'editor_hint_size': 'size',
        'editor_hint_center': 'center',
        'editor_hint_guides': 'guides',
        'editor_hint_background': 'background',
        'editor_hint_save': 'save',
        'editor_hint_cancel': 'cancel',
        'btn_new_group': 'New group',
        'group_rename': 'Rename group',
        'group_delete': 'Delete group',
        'group_move_to': 'Move to group',
        'lbl_group': 'Group',
        'dialog_new_group_title': 'New Group',
        'dialog_new_group_prompt': 'Group name:',
        'dialog_rename_group_title': 'Rename Group',
        'dialog_rename_group_prompt': 'New group name:',
        'common_cancel': 'Cancel',
        'common_save': 'Save',
        'common_yes': 'Yes',
        'common_no': 'No',
        'common_browse': 'Browse',
        'common_undo_warning': 'This action cannot be undone.',
        'preset_auto_applies': 'Applied automatically when {app} opens',
        'preset_no_automation': 'No automatic application',
        'preset_auto_tooltip': 'Apply this preset automatically when its app opens',
        'more_options': 'More options',
        'preset_edit': 'Edit',
        'preset_states': 'Crosshair states',
        'preset_update_current': 'Update with current settings',
        'preset_duplicate': 'Duplicate',
        'preset_delete': 'Delete',
        'preset_edit_title': 'Edit preset',
        'preset_new_title': 'New preset',
        'preset_save_title': 'Save as preset',
        'preset_save_description': 'The crosshair, size, position, opacity, and color will be saved.',
        'preset_edit_description': 'Change the name or associated application.',
        'preset_settings_heading': 'Preset settings',
        'preset_use_current': 'Use current settings',
        'preset_use_current_tooltip': 'Replace this preset’s settings with the ones currently on screen',
        'preset_name_heading': 'Name',
        'preset_name_placeholder': 'e.g. Valorant · competitive',
        'preset_automation_heading': 'Automation',
        'preset_auto_label': 'Apply when an application opens',
        'preset_auto_description': 'This preset loads automatically when that application is in the foreground.',
        'preset_app_placeholder': 'Game name, process (.exe), or window title',
        'preset_detect_button': 'Detect open application',
        'preset_select_executable': 'Select executable',
        'preset_executable_filter': 'Executables (*.exe)',
        'preset_detect_countdown': 'Switch to your game or application now: {seconds} s',
        'preset_detect_none': 'No application detected. Try again and click its window.',
        'preset_detected': 'Detected: {app}',
        'preset_save_changes': 'Save changes',
        'preset_save_button': 'Save preset',
        'preset_error_name_required': 'Enter a name for the preset.',
        'preset_error_name_exists': 'A preset named “{name}” already exists. Choose another name.',
        'preset_error_app_required': 'Choose the application that will activate this preset, or turn off automation.',
        'preset_error_app_exists': 'The “{name}” preset is already applied automatically to that application.',
        'preset_add_button': '+ Preset',
        'preset_count_one': '{count} saved',
        'preset_count_many': '{count} saved',
        'preset_current_unsaved': 'Current settings are not saved as a preset',
        'preset_current_state': 'Preset “{preset}” · state “{state}”',
        'preset_current': 'Preset “{name}”',
        'preset_default_name': 'Preset',
        'preset_saved': 'Preset “{name}” saved',
        'preset_updated': 'Preset “{name}” updated',
        'preset_updated_current': 'Preset “{name}” updated with current settings',
        'preset_copy_suffix': '(copy)',
        'preset_duplicated': 'Preset duplicated as “{name}”',
        'preset_delete_title': 'Delete preset',
        'preset_delete_question': 'Delete the “{name}” preset?\n{warning}',
        'preset_deleted': 'Preset “{name}” deleted',
        'preset_applied': 'Preset “{name}” applied',
        'preset_moved': 'Preset “{name}” moved to “{group}”',
        'preset_auto_conflict': 'The “{name}” preset is already applied automatically to {app}.\nTurn it off first to use this one.',
        'preset_auto_enabled': 'Automatic application enabled for “{name}”',
        'preset_auto_disabled': 'Automatic application disabled for “{name}”',
        'group_exists': 'The “{name}” group already exists.',
        'group_created': 'Group “{name}” created',
        'group_name_exists': 'A group named “{name}” already exists.',
        'group_renamed': 'Group renamed to “{name}”',
        'group_delete_question': 'Delete the “{name}” group?\nIts presets will be moved to “General”.',
        'group_deleted': 'Group “{name}” deleted',
        'states_saved': 'States for “{name}” saved',
        'state_binding_error': 'Could not register the button for: {names}. Try another button or run the app as administrator.',
        'state_reserved_global_hotkey': 'the shortcut used to show or hide the crosshair',
        'state_new_title': 'New state',
        'state_edit_title': 'Edit state',
        'state_dialog_description': 'Choose how the crosshair looks in this state and which button activates it.',
        'state_save_button': 'Save state',
        'state_preview': 'Preview',
        'state_crosshair': 'Crosshair',
        'state_color': 'Color',
        'state_name': 'Name',
        'state_name_placeholder': 'e.g. Aiming',
        'state_size': 'Size',
        'state_position': 'Position relative to center',
        'state_center': 'Center',
        'state_opacity': 'Opacity',
        'state_fullscreen_button': 'Adjust full screen',
        'state_fullscreen_tooltip': 'Open the editor to position and scale this state’s crosshair',
        'state_hotkey_section': 'Button that activates this state',
        'state_hotkey_hint': 'Press to assign any trigger, controller button, mouse button, or key',
        'state_mode_hold': 'Hold: active only while the button is held',
        'state_mode_toggle': 'Toggle: press once to activate and again to switch back',
        'state_error_name_required': 'Enter a name for the state.',
        'state_error_name_exists': 'A state named “{name}” already exists. Choose another name.',
        'state_error_crosshair_required': 'Choose a crosshair for this state.',
        'state_error_hotkey_required': 'Choose the button that activates this state.',
        'state_error_hotkey_taken': 'That button is already used by {owner}. Choose another.',
        'state_mode_hold_short': 'hold',
        'state_mode_toggle_short': 'toggle',
        'state_no_hotkey': 'no button assigned',
        'state_base_name': 'Default',
        'state_base_description': 'This is the default crosshair shown when no other state is active.',
        'state_list_title': 'Crosshair states',
        'state_list_heading': 'States for “{name}”',
        'state_list_description': 'While this preset is in use, press a state’s button to change the crosshair—for example, between hip-fire and aiming, or to use a different crosshair in each perspective. Each state saves its own crosshair, size, position, opacity, and color.',
        'state_add': 'Add state',
        'state_max_count': 'Maximum {max} states per preset.',
        'state_empty': 'There are no states yet. Add one, for example “Aiming” with the right mouse button in “Hold” mode.',
        'state_reserved': 'the “{name}” state',
        'state_default_aiming': 'Aiming',
        'state_default_name': 'State',
    },
    'pt': {
        'nav_crosshairs': 'Miras',
        'nav_position': 'Tamanho e posição',
        'nav_presets': 'Presets',
        'nav_settings': 'Configurações',
        'page_crosshairs_title': 'Miras',
        'page_crosshairs_sub': 'Escolha o design que quer ver no ecrã. Pode adicionar as suas próprias imagens PNG.',
        'page_position_title': 'Tamanho e posição',
        'page_position_sub': 'Ajuste a mira com precisão vendo-a em ecrã inteiro, sobre uma captura do seu jogo.',
        'page_presets_title': 'Presets',
        'page_presets_sub': 'Guarde a sua mira com o nome que quiser, deixe-a carregar automaticamente ao abrir uma aplicação e adicione estados que mudam a mira ao pressionar um botão.',
        'page_settings_title': 'Configurações',
        'lbl_library': 'Biblioteca',
        'btn_add_crosshair': 'Adicionar mira',
        'lbl_no_crosshairs': 'Sem miras ainda. Clique em «Adicionar mira» para importar uma imagem.',
        'lbl_preview': 'Pré-visualização',
        'lbl_opacity': 'OPACIDADE',
        'lbl_color': 'COR DA MIRA',
        'lbl_no_crosshair': 'Nenhuma mira selecionada',
        'lbl_fullscreen_editor': 'Editor em ecrã inteiro',
        'btn_open_editor': 'Abrir editor em ecrã inteiro',
        'lbl_current_values': 'Valores atuais',
        'btn_center': 'Centrar mira',
        'lbl_size': 'TAMANHO',
        'lbl_offset': 'DESLOCAMENTO',
        'lbl_opac_metric': 'OPACIDADE',
        'lbl_monitor': 'Monitor de jogo',
        'lbl_monitor_desc': 'A mira é desenhada centrada no monitor que escolher.',
        'lbl_current_config': 'CONFIGURAÇÃO ATUAL',
        'btn_save_preset': 'Guardar como preset',
        'lbl_your_presets': 'Os seus presets',
        'lbl_no_presets_title': 'Ainda não tem presets',
        'lbl_no_presets_desc': 'Configure a mira como preferir e clique em «Guardar como preset». Pode voltar a ela com um clique ou fazer com que carregue automaticamente com o jogo.',
        'btn_apply': 'Aplicar',
        'lbl_applied': 'Aplicado',
        'lbl_automatic': 'Automático',
        'lbl_appearance': 'Aparência',
        'lbl_activation': 'Ativação',
        'lbl_activation_desc': 'Ative o atalho, a deteção automática ou ambos.',
        'lbl_manual_hotkey': 'Tecla ou botão do comando para mostrar ou ocultar a mira',
        'lbl_auto_desc': 'A mira só aparece quando uma aplicação com preset automático está em primeiro plano e carrega esse preset.',
        'btn_manage_presets': 'Gerir presets',
        'mode_manual_title': 'Atalho de teclado ou comando',
        'mode_manual_desc': 'Mostra ou oculta a mira quando pressionar uma tecla ou botão do comando.',
        'mode_auto_title': 'Automático ao abrir um jogo',
        'mode_auto_desc': 'Aparece sozinha, com o preset, quando a aplicação está em primeiro plano.',
        'lbl_background': 'Segundo plano',
        'lbl_tray': 'Continuar ativa ao fechar a janela',
        'lbl_tray_desc': 'A aplicação minimiza para a bandeja do sistema e a mira continua a funcionar.',
        'lbl_startup': 'Iniciar com o Windows',
        'lbl_startup_desc': 'Abre em segundo plano ao ligar o computador.',
        'lbl_language': 'Idioma',
        'lbl_language_desc': 'Mude o idioma de toda a interface.',
        'tray_show': 'Abrir painel de controlo',
        'tray_edit': 'Editar tamanho e posição',
        'tray_hide': 'Ocultar mira',
        'tray_show_crosshair': 'Mostrar mira',
        'btn_enable_crosshair': 'Ativar mira',
        'btn_disable_crosshair': 'Desativar mira',
        'hotkey_error': 'Não foi possível registar esse atalho. Tente outra tecla ou execute a aplicação como administrador.',
        'theme_dark': 'Escuro',
        'theme_gray': 'Cinzento',
        'theme_light': 'Claro',
        'theme_tooltip': 'Tema {theme}',
        'theme_applied': 'Tema {theme} aplicado',
        'color_original': 'Original',
        'color_original_tip': 'Original (sem tingir a imagem)',
        'color_white': 'Branco',
        'color_red': 'Vermelho',
        'color_orange': 'Laranja',
        'color_yellow': 'Amarelo',
        'color_green': 'Verde',
        'color_cyan': 'Ciano',
        'color_blue': 'Azul',
        'color_violet': 'Violeta',
        'color_pink': 'Rosa',
        'color_custom': 'Personalizado',
        'color_no_tint': 'sem tingir',
        'editor_title': 'Editor da mira',
        'editor_drag_tooltip': 'Arraste para mover este painel',
        'editor_size': 'Tamanho',
        'editor_opacity': 'Opacidade',
        'editor_position': 'Posição',
        'editor_center': 'Centrar',
        'editor_background': 'Fundo',
        'editor_bg_screenshot': 'Captura de ecrã',
        'editor_bg_plain': 'Fundo liso',
        'editor_bg_grid': 'Grelha',
        'editor_guides': 'Guias',
        'editor_cancel': 'Cancelar',
        'editor_cancel_tooltip': 'Descarta as alterações (Esc)',
        'editor_save_exit': 'Guardar e sair',
        'editor_save_tooltip': 'Aplica as alterações (Enter)',
        'editor_hint_arrows': 'Setas',
        'editor_hint_move': 'mover (Shift ×10)',
        'editor_hint_size': 'tamanho',
        'editor_hint_center': 'centrar',
        'editor_hint_guides': 'guias',
        'editor_hint_background': 'fundo',
        'editor_hint_save': 'guardar',
        'editor_hint_cancel': 'cancelar',
        'btn_new_group': 'Novo grupo',
        'group_rename': 'Renomear grupo',
        'group_delete': 'Eliminar grupo',
        'group_move_to': 'Mover para grupo',
        'lbl_group': 'Grupo',
        'dialog_new_group_title': 'Novo grupo',
        'dialog_new_group_prompt': 'Nome do grupo:',
        'dialog_rename_group_title': 'Renomear grupo',
        'dialog_rename_group_prompt': 'Novo nome do grupo:',
        'common_cancel': 'Cancelar',
        'common_save': 'Guardar',
        'common_yes': 'Sim',
        'common_no': 'Não',
        'common_browse': 'Procurar',
        'common_undo_warning': 'Esta ação não pode ser desfeita.',
        'preset_auto_applies': 'Aplica-se automaticamente ao abrir {app}',
        'preset_no_automation': 'Sem aplicação automática',
        'preset_auto_tooltip': 'Aplicar este preset automaticamente ao abrir a aplicação',
        'more_options': 'Mais opções',
        'preset_edit': 'Editar',
        'preset_states': 'Estados da mira',
        'preset_update_current': 'Atualizar com os ajustes atuais',
        'preset_duplicate': 'Duplicar',
        'preset_delete': 'Eliminar',
        'preset_edit_title': 'Editar preset',
        'preset_new_title': 'Novo preset',
        'preset_save_title': 'Guardar como preset',
        'preset_save_description': 'Serão guardados a mira, o tamanho, a posição, a opacidade e a cor.',
        'preset_edit_description': 'Altere o nome ou a aplicação associada.',
        'preset_settings_heading': 'Ajustes do preset',
        'preset_use_current': 'Usar os atuais',
        'preset_use_current_tooltip': 'Substitui os ajustes deste preset pelos que estão no ecrã',
        'preset_name_heading': 'Nome',
        'preset_name_placeholder': 'Ex.: Valorant · competitivo',
        'preset_automation_heading': 'Automatização',
        'preset_auto_label': 'Aplicar ao abrir uma aplicação',
        'preset_auto_description': 'Este preset é carregado automaticamente quando essa aplicação está em primeiro plano.',
        'preset_app_placeholder': 'Nome do jogo, processo (.exe) ou título da janela',
        'preset_detect_button': 'Detetar aplicação aberta',
        'preset_select_executable': 'Selecionar executável',
        'preset_executable_filter': 'Executáveis (*.exe)',
        'preset_detect_countdown': 'Mude agora para o jogo ou aplicação: {seconds} s',
        'preset_detect_none': 'Nenhuma aplicação detetada. Tente novamente e clique na respetiva janela.',
        'preset_detected': 'Detetada: {app}',
        'preset_save_changes': 'Guardar alterações',
        'preset_save_button': 'Guardar preset',
        'preset_error_name_required': 'Introduza um nome para o preset.',
        'preset_error_name_exists': 'Já existe um preset chamado «{name}». Escolha outro nome.',
        'preset_error_app_required': 'Indique a aplicação que ativará este preset ou desative a automatização.',
        'preset_error_app_exists': 'O preset «{name}» já é aplicado automaticamente a essa aplicação.',
        'preset_add_button': '+ Preset',
        'preset_count_one': '{count} guardado',
        'preset_count_many': '{count} guardados',
        'preset_current_unsaved': 'Ajustes atuais não guardados como preset',
        'preset_current_state': 'Preset «{preset}» · estado «{state}»',
        'preset_current': 'Preset «{name}»',
        'preset_default_name': 'Preset',
        'preset_saved': 'Preset «{name}» guardado',
        'preset_updated': 'Preset «{name}» atualizado',
        'preset_updated_current': 'Preset «{name}» atualizado com os ajustes atuais',
        'preset_copy_suffix': '(cópia)',
        'preset_duplicated': 'Preset duplicado como «{name}»',
        'preset_delete_title': 'Eliminar preset',
        'preset_delete_question': 'Eliminar o preset «{name}»?\n{warning}',
        'preset_deleted': 'Preset «{name}» eliminado',
        'preset_applied': 'Preset «{name}» aplicado',
        'preset_moved': 'Preset «{name}» movido para «{group}»',
        'preset_auto_conflict': 'O preset «{name}» já é aplicado automaticamente a {app}.\nDesative-o primeiro se quiser usar este.',
        'preset_auto_enabled': 'Aplicação automática ativada para «{name}»',
        'preset_auto_disabled': 'Aplicação automática desativada para «{name}»',
        'group_exists': 'O grupo «{name}» já existe.',
        'group_created': 'Grupo «{name}» criado',
        'group_name_exists': 'Já existe um grupo chamado «{name}».',
        'group_renamed': 'Grupo renomeado para «{name}»',
        'group_delete_question': 'Eliminar o grupo «{name}»?\nOs seus presets serão movidos para «General».',
        'group_deleted': 'Grupo «{name}» eliminado',
        'states_saved': 'Estados de «{name}» guardados',
        'state_binding_error': 'Não foi possível registar o botão de: {names}. Tente outro botão ou execute a aplicação como administrador.',
        'state_reserved_global_hotkey': 'o atalho para mostrar ou ocultar a mira',
        'state_new_title': 'Novo estado',
        'state_edit_title': 'Editar estado',
        'state_dialog_description': 'Escolha o aspeto da mira neste estado e o botão que o ativa.',
        'state_save_button': 'Guardar estado',
        'state_preview': 'Pré-visualização',
        'state_crosshair': 'Mira',
        'state_color': 'Cor',
        'state_name': 'Nome',
        'state_name_placeholder': 'Ex.: A apontar',
        'state_size': 'Tamanho',
        'state_position': 'Posição em relação ao centro',
        'state_center': 'Centrar',
        'state_opacity': 'Opacidade',
        'state_fullscreen_button': 'Ajustar em ecrã inteiro',
        'state_fullscreen_tooltip': 'Abre o editor para posicionar e ajustar o tamanho da mira deste estado',
        'state_hotkey_section': 'Botão que ativa este estado',
        'state_hotkey_hint': 'Pressione para atribuir qualquer gatilho, botão do comando, rato ou teclado',
        'state_mode_hold': 'Manter: ativo apenas enquanto mantém o botão premido',
        'state_mode_toggle': 'Alternar: uma pressão ativa e outra volta ao anterior',
        'state_error_name_required': 'Introduza um nome para o estado.',
        'state_error_name_exists': 'Já existe um estado chamado «{name}». Escolha outro nome.',
        'state_error_crosshair_required': 'Escolha uma mira para este estado.',
        'state_error_hotkey_required': 'Escolha o botão que ativa este estado.',
        'state_error_hotkey_taken': 'Esse botão já é utilizado por {owner}. Escolha outro.',
        'state_mode_hold_short': 'manter',
        'state_mode_toggle_short': 'alternar',
        'state_no_hotkey': 'sem botão atribuído',
        'state_base_name': 'Principal',
        'state_base_description': 'Esta é a mira predefinida: aparece normalmente e é para ela que se regressa.',
        'state_list_title': 'Estados da mira',
        'state_list_heading': 'Estados de «{name}»',
        'state_list_description': 'Enquanto este preset estiver em uso, pressione o botão de um estado para mudar a mira: por exemplo, entre sem apontar e a apontar, ou use uma mira diferente em cada perspetiva. Cada estado guarda a sua própria mira, tamanho, posição, opacidade e cor.',
        'state_add': 'Adicionar estado',
        'state_max_count': 'Máximo de {max} estados por preset.',
        'state_empty': 'Ainda não há estados. Adicione um, por exemplo «A apontar» com o botão direito do rato no modo «Manter».',
        'state_reserved': 'o estado «{name}»',
        'state_default_aiming': 'A apontar',
        'state_default_name': 'Estado',
    },
    'fr': {
        'nav_crosshairs': 'Réticules',
        'nav_position': 'Taille et position',
        'nav_presets': 'Préréglages',
        'nav_settings': 'Paramètres',
        'page_crosshairs_title': 'Réticules',
        'page_crosshairs_sub': "Choisissez le design que vous voulez voir à l'écran. Vous pouvez ajouter vos propres images PNG.",
        'page_position_title': 'Taille et position',
        'page_position_sub': "Ajustez le réticule avec précision en le voyant en plein écran, sur une capture de votre jeu.",
        'page_presets_title': 'Préréglages',
        'page_presets_sub': "Enregistrez votre réticule avec le nom voulu, laissez-le se charger automatiquement à l'ouverture d'une application et ajoutez des états qui changent le réticule en appuyant sur un bouton.",
        'page_settings_title': 'Paramètres',
        'lbl_library': 'Bibliothèque',
        'btn_add_crosshair': 'Ajouter un réticule',
        'lbl_no_crosshairs': "Pas encore de réticules. Cliquez sur «Ajouter un réticule» pour importer une image.",
        'lbl_preview': 'Aperçu',
        'lbl_opacity': 'OPACITÉ',
        'lbl_color': 'COULEUR DU RÉTICULE',
        'lbl_no_crosshair': 'Aucun réticule sélectionné',
        'lbl_fullscreen_editor': 'Éditeur plein écran',
        'btn_open_editor': "Ouvrir l'éditeur plein écran",
        'lbl_current_values': 'Valeurs actuelles',
        'btn_center': 'Centrer le réticule',
        'lbl_size': 'TAILLE',
        'lbl_offset': 'DÉCALAGE',
        'lbl_opac_metric': 'OPACITÉ',
        'lbl_monitor': 'Moniteur de jeu',
        'lbl_monitor_desc': 'Le réticule est dessiné centré sur le moniteur que vous choisissez.',
        'lbl_current_config': 'CONFIG. ACTUELLE',
        'btn_save_preset': 'Enregistrer comme préréglage',
        'lbl_your_presets': 'Vos préréglages',
        'lbl_no_presets_title': "Pas encore de préréglages",
        'lbl_no_presets_desc': "Configurez votre réticule comme vous le souhaitez et cliquez sur «Enregistrer comme préréglage». Vous pouvez y revenir d'un clic ou le faire se charger automatiquement avec votre jeu.",
        'btn_apply': 'Appliquer',
        'lbl_applied': 'Appliqué',
        'lbl_automatic': 'Automatique',
        'lbl_appearance': 'Apparence',
        'lbl_activation': 'Activation',
        'lbl_activation_desc': 'Activez le raccourci, la détection automatique ou les deux.',
        'lbl_manual_hotkey': 'Touche ou bouton de manette pour afficher ou masquer le réticule',
        'lbl_auto_desc': "Le réticule n'apparaît que lorsqu'une application avec un préréglage automatique est au premier plan et charge ce préréglage.",
        'btn_manage_presets': 'Gérer les préréglages',
        'mode_manual_title': 'Raccourci clavier ou manette',
        'mode_manual_desc': 'Affiche ou masque le réticule lorsque vous appuyez sur une touche ou un bouton.',
        'mode_auto_title': "Automatique à l'ouverture d'un jeu",
        'mode_auto_desc': "Apparaît seul, avec son préréglage, lorsque l'application est au premier plan.",
        'lbl_background': 'Arrière-plan',
        'lbl_tray': 'Continuer à fonctionner à la fermeture',
        'lbl_tray_desc': "L'application se réduit dans la barre des tâches et le réticule continue de fonctionner.",
        'lbl_startup': 'Démarrer avec Windows',
        'lbl_startup_desc': "S'ouvre en arrière-plan au démarrage de l'ordinateur.",
        'lbl_language': 'Langue',
        'lbl_language_desc': "Changer la langue de toute l'interface.",
        'tray_show': 'Ouvrir le panneau de contrôle',
        'tray_edit': 'Modifier la taille et la position',
        'tray_hide': 'Masquer le réticule',
        'tray_show_crosshair': 'Afficher le réticule',
        'btn_enable_crosshair': 'Activer le réticule',
        'btn_disable_crosshair': 'Désactiver le réticule',
        'hotkey_error': "Impossible d'enregistrer ce raccourci. Essayez une autre touche ou exécutez l'application en tant qu'administrateur.",
        'theme_dark': 'Sombre',
        'theme_gray': 'Gris',
        'theme_light': 'Clair',
        'theme_tooltip': 'Thème {theme}',
        'theme_applied': 'Thème {theme} appliqué',
        'color_original': 'Original',
        'color_original_tip': 'Original (sans teinte)',
        'color_white': 'Blanc',
        'color_red': 'Rouge',
        'color_orange': 'Orange',
        'color_yellow': 'Jaune',
        'color_green': 'Vert',
        'color_cyan': 'Cyan',
        'color_blue': 'Bleu',
        'color_violet': 'Violet',
        'color_pink': 'Rose',
        'color_custom': 'Personnalisé',
        'color_no_tint': 'sans teinte',
        'editor_title': 'Éditeur de réticule',
        'editor_drag_tooltip': 'Faites glisser pour déplacer ce panneau',
        'editor_size': 'Taille',
        'editor_opacity': 'Opacité',
        'editor_position': 'Position',
        'editor_center': 'Centrer',
        'editor_background': 'Arrière-plan',
        'editor_bg_screenshot': 'Capture d’écran',
        'editor_bg_plain': 'Couleur unie',
        'editor_bg_grid': 'Grille',
        'editor_guides': 'Repères',
        'editor_cancel': 'Annuler',
        'editor_cancel_tooltip': 'Annuler les modifications (Esc)',
        'editor_save_exit': 'Enregistrer et quitter',
        'editor_save_tooltip': 'Appliquer les modifications (Entrée)',
        'editor_hint_arrows': 'Flèches',
        'editor_hint_move': 'déplacer (Maj ×10)',
        'editor_hint_size': 'taille',
        'editor_hint_center': 'centrer',
        'editor_hint_guides': 'repères',
        'editor_hint_background': 'arrière-plan',
        'editor_hint_save': 'enregistrer',
        'editor_hint_cancel': 'annuler',
        'btn_new_group': 'Nouveau groupe',
        'group_rename': 'Renommer le groupe',
        'group_delete': 'Supprimer le groupe',
        'group_move_to': 'Déplacer vers le groupe',
        'lbl_group': 'Groupe',
        'dialog_new_group_title': 'Nouveau groupe',
        'dialog_new_group_prompt': 'Nom du groupe:',
        'dialog_rename_group_title': 'Renommer le groupe',
        'dialog_rename_group_prompt': 'Nouveau nom du groupe:',
        'common_cancel': 'Annuler',
        'common_save': 'Enregistrer',
        'common_yes': 'Oui',
        'common_no': 'Non',
        'common_browse': 'Parcourir',
        'common_undo_warning': 'Cette action est irréversible.',
        'preset_auto_applies': 'Appliqué automatiquement à l’ouverture de {app}',
        'preset_no_automation': 'Aucune application automatique',
        'preset_auto_tooltip': 'Appliquer ce préréglage automatiquement à l’ouverture de son application',
        'more_options': 'Plus d’options',
        'preset_edit': 'Modifier',
        'preset_states': 'États du réticule',
        'preset_update_current': 'Mettre à jour avec les réglages actuels',
        'preset_duplicate': 'Dupliquer',
        'preset_delete': 'Supprimer',
        'preset_edit_title': 'Modifier le préréglage',
        'preset_new_title': 'Nouveau préréglage',
        'preset_save_title': 'Enregistrer comme préréglage',
        'preset_save_description': 'Le réticule, la taille, la position, l’opacité et la couleur seront enregistrés.',
        'preset_edit_description': 'Modifier le nom ou l’application associée.',
        'preset_settings_heading': 'Réglages du préréglage',
        'preset_use_current': 'Utiliser les réglages actuels',
        'preset_use_current_tooltip': 'Remplacer les réglages de ce préréglage par ceux affichés actuellement',
        'preset_name_heading': 'Nom',
        'preset_name_placeholder': 'Ex. Valorant · compétitif',
        'preset_automation_heading': 'Automatisation',
        'preset_auto_label': 'Appliquer à l’ouverture d’une application',
        'preset_auto_description': 'Ce préréglage se charge automatiquement lorsque cette application est au premier plan.',
        'preset_app_placeholder': 'Nom du jeu, processus (.exe) ou titre de fenêtre',
        'preset_detect_button': 'Détecter une application ouverte',
        'preset_select_executable': 'Sélectionner un exécutable',
        'preset_executable_filter': 'Exécutables (*.exe)',
        'preset_detect_countdown': 'Passez maintenant à votre jeu ou application : {seconds} s',
        'preset_detect_none': 'Aucune application détectée. Réessayez et cliquez sur sa fenêtre.',
        'preset_detected': 'Détectée : {app}',
        'preset_save_changes': 'Enregistrer les modifications',
        'preset_save_button': 'Enregistrer le préréglage',
        'preset_error_name_required': 'Saisissez un nom pour le préréglage.',
        'preset_error_name_exists': 'Un préréglage nommé « {name} » existe déjà. Choisissez un autre nom.',
        'preset_error_app_required': 'Indiquez l’application qui activera ce préréglage ou désactivez l’automatisation.',
        'preset_error_app_exists': 'Le préréglage « {name} » est déjà appliqué automatiquement à cette application.',
        'preset_add_button': '+ Préréglage',
        'preset_count_one': '{count} enregistré',
        'preset_count_many': '{count} enregistrés',
        'preset_current_unsaved': 'Réglages actuels non enregistrés comme préréglage',
        'preset_current_state': 'Préréglage « {preset} » · état « {state} »',
        'preset_current': 'Préréglage « {name} »',
        'preset_default_name': 'Préréglage',
        'preset_saved': 'Préréglage « {name} » enregistré',
        'preset_updated': 'Préréglage « {name} » mis à jour',
        'preset_updated_current': 'Préréglage « {name} » mis à jour avec les réglages actuels',
        'preset_copy_suffix': '(copie)',
        'preset_duplicated': 'Préréglage dupliqué sous le nom « {name} »',
        'preset_delete_title': 'Supprimer le préréglage',
        'preset_delete_question': 'Supprimer le préréglage « {name} » ?\n{warning}',
        'preset_deleted': 'Préréglage « {name} » supprimé',
        'preset_applied': 'Préréglage « {name} » appliqué',
        'preset_moved': 'Préréglage « {name} » déplacé vers « {group} »',
        'preset_auto_conflict': 'Le préréglage « {name} » est déjà appliqué automatiquement à {app}.\nDésactivez-le d’abord pour utiliser celui-ci.',
        'preset_auto_enabled': 'Application automatique activée pour « {name} »',
        'preset_auto_disabled': 'Application automatique désactivée pour « {name} »',
        'group_exists': 'Le groupe « {name} » existe déjà.',
        'group_created': 'Groupe « {name} » créé',
        'group_name_exists': 'Un groupe nommé « {name} » existe déjà.',
        'group_renamed': 'Groupe renommé en « {name} »',
        'group_delete_question': 'Supprimer le groupe « {name} » ?\nSes préréglages seront déplacés vers « General ».',
        'group_deleted': 'Groupe « {name} » supprimé',
        'states_saved': 'États de « {name} » enregistrés',
        'state_binding_error': 'Impossible d’enregistrer le bouton pour : {names}. Essayez un autre bouton ou exécutez l’application en tant qu’administrateur.',
        'state_reserved_global_hotkey': 'le raccourci utilisé pour afficher ou masquer le réticule',
        'state_new_title': 'Nouvel état',
        'state_edit_title': 'Modifier l’état',
        'state_dialog_description': 'Choisissez l’apparence du réticule dans cet état et le bouton qui l’active.',
        'state_save_button': 'Enregistrer l’état',
        'state_preview': 'Aperçu',
        'state_crosshair': 'Réticule',
        'state_color': 'Couleur',
        'state_name': 'Nom',
        'state_name_placeholder': 'Ex. En visée',
        'state_size': 'Taille',
        'state_position': 'Position par rapport au centre',
        'state_center': 'Centrer',
        'state_opacity': 'Opacité',
        'state_fullscreen_button': 'Ajuster en plein écran',
        'state_fullscreen_tooltip': 'Ouvrir l’éditeur pour positionner et redimensionner le réticule de cet état',
        'state_hotkey_section': 'Bouton qui active cet état',
        'state_hotkey_hint': 'Appuyez pour assigner une gâchette, un bouton de manette, de souris ou une touche',
        'state_mode_hold': 'Maintenir : actif uniquement tant que le bouton est enfoncé',
        'state_mode_toggle': 'Basculer : appuyer une fois pour activer, une autre fois pour revenir',
        'state_error_name_required': 'Saisissez un nom pour l’état.',
        'state_error_name_exists': 'Un état nommé « {name} » existe déjà. Choisissez un autre nom.',
        'state_error_crosshair_required': 'Choisissez un réticule pour cet état.',
        'state_error_hotkey_required': 'Choisissez le bouton qui active cet état.',
        'state_error_hotkey_taken': 'Ce bouton est déjà utilisé par {owner}. Choisissez-en un autre.',
        'state_mode_hold_short': 'maintenir',
        'state_mode_toggle_short': 'basculer',
        'state_no_hotkey': 'aucun bouton assigné',
        'state_base_name': 'Principal',
        'state_base_description': 'C’est le réticule par défaut : il s’affiche normalement et c’est à lui que l’on revient.',
        'state_list_title': 'États du réticule',
        'state_list_heading': 'États de « {name} »',
        'state_list_description': 'Lorsque ce préréglage est utilisé, appuyez sur le bouton d’un état pour changer de réticule : par exemple entre le tir sans visée et la visée, ou pour utiliser un réticule différent selon la perspective. Chaque état enregistre son propre réticule, sa taille, sa position, son opacité et sa couleur.',
        'state_add': 'Ajouter un état',
        'state_max_count': 'Maximum : {max} états par préréglage.',
        'state_empty': 'Aucun état pour le moment. Ajoutez-en un, par exemple « En visée » avec le bouton droit de la souris en mode « Maintenir ».',
        'state_reserved': 'l’état « {name} »',
        'state_default_aiming': 'En visée',
        'state_default_name': 'État',
    },
}

_current_language = 'es'


def set_language(code):
    global _current_language
    if code in TRANSLATIONS:
        _current_language = code


def get_language():
    return _current_language


def tr(key):
    lang = TRANSLATIONS.get(_current_language, TRANSLATIONS['es'])
    return lang.get(key, TRANSLATIONS['es'].get(key, key))


def app_logo_path():
    app_root = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(app_root, 'assets', 'akros_crosshair.png')


def load_app_logo():
    path = app_logo_path()
    pixmap = QPixmap(path)
    if pixmap.isNull():
        raise FileNotFoundError(f'No se pudo cargar el logotipo de la aplicacion: {path}')
    return pixmap


def make_app_icon():
    return QIcon(load_app_logo())


# Generacion de iconos vectoriales para la barra de navegacion
def _icon_pixmap(kind, color, size=20, dpr=2):
    px = QPixmap(size * dpr, size * dpr)
    px.setDevicePixelRatio(dpr)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color), 1.7)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    c = size / 2.0
    if kind == 'miras':
        p.drawEllipse(QPointF(c, c), 5.2, 5.2)
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            p.drawLine(QPointF(c + dx * 7.6, c + dy * 7.6), QPointF(c + dx * 9.6, c + dy * 9.6))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(c, c), 1.3, 1.3)
    elif kind == 'position':
        a, b = 3.2, size - 3.2
        k = 4.2
        for (x, y, sx, sy) in ((a, a, 1, 1), (b, a, -1, 1), (a, b, 1, -1), (b, b, -1, -1)):
            p.drawPolyline(QPointF(x + sx * k, y), QPointF(x, y), QPointF(x, y + sy * k))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(c, c), 1.9, 1.9)
    elif kind == 'presets':
        for i, (y, kx) in enumerate(((5.2, 7.5), (10, 13), (14.8, 9))):
            p.setPen(pen)
            p.drawLine(QPointF(3.2, y), QPointF(size - 3.2, y))
            p.setBrush(QColor(C['side']))
            p.drawEllipse(QPointF(kx, y), 2.3, 2.3)
    elif kind == 'activation':
        p.drawArc(QRectF(c - 6, c - 5.4, 12, 12), 120 * 16, -300 * 16)
        p.drawLine(QPointF(c, 2.6), QPointF(c, c - 0.5))
    elif kind == 'settings':
        import math
        p.drawEllipse(QPointF(c, c), 2.7, 2.7)
        p.drawEllipse(QPointF(c, c), 6.0, 6.0)
        for i in range(8):
            ang = math.radians(i * 45)
            p.drawLine(QPointF(c + math.cos(ang) * 6.0, c + math.sin(ang) * 6.0),
                       QPointF(c + math.cos(ang) * 8.4, c + math.sin(ang) * 8.4))
    p.end()
    return px


def make_nav_icon(kind):
    icon = QIcon()
    icon.addPixmap(_icon_pixmap(kind, C['muted']), QIcon.Normal, QIcon.Off)
    icon.addPixmap(_icon_pixmap(kind, C['text']), QIcon.Active, QIcon.Off)
    icon.addPixmap(_icon_pixmap(kind, C['accent']), QIcon.Normal, QIcon.On)
    icon.addPixmap(_icon_pixmap(kind, C['accent']), QIcon.Active, QIcon.On)
    return icon


# Generacion del icono para el menu de opciones adicionales
def make_dots_icon():
    icon = QIcon()
    for color, mode in ((C['muted'], QIcon.Normal), (C['strong'], QIcon.Active)):
        px = QPixmap(40, 40)
        px.setDevicePixelRatio(2)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        for x in (5, 10, 15):
            p.drawEllipse(QPointF(x, 10), 1.6, 1.6)
        p.end()
        icon.addPixmap(px, mode, QIcon.Off)
    return icon


# Recursos graficos generados en carpeta temporal
def _asset(name, painter_fn, size=16):
    folder = os.path.join(tempfile.gettempdir(), 'crosshair_pro_assets')
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name + '.png')
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing, True)
    painter_fn(p)
    p.end()
    px.save(path, 'PNG')
    return path.replace('\\', '/')


def _chevron(up, color):
    def draw(p):
        pen = QPen(QColor(color), 1.8)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        if up:
            p.drawPolyline(QPointF(4.5, 10), QPointF(8, 6.5), QPointF(11.5, 10))
        else:
            p.drawPolyline(QPointF(4.5, 6), QPointF(8, 9.5), QPointF(11.5, 6))
    return draw


def _tick(p):
    pen = QPen(QColor('#FFFFFF'), 2.2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.drawPolyline(QPointF(3.8, 8.4), QPointF(6.7, 11.2), QPointF(12.2, 4.8))


def build_stylesheet():
    down = _asset('chev_down', _chevron(False, C['muted']))
    up = _asset('chev_up', _chevron(True, C['muted']))
    tick = _asset('tick', _tick)
    return f'''
QWidget {{
    color: {C['text']};
    font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}}
QMainWindow, QDialog, QMessageBox, #Root {{ background-color: {C['bg']}; }}
QLabel {{ background: transparent; }}
QToolTip {{
    background-color: {C['card']}; color: {C['text']};
    border: 1px solid {C['border_hi']}; padding: 5px 8px;
}}

#Sidebar {{ background-color: {C['side']}; border-right: 1px solid {C['border']}; }}
#AppTitle {{ font-size: 15px; font-weight: 700; color: {C['strong']}; }}
#PageTitle {{ font-size: 24px; font-weight: 700; color: {C['strong']}; }}
#PageSub {{ font-size: 13px; color: {C['muted']}; }}
#CardTitle {{ font-size: 15px; font-weight: 600; color: {C['strong']}; }}
#Muted {{ color: {C['muted']}; font-size: 12px; }}
#MutedSmall {{ color: {C['muted']}; font-size: 11px; }}
#Metric {{ font-size: 22px; font-weight: 700; color: {C['strong']}; }}
#MetricLabel {{ font-size: 11px; font-weight: 600; color: {C['muted']}; letter-spacing: 1px; }}
#Status {{ color: {C['warn']}; font-size: 12px; }}

QFrame#Card {{
    background-color: {C['card']}; border: 1px solid {C['border']}; border-radius: 14px;
}}
QFrame#Tile {{
    background-color: {C['input']}; border: 1px solid {C['border']}; border-radius: 10px;
}}

QPushButton {{
    background-color: {C['card']}; border: 1px solid {C['border_hi']}; border-radius: 8px;
    padding: 8px 16px; color: {C['text']}; font-weight: 600;
}}
QPushButton:hover {{ background-color: {C['card_hi']}; border-color: {C['border_hi']}; }}
QPushButton:pressed {{ background-color: {C['card']}; }}
QPushButton:disabled {{ color: {C['off']}; background-color: {C['input']}; border-color: {C['border']}; }}
QPushButton:focus {{ border-color: {C['accent']}; }}
QPushButton#Primary {{
    background-color: {C['accent_dark']}; border: 1px solid {C['accent']}; color: white;
}}
QPushButton#Primary:hover {{ background-color: {C['accent_hover']}; }}
QPushButton#Primary:pressed {{ background-color: {C['accent_dark']}; }}
QPushButton#Primary:disabled {{ background-color: {C['input']}; border: 1px solid {C['border']}; color: {C['off']}; }}
QPushButton#Ghost {{ background: transparent; border: 1px solid {C['border_hi']}; color: {C['muted']}; }}
QPushButton#Ghost:hover {{ color: {C['text']}; background-color: {C['card']}; }}

QPushButton#Nav {{
    text-align: left; padding: 12px 20px; border: none;
    border-left: 3px solid transparent; border-radius: 0;
    background: transparent; color: {C['muted']}; font-size: 14px; font-weight: 600;
}}
QPushButton#Nav:hover {{ background-color: {C['input']}; color: {C['text']}; }}
QPushButton#Nav:checked {{
    background-color: {C['nav_active']}; color: {C['accent']}; border-left: 3px solid {C['accent']};
}}

#Section {{ font-size: 11px; font-weight: 700; color: {C['muted']}; letter-spacing: 1px; }}
#Error {{ color: {C['danger']}; font-size: 12px; }}
#MetaOn {{ color: {C['accent']}; font-size: 12px; font-weight: 600; }}
#PresetName {{ font-size: 15px; font-weight: 700; color: {C['strong']}; }}
#Badge {{
    background-color: {C['accent_dark']}; color: white; border-radius: 8px;
    padding: 2px 8px; font-size: 10px; font-weight: 700; letter-spacing: 1px;
}}
#DialogTitle {{ font-size: 18px; font-weight: 700; color: {C['strong']}; }}

QFrame#PresetCard {{
    background-color: {C['input']}; border: 1px solid {C['border']}; border-radius: 12px;
}}
QFrame#PresetCard:hover {{ background-color: {C['card_hi']}; border-color: {C['border_hi']}; }}
QFrame#PresetCard[inuse="true"] {{ border: 1px solid {C['accent']}; background-color: {C['card_hi']}; }}
QFrame#EmptyState {{
    background-color: transparent; border: 1px dashed {C['border_hi']}; border-radius: 12px;
}}

QToolButton#IconBtn {{
    background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 4px;
}}
QToolButton#IconBtn:hover {{ background-color: {C['card']}; border-color: {C['border_hi']}; }}
QToolButton#IconBtn::menu-indicator {{ image: none; width: 0; }}

QLineEdit#HexInput {{ font-family: 'Consolas', 'Cascadia Mono', monospace; font-weight: 600; }}

QFrame#CrosshairCard {{
    background-color: {C['input']}; border: 1px solid {C['border']}; border-radius: 10px;
}}
QFrame#CrosshairCard:hover {{ background-color: {C['card_hi']}; border-color: {C['border_hi']}; }}
QFrame#CrosshairCard[selected="true"] {{
    background-color: {C['card_hi']}; border: 2px solid {C['accent']};
}}

QFrame#ModeCard {{
    background-color: {C['card']}; border: 1px solid {C['border']}; border-radius: 14px;
}}
QFrame#ModeCard:hover {{ border-color: {C['border_hi']}; }}

QSlider::groove:horizontal {{ height: 6px; background: {C['input']}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {C['accent']}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: #FFFFFF; border: 2px solid {C['accent_dark']};
    width: 14px; height: 14px; margin: -6px 0; border-radius: 9px;
}}
QSlider::handle:horizontal:hover {{ border-color: {C['accent']}; }}

QSpinBox, QComboBox, QLineEdit {{
    background-color: {C['input']}; border: 1px solid {C['border_hi']}; border-radius: 8px;
    padding: 6px 10px; color: {C['strong']}; min-height: 18px;
    selection-background-color: {C['accent_dark']};
}}
QSpinBox:focus, QComboBox:focus, QLineEdit:focus {{ border-color: {C['accent']}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 20px; border: none; background: transparent; subcontrol-origin: border;
}}
QSpinBox::up-button {{ subcontrol-position: top right; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; }}
QSpinBox::up-arrow {{ image: url({up}); width: 12px; height: 12px; }}
QSpinBox::down-arrow {{ image: url({down}); width: 12px; height: 12px; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url({down}); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background-color: {C['card']}; border: 1px solid {C['border_hi']}; border-radius: 6px;
    selection-background-color: {C['accent_dark']}; selection-color: {C['strong']}; outline: 0; padding: 4px;
}}

QCheckBox {{ spacing: 10px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;
    border: 1px solid {C['border_hi']}; background: {C['input']};
}}
QCheckBox::indicator:checked {{
    background: {C['accent_dark']}; border-color: {C['accent']}; image: url({tick});
}}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {C['border']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {C['border_hi']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ height: 0; }}

QMenu {{
    background-color: {C['card']}; border: 1px solid {C['border_hi']}; border-radius: 8px; padding: 6px;
}}
QMenu::item {{ padding: 8px 26px; border-radius: 6px; }}
QMenu::item:selected {{ background-color: {C['card_hi']}; }}
QMenu::separator {{ height: 1px; background: {C['border']}; margin: 5px 8px; }}

QMessageBox QLabel {{ color: {C['text']}; font-size: 13px; }}
QMessageBox QPushButton, QDialog QPushButton {{ min-width: 84px; }}

QStatusBar {{
    background-color: {C['side']}; color: {C['muted']}; border-top: 1px solid {C['border']};
    font-size: 12px; padding-left: 8px;
}}
QStatusBar::item {{ border: none; }}

QFrame#EditorPanel {{
    background-color: {C['card']}; border: 1px solid {C['border_hi']}; border-radius: 16px;
}}
#EditorTitle {{ font-size: 14px; font-weight: 700; color: {C['strong']}; }}
#EditorGrip {{ color: {C['muted']}; font-size: 12px; }}
#Kbd {{
    background-color: {C['card']}; border: 1px solid {C['border_hi']}; border-radius: 5px;
    padding: 1px 6px; color: {C['text']}; font-size: 11px; font-weight: 600;
}}
'''
