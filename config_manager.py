# Modulo para administracion de configuracion persistente y perfiles predefinidos
import os
import re
import copy
import json
import sys
import uuid


def get_app_data_dir():
    if getattr(sys, 'frozen', False):
        local_app_data = os.environ.get('LOCALAPPDATA')
        if not local_app_data:
            local_app_data = os.path.join(os.path.expanduser('~'), 'AppData', 'Local')
        return os.path.join(local_app_data, 'AkrosCrossHair')
    return os.path.dirname(os.path.abspath(__file__))


APP_DATA_DIR = get_app_data_dir()
CONFIG_FILE = os.path.join(APP_DATA_DIR, 'config.json')

BACKGROUNDS = ('screenshot', 'plain', 'grid')
THEME_NAMES = ('dark', 'gray', 'light')

DEFAULT_CONFIG = {
    'crosshair_file': 'crosshair.png',
    'size': 48,
    'offset_x': 0,
    'offset_y': 0,
    'opacity': 1.0,
    'color': 'original',
    'manual_enabled': True,
    'auto_enabled': False,
    'manual_active': True,
    'hotkey': 'F2',
    'monitor_index': 0,
    'close_to_tray': True,
    'start_with_windows': False,
    'editor_background': 'screenshot',
    'editor_guides': True,
    'theme': 'dark',
    'language': 'es',
    'crosshair_configs': {},
    'preset_groups': ['General'],
    'presets': []
}

HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')
PRESET_NAME_MAX = 40
STATE_NAME_MAX = 40
MAX_STATES = 6
# Modos de activacion para alternar o mantener pulsado
STATE_MODES = ('toggle', 'hold')


def _to_int(value, default, lo, hi):
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, value))


def _to_float(value, default, lo, hi):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, value))


def _to_bool(value, default):
    return value if isinstance(value, bool) else default


def _to_str(value, default):
    return value.strip() if isinstance(value, str) and value.strip() else default


# Validacion de formato de color para la mira
def _to_color(value, default='original'):
    if isinstance(value, str):
        v = value.strip()
        if HEX_RE.match(v):
            return v.upper()
        if v.lower() in ('original', 'none', ''):
            return 'original'
    return default


def new_preset_id():
    return uuid.uuid4().hex[:10]


# Extraccion de propiedades visuales de la mira
def _visual_values(raw, fallback_file='crosshair.png'):
    return {
        'crosshair_file': _to_str(raw.get('crosshair_file'), fallback_file),
        'size': _to_int(raw.get('size'), 48, 8, 400),
        'offset_x': _to_int(raw.get('offset_x'), 0, -10000, 10000),
        'offset_y': _to_int(raw.get('offset_y'), 0, -10000, 10000),
        'opacity': _to_float(raw.get('opacity'), 1.0, 0.05, 1.0),
        'color': _to_color(raw.get('color')),
    }


# Saneamiento de variantes configuradas para un perfil
def sanitize_state(raw, fallback_file, fallback_name='Estado'):
    if not isinstance(raw, dict):
        return None
    state = {
        'id': _to_str(raw.get('id'), new_preset_id()),
        'name': _to_str(raw.get('name'), fallback_name)[:STATE_NAME_MAX],
    }
    state.update(_visual_values(raw, fallback_file))
    state['hotkey'] = _to_str(raw.get('hotkey'), '')
    mode = raw.get('mode')
    state['mode'] = mode if mode in STATE_MODES else 'toggle'
    return state


def _sanitize_states(raw_list, fallback_file):
    states, ids, names = [], set(), set()
    for i, item in enumerate(raw_list if isinstance(raw_list, list) else []):
        if len(states) >= MAX_STATES:
            break
        st = sanitize_state(item, fallback_file, f'Estado {i + 1}')
        if st is None:
            continue
        while st['id'] in ids:
            st['id'] = new_preset_id()
        base, n = st['name'], 2
        while st['name'].lower() in names:
            st['name'] = f'{base[:STATE_NAME_MAX - 4]} ({n})'
            n += 1
        ids.add(st['id'])
        names.add(st['name'].lower())
        states.append(st)
    return states


# Saneamiento y estructura de perfiles predefinidos
def sanitize_preset(raw, fallback_name='Preset'):
    if not isinstance(raw, dict):
        return None
    preset = {
        'id': _to_str(raw.get('id'), new_preset_id()),
        'name': _to_str(raw.get('name'), fallback_name)[:PRESET_NAME_MAX],
    }
    preset.update(_visual_values(raw))
    app = raw.get('app')
    preset['app'] = app.strip() if isinstance(app, str) else ''
    preset['auto_apply'] = _to_bool(raw.get('auto_apply'), False) and bool(preset['app'])
    preset['states'] = _sanitize_states(raw.get('states'), preset['crosshair_file'])
    grp = raw.get('group')
    preset['group'] = _to_str(grp, 'General') if grp else 'General'
    return preset


