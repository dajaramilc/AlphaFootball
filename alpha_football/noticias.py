# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Núcleo de noticias (v0.4.23.0)
Un solo sitio por el que pasa toda noticia de la carrera (`publicar`) y un solo enganche por jornada
(`cierre_jornada`). Las noticias son dicts en datos_carrera['noticias'] (lo más nuevo primero): van tal
cual al JSON del guardado. Caducan a las JORNADAS_VIDA jornadas y nunca hay más de MAX_NOTICIAS.
Se publican DESPUÉS del hecho real; aquí no se inventa nada. Sin UI.
"""
from __future__ import annotations

import importlib
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

MAX_NOTICIAS = 50
JORNADAS_VIDA = 3               # una noticia de la jornada 5 se ve en la 5, la 6 y la 7
IMPORTANCIA_FEED = 3            # el feed del hub solo muestra las de importancia >= 3
MAX_TITULAR = 60

TIPOS = ('resultado', 'fichaje', 'dt_cambio', 'rumor', 'campeon', 'descenso', 'declaracion', 'lesion',
         'vestuario', 'premio', 'economia', 'cantera', 'promesa', 'record', 'logro', 'otro')

# tipo -> categoría de imagen (un ascenso se publica con categoria='ascenso')
CATEGORIA = {'resultado': 'resultado', 'fichaje': 'fichaje', 'dt_cambio': 'entrenador', 'rumor': 'rumor',
             'campeon': 'titulo', 'descenso': 'descenso', 'declaracion': 'prensa', 'lesion': 'lesion',
             'vestuario': 'vestuario', 'premio': 'premio', 'economia': 'economia', 'cantera': 'promesa',
             'promesa': 'promesa', 'record': 'record', 'logro': 'logro', 'otro': 'general'}

ETIQUETA = {'resultado': "RESULTADO", 'fichaje': "FICHAJE", 'dt_cambio': "ENTRENADOR", 'rumor': "RUMOR",
            'campeon': "CAMPEÓN", 'descenso': "DESCENSO", 'declaracion': "DECLARACIONES", 'lesion': "LESIÓN",
            'vestuario': "VESTUARIO", 'premio': "PREMIO", 'economia': "ECONOMÍA", 'cantera': "CANTERA",
            'promesa': "PROMESA", 'record': "RÉCORD", 'logro': "LOGRO", 'otro': "NOTICIA"}

# categoría -> fondo de la tarjeta cuando la categoría no tiene imágenes
COLOR = {'resultado': (38, 84, 150), 'fichaje': (22, 122, 92), 'rumor': (112, 72, 150),
         'entrenador': (68, 82, 104), 'titulo': (176, 132, 28), 'ascenso': (44, 132, 62),
         'descenso': (146, 44, 44), 'lesion': (170, 62, 50), 'vestuario': (128, 86, 52),
         'premio': (190, 150, 40), 'promesa': (34, 132, 146), 'record': (184, 96, 30),
         'logro': (150, 112, 30), 'economia': (62, 104, 74), 'general': (58, 66, 82), 'prensa': (86, 72, 126)}

RUTA_IMAGENES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'noticias')
EXT_IMAGEN = ('jpg', 'jpeg', 'png')


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _ahora(estado: dict) -> tuple:
    """(temporada, jornada): la jornada son los partidos de liga que el user ya jugó (0 al empezar)."""
    try:
        from alpha_football.salidas import _clave_jornada
        t, j = _clave_jornada(estado)
        return int(t), int(j)
    except Exception as e:
        logger.debug(f"noticias: no se pudo leer la jornada: {e}")
        return int(estado.get('temporada', 1) or 1), 1


def _hoy(estado: dict) -> Optional[str]:
    """Fecha del reloj del juego ('AAAA-MM-DD'); None en una partida sin reloj."""
    cal = (estado.get('datos_carrera') or {}).get('calendario')
    dia = cal.get('dia') if isinstance(cal, dict) else None
    return str(dia) if dia else None


def _ids(cosas) -> list:
    """Acepta objetos con `.id`, dicts con 'id' o los ids sueltos."""
    out = []
    for x in cosas or ():
        v = x.get('id') if isinstance(x, dict) else getattr(x, 'id', x)
        if v is not None:
            out.append(v)
    return out


def _entero(valor, defecto: int) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return defecto


def _normalizar(n: dict) -> None:
    """Completa una noticia de un guardado anterior (las de eventos.registrar_noticia: sin importancia y
    con la clave `jugadores`)."""
    tipo = n.get('tipo') if n.get('tipo') in TIPOS else 'otro'
    n['tipo'] = tipo
    n['id'] = _entero(n.get('id'), 0)
    n['temporada'] = _entero(n.get('temporada'), 1)
    n['jornada'] = _entero(n.get('jornada'), 1)
    n['titular'] = str(n.get('titular', ''))
    n['cuerpo'] = str(n.get('cuerpo', ''))
    n.setdefault('categoria', CATEGORIA[tipo])
    n['importancia'] = max(1, min(5, _entero(n.get('importancia'), IMPORTANCIA_FEED)))
    n.setdefault('equipos_ids', [])
    n.setdefault('jugadores_ids', list(n.get('jugadores') or []))
    n.setdefault('dt_ids', [])
    n.setdefault('leida', False)
    n.setdefault('fecha_creacion', None)


def lista(estado: dict) -> list:
    """Todas las noticias guardadas, lo más nuevo primero. Es la lista del guardado (no una copia)."""
    dc = _dc(estado)
    crudo = dc.get('noticias')
    if not isinstance(crudo, list):
        crudo = dc['noticias'] = []
    if any(not isinstance(n, dict) or 'leida' not in n or 'importancia' not in n for n in crudo):
        crudo[:] = [n for n in crudo if isinstance(n, dict) and ('titular' in n or 'cuerpo' in n)]
        for n in crudo:
            _normalizar(n)
    return crudo


def _siguiente_id(estado: dict, noticias: list) -> int:
    """Contador que solo sube: un id no se reutiliza aunque su noticia ya se haya purgado."""
    dc = _dc(estado)
    sig = max(_entero(dc.get('noticia_sig_id'), 1), max((_entero(n.get('id'), 0) for n in noticias), default=0) + 1)
    dc['noticia_sig_id'] = sig + 1
    return sig


def titular(*formas: str) -> str:
    """La primera forma que cabe en MAX_TITULAR (de la más completa a la más corta); si ninguna cabe, la
    última, que `publicar` recorta."""
    return next((f for f in formas if len(f) <= MAX_TITULAR), formas[-1])


def _recortar(titular: str) -> str:
    t = ' '.join(str(titular).split())
    return t if len(t) <= MAX_TITULAR else t[:MAX_TITULAR - 1].rstrip() + '…'


def publicar(estado: dict, tipo: str, titular: str, cuerpo: str, importancia: int = 3,
             categoria: Optional[str] = None, equipos=(), jugadores=(), dts=(), **extra) -> dict:
    """Publica una noticia y la devuelve. `equipos`, `jugadores` y `dts` aceptan objetos o ids.
    `extra`: `temporada=` y `jornada=` pisan a las actuales (el cierre de temporada publica cuando el
    contador ya subió); `accion={'pantalla', 'texto'}` añade un botón en la pantalla Noticias; cualquier
    otra clave se guarda tal cual (debe ser serializable a JSON)."""
    noticias = lista(estado)
    if tipo not in TIPOS:
        logger.debug(f"noticias: tipo desconocido {tipo!r}, se publica como 'otro'")
        tipo = 'otro'
    t, j = _ahora(estado)
    n = dict(extra)
    n.update({'id': _siguiente_id(estado, noticias), 'tipo': tipo,
              'categoria': categoria if categoria in COLOR else CATEGORIA[tipo],
              'titular': _recortar(titular), 'cuerpo': str(cuerpo),
              'temporada': _entero(extra.get('temporada'), t), 'jornada': _entero(extra.get('jornada'), j),
              'importancia': max(1, min(5, _entero(importancia, IMPORTANCIA_FEED))),
              'equipos_ids': _ids(equipos), 'jugadores_ids': _ids(jugadores), 'dt_ids': _ids(dts),
              'leida': False, 'fecha_creacion': _hoy(estado)})
    noticias.insert(0, n)
    while len(noticias) > MAX_NOTICIAS:      # sale la de menor importancia y, a igualdad, la más vieja
        noticias.remove(min(noticias, key=lambda x: (x['importancia'], x['temporada'], x['jornada'], x['id'])))
    return n


def antiguedad(estado: dict, noticia: dict, ahora: Optional[tuple] = None) -> int:
    """Jornadas que pasaron desde la noticia. La de la última jornada sigue en 0 al empezar la temporada siguiente.
    `ahora` = (temporada, jornada) ya leídas: quien mira muchas noticias las lee una sola vez (leerlas recorre
    el calendario)."""
    t, j = ahora or _ahora(estado)
    n = max(1, _entero(getattr(estado.get('liga'), 'num_jornadas', 0), 0) or 38)
    return max(0, (t - _entero(noticia.get('temporada'), t)) * n + (j - _entero(noticia.get('jornada'), j)))


def activas(estado: dict) -> list:
    """Las que no caducaron: primero las más importantes y, dentro, las más recientes."""
    ahora = _ahora(estado)
    vivas = [(antiguedad(estado, n, ahora), n) for n in lista(estado)]
    vivas = [(a, n) for a, n in vivas if a < JORNADAS_VIDA]
    vivas.sort(key=lambda x: (-x[1]['importancia'], x[0], -x[1]['id']))
    return [n for _a, n in vivas]


def para_feed(estado: dict) -> list:
    return [n for n in activas(estado) if n['importancia'] >= IMPORTANCIA_FEED]


def ultimas(estado: dict, n: int = 10) -> list:
    """Las `n` publicadas más recientemente (para la pantalla de carga)."""
    return lista(estado)[:max(0, int(n))]


def no_leidas(estado: dict) -> int:
    return sum(1 for n in activas(estado) if not n.get('leida'))


def marcar_leida(estado: dict, noticia_id) -> None:
    for n in lista(estado):
        if n['id'] == noticia_id:
            n['leida'] = True
            return


def retirar(estado: dict, noticia_id) -> bool:
    """Quita una noticia ya publicada (p. ej. un fichaje que dejó de estar entre los destacados de la jornada)."""
    noticias = lista(estado)
    quedan = [n for n in noticias if n['id'] != noticia_id]
    if len(quedan) == len(noticias):
        return False
    noticias[:] = quedan
    return True


def purgar(estado: dict) -> int:
    """Borra las de JORNADAS_VIDA o más jornadas de antigüedad. Devuelve cuántas borró."""
    noticias = lista(estado)
    ahora = _ahora(estado)
    quedan = [n for n in noticias if antiguedad(estado, n, ahora) < JORNADAS_VIDA]
    borradas = len(noticias) - len(quedan)
    noticias[:] = quedan
    return borradas


def etiqueta(noticia: dict) -> str:
    """Texto de la etiqueta de la tarjeta ("FICHAJE", "RUMOR"…); un ascenso viaja con tipo 'descenso'."""
    if noticia.get('categoria') == 'ascenso':
        return "ASCENSO"
    return ETIQUETA.get(noticia.get('tipo'), ETIQUETA['otro'])


def imagen(noticia: dict) -> Optional[str]:
    """Ruta de la imagen que le toca: `<categoria><n>.jpg` de RUTA_IMAGENES, siempre la misma para ese id.
    None si la categoría no tiene imágenes (la tarjeta usa entonces COLOR)."""
    cat = noticia.get('categoria') or CATEGORIA.get(noticia.get('tipo'))
    if not cat:
        return None
    try:
        patron = re.compile(rf"^{re.escape(str(cat))}(\d+)\.({'|'.join(EXT_IMAGEN)})$", re.IGNORECASE)
        archivos = sorted((int(m.group(1)), a) for a in os.listdir(RUTA_IMAGENES) for m in [patron.match(a)] if m)
    except OSError:
        return None                          # la carpeta no existe: sin imágenes
    if not archivos:
        return None
    return os.path.join(RUTA_IMAGENES, archivos[_entero(noticia.get('id'), 0) % len(archivos)][1])


def _paso(estado: dict, modulo: str, funcion: str) -> None:
    """Un paso del cierre en su propio `try` (import perezoso): si falla se registra y los demás siguen."""
    nombre = f'alpha_football.{modulo}'
    try:
        getattr(importlib.import_module(nombre), funcion)(estado)
    except ModuleNotFoundError as e:
        if e.name != nombre:
            logger.error(f"noticias: falló {modulo}.{funcion}: {e}", exc_info=True)
        else:
            logger.debug(f"noticias: {modulo}.py todavía no existe")
    except Exception as e:
        logger.error(f"noticias: falló {modulo}.{funcion}: {e}", exc_info=True)


def cierre_jornada(estado: dict) -> None:
    """Único enganche por jornada (lo llama el cierre de jornada de ui/match_screen.py): rumores, generadores
    de noticias y purga."""
    if estado.get('liga') is None or estado.get('mi_equipo') is None:
        return
    _paso(estado, 'rumores', 'revisar_jornada')
    _paso(estado, 'noticias_gen', 'generar_jornada')
    try:
        purgar(estado)
    except Exception as e:
        logger.error(f"noticias: falló la purga: {e}", exc_info=True)
