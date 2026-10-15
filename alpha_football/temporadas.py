# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Temporadas por continente (v0.4.16.0)
Cada continente tiene su temporada (Europa 1 jul → 30 jun, Sudamérica 1 ene → 31 dic), así que van
desfasados medio año: el otro continente arranca a mitad de la suya, cierra en su fecha mientras tú sigues
jugando, y tu cierre de temporada solo cierra tu continente.
- Estado: datos_carrera['mundo'] = {'desfase': True, 'anio': {'europa': 2026, 'sudamerica': 2026},
  'campeones': {copa: club}, 'balon': {continente: podio}}. Sin la marca 'desfase' TODO el juego se comporta
  como antes (las 16 ligas a la par): así siguen las partidas viejas hasta su próximo cierre de temporada.
- El desfase es por FECHA: una liga del otro continente está en la jornada cuyo sábado ya pasó
  (calendario.sabados con el año de su continente). Lo revisa revisar_jornada cada día (dias.revisar_dia) y,
  sin reloj, al cerrar tu jornada.
- Anual y para todos en TU cierre: edad, retiros, contratos y Balón de Oro. El cierre del otro continente
  no envejece a nadie.
Sin UI.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Iterable, Optional

from alpha_football import calendario as CAL

logger = logging.getLogger(__name__)

CONTINENTES = ('europa', 'sudamerica')


# --- Continentes ──────────────────────────────────────────────────────────────

def continente_de(tipo: str) -> str:
    """Continente de una liga por su tipo ('premier' → 'europa')."""
    from alpha_football.paises import es_sudamerica
    return 'sudamerica' if es_sudamerica(tipo or '') else 'europa'


def otro(cont: str) -> str:
    return 'europa' if cont == 'sudamerica' else 'sudamerica'


def paises_de(cont: str) -> tuple:
    """Los tipos de liga (países) de ese continente."""
    from alpha_football.paises import EUROPA, SUDAMERICA
    return tuple(SUDAMERICA if cont == 'sudamerica' else EUROPA)


# --- El mundo ─────────────────────────────────────────────────────────────────

def _leer_mundo(estado: dict) -> dict:
    """El bloque del mundo tal como está guardado (sin crearlo)."""
    m = (estado.get('datos_carrera') or {}).get('mundo')
    return m if isinstance(m, dict) else {}


def mundo(estado: dict) -> dict:
    """datos_carrera['mundo'] (lo crea vacío si falta; crear el bloque no activa el desfase)."""
    dc = estado.setdefault('datos_carrera', {})
    if not isinstance(dc.get('mundo'), dict):
        dc['mundo'] = {}
    return dc['mundo']


def activo(estado: dict) -> bool:
    """¿La partida ya tiene los continentes desfasados? Sin la marca todo se comporta como antes."""
    return bool(_leer_mundo(estado).get('desfase'))


def anio_en(cont: str, d: date) -> int:
    """Año en que empezó la temporada de ese continente que contiene el día `d`."""
    from alpha_football import temporada as T
    mes, dia, _suma = T.CALENDARIO.get(cont, T.CALENDARIO['europa'])['inicio']
    return d.year if (d.month, d.day) >= (mes, dia) else d.year - 1


def anio(estado: dict, cont: str) -> int:
    """Año en que empezó la temporada en curso de ese continente."""
    guardado = (_leer_mundo(estado).get('anio') or {}).get(cont)
    if guardado:
        return int(guardado)
    if cont == CAL.continente(estado):
        return CAL.anio(estado)
    from alpha_football import temporada as T
    return anio_en(cont, T.fecha(estado))


def fin(estado: dict, cont: str) -> date:
    """Último día de la temporada en curso de ese continente (30 jun / 31 dic)."""
    from alpha_football import temporada as T
    mes, dia, suma = T.CALENDARIO.get(cont, T.CALENDARIO['europa'])['fin']
    return date(anio(estado, cont) + suma, mes, dia)


# --- Ligas y fechas ───────────────────────────────────────────────────────────

