    # -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL v0.4 — PUNTO DE ENTRADA Y ORQUESTADOR.

Arranca pygame, inicializa la paleta visual, el sistema de audio,
y gestiona la máquina de estados que transiciona entre pantallas de la UI.
Implementa autoguardado resiliente al cerrar el juego.
"""

from __future__ import annotations

import sys
import os
import logging
import subprocess

# --- DETECCION DE ARGUMENTO DE IMPRESION DE TIMEOUT ---
# Si el usuario o sistema invoca el juego con la bandera '--print-timeout',
# debemos imprimir el valor de timeout configurado para descargas de musica y salir.
try:
    if "--print-timeout" in sys.argv:
        # Ocultamos la advertencia/bienvenida de pygame al importar audio
        os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
        try:
            # Intentamos importar la constante del modulo de audio
            from alpha_football.audio import SOCKET_TIMEOUT
            print(SOCKET_TIMEOUT)
        except Exception as error_imp:
            # En caso de fallo en la importacion, usamos un valor de respaldo por defecto
            print(15)
        sys.exit(0)
except SystemExit:
    # Permitimos la salida del sistema controlada
    sys.exit(0)
except Exception as error_global_args:
    # Manejo de error de respaldo para evitar cualquier interrupcion catastrofica
    print(15)
    sys.exit(0)

# Configuración básica del logging inicial
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("alpha_football_bootstrap")

def instalar_dependencia(nombre_paquete: str) -> bool:
    """
    Intenta instalar un paquete utilizando pip de forma silenciosa y automática.
    Retorna True si la instalación reportó éxito, de lo contrario False.
    """
    try:
        logger.info(f"Intentando instalar la dependencia faltante '{nombre_paquete}' de forma automatica...")
        # Se ejecuta utilizando el mismo intérprete activo
        resultado = subprocess.run(
            [sys.executable, "-m", "pip", "install", nombre_paquete],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Instalacion exitosa de '{nombre_paquete}': {resultado.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as error_proceso:
        logger.error(
            f"Fallo al instalar la dependencia '{nombre_paquete}' mediante pip. "
            f"Codigo de retorno: {error_proceso.returncode}. "
            f"Detalle de error: {error_proceso.stderr.strip()}"
        )
        return False
    except Exception as error_general:
        logger.error(f"Error inesperado al intentar instalar '{nombre_paquete}': {error_general}")
        return False

# Verificación de la dependencia crítica pygame
try:
    import pygame
except ImportError as error_importacion:
    logger.warning(
        f"La libreria Pygame no esta instalada en el sistema: {error_importacion}. "
        "Iniciando instalacion automatica para evitar el cierre del juego..."
    )
    exito = instalar_dependencia("pygame")
    if not exito:
        logger.critical(
            "No se pudo instalar Pygame de forma automatica. "
            "Por favor, instala la libreria manualmente ejecutando: pip install pygame"
        )
        sys.exit(1)
    
    # Reintento de importación
    try:
        import pygame
    except ImportError as error_reintento:
        logger.critical(
            f"Aunque la instalacion reporto exito, la importacion de Pygame volvio a fallar: {error_reintento}."
        )
        sys.exit(1)

# Continuación del logging con el logger oficial
logger = logging.getLogger("alpha_football_main")

# --- MONKEYPATCH PARA EVITAR CONFLICTOS EN LA COLA DE EVENTOS DE PYGAME ---
# Guardamos la función original de pygame.event.get para llamarla una vez por frame
_original_event_get = pygame.event.get
_cached_frame_events = []

def _custom_event_get(eventtype=None, pump=True):
    """
    Retorna la lista de eventos del frame actual sin limpiar la cola repetidamente.
    Permite que tanto las pantallas como el bucle principal inspeccionen los mismos eventos.
    """
    global _cached_frame_events
    try:
        if eventtype is not None:
            if isinstance(eventtype, (list, tuple)):
                return [e for e in _cached_frame_events if e.type in eventtype]
            return [e for e in _cached_frame_events if e.type == eventtype]
        return list(_cached_frame_events)
    except Exception as error_get:
        logger.error(f"Error en el manejador personalizado de eventos: {error_get}")
        return []

# Reemplazamos globalmente en pygame
pygame.event.get = _custom_event_get

# Dimensiones de la pantalla
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60


# --- Autoguardado al Salir ════════════════════════════════════════════════════

def guardar_al_salir(estado: dict) -> None:
    """Intenta guardar la partida automáticamente de forma segura antes de cerrar."""
    try:
        from alpha_football.save import guardar_partida
        from alpha_football.models import EstadoJuego
        
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        
        # Si no hay partida activa en curso, no hacemos nada
        if not liga or not mi_equipo:
            return
            
        alin = estado.get('alineacion_activa')
        datos_estado = {
            "ligas": [liga.to_dict()],
            "copas": [c.to_dict() for c in estado.get("copas", [])],
            "equipo_usuario_id": mi_equipo.id,
            "liga_usuario_id": liga.tipo,
            "temporada": estado.get("temporada", 1),
            "historial": estado.get("historial", []),
            "transfer_log": estado.get("transfer_log", []),
            "pantalla_actual": "temporada",
            "alineacion_activa": {
                "titulares": list(alin.titulares),
                "formacion": str(alin.formacion)
            } if alin else None,
            "dt_nombre": estado.get("dt_nombre", ""),
            "dt_nacionalidad": estado.get("dt_nacionalidad", ""),
            "copa_tipo": estado.get("copa_tipo"),
            "copa_fase_actual": estado.get("copa_fase_actual"),
            "copa_grupo_standing": estado.get("copa_grupo_standing", []),
            "copa_bracket": estado.get("copa_bracket", {}),
            "copa_grupo_partidos": estado.get("copa_grupo_partidos", []),
            "copa_jornada_grupo": estado.get("copa_jornada_grupo", 1),
            "copa_tab": estado.get("copa_tab"),
            "copa_grupos": estado.get("copa_grupos", {}),
            "copa_grupos_standings": estado.get("copa_grupos_standings", {}),
            "copa_bracket_otros": estado.get("copa_bracket_otros", {})
        }

        estado_juego = EstadoJuego.from_dict(datos_estado)

        # Fase 2: autoguardar en un SLOT (multislot). Si no hay slot activo, se elige el primer
        # slot libre (o el 1) para no pisar otras partidas; los juegos cargados conservan su slot.
        try:
            from alpha_football import save as _save
            slot = estado.get('slot_activo')
            if not slot:
                try:
                    libres = [i + 1 for i, h in enumerate(_save.listar_slots()) if h is None]
                    slot = libres[0] if libres else 1
                except Exception:
                    slot = 1
                estado['slot_activo'] = slot
            nombre = f"{mi_equipo.corto} (T{estado_juego.temporada} J{liga.jornada_actual})"
            _save.guardar_en_slot(estado_juego, slot, nombre)
            logger.info(f"Partida autoguardada en el slot {slot} antes de salir.")
        except Exception as e_slot:
            logger.warning(f"No se pudo autoguardar en slot ({e_slot}); usando archivo por defecto.")
            guardar_partida(estado_juego)
    except Exception as e:
        logger.error(f"Error al intentar realizar el autoguardado: {e}")

# --- Coordenadas del Widget de Volumen Global ═════════════════════════════════
# Ubicación del panel principal del control de volumen
RECT_PANEL_VOLUMEN = pygame.Rect(1110, 20, 150, 80)
# Ubicación del indicador visual de barra de progreso de volumen
RECT_BARRA_VOLUMEN = pygame.Rect(1125, 47, 120, 6)
# Botón para disminuir el volumen (-10%)
RECT_BOTON_MINUS = pygame.Rect(1125, 58, 35, 22)
# Botón para silenciar o restaurar el volumen (Mute)
RECT_BOTON_MUTE = pygame.Rect(1167, 58, 35, 22)
# Botón para aumentar el volumen (+10%)
RECT_BOTON_PLUS = pygame.Rect(1210, 58, 35, 22)


def procesar_eventos_volumen(estado: dict, eventos_frame: list) -> list:
    """
    Intercepta y procesa eventos de teclado o mouse relacionados con el volumen.
    Retorna una lista de eventos que deben ser removidos para evitar que otras pantallas los capturen.
    Implementa resiliencia y manejo robusto de excepciones de acuerdo a las reglas del usuario.
    """
    eventos_a_eliminar = []
    try:
        from alpha_football import audio
    except Exception as error_importacion:
        logger.error(f"No se pudo importar el modulo de audio al procesar eventos: {error_importacion}")
        # En caso de excepción, retornamos lista vacía como alternativa segura para asegurar continuidad
        return []

    for evento in eventos_frame:
        try:
            # v0.8: el widget de volumen flotante (con su botón "M") ya NO se dibuja, así que se
            # eliminan sus zonas de clic invisibles en la esquina superior derecha (mute/+/-),
            # que silenciaban la música sin querer. El volumen se controla desde Opciones y con
            # las teclas - / + ; ya no existe atajo de muteo (la tecla/botón M no mutea).

            # Procesamiento de teclas (- y + para control de volumen)
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    # Reducir volumen por teclado
                    nuevo_volumen = max(0.0, audio.CURRENT_VOLUME - 0.1)
                    audio.set_volume(nuevo_volumen)
                    eventos_a_eliminar.append(evento)
                elif evento.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    # Aumentar volumen por teclado
                    nuevo_volumen = min(1.0, audio.CURRENT_VOLUME + 0.1)
                    audio.set_volume(nuevo_volumen)
                    eventos_a_eliminar.append(evento)
                elif evento.key == pygame.K_s and (evento.mod & pygame.KMOD_SHIFT):
                    # Mayús+S: cambia de pista aleatoriamente (misma lógica que el fin de pista).
                    try:
                        audio.next_track()
                    except Exception as e_skip:
                        logger.debug(f"No se pudo cambiar de pista con Mayús+S: {e_skip}")
                    eventos_a_eliminar.append(evento)

        except Exception as error_evento:
            logger.error(f"Error al procesar un evento de volumen individual: {error_evento}. Continuando...")
            # En caso de error en un evento, no hacemos nada y continuamos para asegurar continuidad
            continue

    return eventos_a_eliminar


def renderizar_widget_volumen(screen: pygame.Surface) -> None:
    """
    Dibuja el widget de volumen en la esquina superior derecha con diseño premium.
    Incluye indicador de porcentaje, barra de progreso y botones con efectos de hover.
    Resistente a fallos de inicialización del sistema de audio o de recursos visuales.
    """
    try:
        from alpha_football.ui.theme import draw_panel, get_font, COLORS
        from alpha_football import audio
    except Exception as error_carga:
        logger.error(f"Error al cargar modulos para dibujar volumen: {error_carga}")
        # En caso de fallo de dependencias, no dibujamos para no colgar la renderización
        return

    try:
        # 1. Dibujar el panel contenedor con diseño unificado
        draw_panel(screen, RECT_PANEL_VOLUMEN)
        
        # 2. Determinar porcentaje de volumen y preparar el texto
        try:
            volumen_actual = getattr(audio, 'CURRENT_VOLUME', 0.5)
        except Exception:
            volumen_actual = 0.5
            
        porcentaje_vol = int(volumen_actual * 100)
        texto_volumen = "MUTED" if porcentaje_vol == 0 else f"VOL: {porcentaje_vol}%"
        
        # 3. Renderizar el texto de volumen
        try:
            fuente_sm = get_font('sm')
            color_texto = (255, 215, 0) if porcentaje_vol > 0 else (255, 68, 68)  # Dorado si activo, Rojo si mutado
            superficie_texto = fuente_sm.render(texto_volumen, True, color_texto)
            rect_texto = superficie_texto.get_rect(center=(RECT_PANEL_VOLUMEN.centerx, RECT_PANEL_VOLUMEN.top + 15))
            screen.blit(superficie_texto, rect_texto)
        except Exception as error_texto:
            logger.error(f"Error al renderizar texto del volumen: {error_texto}")
            
        # 4. Dibujar la barra de progreso de volumen
        try:
            # Fondo de la barra (gris oscuro)
            pygame.draw.rect(screen, (40, 50, 75), RECT_BARRA_VOLUMEN, border_radius=2)
            # Relleno de la barra (azul celeste o verde neón si tiene volumen)
            ancho_relleno = int(RECT_BARRA_VOLUMEN.width * volumen_actual)
            if ancho_relleno > 0:
                rect_relleno = pygame.Rect(RECT_BARRA_VOLUMEN.left, RECT_BARRA_VOLUMEN.top, ancho_relleno, RECT_BARRA_VOLUMEN.height)
                color_relleno = COLORS.get('verde', (0, 255, 136)) if volumen_actual > 0.3 else COLORS.get('azul', (0, 191, 255))
                pygame.draw.rect(screen, color_relleno, rect_relleno, border_radius=2)
        except Exception as error_barra:
            logger.error(f"Error al dibujar barra de volumen: {error_barra}")
            
        # 5. Dibujar los mini botones interactivos
        try:
            posicion_mouse = pygame.mouse.get_pos()
            
            def dibujar_mini_boton(rect_boton, texto_boton):
                """Dibuja un botón con cambio de color dinámico al pasar el cursor (hover)."""
                try:
                    hover = rect_boton.collidepoint(posicion_mouse)
                    color_fondo = (30, 45, 75) if hover else (20, 26, 46)
                    color_borde = COLORS.get('verde', (0, 255, 136)) if hover else COLORS.get('azul', (0, 191, 255))
                    color_texto = COLORS.get('verde', (0, 255, 136)) if hover else (255, 255, 255)
                    
                    try:
                        pygame.draw.rect(screen, color_fondo, rect_boton, border_radius=4)
                        pygame.draw.rect(screen, color_borde, rect_boton, width=1, border_radius=4)
                    except TypeError:
                        # Resiliencia si pygame es antiguo y no soporta border_radius en rect
                        pygame.draw.rect(screen, color_fondo, rect_boton)
                        pygame.draw.rect(screen, color_borde, rect_boton, width=1)
                        
                    superficie_btn = fuente_sm.render(texto_boton, True, color_texto)
                    rect_btn_txt = superficie_btn.get_rect(center=rect_boton.center)
                    screen.blit(superficie_btn, rect_btn_txt)
                except Exception as error_interno_btn:
                    logger.error(f"Fallo al dibujar botón '{texto_boton}': {error_interno_btn}")

            dibujar_mini_boton(RECT_BOTON_MINUS, "-")
            dibujar_mini_boton(RECT_BOTON_MUTE, "M")
            dibujar_mini_boton(RECT_BOTON_PLUS, "+")
            
        except Exception as error_botones:
            logger.error(f"Error al procesar botones del widget de volumen: {error_botones}")

    except Exception as error_general:
        logger.critical(f"Excepción general no controlada en renderizar_widget_volumen: {error_general}")


def _dibujar_now_playing(screen: pygame.Surface, estado: dict) -> None:
    """
    Dibuja abajo, de forma breve, la canción que está sonando y luego desaparece sola.
    El temporizador vive en el estado (now_playing_until); si ya venció, no dibuja nada.
    """
    try:
        until = estado.get('now_playing_until', 0)
        texto = estado.get('now_playing_text', "")
        if not texto or pygame.time.get_ticks() > until:
            return

        from alpha_football.ui.theme import get_font, COLORS

        etiqueta = f"♪ Sonando: {texto}"
        if len(etiqueta) > 60:
            etiqueta = etiqueta[:57] + "…"

        fuente = get_font('sm')
        color_verde = COLORS.get('verde', (0, 255, 136))
        superficie = fuente.render(etiqueta, True, color_verde)

        ancho = superficie.get_width() + 30
        alto = 34
        x = (SCREEN_W - ancho) // 2
        y = SCREEN_H - alto - 16

        # Panel translúcido para que el texto se lea sobre cualquier pantalla.
        try:
            panel = pygame.Surface((ancho, alto), pygame.SRCALPHA)
            panel.fill((10, 14, 26, 205))
            screen.blit(panel, (x, y))
            pygame.draw.rect(screen, color_verde, pygame.Rect(x, y, ancho, alto), width=1, border_radius=8)
        except Exception:
            pass

        screen.blit(superficie, (x + 15, y + 8))
    except Exception as error_now_playing:
        logger.error(f"Error al dibujar el aviso de canción actual: {error_now_playing}")


def _dibujar_oferta_toast(screen: pygame.Surface, estado: dict) -> None:
    """Aviso breve ARRIBA cuando llega una nueva oferta (se gestiona en la sección Ofertas)."""
    try:
        until = estado.get('oferta_toast_until', 0)
        texto = estado.get('oferta_toast_text', "")
        if not texto or pygame.time.get_ticks() > until:
            return
        from alpha_football.ui.theme import get_font, COLORS
        etiqueta = f"$ {texto}  —  ve a OFERTAS"
        if len(etiqueta) > 70:
            etiqueta = etiqueta[:67] + "…"
        fuente = get_font('sm')
        color = COLORS.get('dorado', (255, 215, 0))
        superficie = fuente.render(etiqueta, True, color)
        ancho = superficie.get_width() + 30
        alto = 36
        x = (SCREEN_W - ancho) // 2
        y = 16
        try:
            panel = pygame.Surface((ancho, alto), pygame.SRCALPHA)
            panel.fill((10, 14, 26, 220))
            screen.blit(panel, (x, y))
            pygame.draw.rect(screen, color, pygame.Rect(x, y, ancho, alto), width=2, border_radius=8)
        except Exception:
            pass
        screen.blit(superficie, (x + 15, y + 9))
    except Exception as e_toast:
        logger.error(f"Error al dibujar el aviso de oferta: {e_toast}")


# --- Bucle Principal ══════════════════════════════════════════════════════════

def main():
    try:
        # Buffer de audio GRANDE antes de inicializar: el buffer por defecto de pygame
        # (512 muestras) provoca underruns y CORTA las canciones antes de terminar. 4096
        # da reproducción estable de MP3 completos. pre_init debe ir ANTES de pygame.init().
        try:
            pygame.mixer.pre_init(44100, -16, 2, 4096)
        except Exception as e_preinit:
            logger.warning(f"No se pudo prefijar el buffer de audio: {e_preinit}")

        # Inicialización de Pygame
        pygame.init()
        pygame.font.init()
        
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Alpha Football v0.4")
        clock = pygame.time.Clock()
        
        # Estado inicial vacío de la sesión
        estado = {
            'current_screen': 'menu',
            'liga': None,
            'mi_equipo': None,
            'equipos': [],
            'temporada': 1,
            'jornada': 1,
            'copas': [],
            'transfer_log': [],
            'fichajes_realizados': 0,
            'audio_activado': True,
            'volumen': 0.5
        }
        
        # Inicializar música de fondo
        try:
            from alpha_football import audio
            audio.init_audio()
            audio.start_music()
            logger.info("Música de fondo iniciada.")
        except Exception as e_audio:
            logger.warning(f"No se pudo inicializar la música: {e_audio}. El juego correrá en silencio.")

        # Importar los renderers de pantalla UNA SOLA VEZ (antes se hacía `from ... import`
        # dentro del bucle, en cada frame). Se cargan tras pygame.init() para evitar problemas
        # de orden de inicialización.
        PANTALLAS = {}
        try:
            from alpha_football.ui.menu import render as menu_render
            from alpha_football.ui.league_screen import render as league_render
            from alpha_football.ui.match_screen import render as match_render
            from alpha_football.ui.market_screen import render as market_render
            from alpha_football.ui.copa_screen import render as copa_render
            from alpha_football.ui.career_screen import render as career_render
            from alpha_football.ui.team_screen import render as team_render
            from alpha_football.ui.options_screen import render as options_render
            from alpha_football.ui.prepartido_screen import render as prepartido_render
            from alpha_football.ui.ofertas_screen import render as ofertas_render
            from alpha_football.ui.stats_screen import render as stats_render
            from alpha_football.ui.save_slots_screen import render as save_slots_render
            from alpha_football.ui.resumen_temporada_screen import render as resumen_temporada_render
            from alpha_football.ui.edit_screen import render as edit_render
            PANTALLAS = {
                'menu': menu_render,
                'league_screen': league_render,
                'match_screen': match_render,
                'market_screen': market_render,
                'copa_screen': copa_render,
                'career_screen': career_render,
                'team_screen': team_render,
                'options_screen': options_render,
                'prepartido_screen': prepartido_render,
                'ofertas_screen': ofertas_render,
                'stats_screen': stats_render,
                'save_slots_screen': save_slots_render,
                'resumen_temporada_screen': resumen_temporada_render,
                'edit_screen': edit_render,
            }
        except Exception as e_import_pantallas:
            logger.critical(f"No se pudieron importar las pantallas del juego: {e_import_pantallas}", exc_info=True)

        running = True
        while running:
            try:
                from alpha_football import market
                market.ACTIVE_ESTADO = estado
            except Exception:
                pass
            # Consumir y cachear todos los eventos acumulados al inicio del frame
            try:
                global _cached_frame_events
                _cached_frame_events = _original_event_get()
            except Exception as e_events_cache:
                logger.error(f"Error al actualizar la cola de eventos del frame: {e_events_cache}")
                _cached_frame_events = []

            # 0. Atajos globales de volumen (+/-/M). Se SUPRIMEN en la pantalla de Opciones,
            #    que tiene sus propios controles y un campo de texto (la URL podría contener -, +, =).
            if estado.get('current_screen') != 'options_screen':
                try:
                    eventos_a_eliminar = procesar_eventos_volumen(estado, _cached_frame_events)
                    for ev in eventos_a_eliminar:
                        _cached_frame_events.remove(ev)
                except Exception as e_vol_click:
                    logger.error(f"Error al procesar clics o teclas de volumen: {e_vol_click}")

            # 1. Gestionar el tipo de pantalla actual
            current_screen = estado.get('current_screen', 'menu')
            
            # 2. Despachar a la UI correspondiente (renderers ya importados una sola vez)
            next_screen = None
            try:
                render_fn = PANTALLAS.get(current_screen)
                if render_fn is not None:
                    next_screen = render_fn(screen, estado)
                else:
                    logger.error(f"Pantalla desconocida: {current_screen}. Redirigiendo al menú.")
                    estado['current_screen'] = 'menu'
            except Exception as render_err:
                logger.error(f"Error renderizando pantalla '{current_screen}': {render_err}", exc_info=True)
                # Volvemos a league_screen o menú si algo explota
                estado['current_screen'] = 'menu' if current_screen == 'menu' else 'league_screen'
            
            # 3. Transicionar o salir según la respuesta de la pantalla
            if next_screen:
                if next_screen == 'volver':
                    estado['current_screen'] = 'league_screen'
                elif next_screen == 'quit':
                    running = False
                elif next_screen == 'menu':
                    estado['current_screen'] = 'menu'
                else:
                    estado['current_screen'] = next_screen
                    
            # 4. Manejo global de eventos para música y cierre de ventana
            # Leemos la cola de eventos si es que las pantallas dejaron alguno (p.ej. QUIT)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                # Gestionamos eventos de fin de pista del reproductor de audio
                try:
                    from alpha_football import audio
                    audio.check_music_event(event.type)
                except Exception:
                    pass
                    
            # Fase 7: el widget de volumen flotante se retiró de todas las pantallas;
            # el control de volumen vive ahora en la pantalla de Opciones (atajos +/-/M siguen activos).

            # Aviso de "sonando ahora": al cambiar de canción aparece abajo unos segundos y se oculta solo.
            try:
                from alpha_football import audio as _audio_np
                if _audio_np.hay_cancion_nueva():
                    nombre_cancion = _audio_np.cancion_actual()
                    if nombre_cancion:
                        estado['now_playing_text'] = nombre_cancion
                        estado['now_playing_until'] = pygame.time.get_ticks() + 6000  # visible 6 s
                _dibujar_now_playing(screen, estado)
            except Exception as e_now_playing:
                logger.debug(f"No se pudo mostrar el aviso de canción: {e_now_playing}")

            # Aviso de NUEVA OFERTA recibida (toast arriba). Las ofertas se gestionan en Ofertas.
            try:
                ofs = estado.get('ofertas_recibidas', []) or []
                if len(ofs) > estado.get('_ofertas_prev_count', 0):
                    nueva = ofs[-1]
                    jug = nueva.get('jugador') if isinstance(nueva, dict) else None
                    monto = nueva.get('monto', 0) if isinstance(nueva, dict) else 0
                    if jug is not None:
                        estado['oferta_toast_text'] = f"{monto:,} por {getattr(jug, 'nombre_completo', 'jugador')}"
                        estado['oferta_toast_until'] = pygame.time.get_ticks() + 7000
                estado['_ofertas_prev_count'] = len(ofs)
                _dibujar_oferta_toast(screen, estado)
            except Exception as e_toast:
                logger.debug(f"No se pudo mostrar el aviso de oferta: {e_toast}")

            pygame.display.flip()
            clock.tick(FPS)
            
        # Al salir del bucle, guardar partida y detener audio
        logger.info("Cerrando el juego...")
        guardar_al_salir(estado)
        
        try:
            from alpha_football import audio
            audio.stop_music()
        except Exception:
            pass
            
        pygame.quit()
        sys.exit()
        
    except Exception as e_main:
        logger.critical(f"Fallo catastrófico en la ejecución del juego: {e_main}", exc_info=True)
        pygame.quit()
        sys.exit(1)

if __name__ == "__main__":
    main()
