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

# v4.6.0: el editor se ordena en 4 secciones (pestañas de arriba): ENTRENADORES, CLUBES, LIGAS y
# JUGADORES. En ENTRENADORES y JUGADORES, LIBRES muestra los DTs / jugadores sin club de la base.
SECCIONES = [('entrenadores', 'ENTRENADORES'), ('clubes', 'CLUBES'), ('ligas', 'LIGAS'), ('jugadores', 'JUGADORES')]
LIBRES = '_libres'            # valor de edit_liga_sel en modo "sin club"
ID_BASE_LIBRES = 90000        # ids de los jugadores libres creados en el editor
COPAS = ('libertadores', 'champions')

# v3.6.0: RESTAURAR BASE y las listas de los dropdowns con rects fijos, para despachar el clic
# ANTES que cualquier otro control (con un dropdown abierto el clic es solo suyo).
R_RESTAURAR = pygame.Rect(530, 505, 200, 36)

# v3.9.0: resto de rects del editor expuestos (los usa la ayuda H); render los usa tal cual.
R_COL_LISTAS = pygame.Rect(40, 100, 450, 500)
R_EQ_UP, R_EQ_DOWN = pygame.Rect(440, 180, 30, 30), pygame.Rect(440, 315, 30, 30)
R_JUG_UP, R_JUG_DOWN = pygame.Rect(440, 405, 30, 30), pygame.Rect(440, 540, 30, 30)
R_LISTA_UP, R_LISTA_DOWN = pygame.Rect(440, 180, 30, 30), pygame.Rect(440, 540, 30, 30)   # listas de 10
R_LIBRES = pygame.Rect(155, 146, 100, 28)
R_NUEVO = pygame.Rect(265, 146, 205, 28)
R_FORMULARIO = pygame.Rect(510, 100, 730, 500)
R_BORRAR = pygame.Rect(1090, 112, 130, 32)
R_DT_NOMBRE = pygame.Rect(530, 205, 350, 38)
R_DT_ESTILO = pygame.Rect(530, 290, 350, 38)
R_DT_CALIF = pygame.Rect(900, 290, 140, 38)
R_EQ_NOMBRE = pygame.Rect(530, 205, 350, 38)
R_EQ_PRESUPUESTO = pygame.Rect(530, 290, 350, 38)
R_NOMBRE_LIGA = pygame.Rect(530, 205, 500, 38)
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


def rect_seccion(i: int) -> pygame.Rect:
    """v4.6.0: pestaña i de las secciones (ENTRENADORES, CLUBES, LIGAS, JUGADORES)."""
    return pygame.Rect(40 + i * 200, 62, 190, 32)


def rect_tab_liga(i: int) -> pygame.Rect:
    """v3.9.0: pestaña i de ligas/copas (ING, ESP, ... LIB, UCL)."""
    return pygame.Rect(50 + i * 44, 110, 41, 30)


def rect_division(k: int) -> pygame.Rect:
    """v3.9.0: selector de 1ª (k=1) / 2ª (k=2) división."""
    return pygame.Rect(55 + (k - 1) * 46, 146, 42, 28)


def rect_fila(lista: str, i: int) -> pygame.Rect:
    """v3.9.0: fila visible i (0-4) de la lista 'equipos' (y=180) o 'jugadores' (y=405)."""
    return pygame.Rect(55, (180 if lista == 'equipos' else 405) + i * 36, 380, 32)


def rect_fila_lista(i: int) -> pygame.Rect:
    """v4.6.0: fila visible i (0-9) de las listas de una sola columna (DTs, clubes, ligas, libres)."""
    return pygame.Rect(55, 180 + i * 36, 380, 32)


def _boton(screen, rect, texto: str, hover: bool, size: str = 'sm', color: str = 'blanco') -> None:
    """v3.9.0: botón con el texto UNA sola vez y en un tamaño que cabe (antes se escribía dos veces)."""
    draw_button(screen, rect, "", hover)
    col = COLORS['verde'] if hover else COLORS.get(color, COLORS['blanco'])
    txt = get_font(size).render(texto, True, col)
    screen.blit(txt, txt.get_rect(center=rect.center))


def _opciones_dropdown(tipo: str) -> list:
    """v3.6.0: [(valor, texto, rect)] de la lista desplegada del dropdown `tipo`."""
    if tipo == 'estilo_dt':
        r = R_DT_ESTILO
        return [(est, NOMBRE_ESTILO.get(est, est).upper(), pygame.Rect(r.x, r.bottom + i * 30, r.width, 30))
                for i, est in enumerate(ESTILOS_TACTICOS)]
    if tipo == 'posicion':
        return [(pos, pos.upper(), pygame.Rect(860, 311 + i * 30, 300, 30)) for i, pos in enumerate(POSICIONES)]
    if tipo == 'rasgo':
        return [(rsg, rsg.upper(), pygame.Rect(530, 396 + i * 30, 300, 30)) for i, rsg in enumerate(RASGOS_JUGADOR)]
    return []


def _dibujar_dropdown(screen, estado: dict, mouse_pos, aplica: dict) -> None:
    """v3.6.0: dibuja la lista del dropdown abierto AL FINAL (encima de IMPORTAR/RESTAURAR BASE)."""
    try:
        drop = estado.get('edit_dropdown_activo')
        if not drop or not aplica.get(drop):
            return
        foco_d = int(estado.get('edit_drop_foco', 0) or 0)   # v4.2.0: opción con foco de teclado
        for i, (_valor, texto, r) in enumerate(_opciones_dropdown(drop)):
            pygame.draw.rect(screen, (30, 40, 70) if r.collidepoint(mouse_pos) or i == foco_d else (10, 14, 26), r)
            pygame.draw.rect(screen, (0, 191, 255), r, width=1)
            draw_text(screen, texto, (r.x + 12, r.y + 5), size='sm', color='blanco')
    except Exception as e:
        logger.error(f"No se pudo dibujar el dropdown del editor: {e}")