def ligas(estado: dict, paises: Optional[Iterable[str]] = None) -> list:
    """[(liga, tipo, división)] de la partida; con `paises`, solo las de esos países."""
    from alpha_football.mercado_ia import ligas_de_la_partida
    todas = ligas_de_la_partida(estado)
    if paises is None:
        return todas
    filtro = set(paises)
    return [x for x in todas if x[1] in filtro]


def _sabados(estado: dict, liga) -> tuple:
    cont = continente_de(getattr(liga, 'tipo', '') or '')
    n = max(1, int(getattr(liga, 'num_jornadas', 22) or 22))
    return CAL.sabados(n, cont, anio(estado, cont))


def fecha_jornada(estado: dict, liga, jornada: int) -> date:
    """Sábado de esa jornada de la liga, en el calendario de su continente."""
    sabs = _sabados(estado, liga)
    return sabs[max(1, min(len(sabs), int(jornada or 1))) - 1]


def jornadas_por_fecha(estado: dict, liga, d: date) -> int:
    """Cuántas jornadas de esa liga ya deberían estar jugadas el día `d` (su sábado ya pasó)."""
    return sum(1 for s in _sabados(estado, liga) if s <= d)

# --- Pasos por liga del cierre de temporada ───────────────────────────────────
# Los usan tu cierre (resumen_temporada_screen.avanzar_nueva_temporada) y el del otro continente.

def ascensos_descensos(estado: dict, paises: Optional[Iterable[str]] = None,
                       temporada_libro: Optional[int] = None) -> dict:
    """Los 2 primeros de cada 2ª suben y los 2 últimos de cada 1ª bajan, país por país (con `paises`, solo
    en esos). Aplica el salto / bajón de nivel (mercado_ia) y, si asciende tu club, registra su premio en
    el libro de `temporada_libro`. Devuelve {'movimientos': [{'tipo', 'ascendidos', 'descendidos'}],
    'user_asc', 'user_des', 'premio_ascenso_user', 'payload_user' (los de tu país, para la pantalla)}."""
    from alpha_football.ui.resumen_temporada_screen import _swap_promocion
    from alpha_football.mercado_ia import aplicar_ascenso, aplicar_descenso
    primeras = estado.setdefault('primera_division', {})
    segunda = estado.setdefault('segunda_division', {})
    mi_equipo = estado.get('mi_equipo')
    mi_id = getattr(mi_equipo, 'id', None)
    liga_tipo = getattr(estado.get('liga'), 'tipo', '')
    filtro = set(paises) if paises is not None else None
    res = {'movimientos': [], 'user_asc': False, 'user_des': False, 'premio_ascenso_user': 0, 'payload_user': None}
    recien = estado.setdefault('_recien_ascendidos', [])
    for tipo_x in sorted(set(primeras) | set(segunda)):
        if filtro is not None and tipo_x not in filtro:
            continue
        l1, l2 = primeras.get(tipo_x), segunda.get(tipo_x)
        try:
            ascenden, descienden = _swap_promocion(l1, l2)
        except Exception as e_promo:
            logger.error(f"Error en swap promoción/relegación de '{tipo_x}': {e_promo}")
            continue
        if not ascenden and not descienden:
            continue
        # v4.4.0: ascenso +3..+6 (techo 83) y descenso −2..−5 según rendimiento (nivel_temporada);
        # el que asciende cobra el premio de ascenso.
        for eq in ascenden:
            try:
                premio = aplicar_ascenso(eq, tipo_x, estado)
                recien.append(eq.nombre)
                if eq.id == mi_id:
                    res['premio_ascenso_user'] = premio
                    try:   # el premio de ascenso también va al libro de finanzas de la temporada
                        from alpha_football.finanzas import registrar
                        registrar(estado, 'premios', int(premio or 0), temporada_libro,
                                  concepto="Premio de ascenso")       # v0.4.27.0
                    except Exception as e_lib_asc:
                        logger.error(f"No se pudo registrar el premio de ascenso: {e_lib_asc}")
            except Exception as e_asc:
                logger.error(f"Error aplicando el ascenso de {eq.nombre}: {e_asc}")
        for eq in descienden:
            try:
                aplicar_descenso(eq, estado)
            except Exception as e_des:
                logger.error(f"Error aplicando el descenso de {eq.nombre}: {e_des}")
        res['movimientos'].append({'tipo': tipo_x,
                                   'ascendidos': [e.nombre for e in ascenden],
                                   'descendidos': [e.nombre for e in descienden]})
        if tipo_x == liga_tipo:
            def _payload(equipos, origen, destino):
                return [{'nombre': getattr(e, 'nombre', '?'), 'ovr': getattr(e, 'ovr_promedio', 0),
                         'origen': origen, 'destino': destino, 'es_user': e.id == mi_id}
                        for e in equipos]
            res['user_asc'] = any(e.id == mi_id for e in ascenden)
            res['user_des'] = any(e.id == mi_id for e in descienden)
            res['payload_user'] = {
                'ascendidos': _payload(ascenden, 2, 1),
                'descendidos': _payload(descienden, 1, 2),
                'user_ascendio': res['user_asc'],
                'user_descendio': res['user_des'],
            }
        logger.info(f"Promo/releg {tipo_x}: ascendieron {[e.nombre for e in ascenden]} "
                    f"/ descendieron {[e.nombre for e in descienden]}")
    return res


