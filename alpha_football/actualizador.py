# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Auto-actualización (v0.4.15.0)
Al abrir el juego se compara el archivo VERSION con el de GitHub (rama main). Si hay una versión nueva:
- copia bajada como ZIP (sin .git): baja el ZIP de main, lo valida, lo descomprime en una carpeta temporal
  y copia los archivos encima;
- copia git limpia: git pull --ff-only;
- copia git con cambios sin commitear o commits sin subir: no instala, solo avisa en el menú.
Nunca se pisan los datos del jugador (PROTEGIDOS). Sin red o con cualquier error se sigue jugando: queda
en el log. Las únicas puertas al exterior son _descargar (red) y _git: los tests las reemplazan.
Sin UI: main.py llama a al_iniciar() una vez, con la ventana creada y antes del menú.
"""
from __future__ import annotations

import io
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable, Optional

logger = logging.getLogger(__name__)

REPO, RAMA = "dajaramilc/AlphaFootball", "main"
URL_VERSION = f"https://raw.githubusercontent.com/{REPO}/{RAMA}/VERSION"
URL_ZIP = f"https://github.com/{REPO}/archive/refs/heads/{RAMA}.zip"
ESPERA_CONSULTA, ESPERA_DESCARGA = 4, 60          # segundos
MAX_BYTES_ZIP = 300 * 1024 * 1024                 # descomprimido: tope contra un ZIP dañado o malicioso
# Datos del jugador: nunca se pisan (carpetas o archivos de la raíz; los prefijos cubren .bak y .tmp)
PROTEGIDOS = ('saves', 'music', 'preferencias.json', 'musica.txt', 'alpha_football_edited_db.json',
              'alpha_football_db_custom.json', 'context.md')
PREFIJOS_PROTEGIDOS = ('alpha_football_save.json',)


def raiz() -> Path:
    """La carpeta de instalación (donde están main.py y VERSION)."""
    return Path(__file__).resolve().parent.parent


# --- Versiones ────────────────────────────────────────────────────────────────

def version_valida(v) -> bool:
    return isinstance(v, str) and re.fullmatch(r"\d+(\.\d+){1,5}", v.strip()) is not None


def es_mayor(remota, local) -> bool:
    """¿`remota` es posterior a `local`? Número a número (0.4.10.0 > 0.4.9.2). Una remota ilegible nunca
    es mayor; contra una local ilegible (sin VERSION), cualquier remota válida lo es."""
    if not version_valida(remota):
        return False
    if not version_valida(local):
        return True
    a = tuple(int(x) for x in remota.strip().split('.'))
    b = tuple(int(x) for x in local.strip().split('.'))
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def version_local(carpeta: Optional[Path] = None) -> str:
    try:
        return (Path(carpeta or raiz()) / 'VERSION').read_text(encoding='utf-8').strip()
    except OSError as e:
        logger.warning(f"actualizador: no se pudo leer VERSION: {e}")
        return ''


# --- Consulta ─────────────────────────────────────────────────────────────────

def _descargar(url: str, espera: int) -> bytes:
    """Baja una URL https. Es la ÚNICA función que toca la red (los tests la reemplazan)."""
    import urllib.request
    if not url.startswith("https://"):
        raise ValueError(f"URL no permitida: {url}")
    with urllib.request.urlopen(url, timeout=espera) as respuesta:
        return respuesta.read()


def consultar(descargar: Optional[Callable] = None) -> Optional[str]:
    """La versión publicada en GitHub, o None si no hay red, tarda más de 4 s o la respuesta no es una
    versión (portal cautivo, 404…). Nunca lanza."""
    try:
        texto = (descargar or _descargar)(URL_VERSION, ESPERA_CONSULTA).decode('utf-8', 'replace').strip()
    except Exception as e:
        logger.info(f"actualizador: sin respuesta de GitHub ({e}); se sigue jugando")
        return None
    if not version_valida(texto):
        logger.warning("actualizador: la respuesta de GitHub no es una versión; se ignora")
        return None
    return texto


# --- Tipo de copia ────────────────────────────────────────────────────────────

def _git(carpeta: Path, *args: str) -> tuple:
    """(código de salida, salida) de un comando git en esa carpeta; (1, error) si git no está o no responde."""
    try:
        r = subprocess.run(['git', '-C', str(carpeta), *args], capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except Exception as e:
        return 1, str(e)


def tipo_copia(carpeta: Path, git: Optional[Callable] = None) -> str:
    """'zip' (sin .git), 'git_limpia' o 'git_sucia': cambios sin commitear, commits sin subir, sin rama
    remota o git que no responde. Ante la duda es 'git_sucia': no se toca nada."""
    carpeta = Path(carpeta)
    if not (carpeta / '.git').exists():
        return 'zip'
    git = git or _git
    rc, salida = git(carpeta, 'status', '--porcelain')
    if rc != 0 or salida.strip():
        return 'git_sucia'
    rc, salida = git(carpeta, 'rev-list', '--count', '@{u}..HEAD')
    if rc != 0 or salida.strip() != '0':
        return 'git_sucia'
    return 'git_limpia'


# --- ZIP ──────────────────────────────────────────────────────────────────────

_copiar_archivo = shutil.copy2        # la copia hacia la instalación (los tests la hacen fallar)


def protegido(rel: str) -> bool:
    """¿Esa ruta (relativa a la instalación) es un dato del jugador? Esos nunca se pisan."""
    partes = PurePosixPath(str(rel).replace('\\', '/')).parts
    return bool(partes) and (partes[0] in PROTEGIDOS or partes[0].startswith(PREFIJOS_PROTEGIDOS))


def _ruta_segura(nombre: str) -> bool:
    """¿Ese nombre del ZIP se queda dentro de la carpeta? Fuera: absolutas, con unidad, con '..' o con barra
    invertida."""
    if not nombre or '\\' in nombre or ':' in nombre or nombre.startswith('/'):
        return False
    return '..' not in PurePosixPath(nombre).parts


def validar_zip(datos: bytes, version: str) -> tuple:
    """(ok, motivo, prefijo). El ZIP debe traer main.py y un VERSION igual al consultado, y ninguna ruta
    puede salir de la carpeta. `prefijo` es la carpeta raíz del ZIP de GitHub ('AlphaFootball-main/')."""
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            nombres = z.namelist()
            if not nombres:
                return False, "el ZIP está vacío", ''
            if not all(_ruta_segura(n) for n in nombres):
                return False, "el ZIP trae rutas fuera de la carpeta del juego", ''
            if sum(i.file_size for i in z.infolist()) > MAX_BYTES_ZIP:
                return False, "el ZIP es demasiado grande", ''
            raices = {n.split('/', 1)[0] for n in nombres}
            prefijo = '' if 'main.py' in nombres or len(raices) != 1 else next(iter(raices)) + '/'
            for obligatorio in ('main.py', 'VERSION'):
                if prefijo + obligatorio not in nombres:
                    return False, f"al ZIP le falta {obligatorio}", ''
            dentro = z.read(prefijo + 'VERSION').decode('utf-8', 'replace').strip()
            if dentro != version:
                return False, f"el ZIP es de la versión {dentro!r} y se esperaba la {version}", ''
            return True, '', prefijo
    except Exception as e:
        return False, f"no es un ZIP válido: {e}", ''


def extraer(datos: bytes, prefijo: str, destino: Path) -> list:
    """Descomprime en `destino` (una carpeta temporal) los archivos del ZIP, sin su carpeta raíz.
    Devuelve las rutas relativas extraídas."""
    destino = Path(destino).resolve()
    rels = []
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        for info in z.infolist():
            rel = info.filename[len(prefijo):] if info.filename.startswith(prefijo) else ''
            if info.is_dir() or not rel:
                continue
            final = (destino / rel).resolve()
            if destino not in final.parents:                 # defensa en profundidad: validar_zip ya lo filtró
                raise ValueError(f"ruta fuera de la carpeta temporal: {info.filename}")
            final.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as origen, open(final, 'wb') as salida:
                shutil.copyfileobj(origen, salida)
            rels.append(rel)
    return rels


def copiar(origen: Path, carpeta: Path, rels: list, respaldo: Path) -> list:
    """Copia sobre la instalación los archivos extraídos, salvo los protegidos. Si una copia falla, deja
    todo como estaba (restaura lo pisado desde `respaldo`, borra lo nuevo) y relanza el error."""
    origen, carpeta, respaldo = Path(origen), Path(carpeta), Path(respaldo)
    hechos = []                                              # (ruta, ¿existía antes?)
    try:
        for rel in rels:
            if protegido(rel):
                continue
            final = carpeta / rel
            existia = final.exists()
            if existia:
                (respaldo / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(final, respaldo / rel)
            hechos.append((rel, existia))                    # antes de copiar: una copia a medias también se deshace
            final.parent.mkdir(parents=True, exist_ok=True)
            _copiar_archivo(origen / rel, final)
    except Exception:
        for rel, existia in reversed(hechos):
            try:
                if existia:
                    shutil.copy2(respaldo / rel, carpeta / rel)
                else:
                    (carpeta / rel).unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"actualizador: no se pudo restaurar {rel}: {e}")
        raise
    return [rel for rel, _existia in hechos]


def _sin_paso(titulo: str, texto: str = "", avance: Optional[float] = None) -> None:
    """Paso de carga que no dibuja nada (tests y llamadas sin pantalla)."""


def actualizar_zip(carpeta: Path, version: str, descargar: Optional[Callable] = None,
                   paso: Optional[Callable] = None) -> tuple:
    """(ok, motivo). Baja el ZIP de main, lo valida, lo descomprime en una carpeta temporal y recién
    después copia. Si algo falla, la instalación queda como estaba."""
    paso = paso or _sin_paso
    titulo = f"ACTUALIZANDO A {version}"
    try:
        paso(titulo, "Descargando la versión nueva…", 0.15)
        datos = (descargar or _descargar)(URL_ZIP, ESPERA_DESCARGA)
        paso(titulo, "Comprobando la descarga…", 0.45)
        ok, motivo, prefijo = validar_zip(datos, version)
        if not ok:
            return False, motivo
        with tempfile.TemporaryDirectory(prefix='alpha_football_act_') as tmp:
            rels = extraer(datos, prefijo, Path(tmp) / 'nuevo')
            paso(titulo, "Instalando los archivos…", 0.70)
            copiar(Path(tmp) / 'nuevo', Path(carpeta), rels, Path(tmp) / 'respaldo')
        return True, ''
    except Exception as e:
        logger.error(f"actualizador: no se pudo instalar el ZIP: {e}", exc_info=True)
        return False, str(e)


# --- Orquestación ─────────────────────────────────────────────────────────────

def actualizar_git(carpeta: Path, version: str, git: Optional[Callable] = None,
                   paso: Optional[Callable] = None) -> tuple:
    """(ok, motivo): git pull --ff-only en una copia limpia."""
    (paso or _sin_paso)(f"ACTUALIZANDO A {version}", "Bajando los cambios…", 0.40)
    rc, salida = (git or _git)(Path(carpeta), 'pull', '--ff-only')
    return rc == 0, ('' if rc == 0 else salida.strip()[:200])


def _leer(ruta: Path) -> bytes:
    try:
        return Path(ruta).read_bytes()
    except OSError:
        return b''


def instalar_requisitos(carpeta: Path, ejecutar: Optional[Callable] = None) -> bool:
    """pip install -r requirements.txt con el mismo intérprete (como audio.py hace con yt-dlp)."""
    try:
        (ejecutar or subprocess.run)([sys.executable, '-m', 'pip', 'install', '-r',
                                      str(Path(carpeta) / 'requirements.txt')],
                                     capture_output=True, text=True, check=True)
        return True
    except Exception as e:
        logger.error(f"actualizador: no se pudieron instalar las dependencias: {e}")
        return False


def texto_aviso(version: str) -> str:
    return f"Hay una versión nueva ({version})"


def revisar(carpeta: Optional[Path] = None, descargar: Optional[Callable] = None,
            git: Optional[Callable] = None, paso: Optional[Callable] = None,
            instalar: Optional[Callable] = None) -> dict:
    """Consulta GitHub y, si hay una versión nueva, la instala según el tipo de copia.
    Devuelve {'estado': 'sin_red' | 'al_dia' | 'actualizado' | 'aviso', 'version': la remota,
    'aviso': texto para el menú, 'reiniciar': bool}. Nunca lanza: ante cualquier error se sigue jugando."""
    res = {'estado': 'sin_red', 'version': None, 'aviso': '', 'reiniciar': False}
    try:
        carpeta = Path(carpeta or raiz())
        remota = consultar(descargar)
        if remota is None:
            return res
        res['version'] = remota
        if not es_mayor(remota, version_local(carpeta)):
            return dict(res, estado='al_dia')
        aviso = dict(res, estado='aviso', aviso=texto_aviso(remota))
        tipo = tipo_copia(carpeta, git)
        if tipo == 'git_sucia':
            logger.info(f"actualizador: hay una versión nueva ({remota}); la copia git tiene cambios: no se instala")
            return aviso
        requisitos = _leer(carpeta / 'requirements.txt')
        if tipo == 'zip':
            ok, motivo = actualizar_zip(carpeta, remota, descargar, paso)
        else:
            ok, motivo = actualizar_git(carpeta, remota, git, paso)
        if not ok or es_mayor(remota, version_local(carpeta)):   # sin esto, un pull que no trae la versión reiniciaría sin fin
            logger.error(f"actualizador: no se instaló la {remota}: {motivo or 'la versión local no cambió'}")
            return aviso
        if _leer(carpeta / 'requirements.txt') != requisitos:
            (paso or _sin_paso)(f"ACTUALIZANDO A {remota}", "Instalando dependencias…", 0.85)
            (instalar or instalar_requisitos)(carpeta)
        (paso or _sin_paso)(f"ACTUALIZANDO A {remota}", "Listo: reiniciando…", 1.0)
        return dict(res, estado='actualizado', reiniciar=True)
    except Exception as e:
        logger.error(f"actualizador: error inesperado, se sigue jugando: {e}", exc_info=True)
        return res


# --- Arranque ─────────────────────────────────────────────────────────────────

def al_iniciar(revisar_fn: Optional[Callable] = None, mostrar: Optional[Callable] = None,
               cerrar: Optional[Callable] = None) -> dict:
    """Lo que llama main.py al abrir el juego (ventana ya creada, antes del menú): revisa y muestra los
    pasos en la pantalla de carga. En los tests (SDL dummy) o con ALPHA_SIN_ACTUALIZAR=1 no hace nada:
    jamás toca la red."""
    omitido = {'estado': 'omitido', 'version': None, 'aviso': '', 'reiniciar': False}
    if revisar_fn is None and (os.environ.get('SDL_VIDEODRIVER') == 'dummy' or os.environ.get('ALPHA_SIN_ACTUALIZAR')):
        return omitido
    try:
        if mostrar is None or cerrar is None:
            from alpha_football.ui import pantalla_carga
            mostrar, cerrar = mostrar or pantalla_carga.mostrar, cerrar or pantalla_carga.cerrar
        mostrado = []

        def paso(titulo: str, texto: str = "", avance: Optional[float] = None) -> None:
            mostrado.append(titulo)
            mostrar(titulo, texto, avance)
        res = (revisar_fn or revisar)(paso=paso)
        if mostrado:
            cerrar()
        return res
    except Exception as e:
        logger.error(f"actualizador: error al iniciar, se sigue jugando: {e}", exc_info=True)
        return omitido


def reiniciar(lanzar: Optional[Callable] = None, salir: Optional[Callable] = None) -> None:
    """Vuelve a abrir el juego con el código nuevo y cierra este proceso."""
    (lanzar or (lambda cmd, cwd: subprocess.Popen(cmd, cwd=cwd)))([sys.executable] + sys.argv, str(raiz()))
    (salir or sys.exit)(0)