def _campo(screen, rect, texto: str, activo: bool, size: str = 'md', color: str = 'blanco') -> None:
    """v4.6.0: caja de texto / valor de un formulario."""
    pygame.draw.rect(screen, (10, 14, 26) if activo else (20, 26, 46), rect, border_radius=6)
    pygame.draw.rect(screen, (0, 255, 136) if activo else (0, 191, 255), rect, width=1, border_radius=6)
    draw_text(screen, texto, (rect.x + 12, rect.y + 8), size=size, color=color)


def _lista(screen, estado: dict, filas_txt: list, sel: int, clave_off: str, click_pos, mouse_pos,
           visibles: int = 10, fila=rect_fila_lista, up=R_LISTA_UP, down=R_LISTA_DOWN):
    """v4.6.0: lista con scroll; `filas_txt` = [(izquierda, derecha)]. Devuelve el índice clicado."""
    off = max(0, min(int(estado.get(clave_off, 0) or 0), max(0, len(filas_txt) - visibles)))
    estado[clave_off] = off
    elegido = None
    for k, idx in enumerate(range(off, min(len(filas_txt), off + visibles))):
        r = fila(k)
        es = idx == sel
        pygame.draw.rect(screen, (20, 50, 80) if es else ((20, 26, 46) if r.collidepoint(mouse_pos) else (10, 14, 26)),
                         r, border_radius=4)
        pygame.draw.rect(screen, (0, 191, 255), r, width=1, border_radius=4)
        izq, der = filas_txt[idx]
        draw_text(screen, izq, (r.x + 10, r.y + 6), size='sm', color='verde' if es else 'blanco')
        if der:
            draw_text(screen, der, (r.right - 10 - get_font('sm').size(der)[0], r.y + 6), size='sm', color='dorado')
        if click_pos and r.collidepoint(click_pos):
            elegido = idx
    for r, txt in ((up, "▲"), (down, "▼")):
        pygame.draw.rect(screen, (20, 26, 46) if r.collidepoint(mouse_pos) else (10, 14, 26), r, border_radius=4)
        draw_text(screen, txt, (r.x + 8, r.y + 5), size='sm', color='blanco')
    if click_pos:
        if up.collidepoint(click_pos):
            estado[clave_off] = max(0, off - 1)
        elif down.collidepoint(click_pos):
            estado[clave_off] = min(max(0, len(filas_txt) - visibles), off + 1)
    return elegido


def _a_la_vista(estado: dict, clave_off: str, idx: int, visibles: int, total: int) -> None:
    """Corre el scroll para que la fila `idx` quede visible (navegación con teclado)."""
    off = int(estado.get(clave_off, 0) or 0)
    if idx >= 0 and not off <= idx < off + visibles:
        estado[clave_off] = max(0, min(idx, total - visibles))


def _truncar(txt: str, n: int) -> str:
    txt = str(txt or '')
    return txt if len(txt) <= n else txt[:n - 1] + "…"


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


def dt_efectivo(club: dict) -> tuple:
    """v4.6.0: (nombre, estilo, calif) que tendrá el DT del club en la carrera: lo editado o, si
    no, el real de la tabla (nombre '' = uno al azar) y la calificación según las estrellas."""
    from types import SimpleNamespace
    from alpha_football.data.entrenadores import DT_REALES
    from alpha_football.entrenadores import calif_inicial
    real = DT_REALES.get(club.get('nombre', ''))
    nombre = str(club.get('dt_nombre') or '').strip() or (real[0] if real else '')
    estilo = club.get('dt_estilo') or (real[1] if real else normalizar_estilo(club.get('estilo_dt')))
    calif = int(club.get('dt_calif') or 0) or calif_inicial(SimpleNamespace(estrellas=club.get('estrellas', 3.0)))
    return nombre, estilo, calif


def campos_dt(libre: bool) -> tuple:
    """Claves (nombre, estilo, calif) del DT: las del DT libre o las del DT de un club."""
    return ('nombre', 'estilo', 'calif') if libre else ('dt_nombre', 'dt_estilo', 'dt_calif')


def ligas_editor() -> list:
    """v4.6.0: [(clave, texto)] de las 16 ligas (8 países × 1ª/2ª) de la sección LIGAS."""
    return [(_paises.clave_db(p['liga_id'], d), f"{p['corto']} {d}ª") for p in _paises.PAISES for d in (1, 2)]


def nuevo_dt_libre(db: dict) -> int:
    """Agrega un DT sin club a la base y devuelve su índice."""
    lista = db.setdefault('_dts_libres', [])
    lista.append({'nombre': 'Nuevo DT', 'estilo': 'anchelottismo', 'calif': 50})
    return len(lista) - 1


def nuevo_jugador_libre(db: dict) -> int:
    """Agrega un jugador libre (MED, 70, 27 años) a la base y devuelve su índice."""
    from alpha_football.models import Jugador
    lista = db.setdefault('_libres', [])
    jid = max([ID_BASE_LIBRES - 1] + [int(j.get('id', 0) or 0) for j in lista]) + 1
    j = Jugador(nombre='Nuevo', apellido=f'Libre {jid - ID_BASE_LIBRES + 1}', posicion='MED', ataque=70,
                defensa=70, fisico=70, tecnica=70, mental=70, moral=70, id=jid, edad=27).to_dict()
    j['potencial'] = 70
    lista.append(j)
    return len(lista) - 1


def borrar_libre(db: dict, clave: str, idx: int) -> None:
    lista = db.get(clave) or []
    if 0 <= idx < len(lista):
        del lista[idx]


def cambiar_seccion(estado: dict, seccion: str) -> None:
    """v4.6.0: cambia de pestaña; CLUBES y LIGAS no tienen LIBRES y ENTRENADORES no tiene copas."""
    if seccion == estado.get('edit_seccion') or seccion not in dict(SECCIONES):
        return
    estado['edit_seccion'] = seccion
    liga = estado.get('edit_liga_sel', 'premier')
    if (liga == LIBRES and seccion in ('clubes', 'ligas')) or (liga in COPAS and seccion in ('entrenadores', 'ligas')):
        estado['edit_liga_sel'] = 'premier'
    for k, v in (('edit_equipo_idx', 0), ('edit_jugador_idx', -1), ('edit_squad_offset', 0),
                 ('edit_teams_offset', 0), ('edit_input_activo', None), ('edit_dropdown_activo', None)):
        estado[k] = v