def reiniciar_ligas(lista: Iterable) -> None:
    """Deja cada liga lista para una temporada nueva: tablas y estadísticas de temporada a cero, moral
    mínima 70, sin lesiones ni sanciones, energía llena, calendario vacío y jornada 1. No envejece."""
    from alpha_football.sanciones import nueva_temporada as _sanc_nueva
    for liga_r in lista:
        for eq in liga_r.equipos:
            eq.puntos = 0
            eq.sancion_puntos = 0           # v4.6.0: la sanción por quiebra dura una temporada
            eq.pj = 0
            eq.pg = 0
            eq.pe = 0
            eq.pp = 0
            eq.gf = 0
            eq.gc = 0
            for j in eq.jugadores:
                j.goles = 0
                j.asistencias = 0
                j.partidos_jugados = 0
                j.porterias_cero = 0
                j.moral = max(70, j.moral)
                j.lesion_dias = 0
                _sanc_nueva(j)              # sanciones y amarillas de liga y copa a cero
                j.energia = 100.0           # v3.1.0: pretemporada
        liga_r.calendario = []
        liga_r.jornada_actual = 1


def envejecer_ligas(lista: Iterable) -> None:
    """Desarrollo pasivo de fin de temporada (un año más + curva de media). Anual: en TU cierre, para todos."""
    from alpha_football.desarrollo import progresar_liga_pasivo
    for liga_r in lista:
        try:
            progresar_liga_pasivo(liga_r, 1)
        except Exception as e_dev_pasivo:
            logger.error(f"Error en desarrollo pasivo de fin de temporada: {e_dev_pasivo}")

# --- El otro continente, por fecha ────────────────────────────────────────────

def copa_de(cont: str) -> str:
    """La copa internacional de ese continente."""
    return 'libertadores' if cont == 'sudamerica' else 'champions'


def _clave_tabla(e) -> tuple:
    return (getattr(e, 'puntos', 0), getattr(e, 'gf', 0) - getattr(e, 'gc', 0), getattr(e, 'gf', 0))


def _jornadas_jugadas(liga) -> int:
    """Jornadas completas ya jugadas de esa liga."""
    pendientes = [p.jornada for p in (getattr(liga, 'calendario', None) or []) if not p.jugado]
    if not pendientes:
        return int(getattr(liga, 'num_jornadas', 0) or 0) if getattr(liga, 'calendario', None) else 0
    return min(pendientes) - 1


def _avanzar_copa_de(estado: dict, cont: str) -> None:
    """La copa de ese continente juega las fechas que vencieron con la jornada de sus ligas."""
    import random
    from alpha_football import competiciones as CP
    tipo = copa_de(cont)
    CP._asegurar(estado)
    c = CP.copa(estado, tipo)
    CP._avanzar_copa(estado, c, random.Random(), CP._jornada_copa(estado, tipo), jugar_user=False)
    # v0.4.27.0: el campeón se anuncia en cuanto se juega la final (aunque la simule el reloj). `_avanzar_copa` ya lo
    # hace; esta es la red de seguridad (idempotente) para una copa que ya tenía campeón sin anunciar.
    CP._anunciar_campeon(estado, c)


