# -*- coding: utf-8 -*-
"""
Módulo del Menú Principal Rediseñado para Alpha Football.
Permite iniciar una nueva partida, seleccionar liga y equipo, y cargar partidas guardadas.
Implementa una interfaz alineada a la izquierda, efectos de fútbol alegre en el fondo,
sistema de partículas animadas y soporte para el nuevo logotipo.
"""

import pygame
import sys
import logging
import math
import random
import os
from typing import Dict, List, Any

from alpha_football.ui.theme import (
    COLORS, SCREEN_W, SCREEN_H, get_font,
    draw_gradient_bg, draw_panel, draw_button, draw_text
)

# Configuración del logging para el seguimiento de la interfaz
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# v3.7.0: países y ligas salen del registro central (alpha_football/paises.py).
from alpha_football import paises as _paises

# Definición de las ligas oficiales del juego
LIGAS_DISPONIBLES = [{'id': p['liga_id'], 'name': f"{p['liga']} ({p['nombre']})"} for p in _paises.PAISES]

# v2.3 (Fase 9): selector por PAÍS (no por liga). Cada país tiene 2 divisiones.
# El flow es: País → División (1ª / 2ª) → Equipo.
# v3.7.0: alias construido desde paises.PAISES (8 países).
PAISES_DISPONIBLES = [{k: p[k] for k in ('codigo', 'nombre', 'liga_id', 'emoji')} for p in _paises.PAISES]

# Mapeo de países a nombres de liga (usado por las pantallas de selección de país
# y división para mostrar el subtítulo de cada país).
# v3.7.0: alias; 'num_jornadas' ya no se usa para cargar (se deriva del nº de equipos).
CONFIGURACION_LIGAS = {
    p['liga_id']: {'nombre': p['liga'], 'num_jornadas': _paises.num_jornadas(_paises.EQUIPOS_POR_LIGA)}
    for p in _paises.PAISES
}

# v0.7: nacionalidades sugeridas para el alta del DT (además del campo de texto libre).
NACIONALIDADES = [
    "Colombia", "Argentina", "España", "Brasil", "Inglaterra",
    "Italia", "Francia", "Alemania", "Uruguay", "México",
]

def _leer_db_editada() -> dict:
    """v3.7.0: base editada (alpha_football_edited_db.json) o {} si no hay / no se puede leer."""
    import json
    ruta = "alpha_football_edited_db.json"
    if not os.path.exists(ruta):
        return {}
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            db = json.load(f)
        return db if isinstance(db, dict) else {}
    except Exception as e_db:
        logger.error(f"Error al leer la base editada '{ruta}': {e_db}")
        return {}


def _completar_con_datos(equipos: list, tipo: str, division: int, excluir=()) -> list:
    """
    v3.7.0: clubes de data/<tipo>.py (o segunda_<tipo>.py) cuyo nombre no esté en `equipos`
    ni en `excluir`, los necesarios para llegar a 12. Devuelve solo los agregados (crudos).
    Posicional: el editor guarda la liga en el orden de los datos y no agrega ni quita clubes,
    así que los n editados son los n primeros de los datos (aunque se hayan renombrado:
    'Real Vadrid' editado = 'Real Madriz' de los datos). Se agregan desde el índice n.
    """
    faltan = _paises.EQUIPOS_POR_LIGA - len(equipos)
    if faltan <= 0:
        return []
    try:
        datos = _paises.cargar_datos_liga(tipo, division)
        if datos is None:
            return []
        usados = {getattr(eq, 'nombre', '') for eq in equipos} | set(excluir)
        n = len(equipos)
        orden = list(datos.equipos[n:]) + list(datos.equipos[:n])   # los primeros n, solo de respaldo
        agregados = [eq for eq in orden if eq.nombre not in usados][:faltan]
        return agregados
    except Exception as e_merge:
        logger.error(f"No se pudo completar '{tipo}' ({division}ª) con los datos: {e_merge}")
        return []


def load_league_teams(league_id: str):
    """
    Importa dinámicamente el módulo correspondiente a la liga y obtiene el objeto Liga.
    Intenta primero cargar desde la base de datos editada por el usuario en formato JSON.
    Implementa un mecanismo de resiliencia con fallback a datos por defecto si falla.
    """
    # Intentamos primero cargar los datos editados por el usuario si existen localmente
    import os
    import json
    ruta_db_editada = "alpha_football_edited_db.json"
    if os.path.exists(ruta_db_editada):
        try:
            with open(ruta_db_editada, "r", encoding="utf-8") as archivo_json:
                db_datos = json.load(archivo_json)
            if league_id in db_datos:
                from alpha_football.models import Liga, Equipo
                lista_equipos_datos = db_datos[league_id]
                lista_equipos_construidos = []
                for datos_equipo in lista_equipos_datos:
                    try:
                        equipo_instancia = Equipo.from_dict(datos_equipo)
                        lista_equipos_construidos.append(equipo_instancia)
                    except Exception as error_equipo:
                        logger.warning(f"No se pudo reconstruir un equipo individual desde JSON: {error_equipo}. Omitiendo equipo.")
                
                # v3.7.0: la base editada es la principal, pero se completa hasta 12 con los
                # clubes de los datos cuyo nombre no esté (bases editadas con ligas de 6/8).
                equipos_agregados = _completar_con_datos(lista_equipos_construidos, league_id, 1)

                liga_cargada = Liga(
                    nombre=_paises.nombre_liga(league_id, 1),   # v3.7.0: registro (con override)
                    tipo=league_id,
                    equipos=lista_equipos_construidos + equipos_agregados,
                    num_jornadas=_paises.num_jornadas(len(lista_equipos_construidos) + len(equipos_agregados))
                )
                if equipos_agregados:   # v3.7.0: solo los de los datos se escalan (la editada ya viene escalada)
                    try:
                        from alpha_football.market import escalar_presupuestos
                        escalar_presupuestos(Liga(nombre='', tipo=league_id, equipos=equipos_agregados, num_jornadas=2))
                    except Exception as e_bud_m:
                        logger.error(f"No se pudieron escalar los clubes agregados a '{league_id}': {e_bud_m}")
                # v0.8.9: la base editada es la PRINCIPAL del juego, así que la rama editada
                # debe quedar igual de completa que la fresca: plantillas mínimas y, sobre todo,
                # valor + potencial poblados (la editada se guarda con valor/potencial en 0 →
                # sin esto reaparecía el bug "Valor $0" y el potencial salía igual al OVR).
                # NO se re-escalan presupuestos: la editada ya los trae escalados.
                try:
                    from alpha_football.plantilla import expandir_liga, aplicar_techo_region
                    aplicar_techo_region(league_id, liga_cargada.equipos)  # v2.3.6: Sudamérica máx. 81
                    expandir_liga(liga_cargada, 25, 40)
                except Exception as e_exp_ed:
                    logger.warning(f"No se pudo expandir la liga editada '{league_id}': {e_exp_ed}")
                try:
                    from alpha_football.market import asignar_valores_iniciales
                    asignar_valores_iniciales(liga_cargada)
                except Exception as e_asg_ed:
                    logger.warning(f"No se pudieron asignar valores/potenciales a la liga editada '{league_id}': {e_asg_ed}")
                logger.info(f"Liga '{league_id}' cargada exitosamente desde la base de datos editada por el usuario.")
                return liga_cargada
        except Exception as error_carga_json:
            # En caso de error al parsear o abrir el JSON, registramos el detalle y continuamos con la carga por defecto
            logger.error(f"Error al leer base de datos editada '{ruta_db_editada}' para liga '{league_id}': {error_carga_json}. Procediendo con la importación dinámica estándar.")

    try:
        # v3.7.0: importación dinámica desde el registro de países (data/<tipo>.py).
        if league_id not in _paises.TIPOS_LIGA:
            raise ValueError(f"Liga no soportada por el sistema: {league_id}")
        liga_obj = _paises.cargar_datos_liga(league_id, 1)
        if liga_obj is None:
            logger.info(f"Liga '{league_id}' sin datos todavía: no se carga.")
            return None   # v3.7.0: país sin datos → None (no un mock de BetPlay)
        if liga_obj is not None:
            # +5 suplentes por equipo (aplica a liga, carrera y amistoso, que pasan por aquí).
            try:
                from alpha_football.plantilla import expandir_liga, aplicar_techo_region
                aplicar_techo_region(league_id, liga_obj.equipos)  # v2.3.6: Sudamérica máx. 81
                expandir_liga(liga_obj, 25, 40)  # v2.3: 25 jugadores por equipo (cap 40)
            except Exception as e_suplentes:
                logger.warning(f"No se pudieron agregar suplentes a la liga '{league_id}': {e_suplentes}")
            # v0.7.1: escalar presupuestos para que el mercado sea jugable con valores realistas.
            try:
                from alpha_football.market import escalar_presupuestos
                escalar_presupuestos(liga_obj)
            except Exception as e_bud:
                logger.warning(f"No se pudieron escalar presupuestos de '{league_id}': {e_bud}")
            # v0.8.x: poblar `valor` y `potencial` de todos los jugadores antes de devolver,
            # para que ningún jugador quede en "Valor $0" en la UI (mercado, ofertas, etc).
            try:
                from alpha_football.market import asignar_valores_iniciales
                asignar_valores_iniciales(liga_obj)
            except Exception as e_asg:
                logger.warning(f"No se pudieron asignar valores/potenciales iniciales de '{league_id}': {e_asg}")
            return liga_obj
        else:
            raise ValueError("El cargador de liga retornó un objeto nulo.")
        
    except Exception as e:
        logger.error(f"Error al cargar liga '{league_id}': {e}. Usando datos de simulación fallback.")
        
        # Intentamos importar las clases de models.py para el fallback
        try:
            from alpha_football.models import Liga, Equipo, Jugador
        except Exception as e_models:
            logger.warning(f"No se pudo importar models.py: {e_models}. Creando clases mock.")
            # Definimos clases locales en caso de fallo absoluto de dependencias
            from dataclasses import dataclass
            @dataclass
            class Jugador:
                nombre: str
                apellido: str
                posicion: str
                ataque: int
                defensa: int
                fisico: int
                tecnica: int
                mental: int
                moral: int = 70
                lesion_partidos: int = 0
                @property
                def overall(self): return (self.ataque + self.defensa + self.fisico + self.tecnica + self.mental) // 5
                @property
                def nombre_completo(self): return f"{self.nombre} {self.apellido}"
            @dataclass
            class Equipo:
                nombre: str
                ciudad: str
                estrellas: float
                estilo_dt: str
                balance: int
                jugadores: list
            @dataclass
            class Liga:
                nombre: str
                tipo: str
                equipos: list
                num_jornadas: int

        # Generamos equipos y liga de fallback de manera segura
        try:
            mock_equipos = [
                Equipo(nombre="Millonarios F.C.", ciudad="Bogotá", estrellas=3.5, estilo_dt="Posesión", balance=12000000, jugadores=[]),
                Equipo(nombre="Atlético Nacional", ciudad="Medellín", estrellas=4.0, estilo_dt="Ofensivo", balance=15000000, jugadores=[]),
                Equipo(nombre="Junior de Barranquilla", ciudad="Barranquilla", estrellas=3.5, estilo_dt="Contraataque", balance=18000000, jugadores=[]),
                Equipo(nombre="América de Cali", ciudad="Cali", estrellas=3.5, estilo_dt="Presión Alta", balance=10000000, jugadores=[])
            ]
            return Liga(nombre=f"Liga Ficticia {league_id.upper()}", tipo=league_id, equipos=mock_equipos, num_jornadas=6)
        except Exception as e_build:
            logger.critical(f"Fallo crítico al construir liga fallback: {e_build}")
            return None


