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
    from alpha_football.market import calcular_precio
except Exception as error_market:
    print(f"Advertencia: No se pudo importar alpha_football.market ({error_market}). Usando fallback de precio local.", file=sys.stderr)
    def calcular_precio(jugador):
        try:
            return max(50000, (jugador.overall - 45) ** 2 * 3500)
        except Exception:
            return 75000

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
        
        # Oferta de inicio de temporada (se dispara la primera vez que se entra en esta ventana de pases)
        estado.setdefault('oferta_inicio_creada', False)
        estado.setdefault('oferta_inicio_pendiente', False)
        estado.setdefault('oferta_inicio_estrella', None)
        estado.setdefault('oferta_inicio_monto', 0)
        estado.setdefault('oferta_inicio_comprador', None)
        
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
                    estado['oferta_inicio_estrella'] = estrella
                    estado['oferta_inicio_monto'] = monto
                    estado['oferta_inicio_comprador'] = comprador
                    estado['oferta_inicio_pendiente'] = True
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
        else:
            # Jugadores de otros clubes
            for eq in equipos:
                if eq.nombre == mi_equipo.nombre:
                    continue
                for j in eq.jugadores:
                    # Aplicar filtros por posición
                    if tab == 'Todos' or j.posicion == tab:
                        todos_jugadores.append((j, eq))
                        
            # Ordenar por overall de mayor a menor
            todos_jugadores.sort(key=lambda item: item[0].overall, reverse=True)
            
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
        draw_text(screen, f"Fichajes de esta ventana: {estado['fichajes_realizados']}/3", (860, 95), size='sm', color='dorado')

        # 4. Dibujar Pestañas de Filtrado
        tab_names = ['Todos', 'POR', 'DEF', 'MED', 'DEL', 'Libres']
        tab_rects = {}
        tab_x = 40
        tab_y = 100
        tab_w = 120
        tab_h = 35
        
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

        # 5. Dibujar Grid de Jugadores Disponibles (Cards)
        card_w, card_h = 370, 140
        card_spacing_x, card_spacing_y = 20, 15
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
            
            # Botón "Fichar" en la parte inferior derecha del card
            btn_rect = pygame.Rect(x + 240, y + 85, 110, 35)
            can_afford = (mi_equipo.balance >= precio)
            has_slots = (estado['fichajes_realizados'] < 3)
            
            btn_hover = btn_rect.collidepoint(mouse_pos)
            
            if has_slots and can_afford:
                draw_button(screen, btn_rect, "FICHAR", btn_hover)
                card_rects.append((btn_rect, j, eq))
            elif not has_slots:
                # Dibujar botón deshabilitado
                pygame.draw.rect(screen, (40, 40, 40), btn_rect, border_radius=5)
                font = get_font('sm')
                txt = font.render("LIMITE 3", True, (120, 120, 120))
                screen.blit(txt, txt.get_rect(center=btn_rect.center))
            else:
                # Sin fondos
                pygame.draw.rect(screen, (50, 20, 20), btn_rect, border_radius=5)
                font = get_font('sm')
                txt = font.render("SIN FONDOS", True, COLORS['rojo'])
                screen.blit(txt, txt.get_rect(center=btn_rect.center))

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
            pygame.draw.rect(screen, (20, 80, 40), banner_rect, border_radius=5)
            draw_text(screen, estado['success_message'], (60, 623), size='md', color='verde')
            
            estado['success_timer'] -= 1
            if estado['success_timer'] <= 0:
                estado['success_message'] = ""

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
                            
                            # Generar un suplente del mismo puesto
                            suplente = generar_reemplazo_resiliente(estrella.posicion, mi_equipo.estrellas)
                            mi_equipo.jugadores.append(suplente)
                            
                            estado['transfer_log'].append(f"Venta: {estrella.nombre_completo} -> {comprador.nombre} por ${monto:,}")
                            estado['success_message'] = f"Vendido {estrella.nombre_completo}. Llega {suplente.nombre_completo} de reemplazo."
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

                # B. Manejar interacciones del Modal de Confirmación de Compra
                elif estado['show_confirm_modal']:
                    btn_yes_rect = pygame.Rect(SCREEN_W // 2 - 210, SCREEN_H // 2 + 40, 190, 45)
                    btn_no_rect = pygame.Rect(SCREEN_W // 2 + 20, SCREEN_H // 2 + 40, 190, 45)
                    
                    if btn_yes_rect.collidepoint(event.pos):
                        j_buy = estado['selected_player_to_buy']
                        eq_orig = estado['selected_player_club']
                        precio = calcular_precio(j_buy)
                        
                        try:
                            # Efectuar compra
                            mi_equipo.balance -= precio
                            
                            # Si es un rival, quitarlo de su club
                            if eq_orig:
                                eq_orig.jugadores.remove(j_buy)
                            else:
                                # Si es un agente libre, quitarlo del pool libre
                                if 'free_agents_list' in estado and j_buy in estado['free_agents_list']:
                                    estado['free_agents_list'].remove(j_buy)
                            
                            # Gestionar límite de 11 jugadores en plantilla.
                            # Si el equipo ya tiene 11 o más, reemplazamos al peor de la misma posición
                            misma_pos = [p for p in mi_equipo.jugadores if p.posicion == j_buy.posicion]
                            if len(misma_pos) >= 2 or len(mi_equipo.jugadores) >= 11:
                                if misma_pos:
                                    peor = min(misma_pos, key=lambda player: player.overall)
                                else:
                                    peor = min(mi_equipo.jugadores, key=lambda player: player.overall)
                                    
                                mi_equipo.jugadores.remove(peor)
                                if eq_orig:
                                    # Devolver al club de origen
                                    eq_orig.jugadores.append(peor)
                                    log_cambio = f"Cambio: {peor.nombre_completo} al {eq_orig.nombre}"
                                else:
                                    # Se vuelve libre
                                    if 'free_agents_list' in estado:
                                        estado['free_agents_list'].append(peor)
                                    log_cambio = f"Liberado: {peor.nombre_completo}"
                                estado['transfer_log'].append(log_cambio)
                            
                            # Añadir a mi equipo
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
                        
                # D. Botones de Paginación
                if page > 0 and pag_rect_prev.collidepoint(event.pos):
                    estado['market_page'] -= 1
                elif page < total_paginas - 1 and pag_rect_next.collidepoint(event.pos):
                    estado['market_page'] += 1
                    
                # E. Botones "Fichar" en los Cards
                for btn_rect, j, eq in card_rects:
                    if btn_rect.collidepoint(event.pos):
                        estado['selected_player_to_buy'] = j
                        estado['selected_player_club'] = eq
                        estado['show_confirm_modal'] = True
                        
                # F. Botón Salir
                if exit_rect.collidepoint(event.pos):
                    # Limpiar variables temporales del mercado antes de salir
                    estado.pop('market_page', None)
                    estado.pop('market_tab', None)
                    estado.pop('show_confirm_modal', None)
                    estado.pop('selected_player_to_buy', None)
                    estado.pop('selected_player_club', None)
                    estado.pop('oferta_inicio_creada', None)
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
