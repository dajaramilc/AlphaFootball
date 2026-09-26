# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Vestuario (v3.1.0)
Moral por jornada, personalidades, pide-salir, clásicos y cierre de partido del user.
Sin UI. No importa models a nivel de módulo (models importa personalidad_inicial de aquí).
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

PERSONALIDADES = ('normal', 'lider', 'profesional', 'polemico', 'mercenario')
PESOS_PERSONALIDAD = (70, 8, 10, 7, 5)


def personalidad_inicial(rasgo: Optional[str], semilla: str) -> str:
    if rasgo == 'lider':
        return 'lider'
    return random.Random(f"per|{semilla}").choices(PERSONALIDADES, weights=PESOS_PERSONALIDAD)[0]


PERSONALIDAD_TXT = {'normal': "Normal", 'lider': "Líder", 'profesional': "Profesional",
                    'polemico': "Polémico", 'mercenario': "Mercenario"}
UMBRAL_PIDE_SALIR = {'polemico': 3, 'lider': 5}   # v4.4.0: antes polémico 4 y el líder nunca
JORNADAS_PIDE_SALIR = 4                           # v4.4.0: antes 6
# moral por resultado (antes de duplicar las bajas con MULT_BAJA_MORAL): las derrotas pesan
# menos que antes (−2 / clásico −6 / nota < 5.5 −3) para que una mala racha no hunda al plantel
MORAL_VICTORIA, MORAL_DERROTA = 2, -1
MORAL_CLASICO_GANADO, MORAL_CLASICO_PERDIDO = 5, -4
MORAL_NOTA_BAJA = -2
UMBRAL_MORAL_SALIR = 50                           # v4.4.0: moral < 50 cuenta como jornada mala (antes ≤ 30)
MULT_BAJA_MORAL = 2                               # v4.4.0: toda baja de moral pesa el doble
SUELDO_MINIMO_MORAL = 0.8                         # v4.4.0: cobrar < 80% del mercado baja la moral (antes 60%)


def forma(j) -> float:
    notas = list(getattr(j, 'notas_recientes', []) or [])
    return sum(notas) / len(notas) if notas else 6.5


def _mitad(delta: int) -> int:
    return int(delta / 2)