def poner_al_dia(estado: dict, fecha: date, cont: Optional[str] = None) -> int:
    """Con desfase: las ligas del continente `cont` (por defecto, el otro) juegan de fondo las jornadas
    cuyo sábado ya pasó el día `fecha`, y su copa juega las fechas que vencieron. Nunca toca tu liga.
    Devuelve las jornadas de liga jugadas (0 sin desfase)."""
    if not activo(estado):
        return 0
    from alpha_football.ui.league_screen import _simular_jornada_liga_fondo, inicializar_calendario_liga
    cont = cont or otro(CAL.continente(estado))
    liga_user = estado.get('liga')
    jugadas = 0
    for liga, _tipo, _division in ligas(estado, paises_de(cont)):
        if liga is liga_user:
            continue
        try:
            if not getattr(liga, 'calendario', None):
                inicializar_calendario_liga(liga)
            objetivo = jornadas_por_fecha(estado, liga, fecha)
            for _ in range(200):                             # tope de seguridad
                if _jornadas_jugadas(liga) >= objetivo or not _simular_jornada_liga_fondo(liga):
                    break
                jugadas += 1
        except Exception as e:
            logger.error(f"temporadas: no se pudo poner al día {getattr(liga, 'nombre', '?')}: {e}", exc_info=True)
    try:
        _avanzar_copa_de(estado, cont)
    except Exception as e:
        logger.error(f"temporadas: no se pudo avanzar la copa de {cont}: {e}", exc_info=True)
    return jugadas


def arrancar_desfase(estado: dict) -> bool:
    """F1 / F6: desfasa los continentes. Marca el mundo, fija el año de cada continente, sella la copa de
    tu continente, sortea la del otro y deja sus ligas en la jornada que les toca por fecha (a mitad de su
    temporada). Se llama al crear la carrera y, en un save viejo, al terminar su próximo cierre.
    False si ya estaba desfasado o no hay partida."""
    if activo(estado) or estado.get('liga') is None or estado.get('mi_equipo') is None:
        return False
    from alpha_football import temporada as T, competiciones as CP
    mio = CAL.continente(estado)
    el_otro = otro(mio)
    inicio = T.inicio(estado)                                 # el día en que empieza tu temporada
    anios = {mio: CAL.anio(estado), el_otro: anio_en(el_otro, inicio)}     # antes de marcar: CAL.anio lee el mundo
    m = mundo(estado)
    m['anio'] = anios
    m['desfase'] = True
    try:
        c_mia = CP.copa(estado, copa_de(mio))
        if c_mia is not None:
            c_mia['anio'] = anios[mio]                       # la tuya ya está sorteada: solo se sella
        CP.iniciar_temporada(estado, forzar=True, tipos=(copa_de(el_otro),))
    except Exception as e:
        logger.error(f"temporadas: no se pudieron preparar las copas del desfase: {e}", exc_info=True)
    jugadas = poner_al_dia(estado, inicio, el_otro)
    logger.info(f"Continentes desfasados: {el_otro} arranca con {jugadas} jornadas de liga ya jugadas (años {anios}).")
    return True


# --- El cierre del otro continente (F2) ───────────────────────────────────────

NOMBRE_CONTINENTE = {'europa': "Europa", 'sudamerica': "Sudamérica"}


