# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Patrocinios (v4.9.0)
Hasta 3 contratos (camiseta, manga, estadio) con marcas parodia: fijo por jornada, bono por
objetivo, años de contrato. Al vencer llegan ofertas (renovación si cumpliste). Reputación
comercial 0–100 que mejora o empeora las ofertas. Estado en datos_carrera['patrocinios'].
Los clubes de la IA no tienen contratos: siguen con el ingreso de fórmula.
"""
from __future__ import annotations

import logging
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)

ESPACIOS = (('camiseta', 0.50), ('manga', 0.30), ('estadio', 0.20))
NOMBRE_ESPACIO = {'camiseta': "Camiseta", 'manga': "Manga", 'estadio': "Estadio"}
# perfil: (fijo × referencia, bono × referencia, dificultad del objetivo 0 fácil / 1 media / 2 difícil)
PERFILES = {'conservadora': (1.00, 0.10, 0), 'equilibrada': (0.90, 0.25, 1), 'ambiciosa': (0.75, 0.50, 2)}
# v4.9.1: el catálogo (150 marcas con región) y los patrocinios reales viven en data/patrocinadores.py
from alpha_football.data.patrocinadores import MARCAS, PATROCINIOS_REALES   # noqa: E402
LIGAS_SUDAMERICA = ('brasil', 'argentina', 'betplay', 'uruguay', 'ecuador')
SIN_PATROCINIO = 'ninguno'       # v4.9.2: el club arranca con ese espacio vacío (pueden llegar ofertas después)

REP_INICIAL = 50
REP_CUMPLE, REP_FALLA, REP_TITULO, REP_ASCENSO = 6, -5, 8, 8
REP_DESCENSO, REP_QUIEBRA, REP_RESCISION = -10, -15, -8
REP_SIN_INTERES = 15             # por debajo, las marcas pueden no presentarse
PROB_NO_OFERTA = 0.5
FACTOR_DESCENSO, FACTOR_ASCENSO, FACTOR_INVIERNO = 0.60, 1.30, 0.85
PRIMA_FRAC, PRIMA_FIJO = 0.30, 0.88      # prima al contado (× un año de fijo) y fijo que queda
MULTA_FRAC = 0.50                         # rescindir: 50% del fijo que le queda al contrato
NEGOCIAR = {1: (0.10, 0.60), 2: (0.20, 0.30)}   # nivel: (subida de fijo, probabilidad base)
FASE_COPA_DIFICULTAD = ('Fase de liga', 'Octavos', 'Semifinal')
TEXTO_COPA = ("Jugar la copa internacional", "Llegar a octavos de la copa", "Llegar a semifinales de la copa")


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _m(v: int) -> str:
    return f"${int(v) / 1_000_000:.2f}M"


def _rep(p: dict, delta: int) -> None:
    p['reputacion'] = max(0, min(100, int(p.get('reputacion', REP_INICIAL)) + int(delta)))


def mult_reputacion(rep: int) -> float:
    """0 → ×0.80, 50 → ×1.00, 100 → ×1.30 (lineal por tramos)."""
    rep = max(0, min(100, int(rep)))
    return 0.80 + 0.20 * rep / 50 if rep <= 50 else 1.00 + 0.30 * (rep - 50) / 50


def _base(estado: dict) -> int:
    """Patrocinio de fórmula de una temporada para el club del user."""
    from alpha_football import finanzas as F
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    return int(F.base_ingresos(mi, getattr(liga, 'tipo', ''), getattr(liga, 'division', 1) or 1) * F.PATROCINIO_FRAC)


def valor_referencia(estado: dict, espacio: str) -> int:
    return int(_base(estado) * dict(ESPACIOS)[espacio])


# --- objetivos -----------------------------------------------------------------------------

def _juega_copa(estado: dict) -> bool:
    try:
        from alpha_football import competiciones as CP
        return bool(CP.tipo_copa_user(estado))
    except Exception:
        return False


def _puesto_esperado(estado: dict) -> int:
    from alpha_football.market import nivel_club
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    orden = sorted(liga.equipos, key=lambda eq: -nivel_club(eq))
    return next((i + 1 for i, eq in enumerate(orden) if eq is mi), len(orden))


def crear_objetivo(estado: dict, dificultad: int, rng: random.Random, tipo: Optional[str] = None) -> dict:
    """Objetivo de temporada de un contrato según el club y la dificultad (0, 1 o 2)."""
    liga = estado.get('liga')
    n = max(1, int(getattr(liga, 'num_jornadas', 22) or 22))
    n_eq = max(2, len(getattr(liga, 'equipos', []) or []))
    d = max(0, min(2, int(dificultad)))
    if tipo is None:
        tipo = rng.choice(['posicion', 'goles', 'local', 'u21'] + (['copa'] if _juega_copa(estado) else []))
    if tipo == 'posicion':
        meta = max(1, min(n_eq, _puesto_esperado(estado) + (3, 0, -3)[d]))
        texto = "Ganar la liga" if meta == 1 else f"Terminar la liga en el puesto {meta} o mejor"
    elif tipo == 'goles':
        meta = round(n * (1.2, 1.5, 1.9)[d])
        texto = f"Marcar {meta} goles en la liga"
    elif tipo == 'local':
        meta = max(1, round(n / 2 * (0.40, 0.55, 0.70)[d]))
        texto = f"Ganar {meta} partidos de local en la liga"
    elif tipo == 'u21':
        meta = max(1, round((10, 25, 45)[d] * n / 22))
        texto = f"Que los menores de 21 sumen {meta} partidos"
    else:
        tipo, meta, texto = 'copa', FASE_COPA_DIFICULTAD[d], TEXTO_COPA[d]
    return {'tipo': tipo, 'meta': meta, 'texto': texto}


def _valor_actual(estado: dict, tipo: str, posicion: Optional[int] = None):
    """Lo que lleva el club en ese tipo de objetivo (None en copa si no la juega)."""
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    if tipo == 'posicion':
        if posicion is not None:
            return int(posicion)
        from alpha_football.ui.postpartido import posicion_liga
        return int(posicion_liga(liga, mi.id))
    if tipo == 'goles':
        return int(getattr(mi, 'gf', 0) or 0)
    if tipo == 'local':
        return sum(1 for p in getattr(liga, 'calendario', []) or []
                   if p.jugado and p.local_id == mi.id and (p.goles_local or 0) > (p.goles_visitante or 0))
    if tipo == 'u21':
        return sum(int(getattr(j, 'partidos_jugados', 0) or 0) for j in mi.jugadores
                   if int(getattr(j, 'edad', 25) or 25) < 21)
    return estado.get('copa_mejor_fase_temp') or None


def cumple(estado: dict, contrato: dict, posicion: Optional[int] = None) -> Optional[bool]:
    """True/False, o None si esta temporada no aplica (objetivo de copa sin jugar la copa)."""
    obj = contrato.get('objetivo') or {}
    tipo, meta = obj.get('tipo'), obj.get('meta')
    actual = _valor_actual(estado, tipo, posicion)
    if tipo == 'copa':
        if actual is None:
            return None
        from alpha_football.directiva import _indice_fase_copa
        return _indice_fase_copa(actual) >= _indice_fase_copa(meta)
    if tipo == 'posicion':
        return int(actual) <= int(meta)
    return int(actual) >= int(meta)


def progreso(estado: dict, contrato: dict) -> float:
    """Fracción 0..1 para la barra de la pantalla."""
    try:
        obj = contrato.get('objetivo') or {}
        tipo, meta = obj.get('tipo'), obj.get('meta')
        actual = _valor_actual(estado, tipo)
        if tipo == 'copa':
            if actual is None:
                return 0.0
            from alpha_football.directiva import _indice_fase_copa
            f = (_indice_fase_copa(actual) + 1) / (_indice_fase_copa(meta) + 1)
        elif tipo == 'posicion':
            n_eq = len(estado['liga'].equipos)
            f = 1.0 if actual <= meta else 1.0 - (actual - meta) / max(1, n_eq - meta)
        else:
            f = actual / meta if meta else 1.0
        return max(0.0, min(1.0, float(f)))
    except Exception as e:
        logger.error(f"progreso de patrocinio: {e}")
        return 0.0


# --- contratos y estado --------------------------------------------------------------------

def _crear_contrato(estado: dict, marca: tuple, espacio: str, rng: random.Random, anios: int,
                    mult: float = 1.0, fijo: Optional[float] = None) -> dict:
    nombre, rubro, perfil = marca[:3]       # v4.9.1: el catálogo trae también la región
    f_fijo, f_bono, dificultad = PERFILES[perfil]
    ref = valor_referencia(estado, espacio) * mult
    return {'marca': nombre, 'rubro': rubro, 'espacio': espacio, 'perfil': perfil,
            'fijo': int(fijo if fijo is not None else ref * f_fijo), 'bono': int(ref * f_bono),
            'objetivo': crear_objetivo(estado, dificultad, rng), 'anios': int(anios), 'cumplido_ultima': None}


def region_de(estado: dict) -> str:
    """v4.9.1: 'sudamerica' si el club juega en una liga sudamericana; si no, 'europa'."""
    return 'sudamerica' if getattr(estado.get('liga'), 'tipo', '') in LIGAS_SUDAMERICA else 'europa'


def marcas_de_region(region: str) -> list:
    """v4.9.2: marcas que pueden patrocinar a un club de esa región (las globales + las suyas)."""
    return [m for m in MARCAS if m[3] in ('global', region)]


def marcas_para(estado: dict) -> list:
    """v4.9.1: marcas del catálogo que pueden patrocinar a este club (globales + las de su región)."""
    return marcas_de_region(region_de(estado))


def inicial_de(nombre_club: str, editados: Optional[dict], espacio: str, validas=None):
    """v4.9.2: con qué arranca el club en ese espacio: una marca, SIN_PATROCINIO (vacío) o None (al azar).
    Manda lo puesto en el editor (si la marca vale para su región); si no, el dato real. Un club con
    datos reales cuyo estadio no tiene naming arranca sin patrocinador de estadio."""
    ed = (editados or {}).get(espacio)
    if ed == SIN_PATROCINIO or (ed and (validas is None or ed in validas)):
        return ed
    real = PATROCINIOS_REALES.get(nombre_club)
    if real is None:
        return None
    return real.get(espacio) or (SIN_PATROCINIO if espacio == 'estadio' else None)


def _nuevo(estado: dict, rng: Optional[random.Random] = None) -> dict:
    """Los contratos con los que llega el club. Si es de 1ª y tiene patrocinios reales, arranca con
    esos (pueden repetir rubro, y el estadio sin naming queda vacío); lo que no tenga dato se rellena
    con marcas de su región en rubros distintos. Años restantes al azar."""
    rng = rng or random.Random()
    mi = estado['mi_equipo']
    disponibles = {m[0]: m for m in marcas_para(estado)}
    iniciales = {esp: inicial_de(mi.nombre, getattr(mi, 'patrocinios', None), esp, disponibles)
                 for esp, _peso in ESPACIOS}
    elegidas = {esp: disponibles.get(v) for esp, v in iniciales.items()}
    marcas = list(disponibles.values())
    rng.shuffle(marcas)
    for espacio, _peso in ESPACIOS:
        if elegidas[espacio] is None and iniciales[espacio] != SIN_PATROCINIO:
            usados = {m[1] for m in elegidas.values() if m}
            elegidas[espacio] = next(m for m in marcas if m[1] not in usados)
    contratos = {espacio: (_crear_contrato(estado, elegidas[espacio], espacio, rng, rng.randint(1, 3))
                           if elegidas[espacio] else None)
                 for espacio, _peso in ESPACIOS}
    return {'club': estado['mi_equipo'].nombre, 'reputacion': REP_INICIAL, 'contratos': contratos,
            'ofertas': [], 'sig_id': 0}


def _valido(p: Any, mi: Any) -> bool:
    if not isinstance(p, dict) or p.get('club') != getattr(mi, 'nombre', None):
        return False
    cs = p.get('contratos')
    if not isinstance(cs, dict) or not isinstance(p.get('ofertas'), list):
        return False
    return all(esp in cs and (cs[esp] is None or (isinstance(cs[esp], dict) and 'marca' in cs[esp] and 'fijo' in cs[esp]))
               for esp, _w in ESPACIOS)


def datos(estado: dict) -> dict:
    """Estado de patrocinios del club del user; si falta, está corrupto o es de otro club, se genera."""
    dc = _dc(estado)
    p = dc.get('patrocinios')
    if not _valido(p, estado.get('mi_equipo')):
        p = dc['patrocinios'] = _nuevo(estado)
    return p


def cobro_jornada(estado: dict) -> int:
    """Lo que pagan los contratos vigentes en una jornada de liga."""
    n = max(1, int(getattr(estado.get('liga'), 'num_jornadas', 22) or 22))
    return sum(int(c['fijo']) // n for c in datos(estado)['contratos'].values() if c)


def ingreso_anual(estado: dict) -> int:
    return sum(int(c['fijo']) for c in datos(estado)['contratos'].values() if c)


# --- ofertas y acciones --------------------------------------------------------------------

def _ventana(estado: dict) -> Optional[str]:
    """'inicio' | 'invierno' | 'cierre' si el mercado está abierto; None si no."""
    from alpha_football.market import ventana_actual
    liga = estado.get('liga')
    v = ventana_actual(int(getattr(liga, 'jornada_actual', 1) or 1), int(getattr(liga, 'num_jornadas', 22) or 22))
    return v[2] if v else None


def ofertas_de(estado: dict, espacio: str) -> list:
    return [o for o in datos(estado)['ofertas'] if o.get('espacio') == espacio]


def generar_ofertas(estado: dict, espacio: str, rng: Optional[random.Random] = None, factor: float = 1.0,
                    anterior: Optional[dict] = None) -> list:
    """Ofertas para un espacio vacío (reemplazan a las que hubiera): la renovación de `anterior`
    si cumplió su objetivo, y hasta 2 marcas nuevas de rubros libres. Retorna las nuevas."""
    p = datos(estado)
    azar = rng or random.Random()
    p['ofertas'] = [o for o in p['ofertas'] if o.get('espacio') != espacio]
    rep = int(p.get('reputacion', REP_INICIAL))
    mult = mult_reputacion(rep) * factor
    ocupados = {c['rubro'] for esp, c in p['contratos'].items() if c and esp != espacio}
    nuevas = []
    # v4.9.2: la misma marca en otro espacio (camiseta y estadio en la vida real) no veta su renovación
    de_otras = {c['rubro'] for esp, c in p['contratos'].items()
                if c and esp != espacio and (not anterior or c['marca'] != anterior.get('marca'))}
    if anterior and anterior.get('cumplido_ultima') is True and anterior.get('rubro') not in de_otras:
        o = _crear_contrato(estado, (anterior['marca'], anterior['rubro'], anterior['perfil']), espacio, azar,
                            azar.randint(1, 3), mult, fijo=anterior['fijo'] * azar.uniform(1.10, 1.20))
        o['renovacion'] = True
        nuevas.append(o)
        ocupados.add(anterior['rubro'])
    # v4.9.1: solo marcas de su región
    candidatas = [m for m in marcas_para(estado) if m[1] not in ocupados and (not anterior or m[0] != anterior.get('marca'))]
    azar.shuffle(candidatas)
    elegidas = []
    for m in candidatas:
        if m[1] not in {x[1] for x in elegidas}:
            elegidas.append(m)
        if len(elegidas) == 2:
            break
    for m in elegidas:
        variacion = azar.uniform(0.95, 1.05)
        anios = azar.randint(1, 3)
        no_viene = azar.random() < PROB_NO_OFERTA
        if rep < REP_SIN_INTERES and no_viene:
            continue                     # con mala reputación la marca puede no presentarse
        o = _crear_contrato(estado, m, espacio, azar, anios, mult * variacion)
        o['renovacion'] = False
        nuevas.append(o)
    for o in nuevas:
        p['sig_id'] = o['id'] = int(p.get('sig_id', 0) or 0) + 1
        o['negociada'] = False
    p['ofertas'] += nuevas
    return nuevas


def _oferta(p: dict, oferta_id: int) -> Optional[dict]:
    return next((o for o in p['ofertas'] if o.get('id') == oferta_id), None)


def firmar(estado: dict, oferta_id: int, con_prima: bool = False) -> tuple:
    """Firma la oferta. Con prima: 30% de un año al contado y el fijo queda ×0.88."""
    try:
        from alpha_football.finanzas import registrar
        p, mi = datos(estado), estado.get('mi_equipo')
        o = _oferta(p, oferta_id)
        if o is None:
            return False, "Esa oferta ya no está disponible."
        espacio = o['espacio']
        if p['contratos'].get(espacio):
            return False, "Ese espacio ya tiene patrocinador."
        if any(c and c['rubro'] == o['rubro'] and c['marca'] != o['marca']      # v4.9.2: la misma marca sí puede
               for esp, c in p['contratos'].items() if esp != espacio):
            return False, f"Ya tienes una marca del rubro {o['rubro']} en otro espacio."
        c = {k: v for k, v in o.items() if k not in ('id', 'renovacion', 'negociada')}
        extra = ""
        if con_prima:
            prima = int(c['fijo'] * PRIMA_FRAC)
            c['fijo'] = int(c['fijo'] * PRIMA_FIJO)
            mi.balance = int(mi.balance) + prima
            registrar(estado, 'patrocinio', prima)
            extra = f" Prima de firma: {_m(prima)}."
        p['contratos'][espacio] = c
        p['ofertas'] = [x for x in p['ofertas'] if x.get('espacio') != espacio]
        anios = c['anios']
        return True, (f"{c['marca']} patrocina tu {NOMBRE_ESPACIO[espacio].lower()} por {anios} "
                      f"año{'s' if anios != 1 else ''}: {_m(c['fijo'])} al año.{extra}")
    except Exception as e:
        logger.error(f"No se pudo firmar el patrocinio {oferta_id}: {e}", exc_info=True)
        return False, "No se pudo firmar el patrocinio."


def rechazar(estado: dict, oferta_id: int) -> bool:
    p = datos(estado)
    o = _oferta(p, oferta_id)
    if o is None:
        return False
    p['ofertas'].remove(o)
    return True


def prob_negociar(estado: dict, nivel: int) -> float:
    """Probabilidad de que la marca acepte la subida: base del nivel ± 0.3 puntos por punto de reputación."""
    base = NEGOCIAR[nivel][1]
    rep = int(datos(estado).get('reputacion', REP_INICIAL))
    return max(0.05, min(0.90, base + 0.003 * (rep - 50)))


def negociar(estado: dict, oferta_id: int, nivel: int, rng: Optional[random.Random] = None) -> tuple:
    """Pide +10% (nivel 1) o +20% (nivel 2) de fijo, una vez por oferta. Si falla, la marca se retira."""
    try:
        p = datos(estado)
        o = _oferta(p, oferta_id)
        if o is None:
            return False, "Esa oferta ya no está disponible."
        if o.get('negociada'):
            return False, "Ya negociaste esta oferta."
        if (rng or random.Random()).random() < prob_negociar(estado, nivel):
            o['fijo'] = int(o['fijo'] * (1 + NEGOCIAR[nivel][0]))
            o['negociada'] = True
            return True, f"{o['marca']} acepta: sube el fijo a {_m(o['fijo'])} al año."
        p['ofertas'].remove(o)
        return False, f"{o['marca']} no acepta y retira su oferta."
    except Exception as e:
        logger.error(f"No se pudo negociar el patrocinio {oferta_id}: {e}", exc_info=True)
        return False, "No se pudo negociar la oferta."


def multa_rescision(estado: dict, espacio: str) -> int:
    """50% del fijo que le queda al contrato: lo que falta de esta temporada más las siguientes."""
    c = datos(estado)['contratos'].get(espacio)
    if not c:
        return 0
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    n = max(1, int(getattr(liga, 'num_jornadas', 22) or 22))
    jugadas = sum(1 for x in getattr(liga, 'calendario', []) or [] if x.jugado and mi.id in (x.local_id, x.visitante_id))
    restantes = max(0, n - jugadas)
    return int((c['fijo'] * restantes / n + c['fijo'] * max(0, int(c['anios']) - 1)) * MULTA_FRAC)


def rescindir(estado: dict, espacio: str, rng: Optional[random.Random] = None) -> tuple:
    """Rompe el contrato pagando la multa (−8 de reputación). Con el mercado abierto llegan ofertas ya."""
    try:
        from alpha_football.finanzas import registrar
        p, mi = datos(estado), estado.get('mi_equipo')
        c = p['contratos'].get(espacio)
        if not c:
            return False, "Ese espacio no tiene patrocinador."
        multa = multa_rescision(estado, espacio)
        if int(mi.balance) < multa:
            return False, f"Saldo insuficiente para la multa de {_m(multa)}."
        mi.balance = int(mi.balance) - multa
        registrar(estado, 'patrocinio', -multa)
        p['contratos'][espacio] = None
        _rep(p, REP_RESCISION)
        ventana = _ventana(estado)
        if ventana in ('inicio', 'invierno'):
            generar_ofertas(estado, espacio, rng, factor=FACTOR_INVIERNO if ventana == 'invierno' else 1.0,
                            anterior={'marca': c['marca'], 'cumplido_ultima': False})
        return True, f"Contrato con {c['marca']} rescindido. Multa: {_m(multa)}."
    except Exception as e:
        logger.error(f"No se pudo rescindir el patrocinio de {espacio}: {e}", exc_info=True)
        return False, "No se pudo rescindir el contrato."


# --- ciclo de temporada --------------------------------------------------------------------

def _correo(estado: dict, asunto: str, lineas: list) -> None:
    try:
        from alpha_football import correo as C
        C.enviar(estado, 'patrocinador', asunto, "\n".join(lineas), C.accion('patrocinios_screen', "VER PATROCINIOS"))
    except Exception as e:
        logger.error(f"No se pudo enviar el correo de patrocinios: {e}")


def _texto_oferta(o: dict) -> str:
    return (f"{o['marca']} ({o['rubro']}{', renovación' if o.get('renovacion') else ''}): {_m(o['fijo'])} al año "
            f"+ bono de {_m(o['bono'])}, {o['anios']} año{'s' if o['anios'] != 1 else ''}. "
            f"Objetivo: {o['objetivo']['texto']}.")


def evaluar_temporada(estado: dict, posicion: int, temporada: int) -> Optional[dict]:
    """Con la tabla final todavía intacta: evalúa el objetivo de cada contrato, paga los bonos
    (al libro de `temporada`) y ajusta la reputación. Una sola vez por temporada."""
    try:
        from alpha_football.finanzas import registrar
        p, mi = datos(estado), estado.get('mi_equipo')
        if p.get('ultimo_cierre') == int(temporada):
            return None
        p['ultimo_cierre'] = int(temporada)
        lineas, total = [], 0
        for espacio, _peso in ESPACIOS:
            c = p['contratos'].get(espacio)
            if not c:
                continue
            ok = cumple(estado, c, posicion)
            c['cumplido_ultima'] = ok
            quien = f"{c['marca']} ({NOMBRE_ESPACIO[espacio].lower()})"
            if ok is True:
                bono = int(c.get('bono', 0) or 0)
                mi.balance = int(mi.balance) + bono
                registrar(estado, 'patrocinio', bono, int(temporada))
                total += bono
                _rep(p, REP_CUMPLE)
                lineas.append(f"{quien}: objetivo cumplido ({c['objetivo']['texto']}). Bono de {_m(bono)}.")
            elif ok is False:
                _rep(p, REP_FALLA)
                lineas.append(f"{quien}: objetivo no cumplido ({c['objetivo']['texto']}). Sin bono.")
            else:
                lineas.append(f"{quien}: su objetivo no aplicaba esta temporada (no jugó la copa).")
        if int(posicion) == 1 and int(getattr(estado.get('liga'), 'division', 1) or 1) == 1:
            _rep(p, REP_TITULO)
            lineas.append("El título de liga mejora la reputación comercial del club.")
        p['resumen_cierre'] = lineas
        return {'bonos': total, 'lineas': lineas}
    except Exception as e:
        logger.error(f"Error evaluando los patrocinios: {e}", exc_info=True)
        return None


def cambio_division(estado: dict, ascendio: bool, descendio: bool) -> None:
    """Cláusula de división de los contratos vigentes (ascenso ×1.30, descenso ×0.60) y reputación."""
    try:
        if not (ascendio or descendio):
            return
        p = datos(estado)
        factor = FACTOR_ASCENSO if ascendio else FACTOR_DESCENSO
        for c in p['contratos'].values():
            if c:
                c['fijo'], c['bono'] = int(c['fijo'] * factor), int(c['bono'] * factor)
        _rep(p, REP_ASCENSO if ascendio else REP_DESCENSO)
        p.setdefault('resumen_cierre', []).append(
            "Por el ascenso, los contratos vigentes suben un 30%." if ascendio
            else "Por el descenso, los contratos vigentes bajan un 40%.")
    except Exception as e:
        logger.error(f"Error aplicando la cláusula de división de los patrocinios: {e}", exc_info=True)


def cierre_contratos(estado: dict, rng: Optional[random.Random] = None) -> Optional[dict]:
    """Cierre financiero (ya en la temporada nueva): −1 año, vencen los que llegan a 0 y llegan
    ofertas para los espacios vacíos. Cerrar en números rojos baja la reputación."""
    try:
        p, mi = datos(estado), estado.get('mi_equipo')
        azar = rng or random.Random()
        lineas = list(p.pop('resumen_cierre', []) or [])
        if int(mi.balance) < 0:
            _rep(p, REP_QUIEBRA)
            lineas.append("Cerrar la temporada en números rojos daña la reputación comercial del club.")
        p['ofertas'] = []
        vencidos = {}
        for espacio, _peso in ESPACIOS:
            c = p['contratos'].get(espacio)
            if not c:
                continue
            c['anios'] = int(c.get('anios', 1) or 1) - 1
            if c['anios'] <= 0:
                vencidos[espacio] = c
                p['contratos'][espacio] = None
                lineas.append(f"Venció el contrato con {c['marca']} ({NOMBRE_ESPACIO[espacio].lower()}).")
        for espacio, _peso in ESPACIOS:
            if p['contratos'].get(espacio):
                continue
            nuevas = generar_ofertas(estado, espacio, azar, anterior=vencidos.get(espacio))
            if nuevas:
                lineas.append(f"Ofertas para {NOMBRE_ESPACIO[espacio].lower()}:")
                lineas += [f"  · {_texto_oferta(o)}" for o in nuevas]
            else:
                lineas.append(f"Ninguna marca presentó oferta para {NOMBRE_ESPACIO[espacio].lower()}.")
        p['ultima_ventana'] = f"{int(estado.get('temporada', 1) or 1)}-inicio"
        if p['ofertas']:
            lineas.append("Tiene hasta el cierre de la ventana de pases para responder; un espacio vacío no cobra.")
        if lineas:
            _correo(estado, "Patrocinios: ofertas sobre la mesa" if p['ofertas'] else "Patrocinios: cierre de temporada", lineas)
        return {'vencidos': list(vencidos), 'ofertas': len(p['ofertas'])}
    except Exception as e:
        logger.error(f"Error en el cierre de los patrocinios: {e}", exc_info=True)
        return None


def revisar_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Tras cada jornada: al cerrar la ventana se retiran las ofertas sin responder; al abrir la de
    invierno llegan ofertas (15% peores) para los espacios vacíos."""
    try:
        if estado.get('mi_equipo') is None:
            return
        p = datos(estado)
        ventana = _ventana(estado)
        vacios = [esp for esp, _w in ESPACIOS if not p['contratos'].get(esp)]
        nombres = ", ".join(NOMBRE_ESPACIO[esp].lower() for esp in vacios)
        if ventana == 'invierno':
            clave = f"{int(estado.get('temporada', 1) or 1)}-invierno"
            if p.get('ultima_ventana') == clave:
                return
            p['ultima_ventana'] = clave
            lineas = []
            for esp in vacios:
                nuevas = generar_ofertas(estado, esp, rng, factor=FACTOR_INVIERNO)
                lineas += [f"{NOMBRE_ESPACIO[esp]}: {_texto_oferta(o)}" for o in nuevas]
            if lineas:
                _correo(estado, "Patrocinios: ofertas de invierno",
                        lineas + ["A mitad de temporada las marcas pagan menos. Tiene hasta el cierre de la ventana."])
            elif vacios:
                _correo(estado, "Patrocinios: sin interesados",
                        [f"Ninguna marca presentó oferta para: {nombres}. Esos espacios siguen sin cobrar."])
        elif ventana is None and p['ofertas']:
            p['ofertas'] = []
            _correo(estado, "Patrocinios: ofertas retiradas",
                    ["Se cerró la ventana y las marcas retiraron las ofertas sin responder."]
                    + ([f"Sin patrocinador en: {nombres}. No cobrará por esos espacios hasta la próxima ventana."]
                       if vacios else []))
    except Exception as e:
        logger.error(f"Error revisando los patrocinios de la jornada: {e}", exc_info=True)