def actualizar_moral(equipo, reporte: list, gf: int, gc: int, es_clasico: bool, jugaron_ids: set,
                     rng: Optional[random.Random] = None, no_disponibles: Optional[set] = None) -> dict:
    """Moral del plantel del user tras un partido (liga o copa). Ver spec §B y §D."""
    azar = rng or random.Random()
    from alpha_football.finanzas import salario_mercado
    js = list(getattr(equipo, 'jugadores', []) or [])
    notas = {r.get('id'): float(r.get('nota', 6.0)) for r in reporte or []}
    gano, perdio = gf > gc, gf < gc
    d_equipo = ((MORAL_VICTORIA if gano else MORAL_DERROTA if perdio else 0)
                + ((MORAL_CLASICO_GANADO if gano else MORAL_CLASICO_PERDIDO if perdio else 0) if es_clasico else 0))
    hay_lider = any(j.personalidad == 'lider' and j.id in jugaron_ids for j in js)
    if d_equipo < 0 and hay_lider:
        d_equipo = _mitad(d_equipo)
    top5 = {id(j) for j in sorted(js, key=lambda x: -x.overall)[:5]}
    media_plantel = sum(j.overall for j in js) / len(js) if js else 0
    salida = {'quejas': [], 'pide_salir': []}       # v4.4.0: 'quejas' ya no se usa (salidas.py escribe)
    for j in js:
        antes = int(j.moral)
        prof = j.personalidad == 'profesional'
        causas = {'minutos': 0, 'equipo': 0, 'sueldo': 0}     # v4.4.0: bajas por causa (antes del ×2)
        d = max(0, d_equipo)
        causas['equipo'] += min(0, d_equipo)
        if j.id in notas:
            if notas[j.id] >= 7:
                d += 3
            elif notas[j.id] < 5.5:
                causas['equipo'] += MORAL_NOTA_BAJA
        if (id(j) in top5 and j.id not in jugaron_ids and j.disponible
                and j.id not in (no_disponibles or set())):
            causas['minutos'] -= 1 if prof else 3
        # v4.4.0: 3+ partidos seguidos sin jugar siendo de los buenos del plantel
        if j.id in jugaron_ids:
            j.jornadas_sin_jugar = 0
        elif j.disponible and j.id not in (no_disponibles or set()):
            j.jornadas_sin_jugar = int(getattr(j, 'jornadas_sin_jugar', 0) or 0) + 1
        if j.jornadas_sin_jugar >= 3 and j.overall >= media_plantel:
            causas['minutos'] -= 1
        if int(getattr(j, 'salario', 0) or 0) and j.salario < SUELDO_MINIMO_MORAL * salario_mercado(j):
            causas['sueldo'] -= 1 if prof else 4 if j.personalidad == 'mercenario' else 2
        if len(getattr(j, 'notas_recientes', []) or []) >= 3 and forma(j) < 5.5:
            causas['equipo'] -= 2
        causas = {k: v * MULT_BAJA_MORAL for k, v in causas.items()}
        d += sum(causas.values())
        if d == 0 and antes < 70:                   # v4.4.0: la deriva a 70 solo sube
            d = 1
        j.moral = max(0, min(100, antes + d))
        j.causas_moral = (list(getattr(j, 'causas_moral', []) or []) + [causas])[-4:]
    for j in js:                                    # el polémico descontento contagia
        if j.personalidad == 'polemico' and j.moral < 40:
            otros = [o for o in js if o is not j]
            for o in azar.sample(otros, min(3, len(otros))):
                o.moral = max(0, o.moral - MULT_BAJA_MORAL)
                if o.causas_moral:
                    o.causas_moral[-1]['equipo'] = int(o.causas_moral[-1].get('equipo', 0)) - MULT_BAJA_MORAL
    for j in js:
        j.jornadas_moral_baja = j.jornadas_moral_baja + 1 if j.moral < UMBRAL_MORAL_SALIR else 0
        umbral = UMBRAL_PIDE_SALIR.get(j.personalidad, JORNADAS_PIDE_SALIR)
        if not j.pide_salir and j.jornadas_moral_baja >= umbral:
            j.pide_salir = True
            if not getattr(j, 'prestamo', None):    # a préstamo: no es tuyo, no se pone transferible
                j.transferible = True               # v4.4.0: queda en transferibles, bloqueado
            salida['pide_salir'].append(j)
    return salida


def cierre_temporada(estado: dict, rng: Optional[random.Random] = None) -> list:
    """Jóvenes (≤24) con moral ≥75 y promedio ≥6.5: 40% +1 / 15% +2 de potencial."""
    azar = rng or random.Random()
    mi = estado.get('mi_equipo')
    textos = []
    for j in list(getattr(mi, 'jugadores', []) or []):
        if (int(j.edad) <= 24 and int(j.moral) >= 75 and float(j.promedio_nota) >= 6.5
                and int(j.partidos_jugados) > 0 and int(j.potencial) > 0):
            r = azar.random()
            inc = 2 if r < 0.15 else 1 if r < 0.55 else 0
            if inc:
                j.potencial = min(99, j.potencial + inc)
                textos.append(f"{j.nombre} {j.apellido} +{inc} de potencial")
    if textos:
        try:
            from alpha_football import correo as C
            C.enviar(estado, 'club', f"Suben de potencial: {len(textos)} joven{'es' if len(textos) != 1 else ''}",
                     "Buena moral y buena temporada: " + "; ".join(textos) + ".",
                     C.accion('plantilla_screen', "VER PLANTILLA"))
        except Exception as e:
            logger.error(f"No se pudo avisar el bonus de potencial: {e}")
    return textos


