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
                # Buffer grande (4096) para que los MP3 suenen COMPLETOS (evita underruns que
                # cortan la canción). Si pygame.init() ya inicializó el mixer, esto se omite.
                try:
                    pygame.mixer.pre_init(44100, -16, 2, 4096)
                except Exception:
                    pass
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

# Manifiesto de URLs ya descargadas (por URL, NO por nombre de archivo) para que
# renombrar las pistas no provoque que se vuelvan a descargar como pista_N.
_MANIFEST_PATH = os.path.join(MUSIC_DIR, ".descargas.json")
_EXT_AUDIO = (".mp3", ".wav", ".ogg", ".m4a", ".webm", ".opus")


def _cargar_manifest_descargas() -> set:
    """Lee el conjunto de URLs ya descargadas; vacío si no existe/ilegible."""
    import json
    try:
        if os.path.exists(_MANIFEST_PATH):
            with open(_MANIFEST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return set(data)
    except Exception as e:
        logger.warning(f"No se pudo leer el manifiesto de descargas: {e}")
    return set()


def _guardar_manifest_descargas(urls: set) -> None:
    """Guarda el conjunto de URLs ya descargadas (fail-soft)."""
    import json
    try:
        os.makedirs(MUSIC_DIR, exist_ok=True)
        with open(_MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(urls), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"No se pudo guardar el manifiesto de descargas: {e}")


def _hay_audio_en_carpeta() -> bool:
    """True si ya hay al menos un archivo de audio en la carpeta de música."""
    try:
        return any(f.lower().endswith(_EXT_AUDIO) for f in os.listdir(MUSIC_DIR))
    except Exception:
        return False


def _descargar_musica() -> None:
    """
    Descarga de forma silenciosa y asíncrona las canciones listadas en musica.txt.
    Usa un MANIFIESTO por URL para no re-descargar pistas que el usuario ya tiene
    (aunque las haya renombrado) y guarda con el NOMBRE REAL del tema.
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

        # Manifiesto: evita RE-CREAR pistas que ya se bajaron (clave = URL, no nombre de archivo).
        manifest = _cargar_manifest_descargas()
        if not os.path.exists(_MANIFEST_PATH):
            # Primera vez con esta lógica: si YA hay música en la carpeta, asumimos que estas
            # URLs ya se descargaron (el usuario pudo renombrarlas) y NO las volvemos a bajar.
            if _hay_audio_en_carpeta():
                manifest = set(urls)
                _guardar_manifest_descargas(manifest)
                logger.info("Manifiesto de música sembrado: no se re-descargan pistas existentes.")

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

        # Descargar SOLO las URLs que no estén en el manifiesto, con el nombre real del tema.
        out_pattern = os.path.join(MUSIC_DIR, "%(title)s.%(ext)s")
        for url in urls:
            if url in manifest:
                continue

            logger.info(f"Iniciando descarga de: {url}")
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
                logger.info("Descargada y convertida a MP3.")
                manifest.add(url)
                _guardar_manifest_descargas(manifest)
                _actualizar_playlist()
            except Exception as ffmpeg_err:
                logger.warning(
                    f"Fallo al convertir a MP3 (posiblemente falta FFmpeg): {ffmpeg_err}. "
                    f"Intentando descargar en formato original (m4a/webm/etc.)...."
                )
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
                    logger.info("Descargada exitosamente en formato de audio original.")
                    manifest.add(url)
                    _guardar_manifest_descargas(manifest)
                    _actualizar_playlist()
                except Exception as raw_err:
                    logger.error(f"Error critico al descargar ({url}) sin postprocesamiento: {raw_err}")

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


def descargar_por_nombre_async(nombre: str) -> None:
    """
    Descarga por NOMBRE de canción: yt-dlp busca el primer resultado en YouTube
    (`ytsearch1:<nombre>`) y lo baja. Reutiliza el worker de descarga por URL.
    """
    nombre = (nombre or "").strip()
    if not nombre:
        global _DOWNLOAD_STATUS
        _DOWNLOAD_STATUS = {"activo": False, "mensaje": "Escribe el nombre de la canción."}
        return
    descargar_url_async(f"ytsearch1:{nombre}")


# --- Búsqueda interactiva: mostrar resultados antes de descargar (para elegir) -----

# Estado y resultados de la última búsqueda por nombre (para que la UI los muestre).
_SEARCH_STATUS = {"activo": False, "mensaje": ""}
_SEARCH_RESULTS: list = []


def estado_busqueda() -> dict:
    """Estado de la búsqueda interactiva (activo + mensaje)."""
    return dict(_SEARCH_STATUS)


def resultados_busqueda() -> list:
    """Copia de los resultados de la última búsqueda: dicts {title, uploader, duration, url}."""
    return list(_SEARCH_RESULTS)


def limpiar_busqueda() -> None:
    """Borra los resultados (tras elegir uno o al iniciar otra búsqueda)."""
    global _SEARCH_RESULTS, _SEARCH_STATUS
    _SEARCH_RESULTS = []
    _SEARCH_STATUS = {"activo": False, "mensaje": ""}


def buscar_canciones_async(query: str, n: int = 5) -> None:
    """
    Busca en YouTube SIN descargar y deja hasta `n` resultados en _SEARCH_RESULTS para
    que el usuario elija cuál bajar. No bloquea la UI (hilo aparte). Resiliente.
    """
    global _SEARCH_STATUS, _SEARCH_RESULTS
    query = (query or "").strip()
    if not query:
        _SEARCH_STATUS = {"activo": False, "mensaje": "Escribe algo para buscar."}
        return
    if _SEARCH_STATUS.get("activo"):
        return  # ya hay una búsqueda en curso
    _SEARCH_RESULTS = []
    _SEARCH_STATUS = {"activo": True, "mensaje": "Buscando…"}

    def _worker(q: str) -> None:
        global _SEARCH_STATUS, _SEARCH_RESULTS
        try:
            try:
                import yt_dlp
            except ImportError:
                if _intentar_instalar_ytdlp():
                    import yt_dlp
                else:
                    _SEARCH_STATUS = {"activo": False, "mensaje": "yt-dlp no disponible."}
                    return
            opts = {
                "quiet": True, "no_warnings": True, "skip_download": True,
                "extract_flat": True, "noplaylist": True,
                "default_search": "ytsearch", "socket_timeout": SOCKET_TIMEOUT,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch{int(n)}:{q}", download=False)
            entries = (info or {}).get("entries", []) or []
            resultados = []
            for e in entries:
                if not e:
                    continue
                vid = e.get("id") or ""
                url = e.get("url") or e.get("webpage_url") or vid
                if url and not str(url).startswith("http"):
                    url = f"https://www.youtube.com/watch?v={url}"
                if not url:
                    continue
                resultados.append({
                    "title": e.get("title") or "Sin título",
                    "uploader": e.get("uploader") or e.get("channel") or "",
                    "duration": e.get("duration"),
                    "url": url,
                })
            _SEARCH_RESULTS = resultados
            _SEARCH_STATUS = {"activo": False,
                              "mensaje": f"{len(resultados)} resultados — elige uno." if resultados else "Sin resultados."}
        except Exception as ex:
            logger.error(f"Error al buscar canciones '{q}': {ex}")
            _SEARCH_STATUS = {"activo": False, "mensaje": "Falló la búsqueda."}

    threading.Thread(target=_worker, args=(query,), daemon=True).start()


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

        # v0.8.5: idempotente DE VERDAD. Una vez que la música arrancó (IS_PLAYING=True), el avance
        # de pista lo maneja EXCLUSIVAMENTE el end-event (USEREVENT+100) o next_track(). Antes el
        # guard exigía también get_busy()==True; en el hueco entre pistas (get_busy momentáneamente
        # False) una nueva llamada a start_music disparaba _reproducir_siguiente y chocaba con el
        # end-event natural, cortando la pista recién iniciada.
        if IS_PLAYING:
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

# v0.8.3 (F2): cola de canciones. Mantiene un set de las canciones ya reproducidas
# en el ciclo actual; cuando se han reproducido TODAS, se resetea y empieza un
# nuevo ciclo. Al cambiar manualmente (next_track / Mayús+S) también se resetea.
_HISTORIAL_CICLO: set[str] = set()


def reset_cola_musica() -> None:
    """Limpia el historial del ciclo actual (v0.8.3). Llamar tras cambios manuales."""
    global _HISTORIAL_CICLO
    _HISTORIAL_CICLO = set()

# "Sonando ahora": nombre legible de la pista actual y bandera de que cambió la canción,
# para que la UI muestre un aviso breve abajo y luego lo oculte sola.
_CURRENT_TRACK_NAME: str = ""
_TRACK_CHANGED: bool = False


def _titulo_legible(ruta: str) -> str:
    """
    Devuelve el NOMBRE REAL de la pista: usa el tag de título (ID3 vía mutagen si está
    disponible) y, si no, embellece el nombre de archivo (quita guiones bajos y sufijos
    tipo '(Video Oficial)'). Fail-soft: si algo falla, devuelve el nombre de archivo.
    """
    base = os.path.splitext(os.path.basename(ruta))[0]
    # 1) Intentar el título de los metadatos (mejor fuente). Mutagen es opcional.
    try:
        from mutagen import File as _MFile  # type: ignore
        mf = _MFile(ruta, easy=True)
        if mf:
            titulo = (mf.get("title") or [None])[0]
            if titulo:
                base = str(titulo)
    except Exception:
        pass
    # 2) Limpieza del nombre: guiones bajos -> espacios y quitar sufijos de YouTube.
    try:
        import re
        limpio = base.replace("_", " ").strip()
        limpio = re.sub(
            r"\s*[\(\[][^)\]]*(?:oficial|official|video|lyric|audio|hd|4k|mv|visualizer)[^)\]]*[\)\]]",
            "", limpio, flags=re.IGNORECASE,
        )
        limpio = limpio.strip(" -|·")
        return limpio or base
    except Exception:
        return base


def cancion_actual() -> str:
    """Devuelve el nombre legible (real) de la pista que está sonando."""
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
    """Carga y reproduce la siguiente pista disponible en la playlist.

    v0.8.3 (F2): ya no es 100% aleatoria — mantiene un set _HISTORIAL_CICLO con las
    canciones ya reproducidas en este ciclo. Cuando se han reproducido TODAS, resetea
    el set y empieza un nuevo ciclo. Así garantiza que el oyente escuche todas las
    canciones antes de que alguna se repita.
    """
    global PLAYLIST, _LAST_PLAYED_TRACK, _CURRENT_TRACK_NAME, _TRACK_CHANGED
    try:
        if not IS_PLAYING or not PLAYLIST:
            return

        # Resetear el ciclo si ya se han reproducido todas las canciones
        if len(_HISTORIAL_CICLO) >= len(PLAYLIST):
            _HISTORIAL_CICLO.clear()

        # Candidatas = canciones NO reproducidas aún en este ciclo.
        # Si solo queda 1 (la que se está reproduciendo ahora), la excluimos también
        # para no repetir la misma consecutivamente.
        candidatas = [p for p in PLAYLIST
                       if p not in _HISTORIAL_CICLO and p != _LAST_PLAYED_TRACK]
        if not candidatas:
            # Caso degenerado: solo 1 canción o todas recién reproducidas.
            candidatas = list(PLAYLIST)

        pista = random.choice(candidatas)
        _LAST_PLAYED_TRACK = pista
        _HISTORIAL_CICLO.add(pista)

        if os.path.exists(pista):
            pygame.mixer.music.load(pista)
            pygame.mixer.music.play()
            # Guardar el nombre REAL/legible y avisar a la UI de que cambió la canción.
            _CURRENT_TRACK_NAME = _titulo_legible(pista)
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
            _HISTORIAL_CICLO.discard(pista)  # v0.8.3: no contar pistas inválidas
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
    """Pasa manualmente a la siguiente pista de música.

    v0.8.3 (F2): al hacer cambio manual, se resetea el ciclo para que el orden
    sea fresco a partir de la elección del usuario (si el usuario salta a "track 3"
    el ciclo empieza de nuevo desde ahí).
    """
    try:
        # v0.8.3: cambio manual = resetear ciclo
        reset_cola_musica()
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


def eliminar_pista(ruta: str) -> None:
    """
    Elimina físicamente la pista de audio de disco y actualiza la playlist.
    Si la canción a borrar es la que está sonando actualmente, la avanza primero.
    Libera el archivo de pygame.mixer.music.unload() para evitar bloqueos en Windows.
    """
    global PLAYLIST, _LAST_PLAYED_TRACK
    try:
        norm_ruta = os.path.normpath(ruta)
        # Si es la que está sonando, avanzamos pista
        if norm_ruta == os.path.normpath(_LAST_PLAYED_TRACK or ""):
            next_track()
            
        # Intentamos borrar directamente
        try:
            if os.path.exists(norm_ruta):
                os.remove(norm_ruta)
        except OSError:
            # En Windows, si el mixer tiene cargado el archivo, está bloqueado.
            # Forzamos una parada, descargamos la pista cargada y borramos.
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            if os.path.exists(norm_ruta):
                os.remove(norm_ruta)
            
            # Si estaba reproduciéndose música, reanudamos
            if IS_PLAYING:
                _actualizar_playlist()
                _reproducir_siguiente()
                
        # Actualizamos la playlist local
        _actualizar_playlist()
        logger.info(f"Canción eliminada de disco: {norm_ruta}")
    except Exception as e:
        logger.error(f"Error al intentar eliminar la canción {ruta}: {e}")

