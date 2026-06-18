# -*- coding: utf-8 -*-
"""
Alpha Football v0.4 — SISTEMA DE AUDIO.

Gestiona la música de fondo utilizando pygame.mixer.
Lee las URLs de musica.txt y descarga el audio usando yt-dlp de forma asíncrona.
Garantiza el silencio absoluto si hay fallos (resiliencia).
"""

from __future__ import annotations

import os
import sys
import random
import logging
import threading
import subprocess
from typing import Optional
import pygame

# Configuración del logger
logger = logging.getLogger(__name__)

# Definición de la ruta raíz y la carpeta de música de forma absoluta
# para evitar problemas al ejecutar el juego desde distintos directorios
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.normpath(os.path.join(PROJECT_ROOT, "music"))

PLAYLIST: list[str] = []
CURRENT_VOLUME = 0.5
IS_PLAYING = False
_DOWNLOAD_THREAD_STARTED = False

# Timeout de socket para descargas de musica (segundos)
SOCKET_TIMEOUT = 15

def init_audio() -> None:
    """
    Inicializa el mixer de pygame y crea el directorio de música si no existe.
    Inicia la descarga de pistas en segundo plano de forma asíncrona.
    """
    global _DOWNLOAD_THREAD_STARTED
    try:
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e_mix:
                logger.warning(f"No se pudo inicializar pygame.mixer directamente: {e_mix}. Inicializando pygame completo...")
                pygame.init()
        
        # Crear carpeta de música si no existe en el root del proyecto
        if not os.path.exists(MUSIC_DIR):
            os.makedirs(MUSIC_DIR)
            
        _actualizar_playlist()
        
        # Iniciar hilo secundario de descarga solo una vez para no duplicar descargas
        if not _DOWNLOAD_THREAD_STARTED:
            _DOWNLOAD_THREAD_STARTED = True
            hilo_descarga = threading.Thread(target=_descargar_musica, daemon=True)
            hilo_descarga.start()
    except Exception as e:
        logger.error(f"Error al inicializar el audio: {e}. El juego correra en silencio de forma resiliente.")


def _actualizar_playlist() -> None:
    """
    Escanea el directorio absoluto de música en busca de archivos de audio reproducibles
    y los almacena en orden aleatorio (shuffle).
    """
    global PLAYLIST
    try:
        if os.path.exists(MUSIC_DIR):
            # Formatos de audio soportados por pygame.mixer.music
            extensiones = (".mp3", ".wav", ".ogg", ".m4a")
            PLAYLIST = [
                os.path.normpath(os.path.join(MUSIC_DIR, f))
                for f in os.listdir(MUSIC_DIR)
                if f.lower().endswith(extensiones)
            ]
            random.shuffle(PLAYLIST)
            logger.info(f"Playlist actualizada: {len(PLAYLIST)} pistas encontradas en {MUSIC_DIR}.")
    except Exception as e:
        logger.error(f"Error al escanear la carpeta de musica en {MUSIC_DIR}: {e}")