def post_partido_user(estado: dict, user_eq, rival, gf: int, gc: int, reporte: list, minutos: dict,
                      rng: Optional[random.Random] = None, incidencias: Optional[list] = None,
                      incidencias_rival: Optional[list] = None, minutos_rival: Optional[dict] = None) -> list:
    """
    Cierre del partido del user (liga o copa, vivo o instantáneo): físico de ambos equipos,
    lesiones/sanciones por correo, moral, clásico y rachas. Nunca en amistosos.
    v4.0.0: `incidencias`/`incidencias_rival` = las del partido (partido_ctx.incidencias_de); con
    ellas no se sortean lesiones ni rojas al cierre. `minutos_rival` = minutos reales del rival.
    """
    from alpha_football import energia as E, correo as C, directiva as D
    from alpha_football.data.clasicos import es_clasico
    from alpha_football.engine import _once_titular
    azar = rng or random.Random()
    incid = []
    try:
        if minutos_rival is None:
            minutos_rival = {j.id: 90 for j in _once_titular(rival)}
        no_disp = {j.id for j in user_eq.jugadores if not j.disponible}   # antes de descontar el partido
        incid = E.cerrar_partido(user_eq, minutos, rng=azar, incidencias=incidencias)
        E.cerrar_partido(rival, minutos_rival, rng=azar, incidencias=incidencias_rival)
        for inc in incid:
            j = inc['jugador']
            from alpha_football import sanciones as S
            comp = inc.get('competicion') or S.competicion_actual()
            de_comp = "de copa" if comp == 'copa' else "de liga"
            if inc['tipo'] == 'lesion':
                C.enviar(estado, 'medico', f"Lesión: {j.nombre} {j.apellido}",
                         f"Estará fuera {inc['partidos']} partido(s).", C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
            elif inc['tipo'] == 'aviso_amarillas':
                C.enviar(estado, 'club', f"En riesgo: {j.nombre} {j.apellido} tiene {S.amarillas(j, comp)} amarillas",
                         f"Lleva {S.amarillas(j, comp)} amarillas {de_comp}: si ve otra, se pierde el próximo partido {de_comp}.",
                         C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
            elif inc.get('motivo') == 'acumulacion':
                C.enviar(estado, 'club', f"Suspensión por acumulación: {j.nombre} {j.apellido}",
                         f"Llegó a {S.limite(comp)} amarillas {de_comp}: se pierde el próximo partido {de_comp}.",
                         C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
            else:
                C.enviar(estado, 'club', f"Suspensión: {j.nombre} {j.apellido}",
                         f"Expulsado: se pierde {inc['partidos']} partido(s) {de_comp}.",
                         C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
        clasico = es_clasico(user_eq, rival)
        jugaron = {jid for jid, m in minutos.items() if int(m or 0) > 0}
        res = actualizar_moral(user_eq, reporte, gf, gc, clasico, jugaron, rng=azar, no_disponibles=no_disp)
        for j in res['quejas']:
            C.enviar(estado, 'jugador', f"{j.nombre} {j.apellido} está molesto",
                     f"Su moral bajó a {j.moral}. Minutos, contrato o forma: algo no le gusta.",
                     C.accion('plantilla_screen', "VER PLANTILLA"))
        for j in res['pide_salir']:
            C.enviar(estado, 'jugador', f"{j.nombre} {j.apellido} quiere irse",
                     "Lleva semanas descontento y pide salir. Atraerá ofertas como un transferible.",
                     C.accion('plantilla_screen', "VER PLANTILLA"))
        dc = estado.setdefault('datos_carrera', {})
        if clasico:
            dc['confianza'] = max(0, min(100, D.confianza(estado) + (6 if gf > gc else -6 if gf < gc else 0)))
            if gf > gc:
                C.enviar(estado, 'directiva', f"¡Ganaste el clásico a {rival.nombre}!",
                         "La afición y la directiva lo celebran.")
            elif gf < gc:
                D.ajustar_calif(estado, D.CALIF['clasico_perdido'])
            p = D.pedido_activo(estado)
            if p and p.get('tipo') == 'clasico' and rival.nombre in p.get('texto', ''):
                D.resolver_pedido(estado, gf > gc)
        racha = (list(dc.get('racha', [])) + ['G' if gf > gc else 'P' if gf < gc else 'E'])[-3:]
        dc['racha'] = racha
        if racha == ['G'] * 3:
            C.enviar(estado, 'directiva', "Tres victorias seguidas", "La directiva felicita al cuerpo técnico.")
            dc['racha'] = []
        elif racha == ['P'] * 3:
            C.enviar(estado, 'directiva', "Advertencia: tres derrotas seguidas", "Esperamos una reacción inmediata.",
                     C.accion('objetivos_screen', "VER OBJETIVOS"))
            dc['racha'] = []
    except Exception as e:
        logger.error(f"Error en el cierre de vestuario del partido: {e}")
    return incid
