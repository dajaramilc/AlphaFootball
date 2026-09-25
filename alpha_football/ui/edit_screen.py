# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla del Editor de Base de Datos (Pygame)
Permite modificar nombres, valoraciones, rasgos de jugadores y presupuestos, estilos tácticos
y nombres de equipos, guardarlos localmente, exportarlos e importarlos en formato JSON.
"""

import sys
import os
import json
import logging
import pygame

try:
    from alpha_football.ui.theme import (
        SCREEN_W, SCREEN_H, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
    )
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    COLORS = {
        'bg': '#0A0E1A', 'verde': '#00FF88', 'dorado': '#FFD700',
        'rojo': '#FF4444', 'azul': '#00BFFF', 'blanco': '#FFFFFF', 'panel': '#141A2E'
    }
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover):
        pygame.draw.rect(screen, (0, 191, 255) if hover else (20, 26, 46), rect, border_radius=5)
        return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)

# Opciones de los dropdowns
# v3.3.0: los 9 estilos del motor (los viejos del editor se mapean con normalizar_estilo).
from alpha_football.estilos import ESTILOS_UI as ESTILOS_TACTICOS, NOMBRE_ESTILO, normalizar_estilo
RASGOS_JUGADOR = ["ninguno", "regateador", "pulmon_de_hierro", "rustico", "lider"]
POSICIONES = ["POR", "DEF", "MED", "DEL"]

# v3.6.0: RESTAURAR BASE y las listas de los dropdowns con rects fijos, para despachar el clic
# ANTES que cualquier otro control (con un dropdown abierto el clic es solo suyo).
R_RESTAURAR = pygame.Rect(530, 505, 200, 36)

# v3.9.0: resto de rects del editor expuestos (los usa la ayuda H); render los usa tal cual.
R_COL_LISTAS = pygame.Rect(40, 100, 450, 500)
R_NOMBRE_LIGA = pygame.Rect(155, 146, 315, 28)
R_EQ_UP, R_EQ_DOWN = pygame.Rect(440, 180, 30, 30), pygame.Rect(440, 315, 30, 30)
R_JUG_UP, R_JUG_DOWN = pygame.Rect(440, 405, 30, 30), pygame.Rect(440, 540, 30, 30)
R_FORMULARIO = pygame.Rect(510, 100, 730, 500)
R_EQ_NOMBRE = pygame.Rect(530, 205, 350, 38)
R_EQ_PRESUPUESTO = pygame.Rect(530, 290, 350, 38)
R_EQ_ESTILO = pygame.Rect(530, 375, 350, 38)
R_EQ_DT = pygame.Rect(900, 375, 320, 38)
R_J_NOMBRE = pygame.Rect(530, 195, 300, 36)
R_J_APELLIDO = pygame.Rect(860, 195, 300, 36)
R_J_OVR = pygame.Rect(530, 275, 140, 36)
R_J_EDAD = pygame.Rect(700, 275, 130, 36)
R_J_POSICION = pygame.Rect(860, 275, 300, 36)
R_J_RASGO = pygame.Rect(530, 360, 300, 36)
R_J_POTENCIAL = pygame.Rect(860, 360, 140, 36)
R_ARCHIVO = pygame.Rect(530, 455, 400, 36)
R_EXPORTAR = pygame.Rect(950, 455, 120, 36)
R_IMPORTAR = pygame.Rect(1085, 455, 120, 36)
R_APLICAR = pygame.Rect(40, 615, 300, 50)
R_VOLVER = pygame.Rect(360, 615, 240, 50)          # v3.9.0: 240 (en 200 no cabía "VOLVER AL MENÚ")


def rect_tab_liga(i: int) -> pygame.Rect:
    """v3.9.0: pestaña i de ligas/copas (ING, ESP, ... LIB, UCL)."""
    return pygame.Rect(50 + i * 44, 110, 41, 30)


def rect_division(k: int) -> pygame.Rect:
    """v3.9.0: selector de 1ª (k=1) / 2ª (k=2) división."""
    return pygame.Rect(55 + (k - 1) * 46, 146, 42, 28)


def rect_fila(lista: str, i: int) -> pygame.Rect:
    """v3.9.0: fila visible i (0-4) de la lista 'equipos' (y=180) o 'jugadores' (y=405)."""
    return pygame.Rect(55, (180 if lista == 'equipos' else 405) + i * 36, 380, 32)


def _boton(screen, rect, texto: str, hover: bool, size: str = 'sm', color: str = 'blanco') -> None:
    """v3.9.0: botón con el texto UNA sola vez y en un tamaño que cabe (antes se escribía dos veces)."""
    draw_button(screen, rect, "", hover)
    col = COLORS['verde'] if hover else COLORS.get(color, COLORS['blanco'])
    txt = get_font(size).render(texto, True, col)
    screen.blit(txt, txt.get_rect(center=rect.center))


def _opciones_dropdown(tipo: str) -> list:
    """v3.6.0: [(valor, texto, rect)] de la lista desplegada del dropdown `tipo`."""
    if tipo == 'estilo_dt':
        return [(est, NOMBRE_ESTILO.get(est, est).upper(), pygame.Rect(530, 413 + i * 30, 350, 30))
                for i, est in enumerate(ESTILOS_TACTICOS)]
    if tipo == 'posicion':
        return [(pos, pos.upper(), pygame.Rect(860, 311 + i * 30, 300, 30)) for i, pos in enumerate(POSICIONES)]
    if tipo == 'rasgo':
        return [(rsg, rsg.upper(), pygame.Rect(530, 396 + i * 30, 300, 30)) for i, rsg in enumerate(RASGOS_JUGADOR)]
    return []


def _dibujar_dropdown(screen, estado: dict, mouse_pos, modo_jugador: bool) -> None:
    """v3.6.0: dibuja la lista del dropdown abierto AL FINAL (encima de IMPORTAR/RESTAURAR BASE)."""
    try:
        drop = estado.get('edit_dropdown_activo')
        if not drop or (drop == 'estilo_dt') == modo_jugador:
            return
        foco_d = int(estado.get('edit_drop_foco', 0) or 0)   # v4.2.0: opción con foco de teclado
        for i, (_valor, texto, r) in enumerate(_opciones_dropdown(drop)):
            pygame.draw.rect(screen, (30, 40, 70) if r.collidepoint(mouse_pos) or i == foco_d else (10, 14, 26), r)
            pygame.draw.rect(screen, (0, 191, 255), r, width=1)
            draw_text(screen, texto, (r.x + 12, r.y + 5), size='sm', color='blanco')
    except Exception as e:
        logger.error(f"No se pudo dibujar el dropdown del editor: {e}")

def _backfill_internacionales(db: dict) -> None:
    """
    v0.8.8: asegura que la DB del editor tenga las "ligas" internacionales editables
    ('libertadores' y 'champions'). Útil para bases editadas viejas que no las traían.
    """
    try:
        from alpha_football.data.internacional import get_pool_libertadores, get_pool_champions
        if not db.get('libertadores'):
            db['libertadores'] = [eq.to_dict() for eq in get_pool_libertadores()]
        if not db.get('champions'):
            db['champions'] = [eq.to_dict() for eq in get_pool_champions()]
    except Exception as e_intl:
        logger.error(f"Error al inicializar equipos internacionales en editor: {e_intl}")


def _backfill_potenciales(db: dict) -> None:
    """
    v0.8.9: siembra el `potencial` (techo de OVR) de cada jugador de la DB del editor que
    todavía no lo tenga (0/ausente). La base del editor se arma desde `to_dict()` (sin pasar
    por `market.asignar_valores_iniciales`), así que sin esto TODOS quedarían en 0 y el campo
    "Potencial" del editor mostraría siempre el OVR. Solo siembra donde falta → respeta los
    potenciales editados a mano. RNG sembrado por id → coincide con el que vería la carrera.
    """
    try:
        import random
        from alpha_football.desarrollo import calcular_potencial
    except Exception as e_imp:
        logger.error(f"No se pudo importar calcular_potencial para el editor: {e_imp}")
        return
    for equipos in db.values():
        if not isinstance(equipos, list):
            continue
        for equipo in equipos:
            for j in equipo.get('jugadores', []):
                try:
                    if j.get('potencial'):
                        continue
                    ovr = int(j.get('overall') or 0)
                    if not ovr:
                        attrs = [j.get('ataque'), j.get('defensa'), j.get('fisico'),
                                 j.get('tecnica'), j.get('mental')]
                        attrs = [int(a) for a in attrs if a is not None]
                        ovr = (sum(attrs) // len(attrs)) if attrs else 70
                    edad = int(j.get('edad', 25) or 25)
                    j['potencial'] = calcular_potencial(ovr, edad, random.Random(int(j.get('id', 0) or 0)))
                except Exception as e_pot:
                    logger.debug(f"No se pudo sembrar potencial de {j.get('nombre', '?')}: {e_pot}")


from alpha_football import paises as _paises

MAX_NOMBRE_LIGA = 40   # v3.7.0


def pestanas_editor() -> list:
    """v3.7.0: [(clave, texto)] = los 8 países (1ª; la 2ª con el selector) + las 2 copas."""
    return [(p['liga_id'], p['corto']) for p in _paises.PAISES] + [('libertadores', 'LIB'), ('champions', 'UCL')]


def _tipo_div(clave: str) -> tuple:
    """v3.7.0: 'segunda_seriea' -> ('seriea', 2); 'premier' -> ('premier', 1); copas -> (clave, None)."""
    clave = str(clave or '')
    if clave.startswith('segunda_') and clave[len('segunda_'):] in _paises.TIPOS_LIGA:
        return clave[len('segunda_'):], 2
    if clave in _paises.TIPOS_LIGA:
        return clave, 1
    return clave, None


def _backfill_ligas(db: dict) -> None:
    """
    v3.7.0: la base del editor tiene la 1ª y la 2ª ('segunda_<tipo>') de los 8 países con 12
    clubes: bases viejas (5 países, ligas de 6/8, sin 2ª) se completan con los datos, sin
    repetir nombres de club en ninguna liga. Nunca pisa los clubes ya editados.
    """
    claves = [_paises.clave_db(t, d) for t in _paises.TIPOS_LIGA for d in (1, 2)]
    usados = {eq.get('nombre') for c in claves for eq in (db.get(c) or []) if isinstance(eq, dict)}
    for tipo in _paises.TIPOS_LIGA:
        for div in (1, 2):
            clave = _paises.clave_db(tipo, div)
            lista = db.get(clave) if isinstance(db.get(clave), list) else []
            if len(lista) >= _paises.EQUIPOS_POR_LIGA:
                db[clave] = lista
                continue
            try:
                liga = _paises.cargar_datos_liga(tipo, div)
                if liga is not None:
                    from alpha_football.plantilla import expandir_liga
                    from alpha_football.market import escalar_presupuestos
                    # posicional (ver menu._completar_con_datos): los editados son los primeros
                    orden = list(liga.equipos[len(lista):]) + list(liga.equipos[:len(lista)])
                    liga.equipos = [eq for eq in orden if eq.nombre not in usados]
                    liga.equipos = liga.equipos[:_paises.EQUIPOS_POR_LIGA - len(lista)]
                    expandir_liga(liga, 20)
                    escalar_presupuestos(liga)
                    for eq in liga.equipos:
                        usados.add(eq.nombre)
                        lista.append(eq.to_dict())
            except Exception as e_bl:
                logger.error(f"Error al completar la liga {clave} en el editor: {e_bl}")
            db[clave] = lista


def cambiar_division_editor(estado: dict) -> None:
    """v3.7.0: alterna la pestaña del país entre su 1ª y su 2ª (las copas no tienen división)."""
    tipo, div = _tipo_div(estado.get('edit_liga_sel', 'premier'))
    if div is None:
        return
    estado['edit_liga_sel'] = _paises.clave_db(tipo, 2 if div == 1 else 1)
    for k, v in (('edit_equipo_idx', 0), ('edit_jugador_idx', -1), ('edit_squad_offset', 0),
                 ('edit_teams_offset', 0), ('edit_input_activo', None)):
        estado[k] = v


def nombre_liga_editor(estado: dict) -> str:
    """v3.7.0: el nombre (editado o por defecto) de la liga de la pestaña actual."""
    tipo, div = _tipo_div(estado.get('edit_liga_sel', 'premier'))
    if div is None:
        return ''
    campo = 'nombre_2a' if div == 2 else 'nombre'
    db = estado.get('edited_db') or {}
    propio = ((db.get('_ligas') or {}).get(tipo) or {}).get(campo)
    return propio if propio is not None else _paises.nombre_liga_defecto(tipo, div)


def set_nombre_liga_editor(estado: dict, nombre: str) -> None:
    """v3.7.0: renombra en memoria (se persiste con APLICAR Y GUARDAR); máx. 40 caracteres."""
    try:
        tipo, div = _tipo_div(estado.get('edit_liga_sel', 'premier'))
        db = estado.get('edited_db')
        if div is None or db is None:
            return
        campo = 'nombre_2a' if div == 2 else 'nombre'
        db.setdefault('_ligas', {}).setdefault(tipo, {})[campo] = str(nombre or '')[:MAX_NOMBRE_LIGA]
    except Exception as e_nl:
        logger.error(f"No se pudo renombrar la liga en el editor: {e_nl}")


def cargar_base_datos_inicial(estado: dict) -> dict:
    """Carga la base de datos editada desde JSON si existe, o la inicializa desde los módulos base."""
    if 'edited_db' in estado:
        return estado['edited_db']

    ruta_db = "alpha_football_edited_db.json"
    if os.path.exists(ruta_db):
        try:
            with open(ruta_db, "r", encoding="utf-8") as f:
                db = json.load(f)
                _backfill_ligas(db)            # v3.7.0: 8 países × 1ª/2ª con 12 clubes
                _backfill_internacionales(db)  # v0.8.8: añadir int'l si faltan
                _backfill_potenciales(db)      # v0.8.9: sembrar potencial donde falte
                estado['edited_db'] = db
                return db
        except Exception as e:
            logger.error(f"Error al cargar base de datos editada: {e}")

    # Inicializar desde los datos base del juego
    db = {}
    _backfill_ligas(db)   # v3.7.0: 8 países × 1ª/2ª desde los datos

    # v0.8.8: añadir los equipos internacionales (Libertadores / Champions) editables.
    _backfill_internacionales(db)
    _backfill_potenciales(db)  # v0.8.9: sembrar potencial donde falte

    estado['edited_db'] = db
    return db

def guardar_base_datos(estado: dict) -> bool:
    """Guarda la base de datos en memoria en el archivo local JSON."""
    try:
        db = estado.get('edited_db')
        if not db:
            return False
        ruta_db = "alpha_football_edited_db.json"
        with open(ruta_db, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        _paises._cache_overrides['mtime'] = None   # v3.7.0: nombres de liga nuevos
        return True
    except Exception as e:
        logger.error(f"Error al guardar base de datos editada: {e}")
        return False

def restaurar_base(estado: dict) -> dict:
    """v3.6.0: borra la base editada del disco y recarga la original (antes, inline en render)."""
    ruta_db = "alpha_football_edited_db.json"
    if os.path.exists(ruta_db):
        try:
            os.remove(ruta_db)
        except Exception as e:
            logger.error(f"No se pudo borrar la base editada: {e}")
    estado.pop('edited_db', None)
    db = cargar_base_datos_inicial(estado)
    estado['edit_equipo_idx'] = 0
    estado['edit_jugador_idx'] = -1
    estado['edit_mensaje'] = "Base de datos restaurada."
    estado['edit_mensaje_ticks'] = pygame.time.get_ticks()
    return db


def render(screen: pygame.Surface, estado: dict) -> str | None:
    """Renderiza la pantalla de edición de base de datos."""
    try:
        # 1. Asegurar base de datos cargada
        db = cargar_base_datos_inicial(estado)
        
        # Inicializar variables de UI en estado si faltan
        estado.setdefault('edit_liga_sel', 'premier')
        estado.setdefault('edit_equipo_idx', 0)
        estado.setdefault('edit_jugador_idx', -1)  # -1 significa editar equipo, >=0 editar ese jugador
        estado.setdefault('edit_input_activo', None)  # Campo activo de texto
        estado.setdefault('edit_dropdown_activo', None)  # Dropdown activo ('estilo_dt' o 'rasgo' o 'posicion')
        estado.setdefault('edit_squad_offset', 0)
        estado.setdefault('edit_teams_offset', 0)
        estado.setdefault('edit_filepath', 'alpha_football_db_custom.json')
        estado.setdefault('edit_mensaje', '')
        estado.setdefault('edit_mensaje_ticks', 0)
        # v3.9.0: con un campo de texto activo, H se escribe (no abre la ayuda)
        estado['texto_activo'] = bool(estado.get('edit_input_activo'))
        
        liga_sel = estado['edit_liga_sel']
        equipos = db.get(liga_sel, [])
        
        # Asegurar límites correctos del equipo seleccionado
        if not equipos:
            estado['edit_equipo_idx'] = 0
            equipo_sel = None
        else:
            estado['edit_equipo_idx'] = max(0, min(estado['edit_equipo_idx'], len(equipos) - 1))
            equipo_sel = equipos[estado['edit_equipo_idx']]
            
        jugadores = equipo_sel.get('jugadores', []) if equipo_sel else []
        jugador_idx = estado['edit_jugador_idx']
        
        # Ajustar límites del jugador
        if jugador_idx >= len(jugadores):
            estado['edit_jugador_idx'] = -1
            jugador_idx = -1
            
        jugador_sel = jugadores[jugador_idx] if (jugador_idx >= 0 and jugador_idx < len(jugadores)) else None

        # Capturar clics y entrada de teclado
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        campo_inicial = estado.get('edit_input_activo')   # v4.2.0: Enter que cierra un campo no navega
        eventos = list(pygame.event.get())

        for event in eventos:
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos
            elif event.type == pygame.KEYDOWN:
                # Procesar entrada de teclado si hay un campo activo
                campo_activo = estado.get('edit_input_activo')
                if campo_activo:
                    # Si el campo es numérico o de texto
                    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        estado['edit_input_activo'] = None
                    elif event.key == pygame.K_BACKSPACE:
                        if campo_activo == 'league_name':   # v3.7.0
                            set_nombre_liga_editor(estado, nombre_liga_editor(estado)[:-1])
                        elif campo_activo == 'file_path':
                            estado['edit_filepath'] = estado['edit_filepath'][:-1]
                        elif campo_activo == 'team_name':
                            equipo_sel['nombre'] = equipo_sel['nombre'][:-1]
                        elif equipo_sel and campo_activo == 'team_budget':
                            val_str = str(equipo_sel.get('balance', 0))[:-1]
                            equipo_sel['balance'] = int(val_str) if val_str else 0
                        elif equipo_sel and campo_activo == 'team_dt':   # v3.4.0
                            equipo_sel['dt_nombre'] = str(equipo_sel.get('dt_nombre', '') or '')[:-1]
                        elif jugador_sel and campo_activo == 'player_name':
                            jugador_sel['nombre'] = jugador_sel['nombre'][:-1]
                        elif jugador_sel and campo_activo == 'player_apellido':
                            jugador_sel['apellido'] = jugador_sel['apellido'][:-1]
                        elif jugador_sel and campo_activo == 'player_ovr':
                            val_str = str(jugador_sel.get('overall', 70))[:-1]
                            ovr_val = int(val_str) if val_str else 0
                            jugador_sel['overall'] = ovr_val
                            # Sincronizar atributos base
                            jugador_sel['ataque'] = jugador_sel['defensa'] = jugador_sel['fisico'] = jugador_sel['tecnica'] = jugador_sel['mental'] = ovr_val
                        elif jugador_sel and campo_activo == 'player_age':
                            val_str = str(jugador_sel.get('edad', 25))[:-1]
                            jugador_sel['edad'] = int(val_str) if val_str else 0
                        elif jugador_sel and campo_activo == 'player_potencial':
                            # v0.8.x: techo de OVR editable. Al borrar dígitos vamos
                            # dejando el valor sin el último carácter; el clamp de coherencia
                            # (>= OVR) se aplica al TECLEAR (rama de dígitos) y al guardar.
                            val_str = str(jugador_sel.get('potencial', 0) or 0)[:-1]
                            jugador_sel['potencial'] = int(val_str) if val_str else 0
                    else:
                        char = event.unicode
                        # Filtros de caracteres
                        if campo_activo == 'league_name':   # v3.7.0: nombre de la liga (máx. 40)
                            actual = nombre_liga_editor(estado)
                            if char and char.isprintable() and len(actual) < MAX_NOMBRE_LIGA:
                                set_nombre_liga_editor(estado, actual + char)
                        elif campo_activo == 'file_path':
                            if char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/:\\':
                                estado['edit_filepath'] += char
                        elif campo_activo == 'team_name':
                            if len(equipo_sel['nombre']) < 30:
                                equipo_sel['nombre'] += char
                        elif campo_activo == 'team_budget':
                            if char.isdigit() and len(str(equipo_sel['balance'])) < 12:
                                equipo_sel['balance'] = int(str(equipo_sel['balance']) + char)
                        elif equipo_sel and campo_activo == 'team_dt':   # v3.4.0: DT puesto a mano
                            actual = str(equipo_sel.get('dt_nombre', '') or '')
                            if char and char.isprintable() and len(actual) < 26:
                                equipo_sel['dt_nombre'] = actual + char
                        elif jugador_sel and campo_activo == 'player_name':
                            if len(jugador_sel['nombre']) < 25:
                                jugador_sel['nombre'] += char
                        elif jugador_sel and campo_activo == 'player_apellido':
                            if len(jugador_sel['apellido']) < 25:
                                jugador_sel['apellido'] += char
                        elif jugador_sel and campo_activo == 'player_ovr':
                            if char.isdigit():
                                val_str = str(jugador_sel.get('overall', 70))
                                if len(val_str) < 3:
                                    ovr_val = min(99, int(val_str + char))
                                    jugador_sel['overall'] = ovr_val
                                    jugador_sel['ataque'] = jugador_sel['defensa'] = jugador_sel['fisico'] = jugador_sel['tecnica'] = jugador_sel['mental'] = ovr_val
                        elif jugador_sel and campo_activo == 'player_age':
                            if char.isdigit():
                                val_str = str(jugador_sel.get('edad', 25))
                                if len(val_str) < 2:
                                    jugador_sel['edad'] = int(val_str + char)
                        elif jugador_sel and campo_activo == 'player_potencial':
                            # v0.8.x: techo de OVR (1-3 dígitos, clamp [0, 99], nunca por
                            # debajo del OVR actual — un techo menor al OVR no tiene sentido).
                            if char.isdigit():
                                val_str = str(jugador_sel.get('potencial', 0) or 0)
                                if len(val_str) < 3:
                                    raw = int(val_str + char) if val_str != '0' else int(char)
                                    ovr_actual = int(jugador_sel.get('overall', 70) or 70)
                                    # Clamp: [ovr_actual, 99] para que el techo SIEMPRE sea > OVR
                                    jugador_sel['potencial'] = max(ovr_actual, min(99, raw))

        # v3.6.0: con un dropdown abierto el clic es SOLO del dropdown: elige una opción o, si cae
        # fuera, lo cierra. Nunca llega a los campos/botones de abajo (p. ej. RESTAURAR BASE).
        drop = estado.get('edit_dropdown_activo')
        # v4.2.0: teclado en el dropdown: ↑ ↓ opción, Enter la elige, Esc lo cierra
        if drop and campo_inicial is None:
            opciones = _opciones_dropdown(drop)
            foco_d = int(estado.get('edit_drop_foco', 0) or 0)
            for ev in eventos:
                if ev.type != pygame.KEYDOWN or not opciones:
                    continue
                if ev.key == pygame.K_DOWN:
                    foco_d = (foco_d + 1) % len(opciones)
                elif ev.key == pygame.K_UP:
                    foco_d = (foco_d - 1) % len(opciones)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    click_pos = opciones[foco_d % len(opciones)][2].center
                elif ev.key == pygame.K_ESCAPE:
                    estado['edit_dropdown_activo'] = drop = None
                    campo_inicial = 'dropdown'   # este Esc no sale del editor
                    break
            estado['edit_drop_foco'] = foco_d
        if drop and click_pos:
            try:
                for valor, _txt, r in _opciones_dropdown(drop):
                    if r.collidepoint(click_pos):
                        if drop == 'estilo_dt' and equipo_sel is not None and jugador_sel is None:
                            equipo_sel['estilo_dt'] = valor
                        elif drop == 'posicion' and jugador_sel is not None:
                            jugador_sel['posicion'] = valor
                        elif drop == 'rasgo' and jugador_sel is not None:
                            jugador_sel['rasgo'] = None if valor == "ninguno" else valor
                        break
            except Exception as e_drop:
                logger.error(f"Error en el dropdown {drop} del editor: {e_drop}")
            estado['edit_dropdown_activo'] = None
            click_pos = None

        # Dibujar fondo base
        draw_gradient_bg(screen)

        # Título
        draw_text(screen, "MODO EDICIÓN DE BASE DE DATOS", (40, 20), size='xl', color='dorado')
        draw_text(screen, "Modifica atributos de equipos y jugadores. Guarda los cambios para que apliquen a nuevas partidas.", (40, 65), size='sm', color='azul')
        
        # --- COLUMNA 1: LIGA Y SELECCION DE EQUIPOS/JUGADORES (Ancho: 450) ---
        col1_rect = R_COL_LISTAS
        draw_panel(screen, col1_rect)
        
        # Selectores de Liga (v0.8.8: +LIB y UCL; v3.7.0: 8 países + selector 1ª/2ª)
        tipo_sel, div_sel = _tipo_div(liga_sel)
        tab_x = 50
        tab_w = 41
        for l_id, tab_txt in pestanas_editor():
            tab_rect = pygame.Rect(tab_x, 110, tab_w, 30)
            is_active = (l_id == tipo_sel)
            is_hover = tab_rect.collidepoint(mouse_pos)

            c_bg = (0, 191, 255) if is_active else ((20, 26, 46) if is_hover else (10, 14, 26))
            c_border = (255, 215, 0) if is_active else (0, 191, 255)

            pygame.draw.rect(screen, c_bg, tab_rect, border_radius=4)
            pygame.draw.rect(screen, c_border, tab_rect, width=1, border_radius=4)
            draw_text(screen, tab_txt, (tab_rect.x + 5, tab_rect.y + 6), size='sm', color='bg' if is_active else 'blanco')

            if click_pos and tab_rect.collidepoint(click_pos):
                # v3.7.0: al cambiar de país se conserva la división elegida
                estado['edit_liga_sel'] = (_paises.clave_db(l_id, div_sel) if div_sel and l_id in _paises.TIPOS_LIGA
                                           else l_id)
                estado['edit_equipo_idx'] = 0
                estado['edit_jugador_idx'] = -1
                estado['edit_squad_offset'] = 0
                estado['edit_teams_offset'] = 0
                estado['edit_input_activo'] = None

            tab_x += tab_w + 3

        # v3.7.0: 1ª / 2ª del país + "Nombre de la liga" (tecleable, se guarda en "_ligas")
        if div_sel is not None:
            for k in (1, 2):
                r_div = rect_division(k)
                activo_div = (k == div_sel)
                fondo_div = (0, 191, 255) if activo_div else ((20, 26, 46) if r_div.collidepoint(mouse_pos) else (10, 14, 26))
                pygame.draw.rect(screen, fondo_div, r_div, border_radius=4)
                pygame.draw.rect(screen, (255, 215, 0) if activo_div else (0, 191, 255), r_div, width=1, border_radius=4)
                draw_text(screen, f"{k}ª", (r_div.x + 10, r_div.y + 5), size='sm', color='bg' if activo_div else 'blanco')
                if click_pos and r_div.collidepoint(click_pos) and not activo_div:
                    cambiar_division_editor(estado)
            inp_liga = R_NOMBRE_LIGA
            activo_nl = estado.get('edit_input_activo') == 'league_name'
            pygame.draw.rect(screen, (20, 26, 46), inp_liga, border_radius=4)
            pygame.draw.rect(screen, (255, 215, 0) if activo_nl else (0, 191, 255), inp_liga, width=1, border_radius=4)
            txt_nl = nombre_liga_editor(estado)
            txt_nl = txt_nl[-30:] if activo_nl else (txt_nl if len(txt_nl) <= 30 else txt_nl[:29] + "…")
            draw_text(screen, txt_nl + ("|" if activo_nl else ""), (inp_liga.x + 8, inp_liga.y + 5), size='sm',
                      color='dorado' if activo_nl else 'blanco')
            if click_pos and inp_liga.collidepoint(click_pos):
                estado['edit_input_activo'] = 'league_name'
        else:
            draw_text(screen, "Copa internacional (sin divisiones)", (55, 150), size='sm', color='azul')

        # v4.2.0: teclado sin campo activo: ↑ ↓ equipo (o jugador), → entra a la plantilla,
        # ← vuelve al equipo, Ctrl+S guarda, Esc vuelve al menú
        if campo_inicial is None and not estado.get('edit_input_activo') and not estado.get('edit_dropdown_activo'):
            for ev in eventos:
                if ev.type != pygame.KEYDOWN:
                    continue
                if ev.key == pygame.K_ESCAPE:
                    estado.pop('edit_mensaje', None)
                    estado['menu_step'] = 'main'
                    return 'menu'
                if ev.key in (pygame.K_UP, pygame.K_DOWN):
                    d = -1 if ev.key == pygame.K_UP else 1
                    if estado['edit_jugador_idx'] >= 0 and jugadores:
                        estado['edit_jugador_idx'] = max(0, min(len(jugadores) - 1, estado['edit_jugador_idx'] + d))
                    elif equipos:
                        estado['edit_equipo_idx'] = max(0, min(len(equipos) - 1, estado['edit_equipo_idx'] + d))
                        estado['edit_squad_offset'] = 0
                elif ev.key == pygame.K_RIGHT and jugadores and estado['edit_jugador_idx'] < 0:
                    estado['edit_jugador_idx'] = 0
                elif ev.key == pygame.K_LEFT:
                    estado['edit_jugador_idx'] = -1
                elif ev.key == pygame.K_s and (ev.mod & pygame.KMOD_CTRL):
                    ok = guardar_base_datos(estado)
                    estado['edit_mensaje'] = "¡Base de datos guardada con éxito!" if ok else "Error al escribir en disco."
                    estado['edit_mensaje_ticks'] = pygame.time.get_ticks()
            if equipos:   # la selección queda a la vista
                equipo_sel = equipos[estado['edit_equipo_idx']]
                jugadores = equipo_sel.get('jugadores', [])
                off = estado.get('edit_teams_offset', 0)
                if not off <= estado['edit_equipo_idx'] < off + 5:
                    estado['edit_teams_offset'] = max(0, min(estado['edit_equipo_idx'], len(equipos) - 5))
                off = estado.get('edit_squad_offset', 0)
                if estado['edit_jugador_idx'] >= 0 and not off <= estado['edit_jugador_idx'] < off + 5:
                    estado['edit_squad_offset'] = max(0, min(estado['edit_jugador_idx'], len(jugadores) - 5))
                jugador_sel = jugadores[estado['edit_jugador_idx']] if 0 <= estado['edit_jugador_idx'] < len(jugadores) else None

        # Lista de Equipos (Scrollable, 5 visibles)
        teams_offset = estado.get('edit_teams_offset', 0)
        teams_visible = 5
        
        teams_y = 180
        for idx in range(teams_offset, min(len(equipos), teams_offset + teams_visible)):
            eq = equipos[idx]
            eq_rect = pygame.Rect(55, teams_y, 380, 32)
            is_sel = (idx == estado['edit_equipo_idx'] and estado['edit_jugador_idx'] == -1)
            hov = eq_rect.collidepoint(mouse_pos)
            
            c_bg = (20, 50, 80) if is_sel else ((20, 26, 46) if hov else (10, 14, 26))
            pygame.draw.rect(screen, c_bg, eq_rect, border_radius=4)
            pygame.draw.rect(screen, (0, 191, 255), eq_rect, width=1, border_radius=4)
            
            draw_text(screen, eq.get('nombre', 'Equipo')[:26], (65, teams_y + 6), size='sm', color='verde' if is_sel else 'blanco')
            
            if click_pos and eq_rect.collidepoint(click_pos):
                estado['edit_equipo_idx'] = idx
                estado['edit_jugador_idx'] = -1
                estado['edit_squad_offset'] = 0
                estado['edit_input_activo'] = None
                
            teams_y += 36
            
        # Botones de scroll de equipos
        btn_te_up, btn_te_down = R_EQ_UP, R_EQ_DOWN
        pygame.draw.rect(screen, (20, 26, 46) if btn_te_up.collidepoint(mouse_pos) else (10, 14, 26), btn_te_up, border_radius=4)
        pygame.draw.rect(screen, (20, 26, 46) if btn_te_down.collidepoint(mouse_pos) else (10, 14, 26), btn_te_down, border_radius=4)
        draw_text(screen, "▲", (448, 185), size='sm', color='blanco')
        draw_text(screen, "▼", (448, 320), size='sm', color='blanco')
        
        if click_pos:
            if btn_te_up.collidepoint(click_pos):
                estado['edit_teams_offset'] = max(0, teams_offset - 1)
            elif btn_te_down.collidepoint(click_pos):
                estado['edit_teams_offset'] = min(max(0, len(equipos) - teams_visible), teams_offset + 1)
                
        pygame.draw.line(screen, (0, 191, 255), (55, 365), (435, 365), 1)
        
        # Lista de Jugadores (Scrollable, 5 visibles)
        draw_text(screen, f"JUGADORES — {equipo_sel.get('nombre', 'Equipo')[:18] if equipo_sel else 'Ninguno'}", (55, 375), size='sm', color='dorado')
        squad_offset = estado.get('edit_squad_offset', 0)
        squad_visible = 5
        
        squad_y = 405
        for idx in range(squad_offset, min(len(jugadores), squad_offset + squad_visible)):
            j = jugadores[idx]
            j_rect = pygame.Rect(55, squad_y, 380, 32)
            is_sel = (idx == estado['edit_jugador_idx'])
            hov = j_rect.collidepoint(mouse_pos)
            
            c_bg = (20, 50, 80) if is_sel else ((20, 26, 46) if hov else (10, 14, 26))
            pygame.draw.rect(screen, c_bg, j_rect, border_radius=4)
            pygame.draw.rect(screen, (0, 191, 255), j_rect, width=1, border_radius=4)
            
            nombre_comp = f"{j.get('nombre', 'Jugador')} {j.get('apellido', '')}".strip()
            pos_label = f"[{j.get('posicion', 'DEF')}] "
            draw_text(screen, f"{pos_label}{nombre_comp[:24]}", (65, squad_y + 6), size='sm', color='verde' if is_sel else 'blanco')
            # v0.8.1: mostrar OVR real. Si el dict viene sin 'overall' (edited_db viejo),
            # calcularlo desde los 5 atributos. Si tampoco están, caer al default 70.
            ovr_val = j.get('overall')
            if ovr_val is None:
                try:
                    ovr_val = (
                        int(j.get('ataque', 0))
                        + int(j.get('defensa', 0))
                        + int(j.get('fisico', 0))
                        + int(j.get('tecnica', 0))
                        + int(j.get('mental', 0))
                    ) // 5
                except Exception:
                    ovr_val = 70
            draw_text(screen, f"OVR: {ovr_val}", (360, squad_y + 6), size='sm', color='dorado')
            
            if click_pos and j_rect.collidepoint(click_pos):
                estado['edit_jugador_idx'] = idx
                estado['edit_input_activo'] = None
                
            squad_y += 36
            
        # Botones de scroll de plantilla
        btn_sq_up, btn_sq_down = R_JUG_UP, R_JUG_DOWN
        pygame.draw.rect(screen, (20, 26, 46) if btn_sq_up.collidepoint(mouse_pos) else (10, 14, 26), btn_sq_up, border_radius=4)
        pygame.draw.rect(screen, (20, 26, 46) if btn_sq_down.collidepoint(mouse_pos) else (10, 14, 26), btn_sq_down, border_radius=4)
        draw_text(screen, "▲", (448, 410), size='sm', color='blanco')
        draw_text(screen, "▼", (448, 545), size='sm', color='blanco')
        
        if click_pos:
            if btn_sq_up.collidepoint(click_pos):
                estado['edit_squad_offset'] = max(0, squad_offset - 1)
            elif btn_sq_down.collidepoint(click_pos):
                estado['edit_squad_offset'] = min(max(0, len(jugadores) - squad_visible), squad_offset + 1)
                
        # --- COLUMNA 2: FORMULARIO DE EDICION (Ancho: 730) ---
        col2_rect = R_FORMULARIO
        draw_panel(screen, col2_rect)
        
        if not equipo_sel:
            draw_text(screen, "Selecciona un equipo o jugador en la izquierda para editar.", (530, 130), size='md', color='blanco')
        elif jugador_sel is None:
            # --- EDITAR EQUIPO ---
            draw_text(screen, f"EDITAR EQUIPO: {equipo_sel.get('nombre', 'Equipo').upper()}", (530, 120), size='md', color='dorado')
            
            # Nombre del equipo
            draw_text(screen, "Nombre del Equipo:", (530, 180), size='sm', color='blanco')
            inp_team_name = R_EQ_NOMBRE
            is_team_name_active = (estado.get('edit_input_activo') == 'team_name')
            pygame.draw.rect(screen, (10, 14, 26) if is_team_name_active else (20, 26, 46), inp_team_name, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_team_name_active else (0, 191, 255), inp_team_name, width=1, border_radius=6)
            draw_text(screen, equipo_sel.get('nombre', ''), (542, 213), size='md', color='blanco')
            
            if click_pos and inp_team_name.collidepoint(click_pos):
                estado['edit_input_activo'] = 'team_name'
                estado['edit_dropdown_activo'] = None
                
            # Presupuesto (en millones)
            draw_text(screen, "Presupuesto (en enteros $, ej. 15000000 para $15M):", (530, 265), size='sm', color='blanco')
            inp_team_budget = R_EQ_PRESUPUESTO
            is_team_budget_active = (estado.get('edit_input_activo') == 'team_budget')
            pygame.draw.rect(screen, (10, 14, 26) if is_team_budget_active else (20, 26, 46), inp_team_budget, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_team_budget_active else (0, 191, 255), inp_team_budget, width=1, border_radius=6)
            draw_text(screen, f"{equipo_sel.get('balance', 0):,}", (542, 298), size='md', color='blanco')
            
            if click_pos and inp_team_budget.collidepoint(click_pos):
                estado['edit_input_activo'] = 'team_budget'
                estado['edit_dropdown_activo'] = None
                
            # Estilo Táctico (Dropdown)
            draw_text(screen, "Estilo Táctico (DT):", (530, 350), size='sm', color='blanco')
            btn_estilo = R_EQ_ESTILO
            is_drop_estilo = (estado.get('edit_dropdown_activo') == 'estilo_dt')
            pygame.draw.rect(screen, (20, 26, 46), btn_estilo, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_drop_estilo else (0, 191, 255), btn_estilo, width=1, border_radius=6)
            draw_text(screen, NOMBRE_ESTILO.get(normalizar_estilo(equipo_sel.get('estilo_dt')), 'Ancelotismo').upper(),
                      (542, 383), size='sm', color='dorado')   # v3.3.0
            draw_text(screen, "▼", (850, 385), size='sm', color='blanco')
            
            if click_pos and btn_estilo.collidepoint(click_pos):
                estado['edit_dropdown_activo'] = 'estilo_dt' if not is_drop_estilo else None
                estado['edit_input_activo'] = None
                
            # v3.4.0: DT (nombre) a la derecha del estilo (fuera de la lista del dropdown y
            # lejos de RESTAURAR BASE / VOLVER). Vacío = DT real parodia de la tabla.
            draw_text(screen, "DT (nombre, vacío = el real):", (900, 350), size='sm', color='blanco')
            inp_team_dt = R_EQ_DT
            is_team_dt_active = (estado.get('edit_input_activo') == 'team_dt')
            pygame.draw.rect(screen, (10, 14, 26) if is_team_dt_active else (20, 26, 46), inp_team_dt, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_team_dt_active else (0, 191, 255), inp_team_dt, width=1, border_radius=6)
            draw_text(screen, str(equipo_sel.get('dt_nombre', '') or ''), (912, 383), size='sm', color='blanco')
            if click_pos and inp_team_dt.collidepoint(click_pos):
                estado['edit_input_activo'] = 'team_dt'
                estado['edit_dropdown_activo'] = None

            # v3.6.0: la lista del dropdown de estilos se dibuja al final (_dibujar_dropdown)

        else:
            # --- EDITAR JUGADOR ---
            draw_text(screen, f"EDITAR JUGADOR: {jugador_sel.get('nombre', '').upper()} {jugador_sel.get('apellido', '').upper()}", (530, 120), size='md', color='dorado')
            
            # Nombre
            draw_text(screen, "Nombre:", (530, 170), size='sm', color='blanco')
            inp_play_name = R_J_NOMBRE
            is_play_name_act = (estado.get('edit_input_activo') == 'player_name')
            pygame.draw.rect(screen, (10, 14, 26) if is_play_name_act else (20, 26, 46), inp_play_name, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_play_name_act else (0, 191, 255), inp_play_name, width=1, border_radius=6)
            draw_text(screen, jugador_sel.get('nombre', ''), (542, 203), size='md', color='blanco')
            
            if click_pos and inp_play_name.collidepoint(click_pos):
                estado['edit_input_activo'] = 'player_name'
                estado['edit_dropdown_activo'] = None
                
            # Apellido
            draw_text(screen, "Apellido:", (860, 170), size='sm', color='blanco')
            inp_play_ape = R_J_APELLIDO
            is_play_ape_act = (estado.get('edit_input_activo') == 'player_apellido')
            pygame.draw.rect(screen, (10, 14, 26) if is_play_ape_act else (20, 26, 46), inp_play_ape, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_play_ape_act else (0, 191, 255), inp_play_ape, width=1, border_radius=6)
            draw_text(screen, jugador_sel.get('apellido', ''), (872, 203), size='md', color='blanco')
            
            if click_pos and inp_play_ape.collidepoint(click_pos):
                estado['edit_input_activo'] = 'player_apellido'
                estado['edit_dropdown_activo'] = None
                
            # Valoración (Overall)
            draw_text(screen, "OVR (máx. 99):", (530, 250), size='sm', color='blanco')   # v3.9.0: el texto largo pisaba "Edad:"
            inp_play_ovr = R_J_OVR
            is_play_ovr_act = (estado.get('edit_input_activo') == 'player_ovr')
            pygame.draw.rect(screen, (10, 14, 26) if is_play_ovr_act else (20, 26, 46), inp_play_ovr, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_play_ovr_act else (0, 191, 255), inp_play_ovr, width=1, border_radius=6)
            draw_text(screen, str(jugador_sel.get('overall', 70)), (542, 283), size='md', color='blanco')
            
            if click_pos and inp_play_ovr.collidepoint(click_pos):
                estado['edit_input_activo'] = 'player_ovr'
                estado['edit_dropdown_activo'] = None
                
            # Edad
            draw_text(screen, "Edad:", (700, 250), size='sm', color='blanco')
            inp_play_age = R_J_EDAD
            is_play_age_act = (estado.get('edit_input_activo') == 'player_age')
            pygame.draw.rect(screen, (10, 14, 26) if is_play_age_act else (20, 26, 46), inp_play_age, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_play_age_act else (0, 191, 255), inp_play_age, width=1, border_radius=6)
            draw_text(screen, str(jugador_sel.get('edad', 25)), (712, 283), size='md', color='blanco')
            
            if click_pos and inp_play_age.collidepoint(click_pos):
                estado['edit_input_activo'] = 'player_age'
                estado['edit_dropdown_activo'] = None
                
            # Posición (Dropdown)
            draw_text(screen, "Posición:", (860, 250), size='sm', color='blanco')
            btn_pos = R_J_POSICION
            is_drop_pos = (estado.get('edit_dropdown_activo') == 'posicion')
            pygame.draw.rect(screen, (20, 26, 46), btn_pos, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_drop_pos else (0, 191, 255), btn_pos, width=1, border_radius=6)
            draw_text(screen, jugador_sel.get('posicion', 'DEF').upper(), (872, 283), size='sm', color='dorado')
            draw_text(screen, "▼", (1130, 285), size='sm', color='blanco')
            
            if click_pos and btn_pos.collidepoint(click_pos):
                estado['edit_dropdown_activo'] = 'posicion' if not is_drop_pos else None
                estado['edit_input_activo'] = None
                
            # v3.6.0: la lista del dropdown de posición se dibuja al final (_dibujar_dropdown)

            # Rasgo / Característica (Dropdown)
            draw_text(screen, "Rasgo Especial:", (530, 335), size='sm', color='blanco')
            btn_rasgo = R_J_RASGO
            is_drop_rasgo = (estado.get('edit_dropdown_activo') == 'rasgo')
            pygame.draw.rect(screen, (20, 26, 46), btn_rasgo, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_drop_rasgo else (0, 191, 255), btn_rasgo, width=1, border_radius=6)
            
            rg = jugador_sel.get('rasgo')
            rg_label = "NINGUNO" if (not rg or rg == "ninguno") else str(rg).upper()
            draw_text(screen, rg_label, (542, 368), size='sm', color='dorado')
            draw_text(screen, "▼", (800, 368), size='sm', color='blanco')
            
            if click_pos and btn_rasgo.collidepoint(click_pos):
                estado['edit_dropdown_activo'] = 'rasgo' if not is_drop_rasgo else None
                estado['edit_input_activo'] = None
                
            # v3.6.0: la lista del dropdown de rasgo se dibuja al final (_dibujar_dropdown)

            # v0.8.x: Potencial (techo de OVR). Input numérico editable a mano, junto al Rasgo.
            # Si el dict viene sin la clave (0) mostramos el OVR como base sensata en vez de "0".
            draw_text(screen, "Potencial (máx. 99):", (860, 335), size='sm', color='blanco')
            _pot_display = jugador_sel.get('potencial') or jugador_sel.get('overall', 70) or 70
            inp_play_pot = R_J_POTENCIAL
            is_play_pot_act = (estado.get('edit_input_activo') == 'player_potencial')
            pygame.draw.rect(screen, (10, 14, 26) if is_play_pot_act else (20, 26, 46), inp_play_pot, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_play_pot_act else (0, 191, 255), inp_play_pot, width=1, border_radius=6)
            draw_text(screen, str(_pot_display), (872, 368), size='md', color='blanco')

            if click_pos and inp_play_pot.collidepoint(click_pos):
                estado['edit_input_activo'] = 'player_potencial'
                estado['edit_dropdown_activo'] = None

        # --- PANEL DE ACCIONES INFERIORES: EXPORTAR, IMPORTAR, GUARDAR (X=510, Y=430) ---
        actions_y = 430
        draw_text(screen, "IMPORTAR / EXPORTAR BASE DE DATOS", (530, actions_y), size='sm', color='dorado')
        
        # Input ruta de archivo
        inp_file_rect = R_ARCHIVO
        is_file_act = (estado.get('edit_input_activo') == 'file_path')
        pygame.draw.rect(screen, (10, 14, 26) if is_file_act else (20, 26, 46), inp_file_rect, border_radius=6)
        pygame.draw.rect(screen, (0, 255, 136) if is_file_act else (0, 191, 255), inp_file_rect, width=1, border_radius=6)
        draw_text(screen, estado['edit_filepath'], (542, actions_y + 33), size='sm', color='blanco')
        
        if click_pos and inp_file_rect.collidepoint(click_pos):
            estado['edit_input_activo'] = 'file_path'
            estado['edit_dropdown_activo'] = None
            
        # Botones de Importación / Exportación
        btn_export, btn_import = R_EXPORTAR, R_IMPORTAR
        # v3.9.0: un solo texto por botón (antes draw_button + draw_text lo escribían dos veces)
        _boton(screen, btn_export, "EXPORTAR", btn_export.collidepoint(mouse_pos))
        _boton(screen, btn_import, "IMPORTAR", btn_import.collidepoint(mouse_pos))

        # Botón RESTAURAR BASE
        btn_reset = R_RESTAURAR                                   # v3.6.0
        _boton(screen, btn_reset, "RESTAURAR BASE", btn_reset.collidepoint(mouse_pos), color='rojo')

        # Mensajes de éxito / error temporales
        msg = estado.get('edit_mensaje', '')
        if msg:
            if pygame.time.get_ticks() - estado.get('edit_mensaje_ticks', 0) > 4000:
                estado['edit_mensaje'] = ''
            else:
                draw_text(screen, msg, (750, actions_y + 83), size='sm', color='verde' if "éxito" in msg or "cargado" in msg else 'rojo')
                
        # Clics de importación / exportación
        if click_pos:
            if btn_export.collidepoint(click_pos):
                try:
                    fpath = estado['edit_filepath']
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(db, f, ensure_ascii=False, indent=2)
                    estado['edit_mensaje'] = f"Datos exportados con éxito a {fpath}"
                    estado['edit_mensaje_ticks'] = pygame.time.get_ticks()
                except Exception as e_exp:
                    estado['edit_mensaje'] = f"Error al exportar: {str(e_exp)[:25]}"
                    estado['edit_mensaje_ticks'] = pygame.time.get_ticks()
                    
            elif btn_import.collidepoint(click_pos):
                try:
                    fpath = estado['edit_filepath']
                    if os.path.exists(fpath):
                        with open(fpath, "r", encoding="utf-8") as f:
                            imported_db = json.load(f)
                            # Validar que tenga las ligas clave
                            if any(lid in imported_db for lid in _paises.TIPOS_LIGA):   # v3.7.0
                                estado['edited_db'] = imported_db
                                db = imported_db
                                # Forzar recargar standings y vistas
                                estado['edit_equipo_idx'] = 0
                                estado['edit_jugador_idx'] = -1
                                estado['edit_mensaje'] = "¡JSON cargado con éxito en memoria!"
                            else:
                                estado['edit_mensaje'] = "Archivo JSON inválido."
                        estado['edit_mensaje_ticks'] = pygame.time.get_ticks()
                    else:
                        estado['edit_mensaje'] = "El archivo no existe."
                        estado['edit_mensaje_ticks'] = pygame.time.get_ticks()
                except Exception as e_imp:
                    estado['edit_mensaje'] = f"Error de importación: {str(e_imp)[:25]}"
                    estado['edit_mensaje_ticks'] = pygame.time.get_ticks()
                    
            elif btn_reset.collidepoint(click_pos):
                db = restaurar_base(estado)                       # v3.6.0

        # --- BOTONES PRINCIPALES INFERIORES: APLICAR Y VOLVER (X=40, Y=610) ---
        btn_aplicar, btn_volver = R_APLICAR, R_VOLVER
        _boton(screen, btn_aplicar, "APLICAR Y GUARDAR", btn_aplicar.collidepoint(mouse_pos), 'md', 'verde')
        _boton(screen, btn_volver, "VOLVER AL MENÚ", btn_volver.collidepoint(mouse_pos), 'md')

        # v3.6.0: lista del dropdown abierto, encima de todo lo demás
        _dibujar_dropdown(screen, estado, mouse_pos, jugador_sel is not None)

        if click_pos:
            if btn_aplicar.collidepoint(click_pos):
                if guardar_base_datos(estado):
                    estado['edit_mensaje'] = "¡Base de datos guardada con éxito!"
                    estado['edit_mensaje_ticks'] = pygame.time.get_ticks()
                else:
                    estado['edit_mensaje'] = "Error al escribir en disco."
                    estado['edit_mensaje_ticks'] = pygame.time.get_ticks()
                    
            elif btn_volver.collidepoint(click_pos):
                # Limpiar referencias temporales del editor
                estado.pop('edit_mensaje', None)
                estado.pop('edit_input_activo', None)
                estado.pop('edit_dropdown_activo', None)
                estado['menu_step'] = 'main'
                return 'menu'

    except Exception as e_err:
        logger.error(f"Error crítico en pantalla del editor: {e_err}", exc_info=True)
        return 'menu'
        
    return None