def _intentar_instalar_ytdlp() -> bool:
    """
    Intenta instalar la librería de python yt-dlp usando pip de forma automática.
    Retorna True si tiene éxito, de lo contrario False.
    """
    try:
        logger.info("Intentando instalar yt-dlp usando pip de forma automatica...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "yt-dlp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        logger.info("yt-dlp instalado exitosamente via pip.")
        return True
    except Exception as error_inst:
        logger.error(f"No se pudo instalar yt-dlp mediante subprocess: {error_inst}")
        return False

def _descargar_musica() -> None:
    """
    Descarga de forma silenciosa y asíncrona las canciones listadas en musica.txt.
    Usa la biblioteca yt-dlp para mayor estabilidad, instalándola si es necesario.
    """
    try:
        musica_txt_path = os.path.join(PROJECT_ROOT, "musica.txt")
        if not os.path.exists(musica_txt_path):
            logger.warning(f"No se encontro el archivo de canciones: {musica_txt_path}")
            return

        with open(musica_txt_path, "r", encoding="utf-8") as file:
            urls = [line.strip() for line in file if line.strip() and not line.strip().startswith("#")]

        if not urls:
            logger.info("El archivo musica.txt esta vacio.")
            return

        # Importamos yt_dlp dinámicamente o intentamos su instalación si no está
        try:
            import yt_dlp
        except ImportError:
            exito_inst = _intentar_instalar_ytdlp()
            if exito_inst:
                try:
                    import yt_dlp
                except ImportError as e_reimport:
                    logger.error(f"Aunque la instalacion reporto exito, fallo al importar yt-dlp: {e_reimport}")
                    return
            else:
                logger.error("No se pudo obtener yt-dlp. Las descargas de musica estan deshabilitadas.")
                return

        # Procesar y descargar cada URL de la lista
        for i, url in enumerate(urls):
            # Comprobar si ya existe algún archivo con el prefijo pista_i en cualquier formato admitido
            ya_existe = False
            for ext in [".mp3", ".wav", ".ogg", ".m4a", ".webm"]:
                if os.path.exists(os.path.join(MUSIC_DIR, f"pista_{i+1}{ext}")):
                    ya_existe = True
                    break
            
            if ya_existe:
                continue

            logger.info(f"Iniciando descarga de pista {i+1}: {url}")
            
            # 1. Opción recomendada: Descarga y conversión a MP3 con FFmpeg
            out_pattern = os.path.join(MUSIC_DIR, f"pista_{i+1}.%(ext)s")
            ydl_opts_mp3 = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': out_pattern,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'socket_timeout': SOCKET_TIMEOUT,
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts_mp3) as ydl:
                    ydl.download([url])
                logger.info(f"Pista {i+1} descargada y convertida a MP3.")
                _actualizar_playlist()
            except Exception as ffmpeg_err:
                logger.warning(
                    f"Fallo al convertir a MP3 (posiblemente falta FFmpeg): {ffmpeg_err}. "
                    f"Intentando descargar en formato original (m4a/webm/etc.)...."
                )
                # 2. Alternativa: Descargar en formato original directo sin FFmpeg
                ydl_opts_raw = {
                    'format': 'bestaudio/best',
                    'outtmpl': out_pattern,
                    'quiet': True,
                    'no_warnings': True,
                    'noplaylist': True,
                    'socket_timeout': SOCKET_TIMEOUT,
                }
                try:
                    with yt_dlp.YoutubeDL(ydl_opts_raw) as ydl:
                        ydl.download([url])
                    logger.info(f"Pista {i+1} descargada exitosamente en formato de audio original.")
                    _actualizar_playlist()
                except Exception as raw_err:
                    logger.error(f"Error critico al descargar pista {i+1} ({url}) sin postprocesamiento: {raw_err}")

    except Exception as e:
        logger.error(f"Error inesperado en el modulo de descarga de musica: {e}")

# --- Fase 7: importador interactivo de música (YouTube) + preferencias --------

# Estado simple de la descarga interactiva para que la UI muestre feedback sin bloquearse.
_DOWNLOAD_STATUS = {"activo": False, "mensaje": ""}

def estado_descarga() -> dict:
    """Devuelve una copia del estado de la última/actual descarga interactiva."""
    return dict(_DOWNLOAD_STATUS)