def _sanitize_presets(raw_list):
    presets, ids, names = [], set(), set()
    for i, item in enumerate(raw_list if isinstance(raw_list, list) else []):
        p = sanitize_preset(item, f'Preset {i + 1}')
        if p is None:
            continue
        while p['id'] in ids:
            p['id'] = new_preset_id()
        base, n = p['name'], 2
        while p['name'].lower() in names:
            p['name'] = f'{base[:PRESET_NAME_MAX - 4]} ({n})'
            n += 1
        ids.add(p['id'])
        names.add(p['name'].lower())
        presets.append(p)
    return presets


# Migracion de perfiles antiguos hacia el nuevo formato automatico
def _migrate_game_profiles(game_profiles):
    migrated = []
    if isinstance(game_profiles, dict):
        for game, prof in game_profiles.items():
            if isinstance(game, str) and isinstance(prof, dict):
                migrated.append({**prof, 'name': game, 'app': game, 'auto_apply': True})
    return migrated


# Validacion de datos de configuracion
def sanitize_config(data):
    d = DEFAULT_CONFIG
    raw = data if isinstance(data, dict) else {}
    cfg = {}
    cfg.update(_visual_values(raw, d['crosshair_file']))
    cfg['size'] = _to_int(raw.get('size'), d['size'], 8, 400)
    cfg['opacity'] = _to_float(raw.get('opacity'), d['opacity'], 0.05, 1.0)
    legacy_mode = raw.get('activation_mode')
    manual_default = legacy_mode != 'auto'
    auto_default = legacy_mode == 'auto'
    cfg['manual_enabled'] = _to_bool(raw.get('manual_enabled'), manual_default)
    cfg['auto_enabled'] = _to_bool(raw.get('auto_enabled'), auto_default)
    manual_active_default = cfg['manual_enabled'] and not cfg['auto_enabled']
    if manual_active_default:
        # Migracion del interruptor general de activacion manual
        manual_active_default = _to_bool(raw.get('active'), True)
    cfg['manual_active'] = _to_bool(
        raw.get('manual_active'), manual_active_default)
    cfg['hotkey'] = _to_str(raw.get('hotkey'), d['hotkey'])
    cfg['monitor_index'] = _to_int(raw.get('monitor_index'), 0, 0, 16)
    cfg['close_to_tray'] = _to_bool(raw.get('close_to_tray'), d['close_to_tray'])
    cfg['start_with_windows'] = _to_bool(raw.get('start_with_windows'), d['start_with_windows'])
    bg = raw.get('editor_background')
    cfg['editor_background'] = bg if bg in BACKGROUNDS else d['editor_background']
    cfg['editor_guides'] = _to_bool(raw.get('editor_guides'), d['editor_guides'])
    theme = raw.get('theme')
    cfg['theme'] = theme if theme in THEME_NAMES else d['theme']
    lang = raw.get('language')
    cfg['language'] = lang if lang in ('es', 'en', 'pt', 'fr') else d.get('language', 'es')

    cc = raw.get('crosshair_configs')
    clean_cc = {}
    if isinstance(cc, dict):
        for k, v in cc.items():
            if isinstance(k, str) and isinstance(v, dict):
                vals = _visual_values(v)
                vals.pop('crosshair_file')
                clean_cc[k] = vals
    cfg['crosshair_configs'] = clean_cc

    if 'presets' in raw:
        source = raw.get('presets')
    else:
        source = _migrate_game_profiles(raw.get('game_profiles'))
    cfg['presets'] = _sanitize_presets(source)

    groups = raw.get('preset_groups')
    clean_groups = []
    if isinstance(groups, list):
        for g in groups:
            if isinstance(g, str) and g.strip() and g.strip() not in clean_groups:
                clean_groups.append(g.strip())
    if not clean_groups:
        clean_groups = ['General']
    for p in cfg['presets']:
        p_grp = p.get('group', 'General')
        if p_grp not in clean_groups:
            clean_groups.append(p_grp)
    cfg['preset_groups'] = clean_groups
    return cfg


# Carga de opciones guardadas del usuario
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return sanitize_config(json.load(f))
    except Exception:
        return copy.deepcopy(DEFAULT_CONFIG)


# Guardado seguro en disco
def save_config(cfg):
    tmp = CONFIG_FILE + '.tmp'
    try:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        os.replace(tmp, CONFIG_FILE)
        return True
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False

