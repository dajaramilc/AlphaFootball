# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de Opciones (Fase 7).
Centraliza el control de volumen (ya no hay widget flotante global), el toggle de
música y el importador de música de YouTube (yt-dlp asíncrono). Persiste preferencias.
"""
from __future__ import annotations

import logging
import pygame

try:
    from alpha_football.ui.theme import (
        SCREEN_W, SCREEN_H, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
    )
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    COLORS = {'bg': (10, 14, 26), 'verde': (0, 255, 136), 'dorado': (255, 215, 0),
              'rojo': (255, 68, 68), 'azul': (0, 191, 255), 'blanco': (255, 255, 255), 'panel': (20, 26, 46)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=6); return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)


def render(screen, estado: dict):
    """Pantalla de opciones. Retorna estado['options_return'] (def. 'menu') al salir, o None."""
    try:
        from alpha_football import audio
    except Exception:
        audio = None

    # Inicialización perezosa del campo de texto del importador y sub-vista
    estado.setdefault('opt_url', "")
    estado.setdefault('opt_input_activo', False)
    estado.setdefault('opt_view', 'main')
    estado.setdefault('playlist_page', 0)

    mouse_pos = pygame.mouse.get_pos()
    volumen = getattr(audio, 'CURRENT_VOLUME', estado.get('volumen', 0.5)) if audio else 0.5

    # --- Rects de la UI ---
    panel = pygame.Rect(SCREEN_W // 2 - 360, 90, 720, 540)
    rect_menos = pygame.Rect(panel.left + 60, 210, 60, 50)
    rect_mute = pygame.Rect(panel.left + 130, 210, 70, 50)
    rect_mas = pygame.Rect(panel.left + 210, 210, 60, 50)
    rect_input = pygame.Rect(panel.left + 60, 360, 500, 50)
    rect_descargar = pygame.Rect(panel.left + 575, 360, 90, 50)
    rect_volver = pygame.Rect(panel.left + 60, panel.bottom - 60, 200, 48)
    rect_playlist = pygame.Rect(panel.right - 260, panel.bottom - 60, 200, 48)

    # --- VISTA: PLAYLIST INTERNA ---
    if estado.get('opt_view') == 'playlist':
        canciones = []
        try:
            import os
            if audio and hasattr(audio, 'MUSIC_DIR') and os.path.exists(audio.MUSIC_DIR):
                canciones = [
                    os.path.normpath(os.path.join(audio.MUSIC_DIR, f))
                    for f in os.listdir(audio.MUSIC_DIR)
                    if f.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a'))
                ]
            else:
                canciones = list(getattr(audio, 'PLAYLIST', []))
            canciones.sort(key=lambda x: os.path.basename(x).lower())
        except Exception as e_lst:
            logger.error(f"Error al listar canciones en options_screen: {e_lst}")
            canciones = []

        items_por_pagina = 6
        total_paginas = max(1, (len(canciones) + items_por_pagina - 1) // items_por_pagina)
        
        pagina = min(estado.get('playlist_page', 0), total_paginas - 1)
        pagina = max(0, pagina)
        estado['playlist_page'] = pagina
        
        start_idx = pagina * items_por_pagina
        actuales = canciones[start_idx : start_idx + items_por_pagina]

        rect_prev = pygame.Rect(panel.left + 60, panel.bottom - 115, 120, 36)
        rect_next = pygame.Rect(panel.right - 180, panel.bottom - 115, 120, 36)
        rect_volver_opts = pygame.Rect(panel.left + 60, panel.bottom - 60, 200, 48)

        del_rects = []
        for idx, path in enumerate(actuales):
            y_pos = 175 + idx * 50
            del_rect = pygame.Rect(panel.right - 150, y_pos + 4, 90, 32)
            del_rects.append((del_rect, path))

        click_pos = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.event.post(event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                cp = event.pos
                if rect_volver_opts.collidepoint(cp):
                    estado['opt_view'] = 'main'
                elif rect_prev.collidepoint(cp):
                    estado['playlist_page'] = max(0, pagina - 1)
                elif rect_next.collidepoint(cp):
                    estado['playlist_page'] = min(total_paginas - 1, pagina + 1)
                else:
                    for r_del, p_path in del_rects:
                        if r_del.collidepoint(cp):
                            if audio and hasattr(audio, 'eliminar_pista'):
                                audio.eliminar_pista(p_path)
                            else:
                                try:
                                    if os.path.exists(p_path):
                                        os.remove(p_path)
                                except Exception as e_del:
                                    logger.error(f"Fallo al eliminar pista: {e_del}")
                            break

        # Dibujo Playlist
        draw_gradient_bg(screen)
        draw_panel(screen, panel)
        draw_text(screen, "PLAYLIST DEL JUEGO 🎵", (panel.left + 40, 110), size='xl', color='dorado')
        
        if not canciones:
            draw_text(screen, "No se encontraron canciones en la carpeta 'music/'.", (panel.left + 60, 200), size='md', color='blanco')
        else:
            for idx, p_path in enumerate(actuales):
                y_pos = 175 + idx * 50
                row_rect = pygame.Rect(panel.left + 60, y_pos, 600, 40)
                
                # Dibujar fondo de fila
                pygame.draw.rect(screen, (15, 22, 42), row_rect, border_radius=6)
                pygame.draw.rect(screen, (35, 45, 80), row_rect, width=1, border_radius=6)
                
                # Nombre legible de la canción
                legible = ""
                if audio and hasattr(audio, '_titulo_legible'):
                    legible = audio._titulo_legible(p_path)
                else:
                    legible = os.path.splitext(os.path.basename(p_path))[0]
                mostrado = legible[:48]
                draw_text(screen, mostrado, (row_rect.left + 15, row_rect.top + 10), size='sm', color='blanco')
                
                # Botón de eliminar
                r_del = next(r for r, p in del_rects if p == p_path)
                hov_del = r_del.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (60, 20, 25) if hov_del else (20, 26, 46), r_del, border_radius=6)
                pygame.draw.rect(screen, COLORS['rojo'], r_del, width=1, border_radius=6)
                
                font_btn = get_font('sm')
                txt_surf = font_btn.render("BORRAR", True, COLORS['rojo'])
                txt_rect = txt_surf.get_rect(center=r_del.center)
                screen.blit(txt_surf, txt_rect)

            # Paginador
            if total_paginas > 1:
                draw_button(screen, rect_prev, "ANTERIOR", rect_prev.collidepoint(mouse_pos))
                draw_button(screen, rect_next, "SIGUIENTE", rect_next.collidepoint(mouse_pos))
                p_txt = f"Pág. {pagina + 1} de {total_paginas}"
                draw_text(screen, p_txt, (panel.centerx - 50, panel.bottom - 108), size='sm', color='azul')

        draw_button(screen, rect_volver_opts, "VOLVER", rect_volver_opts.collidepoint(mouse_pos))
        return None

    # Resultados de búsqueda por nombre (clicables) para elegir cuál descargar.
    resultados = audio.resultados_busqueda() if (audio and hasattr(audio, 'resultados_busqueda')) else []
    res_rects = [(pygame.Rect(panel.left + 60, 438 + i * 24, 605, 22), r) for i, r in enumerate(resultados[:5])]

    # --- Eventos ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.event.post(event)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cp = event.pos
            estado['opt_input_activo'] = rect_input.collidepoint(cp)
            _elegido = next((r for rr, r in res_rects if rr.collidepoint(cp)), None)
            if _elegido is not None and audio:
                # Descargar SOLO el resultado elegido y limpiar la lista.
                audio.descargar_url_async(_elegido['url'])
                if hasattr(audio, 'limpiar_busqueda'):
                    audio.limpiar_busqueda()
                estado['opt_url'] = ""
            elif audio and rect_menos.collidepoint(cp):
                audio.set_volume(max(0.0, volumen - 0.1)); _persistir(audio, estado)
            elif audio and rect_mas.collidepoint(cp):
                audio.set_volume(min(1.0, volumen + 0.1)); _persistir(audio, estado)
            elif audio and rect_mute.collidepoint(cp):
                if volumen > 0.0:
                    estado['last_non_zero_volume'] = volumen; audio.set_volume(0.0)
                else:
                    audio.set_volume(estado.get('last_non_zero_volume', 0.5))
                _persistir(audio, estado)
            elif rect_descargar.collidepoint(cp):
                if audio:
                    _iniciar_descarga(audio, estado['opt_url'])
                    estado['opt_url'] = ""
            elif rect_playlist.collidepoint(cp):
                estado['opt_view'] = 'playlist'
                estado['playlist_page'] = 0
            elif rect_volver.collidepoint(cp):
                _persistir(audio, estado)
                return estado.get('options_return', 'menu')
        elif event.type == pygame.KEYDOWN and estado['opt_input_activo']:
            es_ctrl = bool(event.mod & pygame.KMOD_CTRL)
            if es_ctrl and event.key == pygame.K_v:
                # Pegar desde el portapapeles (Ctrl+V): es lo que pedía Diego, antes no existía.
                pegado = _leer_portapapeles()
                if pegado:
                    pegado = pegado.replace("\n", "").replace("\r", "").strip()
                    estado['opt_url'] = (estado['opt_url'] + pegado)[:200]
            elif event.key == pygame.K_BACKSPACE:
                estado['opt_url'] = estado['opt_url'][:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if audio:
                    _iniciar_descarga(audio, estado['opt_url']); estado['opt_url'] = ""
            elif event.unicode and event.unicode.isprintable() and len(estado['opt_url']) < 200:
                estado['opt_url'] += event.unicode

    # --- Dibujo ---
    draw_gradient_bg(screen)
    draw_panel(screen, panel)
    draw_text(screen, "OPCIONES", (panel.left + 40, 110), size='xl', color='dorado')

    # Volumen
    draw_text(screen, f"VOLUMEN: {int(volumen * 100)}%", (panel.left + 60, 175), size='md', color='blanco')
    draw_button(screen, rect_menos, "-", rect_menos.collidepoint(mouse_pos))
    draw_button(screen, rect_mute, "M", rect_mute.collidepoint(mouse_pos))
    draw_button(screen, rect_mas, "+", rect_mas.collidepoint(mouse_pos))
    # Barra de volumen
    barra = pygame.Rect(panel.left + 290, 225, 360, 16)
    pygame.draw.rect(screen, (40, 50, 75), barra, border_radius=4)
    relleno = pygame.Rect(barra.left, barra.top, int(barra.width * volumen), barra.height)
    pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), relleno, border_radius=4)
    draw_text(screen, "Atajos globales en el juego: + / - / M", (panel.left + 60, 280), size='sm', color='azul')

    # Importador de música
    draw_text(screen, "IMPORTAR MÚSICA (URL o nombre de canción)", (panel.left + 60, 320), size='md', color='blanco')
    borde_input = COLORS.get('verde', (0, 255, 136)) if estado['opt_input_activo'] else COLORS.get('azul', (0, 191, 255))
    pygame.draw.rect(screen, (12, 18, 36), rect_input, border_radius=6)
    pygame.draw.rect(screen, borde_input, rect_input, width=2, border_radius=6)
    txt = estado['opt_url'] or "Pega una URL (Ctrl+V) o escribe el nombre de la canción…"
    txt_color = 'blanco' if estado['opt_url'] else 'azul'
    mostrado = txt[-46:] if len(txt) > 46 else txt
    draw_text(screen, mostrado, (rect_input.left + 10, rect_input.top + 14), size='sm', color=txt_color)
    # Botón dinámico: BAJAR (si es URL) o BUSCAR (si es un nombre).
    label_btn = "BAJAR" if _es_url(estado['opt_url']) else "BUSCAR"
    draw_button(screen, rect_descargar, label_btn, rect_descargar.collidepoint(mouse_pos))

    # Línea de estado: prioriza la búsqueda; si no, la descarga.
    msg_line, color_line = None, 'blanco'
    if audio:
        sb = audio.estado_busqueda() if hasattr(audio, 'estado_busqueda') else {}
        st = audio.estado_descarga()
        if sb.get('mensaje'):
            msg_line, color_line = sb['mensaje'], ('dorado' if sb.get('activo') else 'verde')
        elif st.get('mensaje'):
            msg_line = st['mensaje']
            color_line = 'dorado' if st.get('activo') else ('verde' if 'Listo' in st['mensaje'] else 'blanco')
    if msg_line:
        draw_text(screen, msg_line, (panel.left + 60, 414), size='sm', color=color_line)

    # Resultados de búsqueda clicables: título — canal [mm:ss]. Clic = descargar ese.
    for rr, r in res_rects:
        hov = rr.collidepoint(mouse_pos)
        try:
            pygame.draw.rect(screen, (22, 40, 30) if hov else (14, 20, 38), rr, border_radius=4)
            pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)) if hov else COLORS.get('azul', (0, 191, 255)),
                             rr, width=1, border_radius=4)
        except Exception:
            pass
        dur = r.get('duration')
        dur_txt = f"  [{int(dur) // 60}:{int(dur) % 60:02d}]" if isinstance(dur, (int, float)) and dur else ""
        etiqueta = r.get('title', '')[:46]
        if r.get('uploader'):
            etiqueta += f" — {r['uploader'][:16]}"
        etiqueta += dur_txt
        draw_text(screen, etiqueta[:72], (rr.x + 8, rr.y + 2), size='sm', color='blanco')

    draw_button(screen, rect_volver, "VOLVER", rect_volver.collidepoint(mouse_pos))
    draw_button(screen, rect_playlist, "VER PLAYLIST", rect_playlist.collidepoint(mouse_pos))
    return None


def _es_url(t: str) -> bool:
    t = (t or "").strip().lower()
    return t.startswith(("http://", "https://", "www.")) or "youtu" in t


def _iniciar_descarga(audio, texto: str) -> None:
    """URL -> descarga directa; nombre -> BUSCA y muestra resultados para elegir (no baja aún)."""
    t = (texto or "").strip()
    if not t or audio is None:
        return
    if _es_url(t):
        audio.descargar_url_async(t)
    else:
        # Busca y muestra opciones; el usuario elige cuál descargar (para no bajar cualquier cosa).
        if hasattr(audio, "buscar_canciones_async"):
            audio.buscar_canciones_async(t)
        else:
            audio.descargar_por_nombre_async(t)


def _leer_portapapeles() -> str:
    """
    Lee el texto del portapapeles del sistema (para Ctrl+V). Resiliente:
    intenta primero Tkinter (fiable en Windows y en la stdlib) y cae a pygame.scrap.
    Devuelve "" si no se puede leer, sin romper la pantalla de opciones.
    """
    # Opción 1: Tkinter — disponible en la librería estándar y estable en Windows.
    try:
        import tkinter
        raiz = tkinter.Tk()
        raiz.withdraw()
        try:
            contenido = raiz.clipboard_get()
        finally:
            raiz.destroy()
        if contenido:
            return str(contenido)
    except Exception as e_tk:
        logger.debug(f"No se pudo leer el portapapeles vía Tkinter: {e_tk}")

    # Opción 2 (fallback): pygame.scrap, que puede no estar inicializado en todos los entornos.
    try:
        import pygame.scrap as scrap
        if not scrap.get_init():
            scrap.init()
        datos = scrap.get(pygame.SCRAP_TEXT)
        if datos:
            return datos.decode("utf-8", errors="ignore").replace("\x00", "")
    except Exception as e_scrap:
        logger.debug(f"No se pudo leer el portapapeles vía pygame.scrap: {e_scrap}")

    return ""


def _persistir(audio, estado: dict) -> None:
    """Guarda el volumen actual en preferencias (fail-soft)."""
    try:
        if audio:
            audio.guardar_preferencias({"volumen": getattr(audio, 'CURRENT_VOLUME', 0.5)})
    except Exception as e:
        logger.debug(f"No se pudo persistir preferencia de volumen: {e}")