def descargar_url_async(url: str) -> None:
    """
    Descarga UNA URL de YouTube en un hilo aparte (no bloquea la UI). Resiliente:
    intenta MP3 (FFmpeg) y cae a formato original; si yt-dlp falla, silencio funcional.
    """
    global _DOWNLOAD_STATUS
    url = (url or "").strip()
    if not url:
        _DOWNLOAD_STATUS = {"activo": False, "mensaje": "Pega una URL válida."}
        return
    if _DOWNLOAD_STATUS.get("activo"):
        return  # ya hay una descarga en curso

    def _worker(target_url: str) -> None:
        global _DOWNLOAD_STATUS
        _DOWNLOAD_STATUS = {"activo": True, "mensaje": "Descargando…"}
        try:
            try:
                import yt_dlp
            except ImportError:
                if _intentar_instalar_ytdlp():
                    import yt_dlp
                else:
                    _DOWNLOAD_STATUS = {"activo": False, "mensaje": "yt-dlp no disponible."}
                    return
            os.makedirs(MUSIC_DIR, exist_ok=True)
            out_pattern = os.path.join(MUSIC_DIR, "%(title)s.%(ext)s")
            opts = {
                'format': 'bestaudio/best',
                'outtmpl': out_pattern,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'socket_timeout': SOCKET_TIMEOUT,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([target_url])
            except Exception as ffmpeg_err:
                logger.warning(f"Descarga MP3 falló ({ffmpeg_err}); intentando formato original…")
                opts.pop('postprocessors', None)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([target_url])
            _actualizar_playlist()
            _DOWNLOAD_STATUS = {"activo": False, "mensaje": "¡Listo! Pista agregada a la música."}
        except Exception as e:
            logger.error(f"Error al descargar la URL '{target_url}': {e}")
            _DOWNLOAD_STATUS = {"activo": False, "mensaje": "Falló la descarga (el juego sigue normal)."}

    threading.Thread(target=_worker, args=(url,), daemon=True).start()


# Preferencias persistentes (volumen, música activada, liga por defecto).
_PREFS_PATH = os.path.join(PROJECT_ROOT, "preferencias.json")
_PREFS_DEFECTO = {"volumen": 0.5, "musica_activada": True, "liga_por_defecto": None}

def cargar_preferencias() -> dict:
    """Lee las preferencias del usuario; devuelve los valores por defecto si no existen/ilegibles."""
    import json
    prefs = dict(_PREFS_DEFECTO)
    try:
        if os.path.exists(_PREFS_PATH):
            with open(_PREFS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                prefs.update({k: data[k] for k in _PREFS_DEFECTO if k in data})
    except Exception as e:
        logger.warning(f"No se pudieron leer las preferencias: {e}")
    return prefs

def guardar_preferencias(prefs: dict) -> None:
    """Guarda las preferencias del usuario (fail-soft)."""
    import json
    try:
        actual = cargar_preferencias()
        actual.update({k: v for k, v in (prefs or {}).items() if k in _PREFS_DEFECTO})
        with open(_PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(actual, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"No se pudieron guardar las preferencias: {e}")


def start_music() -> None:
    """Arranca la reproducción de música en modo aleatorio si no está sonando."""
    global IS_PLAYING
    try:
        if not pygame.mixer.get_init():
            return
            
        if not PLAYLIST:
            _actualizar_playlist()
            if not PLAYLIST:
                logger.info("No hay pistas de musica disponibles en la lista de reproduccion.")
                return

        IS_PLAYING = True
        pygame.mixer.music.set_volume(CURRENT_VOLUME)
        _reproducir_siguiente()
    except Exception as e:
        logger.error(f"Error al iniciar reproduccion de musica: {e}")

_LAST_PLAYED_TRACK: str | None = None

# "Sonando ahora": nombre legible de la pista actual y bandera de que cambió la canción,
# para que la UI muestre un aviso breve abajo y luego lo oculte sola.
_CURRENT_TRACK_NAME: str = ""
_TRACK_CHANGED: bool = False


def cancion_actual() -> str:
    """Devuelve el nombre legible de la pista que está sonando (sin ruta ni extensión)."""
    return _CURRENT_TRACK_NAME


def hay_cancion_nueva() -> bool:
    """
    True una sola vez cuando empezó a sonar una pista nueva (consume la bandera).
    La UI lo usa para mostrar el aviso de 'sonando ahora' justo al cambiar de canción.
    """
    global _TRACK_CHANGED
    if _TRACK_CHANGED:
        _TRACK_CHANGED = False
        return True
    return False


def _reproducir_siguiente() -> None:
    """Carga y reproduce la siguiente pista disponible en la playlist eligiéndola de forma aleatoria."""
    global PLAYLIST, _LAST_PLAYED_TRACK, _CURRENT_TRACK_NAME, _TRACK_CHANGED
    try:
        if not IS_PLAYING or not PLAYLIST:
            return

        # Elegimos una pista al azar para no tener patrón de repetición,
        # evitando repetir la última pista reproducida si hay más de una.
        if len(PLAYLIST) > 1:
            candidatas = [p for p in PLAYLIST if p != _LAST_PLAYED_TRACK]
            pista = random.choice(candidatas)
        else:
            pista = PLAYLIST[0]

        _LAST_PLAYED_TRACK = pista

        if os.path.exists(pista):
            pygame.mixer.music.load(pista)
            pygame.mixer.music.play()
            # Guardar el nombre legible y avisar a la UI de que cambió la canción.
            _CURRENT_TRACK_NAME = os.path.splitext(os.path.basename(pista))[0]
            _TRACK_CHANGED = True
            logger.info(f"Reproduciendo pista: {pista}")
            # Definir un evento personalizado para indicar el final de la pista
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 100)
        else:
            logger.warning(f"La pista {pista} no existe fisicamente. Pasando a la siguiente...")
            try:
                PLAYLIST.remove(pista)
            except ValueError:
                pass
            _reproducir_siguiente()
    except Exception as e:
        logger.error(f"Error al cargar/reproducir pista: {e}. Intentando con la siguiente pista de forma resiliente.")
        if len(PLAYLIST) > 1:
            _reproducir_siguiente()

def check_music_event(event_type: int) -> None:
    """Avanza la canción cuando detecta el evento de finalización."""
    if event_type == pygame.USEREVENT + 100:
        _reproducir_siguiente()

def next_track() -> None:
    """Pasa manualmente a la siguiente pista de música."""
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            _reproducir_siguiente()
    except Exception as e:
        logger.error(f"Error al avanzar a la siguiente pista: {e}")

def set_volume(volumen: float) -> None:
    """Ajusta el volumen global de la música de forma segura."""
    global CURRENT_VOLUME
    try:
        CURRENT_VOLUME = max(0.0, min(1.0, volumen))
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(CURRENT_VOLUME)
    except Exception as e:
        logger.error(f"Error al cambiar volumen de musica: {e}")

def stop_music() -> None:
    """Detiene por completo la reproducción de la música."""
    global IS_PLAYING
    try:
        IS_PLAYING = False
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception as e:
        logger.error(f"Error al detener la musica: {e}")