def _congelar_premios(estado: dict, cont: str, campeon_copa: Optional[str]) -> None:
    """Con sus tablas finales intactas: guarda el podio de ese continente para tu Balón de Oro (se funde en
    tu cierre) y, si es Sudamérica, deja pendiente el Sudamericano del Año de la temporada que cerró."""
    from alpha_football import premios as PR, competiciones as CP
    paises = set(paises_de(cont))
    primeras = {t: l for t, l in (estado.get('primera_division') or {}).items() if t in paises}
    segundas = {t: l for t, l in (estado.get('segunda_division') or {}).items() if t in paises}
    copas = {copa_de(cont): CP.copa(estado, copa_de(cont))}
    temporada = int(estado.get('temporada', 1) or 1)
    datos = PR.calcular_balon_de_oro(primeras, segundas, temporada, campeon_copa, datos_copas=copas)
    mundo(estado).setdefault('balon', {})[cont] = list((datos or {}).get('podio') or [])
    if cont == 'sudamerica' and datos:
        pend = PR._pendientes(estado)
        pend[:] = [x for x in pend if not (isinstance(x, dict) and x.get('premio') == 'sudamericano')]
        pend.append({'premio': 'sudamericano', 'datos': datos,
                     'fecha_entrega': PR.fecha_entrega(estado, 'sudamericano').isoformat()})


def _noticias_cierre(estado: dict, cont: str, res: dict, anio_cerrado: Optional[int] = None) -> None:
    """v0.4.23.0 (antes, un correo de Prensa): noticia con los campeones de liga de la temporada del otro continente.
    v0.4.25.0: lleva SOLO los campeones de liga; los clubes que descienden van en su propia noticia (los mejores).
    v0.4.27.0: la copa no se nombra aquí: su campeón se anuncia solo cuando se gana la final (competiciones /
    `_copa` de `cerrar_continente`), nunca meses después en un cierre."""
    from alpha_football import noticias, noticias_gen
    from alpha_football.paises import pais_de
    nombre_t = noticias.nombre_anio(cont, anio_cerrado) if anio_cerrado is not None else str(anio(estado, cont))
    lineas = []
    for tipo in paises_de(cont):
        campeon = (res.get('campeones') or {}).get(tipo)
        if campeon:
            lineas.append(f"{(pais_de(tipo) or {}).get('nombre', tipo)}: {campeon}")
    if lineas:
        noticias.publicar(estado, 'campeon', f"Terminó la temporada en {NOMBRE_CONTINENTE.get(cont, cont)}",
                          f"Campeones de liga de la temporada {nombre_t}:\n\n" + "\n".join(lineas), importancia=4)
    noticias_gen.publicar_descensos_destacados(estado, res.get('movimientos'),
                                               ambito=NOMBRE_CONTINENTE.get(cont, cont))


