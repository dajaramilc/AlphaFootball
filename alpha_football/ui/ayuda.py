# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — AYUDA CON LA TECLA H (overlay)
v3.9.0: registro de ayuda por pantalla + dibujo del overlay. main.py llama a manejar_evento() con
cada evento del frame (con la ayuda abierta los consume todos) y a dibujar() tras el render de la
pantalla y ANTES de la barra de atajos. Cada item es (rect, titulo, texto): el rect se recorta de la
sombra con borde dorado y un círculo numerado; la leyenda va en el lado con más espacio libre.
"""
from __future__ import annotations

import logging
from typing import Callable

import pygame

logger = logging.getLogger(__name__)

Item = tuple  # (pygame.Rect, titulo: str, texto: str)

POR_PAGINA = 10
PANTALLA = pygame.Rect(0, 0, 1280, 720)
ZONA_UTIL = pygame.Rect(0, 0, 1280, 698)       # v3.9.0: la barra de atajos ocupa y = 698-720
ANCHO_LEYENDA = 420
ANCHOS_LEYENDA = (420, 360, 310)     # v3.9.0: si no hay hueco de 420, se prueba más angosta
DORADO = (255, 215, 0)
BLANCO = (255, 255, 255)
AZUL = (0, 191, 255)
FONDO_LEYENDA = (10, 14, 26, 235)
SIN_AYUDA = "Esta pantalla aún no tiene ayuda detallada. H / ESC para cerrar."

# v3.9.0: nombre de pantalla -> lista de items o función estado -> lista de items (se llena abajo)
AYUDA: dict[str, list | Callable[[dict], list]] = {}


# ════════════════════════════════════════════════════════════ motor

def items(nombre_pantalla: str, estado: dict) -> list:
    """v3.9.0: items de la pantalla (estáticos o calculados por estado), recortados a la ventana."""
    try:
        entrada = AYUDA.get(nombre_pantalla)
        if entrada is None:
            return []
        lista = entrada(estado or {}) if callable(entrada) else entrada
        salida = []
        for it in lista or []:
            try:
                r, titulo, texto = it
                r = pygame.Rect(r).clip(PANTALLA)
                if r.width > 0 and r.height > 0 and titulo and texto:
                    salida.append((r, str(titulo), str(texto)))
            except Exception:
                continue
        return salida
    except Exception as e:
        logger.error(f"No se pudieron calcular los items de ayuda de {nombre_pantalla}: {e}", exc_info=True)
        return []


def _paginas(n_items: int) -> int:
    return max(1, (n_items + POR_PAGINA - 1) // POR_PAGINA)


def _cerrar(estado: dict) -> None:
    estado['ayuda_abierta'] = False
    estado['ayuda_pagina'] = 0


def manejar_evento(estado: dict, ev, nombre_pantalla: str) -> bool:
    """v3.9.0: True si el evento lo consume la ayuda (main no lo pasa a la pantalla).
    Cerrada: solo consume H (y abre) si no hay un campo de texto activo. Abierta: consume todo
    menos QUIT; H/ESC cierran, ←/→ pasan de página."""
    try:
        tipo = getattr(ev, 'type', None)
        if not estado.get('ayuda_abierta'):
            if (tipo == pygame.KEYDOWN and ev.key == pygame.K_h
                    and not estado.get('texto_activo')):
                estado['ayuda_abierta'] = True
                estado['ayuda_pagina'] = 0
                return True
            return False
        if tipo == pygame.QUIT:
            return False
        if tipo == pygame.KEYDOWN:
            if ev.key in (pygame.K_h, pygame.K_ESCAPE):
                _cerrar(estado)
            elif ev.key in (pygame.K_RIGHT, pygame.K_LEFT):
                total = _paginas(len(items(nombre_pantalla, estado)))
                pag = int(estado.get('ayuda_pagina', 0) or 0) + (1 if ev.key == pygame.K_RIGHT else -1)
                estado['ayuda_pagina'] = max(0, min(total - 1, pag))
        return True
    except Exception as e:
        logger.error(f"Error en el manejo de la ayuda: {e}")
        return bool(estado.get('ayuda_abierta'))


# ---------------------------------------------------------------- dibujo

_FUENTES: dict = {}


def _fuente(tam: int, negrita: bool = False):
    clave = (tam, negrita)
    if clave not in _FUENTES:
        try:
            _FUENTES[clave] = pygame.font.SysFont("arial", tam, bold=negrita)
        except Exception:
            _FUENTES[clave] = pygame.font.Font(None, tam + 4)
    return _FUENTES[clave]


def _envolver(partes: list, fuente, ancho: int) -> list:
    """Parte [(texto, color), ...] en líneas de palabras [(palabra, color), ...] que caben en `ancho`."""
    lineas, linea, x = [], [], 0
    esp = fuente.size(" ")[0]
    for texto, color in partes:
        for palabra in texto.split():
            w = fuente.size(palabra)[0]
            if linea and x + w > ancho:
                lineas.append(linea)
                linea, x = [], 0
            linea.append((palabra, color, w))
            x += w + esp
    if linea:
        lineas.append(linea)
    return lineas


def _bloques(pagina: list, inicio: int, fuente, ancho: int) -> list:
    """Cada item -> líneas envueltas de 'N · Título — texto' (título en dorado)."""
    return [_envolver([(f"{inicio + i + 1} · {t} —", DORADO), (x, BLANCO)], fuente, ancho)
            for i, (_r, t, x) in enumerate(pagina)]


_PANELES: dict = {}      # v3.9.0: caché de la posición elegida (rects de la página, alto)


def _elegir_panel(rects: list, alto: int, ancho: int = ANCHO_LEYENDA) -> tuple:
    """Hueco con menos solape: recorre posiciones en rejilla de 16 px y minimiza la fracción tapada de
    cada item (tapar la mitad de un panel grande es mejor que tapar entero un botón). Empate: derecha."""
    alto = min(alto, ZONA_UTIL.height - 24)
    clave = (tuple(tuple(r) for r in rects), alto, ancho)
    if clave in _PANELES:
        p, c = _PANELES[clave]
        return p.copy(), c
    xs = list(range(12, ZONA_UTIL.right - ancho - 11, 16)) + [ZONA_UTIL.right - ancho - 12]
    ys = list(range(12, ZONA_UTIL.bottom - alto - 11, 16)) + [ZONA_UTIL.bottom - alto - 12]
    mejor, mejor_costo = None, None
    for x in reversed(xs):
        for y in ys:
            p = pygame.Rect(x, y, ancho, alto)
            costo = 0.0
            for r in rects:
                c = p.clip(r)
                if c.width and c.height:
                    costo += (c.width * c.height) / max(1, r.width * r.height) + 0.05
                    if p.colliderect(pygame.Rect(r.x - 12, r.y - 12, 28, 28)):
                        costo += 0.6          # tapar el círculo numerado es peor que tapar el rect
                if mejor_costo is not None and costo >= mejor_costo:
                    break
            if mejor_costo is None or costo < mejor_costo - 1e-9:
                mejor, mejor_costo = p, costo
        if mejor_costo == 0:
            break
    if len(_PANELES) > 200:
        _PANELES.clear()
    _PANELES[clave] = (mejor, mejor_costo)
    return mejor.copy(), mejor_costo


def _circulo(screen, centro, n: int) -> None:
    pygame.draw.circle(screen, (10, 14, 26), centro, 14)
    pygame.draw.circle(screen, DORADO, centro, 13)
    s = _fuente(15, True).render(str(n), True, (10, 14, 26))
    screen.blit(s, s.get_rect(center=centro))


def dibujar(screen, nombre_pantalla: str, estado: dict) -> None:
    """v3.9.0: oscurece la pantalla, recorta y numera los items de la página y dibuja la leyenda."""
    try:
        lista = items(nombre_pantalla, estado)
        copia = screen.copy()
        sombra = pygame.Surface(PANTALLA.size, pygame.SRCALPHA)
        sombra.fill((0, 0, 0, 150))
        screen.blit(sombra, (0, 0))
        fuente = _fuente(16)

        if not lista:
            lineas = _envolver([(SIN_AYUDA, BLANCO)], fuente, 380)
            panel = pygame.Rect(0, 0, 420, 40 + len(lineas) * 20)
            panel.center = ZONA_UTIL.center
            _panel_fondo(screen, panel)
            _lineas(screen, lineas, fuente, panel.x + 20, panel.y + 20)
            return

        total = _paginas(len(lista))
        pag = max(0, min(total - 1, int(estado.get('ayuda_pagina', 0) or 0)))
        estado['ayuda_pagina'] = pag
        inicio = pag * POR_PAGINA
        pagina = lista[inicio:inicio + POR_PAGINA]

        # agujeros: la zona de cada item se ve sin sombra, con borde dorado
        for r, _t, _x in pagina:
            screen.blit(copia, r, r)
            pygame.draw.rect(screen, DORADO, r, width=2, border_radius=4)
        for i, (r, _t, _x) in enumerate(pagina):
            cx = max(14, min(PANTALLA.right - 14, r.x + 2))
            cy = max(14, min(PANTALLA.bottom - 14, r.y + 2))
            _circulo(screen, (cx, cy), inicio + i + 1)

        # leyenda
        alto_linea = 19
        rects_pag = [r for r, _t, _x in pagina]
        mejor = None
        for ancho in ANCHOS_LEYENDA:          # la más ancha sin solape; si todas tapan, la que menos
            bl = _bloques(pagina, inicio, fuente, ancho - 28)
            alto = 44 + sum(len(b) * alto_linea + 7 for b in bl) + 26
            if alto > ZONA_UTIL.height - 24:
                continue
            p, costo = _elegir_panel(rects_pag, alto, ancho)
            if mejor is None or costo < mejor[0] - 0.02:
                mejor = (costo, p, bl)
            if costo == 0:
                break
        if mejor is None:
            bl = _bloques(pagina, inicio, fuente, ANCHO_LEYENDA - 28)
            alto = 44 + sum(len(b) * alto_linea + 7 for b in bl) + 26
            mejor = (0, _elegir_panel(rects_pag, alto)[0], bl)
        _costo, panel, bloques = mejor
        _panel_fondo(screen, panel)
        titulo = _fuente(18, True).render("AYUDA", True, AZUL)
        screen.blit(titulo, (panel.x + 14, panel.y + 10))
        y = panel.y + 40
        for b in bloques:
            if y + len(b) * alto_linea > panel.bottom - 26:
                break
            _lineas(screen, b, fuente, panel.x + 14, y)
            y += len(b) * alto_linea + 7
        pie = "H / ESC cerrar" + (f" · ← → página {pag + 1}/{total}" if total > 1 else "")
        s = _fuente(15).render(pie, True, AZUL)
        screen.blit(s, (panel.x + 14, panel.bottom - 22))
    except Exception as e:
        logger.error(f"No se pudo dibujar la ayuda de {nombre_pantalla}: {e}", exc_info=True)
    return None


def _panel_fondo(screen, panel: pygame.Rect) -> None:
    fondo = pygame.Surface(panel.size, pygame.SRCALPHA)
    fondo.fill(FONDO_LEYENDA)
    screen.blit(fondo, panel.topleft)
    pygame.draw.rect(screen, DORADO, panel, width=2, border_radius=8)


_PALABRAS: dict = {}      # v3.9.0: caché de palabras renderizadas (la leyenda se dibuja cada frame)


def _lineas(screen, lineas: list, fuente, x0: int, y: int) -> None:
    esp = fuente.size(" ")[0]
    for linea in lineas:
        x = x0
        for palabra, color, w in linea:
            clave = (palabra, color, id(fuente))
            s = _PALABRAS.get(clave)
            if s is None:
                if len(_PALABRAS) > 4000:
                    _PALABRAS.clear()
                s = _PALABRAS[clave] = fuente.render(palabra, True, color)
            screen.blit(s, (x, y))
            x += w + esp
        y += 19


# ════════════════════════════════════════════════════════════ contenido por pantalla
# v3.9.0: las entradas se registran debajo, pantalla por pantalla.

R = pygame.Rect


def _union(rects) -> pygame.Rect:
    """v3.9.0: rect que abarca una grilla/lista de rects (vacío -> rect nulo, que items() descarta)."""
    rects = [pygame.Rect(r) for r in rects if r is not None]
    if not rects:
        return R(0, 0, 0, 0)
    u = rects[0].unionall(rects[1:]) if len(rects) > 1 else rects[0]
    return u.clip(ZONA_UTIL)


# ---------------------------------------------------------------- menú principal (por paso)
def _ayuda_menu(estado: dict) -> list:
    from alpha_football.ui import menu as M
    paso = estado.get('menu_step', 'main')
    b = M.R_MENU_BOTONES
    if paso in ('select_country', 'amistoso_country'):
        amis = paso == 'amistoso_country'
        return [
            (_union(M.rects_paises()), "Países",
             "Elige el país " + ("del equipo del amistoso." if amis else "donde empezar tu carrera.")
             + " Flechas para moverte, Enter para elegir."),
            (M.R_INFO_PAIS, "Información", "Datos del país sobre el que está el mouse: ligas y nivel."),
            (M.R_VOLVER_ABAJO, "Volver", "Regresa al paso anterior (también ESC)."),
        ]
    if paso in ('select_division', 'amistoso_division'):
        d1, d2 = M.rects_division(paso == 'amistoso_division')
        return [
            (d1, "1ª División", "Liga principal del país: más nivel y presupuesto, pelea por copas. ↑ ↓ y Enter."),
            (d2, "2ª División", "Categoría de ascenso: plantillas más modestas; el objetivo es subir a 1ª."),
            (M.R_VOLVER_ABAJO, "Volver", "Regresa a la elección de país (también ESC)."),
        ]
    if paso == 'select_team':
        liga = estado.get('selected_liga_obj')
        n = len(getattr(liga, 'equipos', []) or []) or 2
        return [
            (_union(M.rects_equipos(n)), "Clubes", "Clic en un club para dirigirlo. Pasa el mouse para ver su ficha."),
            (M.R_INFO_CLUB, "Ficha del club", "Prestigio, media, presupuesto y estrellas del club señalado."),
            (M.R_EQUIPO_VOLVER, "Volver", "Regresa a la elección de división."),
        ]
    if paso == 'dt_setup':
        return [
            (M.R_DT_NOMBRE, "Nombre del DT", "Clic y escribe tu nombre. Mientras escribes, H escribe la letra."),
            (_union(M.rects_nacionalidades()), "Nacionalidad", "Elige una nacionalidad sugerida con un clic."),
            (M.R_DT_NAC_LIBRE, "Otra nacionalidad", "Clic y escribe cualquier otra nacionalidad."),
            (M.R_DT_CONFIRMAR, "Empezar carrera", "Con nombre y nacionalidad listos, pasa a firmar tu contrato."),
            (M.R_DT_VOLVER, "Volver", "Regresa a la elección de club."),
        ]
    if paso == 'load_slots':
        slots = M.rects_slots_carga()
        return [
            (_union(r for r, _d in slots), "Slots", "Clic en un slot ocupado para cargar esa partida."),
            (_union(d for _r, d in slots), "Borrar", "Borra la partida del slot (pide confirmación)."),
            (M.R_CARGA_VOLVER, "Volver", "Regresa al menú principal."),
        ]
    if paso == 'amistoso_teams':
        liga = estado.get('amistoso_liga')
        n = len(getattr(liga, 'equipos', []) or []) or 2
        return [
            (_union(M.rects_equipos(n, amistoso=True)), "Equipos",
             "Elige primero el local y luego el visitante del amistoso."),
            (M.R_AMIS_OTRO_PAIS, "Otro país", "Cambia de país sin perder el equipo ya elegido."),
            (M.R_AMIS_VOLVER, "Volver", "Regresa a la elección de división."),
        ]
    return [
        (b['nueva'], "Nueva partida", "Empieza una carrera: país, división, club y tu DT."),
        (b['cargar'], "Cargar partida", "Continúa una partida guardada en uno de los 5 slots."),
        (b['amistoso'], "Partido amistoso", "Juega un partido suelto entre dos equipos cualesquiera."),
        (b['editor'], "Modo edición", "Edita equipos, jugadores y nombres de ligas de la base de datos."),
        (b['opciones'], "Opciones", "Volumen, música y descargas de canciones."),
        (b['salir'], "Salir", "Cierra el juego."),
        (M.R_PANEL_DERECHO, "Panel informativo", "Ambientación y novedades del juego; no tiene acciones."),
    ]


AYUDA['menu'] = _ayuda_menu


# ---------------------------------------------------------------- hub (league_screen, por pestaña)
_TEXTO_TARJETA = {
    'team_screen': "Elige el once, el banco, la formación, el estilo y la mentalidad.",
    'plantilla_screen': "Lista de tus jugadores: ficha, orden por columnas, transferibles y renovaciones.",
    'cantera_screen': "Juveniles del club: se renuevan cada 6 meses. Súbelos al primer equipo o libéralos.",
    'calendario_screen': "Tus partidos de liga y copa con su fecha real. Dos partidos necesitan 3 días entre sí: si chocan, se reprograma uno.",   # v0.4.11.0
    'buscador_screen': "Busca jugadores de todas las ligas por nombre, posición y rangos, y negocia su fichaje.",
    'favoritos_screen': "Tu lista de jugadores seguidos: búscalos y negocia su fichaje cuando quieras.",
    'ofertas_screen': "Ofertas que otros clubes hacen por tus jugadores: acepta, rechaza o contraoferta.",
    'historial_pases_screen': "Todos los traspasos de la temporada en las ligas y los tuyos.",
    'ojeador_screen': "Tres fichajes recomendados por tu ojeador en cada ventana de pases.",
    'correo_screen': "Mensajes de la directiva, jugadores y otros clubes. El número rojo son los no leídos.",
    'notificaciones_screen': "Mensajes de jugadores y presidente a la izquierda; correo del club a la derecha. Últimos 5 de cada uno.",   # v0.4.10.0
    'noticias_screen': "Titulares vigentes: elige uno y lee su detalle. El punto dorado marca las no leídas.",   # v0.4.23.0
    'stats_screen': "Goleadores, asistidores, vallas invictas y mejores notas de la liga y tu equipo.",
    'copa_screen': "Tu copa internacional: fase de liga o grupos, llaves y estadísticas.",
    'career_screen': "Tus temporadas anteriores, títulos y récords como DT.",
    'otras_ligas_screen': "Tablas y resultados de las demás ligas y sus copas, en vivo.",
    'objetivos_screen': "Lo que exige la directiva esta temporada y su confianza en ti.",
    'contrato_dt_screen': "Tu sueldo, años de contrato, patrimonio y la renovación con el club.",
    'ofertas_dt_screen': "Clubes que te quieren como DT. El número rojo son las ofertas vigentes.",
    'finanzas_screen': "Ingresos, gastos, masa salarial y saldo del club.",
    'patrocinios_screen': "Tus 3 patrocinadores, sus objetivos y las ofertas para firmar, negociar o rechazar.",
    'contratos': "Salarios y vencimientos de tu plantilla ordenados por contrato, para renovar.",
}
_TEXTO_PESTANA = {
    'inicio': "Tablero principal: tabla, JUGAR, jornada y tu club.",
    'direccion': "Formación, plantilla y cantera.",
    'negociaciones': "Fichajes, ofertas recibidas, historial de pases y ojeador.",
    'oficina': "Notificaciones, noticias, estadísticas, copa, carrera, otras ligas, objetivos y tu contrato.",
    'finanzas': "Resumen económico, contratos y patrocinios.",
    'opciones': "Volumen, música y GUARDAR PARTIDA (tecla O desde cualquier pantalla).",
}


_NOMBRE_PESTANA = {'direccion': "Dirección de equipo", 'negociaciones': "Negociaciones", 'oficina': "Oficina",
                   'finanzas': "Finanzas"}


def _ayuda_hub(estado: dict) -> list:
    from alpha_football.ui import league_screen as L
    if estado.get('dialogo_salir'):
        return [
            (L.R_DIALOGO_SALIR, "¿Salir al menú?", "Confirma si quieres dejar la partida y volver al menú principal."),
            (L.R_SALIR_GUARDAR, "Guardar y salir", "Guarda en tu slot y vuelve al menú."),
            (L.R_SALIR_SIN, "Salir sin guardar", "Vuelve al menú perdiendo lo no guardado."),
            (L.R_SALIR_CANCELAR, "Cancelar", "Cierra este diálogo y sigue en el hub (también ESC)."),
        ]
    tab = estado.get('hub_tab') if estado.get('hub_tab') in L.PESTANAS else 'inicio'
    barra = L._rects_barra()
    its = []
    if tab == 'inicio':
        up, down = L.rects_historial()
        prev, nxt = L._rects_jornada()
        its += [
            (_union(barra), "Barra de menú", "Pestañas del hub: ← → para moverte, Enter para abrir. OPCIONES (tecla O) trae GUARDAR."),
            (L.R_SOBRE, "Correo", "El número rojo son los mensajes sin leer. Clic o tecla M para abrir el correo."),
            (L.R_TABLA, "Tabla", "Abre en NOTICIAS; las pestañas NOTICIAS / LIGA / COPA cambian el panel (LIGA: posiciones, tu club resaltado)."),
            (_union([L.rect_tab_tabla('liga'), L.rect_tab_tabla('copa')]), "LIGA / COPA",
             "Alterna entre la tabla de la liga y la de tu copa internacional. Si tu club no la juega, VER COPA te lleva a Otras ligas › Copas."),   # v0.4.26.0
            (L.rect_tab_tabla('noticias'), "NOTICIAS", "Las 3 más recientes primero; cada 5 s corren a las viejas y reinician al parar (N). Clic: ver."),
            (L.R_HIST, "Historial", "Tus partidos jugados. Rueda del mouse o ▲ ▼ para desplazarte."),
            (L.R_JUGAR, "JUGAR", "Juega el partido del día. Sin partido es CONTINUAR: los días pasan hasta tu partido, una oferta o un evento."),   # v0.4.14.1
            (L.R_DIA, "+1 DÍA", "Avanza un solo día (tecla D). Solo aparece cuando hoy no hay partido."),
            (L.R_HORA, "AVANZAR 1 HORA", "Solo el último día de fichajes: pasa una hora (Enter). El panel dice cuántas quedan."
                                          " Con 1 o 2 horas restantes, un fichaje o una venta se cierra igual en ese mismo mercado y el mercado se acaba."),   # v0.4.26.0
            (L.R_CERRAR, "CERRAR MERCADO", "Cierra el mercado antes de las 0 horas (tecla C); pide confirmación."),
            (R(L.R_JUGAR.x, L.Y_AVISOS, L.R_JUGAR.width, L.R_JORNADA.y - L.Y_AVISOS - 6), "Avisos",
             "Tu situación en la copa y alertas: lesiones, contratos, ofertas y correo."),
            (L.R_JORNADA, "Jornada", "Partidos de la jornada. < > cambian de fecha; R abre los resultados."),
            (_union([prev, nxt]), "< >", "Jornada anterior / siguiente en el panel."),
            (L.R_CLUB, "Tu club", "Forma, goleador, media, presupuesto, calificación DT y objetivo de la directiva."),
        ]
        return its
    rects = L._rects_tarjetas(len(L.TARJETAS.get(tab, [])))
    its.append((_union(barra), "Barra de menú",
                "Pestañas del hub: ← → para moverte, Enter para abrir. ESC vuelve a INICIO."))
    for i, clave in enumerate(k for k, *_ in L.BARRA_MENU):
        if clave == tab:
            its.append((barra[i], "Pestaña " + _NOMBRE_PESTANA.get(clave, clave.title()),
                        _TEXTO_PESTANA.get(clave, "Pestaña del hub.")))
    for (titulo, _sub, destino), r in zip(L.TARJETAS.get(tab, []), rects):
        its.append((r, (titulo[0] + titulo[1:].lower()).replace(" dt", " DT"), _TEXTO_TARJETA.get(destino, "Abre esta sección.")
                    + ("" if len(_TEXTO_TARJETA.get(destino, "")) > 80 else " ↑ ↓ y Enter.")))
    return its


AYUDA['league_screen'] = _ayuda_hub


# ---------------------------------------------------------------- historial de carrera
def _ayuda_carrera(estado: dict) -> list:
    from alpha_football.ui import career_screen as C
    return [
        (C.R_VOLVER, "Volver", "Regresa al hub (también ESC, Retroceso o Enter)."),
        (C.R_LOGROS, "Logros", "Hitos del DT: los obtenidos con su temporada y jornada, y los que faltan (tecla L)."),
        (C.R_TOTALES, "Totales", "Resumen de toda tu carrera: temporadas, títulos, puntos, goles y récord."),
        (C.R_BALON_ORO, "Premios", "Balón de Oro y Sudamericano del Año de cada temporada; en verde si es de tu club."),
        (C.R_TEMPORADAS, "Temporada por temporada", "Posición, puntos, goles y campeones de cada año. ↑ ↓ o rueda para desplazar."),
    ]


AYUDA['career_screen'] = _ayuda_carrera


# ---------------------------------------------------------------- opciones (principal / playlist)
def _ayuda_opciones(estado: dict) -> list:
    from alpha_football.ui import options_screen as O
    r = O.rects_opciones()
    if estado.get('opt_view') == 'playlist':
        return [
            (r['canciones'], "Canciones", "Pistas descargadas en la carpeta de música. BORRAR elimina la pista."),
            (_union([r['prev'], r['next']]), "Páginas", "Anterior / siguiente página de la playlist (también ← →)."),
            (r['volver'], "Volver", "Regresa a las opciones (también ESC)."),
        ]
    return [
        (r['volumen'], "Volumen", "Nivel de la música. ← → lo ajustan; también - y + en cualquier pantalla."),
        (_union([r['menos'], r['mute'], r['mas']]), "Botones de volumen", "Baja, silencia / restaura o sube el volumen 10%."),
        (r['input'], "Importar canción", "Pega (Ctrl+V) un enlace o escribe un nombre para buscar y descargar."),
        (r['descargar'], "Descargar", "Descarga el enlace o busca por nombre (también Enter en el campo)."),
        (r['resultados'], "Resultados", "Si buscaste por nombre, clic en un resultado para descargarlo."),
        (r['volver'], "Volver", "Regresa a la pantalla anterior (también ESC)."),
        (r['playlist'], "Ver playlist", "Lista de canciones descargadas, con opción de borrarlas."),
    ] + ([(r['guardar'], "Guardar", "Guarda la partida en uno de los 5 slots (solo en carrera).")]
         if 'guardar' in O.items_opciones(estado) else [])


AYUDA['options_screen'] = _ayuda_opciones


# ---------------------------------------------------------------- prepartido (menú / resultado instantáneo)
def _ayuda_prepartido(estado: dict) -> list:
    from alpha_football.ui import prepartido_screen as P
    res = estado.get('prepartido_resultado')
    if res:
        pen = res.get('penales') if isinstance(res, dict) else None
        r = P.rects_resultado(bool(pen and pen.get('secuencia')))
        its = [(r['marcador'], "Marcador", "Resultado final del partido simulado."),
               (r['goles'], "Goles", "Minuto, autor y equipo de cada gol.")]
        if 'penales' in r:
            its.append((r['penales'], "Penales", "Cobradores y secuencia de la tanda: verde = gol, cruz roja = falla."))
        its.append((r['continuar'], "Continuar", "Vuelve al hub (o a la copa) con el resultado ya registrado."))
        return its
    b = P.botones_menu()
    return [
        (P.R_CARTEL, "Enfrentamiento", "Local y visitante con su media, DT y avisos de cansancio o clásico."),
        (b[0][1], "Jugar en vivo", "Juega el partido minuto a minuto con cambios y táctica. Tecla 1."),
        (b[1][1], "Simular", "Resultado instantáneo sin ver el partido. Tecla 2."),
        (b[2][1], "Dirección de equipo", "Ajusta once, banco, formación y táctica antes de jugar. Tecla 3."),
        (b[3][1], "Once rival", "Mira la alineación probable del rival. Tecla 4."),
        (b[4][1], "Volver", "Regresa al hub sin jugar (también ESC). ↑ ↓ y Enter recorren los botones."),
    ]


AYUDA['prepartido_screen'] = _ayuda_prepartido


# ---------------------------------------------------------------- ofertas recibidas (con / sin contraoferta)
def _ayuda_ofertas(estado: dict) -> list:
    from alpha_football.ui import ofertas_screen as O
    ofertas = estado.get('ofertas_recibidas') or []
    cab = R(36, 72, 900, 30)
    if not ofertas:
        return [
            (cab, "Resumen", "Ofertas pendientes y presupuesto del club."),
            (O.R_VACIO, "Sin ofertas", "Cuando un club quiera a uno de tus jugadores, la oferta aparecerá aquí."),
            (O.R_VOLVER, "Volver", "Regresa al hub (también ESC o Enter)."),
        ]
    if estado.get('contra_abierta'):
        return [
            (O.R_PANEL, "Contraoferta", "Pide más dinero por el jugador. El club responde por correo en 1 a 3 días "
                                        "(el último día de fichajes, a las 3 horas)."),   # v0.4.26.0
            (O.R_MONTO, "Monto", "Escribe la cifra con los números; Retroceso borra el último dígito."),
            (_union([O.R_MAS5, O.R_MAS10, O.R_MAS25]), "+5% +10% +25%", "Sube el monto sobre la oferta original."),
            (O.R_ENVIAR, "Enviar", "Envía la contraoferta (también Enter). ESC la cancela."),
        ]
    n = min(len(ofertas), O.MAX_VISIBLES)
    return [
        (cab, "Resumen", "Ofertas pendientes y presupuesto del club."),
        (_union(O.rect_oferta(i) for i in range(n)), "Ofertas", "Clic o ↑ ↓ para elegir una oferta; ← → también mueven."),
        (O.R_FICHA, "Ficha del jugador", "Datos del jugador pedido y el club que lo quiere."),
        (O.R_ACEPTAR, "Aceptar", "Vende al jugador por el monto ofrecido (tecla A)."),
        (O.R_RECHAZAR, "Rechazar", "Rechaza la oferta y el jugador se queda (tecla R)."),
        (O.R_CONTRA, "Contraofertar", "Abre el panel para pedir más dinero al club comprador (tecla C)."),
        (O.R_VOLVER, "Volver", "Regresa al hub (también ESC)."),
    ]


AYUDA['ofertas_screen'] = _ayuda_ofertas


# ---------------------------------------------------------------- estadísticas
def _ayuda_stats(estado: dict) -> list:
    from alpha_football.ui import stats_screen as S
    return [
        (_union([S.R_ALCANCE_LIGA, S.R_ALCANCE_MI]), "Alcance", "Toda la liga o solo tu equipo (teclas L y T)."),
        (_union(S.rect_tab(i) for i in range(len(S.TABS))), "Pestañas",
         "Goleadores, asistencias, vallas invictas y mejores notas. ← → para cambiar."),
        (S.R_TABLA, "Ranking", "Los mejores de la categoría elegida: jugador, club, posición y partidos."),
        (S.R_VOLVER, "Volver", "Regresa al hub (también ESC)."),
    ]


AYUDA['stats_screen'] = _ayuda_stats


# ---------------------------------------------------------------- guardar partida
def _ayuda_guardar(estado: dict) -> list:
    from alpha_football.ui import save_slots_screen as G
    return [
        (_union(G.rect_slot(i) for i in range(5)), "Slots", "Clic o ↑ ↓ y Enter para guardar ahí. Supr borra el slot elegido."),
        (G.R_DETALLES, "Detalles", "DT, club, temporada, jornada y presupuesto guardados en cada slot."),
        (G.R_VOLVER, "Volver", "Regresa sin guardar (también ESC)."),
        (G.R_SALIR, "Salir al menú", "Deja la partida y vuelve al menú principal (sin guardar)."),
    ]


AYUDA['save_slots_screen'] = _ayuda_guardar


# ---------------------------------------------------------------- resumen de temporada
def _ayuda_resumen(estado: dict) -> list:
    from alpha_football.ui import resumen_temporada_screen as T
    return [
        (T.R_BANNER, "Campeón", "Campeón de la liga y tu posición final."),
        (T.R_CLASIFICACION, "Clasificación final", "Tabla final de tu liga: ascensos, copas y descensos en color."),
        (T.R_PREMIOS, "Premios", "Bota de oro, máximo asistente, guante de oro y MVP de la liga."),
        (T.R_BONO, "Bono", "Dinero que recibe el club por la posición en la liga y lo cobrado en la copa."),
        (T.R_AVANZAR, "Empezar temporada", "Cierra la temporada y arranca la siguiente (Enter o Espacio)."),
    ]


AYUDA['resumen_temporada_screen'] = _ayuda_resumen


# ---------------------------------------------------------------- editor (equipo / jugador / lista abierta)
def _ayuda_editor(estado: dict) -> list:
    from alpha_football.ui import edit_screen as E
    drop = estado.get('edit_dropdown_activo')
    if drop:
        ops = E._opciones_dropdown(drop, estado)
        nombre = {'estilo_dt': "estilo táctico", 'posicion': "posición", 'rasgo': "rasgo"}.get(
            drop, "rubro" if '_rubro_' in str(drop) else "patrocinador")     # v4.9.2: dropdowns de patrocinios
        return [
            (_union(r for _v, _t, r in ops), "Lista desplegada", f"Clic en un {nombre} para elegirlo."),
            (E.R_FORMULARIO, "Formulario", "Un clic fuera de la lista la cierra sin cambiar nada."),
            (E.R_APLICAR, "Aplicar y guardar", "Guarda la base editada en disco para las próximas partidas."),
        ]
    # v4.6.0: secciones ENTRENADORES / CLUBES / LIGAS / JUGADORES
    seccion = estado.get('edit_seccion', 'entrenadores')
    libres = estado.get('edit_liga_sel') == E.LIBRES
    its = [(_union(E.rect_seccion(i) for i in range(len(E.SECCIONES))), "Secciones",
            "Entrenadores, clubes, ligas o jugadores (Tab cambia de sección).")]
    if seccion == 'ligas':
        its += [(_union(E.rect_fila_lista(i) for i in range(10)), "Ligas", "Las 16 ligas (1ª y 2ª de cada país). ▲ ▼ desplazan."),
                (E.R_NOMBRE_LIGA, "Nombre", "Clic y escribe el nombre de la liga (máx. 40).")]
    else:
        its.append((_union(E.rect_tab_liga(i) for i in range(len(E.pestanas_editor()))), "País",
                    "País (ING, ESP...) o copa internacional (LIB, UCL) que se edita."))
        if seccion in ('entrenadores', 'jugadores'):
            its.append((_union([E.R_LIBRES, E.R_NUEVO]) if libres else E.R_LIBRES, "Libres",
                        "Los sin club: entran a tus carreras nuevas desde el inicio. + NUEVO crea uno; BORRAR lo quita."))
    if seccion == 'entrenadores':
        its += [(_union(E.rect_fila_lista(i) for i in range(10)), "Entrenadores", "El DT de cada club (o los libres)."),
                (E.R_DT_NOMBRE, "Nombre", "Vacío = el DT real del club."),
                (_union([E.R_DT_ESTILO, E.R_DT_CALIF]), "Estilo y calificación",
                 "Estilo táctico (también el del club) y calificación 1-99: define su sueldo.")]
    elif seccion == 'clubes':
        its += [(_union(E.rect_fila_lista(i) for i in range(10)), "Clubes", "Clic en un club para editarlo."),
                (_union([E.R_EQ_NOMBRE, E.R_EQ_PRESUPUESTO]), "Nombre y presupuesto",
                 "Clic y escribe; Enter confirma. Presupuesto en pesos enteros."),
                (_union([E.rect_patro_campo('camiseta', 'rubro'), E.rect_patro_campo('estadio', 'marca')]), "Patrocinios",   # v4.9.2
                 "Marcas con que el club arranca la 1ª temporada. Clic en rubro o marca abre la lista de su región.")]
    elif seccion == 'jugadores':
        if not libres:
            its += [(_union(E.rect_fila('equipos', i) for i in range(5)), "Clubes", "Clic en un club para ver su plantilla."),
                    (_union(E.rect_fila('jugadores', i) for i in range(5)), "Jugadores", "Clic en un jugador para editarlo.")]
        else:
            its.append((_union(E.rect_fila_lista(i) for i in range(10)), "Jugadores libres", "Clic en uno para editarlo."))
        ji = estado.get('edit_jugador_idx', -1)
        if isinstance(ji, int) and ji >= 0:
            its += [
                (_union([E.R_J_NOMBRE, E.R_J_APELLIDO]), "Nombre y apellido", "Clic y escribe; Enter confirma. Mientras escribes, H es una letra."),
                (_union([E.R_J_OVR, E.R_J_EDAD]), "OVR y edad", "Media (máx. 99) y edad del jugador; solo números."),
                (E.R_J_POSICION, "Posición", "Despliega la lista: POR, DEF, MED o DEL."),
                (_union([E.R_J_RASGO, E.R_J_POTENCIAL]), "Rasgo y potencial", "Rasgo especial del jugador y su techo de media (máx. 99)."),
            ]
    its += [
        (_union([E.R_ARCHIVO, E.R_EXPORTAR, E.R_IMPORTAR, E.R_RESTAURAR]), "Archivo y restaurar",
         "Exporta o importa la base en el JSON escrito. RESTAURAR BASE descarta todas las ediciones."),
        (_union([E.R_APLICAR, E.R_VOLVER]), "Aplicar / volver", "APLICAR guarda la base en disco; VOLVER regresa al menú."),
    ]
    return its


AYUDA['edit_screen'] = _ayuda_editor


# ---------------------------------------------------------------- ascensos y descensos
def _ayuda_promo(estado: dict) -> list:
    from alpha_football.ui import promo_releg_screen as P
    r = P.rects_promo()
    return [
        (r['cabecera'], "Tu resultado", "Si tu club subió, bajó o se mantiene, y el premio o castigo de media."),
        (_union([r['ascienden'], r['descienden']]), "Tu país", "Clubes que suben a 1ª y bajan a 2ª en tu país."),
        (r['paises'], "Todas las ligas", "Ascensos y descensos del resto de los países."),
        (r['retiros'], "Retiros", "Jugadores que se retiran (los de tu club primero) y el juvenil que los reemplaza."),
        (r['continuar'], "Continuar", "Sigue a la nueva temporada (Enter o ESC)."),
    ]


AYUDA['promo_releg_screen'] = _ayuda_promo


# ---------------------------------------------------------------- otras ligas (ligas / copas)
def _ayuda_otras_ligas(estado: dict) -> list:
    from alpha_football.ui import otras_ligas_screen as O
    if estado.get('otras_ligas_copas'):
        return [
            (O.rect_tab_copas(), "Ver ligas", "Vuelve a las tablas de las ligas (tecla C)."),
            (_union([O.rect_pais(0), O.rect_pais(1), O.rect_pais(2)]), "Copas", "Champions, Libertadores o Intercontinental; ↑ ↓ cambian. Debajo, cómo va cada una."),
            (O.R_PANEL, "Copa elegida", "Tabla de la fase de liga, grupos o llaves con global y penales. La Intercontinental muestra su final y el historial de campeones."),
            (O.R_VOLVER, "Volver", "Regresa al hub (también ESC)."),
        ]
    n = len(O.ligas_disponibles(estado)) // 2 or 8
    return [
        (O.rect_tab_copas(), "Copas", "Muestra cómo van Champions, Libertadores e Intercontinental (tecla C)."),
        (_union([O.rect_division(0), O.rect_division(1)]), "División", "1ª o 2ª división del país elegido (← →)."),
        (_union(O.rect_pais(i) for i in range(n)), "Países", "Clic o ↑ ↓ para ver la liga de otro país."),
        (O.R_PANEL, "Tabla y resultados", "Posiciones con cupos de copa y descenso, DT de cada club y últimos resultados."),
        (O.R_VOLVER, "Volver", "Regresa al hub (también ESC)."),
    ]


AYUDA['otras_ligas_screen'] = _ayuda_otras_ligas


# ---------------------------------------------------------------- plantilla
def _ayuda_plantilla(estado: dict) -> list:
    from alpha_football.ui import plantilla_screen as P
    r = P._rects()
    cab = _union(P.rect_columna(c) for c, _t, _x in P.COLUMNAS if c)
    return [
        (r['orden'], "Orden rápido", "Cicla el orden: posición, media, edad, valor y contrato (tecla S)."),
        (cab, "Encabezados", "Clic en una columna para ordenar por ella; otro clic invierte (flecha ▲ ▼)."),
        (R(P.R_LISTA.x + 8, P.FILA_Y0, P.R_LISTA.width - 16, P.FILAS_VISIBLES * P.FILA_H), "Jugadores",
         "Clic o ↑ ↓ para ver su ficha. Verde = titular; T transferible; LES lesionado; SAN sancionado."),
        (R(P.R_FICHA.x, P.R_FICHA.y, P.R_FICHA.width, r['renovar'].y - P.R_FICHA.y - 6), "Ficha",
         "Estado, media, potencial, valor, contrato, atributos y estadísticas del jugador elegido."
         " Forma: de PÉSIMA a IMPARABLE según sus últimas 5 notas; multiplica lo que sube de media y de potencial (×0.5 a ×2)."),
        # v0.4.26.0: forma, energía y moral (misma ficha)
        (R(P.R_FICHA.x, P.R_FICHA.y, P.R_FICHA.width, r['renovar'].y - P.R_FICHA.y - 6), "Forma imparable",
         "3 notas seguidas de 7.7 o más; dura 5 partidos (progresa el doble) y pasa a buena. Moral de 85 o más: "
         "progresa un 25 % más (tope ×3 en total)."),
        (R(P.R_FICHA.x, P.R_FICHA.y, P.R_FICHA.width, r['renovar'].y - P.R_FICHA.y - 6), "Energía",
         "Recupera una cantidad fija por día (≈ 30-35 por semana, según resistencia); un partido gasta ~29. "
         "Con partidos cada 3-4 días conviene rotar."),
        (R(P.R_FICHA.x, P.R_FICHA.y, P.R_FICHA.width, r['renovar'].y - P.R_FICHA.y - 6), "Moral",
         "Ganar después de 3 partidos sin ganar le sube +10 a toda la plantilla; un título, +25; pasar de fase en copa, +8."),
        (r['renovar'], "Renovar contrato", "Abre la negociación para extender su contrato (tecla R)."),
        (r['transferible'], "Transferible", "Lo pone en venta o lo quita (tecla T). Ponerlo baja su moral."),
        (r['lista_prestamo'], "Préstamo", "Pone al jugador en la lista de préstamo: los clubes te mandan ofertas de cesión (tecla P)."),
        (r['liberar'], "Liberar jugador", "Rescinde su contrato: pagas la mitad de los sueldos pendientes y queda como agente libre (tecla L, con confirmación)."),
        (r['prestamos'], "Préstamos", "Tus jugadores a préstamo y los cedidos, con CONCLUIR PRÉSTAMO."),
        (r['volver'], "Volver", "Regresa al hub (también ESC)."),
    ]


AYUDA['plantilla_screen'] = _ayuda_plantilla


# ---------------------------------------------------------------- buscador (normal / filtros abiertos)
def _ayuda_buscador(estado: dict) -> list:
    from alpha_football.ui import buscador_screen as B
    if estado.get('filtros_abierto'):
        campos = [B.rect_campo(c) for c in B.CAMPOS]
        pasos = [B._rect_paso(c, s) for c in B.CAMPOS for s in (-1, 1)]
        return [
            (_union(campos + pasos), "Rangos", "Mínimo y máximo de edad, media, potencial y precio. Escribe (Tab = siguiente) o usa - / +."),
            (_union([B.R_POS_F, B.R_LIGA_F]), "Posición y liga", "Clic para ciclar la posición y la liga del filtro."),
            (B.R_LIMPIAR, "Limpiar", "Vuelve todos los rangos a sus valores por defecto."),
            (B.R_APLICAR, "Aplicar", "Aplica los filtros y busca (Enter). ESC o clic fuera cierra sin aplicar."),
        ]
    r = B._rects()
    return [
        (r['nombre'], "Nombre", "Clic y escribe parte del nombre; Enter busca. Mientras escribes, H es una letra."),
        (_union([r['pos'], r['liga']]), "Posición y liga", "Clic para ciclar la posición y la liga donde buscar."),
        (_union([r['buscar'], r['limpiar']]), "Buscar / limpiar", "BUSCAR aplica los filtros; LIMPIAR los borra todos."),
        (B.R_FILTROS, "Filtros", "Abre los rangos de edad, media, potencial y precio."),
        (B.R_SOLO_LIBRES, "Solo agentes libres", "Muestra solo jugadores sin club (se fichan sin pagar traspaso)."),
        (_union(v for k, v in r.items() if k.startswith('orden_')) if (estado.get('busq') or {}).get('buscado')
         else R(16, 150, 800, 34), "Ordenar",
         "Tras BUSCAR aparecen los botones para ordenar; otro clic invierte el sentido."),
        (B.R_LISTA, "Resultados", "Jugadores que cumplen los filtros. Clic o ↑ ↓ para ver su ficha."),
        (R(B.R_FICHA.x, B.R_FICHA.y, B.R_FICHA.width, r['favorito'].y - B.R_FICHA.y - 6), "Ficha", "Datos, club y precio del jugador elegido."),
        (r['favorito'], "Favorito", "Agrega o quita al jugador de tu lista de FAVORITOS (en NEGOCIACIONES)."),
        (r['fichar'], "Negociar fichaje", "Abre la negociación con su club y luego con el jugador."),
        (r['prestamo'], "Préstamo", "Pide al jugador a préstamo por 6 meses o 1 año pagando un % del sueldo."),
        (r['volver'], "Volver", "Regresa al hub (también ESC)."),
    ]


AYUDA['buscador_screen'] = _ayuda_buscador


# ---------------------------------------------------------------- favoritos
def _ayuda_favoritos(estado: dict) -> list:
    from alpha_football.ui import favoritos_screen as FV
    from alpha_football.ui import buscador_screen as B
    r = B._rects()
    return [
        (FV.R_NOMBRE, "Buscar", "Clic y escribe parte del nombre para filtrar tus favoritos."),
        (FV.R_LISTA, "Favoritos", "Los jugadores que marcaste en NEGOCIAR. Clic o ↑ ↓ para ver su ficha."),
        (r['favorito'], "Quitar", "Lo saca de tu lista de favoritos (tecla Supr)."),
        (r['fichar'], "Negociar fichaje", "Abre la negociación con su club y luego con el jugador (Enter)."),
        (FV.R_VOLVER, "Volver", "Regresa al hub (también ESC)."),
    ]


AYUDA['favoritos_screen'] = _ayuda_favoritos


# ---------------------------------------------------------------- historial de pases
def _ayuda_historial_pases(estado: dict) -> list:
    from alpha_football.ui import historial_pases_screen as H
    r = H._rects()
    return [
        (_union([r['general'], r['propio']]), "Pestañas", "Todos los pases de las ligas o solo los de tu club (← → o Tab)."),
        (H.R_LISTA, "Pases", "Clic en un encabezado ordena por esa columna (otro clic invierte). ↑ ↓, RePág/AvPág o rueda."),
        (r['volver'], "Volver", "Regresa al hub (también ESC)."),
    ]


# ---------------------------------------------------------------- cantera (v4.8.0)
def _ayuda_cantera(estado: dict) -> list:
    from alpha_football.ui import cantera_screen as CS
    r = CS._rects()
    return [
        (CS.R_LISTA, "Canteranos", "Cada 6 meses llegan nuevos, algunos se van y el resto mejora. En dorado, la joya."),
        (CS.R_FICHA, "Ficha", "Datos del canterano elegido: media, potencial y atributos."),
        (r['subir'], "Subir", "Lo pasa al primer equipo con contrato nuevo (tecla S). Necesita cupo en la plantilla."),
        (r['liberar'], "Liberar", "Lo saca de la cantera; pide confirmación (tecla L, Enter confirma)."),
        (r['volver'], "Volver", "Regresa al hub (también ESC)."),
    ]


# ---------------------------------------------------------------- calendario (v0.4.11.0)
def _ayuda_calendario(estado: dict) -> list:
    from alpha_football.ui import calendario_screen as KS
    r = KS._rects()
    return [
        (KS.R_GRILLA, "Mes", "Clic en un día futuro simula hasta ahí. Franja verde: mercado abierto; rojo: cierre; dorado: hoy."),
        (r['prev'], "Mes anterior", "También con la flecha izquierda."),
        (r['next'], "Mes siguiente", "También con la flecha derecha."),
        (r['volver'], "Volver", "Regresa al hub (también ESC)."),
    ]


# ---------------------------------------------------------------- patrocinios (v4.9.0)
def _ayuda_patrocinios(estado: dict) -> list:
    from alpha_football.ui import patrocinios_screen as PS
    r = PS._rects()
    return [
        (r['reputacion'], "Reputación", "Sube al cumplir objetivos y baja al fallarlos, descender o rescindir. Mejora las ofertas."),
        (_union([PS._rect_espacio(i) for i in range(3)]), "Espacios",
         "Camiseta, manga y estadio: marca, fijo, bono, objetivo y años. ← → o clic para elegir."),
        (PS.R_OFERTAS, "Ofertas", "Firma (F), firma con prima (P), pide +10% o +20% (1, 2) o rechaza (R). Vencen con la ventana."),
        (r['volver'], "Volver", "Regresa al hub (también ESC)."),
    ]


# ---------------------------------------------------------------- ojeador
def _ayuda_ojeador(estado: dict) -> list:
    from alpha_football.ui import ojeador_screen as O
    # número de recomendaciones de la ventana (cacheadas en datos_carrera; recalcularlas cada frame es caro)
    n = len(((estado.get('datos_carrera') or {}).get('ojeador') or {}).get('recs') or []) or 3
    tarjetas, fichar = O._rects_tarjetas(n), O._rects_fichar(n)
    return [
        (R(12, 80, 760, 28), "Criterio", "El ojeador busca refuerzos para los puestos más flojos de tu once, dentro del presupuesto, "
                                         "y solo recomienda jugadores que se pueden comprar (no los recién llegados a su club "
                                         "ni los que están a préstamo)."),   # v0.4.26.0
        (_union(R(t.x, t.y, t.width, f.y - t.y - 6) for t, f in zip(tarjetas, fichar)), "Recomendados",
         "Hasta 3 jugadores con su club, precio y el motivo de la recomendación."),
        (_union(fichar), "Negociar", "Abre la negociación de fichaje del jugador de esa tarjeta."),
        (O._volver(), "Volver", "Regresa al hub (también ESC)."),
    ]


# ---------------------------------------------------------------- objetivos de la directiva
def _ayuda_objetivos(estado: dict) -> list:
    from alpha_football.ui import objetivos_screen as O
    if estado.get('objetivos_reglas_abierto'):     # v4.6.0
        return [(O.R_REGLAS, "Reglas", "Premio o multa según cómo termines, y qué cuenta como fallo. Clic o ESC cierra.")]
    return [      # v4.7.0: por secciones
        (O.R_TOP, "Directiva", "Confianza, calificación de DT y pedido activo de la directiva."),
        (O.R_LOCAL, "Local", "Meta de liga y cómo vas."),
        (O.R_AYUDA_META, "Reglas", "Qué pasa si superas, cumples o fallas (tecla I)."),
        (O.R_INTER, "Internacional", "Meta de copa y fase alcanzada (solo calificación)."),
        (O.R_FIN, "Finanzas", "Tope de masa salarial y saldo mínimo al cierre."),
        (O.R_MARCA, "Marca", "Meta de marca de la temporada: +4 / −3 de calificación."),
        (O.R_JUV, "Juveniles", "Meta de juveniles de la temporada: +4 / −3 de calificación."),
        (O._volver(), "Volver", "Regresa al hub (también ESC)."),
    ]


# ---------------------------------------------------------------- correo
def _ayuda_correo(estado: dict) -> list:
    from alpha_football.ui import correo_screen as C
    its = [
        (C.R_LISTA, "Bandeja", "Mensajes recibidos; los no leídos resaltados. Clic o ↑ ↓ para abrir uno."),
        (R(C.R_MSG.x, C.R_MSG.y, C.R_MSG.width, C._rect_accion().y - C.R_MSG.y - 6), "Mensaje",
         "Texto completo del mensaje elegido: directiva, jugadores u otros clubes."),
    ]
    try:                                   # el botón de acción solo existe si el mensaje elegido lo trae
        from alpha_football import correo as CO
        msgs = CO.bandeja(estado)
        m = msgs[max(0, min(int(estado.get('correo_sel', 0) or 0), len(msgs) - 1))] if msgs else {}
        if (m.get('accion') or {}).get('pantalla'):
            its.append((C._rect_accion(), "Acción", "Te lleva a lo que pide el mensaje (negociar, renovar, ofertas...). Enter."))
    except Exception:
        pass
    its.append((C._rect_accion(), "Decisiones", "Algunos mensajes piden decidir: clic o ← → y Enter. Sin responder, se deja pasar."))   # v0.4.10.0
    its.append((C.R_LISTA, "Forma de tus jugadores",      # v0.4.26.0
                "Los jugadores de tu club avisan al entrar en racha imparable y al terminarla (con lo que avanzaron)."))
    its.append((C._volver(), "Volver", "Regresa a NOTIFICACIONES (también ESC)."))
    return its


def _ayuda_notificaciones(estado: dict) -> list:     # v0.4.10.0
    from alpha_football.ui import notificaciones_screen as NS
    return [(NS.R_MENSAJES, "Mensajes", "Lo personal: lo que te escriben tus jugadores y el presidente."),
            (NS.R_CORREO, "Correo", "Lo institucional: directiva, secretaría, médicos, cantera, patrocinadores y prensa."),
            (NS.rect_todos(0), "Ver todos", "Abre la lista completa de ese lado. Clic en un mensaje lo abre directo."),
            (NS._volver(), "Volver", "Regresa al hub (también ESC).")]


def _ayuda_noticias(estado: dict) -> list:     # v0.4.23.0
    from alpha_football.ui import noticias_screen as NS
    return [(NS.R_LISTA, "Lista", "Noticias vigentes, las más recientes primero (mismo día: las importantes). Punto dorado = sin leer."),
            (NS.R_DETALLE, "Detalle", "Imagen, titular, fecha y cuerpo de la noticia elegida. Al verla queda leída."),
            (NS.R_ACCION, "Botón", "Algunas noticias traen un atajo (por ejemplo ver los remates): clic o Enter."),
            (NS._volver(), "Volver", "Regresa al hub (también ESC).")]


# ---------------------------------------------------------------- despido / fin de contrato
def _ayuda_despido(estado: dict) -> list:
    from alpha_football.ui import despido_screen as D
    pend = estado.get('despido_pendiente') or {}
    n = len(pend.get('opciones') or [])
    its = [(R(16, 20, 1248, 116), "Motivo", "Por qué terminó tu etapa en el club (despido o fin de contrato).")]
    if n:
        its.append((_union(D._rects_opciones(n)), "Ofertas de banquillo",
                    "Clubes que te quieren. Clic en una tarjeta para firmar allí tu nuevo contrato."))
    else:
        its.append((R(16, 212, 1248, 40), "Sin ofertas", "Nadie más te ofrece trabajo: clic en cualquier lado para seguir."))
    return its


AYUDA['historial_pases_screen'] = _ayuda_historial_pases
AYUDA['cantera_screen'] = _ayuda_cantera
AYUDA['calendario_screen'] = _ayuda_calendario
AYUDA['patrocinios_screen'] = _ayuda_patrocinios
AYUDA['ojeador_screen'] = _ayuda_ojeador
AYUDA['objetivos_screen'] = _ayuda_objetivos
AYUDA['correo_screen'] = _ayuda_correo
AYUDA['notificaciones_screen'] = _ayuda_notificaciones
AYUDA['noticias_screen'] = _ayuda_noticias
AYUDA['despido_screen'] = _ayuda_despido


# ---------------------------------------------------------------- finanzas
def _ayuda_finanzas(estado: dict) -> list:
    from alpha_football.ui import finanzas_screen as F
    if estado.get('espaldarazo_abierto'):      # v4.7.0: el espaldarazo vive en FINANZAS
        rs = F._rects_espaldarazo()
        return [
            (rs[0], "Nivel 1", "Más presupuesto a cambio de subir la meta 1 puesto (tecla 1)."),
            (rs[1], "Nivel 2", "Más dinero, meta 2 puestos más alta (tecla 2)."),
            (rs[2], "Nivel 3", "El mayor aporte, meta 3 puestos más alta (tecla 3). ESC cierra sin pedir."),
        ]
    return [
        (F.R_SALDO, "Saldo y valor", "Saldo, valor del club (plantilla + saldo), sus proyecciones y la masa salarial contra el tope."),
        (F.R_LIBRO, "Ingresos y gastos", "Taquilla, patrocinio y premios contra salarios y fichajes de la temporada."),
        (F.R_ESPALDARAZO, "Espaldarazo financiero", "Dinero ya a cambio de una meta más alta; la mitad se descuenta al cierre."
                                                      " También sube el tope de masa salarial en el mismo porcentaje."),   # v0.4.26.0
        (F.R_CAMISETAS, "Venta de camisetas",      # v0.4.26.0
         "Tu popularidad (0-100) sube fuerte cuando rindes por encima de la meta de la directiva y baja despacio. "
         "Da ingresos cada jornada y suma al valor del club."),
        (F._volver(), "Volver", "Regresa al hub (también ESC)."),
    ]


# ---------------------------------------------------------------- negociación (por etapa)
def _ayuda_negociacion(estado: dict) -> list:
    from alpha_football.ui import negociacion_screen as N
    r = N._rects()
    neg = estado.get('neg') or {}
    etapa = neg.get('etapa', 'club')
    renovar = neg.get('modo') == 'renovar' or neg.get('club') is None
    its = [(N.R_INFO, "Jugador", "Club, media, valor y contrato actual del jugador.")]
    if etapa == 'club' and not renovar:
        its += [
            (_union([r['monto_menos'], r['monto'], r['monto_mas']]), "Tu oferta",
             "Escribe la cifra con los números o usa − / + para ajustarla."),
            (r['ofertar'], "Ofertar", "Envía la oferta al club: puede aceptar, pedir más o rechazar."),
            (r['clausula'], "Pagar cláusula", "Pagas la cláusula de rescisión: el club no puede negarse."),
            (N.R_JUG, "Contrato", "Se habilita cuando cierres el acuerdo con el club."),
        ]
    elif etapa == 'jugador':
        its += [
            (N.R_CLUB, "Club", "Acuerdo con el club ya cerrado (o agente libre / renovación)."),
            (_union([r['sal_menos'], r['salario'], r['sal_mas']]), "Salario", "Sueldo anual que ofreces; en verde si llega a lo que pide."),
            (_union([r['anios_menos'], r['anios'], r['anios_mas']]), "Años", "Duración del contrato (con 32+ años, hasta 2)."),
            (r['clau_ciclo'], "Cláusula", "Cicla la cláusula ×1.5 / ×2 / ×3; más alta = pide más salario."),
            (r['proponer'], "Proponer contrato", "Envía la propuesta al jugador."),
        ]
    else:
        its += [(N.R_CLUB, "Club", "Resultado de la negociación con el club."),
                (N.R_JUG, "Contrato", "Resultado de la negociación con el jugador.")]
    its.append((r['volver'], "Cancelar / volver", "Sale de la negociación (también ESC). Abajo a la izquierda, la respuesta."))
    return its


# ---------------------------------------------------------------- contrato del DT (alta / renovación / ver)
def _ayuda_contrato_dt(estado: dict) -> list:
    from alpha_football.ui import contrato_dt_screen as C
    m = C.modo(estado)
    if m == 'ver':
        return [
            (R(16, 150, 1248, 190), "Tu contrato", "Sueldo anual, temporadas del contrato, patrimonio y estado de la renovación."),
            (R(16, 352, 1248, 230), "Clubes dirigidos", "Tus cambios de club a lo largo de la carrera."),
            (C.R_VOLVER, "Volver", "Regresa al hub (también ESC)."),
        ]
    rs = C._rects(3)
    its = [(R(16, 80, 1248, 34), "Club y calificación", "Club que te contrata y tu calificación de DT (sube el sueldo que ofrecen).")]
    its += [(rs[0], "1 año", "Más sueldo por temporada, menos estabilidad."),
            (rs[1], "2 años", "Opción equilibrada."),
            (rs[2], "3 años", "Más estabilidad, algo menos de sueldo. ← → y Enter, o clic en FIRMAR.")]
    if m == 'renovacion':
        its.append((C.R_RECHAZAR, "Rechazar", "No renuevas: dejarás el club al final de la temporada."))
    if m != 'alta':
        its.append((C.R_VOLVER, "Volver", "Decides más tarde (también ESC)."))
    return its


# ---------------------------------------------------------------- veredicto de la directiva
def _ayuda_veredicto(estado: dict) -> list:
    from alpha_football.ui import veredicto_screen as V
    seguir = (R(12, 652, 300, 36), "Continuar", "Enter, Espacio o clic para seguir.")
    if int(estado.get('veredicto_paso', 0) or 0) == 0:
        return [(V.R_CORREO, "Correo de la directiva", "Evaluación de tu temporada frente al objetivo que te pidieron."), seguir]
    return [(R(140, 190, 1000, 260), "Veredicto", "Posición final contra la meta, premio o multa, calificación y confianza."), seguir]


# ---------------------------------------------------------------- ofertas de banquillo
def _ayuda_ofertas_dt(estado: dict) -> list:
    from alpha_football.ui import ofertas_dt_screen as O
    try:
        from alpha_football import entrenadores as EN
        n = len(EN.ofertas_activas(estado)[:4])
    except Exception:
        n = 0
    if not n:
        return [
            (R(16, 110, 1000, 70), "Sin ofertas", "Si un club que va mal echa a su DT y tu calificación alcanza, te escribirá."),
            (R(16, 16, 700, 56), "Ofertas de banquillo", "Aquí aparecen los clubes que te quieren como DT; duran 3 jornadas."),
            (O.R_VOLVER, "Volver", "Regresa al hub (también ESC)."),
        ]
    return [
        (_union(O._fila(i) for i in range(n)), "Ofertas", "Club, liga, media, posición en la tabla y cuántas jornadas le quedan a la oferta."),
        (_union(O.rect_aceptar(i) for i in range(n)), "Aceptar", "Dejas tu club y firmas con el nuevo."),
        (_union(O.rect_rechazar(i) for i in range(n)), "Rechazar", "Descarta la oferta: contratan a otro."),
        (O.R_VOLVER, "Volver", "Regresa al hub (también ESC)."),
    ]


AYUDA['finanzas_screen'] = _ayuda_finanzas
AYUDA['negociacion_screen'] = _ayuda_negociacion
AYUDA['contrato_dt_screen'] = _ayuda_contrato_dt
AYUDA['veredicto_screen'] = _ayuda_veredicto
AYUDA['ofertas_dt_screen'] = _ayuda_ofertas_dt


# ---------------------------------------------------------------- gala de premios (v0.4.17.0)
def _ayuda_gala(estado: dict) -> list:
    from alpha_football.ui import gala_balon_screen as G
    return [
        (G.R_PREMIO, "Premio", "Qué premio se entrega, de qué temporada y la fecha de la gala."),
        (G.R_GANADOR, "Ganador", "El ganador con su club, su liga y sus números; en verde si juega en tu club."),
        (G.R_PODIO, "Podio", "Segundo y tercer puesto; en verde los de tu club."),
        (R(12, 652, 300, 36), "Continuar", "Enter, Espacio o clic para seguir."),
    ]


AYUDA['gala_balon_screen'] = _ayuda_gala


# ---------------------------------------------------------------- dirección de equipo (normal / en vivo / rival)
def _items_direccion(estado: dict, en_partido: bool) -> list:
    from alpha_football.ui import team_screen as T
    rc = T._rects_cabecera()
    its = [
        (rc['form_box'], "Formación", "Clic para elegir el dibujo táctico en la lista (también teclas [ y ])."),
        (rc['form_ayuda'], "Tácticas afines", "Las tácticas que encajan con esta formación: con una de ellas rindes un poco más."),
        (_union([rc['tact_prev'], rc['tact_box'], rc['tact_next']]), "Estilo", "Estilo de juego del DT (teclas - y =). La familiaridad sube jugándolo."),
        (_union([rc['ment_prev'], rc['ment_box'], rc['ment_next']]), "Mentalidad", "De autobús a todo o nada: más ataque = más goles a favor y en contra (, y .)."),
    ]
    if en_partido:
        its += [
            (rc['ok'], "Reanudar", "Vuelve al partido con los cambios hechos (Enter)."),
            (rc['cancel'], "Deshacer", "Revierte lo hecho desde que abriste la dirección (ESC)."),
            (T._CAMPO, "Campo", "Clic en un titular y luego en otro para cambiarlos de puesto."),
            (T._FICHA, "Ficha", "Datos y nota en vivo. Energía: verde bien, amarilla (<70) rinde menos, roja (<55) se cansa el doble."
                                " Forma: pésima/mala/normal/buena/imparable (por las últimas 5 notas); en el campo el jugador imparable titila en blanco."),   # v0.4.26.0
            (_union(T.rect_tarjeta_banco(n) for n in range(10)), "Banco",
             "Titular y luego suplente = cambio (máx. 5; el que sale no vuelve a entrar)."),
        ]
        return its
    its += [
        (rc['auto'], "Auto", "Arma el mejor once para la formación elegida (tecla A)."),
        (rc['ok'], "Confirmar", "Guarda la alineación y vuelve (Enter)."),
        (rc['cancel'], "Cancelar", "Descarta los cambios y vuelve (ESC)."),
        (T._CAMPO, "Campo", "Clic en un jugador y luego en otro para intercambiarlos (puesto o banco)."),
        (T._FICHA, "Ficha", "Atributos y estado. Energía: verde bien, amarilla (<70) rinde menos, roja (<55) se cansa el doble."
                            " Forma: pésima/mala/normal/buena/imparable (por las últimas 5 notas); en el campo el jugador imparable titila en blanco."),   # v0.4.26.0
        (_union(T.rect_tarjeta_banco(n) for n in range(10)), "Banco / reservas", "Los 10 convocados; con VER RESERVAS, el resto de la plantilla."),
        (T.R_BANCO_TOGGLE, "Ver reservas", "Alterna entre el banco y las reservas (tecla R); ◀ ▶ pasan de página."),
    ]
    return its


def _ayuda_team(estado: dict) -> list:
    from alpha_football.ui import team_screen as T
    obj = estado.get('team_equipo_objetivo')
    mi = estado.get('amis_local') if estado.get('team_contexto') == 'amistoso' else estado.get('mi_equipo')
    if obj is not None and obj is not mi:
        return [
            (T.R_VISOR_LISTA, "Plantilla rival", "Todos los jugadores del rival con posición y media (solo lectura)."),
            (T.R_VISOR_CAMPO, "Once probable", "Los 11 mejores del rival por posición en su formación."),
            (T.R_VISOR_VOLVER, "Volver a mi once", "Sale del visor y vuelve al prepartido."),
        ]
    return _items_direccion(estado, False)


AYUDA['team_screen'] = _ayuda_team


# ---------------------------------------------------------------- partido (vivo / descanso / penales / final)
def _ayuda_partido(estado: dict) -> list:
    from alpha_football.ui import match_screen as M
    sim = estado.get('sim_estado', 'jugando')
    if sim == 'medio_tiempo' or estado.get('sim_tactico_abierto'):
        return _items_direccion(estado, True)          # dirección en vivo (misma pantalla que DIRECCIÓN)
    if (sim == 'finalizado' and estado.get('sim_penales_sel') is not None
            and not estado.get('sim_penales_resuelto')):
        return [
            (R(M.R_PENALES.x, M.R_PENALES.y, M.R_PENALES.width, 90), "Definición por penales",
             "El partido terminó empatado y se define desde el punto penal."),
            (R(M.R_PENALES.x + 30, M.R_PENALES.y + 95, 580, M.FILAS_PENALES * 36 - 4), "Cobradores",
             "Ordenados por penales. Clic para elegir o quitar (máx. 5); el número es el orden de tiro."),
            (M.R_PENALES_DEFINIR, "Definir en penales", "Lanza la tanda con los cobradores elegidos."),
        ]
    if sim == 'finalizado':   # v4.1.0: post-partido
        from alpha_football.ui import postpartido as PP
        return [
            (_union([PP.R_TAB_CALIF, PP.R_TAB_TABLA, PP.R_TAB_RES]), "Pestañas",
             "← → cambian: notas, cómo queda tu liga o copa y los demás resultados de la fecha."),
            (PP.R_PANEL, "Detalle", "Nota de cada jugador con goles, asistencias, tarjetas, lesiones y cambios. ↑ ↓ desplazan."),
            (PP.R_CONTINUAR, "Continuar", "Vuelve al hub (también Enter)."),
        ]
    if estado.get('sim_cambio_forzado') is not None:
        return [(M.R_SELECTOR, "Cambio por lesión", "Se lesionó un jugador tuyo: elige quién entra (↑ ↓ + Enter o clic).")]
    its = [
        (M.R_MARCADOR, "Marcador", "Equipos, mentalidades, goles y minuto. Con esta ayuda abierta el reloj se detiene."),
        (M.R_TRANSMISION, "Transmisión", "Minuto a minuto. Goles, tarjetas y lesiones detienen el reloj un momento (Enter sigue)."),
        (M.R_VELOCIDAD, "Velocidad", "Cambia el ritmo del reloj: x1, x2 o x5 (tecla V)."),
    ]
    if estado.get('mi_equipo') is not None or estado.get('amis_local') is not None:
        its += [
            (M.R_TACTICA, "Táctica", "Pausa y abre la dirección en vivo: formación, estilo y hasta 5 cambios (tecla T)."),
            (M.R_RIVAL, "Rival", "Pausa y muestra al rival en cancha: formación, notas en vivo, goles y cambios (tecla R)."),
            (_union(M._rects_tira_mentalidad()), "Mentalidad", "Cambia la actitud al instante sin pausar (teclas 1 a 5)."),
        ]
    return its


AYUDA['match_screen'] = _ayuda_partido


# ---------------------------------------------------------------- copa internacional (por pestaña y tipo)
_TEXTO_CONTENIDO_COPA = {
    ('liga_grupos', 'champions'): "Tabla de la fase de liga de 36: verde 1-8 a octavos, azul 9-24 al playoff, gris eliminados.",
    ('liga_grupos', 'libertadores'): "Los 8 grupos de 4: pasan a octavos el 1º y el 2º de cada grupo.",
    ('llaves', 'champions'): "Cruces de eliminación directa con el global de ida y vuelta y los penales.",
    ('llaves', 'libertadores'): "Cruces de eliminación directa con el global de ida y vuelta y los penales.",
    ('estadisticas', 'champions'): "Goleadores, asistidores y vallas invictas de la copa; tu club resaltado.",
    ('estadisticas', 'libertadores'): "Goleadores, asistidores y vallas invictas de la copa; tu club resaltado.",
}


def _ayuda_copa(estado: dict) -> list:
    from alpha_football.ui import copa_screen as S
    tipo = estado.get('copa_vista') if estado.get('copa_vista') in ('champions', 'libertadores') else 'champions'
    pestana = estado.get('copa_pestana') if estado.get('copa_pestana') in S.PESTANAS else 'liga_grupos'
    its = [
        (R(36, 14, 850, 80), "Estado de la copa", "Fase en juego o campeón, y cómo va tu club."),
        (R(36, 14, 850, 80), "Copa Intercontinental",     # v0.4.26.0
         "En diciembre, una semana después de la final de la Libertadores, el campeón de la Libertadores juega contra "
         "el campeón de Europa a partido único (empate = penales). El campeón cobra 20 M€ y el finalista 6 M€. Si tu "
         "club la juega, aparece en tu calendario y se juega desde JUGAR."),
        (S.R_SELECTOR_COPA, "Champions / Libertadores", "Alterna la copa que ves (tecla C)."),
        (_union(S.rect_pestana(p) for p in S.PESTANAS), "Pestañas", "Fase de liga o grupos, llaves, partidos y estadísticas (1-4 o ← →)."),
    ]
    if pestana == 'partidos':
        its += [
            (_union([S.R_FECHA_ANT, S.R_FECHA_SIG]), "Fecha", "< > (o ← →) cambian la fecha: cada una se juega tras una jornada de liga."),
            (R(S.R_CONTENIDO.x, S.R_FECHA_ANT.bottom + 8, S.R_CONTENIDO.width, S.R_CONTENIDO.bottom - S.R_FECHA_ANT.bottom - 8),
             "Partidos", "Resultados de la fecha elegida (o los que faltan jugar); el tuyo resaltado."),
        ]
    else:
        its.append((S.R_CONTENIDO, {'liga_grupos': "Fase de liga" if tipo == 'champions' else "Grupos", 'llaves': "Llaves",
                                    'estadisticas': "Estadísticas"}[pestana],
                    _TEXTO_CONTENIDO_COPA.get((pestana, tipo), "Contenido de la copa.")))
    its.append((S.R_VOLVER, "Volver", "Regresa al hub (también ESC). Tu partido de copa se juega desde JUGAR."))
    return its          # v0.4.26.0: sin "Simular resto" (el botón ya no existe)


AYUDA['copa_screen'] = _ayuda_copa