def _mensaje(estado: dict, texto: str) -> None:
    estado['edit_mensaje'] = texto
    estado['edit_mensaje_ticks'] = pygame.time.get_ticks()


def render(screen: pygame.Surface, estado: dict) -> str | None:
    """Renderiza el editor: pestañas de sección, lista a la izquierda y formulario a la derecha."""
    try:
        db = cargar_base_datos_inicial(estado)

        estado.setdefault('edit_seccion', 'entrenadores')   # v4.6.0
        estado.setdefault('edit_liga_sel', 'premier')
        estado.setdefault('edit_equipo_idx', 0)
        estado.setdefault('edit_jugador_idx', -1)  # -1 = ningún jugador elegido
        estado.setdefault('edit_input_activo', None)  # Campo activo de texto
        estado.setdefault('edit_dropdown_activo', None)  # 'estilo_dt' / 'rasgo' / 'posicion'
        estado.setdefault('edit_squad_offset', 0)
        estado.setdefault('edit_teams_offset', 0)
        estado.setdefault('edit_filepath', 'alpha_football_db_custom.json')
        estado.setdefault('edit_mensaje', '')
        estado.setdefault('edit_mensaje_ticks', 0)
        # v3.9.0: con un campo de texto activo, H se escribe (no abre la ayuda)
        estado['texto_activo'] = bool(estado.get('edit_input_activo'))

        seccion = estado['edit_seccion'] if estado['edit_seccion'] in dict(SECCIONES) else 'entrenadores'
        if seccion == 'ligas' and estado['edit_liga_sel'] not in dict(ligas_editor()):
            estado['edit_liga_sel'] = 'premier'
        libres = estado['edit_liga_sel'] == LIBRES and seccion in ('entrenadores', 'jugadores')
        if estado['edit_liga_sel'] == LIBRES and not libres:
            estado['edit_liga_sel'] = 'premier'
        k_nom, k_est, k_cal = campos_dt(libres)

        def resolver() -> dict:
            """Lo elegido ahora: lista de clubes, club, jugadores, jugador y DT según la sección."""
            s = {'equipos': [], 'equipo': None, 'jugadores': [], 'jugador': None, 'dt': None}
            if libres and seccion == 'entrenadores':
                lst = db.setdefault('_dts_libres', [])
                estado['edit_equipo_idx'] = max(0, min(estado['edit_equipo_idx'], len(lst) - 1))
                s['dt'] = lst[estado['edit_equipo_idx']] if lst else None
                return s
            if libres:
                s['jugadores'] = db.setdefault('_libres', [])
            else:
                s['equipos'] = db.get(estado['edit_liga_sel'], []) or []
                if s['equipos']:
                    estado['edit_equipo_idx'] = max(0, min(estado['edit_equipo_idx'], len(s['equipos']) - 1))
                    s['equipo'] = s['equipos'][estado['edit_equipo_idx']]
                    s['jugadores'] = s['equipo'].get('jugadores', [])
                if seccion == 'entrenadores':
                    s['dt'] = s['equipo']
            if estado['edit_jugador_idx'] >= len(s['jugadores']):
                estado['edit_jugador_idx'] = len(s['jugadores']) - 1 if libres else -1
            ji = estado['edit_jugador_idx']
            if seccion == 'jugadores' and 0 <= ji < len(s['jugadores']):
                s['jugador'] = s['jugadores'][ji]
            return s

        sel = resolver()
        equipos, equipo_sel, jugadores, jugador_sel, dt_sel = (sel['equipos'], sel['equipo'], sel['jugadores'],
                                                               sel['jugador'], sel['dt'])

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
                campo_activo = estado.get('edit_input_activo')
                if not campo_activo:
                    continue
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    estado['edit_input_activo'] = None
                elif event.key == pygame.K_BACKSPACE:
                    if campo_activo == 'league_name':   # v3.7.0
                        set_nombre_liga_editor(estado, nombre_liga_editor(estado)[:-1])
                    elif campo_activo == 'file_path':
                        estado['edit_filepath'] = estado['edit_filepath'][:-1]
                    elif equipo_sel and campo_activo == 'team_name':
                        equipo_sel['nombre'] = equipo_sel['nombre'][:-1]
                    elif equipo_sel and campo_activo == 'team_budget':
                        val_str = str(equipo_sel.get('balance', 0))[:-1]
                        equipo_sel['balance'] = int(val_str) if val_str else 0
                    elif dt_sel is not None and campo_activo == 'dt_nombre':   # v4.6.0
                        dt_sel[k_nom] = str(dt_sel.get(k_nom, '') or '')[:-1]
                    elif dt_sel is not None and campo_activo == 'dt_calif':
                        val_str = str(dt_sel.get(k_cal, 0) or 0)[:-1]
                        dt_sel[k_cal] = int(val_str) if val_str else 0
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
                        # v0.8.x: techo de OVR editable; el clamp (>= OVR) se aplica al teclear.
                        val_str = str(jugador_sel.get('potencial', 0) or 0)[:-1]
                        jugador_sel['potencial'] = int(val_str) if val_str else 0
                else:
                    char = event.unicode
                    if campo_activo == 'league_name':   # v3.7.0: nombre de la liga (máx. 40)
                        actual = nombre_liga_editor(estado)
                        if char and char.isprintable() and len(actual) < MAX_NOMBRE_LIGA:
                            set_nombre_liga_editor(estado, actual + char)
                    elif campo_activo == 'file_path':
                        if char and char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/:\\':
                            estado['edit_filepath'] += char
                    elif equipo_sel and campo_activo == 'team_name':
                        if char and char.isprintable() and len(equipo_sel['nombre']) < 30:
                            equipo_sel['nombre'] += char
                    elif equipo_sel and campo_activo == 'team_budget':
                        if char.isdigit() and len(str(equipo_sel['balance'])) < 12:
                            equipo_sel['balance'] = int(str(equipo_sel['balance']) + char)
                    elif dt_sel is not None and campo_activo == 'dt_nombre':   # v4.6.0
                        actual = str(dt_sel.get(k_nom, '') or '')
                        if char and char.isprintable() and len(actual) < 26:
                            dt_sel[k_nom] = actual + char
                    elif dt_sel is not None and campo_activo == 'dt_calif':
                        if char.isdigit():
                            val_str = str(dt_sel.get(k_cal, 0) or 0)
                            raw = int(char) if val_str == '0' else int(val_str + char)
                            if len(str(raw)) <= 2:
                                dt_sel[k_cal] = max(0, min(99, raw))
                    elif jugador_sel and campo_activo == 'player_name':
                        if char and char.isprintable() and len(jugador_sel['nombre']) < 25:
                            jugador_sel['nombre'] += char
                    elif jugador_sel and campo_activo == 'player_apellido':
                        if char and char.isprintable() and len(jugador_sel['apellido']) < 25:
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
                        # v0.8.x: techo de OVR (clamp [OVR, 99]: un techo menor al OVR no tiene sentido).
                        if char.isdigit():
                            val_str = str(jugador_sel.get('potencial', 0) or 0)
                            if len(val_str) < 3:
                                raw = int(val_str + char) if val_str != '0' else int(char)
                                ovr_actual = int(jugador_sel.get('overall', 70) or 70)
                                jugador_sel['potencial'] = max(ovr_actual, min(99, raw))

        # v3.6.0: con un dropdown abierto el clic es SOLO del dropdown: elige una opción o, si cae
        # fuera, lo cierra. Nunca llega a los campos/botones de abajo (p. ej. RESTAURAR BASE).
        aplica_drop = {'estilo_dt': seccion == 'entrenadores' and dt_sel is not None,
                       'posicion': jugador_sel is not None, 'rasgo': jugador_sel is not None}
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
                    if r.collidepoint(click_pos) and aplica_drop.get(drop):
                        if drop == 'estilo_dt':
                            dt_sel[k_est] = valor
                            if not libres:
                                dt_sel['estilo_dt'] = valor   # el estilo del club es el de su DT
                        elif drop == 'posicion':
                            jugador_sel['posicion'] = valor
                        elif drop == 'rasgo':
                            jugador_sel['rasgo'] = None if valor == "ninguno" else valor
                        break
            except Exception as e_drop:
                logger.error(f"Error en el dropdown {drop} del editor: {e_drop}")
            estado['edit_dropdown_activo'] = None
            click_pos = None

        # v4.2.0: teclado sin campo activo: Tab sección, ↑ ↓ lista, → entra a la plantilla,
        # ← vuelve al club, Ctrl+S guarda, Esc vuelve al menú
        ligas = ligas_editor()
        if campo_inicial is None and not estado.get('edit_input_activo') and not estado.get('edit_dropdown_activo'):
            for ev in eventos:
                if ev.type != pygame.KEYDOWN:
                    continue
                if ev.key == pygame.K_ESCAPE:
                    estado.pop('edit_mensaje', None)
                    estado['menu_step'] = 'main'
                    return 'menu'
                if ev.key == pygame.K_TAB:
                    i = [c for c, _t in SECCIONES].index(seccion)
                    cambiar_seccion(estado, SECCIONES[(i + (-1 if ev.mod & pygame.KMOD_SHIFT else 1)) % 4][0])
                    return None
                if ev.key in (pygame.K_UP, pygame.K_DOWN):
                    d = -1 if ev.key == pygame.K_UP else 1
                    if seccion == 'jugadores' and (libres or estado['edit_jugador_idx'] >= 0):
                        if jugadores:
                            estado['edit_jugador_idx'] = max(0, min(len(jugadores) - 1, estado['edit_jugador_idx'] + d))
                    elif seccion == 'ligas':
                        claves = [c for c, _t in ligas]
                        i = claves.index(estado['edit_liga_sel']) if estado['edit_liga_sel'] in claves else 0
                        estado['edit_liga_sel'] = claves[max(0, min(len(claves) - 1, i + d))]
                    else:
                        n = len(db.get('_dts_libres') or []) if (libres and seccion == 'entrenadores') else len(equipos)
                        if n:
                            estado['edit_equipo_idx'] = max(0, min(n - 1, estado['edit_equipo_idx'] + d))
                            estado['edit_squad_offset'] = 0 if seccion == 'jugadores' else estado['edit_squad_offset']
                elif ev.key == pygame.K_RIGHT and seccion == 'jugadores' and not libres and jugadores \
                        and estado['edit_jugador_idx'] < 0:
                    estado['edit_jugador_idx'] = 0
                elif ev.key == pygame.K_LEFT and seccion == 'jugadores' and not libres:
                    estado['edit_jugador_idx'] = -1
                elif ev.key == pygame.K_s and (ev.mod & pygame.KMOD_CTRL):
                    ok = guardar_base_datos(estado)
                    _mensaje(estado, "¡Base de datos guardada con éxito!" if ok else "Error al escribir en disco.")
            sel = resolver()   # la selección queda a la vista
            equipos, equipo_sel, jugadores, jugador_sel, dt_sel = (sel['equipos'], sel['equipo'], sel['jugadores'],
                                                                   sel['jugador'], sel['dt'])
            if seccion == 'ligas':
                claves = [c for c, _t in ligas]
                if estado['edit_liga_sel'] in claves:
                    _a_la_vista(estado, 'edit_teams_offset', claves.index(estado['edit_liga_sel']), 10, len(claves))
            elif seccion == 'jugadores' and not libres:
                _a_la_vista(estado, 'edit_teams_offset', estado['edit_equipo_idx'], 5, len(equipos))
                _a_la_vista(estado, 'edit_squad_offset', estado['edit_jugador_idx'], 5, len(jugadores))
            elif seccion == 'jugadores':
                _a_la_vista(estado, 'edit_squad_offset', estado['edit_jugador_idx'], 10, len(jugadores))
            else:
                n = len(db.get('_dts_libres') or []) if libres else len(equipos)
                _a_la_vista(estado, 'edit_teams_offset', estado['edit_equipo_idx'], 10, n)

        # Dibujar fondo base y título
        draw_gradient_bg(screen)
        draw_text(screen, "MODO EDICIÓN DE BASE DE DATOS", (40, 16), size='lg', color='dorado')

        # v4.6.0: pestañas de sección
        for i, (clave, texto) in enumerate(SECCIONES):
            r = rect_seccion(i)
            activa = clave == seccion
            pygame.draw.rect(screen, (0, 191, 255) if activa else ((20, 26, 46) if r.collidepoint(mouse_pos) else (10, 14, 26)),
                             r, border_radius=6)
            pygame.draw.rect(screen, (255, 215, 0) if activa else (0, 191, 255), r, width=1, border_radius=6)
            t = get_font('sm').render(texto, True, COLORS['bg'] if activa else COLORS['blanco'])
            screen.blit(t, t.get_rect(center=r.center))
            if click_pos and r.collidepoint(click_pos):
                cambiar_seccion(estado, clave)
                return None

        # --- COLUMNA 1: LISTA ---
        draw_panel(screen, R_COL_LISTAS)
        tipo_sel, div_sel = _tipo_div(estado['edit_liga_sel'])
        if seccion != 'ligas':
            # Selectores de liga (v0.8.8: +LIB y UCL; v3.7.0: 8 países + selector 1ª/2ª)
            pestanas = [p for p in pestanas_editor() if not (seccion == 'entrenadores' and p[0] in COPAS)]
            for i, (l_id, tab_txt) in enumerate(pestanas):
                tab_rect = rect_tab_liga(i)
                is_active = (l_id == tipo_sel) and not libres
                c_bg = (0, 191, 255) if is_active else ((20, 26, 46) if tab_rect.collidepoint(mouse_pos) else (10, 14, 26))
                pygame.draw.rect(screen, c_bg, tab_rect, border_radius=4)
                pygame.draw.rect(screen, (255, 215, 0) if is_active else (0, 191, 255), tab_rect, width=1, border_radius=4)
                draw_text(screen, tab_txt, (tab_rect.x + 5, tab_rect.y + 6), size='sm', color='bg' if is_active else 'blanco')
                if click_pos and tab_rect.collidepoint(click_pos):
                    # v3.7.0: al cambiar de país se conserva la división elegida
                    estado['edit_liga_sel'] = (_paises.clave_db(l_id, div_sel) if div_sel and l_id in _paises.TIPOS_LIGA
                                               else l_id)
                    for k, v in (('edit_equipo_idx', 0), ('edit_jugador_idx', -1), ('edit_squad_offset', 0),
                                 ('edit_teams_offset', 0), ('edit_input_activo', None)):
                        estado[k] = v
            if libres:
                pass
            elif div_sel is not None:
                for k in (1, 2):
                    r_div = rect_division(k)
                    activo_div = (k == div_sel)
                    fondo_div = (0, 191, 255) if activo_div else ((20, 26, 46) if r_div.collidepoint(mouse_pos) else (10, 14, 26))
                    pygame.draw.rect(screen, fondo_div, r_div, border_radius=4)
                    pygame.draw.rect(screen, (255, 215, 0) if activo_div else (0, 191, 255), r_div, width=1, border_radius=4)
                    draw_text(screen, f"{k}ª", (r_div.x + 10, r_div.y + 5), size='sm', color='bg' if activo_div else 'blanco')
                    if click_pos and r_div.collidepoint(click_pos) and not activo_div:
                        cambiar_division_editor(estado)
            else:
                draw_text(screen, "Copa int.", (55, 150), size='sm', color='azul')
            if seccion in ('entrenadores', 'jugadores'):
                pygame.draw.rect(screen, (0, 191, 255) if libres else ((20, 26, 46) if R_LIBRES.collidepoint(mouse_pos) else (10, 14, 26)),
                                 R_LIBRES, border_radius=4)
                pygame.draw.rect(screen, (255, 215, 0) if libres else (0, 191, 255), R_LIBRES, width=1, border_radius=4)
                t = get_font('sm').render("LIBRES", True, COLORS['bg'] if libres else COLORS['blanco'])
                screen.blit(t, t.get_rect(center=R_LIBRES.center))
                if click_pos and R_LIBRES.collidepoint(click_pos) and not libres:
                    estado['edit_liga_sel'] = LIBRES
                    for k, v in (('edit_equipo_idx', 0), ('edit_jugador_idx', 0 if seccion == 'jugadores' else -1),
                                 ('edit_squad_offset', 0), ('edit_teams_offset', 0), ('edit_input_activo', None)):
                        estado[k] = v
                if libres:
                    _boton(screen, R_NUEVO, "+ NUEVO DT" if seccion == 'entrenadores' else "+ NUEVO JUGADOR",
                           R_NUEVO.collidepoint(mouse_pos), color='verde')
                    if click_pos and R_NUEVO.collidepoint(click_pos):
                        if seccion == 'entrenadores':
                            estado['edit_equipo_idx'] = nuevo_dt_libre(db)
                            _a_la_vista(estado, 'edit_teams_offset', estado['edit_equipo_idx'], 10, len(db['_dts_libres']))
                        else:
                            estado['edit_jugador_idx'] = nuevo_jugador_libre(db)
                            _a_la_vista(estado, 'edit_squad_offset', estado['edit_jugador_idx'], 10, len(db['_libres']))
                        estado['edit_input_activo'] = None
        else:
            draw_text(screen, "Elige la liga que quieres renombrar", (55, 130), size='sm', color='azul')

        if seccion == 'entrenadores':
            if libres:
                lst = db.get('_dts_libres') or []
                filas = [(_truncar(x.get('nombre', ''), 24), f"{NOMBRE_ESTILO.get(normalizar_estilo(x.get('estilo')), '')} · {x.get('calif', 0)}")
                         for x in lst]
                if not lst:
                    draw_text(screen, "Sin DTs libres: crea uno con + NUEVO DT", (55, 190), size='sm', color='azul')
            else:
                filas = []
                for eq in equipos:
                    nom = dt_efectivo(eq)[0] or "(al azar)"
                    filas.append((_truncar(nom, 20), _truncar(eq.get('nombre', ''), 16)))
            elegido = _lista(screen, estado, filas, estado['edit_equipo_idx'], 'edit_teams_offset', click_pos, mouse_pos)
            if elegido is not None:
                estado['edit_equipo_idx'] = elegido
                estado['edit_input_activo'] = None
        elif seccion == 'clubes':
            filas = [(_truncar(eq.get('nombre', 'Equipo'), 26), f"${int(eq.get('balance', 0) or 0) / 1_000_000:.1f}M")
                     for eq in equipos]
            elegido = _lista(screen, estado, filas, estado['edit_equipo_idx'], 'edit_teams_offset', click_pos, mouse_pos)
            if elegido is not None:
                estado['edit_equipo_idx'] = elegido
                estado['edit_input_activo'] = None
        elif seccion == 'ligas':
            claves = [c for c, _t in ligas]
            filas = []
            for clave, texto in ligas:
                t, d = _tipo_div(clave)
                propio = ((db.get('_ligas') or {}).get(t) or {}).get('nombre_2a' if d == 2 else 'nombre')
                filas.append((texto, _truncar(propio if propio is not None else _paises.nombre_liga_defecto(t, d), 30)))
            actual = claves.index(estado['edit_liga_sel']) if estado['edit_liga_sel'] in claves else -1
            elegido = _lista(screen, estado, filas, actual, 'edit_teams_offset', click_pos, mouse_pos)
            if elegido is not None:
                estado['edit_liga_sel'] = claves[elegido]
                estado['edit_input_activo'] = None
        elif libres:   # jugadores libres
            filas = [(f"[{j.get('posicion', 'MED')}] {_truncar((j.get('nombre', '') + ' ' + j.get('apellido', '')).strip(), 22)}",
                      f"OVR: {j.get('overall', 70)}") for j in jugadores]
            if not jugadores:
                draw_text(screen, "Sin jugadores libres: crea uno con + NUEVO JUGADOR", (55, 190), size='sm', color='azul')
            elegido = _lista(screen, estado, filas, estado['edit_jugador_idx'], 'edit_squad_offset', click_pos, mouse_pos)
            if elegido is not None:
                estado['edit_jugador_idx'] = elegido
                estado['edit_input_activo'] = None
        else:   # jugadores de un club: clubes arriba (5) y plantilla abajo (5)
            filas = [(_truncar(eq.get('nombre', 'Equipo'), 26), '') for eq in equipos]
            sel_eq = estado['edit_equipo_idx'] if estado['edit_jugador_idx'] == -1 else -1
            elegido = _lista(screen, estado, filas, sel_eq, 'edit_teams_offset', click_pos, mouse_pos, visibles=5,
                             fila=lambda k: rect_fila('equipos', k), up=R_EQ_UP, down=R_EQ_DOWN)
            if elegido is not None:
                estado['edit_equipo_idx'] = elegido
                estado['edit_jugador_idx'] = -1
                estado['edit_squad_offset'] = 0
                estado['edit_input_activo'] = None
            pygame.draw.line(screen, (0, 191, 255), (55, 365), (435, 365), 1)
            draw_text(screen, f"JUGADORES — {_truncar(equipo_sel.get('nombre', 'Equipo'), 18) if equipo_sel else 'Ninguno'}",
                      (55, 375), size='sm', color='dorado')
            # v0.8.1: OVR real (si el dict viene sin 'overall', el promedio de los 5 atributos)
            filas = []
            for j in jugadores:
                ovr_val = j.get('overall')
                if ovr_val is None:
                    try:
                        ovr_val = sum(int(j.get(a, 0)) for a in ('ataque', 'defensa', 'fisico', 'tecnica', 'mental')) // 5
                    except Exception:
                        ovr_val = 70
                nombre_comp = f"{j.get('nombre', 'Jugador')} {j.get('apellido', '')}".strip()
                filas.append((f"[{j.get('posicion', 'DEF')}] {nombre_comp[:24]}", f"OVR: {ovr_val}"))
            elegido = _lista(screen, estado, filas, estado['edit_jugador_idx'], 'edit_squad_offset', click_pos, mouse_pos,
                             visibles=5, fila=lambda k: rect_fila('jugadores', k), up=R_JUG_UP, down=R_JUG_DOWN)
            if elegido is not None:
                estado['edit_jugador_idx'] = elegido
                estado['edit_input_activo'] = None

        # --- COLUMNA 2: FORMULARIO ---
        draw_panel(screen, R_FORMULARIO)
        activo = estado.get('edit_input_activo')

        def activar(rect, campo) -> bool:
            if click_pos and rect.collidepoint(click_pos):
                estado['edit_input_activo'] = campo
                estado['edit_dropdown_activo'] = None
                return True
            return False

        def boton_borrar(clave: str, idx: int) -> None:
            _boton(screen, R_BORRAR, "BORRAR", R_BORRAR.collidepoint(mouse_pos), color='rojo')
            if click_pos and R_BORRAR.collidepoint(click_pos):
                borrar_libre(db, clave, idx)
                estado['edit_input_activo'] = None
                _mensaje(estado, "Borrado de los libres.")

        if seccion == 'entrenadores':
            if dt_sel is None:
                draw_text(screen, "Elige un DT de la lista de la izquierda." if not libres else
                          "Crea un DT sin club con + NUEVO DT.", (530, 130), size='md', color='blanco')
            else:
                if libres:
                    nombre, estilo, calif = (dt_sel.get('nombre', ''), normalizar_estilo(dt_sel.get('estilo')),
                                             int(dt_sel.get('calif', 0) or 0))
                    draw_text(screen, "DT LIBRE (sin club)", (530, 120), size='md', color='dorado')
                    boton_borrar('_dts_libres', estado['edit_equipo_idx'])
                else:
                    nombre, estilo, calif = dt_efectivo(dt_sel)
                    draw_text(screen, f"DT DE {_truncar(dt_sel.get('nombre', 'Equipo').upper(), 34)}", (530, 120),
                              size='md', color='dorado')
                draw_text(screen, "Nombre del DT:" if libres else "Nombre del DT (vacío = el real):", (530, 180),
                          size='sm', color='blanco')
                propio = str(dt_sel.get(k_nom, '') or '')
                if propio or activo == 'dt_nombre':
                    _campo(screen, R_DT_NOMBRE, propio + ("|" if activo == 'dt_nombre' else ''), activo == 'dt_nombre')
                else:
                    _campo(screen, R_DT_NOMBRE, f"({nombre or 'uno al azar'})", False, color='azul')
                activar(R_DT_NOMBRE, 'dt_nombre')
                draw_text(screen, "Estilo táctico:", (530, 265), size='sm', color='blanco')
                _campo(screen, R_DT_ESTILO, NOMBRE_ESTILO.get(estilo, 'Ancelotismo').upper(),
                       estado.get('edit_dropdown_activo') == 'estilo_dt', size='sm', color='dorado')
                draw_text(screen, "▼", (R_DT_ESTILO.right - 30, R_DT_ESTILO.y + 10), size='sm', color='blanco')
                if click_pos and R_DT_ESTILO.collidepoint(click_pos):
                    estado['edit_dropdown_activo'] = None if estado.get('edit_dropdown_activo') == 'estilo_dt' else 'estilo_dt'
                    estado['edit_input_activo'] = None
                draw_text(screen, "Calificación (1-99):", (900, 265), size='sm', color='blanco')
                _campo(screen, R_DT_CALIF, str(dt_sel.get(k_cal) or calif), activo == 'dt_calif')
                if activar(R_DT_CALIF, 'dt_calif') and not dt_sel.get(k_cal):
                    dt_sel[k_cal] = calif          # se edita a partir de la actual
                try:
                    from types import SimpleNamespace
                    from alpha_football import entrenadores as _EN
                    c = int(dt_sel.get(k_cal) or calif)
                    s = (_EN.sueldo_pedido(c) if libres else
                         _EN.sueldo_inicial(SimpleNamespace(balance=int(dt_sel.get('balance', 0) or 0)), c))
                    draw_text(screen, f"Sueldo anual: ${s / 1_000_000:.2f}M  ·  un club lo contrata si le cuesta "
                              f"≤ {int(_EN.FRAC_SUELDO_DT * 100)}% de su saldo", (530, 345), size='sm', color='azul')
                except Exception as e_s:
                    logger.debug(f"Sueldo del DT en el editor: {e_s}")
        elif seccion == 'clubes':
            if not equipo_sel:
                draw_text(screen, "Elige un club de la lista de la izquierda.", (530, 130), size='md', color='blanco')
            else:
                draw_text(screen, f"EDITAR CLUB: {_truncar(equipo_sel.get('nombre', 'Equipo').upper(), 34)}", (530, 120),
                          size='md', color='dorado')
                draw_text(screen, "Nombre del club:", (530, 180), size='sm', color='blanco')
                _campo(screen, R_EQ_NOMBRE, equipo_sel.get('nombre', ''), activo == 'team_name')
                activar(R_EQ_NOMBRE, 'team_name')
                draw_text(screen, "Presupuesto (en enteros $, ej. 15000000 para $15M):", (530, 265), size='sm', color='blanco')
                _campo(screen, R_EQ_PRESUPUESTO, f"{equipo_sel.get('balance', 0):,}", activo == 'team_budget')
                activar(R_EQ_PRESUPUESTO, 'team_budget')
        elif seccion == 'ligas':
            texto = dict(ligas).get(estado['edit_liga_sel'], '')
            draw_text(screen, f"LIGA {texto}", (530, 120), size='md', color='dorado')
            draw_text(screen, f"Nombre de la liga (máx. {MAX_NOMBRE_LIGA}):", (530, 180), size='sm', color='blanco')
            txt_nl = nombre_liga_editor(estado)
            _campo(screen, R_NOMBRE_LIGA, (txt_nl[-34:] + "|") if activo == 'league_name' else _truncar(txt_nl, 36),
                   activo == 'league_name', color='dorado' if activo == 'league_name' else 'blanco')
            activar(R_NOMBRE_LIGA, 'league_name')
        elif jugador_sel is None:
            draw_text(screen, "Elige un jugador de la lista." if not libres else "Crea un jugador libre con + NUEVO JUGADOR.",
                      (530, 130), size='md', color='blanco')
        else:
            titulo = "JUGADOR LIBRE" if libres else "EDITAR JUGADOR"
            draw_text(screen, _truncar(f"{titulo}: {jugador_sel.get('nombre', '').upper()} {jugador_sel.get('apellido', '').upper()}", 44),
                      (530, 120), size='md', color='dorado')
            if libres:
                boton_borrar('_libres', estado['edit_jugador_idx'])
            draw_text(screen, "Nombre:", (530, 170), size='sm', color='blanco')
            _campo(screen, R_J_NOMBRE, jugador_sel.get('nombre', ''), activo == 'player_name')
            activar(R_J_NOMBRE, 'player_name')
            draw_text(screen, "Apellido:", (860, 170), size='sm', color='blanco')
            _campo(screen, R_J_APELLIDO, jugador_sel.get('apellido', ''), activo == 'player_apellido')
            activar(R_J_APELLIDO, 'player_apellido')
            draw_text(screen, "OVR (máx. 99):", (530, 250), size='sm', color='blanco')   # v3.9.0
            _campo(screen, R_J_OVR, str(jugador_sel.get('overall', 70)), activo == 'player_ovr')
            activar(R_J_OVR, 'player_ovr')
            draw_text(screen, "Edad:", (700, 250), size='sm', color='blanco')
            _campo(screen, R_J_EDAD, str(jugador_sel.get('edad', 25)), activo == 'player_age')
            activar(R_J_EDAD, 'player_age')
            draw_text(screen, "Posición:", (860, 250), size='sm', color='blanco')
            _campo(screen, R_J_POSICION, jugador_sel.get('posicion', 'DEF').upper(),
                   estado.get('edit_dropdown_activo') == 'posicion', size='sm', color='dorado')
            draw_text(screen, "▼", (1130, 285), size='sm', color='blanco')
            if click_pos and R_J_POSICION.collidepoint(click_pos):
                estado['edit_dropdown_activo'] = None if estado.get('edit_dropdown_activo') == 'posicion' else 'posicion'
                estado['edit_input_activo'] = None
            draw_text(screen, "Rasgo Especial:", (530, 335), size='sm', color='blanco')
            rg = jugador_sel.get('rasgo')
            _campo(screen, R_J_RASGO, "NINGUNO" if (not rg or rg == "ninguno") else str(rg).upper(),
                   estado.get('edit_dropdown_activo') == 'rasgo', size='sm', color='dorado')
            draw_text(screen, "▼", (800, 368), size='sm', color='blanco')
            if click_pos and R_J_RASGO.collidepoint(click_pos):
                estado['edit_dropdown_activo'] = None if estado.get('edit_dropdown_activo') == 'rasgo' else 'rasgo'
                estado['edit_input_activo'] = None
            # v0.8.x: Potencial (techo de OVR); sin la clave (0) se muestra el OVR.
            draw_text(screen, "Potencial (máx. 99):", (860, 335), size='sm', color='blanco')
            _campo(screen, R_J_POTENCIAL, str(jugador_sel.get('potencial') or jugador_sel.get('overall', 70) or 70),
                   activo == 'player_potencial')
            activar(R_J_POTENCIAL, 'player_potencial')

        # --- ACCIONES: EXPORTAR, IMPORTAR, RESTAURAR ---
        actions_y = 430
        draw_text(screen, "IMPORTAR / EXPORTAR BASE DE DATOS", (530, actions_y), size='sm', color='dorado')
        _campo(screen, R_ARCHIVO, estado['edit_filepath'], activo == 'file_path', size='sm')
        activar(R_ARCHIVO, 'file_path')
        # v3.9.0: un solo texto por botón (antes draw_button + draw_text lo escribían dos veces)
        _boton(screen, R_EXPORTAR, "EXPORTAR", R_EXPORTAR.collidepoint(mouse_pos))
        _boton(screen, R_IMPORTAR, "IMPORTAR", R_IMPORTAR.collidepoint(mouse_pos))
        _boton(screen, R_RESTAURAR, "RESTAURAR BASE", R_RESTAURAR.collidepoint(mouse_pos), color='rojo')   # v3.6.0

        # Mensajes de éxito / error temporales
        msg = estado.get('edit_mensaje', '')
        if msg:
            if pygame.time.get_ticks() - estado.get('edit_mensaje_ticks', 0) > 4000:
                estado['edit_mensaje'] = ''
            else:
                draw_text(screen, msg, (750, actions_y + 83), size='sm',
                          color='verde' if "éxito" in msg or "cargado" in msg else 'rojo')

        if click_pos:
            if R_EXPORTAR.collidepoint(click_pos):
                try:
                    fpath = estado['edit_filepath']
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(db, f, ensure_ascii=False, indent=2)
                    _mensaje(estado, f"Datos exportados con éxito a {fpath}")
                except Exception as e_exp:
                    _mensaje(estado, f"Error al exportar: {str(e_exp)[:25]}")
            elif R_IMPORTAR.collidepoint(click_pos):
                try:
                    fpath = estado['edit_filepath']
                    if os.path.exists(fpath):
                        with open(fpath, "r", encoding="utf-8") as f:
                            imported_db = json.load(f)
                        if any(lid in imported_db for lid in _paises.TIPOS_LIGA):   # v3.7.0
                            estado['edited_db'] = db = imported_db
                            estado['edit_equipo_idx'] = 0
                            estado['edit_jugador_idx'] = -1
                            _mensaje(estado, "¡JSON cargado con éxito en memoria!")
                        else:
                            _mensaje(estado, "Archivo JSON inválido.")
                    else:
                        _mensaje(estado, "El archivo no existe.")
                except Exception as e_imp:
                    _mensaje(estado, f"Error de importación: {str(e_imp)[:25]}")
            elif R_RESTAURAR.collidepoint(click_pos):
                db = restaurar_base(estado)                       # v3.6.0

        # --- BOTONES PRINCIPALES: APLICAR Y VOLVER ---
        _boton(screen, R_APLICAR, "APLICAR Y GUARDAR", R_APLICAR.collidepoint(mouse_pos), 'md', 'verde')
        _boton(screen, R_VOLVER, "VOLVER AL MENÚ", R_VOLVER.collidepoint(mouse_pos), 'md')

        # v3.6.0: lista del dropdown abierto, encima de todo lo demás
        _dibujar_dropdown(screen, estado, mouse_pos, aplica_drop)

        if click_pos:
            if R_APLICAR.collidepoint(click_pos):
                ok = guardar_base_datos(estado)
                _mensaje(estado, "¡Base de datos guardada con éxito!" if ok else "Error al escribir en disco.")
            elif R_VOLVER.collidepoint(click_pos):
                estado.pop('edit_mensaje', None)
                estado.pop('edit_input_activo', None)
                estado.pop('edit_dropdown_activo', None)
                estado['menu_step'] = 'main'
                return 'menu'

    except Exception as e_err:
        logger.error(f"Error crítico en pantalla del editor: {e_err}", exc_info=True)
        return 'menu'

    return None