def load_division_teams(country_id: str, division: int):
    """
    v2.3 (Fase 9): carga la liga del país seleccionado, sea 1ª o 2ª división.
    - division=1: usa load_league_teams (flujo actual, sin cambios).
    - division=2: importa el módulo data/segunda_<country_id>.py y aplica
      las mismas pós-procesados que load_league_teams.
    Retorna el objeto Liga o None si falla.
    """
    # v2.3.1 (FIX CRÍTICO): traducir código de país a ID de liga.
    # PAISES_DISPONIBLES usa 'colombia'/'espana'/'inglaterra' pero los
    # módulos se llaman data/{betplay,laliga,premier,brasil,argentina}.py.
    pais = next((p for p in PAISES_DISPONIBLES if p['codigo'] == country_id), None)
    liga_id = pais['liga_id'] if pais else country_id
    if division == 1:
        return load_league_teams(liga_id)
    if division == 2:
        try:
            # v3.7.0: registro de países; None si el país aún no tiene datos de 2ª.
            liga_obj = _paises.cargar_datos_liga(liga_id, 2)
            if liga_obj is None:
                logger.info(f"2ª división de '{liga_id}' sin datos todavía: no se carga.")
                return None
            # v3.7.0: la 2ª editada en el editor (clave 'segunda_<tipo>') es la principal y se
            # completa hasta 12 con los datos; sus presupuestos no se re-escalan.
            nuevos = liga_obj.equipos
            editados_2a = _leer_db_editada().get(_paises.clave_db(liga_id, 2))
            if isinstance(editados_2a, list) and editados_2a:
                from alpha_football.models import Equipo
                equipos_ed = []
                for d_eq in editados_2a:
                    try:
                        equipos_ed.append(Equipo.from_dict(d_eq))
                    except Exception as e_eq2:
                        logger.warning(f"Equipo de 2ª editado inválido en '{liga_id}': {e_eq2}")
                if equipos_ed:
                    nuevos = _completar_con_datos(equipos_ed, liga_id, 2)
                    liga_obj.equipos = equipos_ed + nuevos
                    liga_obj.num_jornadas = _paises.num_jornadas(len(liga_obj.equipos))
                    for eq in liga_obj.equipos:
                        eq.division = 2
            liga_obj.nombre = _paises.nombre_liga(liga_id, 2)
            # Mismas pós-procesados que load_league_teams
            try:
                from alpha_football.plantilla import expandir_liga, aplicar_techo_region, acercar_segunda
                aplicar_techo_region(liga_id, liga_obj.equipos)  # v2.3.6: Sudamérica máx. 81
                liga_1a = load_league_teams(liga_id)             # v3.0.0: brecha 1ª-2ª de ~12
                if liga_1a and liga_1a.equipos:
                    acercar_segunda(liga_obj.equipos, liga_1a.equipos)
                expandir_liga(liga_obj, 25, 40)
            except Exception as e_exp:
                logger.warning(f"No se pudo expandir plantilla 2ª {liga_id}: {e_exp}")
            try:
                from alpha_football.market import escalar_presupuestos, asignar_valores_iniciales
                from alpha_football.models import Liga
                escalar_presupuestos(Liga(nombre='', tipo=liga_id, equipos=list(nuevos), num_jornadas=2))
                asignar_valores_iniciales(liga_obj)
            except Exception as e_mkt:
                logger.warning(f"No se pudo escalar/asignar valores 2ª {liga_id}: {e_mkt}")
            logger.info(f"2ª división de {liga_id} cargada: {len(liga_obj.equipos)} equipos")
            return liga_obj
        except Exception as e:
            logger.error(f"Error al cargar 2ª división de {liga_id}: {e}")
            return None
    return None


TIPOS_LIGA = _paises.TIPOS_LIGA   # v3.7.0: alias del registro (8 países)


from alpha_football.ui.foco import teclado_a_clic   # noqa: E402  v4.2.0: foco de teclado compartido


def botones_main() -> list:
    """v4.2.0: botones del menú inicial como (texto, rect, acción), en orden de foco de teclado."""
    return [("NUEVA PARTIDA", R_MENU_BOTONES['nueva'], 'nueva'),
            ("CARGAR PARTIDA", R_MENU_BOTONES['cargar'], 'cargar'),
            ("PARTIDO AMISTOSO", R_MENU_BOTONES['amistoso'], 'amistoso'),
            ("MODO EDICIÓN", R_MENU_BOTONES['editor'], 'editor'),
            ("OPCIONES", R_MENU_BOTONES['opciones'], 'opciones'),
            ("SALIR", R_MENU_BOTONES['salir'], 'salir')]