def cerrar_continente(estado: dict, cont: str) -> dict:
    """F2: cierra la temporada de ese continente mientras la tuya sigue (el tuyo lo cierra
    avanzar_nueva_temporada). Termina su copa, congela sus premios, guarda las tablas finales, aplica nivel,
    despidos de DTs y ascensos/descensos, reinicia sus ligas (sin envejecer a nadie), cobra los ingresos,
    sube su año, sortea su copa nueva y te avisa por correo. Cada paso va bajo su propio control de
    errores: uno que falla se registra y el cierre sigue (el año sube siempre: si no, se repetiría cada día).
    Devuelve {'campeones': {país: club}, 'copa': club, 'movimientos': [...]}."""
    res = {'campeones': {}, 'copa': None, 'movimientos': []}
    if not activo(estado) or cont == CAL.continente(estado):
        return res
    from alpha_football import competiciones as CP, nivel_temporada as NT, entrenadores as EN, mercado_ia as MIA
    from alpha_football.ui.league_screen import completar_ligas_de_fondo
    from alpha_football.ui.copa_screen import guardar_ranking_copas
    paises = paises_de(cont)
    tipo_copa = copa_de(cont)
    m = mundo(estado)
    anio_cerrado = anio(estado, cont)

    def paso(nombre: str, fn) -> None:
        try:
            fn()
        except Exception as e:
            logger.error(f"temporadas: falló '{nombre}' al cerrar {cont}: {e}", exc_info=True)

    def _copa() -> None:
        CP.simular_todo(estado, tipos=(tipo_copa,))
        res['copa'] = CP.campeon(estado, tipo_copa)
        m.setdefault('campeones', {})[tipo_copa] = res['copa']
        # v0.4.27.0: si por lo que sea no salió al jugarse la final, el campeón se anuncia ahora, ANTES de sortear la
        # copa nueva (después `CP.copa` ya es la de la temporada siguiente y no tiene campeón)
        CP._anunciar_campeon(estado, CP.copa(estado, tipo_copa))

    def _campeones() -> None:
        for liga, tipo, division in ligas(estado, paises):
            if int(division or 1) == 1:
                res['campeones'][tipo] = max(liga.equipos, key=_clave_tabla).nombre

    def _ascensos() -> None:
        res['movimientos'] = ascensos_descensos(estado, paises)['movimientos']

    def _anio_y_copa_nuevos() -> None:
        CP.iniciar_temporada(estado, forzar=True, tipos=(tipo_copa,))

    paso("completar sus ligas", lambda: completar_ligas_de_fondo(estado, paises=paises))
    paso("terminar su copa", _copa)
    paso("campeones de liga", _campeones)
    paso("congelar premios", lambda: _congelar_premios(estado, cont, res['copa']))
    paso("tablas finales para la copa", lambda: guardar_ranking_copas(estado, paises=paises))
    paso("nivel de temporada", lambda: NT.preparar(estado, paises=paises))
    paso("despidos de DTs", lambda: EN.cierre_temporada(estado, paises=paises))
    paso("ascensos y descensos", _ascensos)
    paso("bajón por objetivos", lambda: NT.aplicar_objetivos(estado, paises=paises))
    paso("reiniciar sus ligas", lambda: reiniciar_ligas([l for l, _t, _d in ligas(estado, paises)]))
    paso("topes de nivel", lambda: NT.aplicar_topes(estado, paises=paises))
    paso("ingresos de sus clubes", lambda: MIA.ingresos_fin_temporada(estado, paises=paises))
    paso("objetivos de la IA", lambda: NT.foto_objetivos_ia(estado, paises=paises))
    m.setdefault('anio', {})[cont] = anio_cerrado + 1          # fuera de `paso`: sube pase lo que pase
    paso("sortear su copa nueva", _anio_y_copa_nuevos)
    paso("noticias del cierre", lambda: _noticias_cierre(estado, cont, res, anio_cerrado))
    logger.info(f"Cerró la temporada {anio_cerrado} de {cont}: copa {res['copa']}, {len(res['movimientos'])} países con ascensos.")
    return res


def revisar_jornada(estado: dict) -> None:
    """Cada día (dias.revisar_dia) y, sin reloj, al cerrar tu jornada: el otro continente juega lo que le
    toca por fecha y, si su temporada ya terminó, se cierra y empieza la siguiente. Idempotente; nunca toca
    tu continente. Sin desfase no hace nada."""
    try:
        if not activo(estado) or estado.get('liga') is None or estado.get('mi_equipo') is None:
            return
        from alpha_football import temporada as T
        hoy = T.fecha(estado)
        el_otro = otro(CAL.continente(estado))
        for _ in range(3):                                   # a lo sumo un cierre por llamada; 3 = margen
            limite = fin(estado, el_otro)
            poner_al_dia(estado, min(hoy, limite), el_otro)
            if hoy <= limite:
                break
            cerrar_continente(estado, el_otro)
    except Exception as e:
        logger.error(f"temporadas: error revisando el otro continente: {e}", exc_info=True)


def paises_al_ritmo_del_user(estado: dict) -> Optional[tuple]:
    """Los países cuyas ligas de fondo avanzan una jornada por cada jornada tuya: con desfase, los de tu
    continente; sin él, None (= todas, como siempre)."""
    return paises_de(CAL.continente(estado)) if activo(estado) else None

# --- Tu cierre de temporada (F3) ──────────────────────────────────────────────

def paises_cierre(estado: dict) -> Optional[tuple]:
    """Los países que cierra TU cierre de temporada: con desfase, los de tu continente; sin él, None
    (= todos, como siempre)."""
    return paises_de(CAL.continente(estado)) if activo(estado) else None


def subir_anio(estado: dict, cont: str) -> None:
    """Ese continente empieza una temporada nueva (solo con desfase: sin él el año sale de tu temporada)."""
    if activo(estado):
        mundo(estado).setdefault('anio', {})[cont] = anio(estado, cont) + 1


