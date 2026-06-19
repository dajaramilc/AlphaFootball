# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla del Mercado de Pases (Pygame)
Muestra un grid de jugadores con cards, pestañas de filtrado, un historial lateral
y gestiona la compra de jugadores y ofertas de inicio de temporada de forma resiliente.
"""

import sys
import os
import random

# Intentar importar pygame de manera segura
try:
    import pygame
except ImportError as error_pygame:
    print(f"Error crítico al importar pygame en market_screen: {error_pygame}. El juego no podrá renderizar la UI.", file=sys.stderr)
    raise error_pygame

# Importación resiliente del tema visual
try:
    from alpha_football.ui.theme import (
        SCREEN_W,
        SCREEN_H,
        COLORS,
        get_font,
        draw_gradient_bg,
        draw_panel,
        draw_button,
        draw_text
    )
except Exception as error_import_theme:
    print(f"Advertencia: No se pudo importar alpha_football.ui.theme ({error_import_theme}). Usando fallback local.", file=sys.stderr)
    
    # Fallback local para garantizar la continuidad del sistema
    SCREEN_W = 1280
    SCREEN_H = 720
    COLORS = {
        'bg': '#0A0E1A',
        'verde': '#00FF88',
        'dorado': '#FFD700',
        'rojo': '#FF4444',
        'azul': '#00BFFF',
        'blanco': '#FFFFFF',
        'panel': '#141A2E'
    }
    
    def get_font(size):
        try:
            if size == 'sm': return pygame.font.SysFont("Arial", 16)
            elif size == 'md': return pygame.font.SysFont("Arial", 20)
            elif size == 'lg': return pygame.font.SysFont("Arial", 28)
            elif size == 'xl': return pygame.font.SysFont("Arial", 42)
        except Exception:
            pass
        return pygame.font.Font(None, 24)
        
    def draw_gradient_bg(screen):
        screen.fill((10, 14, 26)) # '#0A0E1A'
        
    def draw_panel(screen, rect):
        pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8) # '#141A2E'
        pygame.draw.rect(screen, (0, 191, 255), rect, width=1, border_radius=8)
        
    def draw_button(screen, rect, text, hover):
        color_bg = (0, 191, 255) if hover else (20, 26, 46)
        color_fg = (10, 14, 26) if hover else (255, 255, 255)
        pygame.draw.rect(screen, color_bg, rect, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), rect, width=1, border_radius=5)
        
        font = get_font('md')
        txt_surf = font.render(text, True, color_fg)
        txt_rect = txt_surf.get_rect(center=rect.center)
        screen.blit(txt_surf, txt_rect)
        return rect
        
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True):
        hex_color = COLORS.get(color, '#FFFFFF')
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        
        font = get_font(size)
        if shadow:
            shadow_surf = font.render(text, True, (0, 0, 0))
            screen.blit(shadow_surf, (pos[0] + 1, pos[1] + 1))
        txt_surf = font.render(text, True, (r, g, b))
        screen.blit(txt_surf, pos)

# Importaciones de lógica de mercado con fallback resiliente
try:
    from alpha_football.market import calcular_precio, calcular_valor
except Exception as error_market:
    print(f"Advertencia: No se pudo importar alpha_football.market ({error_market}). Usando fallback de precio local.", file=sys.stderr)
    def calcular_precio(jugador):
        try:
            return max(50000, (jugador.overall - 45) ** 2 * 3500)
        except Exception:
            return 75000
    def calcular_valor(jugador):
        try:
            return max(50000, (jugador.overall - 45) ** 2 * 2500)
        except Exception:
            return 50000

# v0.7: módulo de mercado para factibilidad y mercado internacional (resiliente).
try:
    from alpha_football import market as _market
except Exception:
    _market = None


def _puede_fichar(mi_equipo, jugador, precio):
    """Wrapper resiliente de market.puede_fichar (tope de nivel + plantilla 32 + dinero)."""
    if _market and hasattr(_market, 'puede_fichar'):
        try:
            return _market.puede_fichar(mi_equipo, jugador, precio)
        except Exception:
            pass
    # Fallback mínimo: solo dinero
    return (mi_equipo.balance >= precio, "OK" if mi_equipo.balance >= precio else "Sin fondos")

try:
    from alpha_football.data.free_agents import get_free_agents
except Exception as error_fa:
    print(f"Advertencia: No se pudo importar get_free_agents ({error_fa}). Usando fallback de agentes libres local.", file=sys.stderr)
    def get_free_agents(jornada):
        try:
            from alpha_football.models import Jugador
        except Exception:
            # Recrear clase Jugador local si falla totalmente la importación
            class Jugador:
                def __init__(self, nombre, apellido, posicion, ataque, defensa, fisico, tecnica, mental):
                    self.nombre = nombre
                    self.apellido = apellido
                    self.posicion = posicion
                    self.ataque = ataque
                    self.defensa = defensa
                    self.fisico = fisico
                    self.tecnica = tecnica
                    self.mental = mental
                    self.moral = 70
                    self.rasgo = None
                    self.lesion_partidos = 0
                @property
                def nombre_completo(self): return f"{self.nombre} {self.apellido}"
                @property
                def overall(self): return (self.ataque + self.defensa + self.fisico + self.tecnica + self.mental) // 5
        
        # Generar 3 libres decentes
        nombres = ["James", "Cuadrado", "Ospina", "Quintero", "Falcaito"]
        apellidos = ["Rodriguez", "Sanches", "Londono", "Ruiz", "Vargas"]
        posiciones = ["POR", "DEF", "MED", "DEL"]
        
        libres = []
        for i in range(3):
            pos = random.choice(posiciones)
            libres.append(Jugador(
                nombre=random.choice(nombres),
                apellido=random.choice(apellidos),
                posicion=pos,
                ataque=random.randint(62, 75),
                defensa=random.randint(62, 75),
                fisico=random.randint(62, 75),
                tecnica=random.randint(62, 75),
                mental=random.randint(62, 75)
            ))
        return libres

# Lógica local resiliente para generar jugadores en caso de venta (reemplazo)
def generar_reemplazo_resiliente(posicion, estrellas_equipo):
    try:
        from alpha_football.models import Jugador
    except Exception:
        class Jugador:
            def __init__(self, nombre, apellido, posicion, ataque, defensa, fisico, tecnica, mental):
                self.nombre = nombre
                self.apellido = apellido
                self.posicion = posicion
                self.ataque = ataque
                self.defensa = defensa
                self.fisico = fisico
                self.tecnica = tecnica
                self.mental = mental
                self.moral = 70
                self.rasgo = None
                self.lesion_partidos = 0
            @property
            def nombre_completo(self): return f"{self.nombre} {self.apellido}"
            @property
            def overall(self): return (self.ataque + self.defensa + self.fisico + self.tecnica + self.mental) // 5

    nombres_pool = ["Andres", "Brayan", "Mateo", "Santiago", "Jhon", "Luis", "Carlos"]
    apellidos_pool = ["Mendoza", "Mosquera", "Valencia", "Riascos", "Zapata", "Moreno"]
    
    lo = int(40 + estrellas_equipo * 5)
    hi = min(lo + 20, 76)
    
    return Jugador(
        nombre=random.choice(nombres_pool),
        apellido=random.choice(apellidos_pool),
        posicion=posicion,
        ataque=random.randint(lo, hi),
        defensa=random.randint(lo, hi),
        fisico=random.randint(lo, hi),
        tecnica=random.randint(lo, hi),
        mental=random.randint(lo, hi)
    )


def self_box(screen, rect, text, active):
    """Dibuja un input box con borde neón. Helper de mercado (v0.8.2)."""
    try:
        pygame.draw.rect(screen, (10, 14, 26) if active else (20, 26, 46), rect, border_radius=4)
        pygame.draw.rect(screen, (0, 255, 136) if active else (0, 191, 255), rect, width=1, border_radius=4)
    except Exception:
        pass
    display = text or ''
    draw_text(screen, display, (rect.x + 6, rect.y + 6), size='sm', color='blanco')
    if active:
        # Cursor parpadeante al final del texto
        try:
            font = get_font('sm')
            w = font.size(display)[0]
            cursor_x = rect.x + 6 + w + 2
            cursor_y = rect.y + 5
            pygame.draw.line(screen, (0, 255, 136), (cursor_x, cursor_y), (cursor_x, cursor_y + 16), 2)
        except Exception:
            pass


def _cargar_equipos_por_tipo(tipo: str, estado: dict) -> list:
    """
    v0.8.4: carga resiliente de los equipos de una liga por su `tipo` (betplay, laliga,
    premier, brasil, argentina). Sirve al filtro "Por país" del mercado, que permite fichar
    entre ligas. Lee primero de estado['ligas'] (si existe) y, si no, cae a los módulos de
    datos. Devuelve [] ante cualquier fallo para no romper el render del mercado.
    """
    # 1. Intentar desde estado['ligas'] (si una sesión lo pobló).
    try:
        for l in estado.get('ligas', []) or []:
            l_tipo = l.get('tipo') if isinstance(l, dict) else getattr(l, 'tipo', None)
            if l_tipo == tipo:
                eqs = l.get('equipos', []) if isinstance(l, dict) else getattr(l, 'equipos', [])
                return list(eqs or [])
    except Exception as e:
        print(f"Error leyendo estado['ligas'] para tipo '{tipo}': {e}", file=sys.stderr)
    # 2. Fallback: cargar la liga desde su módulo de datos.
    try:
        from alpha_football.data import premier, laliga, betplay, brasil, argentina
        mapa = {
            'premier': premier, 'laliga': laliga, 'betplay': betplay,
            'brasil': brasil, 'argentina': argentina,
        }
        mod = mapa.get(tipo)
        if mod is not None:
            return list(mod.get_liga().equipos)
    except Exception as e:
        print(f"Error cargando liga '{tipo}' desde datos: {e}", file=sys.stderr)
    return []


def render(screen, estado: dict) -> str | None:
    """
    Renderiza la pantalla del mercado de pases y gestiona las interacciones.
    Retorna "volver" cuando el usuario desea salir, o None si continúa en pantalla.
    """
    try:
        # 1. Asegurar estado persistente de la pantalla
        mi_equipo = estado.get('mi_equipo')
        equipos = estado.get('equipos', [])
        liga = estado.get('liga')
        jornada = estado.get('jornada_actual', 1)
        
        # Verificar disponibilidad del mercado (abierto solo primeras 3 y últimas 3 jornadas)
        jornada_actual = getattr(liga, "jornada_actual", 1) if liga else 1
        num_jornadas = getattr(liga, "num_jornadas", 10) if liga else 10
        mercado_abierto = (jornada_actual <= 3) or (jornada_actual > num_jornadas - 3)
        
        if not mercado_abierto:
            # Renderizar pantalla de mercado cerrado
            draw_gradient_bg(screen)
            font_title = get_font('xl')
            title_surf = font_title.render("MERCADO CERRADO", True, COLORS['rojo'])
            title_rect = title_surf.get_rect(center=(SCREEN_W // 2, 180))
            screen.blit(title_surf, title_rect)
            
            panel_rect = pygame.Rect(SCREEN_W // 2 - 300, 260, 600, 220)
            draw_panel(screen, panel_rect)
            
            draw_text(screen, "El mercado de fichajes solo abre durante:", (SCREEN_W // 2 - 250, 290), size='md', color='blanco')
            draw_text(screen, "• Las primeras 3 jornadas de la temporada (Jor. 1-3)", (SCREEN_W // 2 - 250, 340), size='sm', color='azul')
            draw_text(screen, f"• Las últimas 3 jornadas de la temporada (Jor. {num_jornadas-2}-{num_jornadas})", (SCREEN_W // 2 - 250, 385), size='sm', color='azul')
            draw_text(screen, f"Jornada actual de tu liga: {jornada_actual} / {num_jornadas}", (SCREEN_W // 2 - 250, 430), size='sm', color='dorado')
            
            back_rect = pygame.Rect(SCREEN_W // 2 - 150, 520, 300, 60)
            back_hover = back_rect.collidepoint(pygame.mouse.get_pos())
            draw_button(screen, back_rect, "VOLVER A LIGA", back_hover)
            
            click_pos = None
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    click_pos = event.pos
                    
            if click_pos and back_rect.collidepoint(click_pos):
                return "volver"
                
            return None
        
        # Inicializar variables locales en el diccionario global para persistencia
        estado.setdefault('market_tab', 'Todos')
        estado.setdefault('market_page', 0)
        estado.setdefault('fichajes_realizados', 0)
        estado.setdefault('transfer_log', [])
        estado.setdefault('success_message', "")
        estado.setdefault('success_timer', 0)

        # v0.8.1: resetear historial de transferencias y contador de fichajes cuando
        # el usuario entra a una ventana DIFERENTE de la última que vio. Esto evita
        # que el log se acumule indefinidamente y que el contador quede pegado.
        try:
            if mercado_abierto:
                if jornada_actual <= 3:
                    ventana_id = f"T{estado.get('temporada', 1)}_J1-3"
                else:
                    ventana_id = f"T{estado.get('temporada', 1)}_J{num_jornadas-2}-{num_jornadas}"
                ultima = estado.get('ultima_ventana_mercado_id')
                if ultima != ventana_id:
                    estado['transfer_log'] = []
                    estado['fichajes_realizados'] = 0
                    estado['ultima_ventana_mercado_id'] = ventana_id
            else:
                # Mercado cerrado: no tocar nada; si reabre, el bloque de arriba
                # detectará el cambio de ventana y resetea.
                pass
        except Exception as e_win:
            print(f"Error al resetear ventana de transferencias: {e_win}", file=sys.stderr)
        
        # Oferta de inicio de temporada (se dispara la primera vez que se entra en esta ventana de pases)
        estado.setdefault('oferta_inicio_creada', False)
        estado.setdefault('oferta_inicio_pendiente', False)
        estado.setdefault('oferta_inicio_estrella', None)
        estado.setdefault('oferta_inicio_monto', 0)
        estado.setdefault('oferta_inicio_comprador', None)

        # Fase 4: buzón de ofertas recurrentes de la IA por jugadores propios (15%/jornada)
        estado.setdefault('ofertas_recibidas', [])
        
        # Inicializar oferta de inicio de temporada si es el primer fichaje disponible
        if not estado['oferta_inicio_creada'] and estado['fichajes_realizados'] == 0 and mi_equipo and len(mi_equipo.jugadores) > 0:
            try:
                estrella = mi_equipo.jugador_estrella
                # 1.05 a 1.35 veces su valor
                monto = int(calcular_precio(estrella) * random.uniform(1.05, 1.35))
                # Elegir un comprador rival
                rivales = [e for e in equipos if e.nombre != mi_equipo.nombre]
                if rivales:
                    comprador = random.choice(rivales)
                    # v0.7.1: las ofertas NO se muestran en el mercado; van a la sección Ofertas.
                    estado.setdefault('ofertas_recibidas', []).append(
                        {'jugador': estrella, 'comprador': comprador, 'monto': monto})
                estado['oferta_inicio_creada'] = True
            except Exception as e_oferta:
                print(f"Error al generar oferta inicial: {e_oferta}", file=sys.stderr)
                estado['oferta_inicio_creada'] = True

        # Modal de confirmación de compra
        estado.setdefault('show_confirm_modal', False)
        estado.setdefault('selected_player_to_buy', None)
        estado.setdefault('selected_player_club', None)

        # Dibujar fondo base
        draw_gradient_bg(screen)
        
        # Obtener lista de jugadores del mercado según la pestaña activa
        todos_jugadores = []  # Lista de tuplas: (Jugador, Club_Origen)
        
        tab = estado['market_tab']
        
        if tab == 'Libres':
            # Obtener agentes libres correspondientes a esta jornada
            # Si no están cargados en el estado, los generamos y guardamos
            if 'free_agents_list' not in estado:
                try:
                    estado['free_agents_list'] = get_free_agents(jornada)
                except Exception:
                    estado['free_agents_list'] = []

            for j in estado.get('free_agents_list', []):
                todos_jugadores.append((j, None))
        elif tab == 'Internacional':
            # v0.7: jugadores de ligas más fuertes. Se pueden OJEAR aunque no alcance la plata.
            if _market and hasattr(_market, 'pool_internacional'):
                try:
                    for j, club, _tipo in _market.pool_internacional(estado):
                        todos_jugadores.append((j, club))
                except Exception as e_intl:
                    print(f"Error al cargar mercado internacional: {e_intl}", file=sys.stderr)
        else:
            # v0.8.2: el filtro de país se aplica por SEPARADO (botón "Por país" arriba),
            # no en las pestañas superiores. Las pestañas ahora son solo por posición.
            _PAIS_A_TIPO = {
                'Colombia': 'betplay',
                'España': 'laliga',
                'Inglaterra': 'premier',
                'Brasil': 'brasil',
                'Argentina': 'argentina',
            }
            pais_tipo = _PAIS_A_TIPO.get(estado.get('market_pais_filtro') or 'Todos')

            # v0.8.4: el filtro "Por país" ahora habilita fichajes ENTRE LIGAS.
            # Antes filtraba estado['equipos'] (solo TU liga) por eq.tipo/eq.liga_tipo (atributos
            # que Equipo no tiene) con fallback a estado['ligas'] (nunca poblado) -> lista vacía.
            # Ahora: si eliges un país distinto al de tu liga, cargamos los equipos de ESA liga
            # (cacheados por sesión para que la baja al fichar persista visualmente).
            liga_usuario_tipo = getattr(estado.get('liga'), 'tipo', None)
            if pais_tipo and pais_tipo != liga_usuario_tipo:
                cache = estado.setdefault('_market_ligas_cache', {})
                if pais_tipo not in cache:
                    cache[pais_tipo] = _cargar_equipos_por_tipo(pais_tipo, estado)
                equipos_fuente = cache[pais_tipo]
            else:
                # País 'Todos' o el de tu propia liga: usar los equipos persistentes del estado.
                equipos_fuente = equipos

            # Jugadores de otros clubes
            for eq in equipos_fuente:
                if mi_equipo and getattr(eq, 'nombre', None) == mi_equipo.nombre:
                    continue
                for j in getattr(eq, 'jugadores', []):
                    # Aplicar filtros por posición
                    if tab in ('Todos', 'POR', 'DEF', 'MED', 'DEL'):
                        if tab == 'Todos' or j.posicion == tab:
                            todos_jugadores.append((j, eq))

            # Ordenar por overall de mayor a menor
            todos_jugadores.sort(key=lambda item: item[0].overall, reverse=True)

        # v0.8.2: aplicar filtros del panel FILTROS (precio / OVR / nombre).
        try:
            prec_min = int(estado.get('market_precio_min', 0) or 0)
            prec_max = int(estado.get('market_precio_max', 0) or 0)
            ovr_min = int(estado.get('market_ovr_min', 0) or 0)
            ovr_max = int(estado.get('market_ovr_max', 0) or 0)
            search_name = (estado.get('market_nombre_search') or '').strip().lower()
            hay_filtros = (prec_min > 0 or prec_max > 0 or ovr_min > 0 or ovr_max > 0 or len(search_name) >= 2)
            if hay_filtros:
                # v0.8.2: búsqueda por nombre con similitud semántica (difflib.SequenceMatcher).
                # ratio > 0.5 = tolerante: "yimmi" encuentra "Yimmi Chatarra" y similares.
                if search_name and len(search_name) >= 2:
                    try:
                        from difflib import SequenceMatcher
                    except Exception:
                        SequenceMatcher = None
                else:
                    SequenceMatcher = None
                filtrados = []
                for j, eq in todos_jugadores:
                    try:
                        prec = calcular_precio(j)
                        ovr = getattr(j, 'overall', 0)
                    except Exception:
                        continue
                    if prec_min > 0 and prec < prec_min:
                        continue
                    if prec_max > 0 and prec > prec_max:
                        continue
                    if ovr_min > 0 and ovr < ovr_min:
                        continue
                    if ovr_max > 0 and ovr > ovr_max:
                        continue
                    if SequenceMatcher is not None and search_name:
                        try:
                            nombre_norm = (getattr(j, 'nombre_completo', '') or '').lower()
                            ratio = SequenceMatcher(None, search_name, nombre_norm).ratio()
                            # Si la palabra aparece como substring, también pasa (mejor UX)
                            if ratio <= 0.5 and search_name not in nombre_norm:
                                continue
                        except Exception:
                            pass
                    filtrados.append((j, eq))
                todos_jugadores = filtrados
        except Exception as e_filtros:
            print(f"Error al aplicar filtros de precio/OVR: {e_filtros}", file=sys.stderr)
            
        # Paginación
        items_por_pagina = 6
        total_paginas = max(1, (len(todos_jugadores) + items_por_pagina - 1) // items_por_pagina)
        
        # Evitar índice de página fuera de rango tras cambiar de pestaña
        if estado['market_page'] >= total_paginas:
            estado['market_page'] = 0
            
        page = estado['market_page']
        start_idx = page * items_por_pagina
        end_idx = min(start_idx + items_por_pagina, len(todos_jugadores))
        jugadores_pagina = todos_jugadores[start_idx:end_idx]

        # 2. Dibujar Encabezado Superior
        draw_text(screen, "MERCADO DE PASES", (40, 20), size='xl', color='dorado')
        draw_text(screen, f"DT: {estado.get('dt_nombre', 'Mister')}  |  Club: {mi_equipo.nombre}", (40, 65), size='sm', color='azul')
        
        # 3. Dibujar Panel de Información del Usuario
        info_rect = pygame.Rect(840, 20, 400, 110)
        draw_panel(screen, info_rect)
        draw_text(screen, "TU PRESUPUESTO:", (860, 35), size='sm', color='blanco')
        draw_text(screen, f"${mi_equipo.balance:,}", (860, 55), size='lg', color='verde')
        draw_text(screen, f"Fichajes de esta ventana: {estado['fichajes_realizados']}", (860, 95), size='sm', color='dorado')

        # 4. Dibujar Pestañas de Filtrado (v0.8.2: solo posición/tab, NO país — país va aparte)
        tab_names = ['Todos', 'POR', 'DEF', 'MED', 'DEL', 'Libres', 'Internacional']
        tab_rects = {}
        tab_x = 40
        tab_y = 100
        tab_w = 110
        tab_h = 32

        mouse_pos = pygame.mouse.get_pos()

        for name in tab_names:
            rect = pygame.Rect(tab_x, tab_y, tab_w, tab_h)
            tab_rects[name] = rect

            # Dibujar pestaña activa con otro estilo
            is_active = (name == tab)
            is_hover = rect.collidepoint(mouse_pos)

            color_bg = (0, 191, 255) if is_active else ((20, 26, 46) if is_hover else (10, 14, 26))
            color_border = (255, 215, 0) if is_active else (0, 191, 255)
            color_txt = 'bg' if is_active else 'blanco'

            pygame.draw.rect(screen, color_bg, rect, border_radius=5)
            pygame.draw.rect(screen, color_border, rect, width=1, border_radius=5)

            # Centrar texto en pestaña
            font = get_font('md')
            txt_surf = font.render(name, True, COLORS.get(color_txt, (255, 255, 255)))
            txt_rect = txt_surf.get_rect(center=rect.center)
            screen.blit(txt_surf, txt_rect)

            tab_x += tab_w + 10

        # 4b. v0.8.2: botón "Por país: X" (dropdown) + botón "FILTROS" — a la derecha de las pestañas.
        pais_actual = estado.get('market_pais_filtro') or 'Todos'
        pais_btn = pygame.Rect(tab_x, tab_y, 200, tab_h)
        is_hover_pais = pais_btn.collidepoint(mouse_pos)
        is_dropdown_open = bool(estado.get('market_pais_dropdown_open'))
        try:
            pygame.draw.rect(screen, (40, 60, 90) if is_dropdown_open else ((30, 45, 75) if is_hover_pais else (20, 26, 46)), pais_btn, border_radius=5)
            pygame.draw.rect(screen, (255, 215, 0) if is_dropdown_open else (0, 191, 255), pais_btn, width=1, border_radius=5)
        except Exception:
            pass
        draw_text(screen, f"País: {pais_actual} ▼", (pais_btn.x + 12, pais_btn.y + 7), size='sm', color='blanco')

        # Indicador de filtros activos (puntito verde) si hay alguno
        hay_filtros_activos = (
            (estado.get('market_precio_min', 0) or 0) > 0
            or (estado.get('market_precio_max', 0) or 0) > 0
            or (estado.get('market_ovr_min', 0) or 0) > 0
            or (estado.get('market_ovr_max', 0) or 0) > 0
            or (estado.get('market_nombre_search') or '').strip()
        )
        filtros_btn = pygame.Rect(tab_x + 210, tab_y, 130, tab_h)
        is_hover_filtros = filtros_btn.collidepoint(mouse_pos)
        is_filtros_open = bool(estado.get('market_filtros_open'))
        try:
            pygame.draw.rect(screen, (50, 80, 50) if is_filtros_open else ((30, 45, 75) if is_hover_filtros else (20, 26, 46)), filtros_btn, border_radius=5)
            pygame.draw.rect(screen, (255, 215, 0) if is_filtros_open else (0, 191, 255), filtros_btn, width=1, border_radius=5)
        except Exception:
            pass
        draw_text(screen, f"FILTROS{' •' if hay_filtros_activos else ''}", (filtros_btn.x + 12, filtros_btn.y + 7), size='sm', color='verde' if hay_filtros_activos else 'blanco')

        # 5. Dibujar Grid de Jugadores Disponibles (Cards)
        card_w, card_h = 370, 130
        card_spacing_x, card_spacing_y = 20, 12
        grid_start_x, grid_start_y = 40, 150
        
        card_rects = [] # Almacenar tuples (Rect, Jugador, Club)
        
        for i, (j, eq) in enumerate(jugadores_pagina):
            row = i // 2
            col = i % 2
            
            x = grid_start_x + col * (card_w + card_spacing_x)
            y = grid_start_y + row * (card_h + card_spacing_y)
            rect = pygame.Rect(x, y, card_w, card_h)
            
            # Dibujar card
            draw_panel(screen, rect)
            
            # Nombre y Posición
            pos_tag = f"[{j.posicion}]"
            nombre_completo = j.nombre_completo
            nombre_trunc = nombre_completo[:18] + ".." if len(nombre_completo) > 18 else nombre_completo
            draw_text(screen, nombre_trunc, (x + 15, y + 15), size='md', color='blanco')
            draw_text(screen, pos_tag, (x + 15, y + 35), size='sm', color='azul')
            
            # Atributos OVR
            draw_text(screen, f"OVR: {j.overall}", (x + 15, y + 60), size='md', color='dorado')
            draw_text(screen, f"Moral: {j.moral}%", (x + 15, y + 80), size='sm', color='blanco')
            
            if j.rasgo:
                draw_text(screen, f"Rasgo: {j.rasgo}", (x + 15, y + 100), size='sm', color='dorado')
            
            # Club de origen
            club_txt = eq.nombre if eq else "Libre (Agente Libre)"
            club_recortado = club_txt[:20] + "..." if len(club_txt) > 20 else club_txt
            draw_text(screen, club_recortado, (x + 180, y + 15), size='sm', color='blanco')
            
            # Precio
            precio = calcular_precio(j)
            draw_text(screen, f"${precio:,}", (x + 180, y + 38), size='md', color='verde')
            
            # Botón "Fichar" (v0.8.1: sin límite por ventana — tope = nivel + dinero + plantilla 32).
            btn_rect = pygame.Rect(x + 240, y + 85, 110, 35)
            ok, motivo = _puede_fichar(mi_equipo, j, precio)
            btn_hover = btn_rect.collidepoint(mouse_pos)

            if ok:
                draw_button(screen, btn_rect, "FICHAR", btn_hover)
            else:
                pygame.draw.rect(screen, (50, 20, 20), btn_rect, border_radius=5)
                if 'Nivel' in motivo:
                    etiqueta, col = "NIVEL", COLORS['rojo']
                elif 'llena' in motivo.lower():
                    etiqueta, col = "LLENA", COLORS['rojo']
                else:
                    etiqueta, col = "AHORRA", COLORS['dorado']
                font = get_font('sm')
                txt = font.render(etiqueta, True, col)
                screen.blit(txt, txt.get_rect(center=btn_rect.center))

            # Registrar el botón siempre para capturar clics y dar retroalimentación
            card_rects.append((btn_rect, j, eq, ok, motivo))

        # 6. Dibujar Controles de Paginación
        pag_rect_prev = pygame.Rect(40, 630, 100, 35)
        pag_rect_next = pygame.Rect(680, 630, 100, 35)
        
        prev_hover = pag_rect_prev.collidepoint(mouse_pos)
        next_hover = pag_rect_next.collidepoint(mouse_pos)
        
        if page > 0:
            draw_button(screen, pag_rect_prev, "Anterior", prev_hover)
        if page < total_paginas - 1:
            draw_button(screen, pag_rect_next, "Siguiente", next_hover)
            
        draw_text(screen, f"Página {page+1} de {total_paginas}", (350, 638), size='md', color='blanco')

        # 7. Dibujar Panel Lateral: Historial y Logs de Fichajes
        hist_rect = pygame.Rect(840, 145, 400, 430)
        draw_panel(screen, hist_rect)
        draw_text(screen, "HISTORIAL DE ESTA VENTANA", (860, 160), size='md', color='azul')
        
        # Línea divisoria
        pygame.draw.line(screen, (0, 191, 255), (860, 185), (1220, 185), 1)
        
        # Renderizar logs de fichajes (últimos 8 movimientos)
        logs = estado['transfer_log']
        log_y = 200
        if not logs:
            draw_text(screen, "No hay transferencias registradas.", (860, log_y), size='sm', color='blanco')
        else:
            for log_msg in logs[-8:]:
                # Truncar textos largos si es necesario
                msg_recortado = log_msg[:42] + "..." if len(log_msg) > 42 else log_msg
                draw_text(screen, f"• {msg_recortado}", (860, log_y), size='sm', color='verde')
                log_y += 28

        # 8. Dibujar Botón de Salida en la parte inferior derecha
        exit_rect = pygame.Rect(840, 595, 400, 70)
        exit_hover = exit_rect.collidepoint(mouse_pos)
        draw_button(screen, exit_rect, "CERRAR MERCADO Y CONTINUAR", exit_hover)

        # 9. Temporizador de Mensaje de Éxito / Alerta
        if estado.get('success_message'):
            banner_rect = pygame.Rect(40, 610, 760, 50)
            msg = estado['success_message']
            is_error = any(kw in msg.lower() for kw in ["llena", "superior", "insuficiente", "límite", "limite", "debes vender"])
            bg_color = (80, 20, 20) if is_error else (20, 80, 40)
            text_color = 'rojo' if is_error else 'verde'
            pygame.draw.rect(screen, bg_color, banner_rect, border_radius=5)
            draw_text(screen, msg, (60, 623), size='md', color=text_color)

            estado['success_timer'] -= 1
            if estado['success_timer'] <= 0:
                estado['success_message'] = ""

        # 9b. v0.8.2: dropdown "Por país" — opciones debajo del botón
        if estado.get('market_pais_dropdown_open'):
            dd_items = ['Todos', 'Colombia', 'España', 'Inglaterra', 'Brasil', 'Argentina']
            dd_x = pais_btn.x
            dd_y = pais_btn.bottom + 2
            item_h = 26
            for i, nombre in enumerate(dd_items):
                item_rect = pygame.Rect(dd_x, dd_y + i * item_h, pais_btn.width, item_h)
                is_active = (nombre == (estado.get('market_pais_filtro') or 'Todos'))
                is_hover_item = item_rect.collidepoint(mouse_pos)
                try:
                    pygame.draw.rect(screen, (40, 80, 110) if is_active else ((30, 45, 75) if is_hover_item else (20, 26, 46)), item_rect, border_radius=3)
                    pygame.draw.rect(screen, (0, 255, 136) if is_active else (0, 191, 255), item_rect, width=1, border_radius=3)
                except Exception:
                    pass
                draw_text(screen, nombre, (item_rect.x + 10, item_rect.y + 5), size='sm',
                          color='verde' if is_active else 'blanco')

        # 9c. v0.8.2: panel FILTROS (overlay flotante)
        if estado.get('market_filtros_open'):
            panel_x, panel_y, panel_w, panel_h = 360, 145, 460, 290
            panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
            # Sombra semitransparente
            try:
                sombra = pygame.Surface((panel_w + 12, panel_h + 12), pygame.SRCALPHA)
                sombra.fill((0, 0, 0, 130))
                screen.blit(sombra, (panel_x - 6, panel_y - 6))
            except Exception:
                pass
            draw_panel(screen, panel_rect)
            try:
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), panel_rect, width=2, border_radius=8)
            except Exception:
                pass
            # Título
            draw_text(screen, "FILTROS", (panel_x + 20, panel_y + 15), size='lg', color='dorado')
            draw_text(screen, "(clic en un campo para escribir)", (panel_x + 120, panel_y + 22), size='sm', color='azul')

            # Labels y campos
            in_prec_min = pygame.Rect(panel_x + 160, panel_y + 60, 100, 28)
            in_prec_max = pygame.Rect(panel_x + 290, panel_y + 60, 100, 28)
            in_ovr_min = pygame.Rect(panel_x + 160, panel_y + 110, 60, 28)
            in_ovr_max = pygame.Rect(panel_x + 250, panel_y + 110, 60, 28)
            in_nombre = pygame.Rect(panel_x + 160, panel_y + 160, 270, 28)

            draw_text(screen, "Precio mín $:", (panel_x + 20, panel_y + 67), size='sm', color='blanco')
            self_box(screen, in_prec_min, str(estado.get('market_precio_min', 0) or 0) or '0',
                     estado.get('market_filter_input') == 'precio_min')
            draw_text(screen, "Precio máx $:", (panel_x + 270, panel_y + 67), size='sm', color='blanco')
            self_box(screen, in_prec_max, str(estado.get('market_precio_max', 0) or 0) or '0',
                     estado.get('market_filter_input') == 'precio_max')

            draw_text(screen, "OVR mín:", (panel_x + 20, panel_y + 117), size='sm', color='blanco')
            self_box(screen, in_ovr_min, str(estado.get('market_ovr_min', 0) or 0) or '0',
                     estado.get('market_filter_input') == 'ovr_min')
            draw_text(screen, "OVR máx:", (panel_x + 230, panel_y + 117), size='sm', color='blanco')
            self_box(screen, in_ovr_max, str(estado.get('market_ovr_max', 0) or 0) or '0',
                     estado.get('market_filter_input') == 'ovr_max')

            draw_text(screen, "Nombre:", (panel_x + 20, panel_y + 167), size='sm', color='blanco')
            self_box(screen, in_nombre, estado.get('market_nombre_search', '') or '',
                     estado.get('market_filter_input') == 'nombre')
            draw_text(screen, "(similitud)", (panel_x + 320, panel_y + 167), size='sm', color='azul')

            # Botones LIMPIAR y CERRAR
            btn_limpiar = pygame.Rect(panel_x + 60, panel_y + 215, 140, 40)
            btn_cerrar = pygame.Rect(panel_x + 270, panel_y + 215, 140, 40)
            draw_button(screen, btn_limpiar, "LIMPIAR", btn_limpiar.collidepoint(mouse_pos))
            draw_button(screen, btn_cerrar, "APLICAR Y CERRAR", btn_cerrar.collidepoint(mouse_pos))

        # 10. Dibujar Modal de Oferta Inicial (si está activa)
        if estado['oferta_inicio_pendiente']:
            estrella = estado['oferta_inicio_estrella']
            monto = estado['oferta_inicio_monto']
            comprador = estado['oferta_inicio_comprador']
            
            # Capa de oscurecimiento
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((10, 14, 26, 220)) # Transparencia oscura
            screen.blit(overlay, (0, 0))
            
            # Panel de Modal
            modal_rect = pygame.Rect(SCREEN_W // 2 - 250, SCREEN_H // 2 - 160, 500, 320)
            draw_panel(screen, modal_rect)
            
            # Contenido del Modal
            draw_text(screen, "¡OFERTA DE TRANSFERENCIA!", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 130), size='lg', color='dorado')
            draw_text(screen, f"El club {comprador.nombre} ofrece:", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 80), size='sm', color='blanco')
            draw_text(screen, f"${monto:,}", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 50), size='lg', color='verde')
            draw_text(screen, f"por {estrella.nombre_completo}", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 10), size='md', color='blanco')
            draw_text(screen, f"Pos: {estrella.posicion}  |  OVR: {estrella.overall}", (SCREEN_W // 2 - 210, SCREEN_H // 2 + 15), size='sm', color='azul')
            
            # Botones del Modal
            btn_acc_rect = pygame.Rect(SCREEN_W // 2 - 210, SCREEN_H // 2 + 65, 190, 45)
            btn_rej_rect = pygame.Rect(SCREEN_W // 2 + 20, SCREEN_H // 2 + 65, 190, 45)
            
            acc_hover = btn_acc_rect.collidepoint(mouse_pos)
            rej_hover = btn_rej_rect.collidepoint(mouse_pos)
            
            draw_button(screen, btn_acc_rect, "ACEPTAR OFERTA", acc_hover)
            draw_button(screen, btn_rej_rect, "RECHAZAR OFERTA", rej_hover)

        # 10b. (v0.7.1) Buzón retirado del mercado: las ofertas se gestionan en la sección Ofertas.
        elif False:
            of = estado['ofertas_recibidas'][0]
            jug = of.get('jugador'); comp = of.get('comprador'); monto = of.get('monto', 0)

            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((10, 14, 26, 220))
            screen.blit(overlay, (0, 0))

            modal_rect = pygame.Rect(SCREEN_W // 2 - 250, SCREEN_H // 2 - 170, 500, 340)
            draw_panel(screen, modal_rect)

            draw_text(screen, "BUZON DE OFERTAS", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 145), size='lg', color='dorado')
            draw_text(screen, f"Pendientes: {len(estado['ofertas_recibidas'])}", (SCREEN_W // 2 + 70, SCREEN_H // 2 - 140), size='sm', color='azul')
            if jug and comp:
                draw_text(screen, f"{comp.nombre[:24]} ofrece:", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 90), size='sm', color='blanco')
                draw_text(screen, f"${monto:,}", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 60), size='lg', color='verde')
                draw_text(screen, f"por {jug.nombre_completo}", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 20), size='md', color='blanco')
                draw_text(screen, f"Pos: {jug.posicion}  |  OVR: {jug.overall}  |  Valor: ${(getattr(jug,'valor',0) or calcular_valor(jug)):,}", (SCREEN_W // 2 - 210, SCREEN_H // 2 + 5), size='sm', color='azul')

            btn_acc_rect = pygame.Rect(SCREEN_W // 2 - 210, SCREEN_H // 2 + 70, 190, 45)
            btn_rej_rect = pygame.Rect(SCREEN_W // 2 + 20, SCREEN_H // 2 + 70, 190, 45)
            draw_button(screen, btn_acc_rect, "ACEPTAR", btn_acc_rect.collidepoint(mouse_pos))
            draw_button(screen, btn_rej_rect, "RECHAZAR", btn_rej_rect.collidepoint(mouse_pos))

        # 11. Dibujar Modal de Confirmación de Compra (si está activa)
        elif estado['show_confirm_modal']:
            j_buy = estado['selected_player_to_buy']
            eq_orig = estado['selected_player_club']
            precio = calcular_precio(j_buy)
            
            # Capa de oscurecimiento
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((10, 14, 26, 220))
            screen.blit(overlay, (0, 0))
            
            # Panel de Modal
            modal_rect = pygame.Rect(SCREEN_W // 2 - 250, SCREEN_H // 2 - 140, 500, 280)
            draw_panel(screen, modal_rect)
            
            # Contenido
            draw_text(screen, "¿CONFIRMAR FICHAJE?", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 110), size='lg', color='dorado')
            draw_text(screen, f"¿Deseas contratar a {j_buy.nombre_completo}?", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 60), size='sm', color='blanco')
            draw_text(screen, f"Costo de transferencia: ${precio:,}", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 35), size='md', color='verde')
            draw_text(screen, f"Estadísticas del jugador: OVR {j_buy.overall} [{j_buy.posicion}]", (SCREEN_W // 2 - 210, SCREEN_H // 2 - 10), size='sm', color='azul')
            
            # Botones
            btn_yes_rect = pygame.Rect(SCREEN_W // 2 - 210, SCREEN_H // 2 + 40, 190, 45)
            btn_no_rect = pygame.Rect(SCREEN_W // 2 + 20, SCREEN_H // 2 + 40, 190, 45)
            
            yes_hover = btn_yes_rect.collidepoint(mouse_pos)
            no_hover = btn_no_rect.collidepoint(mouse_pos)
            
            draw_button(screen, btn_yes_rect, "CONFIRMAR", yes_hover)
            draw_button(screen, btn_no_rect, "CANCELAR", no_hover)

        # 12. Capturar Eventos del Usuario de forma resiliente
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            elif event.type == pygame.KEYDOWN:
                # v0.8.2: entrada de teclado para los inputs de filtro (precio/OVR/nombre).
                if estado.get('market_filter_input'):
                    fname = estado['market_filter_input']
                    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        estado['market_filter_input'] = None
                    elif event.key == pygame.K_BACKSPACE:
                        if fname == 'nombre':
                            actual = estado.get('market_nombre_search') or ''
                            estado['market_nombre_search'] = actual[:-1]
                        else:
                            actual = str(estado.get(f'market_{fname}', 0) or 0)
                            nuevo = int(actual[:-1]) if actual[:-1] else 0
                            estado[f'market_{fname}'] = nuevo
                    elif event.key == pygame.K_ESCAPE:
                        estado['market_filter_input'] = None
                    else:
                        ch = event.unicode
                        if fname == 'nombre':
                            # Búsqueda por nombre: aceptar letras, números, espacios, acentos
                            if ch and (ch.isalnum() or ch in ' .-\'_áéíóúñÁÉÍÓÚÑüÜ'):
                                actual = estado.get('market_nombre_search') or ''
                                if len(actual) < 30:
                                    estado['market_nombre_search'] = actual + ch
                        else:
                            if ch and ch.isdigit():
                                actual = str(estado.get(f'market_{fname}', 0) or 0)
                                if len(actual) < 12:
                                    nuevo = int(actual + ch) if actual != '0' else int(ch)
                                    estado[f'market_{fname}'] = nuevo
                    continue  # Consumir el evento para no procesarlo como click

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # A. Manejar interacciones del Modal de Oferta Inicial
                if estado['oferta_inicio_pendiente']:
                    btn_acc_rect = pygame.Rect(SCREEN_W // 2 - 210, SCREEN_H // 2 + 65, 190, 45)
                    btn_rej_rect = pygame.Rect(SCREEN_W // 2 + 20, SCREEN_H // 2 + 65, 190, 45)
                    
                    if btn_acc_rect.collidepoint(event.pos):
                        # Aceptar venta de estrella
                        estrella = estado['oferta_inicio_estrella']
                        monto = estado['oferta_inicio_monto']
                        comprador = estado['oferta_inicio_comprador']
                        
                        try:
                            # Aumentar balance
                            mi_equipo.balance += monto
                            # Remover de mi equipo
                            mi_equipo.jugadores.remove(estrella)
                            # Añadir a equipo comprador
                            comprador.jugadores.append(estrella)

                            # v0.8.2: solo generar suplente si la plantilla cae por debajo de 15.
                            # Antes siempre se rellenaba, manteniendo la plantilla al tope artificialmente.
                            suplente = None
                            if len(mi_equipo.jugadores) < 15:
                                suplente = generar_reemplazo_resiliente(estrella.posicion, mi_equipo.estrellas)
                                mi_equipo.jugadores.append(suplente)

                            estado['transfer_log'].append(f"Venta: {estrella.nombre_completo} -> {comprador.nombre} por ${monto:,}")
                            if suplente is not None:
                                estado['success_message'] = f"Vendido {estrella.nombre_completo}. Llega {suplente.nombre_completo} de reemplazo."
                            else:
                                estado['success_message'] = f"Vendido {estrella.nombre_completo}. Plantilla en {len(mi_equipo.jugadores)} jugadores."
                            estado['success_timer'] = 200
                        except Exception as e_action:
                            print(f"Error procesando aceptación de oferta: {e_action}", file=sys.stderr)

                        estado['oferta_inicio_pendiente'] = False
                        
                    elif btn_rej_rect.collidepoint(event.pos):
                        # Rechazar venta
                        estrella = estado['oferta_inicio_estrella']
                        estado['transfer_log'].append(f"Rechazado: Oferta por {estrella.nombre_completo} declinada.")
                        estado['oferta_inicio_pendiente'] = False
                    continue # Salir del frame para evitar clics duplicados bajo el modal

                # A2. (v0.7.1) Buzón retirado del mercado: las ofertas se gestionan en la sección Ofertas.
                elif False:
                    btn_acc_rect = pygame.Rect(SCREEN_W // 2 - 210, SCREEN_H // 2 + 70, 190, 45)
                    btn_rej_rect = pygame.Rect(SCREEN_W // 2 + 20, SCREEN_H // 2 + 70, 190, 45)
                    if btn_acc_rect.collidepoint(event.pos):
                        of = estado['ofertas_recibidas'].pop(0)
                        jug = of.get('jugador'); comp = of.get('comprador'); monto = of.get('monto', 0)
                        try:
                            mi_equipo.balance += monto
                            if jug in mi_equipo.jugadores:
                                mi_equipo.jugadores.remove(jug)
                            comp.jugadores.append(jug)
                            try:
                                comp.balance = max(0, comp.balance - monto)
                            except Exception:
                                pass
                            # v0.8.2: solo generar suplente si la plantilla cae por debajo de 15.
                            suplente = None
                            if len(mi_equipo.jugadores) < 15:
                                suplente = generar_reemplazo_resiliente(jug.posicion, mi_equipo.estrellas)
                                mi_equipo.jugadores.append(suplente)
                            estado['transfer_log'].append(f"Venta: {jug.nombre_completo} -> {comp.nombre} por ${monto:,}")
                            if suplente is not None:
                                estado['success_message'] = f"Vendiste a {jug.nombre_completo} por ${monto:,}. Llega {suplente.nombre_completo}."
                            else:
                                estado['success_message'] = f"Vendiste a {jug.nombre_completo} por ${monto:,}. Plantilla en {len(mi_equipo.jugadores)} jugadores."
                            estado['success_timer'] = 200
                        except Exception as e_acc:
                            print(f"Error al aceptar oferta del buzon: {e_acc}", file=sys.stderr)
                    elif btn_rej_rect.collidepoint(event.pos):
                        of = estado['ofertas_recibidas'].pop(0)
                        try:
                            estado['transfer_log'].append(f"Rechazada: oferta por {of['jugador'].nombre_completo}.")
                        except Exception:
                            pass
                    continue

                # B. Manejar interacciones del Modal de Confirmación de Compra
                elif estado['show_confirm_modal']:
                    btn_yes_rect = pygame.Rect(SCREEN_W // 2 - 210, SCREEN_H // 2 + 40, 190, 45)
                    btn_no_rect = pygame.Rect(SCREEN_W // 2 + 20, SCREEN_H // 2 + 40, 190, 45)
                    
                    if btn_yes_rect.collidepoint(event.pos):
                        j_buy = estado['selected_player_to_buy']
                        eq_orig = estado['selected_player_club']
                        es_intl = estado.get('selected_player_intl', False)
                        precio = calcular_precio(j_buy)

                        # Revalidar factibilidad (tope de nivel + plantilla 32 + dinero).
                        ok, motivo = _puede_fichar(mi_equipo, j_buy, precio)
                        if not ok:
                            estado['success_message'] = motivo
                            estado['success_timer'] = 200
                        else:
                            try:
                                mi_equipo.balance -= precio
                                if es_intl:
                                    # Internacional: quitar del pool cacheado (no es un club activo).
                                    pool = estado.get('_pool_internacional', [])
                                    estado['_pool_internacional'] = [
                                        (jj, cc, tt) for (jj, cc, tt) in pool if jj is not j_buy
                                    ]
                                elif eq_orig:
                                    if j_buy in eq_orig.jugadores:
                                        eq_orig.jugadores.remove(j_buy)
                                elif 'free_agents_list' in estado and j_buy in estado['free_agents_list']:
                                    estado['free_agents_list'].remove(j_buy)

                                # Añadir a mi equipo (hasta 32; el tope ya lo validó puede_fichar).
                                mi_equipo.jugadores.append(j_buy)
                                estado['fichajes_realizados'] += 1

                                club_nombre = eq_orig.nombre if eq_orig else "Libre"
                                estado['transfer_log'].append(f"Compra: {j_buy.nombre_completo} de {club_nombre} por ${precio:,}")
                                estado['success_message'] = f"¡Fichaje exitoso de {j_buy.nombre_completo}!"
                                estado['success_timer'] = 180
                            except Exception as e_compra:
                                print(f"Error procesando compra de jugador: {e_compra}", file=sys.stderr)

                        estado['show_confirm_modal'] = False
                        estado['selected_player_to_buy'] = None
                        estado['selected_player_club'] = None
                        estado['selected_player_intl'] = False
                        
                    elif btn_no_rect.collidepoint(event.pos):
                        estado['show_confirm_modal'] = False
                        estado['selected_player_to_buy'] = None
                        estado['selected_player_club'] = None
                    continue

                # C. Manejar pestañas (Tabs)
                for name, rect in tab_rects.items():
                    if rect.collidepoint(event.pos):
                        estado['market_tab'] = name
                        estado['market_page'] = 0 # Reiniciar página al cambiar filtro

                # C2. v0.8.2: botón "Por país" — abre/cierra el dropdown.
                if pais_btn.collidepoint(event.pos):
                    estado['market_pais_dropdown_open'] = not estado.get('market_pais_dropdown_open', False)
                    # Si abrimos país, cerramos filtros
                    if estado['market_pais_dropdown_open']:
                        estado['market_filtros_open'] = False
                elif estado.get('market_pais_dropdown_open'):
                    # Click dentro del dropdown pero fuera del botón = seleccionar opción
                    dd_items = ['Todos', 'Colombia', 'España', 'Inglaterra', 'Brasil', 'Argentina']
                    dd_x = pais_btn.x
                    dd_y = pais_btn.bottom + 2
                    item_h = 26
                    for i, nombre in enumerate(dd_items):
                        item_rect = pygame.Rect(dd_x, dd_y + i * item_h, pais_btn.width, item_h)
                        if item_rect.collidepoint(event.pos):
                            estado['market_pais_filtro'] = nombre
                            estado['market_pais_dropdown_open'] = False
                            estado['market_page'] = 0

                # C3. v0.8.2: botón FILTROS — abre/cierra el panel de filtros.
                if filtros_btn.collidepoint(event.pos):
                    estado['market_filtros_open'] = not estado.get('market_filtros_open', False)
                    if estado['market_filtros_open']:
                        estado['market_pais_dropdown_open'] = False
                elif estado.get('market_filtros_open'):
                    # Click dentro del panel de filtros
                    panel_x, panel_y, panel_w, panel_h = 360, 145, 460, 290
                    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
                    if panel_rect.collidepoint(event.pos):
                        # Detectar sobre qué input se hizo click
                        in_prec_min = pygame.Rect(panel_x + 160, panel_y + 60, 100, 28)
                        in_prec_max = pygame.Rect(panel_x + 290, panel_y + 60, 100, 28)
                        in_ovr_min = pygame.Rect(panel_x + 160, panel_y + 110, 60, 28)
                        in_ovr_max = pygame.Rect(panel_x + 250, panel_y + 110, 60, 28)
                        in_nombre = pygame.Rect(panel_x + 160, panel_y + 160, 270, 28)
                        btn_limpiar = pygame.Rect(panel_x + 60, panel_y + 215, 140, 40)
                        btn_cerrar = pygame.Rect(panel_x + 270, panel_y + 215, 140, 40)
                        if in_prec_min.collidepoint(event.pos):
                            estado['market_filter_input'] = 'precio_min'
                        elif in_prec_max.collidepoint(event.pos):
                            estado['market_filter_input'] = 'precio_max'
                        elif in_ovr_min.collidepoint(event.pos):
                            estado['market_filter_input'] = 'ovr_min'
                        elif in_ovr_max.collidepoint(event.pos):
                            estado['market_filter_input'] = 'ovr_max'
                        elif in_nombre.collidepoint(event.pos):
                            estado['market_filter_input'] = 'nombre'
                        elif btn_limpiar.collidepoint(event.pos):
                            estado['market_precio_min'] = 0
                            estado['market_precio_max'] = 0
                            estado['market_ovr_min'] = 0
                            estado['market_ovr_max'] = 0
                            estado['market_nombre_search'] = ''
                            estado['market_filter_input'] = None
                        elif btn_cerrar.collidepoint(event.pos):
                            estado['market_filtros_open'] = False
                            estado['market_filter_input'] = None
                    else:
                        # Click fuera del panel: cerrarlo
                        estado['market_filtros_open'] = False
                        estado['market_filter_input'] = None

                # D. Botones de Paginación
                if page > 0 and pag_rect_prev.collidepoint(event.pos):
                    estado['market_page'] -= 1
                elif page < total_paginas - 1 and pag_rect_next.collidepoint(event.pos):
                    estado['market_page'] += 1

                # E. Botones "Fichar" en los Cards
                for btn_rect, j, eq, ok, motivo in card_rects:
                    if btn_rect.collidepoint(event.pos):
                        if ok:
                            estado['selected_player_to_buy'] = j
                            estado['selected_player_club'] = eq
                            estado['selected_player_intl'] = (estado.get('market_tab') == 'Internacional')
                            estado['show_confirm_modal'] = True
                        else:
                            estado['success_message'] = motivo
                            estado['success_timer'] = 200

                # F. Botón Salir
                if exit_rect.collidepoint(event.pos):
                    # Limpiar variables temporales del mercado antes de salir
                    estado.pop('market_page', None)
                    estado.pop('market_tab', None)
                    estado.pop('show_confirm_modal', None)
                    estado.pop('selected_player_to_buy', None)
                    estado.pop('selected_player_club', None)
                    estado.pop('oferta_inicio_creada', None)
                    estado.pop('market_filter_input', None)
                    estado.pop('market_pais_dropdown_open', None)
                    estado.pop('market_filtros_open', None)
                    estado.pop('market_pais_filtro', None)
                    estado.pop('_market_ligas_cache', None)  # v0.8.4: cache de ligas para fichajes entre ligas
                    estado.pop('free_agents_list', None)
                    return "volver"

    except Exception as general_error:
        print(f"Error general en el renderizado de la pantalla del mercado: {general_error}. Intentando recuperarse...", file=sys.stderr)
        # Fallback de recuperación ante cualquier caída del renderizado
        try:
            # Dibujar un fondo plano y un botón de emergencia
            screen.fill((10, 20, 30))
            emerg_rect = pygame.Rect(490, 330, 300, 60)
            pygame.draw.rect(screen, (255, 0, 0), emerg_rect, border_radius=5)
            font = pygame.font.Font(None, 24)
            txt = font.render("ERROR DE UI. HAZ CLIC PARA CONTINUAR", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=emerg_rect.center))
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if emerg_rect.collidepoint(event.pos):
                        return "volver"
        except Exception as deep_error:
            print(f"Error irrecuperable en fallback del mercado: {deep_error}", file=sys.stderr)
            return "volver"

    return None
