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
from datetime import date
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

# v0.4.27.0: un fichaje atípico (negociacion._variante_fichaje) cambia solo la etiqueta de su tarjeta
ETIQUETA_VARIANTE = {'ganga': "GANGA", 'generoso': "PAGO GENEROSO", 'traicion': "TRAICIÓN"}

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


NEGRITA = '**'


def negrita(texto) -> str:
    """v0.4.27.0: marca `texto` en negrita para el cuerpo de una noticia o de un correo ('**Nombre**'). Las
    pantallas Noticias y Correo la dibujan; en cualquier otro sitio se quita con `sin_marcas`."""
    return f"{NEGRITA}{texto}{NEGRITA}"


def sin_marcas(texto) -> str:
    """v0.4.27.0: el texto sin las marcas de negrita (para titulares, asuntos y vistas previas)."""
    return str(texto if texto is not None else '').replace(NEGRITA, '')


def _refs_jugadores(cosas) -> tuple:
    """v0.4.27.0: ([ids], [nombres completos]) en paralelo. El id solo es único dentro de un club: el nombre completo
    (único en la carrera) es lo que permite encontrar al jugador luego, en cualquier club. Con ids sueltos o dicts
    sin nombre, el nombre queda vacío."""
    ids, nombres = [], []
    for x in cosas or ():
        v = x.get('id') if isinstance(x, dict) else getattr(x, 'id', x)
        if isinstance(x, dict):
            nombre = x.get('nombre_completo') or f"{x.get('nombre', '')} {x.get('apellido', '')}".strip()
        else:
            nombre = (getattr(x, 'nombre_completo', None)
                      or f"{getattr(x, 'nombre', '')} {getattr(x, 'apellido', '')}".strip())
        if v is None and nombre:
            v = -1                       # un dato sin id (la ficha del Balón de Oro): se encuentra por su nombre
        if v is None:
            continue
        ids.append(v)
        nombres.append(str(nombre or ''))
    return ids, nombres


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
    n.setdefault('jugadores_nombres', [])        # v0.4.27.0: en paralelo a jugadores_ids (vacío en las viejas)
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
    t = ' '.join(sin_marcas(titular).split())      # v0.4.27.0: un titular nunca lleva negrita
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
    ids_jug, nombres_jug = _refs_jugadores(jugadores)      # v0.4.27.0: con su nombre, para abrir la ficha desde la noticia
    n = dict(extra)
    n.update({'id': _siguiente_id(estado, noticias), 'tipo': tipo,
              'categoria': categoria if categoria in COLOR else CATEGORIA[tipo],
              'titular': _recortar(titular), 'cuerpo': str(cuerpo),
              'temporada': _entero(extra.get('temporada'), t), 'jornada': _entero(extra.get('jornada'), j),
              'importancia': max(1, min(5, _entero(importancia, IMPORTANCIA_FEED))),
              'equipos_ids': _ids(equipos), 'jugadores_ids': ids_jug, 'jugadores_nombres': nombres_jug,
              'dt_ids': _ids(dts),
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


def _fecha(noticia: dict) -> Optional[date]:
    """La fecha real de publicación (`fecha_creacion`); None si no la tiene o es ilegible."""
    try:
        return date.fromisoformat(str(noticia.get('fecha_creacion')))
    except ValueError:
        return None


def fecha_texto(noticia: dict, largo: bool = True) -> str:
    """'sáb 12 sep 2026' (corto: 'sáb 12 sep'). Sin fecha real (partida sin reloj o guardado anterior):
    'Temporada 2 – Jornada 7' (corto: 'T2 · J7')."""
    d = _fecha(noticia)
    if d is not None:
        from alpha_football import calendario as CAL
        return CAL.texto_fecha(d, largo)
    t, j = noticia.get('temporada', '?'), noticia.get('jornada', '?')
    return f"Temporada {t} – Jornada {j}" if largo else f"T{t} · J{j}"


def nombre_anio(continente: str, anio: int) -> str:
    """'2026/27' en Europa (la temporada cruza el año) y '2027' en Sudamérica (año natural)."""
    return f"{int(anio)}/{(int(anio) + 1) % 100:02d}" if continente == 'europa' else str(int(anio))


def nombre_temporada(estado: dict, temporada, continente: Optional[str] = None) -> str:
    """El nombre real de la temporada de carrera número `temporada` ('2026/27'), el que se lee en una noticia
    en vez de 'la temporada 11'. `continente` por defecto es el de tu liga."""
    try:
        from alpha_football import calendario as CAL
        cont = continente or CAL.continente(estado)
        return nombre_anio(cont, CAL.ANIO_BASE[cont] + _entero(temporada, 1) - 1)
    except Exception as e:
        logger.debug(f"noticias: no se pudo nombrar la temporada {temporada!r}: {e}")
        return str(temporada)


def reiniciar_feed(estado: dict) -> None:
    """El juego se detuvo (terminó un CONTINUAR, pasó una hora del último día): el feed del hub vuelve a
    empezar por las tres noticias más recientes y de ahí corre hacia las viejas."""
    estado.pop('feed_t0', None)


def activas(estado: dict) -> list:
    """Las que no caducaron: primero las más recientes (fecha real) y, dentro del mismo día, las más importantes.
    Sin fecha van al final y se ordenan por jornada."""
    ahora = _ahora(estado)
    vivas = [(antiguedad(estado, n, ahora), n) for n in lista(estado)]
    vivas = [(a, n) for a, n in vivas if a < JORNADAS_VIDA]

    def clave(x):
        a, n = x
        d = _fecha(n)
        return (-(d.toordinal() if d else 0), a, -n['importancia'], -n['id'])
    vivas.sort(key=clave)
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


def jugadores_de(estado: dict, noticia: dict) -> list:
    """v0.4.27.0: [(jugador, club)] de los jugadores de la noticia que todavía existen (en un club o entre los
    agentes libres, con "Agente libre" como club), en el orden de la noticia. Se busca por nombre completo (único
    en la carrera: el id solo lo es dentro de un club) y, con varios del mismo nombre, el que además tiene su id.
    Una noticia vieja, sin nombres, solo encuentra por id a los de tu plantilla. Al que ya no está (se retiró)
    simplemente se le omite."""
    ids = list(noticia.get('jugadores_ids') or [])
    if not ids:
        return []
    nombres = list(noticia.get('jugadores_nombres') or [])
    nombres += [''] * (len(ids) - len(nombres))
    quieren = {n for n in nombres if n}
    mi = estado.get('mi_equipo')
    por_nombre: dict = {}
    if quieren:
        clubes, vistos = [], set()
        liga = estado.get('liga')
        try:
            from alpha_football.mercado_ia import ligas_de_la_partida
            todas = [lg for lg, _t, _d in ligas_de_la_partida(estado)]
        except Exception as e:
            logger.debug(f"noticias: sin ligas para buscar jugadores: {e}")
            todas = []
        for eq in [mi] + list(getattr(liga, 'equipos', None) or []) + [e for lg in todas for e in lg.equipos]:
            if eq is not None and id(eq) not in vistos:
                vistos.add(id(eq))
                clubes.append(eq)
        for eq in clubes:
            for j in getattr(eq, 'jugadores', None) or []:
                nombre = getattr(j, 'nombre_completo', None)
                if nombre in quieren:
                    por_nombre.setdefault(nombre, []).append((j, getattr(eq, 'nombre', '')))
        for j in estado.get('free_agents_list') or []:
            nombre = getattr(j, 'nombre_completo', None)
            if nombre in quieren:
                por_nombre.setdefault(nombre, []).append((j, "Agente libre"))
    out = []
    for i, nombre in zip(ids, nombres):
        if nombre:
            cands = por_nombre.get(nombre) or []
            hallado = next((c for c in cands if getattr(c[0], 'id', None) == i), cands[0] if cands else None)
        else:                                    # noticia vieja: solo tu plantilla, por id
            j = next((x for x in getattr(mi, 'jugadores', None) or [] if getattr(x, 'id', None) == i), None)
            hallado = (j, getattr(mi, 'nombre', '')) if j is not None else None
        if hallado is not None and all(hallado[0] is not x[0] for x in out):
            out.append(hallado)
    return out


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
    if noticia.get('liberacion'):                  # v0.4.27.0: un club suelta a un jugador (tipo 'otro', imagen de fichaje)
        return "LIBERADO"
    if noticia.get('variante') in ETIQUETA_VARIANTE:    # v0.4.27.0: fichaje atípico (mismo tipo 'fichaje')
        return ETIQUETA_VARIANTE[noticia['variante']]
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