def campeones_copas(estado: dict, del_cierre: dict) -> dict:
    """Los campeones de las dos copas para el registro de tu temporada: con desfase, el de tu copa (recién
    terminada) y el último campeón conocido de la otra (la que cerró su continente)."""
    if not activo(estado):
        return dict(del_cierre)
    mia = copa_de(CAL.continente(estado))
    guardados = mundo(estado).setdefault('campeones', {})
    guardados[mia] = del_cierre.get(mia)
    return {tipo: (del_cierre.get(tipo) if tipo == mia else guardados.get(tipo)) for tipo in del_cierre}


def mapas_cierre(estado: dict, primeras: dict, segundas: dict) -> tuple:
    """(primeras, segundas) que entran en los premios de tu cierre: con desfase, solo tu continente."""
    paises = paises_cierre(estado)
    if paises is None:
        return primeras, segundas
    return ({t: l for t, l in (primeras or {}).items() if t in paises},
            {t: l for t, l in (segundas or {}).items() if t in paises})


def fundir_balon(estado: dict) -> None:
    """Tu cierre calculó el Balón de Oro solo con tu continente: se le suma el podio congelado del otro (su
    última temporada cerrada) y manda el puntaje. Sin desfase o sin podio congelado no hace nada."""
    if not activo(estado):
        return
    from alpha_football import premios as PR
    el_otro = otro(CAL.continente(estado))
    guardado = mundo(estado).setdefault('balon', {})
    congelado = list(guardado.get(el_otro) or [])
    if not congelado:
        return
    pend = PR._pendientes(estado)
    premio = next((x for x in pend if isinstance(x, dict) and x.get('premio') == 'balon_oro'), None)
    if premio is None:
        premio = {'premio': 'balon_oro', 'fecha_entrega': PR.fecha_entrega(estado, 'balon_oro').isoformat(),
                  'datos': {'temporada': int(estado.get('temporada', 2) or 2) - 1, 'podio': []}}
        pend.append(premio)
    datos = premio.setdefault('datos', {})
    podio = sorted(list(datos.get('podio') or []) + congelado,
                   key=lambda f: float((f or {}).get('puntaje', 0) or 0), reverse=True)[:3]
    datos['podio'], datos['ganador'] = podio, podio[0]
    guardado[el_otro] = []                                   # ya se usó: no cuenta dos veces

# --- Cambiar de continente (F5) ───────────────────────────────────────────────

def antes_de_cambiar_de_club(estado: dict) -> tuple:
    """(continente, día de hoy o None) antes de que cambies de club: lo necesita al_cambiar_de_club."""
    try:
        from alpha_football import dias
        return CAL.continente(estado), (dias.hoy(estado) if dias.activo(estado) else None)
    except Exception as e:
        logger.error(f"temporadas: no se pudo leer el estado previo al cambio de club: {e}")
        return CAL.continente(estado), None


def al_cambiar_de_club(estado: dict, cont_anterior: str, hoy_anterior: Optional[date] = None) -> None:
    """F5: aceptaste un club del otro continente. Sigues desde la jornada en que va esa liga, con su
    calendario y su año; el reloj conserva el día de hoy (no salta a tu próximo partido) y el continente
    que dejas pasa a avanzar por fecha. Sin desfase o sin cambio de continente no hace nada."""
    try:
        if not activo(estado) or cont_anterior == CAL.continente(estado):
            return
        liga = estado.get('liga')
        if liga is not None and not getattr(liga, 'calendario', None):
            from alpha_football.ui.league_screen import inicializar_calendario_liga
            inicializar_calendario_liga(liga)
        if hoy_anterior is not None:
            cal = CAL.asegurar(estado)                       # ya es el bloque del club nuevo
            prox = CAL.proximo_evento(estado)
            if prox is None or hoy_anterior <= prox['fecha']:
                cal['dia'] = hoy_anterior.isoformat()
        revisar_jornada(estado)
    except Exception as e:
        logger.error(f"temporadas: error al cambiar de continente: {e}", exc_info=True)
