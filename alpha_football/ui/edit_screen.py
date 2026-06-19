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
ESTILOS_TACTICOS = ["anchelottismo", "guardiolismo", "flickismo", "cruyffismo", "mourinhismo", "simeonismo", "bielsismo", "chapecoense"]
RASGOS_JUGADOR = ["ninguno", "regateador", "pulmon_de_hierro", "rustico", "lider"]
POSICIONES = ["POR", "DEF", "MED", "DEL"]

def cargar_base_datos_inicial(estado: dict) -> dict:
    """Carga la base de datos editada desde JSON si existe, o la inicializa desde los módulos base."""
    if 'edited_db' in estado:
        return estado['edited_db']
        
    ruta_db = "alpha_football_edited_db.json"
    if os.path.exists(ruta_db):
        try:
            with open(ruta_db, "r", encoding="utf-8") as f:
                db = json.load(f)
                estado['edited_db'] = db
                return db
        except Exception as e:
            logger.error(f"Error al cargar base de datos editada: {e}")
            
    # Inicializar desde los datos base del juego
    db = {}
    ligas_ids = ['premier', 'laliga', 'betplay', 'brasil', 'argentina']
    for lid in ligas_ids:
        try:
            if lid == 'premier':
                from alpha_football.data.premier import get_liga
            elif lid == 'laliga':
                from alpha_football.data.laliga import get_liga
            elif lid == 'betplay':
                from alpha_football.data.betplay import get_liga
            elif lid == 'brasil':
                from alpha_football.data.brasil import get_liga
            elif lid == 'argentina':
                from alpha_football.data.argentina import get_liga
                
            liga = get_liga()
            from alpha_football.plantilla import expandir_liga
            from alpha_football.market import escalar_presupuestos
            expandir_liga(liga, 20)
            escalar_presupuestos(liga)
            
            db[lid] = [eq.to_dict() for eq in liga.equipos]
        except Exception as e:
            logger.error(f"Error al cargar liga {lid} en editor: {e}")
            
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
        return True
    except Exception as e:
        logger.error(f"Error al guardar base de datos editada: {e}")
        return False

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
        
        for event in pygame.event.get():
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
                        if campo_activo == 'file_path':
                            estado['edit_filepath'] = estado['edit_filepath'][:-1]
                        elif campo_activo == 'team_name':
                            equipo_sel['nombre'] = equipo_sel['nombre'][:-1]
                        elif equipo_sel and campo_activo == 'team_budget':
                            val_str = str(equipo_sel.get('balance', 0))[:-1]
                            equipo_sel['balance'] = int(val_str) if val_str else 0
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
                    else:
                        char = event.unicode
                        # Filtros de caracteres
                        if campo_activo == 'file_path':
                            if char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/:\\':
                                estado['edit_filepath'] += char
                        elif campo_activo == 'team_name':
                            if len(equipo_sel['nombre']) < 30:
                                equipo_sel['nombre'] += char
                        elif campo_activo == 'team_budget':
                            if char.isdigit() and len(str(equipo_sel['balance'])) < 12:
                                equipo_sel['balance'] = int(str(equipo_sel['balance']) + char)
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

        # Dibujar fondo base
        draw_gradient_bg(screen)
        
        # Título
        draw_text(screen, "MODO EDICIÓN DE BASE DE DATOS", (40, 20), size='xl', color='dorado')
        draw_text(screen, "Modifica atributos de equipos y jugadores. Guarda los cambios para que apliquen a nuevas partidas.", (40, 65), size='sm', color='azul')
        
        # --- COLUMNA 1: LIGA Y SELECCION DE EQUIPOS/JUGADORES (Ancho: 450) ---
        col1_rect = pygame.Rect(40, 100, 450, 500)
        draw_panel(screen, col1_rect)
        
        # Selectores de Liga
        ligas_tabs = ['premier', 'laliga', 'betplay', 'brasil', 'argentina']
        tab_names = {'premier': 'PREM', 'laliga': 'ESP', 'betplay': 'COL', 'brasil': 'BRA', 'argentina': 'ARG'}
        tab_x = 55
        tab_w = 75
        for l_id in ligas_tabs:
            tab_rect = pygame.Rect(tab_x, 115, tab_w, 30)
            is_active = (l_id == liga_sel)
            is_hover = tab_rect.collidepoint(mouse_pos)
            
            c_bg = (0, 191, 255) if is_active else ((20, 26, 46) if is_hover else (10, 14, 26))
            c_border = (255, 215, 0) if is_active else (0, 191, 255)
            
            pygame.draw.rect(screen, c_bg, tab_rect, border_radius=4)
            pygame.draw.rect(screen, c_border, tab_rect, width=1, border_radius=4)
            draw_text(screen, tab_names[l_id], (tab_rect.x + 18, tab_rect.y + 6), size='sm', color='bg' if is_active else 'blanco')
            
            if click_pos and tab_rect.collidepoint(click_pos):
                estado['edit_liga_sel'] = l_id
                estado['edit_equipo_idx'] = 0
                estado['edit_jugador_idx'] = -1
                estado['edit_squad_offset'] = 0
                estado['edit_teams_offset'] = 0
                estado['edit_input_activo'] = None
                
            tab_x += tab_w + 5
            
        # Lista de Equipos (Scrollable, 5 visibles)
        draw_text(screen, "EQUIPOS", (55, 155), size='sm', color='dorado')
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
        btn_te_up = pygame.Rect(440, 180, 30, 30)
        btn_te_down = pygame.Rect(440, 315, 30, 30)
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
            draw_text(screen, f"OVR: {j.get('overall', 70)}", (360, squad_y + 6), size='sm', color='dorado')
            
            if click_pos and j_rect.collidepoint(click_pos):
                estado['edit_jugador_idx'] = idx
                estado['edit_input_activo'] = None
                
            squad_y += 36
            
        # Botones de scroll de plantilla
        btn_sq_up = pygame.Rect(440, 405, 30, 30)
        btn_sq_down = pygame.Rect(440, 540, 30, 30)
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
        col2_rect = pygame.Rect(510, 100, 730, 500)
        draw_panel(screen, col2_rect)
        
        if not equipo_sel:
            draw_text(screen, "Selecciona un equipo o jugador en la izquierda para editar.", (530, 130), size='md', color='blanco')
        elif jugador_sel is None:
            # --- EDITAR EQUIPO ---
            draw_text(screen, f"EDITAR EQUIPO: {equipo_sel.get('nombre', 'Equipo').upper()}", (530, 120), size='md', color='dorado')
            
            # Nombre del equipo
            draw_text(screen, "Nombre del Equipo:", (530, 180), size='sm', color='blanco')
            inp_team_name = pygame.Rect(530, 205, 350, 38)
            is_team_name_active = (estado.get('edit_input_activo') == 'team_name')
            pygame.draw.rect(screen, (10, 14, 26) if is_team_name_active else (20, 26, 46), inp_team_name, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_team_name_active else (0, 191, 255), inp_team_name, width=1, border_radius=6)
            draw_text(screen, equipo_sel.get('nombre', ''), (542, 213), size='md', color='blanco')
            
            if click_pos and inp_team_name.collidepoint(click_pos):
                estado['edit_input_activo'] = 'team_name'
                estado['edit_dropdown_activo'] = None
                
            # Presupuesto (en millones)
            draw_text(screen, "Presupuesto (en enteros $, ej. 15000000 para $15M):", (530, 265), size='sm', color='blanco')
            inp_team_budget = pygame.Rect(530, 290, 350, 38)
            is_team_budget_active = (estado.get('edit_input_activo') == 'team_budget')
            pygame.draw.rect(screen, (10, 14, 26) if is_team_budget_active else (20, 26, 46), inp_team_budget, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_team_budget_active else (0, 191, 255), inp_team_budget, width=1, border_radius=6)
            draw_text(screen, f"{equipo_sel.get('balance', 0):,}", (542, 298), size='md', color='blanco')
            
            if click_pos and inp_team_budget.collidepoint(click_pos):
                estado['edit_input_activo'] = 'team_budget'
                estado['edit_dropdown_activo'] = None
                
            # Estilo Táctico (Dropdown)
            draw_text(screen, "Estilo Táctico (DT):", (530, 350), size='sm', color='blanco')
            btn_estilo = pygame.Rect(530, 375, 350, 38)
            is_drop_estilo = (estado.get('edit_dropdown_activo') == 'estilo_dt')
            pygame.draw.rect(screen, (20, 26, 46), btn_estilo, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_drop_estilo else (0, 191, 255), btn_estilo, width=1, border_radius=6)
            draw_text(screen, equipo_sel.get('estilo_dt', 'Cruyffismo').upper(), (542, 383), size='sm', color='dorado')
            draw_text(screen, "▼", (850, 385), size='sm', color='blanco')
            
            if click_pos and btn_estilo.collidepoint(click_pos):
                estado['edit_dropdown_activo'] = 'estilo_dt' if not is_drop_estilo else None
                estado['edit_input_activo'] = None
                
            # Dibujar dropdown de Estilos Tácticos si está abierto
            if is_drop_estilo:
                drop_y = 413
                for est in ESTILOS_TACTICOS:
                    est_rect = pygame.Rect(530, drop_y, 350, 30)
                    hov_est = est_rect.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (30, 40, 70) if hov_est else (10, 14, 26), est_rect)
                    pygame.draw.rect(screen, (0, 191, 255), est_rect, width=1)
                    draw_text(screen, est.upper(), (542, drop_y + 5), size='sm', color='blanco')
                    
                    if click_pos and est_rect.collidepoint(click_pos):
                        equipo_sel['estilo_dt'] = est
                        estado['edit_dropdown_activo'] = None
                        
                    drop_y += 30

        else:
            # --- EDITAR JUGADOR ---
            draw_text(screen, f"EDITAR JUGADOR: {jugador_sel.get('nombre', '').upper()} {jugador_sel.get('apellido', '').upper()}", (530, 120), size='md', color='dorado')
            
            # Nombre
            draw_text(screen, "Nombre:", (530, 170), size='sm', color='blanco')
            inp_play_name = pygame.Rect(530, 195, 300, 36)
            is_play_name_act = (estado.get('edit_input_activo') == 'player_name')
            pygame.draw.rect(screen, (10, 14, 26) if is_play_name_act else (20, 26, 46), inp_play_name, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_play_name_act else (0, 191, 255), inp_play_name, width=1, border_radius=6)
            draw_text(screen, jugador_sel.get('nombre', ''), (542, 203), size='md', color='blanco')
            
            if click_pos and inp_play_name.collidepoint(click_pos):
                estado['edit_input_activo'] = 'player_name'
                estado['edit_dropdown_activo'] = None
                
            # Apellido
            draw_text(screen, "Apellido:", (860, 170), size='sm', color='blanco')
            inp_play_ape = pygame.Rect(860, 195, 300, 36)
            is_play_ape_act = (estado.get('edit_input_activo') == 'player_apellido')
            pygame.draw.rect(screen, (10, 14, 26) if is_play_ape_act else (20, 26, 46), inp_play_ape, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_play_ape_act else (0, 191, 255), inp_play_ape, width=1, border_radius=6)
            draw_text(screen, jugador_sel.get('apellido', ''), (872, 203), size='md', color='blanco')
            
            if click_pos and inp_play_ape.collidepoint(click_pos):
                estado['edit_input_activo'] = 'player_apellido'
                estado['edit_dropdown_activo'] = None
                
            # Valoración (Overall)
            draw_text(screen, "Valoración (OVR) (máx. 99):", (530, 250), size='sm', color='blanco')
            inp_play_ovr = pygame.Rect(530, 275, 140, 36)
            is_play_ovr_act = (estado.get('edit_input_activo') == 'player_ovr')
            pygame.draw.rect(screen, (10, 14, 26) if is_play_ovr_act else (20, 26, 46), inp_play_ovr, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_play_ovr_act else (0, 191, 255), inp_play_ovr, width=1, border_radius=6)
            draw_text(screen, str(jugador_sel.get('overall', 70)), (542, 283), size='md', color='blanco')
            
            if click_pos and inp_play_ovr.collidepoint(click_pos):
                estado['edit_input_activo'] = 'player_ovr'
                estado['edit_dropdown_activo'] = None
                
            # Edad
            draw_text(screen, "Edad:", (700, 250), size='sm', color='blanco')
            inp_play_age = pygame.Rect(700, 275, 130, 36)
            is_play_age_act = (estado.get('edit_input_activo') == 'player_age')
            pygame.draw.rect(screen, (10, 14, 26) if is_play_age_act else (20, 26, 46), inp_play_age, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_play_age_act else (0, 191, 255), inp_play_age, width=1, border_radius=6)
            draw_text(screen, str(jugador_sel.get('edad', 25)), (712, 283), size='md', color='blanco')
            
            if click_pos and inp_play_age.collidepoint(click_pos):
                estado['edit_input_activo'] = 'player_age'
                estado['edit_dropdown_activo'] = None
                
            # Posición (Dropdown)
            draw_text(screen, "Posición:", (860, 250), size='sm', color='blanco')
            btn_pos = pygame.Rect(860, 275, 300, 36)
            is_drop_pos = (estado.get('edit_dropdown_activo') == 'posicion')
            pygame.draw.rect(screen, (20, 26, 46), btn_pos, border_radius=6)
            pygame.draw.rect(screen, (0, 255, 136) if is_drop_pos else (0, 191, 255), btn_pos, width=1, border_radius=6)
            draw_text(screen, jugador_sel.get('posicion', 'DEF').upper(), (872, 283), size='sm', color='dorado')
            draw_text(screen, "▼", (1130, 285), size='sm', color='blanco')
            
            if click_pos and btn_pos.collidepoint(click_pos):
                estado['edit_dropdown_activo'] = 'posicion' if not is_drop_pos else None
                estado['edit_input_activo'] = None
                
            if is_drop_pos:
                drop_y = 311
                for pos in POSICIONES:
                    pos_rect = pygame.Rect(860, drop_y, 300, 30)
                    hov_pos = pos_rect.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (30, 40, 70) if hov_pos else (10, 14, 26), pos_rect)
                    pygame.draw.rect(screen, (0, 191, 255), pos_rect, width=1)
                    draw_text(screen, pos.upper(), (872, drop_y + 5), size='sm', color='blanco')
                    
                    if click_pos and pos_rect.collidepoint(click_pos):
                        jugador_sel['posicion'] = pos
                        estado['edit_dropdown_activo'] = None
                        
                    drop_y += 30
                    
            # Rasgo / Característica (Dropdown)
            draw_text(screen, "Rasgo Especial:", (530, 335), size='sm', color='blanco')
            btn_rasgo = pygame.Rect(530, 360, 300, 36)
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
                
            if is_drop_rasgo:
                drop_y = 396
                for rsg in RASGOS_JUGADOR:
                    rsg_rect = pygame.Rect(530, drop_y, 300, 30)
                    hov_rsg = rsg_rect.collidepoint(mouse_pos)
                    pygame.draw.rect(screen, (30, 40, 70) if hov_rsg else (10, 14, 26), rsg_rect)
                    pygame.draw.rect(screen, (0, 191, 255), rsg_rect, width=1)
                    draw_text(screen, rsg.upper(), (542, drop_y + 5), size='sm', color='blanco')
                    
                    if click_pos and rsg_rect.collidepoint(click_pos):
                        jugador_sel['rasgo'] = None if rsg == "ninguno" else rsg
                        estado['edit_dropdown_activo'] = None
                        
                    drop_y += 30

        # --- PANEL DE ACCIONES INFERIORES: EXPORTAR, IMPORTAR, GUARDAR (X=510, Y=430) ---
        actions_y = 430
        draw_text(screen, "IMPORTAR / EXPORTAR BASE DE DATOS", (530, actions_y), size='sm', color='dorado')
        
        # Input ruta de archivo
        inp_file_rect = pygame.Rect(530, actions_y + 25, 400, 36)
        is_file_act = (estado.get('edit_input_activo') == 'file_path')
        pygame.draw.rect(screen, (10, 14, 26) if is_file_act else (20, 26, 46), inp_file_rect, border_radius=6)
        pygame.draw.rect(screen, (0, 255, 136) if is_file_act else (0, 191, 255), inp_file_rect, width=1, border_radius=6)
        draw_text(screen, estado['edit_filepath'], (542, actions_y + 33), size='sm', color='blanco')
        
        if click_pos and inp_file_rect.collidepoint(click_pos):
            estado['edit_input_activo'] = 'file_path'
            estado['edit_dropdown_activo'] = None
            
        # Botones de Importación / Exportación
        btn_export = pygame.Rect(950, actions_y + 25, 120, 36)
        btn_import = pygame.Rect(1085, actions_y + 25, 120, 36)
        
        hov_exp = btn_export.collidepoint(mouse_pos)
        hov_imp = btn_import.collidepoint(mouse_pos)
        
        draw_button(screen, btn_export, "EXPORTAR", hov_exp)
        draw_button(screen, btn_import, "IMPORTAR", hov_imp)
        draw_text(screen, "EXPORTAR", (970, actions_y + 33), size='sm', color='bg' if hov_exp else 'blanco')
        draw_text(screen, "IMPORTAR", (1105, actions_y + 33), size='sm', color='bg' if hov_imp else 'blanco')
        
        # Botón RESTAURAR BASE BASE
        btn_reset = pygame.Rect(530, actions_y + 75, 200, 36)
        hov_rst = btn_reset.collidepoint(mouse_pos)
        draw_button(screen, btn_reset, "RESTAURAR BASE", hov_rst)
        draw_text(screen, "RESTAURAR BASE BASE", (550, actions_y + 83), size='sm', color='bg' if hov_rst else 'rojo')
        
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
                            if any(lid in imported_db for lid in ['premier', 'laliga', 'betplay']):
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
                ruta_db = "alpha_football_edited_db.json"
                if os.path.exists(ruta_db):
                    try:
                        os.remove(ruta_db)
                    except: pass
                estado.pop('edited_db', None)
                db = cargar_base_datos_inicial(estado)
                estado['edit_equipo_idx'] = 0
                estado['edit_jugador_idx'] = -1
                estado['edit_mensaje'] = "Base de datos restaurada."
                estado['edit_mensaje_ticks'] = pygame.time.get_ticks()

        # --- BOTONES PRINCIPALES INFERIORES: APLICAR Y VOLVER (X=40, Y=610) ---
        btn_aplicar = pygame.Rect(40, 615, 300, 50)
        btn_volver = pygame.Rect(360, 615, 200, 50)
        
        hov_ap = btn_aplicar.collidepoint(mouse_pos)
        hov_vo = btn_volver.collidepoint(mouse_pos)
        
        draw_button(screen, btn_aplicar, "APLICAR Y GUARDAR", hov_ap)
        draw_button(screen, btn_volver, "VOLVER AL MENÚ", hov_vo)
        
        draw_text(screen, "APLICAR Y GUARDAR Cambios", (70, 628), size='md', color='bg' if hov_ap else 'verde')
        draw_text(screen, "VOLVER AL MENÚ", (390, 628), size='md', color='bg' if hov_vo else 'blanco')
        
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