def rects_paises() -> list:
    """v3.7.0: grilla de 8 países del alta / amistoso (4 filas × 2 columnas, orden por filas)."""
    x0, y0, w, h, gap_x, gap_y = 100, 270, 262, 58, 8, 8   # cabe a la izquierda del panel derecho (x≈640)
    return [pygame.Rect(x0 + (i % 2) * (w + gap_x), y0 + (i // 2) * (h + gap_y), w, h)
            for i in range(len(PAISES_DISPONIBLES))]


# v3.9.0: rects del menú expuestos (los usa la ayuda de la tecla H); render los usa tal cual.
R_MENU_BOTONES = {
    'nueva': pygame.Rect(100, 256, 320, 50), 'cargar': pygame.Rect(100, 312, 320, 50),
    'amistoso': pygame.Rect(100, 368, 320, 50), 'editor': pygame.Rect(100, 424, 320, 50),
    'opciones': pygame.Rect(100, 480, 320, 50), 'salir': pygame.Rect(100, 536, 320, 50),
}
R_PANEL_DERECHO = pygame.Rect(640, 100, 520, 520)
R_VOLVER_ABAJO = pygame.Rect(540, 640, 200, 50)       # país / división (alta y amistoso)
R_INFO_PAIS = pygame.Rect(740, 280, 460, 290)
R_INFO_CLUB = pygame.Rect(760, 220, 420, 380)
R_DT_NOMBRE = pygame.Rect(100, 272, 430, 44)
R_DT_NAC_LIBRE = pygame.Rect(560, 365, 320, 42)
R_DT_CONFIRMAR = pygame.Rect(560, 540, 320, 52)
R_DT_VOLVER = pygame.Rect(100, 600, 200, 48)
R_CARGA_VOLVER = pygame.Rect(100, 600, 200, 50)
R_EQUIPO_VOLVER = pygame.Rect(100, 610, 180, 48)     # v3.9.0: antes y=590 pisaba la 6ª fila
R_AMIS_OTRO_PAIS = pygame.Rect(340, 620, 230, 50)   # v3.9.0: bajo la 6ª fila de clubes (antes y=600 la pisaba)
R_AMIS_VOLVER = pygame.Rect(100, 620, 200, 50)


def rects_division(amistoso: bool = False) -> tuple:
    """v3.9.0: botones 1ª y 2ª división (alta: 540×134; amistoso: 440×110)."""
    btn_w, btn_h = (440, 110) if amistoso else (540, 134)
    cx = SCREEN_W // 2
    ys = (290, 410) if amistoso else (285, 432)
    return tuple(pygame.Rect(cx - btn_w // 2, y, btn_w, btn_h) for y in ys)


def rects_equipos(n: int, amistoso: bool = False) -> list:
    """v3.9.0: grilla de clubes de 2 columnas (alta: desde y=220 cada 65; amistoso: desde y=230)."""
    y0 = 230 if amistoso else 220
    return [pygame.Rect(100 + (i % 2) * 330, y0 + (i // 2) * 65, 300, 50) for i in range(n)]


def rects_nacionalidades() -> list:
    """v3.9.0: botones de nacionalidades sugeridas del alta del DT (2 columnas)."""
    return [pygame.Rect(100 + (i % 2) * 215, 365 + (i // 2) * 46, 200, 38) for i in range(len(NACIONALIDADES))]


def rects_slots_carga() -> list:
    """v3.9.0: (slot, botón BORRAR) de los 5 slots de CARGAR PARTIDA."""
    return [(pygame.Rect(100, 245 + i * 64, 560, 54), pygame.Rect(1080, 245 + i * 64, 100, 54)) for i in range(5)]


def _paso_pais(idx: int, key) -> int:
    """v3.7.0: navegación por teclado en la grilla (←→ columna, ↑↓ fila)."""
    n = len(PAISES_DISPONIBLES) or 1
    paso = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1, pygame.K_UP: -2, pygame.K_DOWN: 2}.get(key, 0)
    return (int(idx) + paso) % n


def texto_division(tipo: str, division: int) -> str:
    """v3.7.0: "12 equipos · 22 jornadas" (calculado; todas las ligas son de 12)."""
    n = _paises.EQUIPOS_POR_LIGA
    return f"{n} equipos · {_paises.num_jornadas(n)} jornadas"


def sincronizar_nombres_ligas(primeras: dict, segunda: dict) -> None:
    """v3.7.0: liga.nombre = el del registro / editor (lo muestran hub, resumen, finanzas...)."""
    for div, mapa in ((1, primeras or {}), (2, segunda or {})):
        for tipo, liga in mapa.items():
            try:
                if liga is not None:
                    liga.nombre = _paises.nombre_liga(tipo, div)
            except Exception as e_nom:
                logger.error(f"No se pudo actualizar el nombre de la liga {tipo}: {e_nom}")


def _ligas_por_division(liga_user, primeras: dict, segunda: dict):
    """
    v2.3.5: completa los mapas {tipo: Liga} de 1ª y 2ª división de los 5 países.
    - La liga del usuario ocupa su lugar (mismo objeto, nunca una copia aparte).
    - Las que falten (carrera nueva o save viejo) se cargan desde los datos.
    - Saves viejos: se quitan de la otra división del país los equipos que ya están en la del user.
    """
    div_user = getattr(liga_user, 'division', 1) if liga_user else 1
    tipo_user = getattr(liga_user, 'tipo', None)
    for tipo in TIPOS_LIGA:
        if liga_user is not None and tipo == tipo_user:
            (primeras if div_user == 1 else segunda)[tipo] = liga_user
        if tipo not in primeras:
            liga_1a = load_league_teams(tipo)
            if liga_1a:
                liga_1a.division = 1
                primeras[tipo] = liga_1a
        if tipo not in segunda:
            liga_2a = load_division_teams(tipo, 2)
            if liga_2a:
                segunda[tipo] = liga_2a
        if liga_user is not None and tipo == tipo_user:
            otra = (segunda if div_user == 1 else primeras).get(tipo)
            if otra is not None:
                ids_user = {e.id for e in liga_user.equipos}
                otra.equipos = [e for e in otra.equipos if e.id not in ids_user]
    sincronizar_nombres_ligas(primeras, segunda)   # v3.7.0: nombres del editor también en saves
    try:  # v3.1.0: clásicos (saves viejos y carreras nuevas; no pisa los editados)
        from alpha_football.data.clasicos import asignar_rivales
        asignar_rivales([e for l in list(primeras.values()) + list(segunda.values())
                         if l is not None for e in l.equipos])
    except Exception as e_cl:
        logger.error(f"No se pudieron asignar los clásicos: {e_cl}")
    return primeras, segunda


def _dibujar_balon_decorativo(screen: pygame.Surface, cx: int, cy: int, radio: int, angulo: float):
    """
    Dibuja un balón de fútbol alegre dinámicamente usando comandos de dibujo de Pygame.
    El balón se compone de un círculo blanco y pentágonos internos orientados según el ángulo.
    """
    try:
        # Dibujar círculo exterior blanco con borde negro
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), radio)
        pygame.draw.circle(screen, (10, 14, 26), (cx, cy), radio, width=2)
        
        # Pentágono central
        largo_pent = radio * 0.35
        puntos_pent = []
        for i in range(5):
            ang = i * 2 * math.pi / 5 + angulo
            x = cx + int(largo_pent * math.cos(ang))
            y = cy + int(largo_pent * math.sin(ang))
            puntos_pent.append((x, y))
        
        try:
            pygame.draw.polygon(screen, (20, 26, 46), puntos_pent)
        except Exception:
            # Fallback si falla el polígono
            pass
        
        # Conectar vértices centrales a la periferia y dibujar gajos externos
        for i in range(5):
            x_centro, y_centro = puntos_pent[i]
            # Dirección radial
            ang_per = i * 2 * math.pi / 5 + angulo
            x_per = cx + int(radio * math.cos(ang_per))
            y_per = cy + int(radio * math.sin(ang_per))
            pygame.draw.line(screen, (10, 14, 26), (x_centro, y_centro), (x_per, y_per), 2)
            
            # Dibujar pequeños triángulos en la periferia para simular los gajos del balón
            ang_der = ang_per + math.pi / 5
            x_der = cx + int(radio * math.cos(ang_der))
            y_der = cy + int(radio * math.sin(ang_der))
            
            ang_izq = ang_per - math.pi / 5
            x_izq = cx + int(radio * math.cos(ang_izq))
            y_izq = cy + int(radio * math.sin(ang_izq))
            
            # Líneas del gajo externo
            try:
                pygame.draw.polygon(screen, (10, 14, 26), [puntos_pent[i], (x_der, y_der), (x_izq, y_izq)], width=1)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error al dibujar balón decorativo: {e}")


def _dibujar_logo_fallback(screen: pygame.Surface, x: int, y: int):
    """
    Dibuja un logo dinámico y alegre directamente en pantalla con Pygame
    si no está disponible el archivo logo.png.
    """
    try:
        # Caja contenedora del logo (estilo mini campo de fútbol)
        ancho, alto = 400, 100
        rect_caja = pygame.Rect(x, y, ancho, alto)
        
        # Fondo verde césped y borde brillante con esquinas redondeadas
        try:
            pygame.draw.rect(screen, (15, 80, 45), rect_caja, border_radius=10)
            pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), rect_caja, width=3, border_radius=10)
        except TypeError:
            pygame.draw.rect(screen, (15, 80, 45), rect_caja)
            pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), rect_caja, width=3)
        
        # Líneas de campo de fútbol de adorno
        pygame.draw.line(screen, (255, 255, 255), (x + ancho // 2, y), (x + ancho // 2, y + alto), 2)
        try:
            pygame.draw.circle(screen, (255, 255, 255), (x + ancho // 2, y + alto // 2), 22, width=2)
        except Exception:
            pass
        
        # Balón animado en el centro
        _dibujar_balon_decorativo(screen, x + ancho // 2, y + alto // 2, 12, pygame.time.get_ticks() / 1000.0)
        
        # Textos a los lados
        font = get_font('lg')
        # Lado izquierdo
        texto_izq = font.render("ALPHA", True, COLORS.get('blanco', (255, 255, 255)))
        rect_izq = texto_izq.get_rect(center=(x + ancho // 4, y + alto // 2))
        screen.blit(texto_izq, rect_izq)
        
        # Lado derecho
        texto_der = font.render("FOOTBALL", True, COLORS.get('verde', (0, 255, 136)))
        rect_der = texto_der.get_rect(center=(x + 3 * ancho // 4, y + alto // 2))
        screen.blit(texto_der, rect_der)
        
    except Exception as e:
        logger.error(f"Error al dibujar logo fallback: {e}")
        # Dibujar un texto de respaldo básico si todo falla
        draw_text(screen, "ALPHA FOOTBALL", (x, y), size='xl', color='verde')


def _dibujar_logo_principal(screen: pygame.Surface, x: int, y: int, estado: dict):
    """
    Intenta cargar y dibujar el logotipo oficial en formato imagen PNG.
    Si el archivo no está en disco, delega en el renderizado vectorial de respaldo.
    """
    try:
        # Cachear en el estado para optimizar lecturas de disco
        if 'cached_logo' in estado:
            if estado['cached_logo'] is not None:
                screen.blit(estado['cached_logo'], (x, y))
                return
            else:
                _dibujar_logo_fallback(screen, x, y)
                return
                
        # Ruta de búsqueda de la imagen
        ruta_logo = os.path.join("alpha_football", "assets", "logo.png")
        
        if os.path.exists(ruta_logo):
            try:
                logo_img = pygame.image.load(ruta_logo).convert_alpha()
                # Escalar suavemente al tamaño de la interfaz a la izquierda (400x100)
                logo_img = pygame.transform.smoothscale(logo_img, (400, 100))
                estado['cached_logo'] = logo_img
                screen.blit(logo_img, (x, y))
                return
            except Exception as e_load:
                logger.error(f"Error cargando imagen del logo: {e_load}. Usando fallback.")
                estado['cached_logo'] = None
        else:
            logger.info("El archivo de logotipo no se encuentra en disco. Usando fallback vectorial.")
            estado['cached_logo'] = None
            
        _dibujar_logo_fallback(screen, x, y)
        
    except Exception as e:
        logger.error(f"Error general en _dibujar_logo_principal: {e}. Dibujando texto básico.")
        draw_text(screen, "ALPHA FOOTBALL", (x, y), size='xl', color='verde')


def _inicializar_y_dibujar_particulas(screen: pygame.Surface, estado: dict):
    """
    Actualiza y dibuja partículas alegres flotantes de fondo para ambientar el juego.
    Las partículas pueden ser balones pequeños, estrellas doradas o confeti multicolor.
    """
    try:
        # Inicializar partículas si no existen en el estado
        if 'particulas' not in estado or not estado['particulas']:
            particulas = []
            for _ in range(25):  # 25 partículas es un buen balance de rendimiento
                particulas.append({
                    'x': random.randint(0, SCREEN_W),
                    'y': random.randint(0, SCREEN_H),
                    'vx': random.uniform(-0.8, 0.8),
                    'vy': random.uniform(0.4, 1.2),  # Movimiento hacia abajo
                    'tipo': random.choice(['balon', 'estrella', 'confeti']),
                    'tamano': random.randint(8, 14),
                    'angulo': random.uniform(0, 360),
                    'rotacion': random.uniform(-1.5, 1.5),
                    'color': random.choice([COLORS['verde'], COLORS['azul'], COLORS['dorado'], COLORS['rojo']])
                })
            estado['particulas'] = particulas
            
        # Actualizar y dibujar cada partícula
        for p in estado['particulas']:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['angulo'] += p['rotacion']
            
            # Reposicionar si sale de la pantalla
            if p['y'] > SCREEN_H + 20:
                p['y'] = -20
                p['x'] = random.randint(0, SCREEN_W)
                p['vy'] = random.uniform(0.4, 1.2)
            if p['x'] < -20 or p['x'] > SCREEN_W + 20:
                p['x'] = random.randint(0, SCREEN_W)
                
            px, py = int(p['x']), int(p['y'])
            tam = p['tamano']
            
            if p['tipo'] == 'balon':
                # Dibujar un pequeño balón de fútbol
                pygame.draw.circle(screen, (255, 255, 255), (px, py), tam)
                pygame.draw.circle(screen, (10, 14, 26), (px, py), tam, width=1)
                for i in range(3):
                    rad = i * math.pi / 3 + p['angulo']
                    ex = px + int(tam * math.cos(rad))
                    ey = py + int(tam * math.sin(rad))
                    pygame.draw.line(screen, (10, 14, 26), (px, py), (ex, ey), 1)
            elif p['tipo'] == 'estrella':
                # Dibujar estrella de 5 puntas
                puntos = []
                for i in range(10):
                    r = tam if i % 2 == 0 else tam // 2
                    rad = i * math.pi / 5 + p['angulo']
                    puntos.append((px + r * math.cos(rad), py + r * math.sin(rad)))
                try:
                    pygame.draw.polygon(screen, p['color'], puntos)
                except Exception:
                    pass
            else:
                # Dibujar confeti rectangular
                ancho_c, alto_c = tam, tam // 2
                rad = p['angulo']
                cos_a, sin_a = math.cos(rad), math.sin(rad)
                puntos_rect = [
                    (px + int(-ancho_c*cos_a - -alto_c*sin_a), py + int(-ancho_c*sin_a + -alto_c*cos_a)),
                    (px + int(ancho_c*cos_a - -alto_c*sin_a), py + int(ancho_c*sin_a + -alto_c*cos_a)),
                    (px + int(ancho_c*cos_a - alto_c*sin_a), py + int(ancho_c*sin_a + alto_c*cos_a)),
                    (px + int(-ancho_c*cos_a - alto_c*sin_a), py + int(-ancho_c*sin_a + alto_c*cos_a))
                ]
                try:
                    pygame.draw.polygon(screen, p['color'], puntos_rect)
                except Exception:
                    pass
                
    except Exception as e:
        logger.error(f"Error al procesar partículas en el menú: {e}. Limpiando lista para evitar caídas.")
        estado['particulas'] = []


def _dibujar_fondo_futbol(screen: pygame.Surface):
    """
    Dibuja un fondo futbolístico alegre con bandas de césped verde alternantes y líneas de campo
    sobre el gradiente azul base para mantener una atmósfera de estadio premium.
    """
    try:
        # 1. Dibujar el gradiente azul base de fondo
        draw_gradient_bg(screen)
        
        # 2. Dibujar franjas de césped semi-transparentes
        ancho_franja = 80
        surf_patron = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        
        # Bandas verdes neón extremadamente sutiles
        for x in range(0, SCREEN_W, ancho_franja * 2):
            pygame.draw.rect(surf_patron, (0, 255, 136, 8), (x, 0, ancho_franja, SCREEN_H))
            
        # 3. Dibujar líneas de cal del campo de fútbol con brillo semi-transparente
        color_linea = (255, 255, 255, 20)
        
        # Línea de medio campo
        pygame.draw.line(surf_patron, color_linea, (SCREEN_W // 2, 0), (SCREEN_W // 2, SCREEN_H), 2)
        # Círculo central
        try:
            pygame.draw.circle(surf_patron, color_linea, (SCREEN_W // 2, SCREEN_H // 2), 160, width=2)
            pygame.draw.circle(surf_patron, color_linea, (SCREEN_W // 2, SCREEN_H // 2), 6)
        except Exception:
            pass
        
        # Área de portería izquierda (cerca de los menús alineados a la izquierda)
        try:
            pygame.draw.rect(surf_patron, color_linea, (-2, SCREEN_H // 2 - 200, 220, 400), width=2)
            pygame.draw.rect(surf_patron, color_linea, (-2, SCREEN_H // 2 - 100, 80, 200), width=2)
            pygame.draw.arc(surf_patron, color_linea, (120, SCREEN_H // 2 - 80, 200, 160), -math.pi/2, math.pi/2, width=2)
        except Exception:
            pass
        
        # Área de portería derecha
        try:
            pygame.draw.rect(surf_patron, color_linea, (SCREEN_W - 218, SCREEN_H // 2 - 200, 220, 400), width=2)
            pygame.draw.rect(surf_patron, color_linea, (SCREEN_W - 78, SCREEN_H // 2 - 100, 80, 200), width=2)
            pygame.draw.arc(surf_patron, color_linea, (SCREEN_W - 320, SCREEN_H // 2 - 80, 200, 160), math.pi/2, 3*math.pi/2, width=2)
        except Exception:
            pass
        
        screen.blit(surf_patron, (0, 0))
        
    except Exception as e:
        logger.error(f"Error al dibujar fondo de fútbol alegre: {e}. Usando color de fondo plano como fallback.")
        try:
            screen.fill(COLORS.get('bg', (10, 14, 26)))
        except Exception:
            pass


def _dibujar_boton_premium(screen: pygame.Surface, rect: pygame.Rect, texto: str, hover: bool) -> pygame.Rect:
    """
    Dibuja un botón interactivo elegante y premium con bordes redondeados y efectos interactivos.
    Si hay hover, el botón se desplaza ligeramente, el borde brilla en verde neón y aparece un balón alegre girando.
    """
    button_rect = pygame.Rect(rect)
    try:
        # Desplazamiento interactivo suave cuando hay hover
        if hover:
            dibujo_rect = pygame.Rect(button_rect.left + 8, button_rect.top, button_rect.width - 8, button_rect.height)
            bg_color = (25, 38, 70)          # Fondo azulado/verde brillante
            border_color = COLORS.get('verde', (0, 255, 136))   # Borde verde neón
            text_color = COLORS.get('verde', (0, 255, 136))     # Texto verde
        else:
            dibujo_rect = button_rect
            bg_color = COLORS.get('panel', (20, 26, 46))       # Fondo azul oscuro
            border_color = COLORS.get('azul', (0, 191, 255))    # Borde azul celeste
            text_color = COLORS.get('blanco', (255, 255, 255))  # Texto blanco
            
        # Dibujar sombra del botón para efecto tridimensional
        sombra_rect = pygame.Rect(dibujo_rect.left + 3, dibujo_rect.top + 3, dibujo_rect.width, dibujo_rect.height)
        try:
            pygame.draw.rect(screen, (5, 8, 15), sombra_rect, border_radius=8)
        except TypeError:
            pygame.draw.rect(screen, (5, 8, 15), sombra_rect)
            
        # Dibujar el cuerpo del botón
        try:
            pygame.draw.rect(screen, bg_color, dibujo_rect, border_radius=8)
            pygame.draw.rect(screen, border_color, dibujo_rect, width=2, border_radius=8)
        except TypeError:
            pygame.draw.rect(screen, bg_color, dibujo_rect)
            pygame.draw.rect(screen, border_color, dibujo_rect, width=2)
            
        # Dibujo del texto e iconos
        font = get_font('md')
        text_surf = font.render(texto, True, text_color)
        text_rect = text_surf.get_rect()
        
        if hover:
            # Dibujar el balón flotando y girando al lado del texto
            angulo_balon = pygame.time.get_ticks() / 200.0
            bx = dibujo_rect.left + 25
            by = dibujo_rect.centery
            _dibujar_balon_decorativo(screen, bx, by, 10, angulo_balon)
            # Centrar texto en el espacio restante del botón
            text_rect.center = (dibujo_rect.left + (dibujo_rect.width + 35) // 2, dibujo_rect.centery)
        else:
            text_rect.center = dibujo_rect.center
            
        screen.blit(text_surf, text_rect)
        
    except Exception as e:
        logger.error(f"Error en _dibujar_boton_premium para '{texto}': {e}. Usando fallback.")
        # Fallback a draw_button de theme.py
        try:
            draw_button(screen, rect, texto, hover)
        except Exception:
            pass
            
    return button_rect


def _dibujar_boton_rojo(screen: pygame.Surface, rect: pygame.Rect, texto: str, hover: bool) -> pygame.Rect:
    """
    Dibuja un botón rojo premium interactivo con bordes redondeados y efectos interactivos.
    Utilizado para confirmación y acciones destructivas (p.ej. eliminar slots de guardado).
    """
    button_rect = pygame.Rect(rect)
    try:
        if hover:
            dibujo_rect = pygame.Rect(button_rect.left, button_rect.top - 2, button_rect.width, button_rect.height)
            bg_color = (60, 20, 25)
            border_color = COLORS.get('rojo', (255, 68, 68))
            text_color = COLORS.get('rojo', (255, 68, 68))
        else:
            dibujo_rect = button_rect
            bg_color = COLORS.get('panel', (20, 26, 46))
            border_color = COLORS.get('rojo', (255, 68, 68))
            text_color = COLORS.get('blanco', (255, 255, 255))
            
        sombra_rect = pygame.Rect(dibujo_rect.left + 3, dibujo_rect.top + 3, dibujo_rect.width, dibujo_rect.height)
        try:
            pygame.draw.rect(screen, (5, 8, 15), sombra_rect, border_radius=8)
        except TypeError:
            pygame.draw.rect(screen, (5, 8, 15), sombra_rect)
            
        try:
            pygame.draw.rect(screen, bg_color, dibujo_rect, border_radius=8)
            pygame.draw.rect(screen, border_color, dibujo_rect, width=2, border_radius=8)
        except TypeError:
            pygame.draw.rect(screen, bg_color, dibujo_rect)
            pygame.draw.rect(screen, border_color, dibujo_rect, width=2)
            
        font = get_font('sm')
        text_surf = font.render(texto, True, text_color)
        text_rect = text_surf.get_rect(center=dibujo_rect.center)
        screen.blit(text_surf, text_rect)
    except Exception as e:
        logger.error(f"Error al dibujar boton rojo: {e}")
    return button_rect



def _dibujar_panel_derecho(screen: pygame.Surface, estado: dict):
    """
    Dibuja un panel informativo premium y alegre sobre el fútbol en el lado derecho de la pantalla
    para equilibrar visualmente el menú principal alineado a la izquierda.
    """
    try:
        panel_rect = R_PANEL_DERECHO
        
        # Dibujar panel con esquinas redondeadas y brillo dual
        try:
            pygame.draw.rect(screen, (15, 22, 40, 200), panel_rect, border_radius=15) # Fondo semi-transparente
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), panel_rect, width=2, border_radius=15) # Borde exterior
            
            borde_interno = pygame.Rect(panel_rect.left + 4, panel_rect.top + 4, panel_rect.width - 8, panel_rect.height - 8)
            pygame.draw.rect(screen, (0, 255, 136, 40), borde_interno, width=1, border_radius=12)
        except TypeError:
            pygame.draw.rect(screen, COLORS.get('panel', (20, 26, 46)), panel_rect)
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), panel_rect, width=2)

        # Frases de fútbol alegres y tácticas
        frases = [
            "¡El fútbol se juega con la mente, pero se siente con el corazón!",
            "¡Diseña la táctica perfecta, domina el mediocampo y alcanza la copa!",
            "¡El verdadero estratega ve el espacio donde otros solo ven rivales!",
            "¡Precios reales en el mercado! Ficha con inteligencia y cabeza.",
            "¡Las copas internacionales te esperan para escribir tu nombre en la gloria!",
            "¡Alinea tu equipo con alegría y entrena a las futuras estrellas mundiales!",
            "¡El grito de gol es el idioma universal de la alegría táctica!"
        ]
        
        # Elegir frase basándose en los ticks de pygame
        indice_frase = (pygame.time.get_ticks() // 8000) % len(frases)
        frase_actual = frases[indice_frase]
        
        # Dibujar título del panel
        draw_text(screen, "DIARIO DE ESTRATEGIA", (670, 130), size='lg', color='verde')
        
        # Dibujar gran balón de fútbol alegre en el centro del panel con levitación suave
        levitacion = int(10 * math.sin(pygame.time.get_ticks() / 500.0))
        cx, cy = 900, 310 + levitacion
        angulo_giro = pygame.time.get_ticks() / 1000.0
        
        # Sombra del balón
        try:
            pygame.draw.ellipse(screen, (5, 8, 15), (cx - 60, 410, 120, 20))
        except Exception:
            pass
        
        # Balón principal
        _dibujar_balon_decorativo(screen, cx, cy, 70, angulo_giro)
        
        # Dibujar la frase motivadora envuelta
        font_sm = get_font('sm')
        
        # Envoltura de texto
        palabras = frase_actual.split(' ')
        lineas = []
        linea_actual = ""
        for palabra in palabras:
            test_linea = linea_actual + palabra + " "
            if font_sm.size(test_linea)[0] > 440:
                lineas.append(linea_actual.strip())
                linea_actual = palabra + " "
            else:
                linea_actual = test_linea
        if linea_actual:
            lineas.append(linea_actual.strip())
            
        # Dibujar líneas de texto
        y_texto = 450
        for linea in lineas:
            text_surf = font_sm.render(linea, True, COLORS.get('blanco', (255, 255, 255)))
            text_rect = text_surf.get_rect(center=(900, y_texto))
            screen.blit(text_surf, text_rect)
            y_texto += 22
            
    except Exception as e:
        logger.error(f"Error al dibujar panel derecho decorativo: {e}")


def _dibujar_estrellas_prestigio(screen: pygame.Surface, x: int, y: int, estrellas_count: float, estado: dict):
    """
    Dibuja el prestigio del equipo usando las imágenes de estrellas de st-1,
    o cae a caracteres dorados si los assets no están disponibles.
    """
    try:
        # Carga perezosa de imágenes de estrella en el estado
        if 'star_active' not in estado:
            import os
            ruta_act = os.path.join("alpha_football", "assets", "star_active.png")
            ruta_inact = os.path.join("alpha_football", "assets", "star_inactive.png")
            
            estado['star_active'] = None
            estado['star_inactive'] = None
            
            if os.path.exists(ruta_act):
                try:
                    estado['star_active'] = pygame.image.load(ruta_act).convert_alpha()
                except Exception:
                    pass
            if os.path.exists(ruta_inact):
                try:
                    estado['star_inactive'] = pygame.image.load(ruta_inact).convert_alpha()
                except Exception:
                    pass
                    
        img_act = estado.get('star_active')
        img_inact = estado.get('star_inactive')
        
        # Dibujar las estrellas
        if img_act and img_inact:
            pos_x = x
            for i in range(5):
                # Decidir si la estrella se muestra activa
                if i < estrellas_count:
                    screen.blit(img_act, (pos_x, y))
                else:
                    screen.blit(img_inact, (pos_x, y))
                pos_x += 36
        else:
            # Fallback a caracteres unicode dorados "★"
            stars_int = int(estrellas_count)
            stars_str = "★" * stars_int
            if estrellas_count % 1 >= 0.5:
                stars_str += "½"
            stars_str += "☆" * (5 - len(stars_str))
            draw_text(screen, stars_str, (x, y), size='md', color='dorado')
            
    except Exception as e:
        logger.error(f"Error al dibujar estrellas de prestigio: {e}")


def _aplicar_estado_cargado(estado: dict, loaded) -> bool:
    """Vuelca un EstadoJuego cargado en el estado runtime del juego. True si OK."""
    if not loaded:
        return False
    try:
        liga = loaded.ligas[0] if loaded.ligas else None
        mi_equipo = None
        if liga and loaded.equipo_usuario_id:
            for eq in liga.equipos:
                if eq.id == loaded.equipo_usuario_id:
                    mi_equipo = eq
                    break
        
        # --- EXPANSIÓN RESILIENTE DE PLANTILLA AL CARGAR ---
        # Si la liga viene de un save con plantillas viejas (menos jugadores),
        # las expandimos con suplentes generados para garantizar que el usuario
        # siempre tenga fondo de banco completo.
        try:
            from alpha_football.plantilla import expandir_liga
            if liga:
                expandir_liga(liga, 25, 40)  # v2.3: 25 jugadores base, tope 40
        except Exception as error_expansion_carga:
            logger.warning(f"No se pudo expandir plantillas al cargar save: {error_expansion_carga}")

        # v0.8.x: rellenar `valor` y `potencial` al cargar save. Los saves viejos o los
        # jugadores que no han jugado nunca tenían `valor=0`, mostrando "Valor $0" en
        # la UI. Se recalcula con la fórmula real al cargar.
        try:
            if liga:
                from alpha_football.market import asignar_valores_iniciales
                asignar_valores_iniciales(liga)
        except Exception as e_asg_save:
            logger.warning(f"No se pudieron asignar valores/potenciales al cargar save: {e_asg_save}")

        slot = estado.get('slot_activo')  # preservar si ya venía marcado
        estado.clear()
        estado['liga'] = liga
        estado['mi_equipo'] = mi_equipo
        estado['equipos'] = liga.equipos if liga else []
        estado['temporada'] = loaded.temporada
        estado['jornada'] = liga.jornada_actual if liga else 1
        estado['copas'] = loaded.copas
        estado['transfer_log'] = list(loaded.transfer_log)
        estado['historial'] = list(loaded.historial)
        estado['dt_nombre'] = getattr(loaded, 'dt_nombre', "")
        estado['dt_nacionalidad'] = getattr(loaded, 'dt_nacionalidad', "")
        
        # v3.8.0: las copas viven en datos_carrera['copas'] (motor de competiciones). Un save viejo
        # con la copa vieja a mitad de temporada deja sus claves para que el hub la regenere
        # (copa_screen.sincronizar_copa_user). Las claves derivadas las recalcula el hub.
        if getattr(loaded, 'copa_tipo', None) is not None and not (getattr(loaded, 'datos_carrera', None) or {}).get('copas'):
            estado['copa_fase_actual'] = loaded.copa_fase_actual or 'grupos'
            estado['copa_bracket'] = dict(loaded.copa_bracket or {})
        _motivo_cargado = getattr(loaded, 'copa_clasificado_motivo', '') or ''
        if _motivo_cargado:
            estado['copa_clasificado_motivo'] = _motivo_cargado

        # v2.3 (Fase 8): restaurar división del usuario (1 o 2) para saber en qué
        # división quedó el user tras el último swap de promoción/relegación.
        # v2.3.5: la división del usuario sale de su propia liga (siempre se guarda);
        # los saves viejos sin el campo ya no quedan en 1ª por error.
        estado['liga_usuario_division'] = int(getattr(liga, 'division', 0) or getattr(loaded, 'liga_usuario_division', 1) or 1)

        # v2.3.5: las 10 ligas (1ª y 2ª de los 5 países) vienen del save; la del user
        # ES su liga (mismo objeto). Los saves viejos regeneran las que falten.
        try:
            primeras, segunda = _ligas_por_division(
                liga,
                dict(getattr(loaded, 'primera_division', None) or {}),
                dict(getattr(loaded, 'segunda_division', None) or {}),
            )
            estado['primera_division'] = primeras
            estado['segunda_division'] = segunda
            from alpha_football.nombres import desduplicar   # v4.4.0: sin nombres repetidos
            desduplicar(estado)
        except Exception as e_divs:
            logger.error(f"Error preparando 1ª/2ª divisiones: {e_divs}")
            estado['primera_division'] = {}
            estado['segunda_division'] = {}

        # v2.3.6: clasificación real a copas + historial del Balón de Oro
        estado['datos_carrera'] = dict(getattr(loaded, 'datos_carrera', None) or {})
        # v2.3.7: valores según la región de cada liga (antes los de las ligas de fondo
        # sudamericanas salían a precio europeo) y, en saves viejos, presupuestos
        # realistas para los clubes de la IA (el del user no se toca).
        try:
            from alpha_football.market import registrar_regiones, calcular_valor
            from alpha_football.mercado_ia import ligas_de_la_partida, asignar_presupuestos_realistas
            registrar_regiones(estado)
            for liga_x, _t, _d in ligas_de_la_partida(estado):
                for eq in liga_x.equipos:
                    for j in eq.jugadores:
                        j.valor = calcular_valor(j)
            if not estado['datos_carrera'].get('presupuestos_v237'):
                asignar_presupuestos_realistas(estado, incluir_usuario=False)
                estado['datos_carrera']['presupuestos_v237'] = True
            # v2.3.8: nacionalidades (para los regens) y más techo para los jóvenes
            from alpha_football.retiros import asignar_nacionalidades
            asignar_nacionalidades(estado)
            if not estado['datos_carrera'].get('potencial_v238'):
                from alpha_football.desarrollo import migrar_potencial_jovenes
                migrar_potencial_jovenes([e for l, _t, _d in ligas_de_la_partida(estado) for e in l.equipos])
                estado['datos_carrera']['potencial_v238'] = True
        except Exception as e_eco:
            logger.error(f"No se pudo preparar la economía de la partida: {e_eco}")

        if slot:
            estado['slot_activo'] = slot
        if loaded.alineacion_activa:
            estado['alineacion_activa'] = loaded.alineacion_activa
            if mi_equipo:
                mi_equipo.alineacion_activa = loaded.alineacion_activa
        elif mi_equipo:
            from alpha_football.models import alineacion_por_defecto
            da = alineacion_por_defecto(mi_equipo)
            estado['alineacion_activa'] = da
            mi_equipo.alineacion_activa = da
        estado['current_screen'] = 'league_screen'
        return True
    except Exception as e:
        logger.error(f"Error al aplicar estado cargado: {e}")
        return False


def render(screen: pygame.Surface, estado: dict) -> str | None:
    """
    Dibuja la pantalla del menú y gestiona los clics e interacciones del usuario.
    Retorna la acción elegida (por ejemplo, 'league_screen') o None si permanece en el menú.
    """
    # 1. Inicialización y validación del paso actual del menú
    if 'menu_step' not in estado:
        estado['menu_step'] = 'main'
    # v3.9.0: con el foco en el nombre / nacionalidad del DT, H se escribe (no abre la ayuda)
    estado['texto_activo'] = (estado.get('menu_step') == 'dt_setup'
                              and estado.get('dt_focus', 'name') in ('name', 'nac'))
        
    # Inicialización del audio si no se ha iniciado
    if not estado.get('music_started', False):
        try:
            from alpha_football import audio
            try:
                audio.init_audio()
            except Exception as e_init:
                logger.warning(f"No se pudo inicializar sistema de audio: {e_init}")
            try:
                audio.start_music()
                estado['music_started'] = True
            except Exception as e_start:
                logger.warning(f"No se pudo reproducir música de fondo: {e_start}")
        except Exception as e_import:
            logger.debug(f"Módulo de audio no disponible para el menú: {e_import}")

    # 2. Captura segura de posición de ratón y clics del frame actual
    mouse_pos = pygame.mouse.get_pos()
    click_pos = None
    key_events = []  # v0.7: teclas para el alta del DT (nombre / nacionalidad libre)

    try:
        # Extraemos eventos del cache (manejado por el orquestador principal main.py)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Re-postear para que main.py actúe ante el quit
                pygame.event.post(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clic izquierdo
                    click_pos = event.pos
            elif event.type == pygame.KEYDOWN:
                key_events.append(event)
    except Exception as e_events:
        logger.error(f"Error al procesar eventos en render de menú: {e_events}")

    # 3. Dibujar fondo de fútbol y partículas alegres
    _dibujar_fondo_futbol(screen)
    _inicializar_y_dibujar_particulas(screen, estado)

    # --- PANTALLA PRINCIPAL DEL MENÚ (ALINEADO A LA IZQUIERDA) ---
    if estado['menu_step'] == 'main':
        # Dibujar logo y eslogan alineados a la izquierda
        _dibujar_logo_principal(screen, 100, 100, estado)
        draw_text(screen, "La revolución táctica pixelada", (100, 215), size='sm', color='azul')

        # v4.2.0: botones con foco de teclado (↑ ↓ / Tab mueven, Enter elige; el mouse mueve el foco)
        botones = botones_main()
        foco = int(estado.get('menu_foco', 0) or 0) % len(botones)
        for i, (_t, r, _a) in enumerate(botones):
            if r.collidepoint(mouse_pos) and estado.get('_menu_mouse_prev') != mouse_pos:
                foco = i
        estado['_menu_mouse_prev'] = mouse_pos
        accion = None
        for ev in key_events:
            if ev.key in (pygame.K_DOWN, pygame.K_TAB):
                foco = (foco + 1) % len(botones)
            elif ev.key == pygame.K_UP:
                foco = (foco - 1) % len(botones)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                accion = botones[foco][2]
        estado['menu_foco'] = foco
        for i, (texto, r, _a) in enumerate(botones):
            _dibujar_boton_premium(screen, r, texto, i == foco)

        # Dibujar panel de ambientación a la derecha
        _dibujar_panel_derecho(screen, estado)

        # Lógica de clics
        if click_pos:
            accion = next((a for _t, r, a in botones if r.collidepoint(click_pos)), accion)
        if accion == 'nueva':
            estado['menu_step'] = 'select_country'
        elif accion == 'cargar':
            estado['menu_step'] = 'load_slots'   # Fase 2: selector de slots
        elif accion == 'amistoso':
            # v2.3 (Fase 9): País → División → Equipo. Igual que nueva partida pero
            # con flag de amistoso.
            estado['amis_local'] = None
            estado['amis_visitante'] = None
            estado['amis_phase'] = 'local'
            estado['menu_step'] = 'amistoso_country'
        elif accion == 'editor':
            estado['current_screen'] = 'edit_screen'
            return 'edit_screen'
        elif accion == 'opciones':
            estado['options_return'] = 'menu'
            estado['current_screen'] = 'options_screen'
            return 'options_screen'
        elif accion == 'salir':
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        # Render de errores temporales
        if 'menu_error' in estado:
            if pygame.time.get_ticks() - estado.get('menu_error_ticks', 0) > 3000:
                estado.pop('menu_error', None)
                estado.pop('menu_error_ticks', None)
            else:
                draw_text(screen, estado['menu_error'], (100, 505), size='md', color='rojo')

    # --- SELECCIÓN DE PAÍS (v2.3 / Fase 9) ---
    elif estado['menu_step'] == 'select_country':
        # Mostrar cabecera del logo y título alineados a la izquierda
        _dibujar_logo_principal(screen, 100, 80, estado)
        draw_text(screen, "SELECCIONA UN PAÍS", (100, 195), size='lg', color='verde')
        draw_text(screen, "Cada país tiene 1ª y 2ª División. Elige dónde empezar.",
                  (100, 235), size='sm', color='azul')
        # Hint de teclado (nuevo en esta tanda)
        draw_text(screen, "[Flechas = mover · Enter = elegir país · Esc = volver]",
                  (100, 660), size='sm', color='azul')

        # v2.3 (Fase 9 bugfix): botones más compactos y posicionados para que
        # quepan los 5 países sin solaparse con el botón VOLVER ni con el header.
        start_y = 280
        btn_w, btn_h = 380, 56
        spacing_y = 8

        # Inicializar el índice de país resaltado por teclado (persistente)
        if 'pais_keyboard_idx' not in estado:
            estado['pais_keyboard_idx'] = 0

        # Resaltado por teclado: tiene prioridad sobre el hover del mouse.
        # ↑/↓ mueven el índice, Enter selecciona, Esc vuelve.
        for ev in key_events:
            if ev.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):   # v3.7.0: grilla
                estado['pais_keyboard_idx'] = _paso_pais(estado['pais_keyboard_idx'], ev.key)
            elif ev.key == pygame.K_RETURN or ev.key == pygame.K_SPACE:
                # Simula click en el país resaltado por teclado
                idx = estado['pais_keyboard_idx']
                if 0 <= idx < len(PAISES_DISPONIBLES):
                    pais = PAISES_DISPONIBLES[idx]
                    estado['selected_country_id'] = pais['codigo']
                    estado['selected_league_id'] = pais['liga_id']
                    estado['menu_step'] = 'select_division'
            elif ev.key == pygame.K_ESCAPE:
                estado['menu_step'] = 'main'
            # rueda del mouse para navegar
            elif ev.type == pygame.MOUSEWHEEL:
                if ev.y > 0:
                    estado['pais_keyboard_idx'] = (estado['pais_keyboard_idx'] - 1) % len(PAISES_DISPONIBLES)
                elif ev.y < 0:
                    estado['pais_keyboard_idx'] = (estado['pais_keyboard_idx'] + 1) % len(PAISES_DISPONIBLES)

        volver_rect = R_VOLVER_ABAJO  # Esquina inferior derecha
        hover_volver = volver_rect.collidepoint(mouse_pos)

        # Dibujar los países (botones con emoji-pill + nombre grande)
        hovered_pais = None
        kb_idx = int(estado.get('pais_keyboard_idx', 0))
        for i, pais in enumerate(PAISES_DISPONIBLES):
            btn_rect = rects_paises()[i]   # v3.7.0: grilla 4×2
            hover = btn_rect.collidepoint(mouse_pos)
            kb_selected = (i == kb_idx)
            if hover or kb_selected:
                hovered_pais = pais
            try:
                # Fondo del botón (hover o teclado tienen prioridad)
                if kb_selected and not hover:
                    bg = (50, 60, 100)  # azul-violeta para teclado
                elif hover:
                    bg = (30, 45, 75)
                else:
                    bg = (12, 18, 36)
                pygame.draw.rect(screen, bg, btn_rect, border_radius=8)
                # Borde (dorado si está resaltado por teclado, verde si es hover, azul normal)
                if kb_selected and not hover:
                    borde = COLORS.get('dorado', (255, 215, 0))
                    borde_w = 3
                elif hover:
                    borde = COLORS.get('verde', (0, 255, 136))
                    borde_w = 3
                else:
                    borde = COLORS.get('azul', (0, 191, 255))
                    borde_w = 2
                pygame.draw.rect(screen, borde, btn_rect, width=borde_w, border_radius=8)
                # Pill del emoji a la izquierda
                pill = pygame.Rect(btn_rect.x + 6, btn_rect.y + 6, 38, btn_rect.height - 12)   # v3.7.0: más angosta
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), pill, border_radius=6)
                draw_text(screen, pais['emoji'], (pill.x + 4, pill.y + 12), size='md',
                          color='azul', shadow=False)
                # Indicador de selección por teclado
                if kb_selected and not hover:
                    draw_text(screen, "▶", (btn_rect.x + btn_rect.width - 30, btn_rect.y + 18),
                              size='lg', color='dorado')
            except Exception:
                pass
            # Nombre del país en grande
            draw_text(screen, pais['nombre'].upper(),
                      (btn_rect.x + 52, btn_rect.y + 6), size='lg',
                      color='dorado' if (kb_selected and not hover) else ('verde' if hover else 'blanco'))
            # Subtítulo: nombre de la liga
            nombre_1a = _paises.nombre_liga(pais['liga_id'], 1)   # v3.7.0: con el nombre del editor
            draw_text(screen, nombre_1a if len(nombre_1a) <= 23 else nombre_1a[:22] + "…",
                      (btn_rect.x + 52, btn_rect.y + 34), size='sm', color='azul')

            if click_pos and btn_rect.collidepoint(click_pos):
                estado['selected_country_id'] = pais['codigo']
                estado['selected_league_id'] = pais['liga_id']   # compat
                estado['menu_step'] = 'select_division'

        # Panel derecho con info del país hover
        panel_rect = R_INFO_PAIS
        draw_panel(screen, panel_rect)
        if hovered_pais:
            try:
                draw_text(screen, hovered_pais['nombre'].upper(), (760, 300),
                          size='xl', color='dorado')
                _tid = hovered_pais['liga_id']   # v3.7.0: nombres del editor + equipos/jornadas calculados
                draw_text(screen, f"1ª: {_paises.nombre_liga(_tid, 1)[:40]}", (760, 350), size='sm', color='verde')
                draw_text(screen, f"    {texto_division(_tid, 1)} · Copa Internacional",
                          (760, 374), size='sm', color='blanco')
                draw_text(screen, f"2ª: {_paises.nombre_liga(_tid, 2)[:40]}", (760, 408), size='sm', color='verde')
                draw_text(screen, f"    {texto_division(_tid, 2)} · Ascenso/Descenso",
                          (760, 432), size='sm', color='blanco')
                draw_text(screen, "Elige tu división en la siguiente pantalla.",
                          (760, 470), size='md', color='dorado')
            except Exception:
                pass
        else:
            draw_text(screen, "INFORMACIÓN DEL PAÍS", (760, 300), size='lg', color='azul')
            draw_text(screen, "Pasa el mouse sobre", (760, 360), size='md', color='blanco')
            draw_text(screen, "un país para ver sus", (760, 390), size='md', color='blanco')
            draw_text(screen, "ligas disponibles.", (760, 420), size='md', color='blanco')

        # Botón Volver
        _dibujar_boton_premium(screen, volver_rect, "VOLVER", hover_volver)
        if click_pos and volver_rect.collidepoint(click_pos):
            estado['menu_step'] = 'main'

        # v3.9.1: sin el "Diario de estrategia" aquí: se dibujaba encima del panel de info del país.

        # Mostrar error si existe
        if 'menu_error' in estado:
            if pygame.time.get_ticks() - estado.get('menu_error_ticks', 0) > 3000:
                estado.pop('menu_error', None)
                estado.pop('menu_error_ticks', None)
            else:
                draw_text(screen, estado['menu_error'], (100, 570), size='sm', color='rojo')

    # --- SELECCIÓN DE DIVISIÓN (v2.3 / Fase 9) ---
    elif estado['menu_step'] == 'select_division':
        # Cabecera con país elegido
        _dibujar_logo_principal(screen, 100, 80, estado)
        draw_text(screen, "SELECCIONA LA DIVISIÓN", (100, 195), size='lg', color='verde')
        pais = next((p for p in PAISES_DISPONIBLES
                     if p['codigo'] == estado.get('selected_country_id')), None)
        if pais:
            draw_text(screen, f"País: [{pais['emoji']}] {pais['nombre'].upper()}",
                      (100, 235), size='md', color='dorado')
        _tipo_div = pais['liga_id'] if pais else ''   # v3.7.0
        # Hint de teclado
        draw_text(screen, "[↑ ↓ Enter = elegir · Esc = volver]",
                  (100, 660), size='sm', color='azul')

        # v2.3 (Fase 9 bugfix): botón VOLVER reubicado para no chocar
        # con los botones de división y visible a la derecha.
        volver_rect = R_VOLVER_ABAJO
        hover_volver = volver_rect.collidepoint(mouse_pos)

        # Resaltado por teclado: el índice activo se persiste en estado.
        if 'division_keyboard_idx' not in estado:
            estado['division_keyboard_idx'] = 0

        # 2 botones grandes centrados
        btn_w, btn_h = 540, 134   # v3.7.0: las 3 líneas de info no se salían del botón
        cx = SCREEN_W // 2
        btn_1a = pygame.Rect(cx - btn_w // 2, 285, btn_w, btn_h)
        btn_2a = pygame.Rect(cx - btn_w // 2, 432, btn_w, btn_h)

        # Procesar teclado: ↑↓ mueve el índice, Enter selecciona, Esc vuelve.
        for ev in key_events:
            if ev.key == pygame.K_UP or ev.key == pygame.K_DOWN:
                estado['division_keyboard_idx'] = 1 - int(estado.get('division_keyboard_idx', 0))
            elif ev.key == pygame.K_RETURN or ev.key == pygame.K_SPACE:
                # Simula click en 1ª o 2ª según el índice
                idx = int(estado.get('division_keyboard_idx', 0))
                estado['selected_division'] = idx + 1
                liga_obj = load_division_teams(estado.get('selected_country_id'), idx + 1)
                if liga_obj:
                    estado['selected_liga_obj'] = liga_obj
                    if estado.get('amistoso_phase') in ('local', 'visitante'):
                        estado['menu_step'] = 'amistoso_teams'
                    else:
                        estado['menu_step'] = 'select_team'
                else:
                    estado['menu_error'] = f"Error al cargar {'1ª' if idx == 0 else '2ª'} división."
                    estado['menu_error_ticks'] = pygame.time.get_ticks()
            elif ev.key == pygame.K_ESCAPE:
                estado['menu_step'] = 'select_country'

        # Teclado + hover del mouse: la selección por teclado se combina
        # con la detección del mouse para el resaltado visual.
        kb_idx = int(estado.get('division_keyboard_idx', 0))

        def _draw_div_btn(rect, titulo, color_acc, hover, info_lines):
            try:
                pygame.draw.rect(screen, (12, 18, 36), rect, border_radius=10)
                pygame.draw.rect(screen,
                                 color_acc if hover else COLORS.get('azul', (0, 191, 255)),
                                 rect, width=3, border_radius=10)
            except Exception:
                pass
            draw_text(screen, titulo, (rect.x + 22, rect.y + 14), size='xl', color=color_acc)
            for j, line in enumerate(info_lines):
                draw_text(screen, line, (rect.x + 22, rect.y + 62 + j * 22),
                          size='sm', color='blanco')

        _draw_div_btn(
            btn_1a, "1ª DIVISIÓN",
            COLORS.get('verde', (0, 255, 136)),
            btn_1a.collidepoint(mouse_pos) or (kb_idx == 0 and not click_pos),
            [
                "La elite del país. Juega la Copa Internacional.",
                f"{texto_division(_tipo_div, 1)} · Premios grandes",   # v3.7.0
                "Los primeros clasifican a Copa. Riesgo de descenso.",   # v3.7.0: el cupo varía por país
            ]
        )
        _draw_div_btn(
            btn_2a, "2ª DIVISIÓN",
            COLORS.get('azul', (0, 191, 255)),
            btn_2a.collidepoint(mouse_pos) or (kb_idx == 1 and not click_pos),
            [
                "El camino hacia la gloria. Ascenso/Descenso.",
                f"{texto_division(_tipo_div, 2)} · Premios duplicados",   # v3.7.0
                "Top 2 sube a 1ª · Bottom 2 baja a 3ª (futuro).",
            ]
        )

        if click_pos:
            if btn_1a.collidepoint(click_pos):
                estado['selected_division'] = 1
                liga_obj = load_division_teams(estado.get('selected_country_id'), 1)
                if liga_obj:
                    estado['selected_liga_obj'] = liga_obj
                    # Si estamos en amistoso, redirigir al step correcto
                    if estado.get('amistoso_phase') in ('local', 'visitante'):
                        estado['menu_step'] = 'amistoso_teams'
                    else:
                        estado['menu_step'] = 'select_team'
                else:
                    estado['menu_error'] = "Error al cargar 1ª división."
                    estado['menu_error_ticks'] = pygame.time.get_ticks()
            elif btn_2a.collidepoint(click_pos):
                estado['selected_division'] = 2
                liga_obj = load_division_teams(estado.get('selected_country_id'), 2)
                if liga_obj:
                    estado['selected_liga_obj'] = liga_obj
                    if estado.get('amistoso_phase') in ('local', 'visitante'):
                        estado['menu_step'] = 'amistoso_teams'
                    else:
                        estado['menu_step'] = 'select_team'
                else:
                    estado['menu_error'] = "Error al cargar 2ª división."
                    estado['menu_error_ticks'] = pygame.time.get_ticks()

        # Dibujar botón Volver con la nueva posición
        _dibujar_boton_premium(screen, volver_rect, "VOLVER", hover_volver)
        if click_pos and volver_rect.collidepoint(click_pos):
            estado['menu_step'] = 'select_country'

    # --- SELECCIÓN DE EQUIPO ---
    elif estado['menu_step'] == 'select_team':
        # Cabecera de logo y título alineados a la izquierda
        _dibujar_logo_principal(screen, 100, 50, estado)
        draw_text(screen, "SELECCIONA TU EQUIPO", (100, 160), size='lg', color='verde')

        # Cargar equipos de la liga activa
        equipos = []
        if 'selected_liga_obj' in estado and estado['selected_liga_obj']:
            equipos = estado['selected_liga_obj'].equipos

        # Coordenadas del grid de equipos (2 columnas a la izquierda)
        grid_x = 100
        grid_y = 220
        col_w = 300
        row_h = 50
        spacing_x = 30
        spacing_y = 15

        hovered_team = None
        # v4.2.0: teclado (flechas + Enter; ESC vuelve)
        rects_eq = [pygame.Rect(grid_x + (i % 2) * (col_w + spacing_x), grid_y + (i // 2) * (row_h + spacing_y),
                                col_w, row_h) for i in range(len(equipos))]
        foco_eq, clic_tec = teclado_a_clic(estado, 'menu_foco_equipo', rects_eq, key_events, columnas=2,
                                           esc_rect=R_EQUIPO_VOLVER)
        click_pos = clic_tec or click_pos
        if equipos and 0 <= foco_eq < len(equipos) and not any(r.collidepoint(mouse_pos) for r in rects_eq):
            hovered_team = equipos[foco_eq]

        # Renderizar cada botón de equipo
        for i, equipo in enumerate(equipos):
            btn_rect = rects_eq[i]
            hover_eq = btn_rect.collidepoint(mouse_pos) or (i == foco_eq and hovered_team is equipo)

            if btn_rect.collidepoint(mouse_pos):
                hovered_team = equipo

            _dibujar_boton_premium(screen, btn_rect, equipo.nombre, hover_eq)

            if click_pos and btn_rect.collidepoint(click_pos):
                # v0.7: antes de empezar, el usuario crea su DT (nombre + nacionalidad).
                estado['pending_equipo'] = equipo
                estado['menu_step'] = 'dt_setup'
                estado.setdefault('dt_nombre', "")
                estado.setdefault('dt_nac_sel', "")
                estado['dt_name_focus'] = True

        # Panel de detalles en la derecha
        panel_rect = R_INFO_CLUB
        draw_panel(screen, panel_rect)

        if hovered_team:
            # Detalles del equipo sobre el que está el mouse
            draw_text(screen, hovered_team.nombre, (780, 240), size='lg', color='verde')
            draw_text(screen, f"Ciudad: {hovered_team.ciudad}", (780, 295), size='md', color='blanco')
            
            # Dibujar estrellas de prestigio (usando assets o fallback)
            draw_text(screen, "Prestigio: ", (780, 335), size='md', color='blanco')
            _dibujar_estrellas_prestigio(screen, 880, 330, hovered_team.estrellas, estado)
            
            try:  # v3.4.0: nombre para mostrar del estilo, no la clave cruda
                from alpha_football.estilos import NOMBRE_ESTILO, normalizar_estilo
                _estilo_txt = NOMBRE_ESTILO.get(normalizar_estilo(hovered_team.estilo_dt), hovered_team.estilo_dt)
            except Exception as e_est:
                logger.error(f"Error al leer el nombre del estilo: {e_est}")
                _estilo_txt = hovered_team.estilo_dt
            draw_text(screen, f"Estilo de Juego: {_estilo_txt}", (780, 375), size='md', color='azul')
            draw_text(screen, f"Presupuesto: ${hovered_team.balance:,}", (780, 415), size='md', color='verde')
            
            # Mostrar primer jugador estrella disponible
            if hasattr(hovered_team, 'jugadores') and hovered_team.jugadores:
                try:
                    estrella = max(hovered_team.jugadores, key=lambda j: getattr(j, 'overall', 70))
                    draw_text(screen, f"Estrella: {estrella.nombre_completo} (OVR {getattr(estrella, 'overall', 70)})", (780, 465), size='sm', color='dorado')
                except Exception:
                    pass
        else:
            # Texto informativo predeterminado
            draw_text(screen, "INFORMACIÓN DEL CLUB", (780, 240), size='lg', color='azul')
            draw_text(screen, "Pasa el mouse sobre", (780, 300), size='md', color='blanco')
            draw_text(screen, "un equipo para ver sus", (780, 340), size='md', color='blanco')
            draw_text(screen, "estadísticas detalladas.", (780, 380), size='md', color='blanco')

        # Botón Volver
        volver_rect = R_EQUIPO_VOLVER
        hover_vol = volver_rect.collidepoint(mouse_pos)
        _dibujar_boton_premium(screen, volver_rect, "VOLVER", hover_vol)
        if click_pos and volver_rect.collidepoint(click_pos):
            # v2.3: volver a selección de división (no de país)
            estado['menu_step'] = 'select_division'

    # --- ALTA DEL DT: NOMBRE + NACIONALIDAD (v0.7) ---
    elif estado['menu_step'] == 'dt_setup':
        _dibujar_logo_principal(screen, 100, 55, estado)
        draw_text(screen, "CREA TU DIRECTOR TÉCNICO", (100, 170), size='lg', color='verde')
        equipo = estado.get('pending_equipo')
        if equipo:
            draw_text(screen, f"Club elegido: {getattr(equipo, 'corto', None) or equipo.nombre}", (100, 210), size='sm', color='dorado')

        estado.setdefault('dt_nac_custom', "")
        estado.setdefault('dt_focus', 'name')

        # Campo de nombre del DT
        draw_text(screen, "Nombre del DT:", (100, 248), size='sm', color='blanco')
        name_rect = R_DT_NOMBRE
        foco_name = (estado['dt_focus'] == 'name')
        pygame.draw.rect(screen, (12, 18, 36), name_rect, border_radius=6)
        pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)) if foco_name else COLORS.get('azul', (0, 191, 255)),
                         name_rect, width=2, border_radius=6)
        nombre_txt = estado.get('dt_nombre', '') or "Escribe tu nombre…"
        draw_text(screen, nombre_txt[:30], (name_rect.x + 10, name_rect.y + 12), size='sm',
                  color='blanco' if estado.get('dt_nombre') else 'azul')

        # Nacionalidades sugeridas (botones)
        draw_text(screen, "Nacionalidad:", (100, 335), size='sm', color='blanco')
        nac_rects = []
        for i, pais in enumerate(NACIONALIDADES):
            col = i % 2
            row = i // 2
            r = rects_nacionalidades()[i]
            nac_rects.append((r, pais))
            sel = (estado.get('dt_nac_sel') == pais and not estado.get('dt_nac_custom', '').strip())
            _dibujar_boton_premium(screen, r, pais, r.collidepoint(mouse_pos) or sel)

        # Campo de nacionalidad libre
        draw_text(screen, "Otra nacionalidad:", (560, 335), size='sm', color='blanco')
        nac_rect = R_DT_NAC_LIBRE
        foco_nac = (estado['dt_focus'] == 'nac')
        pygame.draw.rect(screen, (12, 18, 36), nac_rect, border_radius=6)
        pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)) if foco_nac else COLORS.get('azul', (0, 191, 255)),
                         nac_rect, width=2, border_radius=6)
        nac_txt = estado.get('dt_nac_custom', '') or "Escribe otra…"
        draw_text(screen, nac_txt[:24], (nac_rect.x + 8, nac_rect.y + 11), size='sm',
                  color='blanco' if estado.get('dt_nac_custom') else 'azul')

        # v4.2.0: Tab recorre nombre → lista de nacionalidades → otra; en la lista, flechas eligen
        teclas_texto = []
        for ev in key_events:
            if ev.key == pygame.K_TAB:
                estado['dt_focus'] = {'name': 'lista', 'lista': 'nac'}.get(estado['dt_focus'], 'name')
            elif estado['dt_focus'] == 'lista' and ev.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                i = NACIONALIDADES.index(estado['dt_nac_sel']) if estado.get('dt_nac_sel') in NACIONALIDADES else -1
                paso = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1, pygame.K_UP: -2, pygame.K_DOWN: 2}[ev.key]
                estado['dt_nac_sel'] = NACIONALIDADES[max(0, min(len(NACIONALIDADES) - 1, i + paso if i >= 0 else 0))]
                estado['dt_nac_custom'] = ""
            elif ev.key not in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                teclas_texto.append(ev)

        # Procesar teclado en el campo enfocado
        for ev in teclas_texto:
            campo = 'dt_nombre' if estado['dt_focus'] == 'name' else ('dt_nac_custom' if estado['dt_focus'] == 'nac' else None)
            if not campo:
                continue
            if ev.key == pygame.K_BACKSPACE:
                estado[campo] = estado.get(campo, '')[:-1]
            elif getattr(ev, 'unicode', '') and ev.unicode.isprintable() and len(estado.get(campo, '')) < 24:
                estado[campo] = estado.get(campo, '') + ev.unicode

        # Botones de acción
        nac_final = (estado.get('dt_nac_custom', '').strip() or estado.get('dt_nac_sel', '')).strip()
        listo = bool(estado.get('dt_nombre', '').strip()) and bool(nac_final)
        btn_conf = R_DT_CONFIRMAR
        btn_volver = R_DT_VOLVER
        _dibujar_boton_premium(screen, btn_conf, "EMPEZAR CARRERA" if listo else "FALTAN DATOS",
                               btn_conf.collidepoint(mouse_pos) or listo)
        _dibujar_boton_premium(screen, btn_volver, "VOLVER", btn_volver.collidepoint(mouse_pos))
        draw_text(screen, "Tab cambia de campo · Enter empieza · Esc vuelve", (560, 600), size='sm', color='azul')
        for ev in key_events:   # v4.2.0: Enter = EMPEZAR (si está listo), ESC = VOLVER
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and listo:
                click_pos = btn_conf.center
            elif ev.key == pygame.K_ESCAPE:
                click_pos = btn_volver.center

        if click_pos:
            if name_rect.collidepoint(click_pos):
                estado['dt_focus'] = 'name'
            elif nac_rect.collidepoint(click_pos):
                estado['dt_focus'] = 'nac'
            elif btn_volver.collidepoint(click_pos):
                estado['menu_step'] = 'select_team'
            elif btn_conf.collidepoint(click_pos) and listo:
                try:
                    equipo = estado.get('pending_equipo')
                    liga_obj = estado.get('selected_liga_obj')
                    dt_nombre_final = estado.get('dt_nombre', '').strip() or "DT Parodia"
                    if not equipo or not liga_obj:
                        logger.error("Falta pending_equipo o selected_liga_obj al confirmar DT")
                        return "menu"
                    # v2.3.2 (FIX): capturar pais/division ANTES del clear() para que
                    # no queden vacios despues.
                    _pais_sel = estado.get('selected_country_id', '')
                    _div_sel = int(estado.get('selected_division', 1) or 1)
                    # v0.8.3: LIMPIEZA TOTAL del estado antes de empezar una carrera nueva.
                    # Sin esto, ofertas/mercado/copa/audio/etc. de la partida anterior
                    # se filtraban a la nueva (ej. ofertas de un BetPlay aparecian en
                    # un Real Madrid). Ahora se garantiza aislamiento por partida.
                    estado.clear()
                    # Re-inicializar claves esenciales (defaults vacíos para evitar KeyError)
                    estado['liga'] = liga_obj
                    estado['mi_equipo'] = equipo
                    estado['equipos'] = liga_obj.equipos
                    estado['temporada'] = 1
                    estado['jornada'] = 1
                    estado['historial'] = []
                    estado['transfer_log'] = []
                    estado['fichajes_realizados'] = 0
                    estado['dt_nombre'] = dt_nombre_final
                    estado['dt_nacionalidad'] = nac_final
                    estado['datos_carrera'] = {}  # v2.3.6: ranking de copas + Balón de Oro
                    # v2.3 (Fase 9): persistir país + división elegidos
                    estado['selected_country_id'] = _pais_sel
                    estado['selected_division'] = _div_sel
                    estado['liga_usuario_division'] = _div_sel
                    # v2.3: cargar las 5 ligas de 2ª división on-demand (necesarias para el swap
                    # de promoción/relegación y para que la pantalla de liga las pueda mostrar).
                    # v2.3.5: las 10 ligas de la carrera; la del user ES su liga.
                    from alpha_football.ui import pantalla_carga
                    pantalla_carga.mostrar("INICIANDO CARRERA", "Cargando las 10 ligas", 0.1)
                    estado['primera_division'], estado['segunda_division'] = _ligas_por_division(liga_obj, {}, {})
                    from alpha_football.nombres import desduplicar   # v4.4.0: sin nombres repetidos
                    desduplicar(estado)
                    # v2.3.7: presupuestos realistas (liga, división y prestigio) para todos
                    pantalla_carga.mostrar("INICIANDO CARRERA", "Presupuestos y nacionalidades", 0.45)
                    try:
                        from alpha_football.mercado_ia import asignar_presupuestos_realistas
                        asignar_presupuestos_realistas(estado, incluir_usuario=True)
                        estado['datos_carrera']['presupuestos_v237'] = True
                        estado['datos_carrera']['potencial_v238'] = True  # ya nace con la tabla nueva
                        from alpha_football.retiros import asignar_nacionalidades
                        asignar_nacionalidades(estado)
                    except Exception as e_eco:
                        logger.error(f"No se pudieron asignar presupuestos realistas: {e_eco}")
                    # El equipo del user está en la división que eligió
                    equipo.division = _div_sel
                    estado['current_screen'] = "league_screen"
                    # Defaults vacíos para evitar herencia de keys obsoletas
                    for _k in ('ofertas_recibidas', 'mercado', 'mercado_ofertas',
                               '_pool_internacional', 'free_agents_list', 'free_agents_clave',
                               'recent_offers_player_ids', 'mercado_ofertas_temp',
                               'ultima_ventana_mercado_id',
                               'sim_comentarios', 'sim_eventos', 'sim_minuto_por_jugador',
                               'sim_nota_por_jugador', 'sim_asist_por_jugador',
                               'now_playing_text', 'oferta_toast_text', 'oferta_toast_until',
                               '_ofertas_prev_count', 'prepartido_resultado'):
                        estado[_k] = []
                    # v3.8.0: fuera el estado de la copa vieja y las caches del motor de la carrera anterior
                    for _k in ('copa_fase_actual', 'copa_tab', 'copa_jornada_grupo', 'copa_grupos',
                               'copa_grupos_standings', 'copa_grupo_standing', 'copa_grupo_partidos',
                               'copa_bracket', 'copa_bracket_otros', 'copa_tipo', '_copas_pool',
                               '_copas_ligas_cache', '_copas_generados', '_hub_copa_sync',
                               'copa_vista', 'copa_pestana', 'copa_fecha_sel', '_copa_sync_clave'):
                        estado.pop(_k, None)
                    for _k in ('copa_mejor_fase_temp', 'match_mode',
                               'partido_actual', 'partido_local_obj', 'partido_visitante_obj',
                               'partido_copa_dict', 'partido_copa_bracket_fase',
                               'sim_resultado', 'sim_estado', 'sim_velocidad_factor',
                               'sim_minuto', 'sim_goles_l', 'sim_goles_v',
                               'sim_desarrollo', 'sim_desarrollo_done',
                               'sim_eventos_procesados', 'sim_flash_goles',
                               'sim_goleador_flash', 'sim_confeti', 'sim_tactico_abierto',
                               'sim_sub_out', 'sim_subs_realizadas', 'sim_salieron',
                               'sim_alin_partido', 'sim_dir_snapshot',
                               'sim_penales_resuelto', 'sim_penales_marcador',
                               'sim_penales_gana_user', 'sim_penales_sel',
                               'sim_last_tick'):
                        estado[_k] = None
                    # Táctica por defecto al iniciar carrera: equilibrada (cambiable luego).
                    equipo.estilo_dt = "anchelottismo"
                    if not getattr(equipo, 'tactica_familiaridad', None):
                        equipo.tactica_familiaridad = {}
                    # v3.8.0: las copas de la T1 se sortean con el motor (cupos por media de cada
                    # 1ª); en 2ª división no se clasifica. Las claves copa_* se derivan de ahí.
                    estado['copa_clasificado_motivo'] = ("En 2ª división no se clasifica a copa."
                                                         if _div_sel == 2 else "")
                    pantalla_carga.mostrar("INICIANDO CARRERA", "Sorteando las copas", 0.75)
                    try:
                        from alpha_football.ui.copa_screen import iniciar_copas_temporada
                        iniciar_copas_temporada(estado, forzar=True)
                    except Exception as e_clasif:
                        logger.error(f"Error al sortear las copas de la T1: {e_clasif}")
                        estado['copa_clasificado'] = False
                        estado['copa_user_en_copa'] = False
                        estado['copa_clasificado_motivo'] = "Default (cálculo falló)"
                    from alpha_football.models import alineacion_por_defecto
                    def_alin = alineacion_por_defecto(equipo)
                    estado['alineacion_activa'] = def_alin
                    equipo.alineacion_activa = def_alin
                    for k in ('menu_step', 'selected_league_id', 'selected_liga_obj', 'pending_equipo',
                              'dt_focus', 'dt_nac_sel', 'dt_nac_custom', 'dt_name_focus',
                              'amistoso_phase', 'amistoso_country_id', 'amistoso_division'):
                        estado.pop(k, None)
                    # NOTA: 'selected_country_id' y 'selected_division' NO se popean aqui;
                    # los seteamos antes del clear() y los conservamos para el save.
                    logger.info(f"Nueva carrera iniciada: liga={estado['liga'].tipo} equipo={equipo.nombre}")
                    estado['contrato_modo'] = 'alta'      # v3.2.0: firma estilo FIFA antes del hub
                    pantalla_carga.mostrar("INICIANDO CARRERA", "Listo", 1.0)
                    return "contrato_dt_screen"
                except Exception as e_dt:
                    logger.error(f"Error al finalizar alta del DT: {e_dt}")
                finally:
                    from alpha_football.ui import pantalla_carga as _pc
                    _pc.cerrar()
            else:
                for r, pais in nac_rects:
                    if r.collidepoint(click_pos):
                        estado['dt_nac_sel'] = pais
                        estado['dt_nac_custom'] = ""
                        estado['dt_focus'] = None

    # --- CARGAR PARTIDA: SELECTOR DE SLOTS (Fase 2) ---
    elif estado['menu_step'] == 'load_slots':
        _dibujar_logo_principal(screen, 100, 70, estado)
        draw_text(screen, "CARGAR PARTIDA — ELIGE UN SLOT", (100, 185), size='lg', color='verde')
        try:
            from alpha_football import save
            cabeceras = save.listar_slots()
        except Exception as e_ls:
            logger.error(f"No se pudieron listar los slots: {e_ls}")
            cabeceras = [None] * 5

        # v4.2.0: ↑ ↓ slot, Enter carga, Supr borra, Esc vuelve (con el modal abierto: Enter sí, Esc no)
        foco_slot = int(estado.get('menu_foco_slot', 0) or 0) % 6
        if not estado.get('confirmar_borrar_slot'):
            rects_carga = [rs[0] for rs in rects_slots_carga()] + [R_CARGA_VOLVER]
            foco_slot, clic_tec = teclado_a_clic(estado, 'menu_foco_slot', rects_carga, key_events,
                                                 esc_rect=R_CARGA_VOLVER)
            click_pos = clic_tec or click_pos
            if any(ev.key == pygame.K_DELETE for ev in key_events) and foco_slot < 5:
                if foco_slot < len(cabeceras) and cabeceras[foco_slot]:
                    click_pos = rects_slots_carga()[foco_slot][1].center
        for i in range(5):
            r, del_rect = rects_slots_carga()[i]
            hdr = cabeceras[i] if i < len(cabeceras) else None
            etiqueta = f"Slot {i+1}: {hdr.get('nombre_partida','Partida')}" if hdr else f"Slot {i+1}: [Slot Libre]"
            _dibujar_boton_premium(screen, r, etiqueta, r.collidepoint(mouse_pos) or i == foco_slot)
            
            if hdr:
                # v0.8.7.2: dos líneas con DT + equipo y temp/jor/presupuesto
                draw_text(screen,
                          f"DT: {hdr.get('dt_nombre','—')}  ·  {hdr.get('equipo_nombre','—')}",
                          (680, 245 + i * 64 + 8), size='sm', color='dorado')
                pres = int(hdr.get('presupuesto', 0) or 0)
                pres_m = pres / 1_000_000
                draw_text(screen,
                          f"Temp {hdr.get('temporada',1)}  ·  Jor {hdr.get('jornada',1)}  ·  ${pres_m:.1f}M",
                          (680, 245 + i * 64 + 30), size='sm', color='azul')
                
                # Botón de borrar rojo al extremo derecho
                hov_del = del_rect.collidepoint(mouse_pos)
                _dibujar_boton_rojo(screen, del_rect, "BORRAR", hov_del)

            # Bloquear clics normales si se está confirmando un borrado
            if not estado.get('confirmar_borrar_slot'):
                if click_pos and hdr and del_rect.collidepoint(click_pos):
                    estado['confirmar_borrar_slot'] = i + 1
                    # v0.8.5: consumir el clic que ABRE el modal. Si no, ese mismo click_pos llega
                    # al handler del modal (el botón BORRAR está fuera de modal_rect, así que
                    # `not modal_rect.collidepoint` lo cerraba al instante → el modal parpadeaba).
                    click_pos = None
                elif click_pos and r.collidepoint(click_pos) and hdr:
                    from alpha_football.ui import pantalla_carga
                    try:
                        from alpha_football import save
                        pantalla_carga.mostrar("CARGANDO PARTIDA", f"Slot {i + 1}: {hdr.get('nombre_partida', '')}")
                        loaded = save.cargar_slot(i + 1)
                        estado['slot_activo'] = i + 1
                        if _aplicar_estado_cargado(estado, loaded):
                            return 'league_screen'
                    except Exception as e_ld:
                        logger.error(f"Error al cargar slot {i+1}: {e_ld}")
                        estado['menu_error'] = "No se pudo cargar ese slot."
                        estado['menu_error_ticks'] = pygame.time.get_ticks()
                    finally:
                        pantalla_carga.cerrar()

        volver_rect = R_CARGA_VOLVER
        _dibujar_boton_premium(screen, volver_rect, "VOLVER", volver_rect.collidepoint(mouse_pos) or foco_slot == 5)
        if click_pos and volver_rect.collidepoint(click_pos) and not estado.get('confirmar_borrar_slot'):
            estado['menu_step'] = 'main'
        if 'menu_error' in estado:
            if pygame.time.get_ticks() - estado.get('menu_error_ticks', 0) > 3000:
                estado.pop('menu_error', None)
            else:
                draw_text(screen, estado['menu_error'], (100, 560), size='sm', color='rojo')

        # Modal de confirmación de borrado
        slot_a_borrar = estado.get('confirmar_borrar_slot')
        if slot_a_borrar:
            # Dibujamos un overlay oscuro translúcido
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((10, 14, 26, 210))
            screen.blit(overlay, (0, 0))
            
            modal_rect = pygame.Rect(SCREEN_W // 2 - 220, SCREEN_H // 2 - 100, 440, 200)
            pygame.draw.rect(screen, COLORS.get('panel', (20, 26, 46)), modal_rect, border_radius=12)
            pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), modal_rect, width=2, border_radius=12)
            
            draw_text(screen, "CONFIRMAR BORRADO", (modal_rect.centerx - 120, modal_rect.y + 20), size='md', color='rojo')
            draw_text(screen, f"¿Deseas eliminar la partida del Slot {slot_a_borrar}?", (modal_rect.centerx - 170, modal_rect.y + 70), size='sm', color='blanco')
            
            btn_si = pygame.Rect(modal_rect.x + 40, modal_rect.y + 120, 150, 44)
            btn_no = pygame.Rect(modal_rect.x + 250, modal_rect.y + 120, 150, 44)
            
            hov_si = btn_si.collidepoint(mouse_pos)
            hov_no = btn_no.collidepoint(mouse_pos)
            
            _dibujar_boton_rojo(screen, btn_si, "SÍ, BORRAR", hov_si)
            _dibujar_boton_premium(screen, btn_no, "CANCELAR", hov_no)
            for ev in key_events:   # v4.2.0
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    click_pos = btn_si.center
                elif ev.key == pygame.K_ESCAPE:
                    click_pos = btn_no.center
            
            if click_pos:
                if btn_si.collidepoint(click_pos):
                    try:
                        from alpha_football import save
                        save.eliminar_slot(slot_a_borrar)
                        logger.info(f"Slot {slot_a_borrar} borrado con éxito.")
                    except Exception as e_del:
                        logger.error(f"Error borrando slot {slot_a_borrar}: {e_del}")
                    estado.pop('confirmar_borrar_slot', None)
                elif btn_no.collidepoint(click_pos) or not modal_rect.collidepoint(click_pos):
                    estado.pop('confirmar_borrar_slot', None)

    # --- PARTIDO AMISTOSO: ELEGIR PAÍS (v2.3 / Fase 9) ---
    elif estado['menu_step'] == 'amistoso_country':
        _dibujar_logo_principal(screen, 100, 80, estado)
        fase = estado.get('amis_phase', 'local')
        equipo_paso = "LOCAL" if fase == 'local' else "VISITANTE"
        draw_text(screen, f"AMISTOSO — PAÍS DEL EQUIPO {equipo_paso}", (100, 195), size='lg', color='verde')
        if fase == 'visitante' and estado.get('amis_local'):
            draw_text(screen, f"Local: {estado['amis_local'].nombre}", (100, 235), size='sm', color='dorado')
        # Hint teclado
        draw_text(screen, "[↑ ↓ Enter = elegir · Esc = volver]",
                  (100, 660), size='sm', color='azul')

        # v2.3 (Fase 9 bugfix): botones compactos + VOLVER movido
        start_y = 280
        btn_w, btn_h = 380, 56
        spacing_y = 8

        if 'amistoso_pais_kb_idx' not in estado:
            estado['amistoso_pais_kb_idx'] = 0

        for ev in key_events:
            if ev.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):   # v3.7.0: grilla
                estado['amistoso_pais_kb_idx'] = _paso_pais(estado['amistoso_pais_kb_idx'], ev.key)
            elif ev.key == pygame.K_RETURN or ev.key == pygame.K_SPACE:
                idx = estado['amistoso_pais_kb_idx']
                if 0 <= idx < len(PAISES_DISPONIBLES):
                    pais = PAISES_DISPONIBLES[idx]
                    estado['amistoso_country_id'] = pais['codigo']
                    estado['menu_step'] = 'amistoso_division'
            elif ev.key == pygame.K_ESCAPE:
                estado['menu_step'] = 'main'

        volver_rect = R_VOLVER_ABAJO
        hover_volver = volver_rect.collidepoint(mouse_pos)

        for i, pais in enumerate(PAISES_DISPONIBLES):
            btn_rect = rects_paises()[i]   # v3.7.0: grilla 4×2
            hover = btn_rect.collidepoint(mouse_pos)
            kb_selected = (i == estado.get('amistoso_pais_kb_idx', 0))
            if hover or kb_selected:
                pass
            try:
                if kb_selected and not hover:
                    bg = (50, 60, 100)
                elif hover:
                    bg = (30, 45, 75)
                else:
                    bg = (12, 18, 36)
                pygame.draw.rect(screen, bg, btn_rect, border_radius=8)
                if kb_selected and not hover:
                    borde = COLORS.get('dorado', (255, 215, 0))
                    borde_w = 3
                elif hover:
                    borde = COLORS.get('verde', (0, 255, 136))
                    borde_w = 3
                else:
                    borde = COLORS.get('azul', (0, 191, 255))
                    borde_w = 2
                pygame.draw.rect(screen, borde, btn_rect, width=borde_w, border_radius=8)
                pill = pygame.Rect(btn_rect.x + 6, btn_rect.y + 6, 38, btn_rect.height - 12)   # v3.7.0
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), pill, border_radius=6)
                draw_text(screen, pais['emoji'], (pill.x + 4, pill.y + 12), size='md',
                          color='azul', shadow=False)
            except Exception:
                pass
            draw_text(screen, pais['nombre'].upper(),
                      (btn_rect.x + 52, btn_rect.y + 12), size='lg',
                      color='dorado' if (kb_selected and not hover) else ('verde' if hover else 'blanco'))
            if click_pos and btn_rect.collidepoint(click_pos):
                estado['amistoso_country_id'] = pais['codigo']
                estado['menu_step'] = 'amistoso_division'
        # Botón Volver
        _dibujar_boton_premium(screen, volver_rect, "VOLVER", hover_volver)
        if click_pos and volver_rect.collidepoint(click_pos):
            estado['menu_step'] = 'main'
        _dibujar_panel_derecho(screen, estado)

    # --- PARTIDO AMISTOSO: ELEGIR DIVISIÓN (v2.3) ---
    elif estado['menu_step'] == 'amistoso_division':
        _dibujar_logo_principal(screen, 100, 80, estado)
        fase = estado.get('amis_phase', 'local')
        equipo_paso = "LOCAL" if fase == 'local' else "VISITANTE"
        draw_text(screen, f"AMISTOSO — DIVISIÓN DEL EQUIPO {equipo_paso}", (100, 195), size='lg', color='verde')
        if fase == 'visitante' and estado.get('amis_local'):
            draw_text(screen, f"Local: {estado['amis_local'].nombre}", (100, 235), size='sm', color='dorado')
        # Hint teclado
        draw_text(screen, "[↑ ↓ Enter = elegir · Esc = volver]",
                  (100, 660), size='sm', color='azul')

        # v2.3 (Fase 9 bugfix): VOLVER movido para no chocar
        volver_rect = R_VOLVER_ABAJO
        hover_volver = volver_rect.collidepoint(mouse_pos)

        # v2.3 (Fase 9 bugfix): botones más compactos (110 alto en vez de 120)
        btn_w, btn_h = 440, 110
        cx = SCREEN_W // 2
        btn_1a = pygame.Rect(cx - btn_w // 2, 290, btn_w, btn_h)
        btn_2a = pygame.Rect(cx - btn_w // 2, 410, btn_w, btn_h)

        # Teclado: ↑↓ alterna 1ª/2ª, Enter selecciona, Esc vuelve.
        if 'amistoso_div_kb_idx' not in estado:
            estado['amistoso_div_kb_idx'] = 0
        for ev in key_events:
            if ev.key == pygame.K_UP or ev.key == pygame.K_DOWN:
                estado['amistoso_div_kb_idx'] = 1 - int(estado.get('amistoso_div_kb_idx', 0))
            elif ev.key == pygame.K_RETURN or ev.key == pygame.K_SPACE:
                idx = int(estado.get('amistoso_div_kb_idx', 0))
                estado['amistoso_division'] = idx + 1
                liga_obj = load_division_teams(estado.get('amistoso_country_id'), idx + 1)
                if liga_obj:
                    estado['amistoso_liga'] = liga_obj
                    estado['menu_step'] = 'amistoso_teams'
                else:
                    estado['menu_error'] = f"Error al cargar {'1ª' if idx == 0 else '2ª'} división."
                    estado['menu_error_ticks'] = pygame.time.get_ticks()
            elif ev.key == pygame.K_ESCAPE:
                estado['menu_step'] = 'amistoso_country'

        kb_idx = int(estado.get('amistoso_div_kb_idx', 0))

        def _draw_amis_div(rect, titulo, color_acc, hover, info_lines):
            try:
                pygame.draw.rect(screen, (12, 18, 36), rect, border_radius=10)
                pygame.draw.rect(screen,
                                 color_acc if hover else COLORS.get('azul', (0, 191, 255)),
                                 rect, width=3, border_radius=10)
            except Exception:
                pass
            draw_text(screen, titulo, (rect.x + 22, rect.y + 14), size='xl', color=color_acc)
            for j, line in enumerate(info_lines):
                draw_text(screen, line, (rect.x + 22, rect.y + 56 + j * 22),
                          size='sm', color='blanco')

        _draw_amis_div(
            btn_1a, "1ª DIVISIÓN",
            COLORS.get('verde', (0, 255, 136)),
            btn_1a.collidepoint(mouse_pos) or (kb_idx == 0 and not click_pos),
            ["La elite. Los mejores equipos del país.", texto_division('', 1)]   # v3.7.0
        )
        _draw_amis_div(
            btn_2a, "2ª DIVISIÓN",
            COLORS.get('azul', (0, 191, 255)),
            btn_2a.collidepoint(mouse_pos) or (kb_idx == 1 and not click_pos),
            ["El ascenso/descenso. OVR más bajo.", texto_division('', 2)]   # v3.7.0
        )

        if click_pos:
            if btn_1a.collidepoint(click_pos):
                estado['amistoso_division'] = 1
                liga_obj = load_division_teams(estado.get('amistoso_country_id'), 1)
                if liga_obj:
                    estado['amistoso_liga'] = liga_obj
                    estado['menu_step'] = 'amistoso_teams'
                else:
                    estado['menu_error'] = "Error al cargar 1ª división."
                    estado['menu_error_ticks'] = pygame.time.get_ticks()
            elif btn_2a.collidepoint(click_pos):
                estado['amistoso_division'] = 2
                liga_obj = load_division_teams(estado.get('amistoso_country_id'), 2)
                if liga_obj:
                    estado['amistoso_liga'] = liga_obj
                    estado['menu_step'] = 'amistoso_teams'
                else:
                    estado['menu_error'] = "Error al cargar 2ª división."
                    estado['menu_error_ticks'] = pygame.time.get_ticks()

        # Botón Volver con la nueva posición (esquina inferior derecha)
        _dibujar_boton_premium(screen, volver_rect, "VOLVER", hover_volver)
        if click_pos and volver_rect.collidepoint(click_pos):
            estado['menu_step'] = 'amistoso_country'

    # --- PARTIDO AMISTOSO: ELEGIR LOS DOS EQUIPOS (v2.3) ---
    elif estado['menu_step'] == 'amistoso_teams':
        _dibujar_logo_principal(screen, 100, 40, estado)
        fase = estado.get('amis_phase', 'local')
        local = estado.get('amis_local')
        paso = "LOCAL" if fase == 'local' else "VISITANTE"
        draw_text(screen, f"AMISTOSO — ELIGE EL EQUIPO {paso}", (100, 150), size='lg', color='verde')
        if fase == 'visitante' and local:
            draw_text(screen, f"Local: {local.nombre}", (100, 195), size='sm', color='dorado')
        liga_obj = estado.get('amistoso_liga')
        equipos = liga_obj.equipos if liga_obj else []
        # v4.2.0: flechas + Enter; ESC vuelve
        rects_am = [pygame.Rect(100 + (i % 2) * 330, 230 + (i // 2) * 65, 300, 50) for i in range(len(equipos))]
        foco_am, clic_tec = teclado_a_clic(estado, 'menu_foco_amis', rects_am, key_events, columnas=2,
                                           esc_rect=R_AMIS_VOLVER)
        click_pos = clic_tec or click_pos
        for i, equipo in enumerate(equipos):
            btn_rect = rects_am[i]
            _dibujar_boton_premium(screen, btn_rect, equipo.nombre, btn_rect.collidepoint(mouse_pos) or i == foco_am)
            if click_pos and btn_rect.collidepoint(click_pos):
                if fase == 'local':
                    # Elegido el local: ahora vamos a elegir el PAÍS del VISITANTE (puede ser otro).
                    estado['amis_local'] = equipo
                    estado['amis_phase'] = 'visitante'
                    estado['menu_step'] = 'amistoso_country'
                elif local is not None and equipo.id != local.id:
                    # Visitante elegido: lanzar el prepartido (que luego va al amistoso).
                    estado['amis_visitante'] = equipo
                    estado['match_mode'] = 'amistoso'
                    estado['partido_actual'] = None
                    estado.pop('sim_resultado', None)
                    estado['menu_step'] = 'main'
                    return 'prepartido_screen'
        # Botón para cambiar de país sin perder el equipo ya elegido.
        otra_liga_rect = R_AMIS_OTRO_PAIS
        _dibujar_boton_premium(screen, otra_liga_rect, "OTRO PAÍS", otra_liga_rect.collidepoint(mouse_pos))
        if click_pos and otra_liga_rect.collidepoint(click_pos):
            estado['menu_step'] = 'amistoso_country'
        volver_rect = R_AMIS_VOLVER
        _dibujar_boton_premium(screen, volver_rect, "VOLVER", volver_rect.collidepoint(mouse_pos))
        if click_pos and volver_rect.collidepoint(click_pos):
            estado['menu_step'] = 'amistoso_division'

    return None
