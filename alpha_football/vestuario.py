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

# v0.4.18.0: el presidente felicita solo al llegar a estas victorias seguidas, cada vez más asombrado
FELICITACIONES_RACHA = {
    3: ("Tres victorias seguidas",
        "Míster, tres seguidas. Así da gusto ir al palco. Siga así, que la gente ya se ilusiona."),
    5: ("Cinco victorias seguidas",
        "Míster, ¡cinco seguidas! En la ciudad no se habla de otra cosa y la grada ya canta su nombre. "
        "Que no se le suba a nadie a la cabeza, pero esto es de equipo grande."),
    10: ("¡Diez victorias seguidas!",
         "¡Diez victorias seguidas, míster! No me lo puedo creer. Los socios me paran por la calle para "
         "darle las gracias y en el palco no se habla de otra cosa. Esto ya es historia del club."),
    15: ("¡Quince victorias seguidas!",
         "¡Quince seguidas! Míster, esto ya no es una racha, es un fenómeno. Los medios hablan de nosotros "
         "en todo el continente y yo no paro de recibir llamadas. ¡Qué orgullo de equipo!"),
    20: ("¡¡Veinte victorias seguidas!!",
         "¡¡Veinte victorias seguidas!! Míster, no tengo palabras. Nadie en la historia del club había llegado "
         "tan lejos. Los hinchas ya hablan de usted como de una leyenda. ¡Increíble, de verdad increíble!"),
    25: ("¡¡¡Veinticinco victorias seguidas!!!",
         "¡¡¡Veinticinco victorias seguidas!!! Míster, esto es de otro planeta. Los rivales nos miran con miedo, "
         "la prensa del mundo entero se ha rendido y yo sigo sin despertar del sueño. ¡Nunca vi algo igual!"),
    30: ("¡¡¡TREINTA victorias seguidas!!!",
         "¡¡¡TREINTA VICTORIAS SEGUIDAS!!! Míster, ¡esto es una locura! Ya no encuentro cómo agradecérselo: "
         "usted ha escrito la página más grande de la historia de este club y de todo el fútbol. "
         "¡Que nadie nos despierte, por favor, que nadie nos despierte!"),
}


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


MORAL_RACHA_SIN_GANAR = 10                        # v0.4.26.0: ganar tras 3+ partidos sin ganar sube a todos +10
PARTIDOS_SIN_GANAR = 3


def forma(j) -> float:
    notas = list(getattr(j, 'notas_recientes', []) or [])
    return sum(notas) / len(notas) if notas else 6.5


def impulso_moral(estado: dict, equipo, cantidad: int, motivo: str) -> int:
    """v0.4.26.0: sube la moral de TODA la plantilla `cantidad` puntos (tope 100) y deja la causa en la última
    entrada de `causas_moral` (claves 'impulso' = lo que subió y 'motivo_impulso'; las bajas siguen en
    minutos/equipo/sueldo). Sin `equipo`, el del user. Devuelve cuántos jugadores subieron.
    Lo usan: ganar tras 3+ sin ganar (+10, post_partido_user), título (+25) y pasar de fase en copa (+8)."""
    try:
        equipo = equipo if equipo is not None else (estado or {}).get('mi_equipo')
        cantidad = int(cantidad)
        if equipo is None or cantidad <= 0:
            return 0
        subieron = 0
        for j in list(getattr(equipo, 'jugadores', []) or []):
            antes = int(getattr(j, 'moral', 70))
            j.moral = min(100, antes + cantidad)
            causas = list(getattr(j, 'causas_moral', []) or [])
            if causas and isinstance(causas[-1], dict):
                ultima = causas[-1]
            else:
                ultima = {'minutos': 0, 'equipo': 0, 'sueldo': 0}
                causas.append(ultima)
            ultima['impulso'] = int(ultima.get('impulso', 0) or 0) + (j.moral - antes)
            ultima['motivo_impulso'] = str(motivo)
            j.causas_moral = causas[-4:]
            if j.moral > antes:
                subieron += 1
        return subieron
    except Exception as e:
        logger.error(f"No se pudo dar el impulso de moral ({motivo}): {e}")
        return 0


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


def _correos_forma(estado: dict, user_eq, reporte: list) -> None:
    """v0.4.26.0: correo (Secretaría técnica) cuando un jugador de tu club entra en racha imparable y cuando
    termina, con lo que avanzó durante la racha. Los eventos vienen en el reporte del desarrollo (forma_evento)."""
    propios = {id(j) for j in getattr(user_eq, 'jugadores', []) or []}
    try:
        from alpha_football import correo as C
        from alpha_football.forma import PARTIDOS_IMPARABLE
        for r in reporte or []:
            ev, j = r.get('forma_evento'), r.get('obj')
            if not ev or j is None or id(j) not in propios:
                continue
            nombre = f"{j.nombre} {j.apellido}"
            if ev.get('tipo') == 'entra':
                C.enviar(estado, 'club', f"{nombre} está imparable",
                         f"{nombre} lleva tres partidos seguidos de nota altísima y atraviesa un momento de forma "
                         f"extraordinario. Durante los próximos {PARTIDOS_IMPARABLE} partidos progresará el doble de rápido "
                         "en media y en potencial: conviene que siga jugando.",
                         C.accion('plantilla_screen', "VER PLANTILLA"), jugador=j)
            elif ev.get('tipo') == 'sale':
                ganado = f"+{ev.get('media', 0)} de media / +{ev.get('potencial', 0)} de potencial"
                C.enviar(estado, 'club', f"Termina la racha de {nombre}",
                         f"{nombre} cierra su racha imparable y vuelve a una forma buena. Lo que avanzó mientras duró: "
                         f"{ganado}.", C.accion('plantilla_screen', "VER PLANTILLA"), jugador=j)
    except Exception as e:
        logger.error(f"No se pudo avisar la forma de los jugadores: {e}")


# v0.4.26.0 (ítem 9): bonus de potencial al cerrar la temporada, más jugadores y más puntos.
# Antes: ≤24 con moral ≥75 y promedio ≥6.5 → 40 % +1 / 15 % +2 (media +0.70). Ahora: moral ≥70 y promedio ≥6.3
# (o forma buena/imparable) → 53 % +1 / 25 % +2 / 7 % +3 (media +1.24), y con promedio ≥7.0 un punto más (tope +3).
CORTES_POT_TEMPORADA = ((0.07, 3), (0.32, 2), (0.85, 1))


def cierre_temporada(estado: dict, rng: Optional[random.Random] = None) -> list:
    """Jóvenes (≤24) con buena moral y buena temporada suben de potencial (ver CORTES_POT_TEMPORADA)."""
    azar = rng or random.Random()
    mi = estado.get('mi_equipo')
    textos = []
    from alpha_football import forma as FO
    for j in list(getattr(mi, 'jugadores', []) or []):
        en_forma = FO.nivel(j) in ('buena', 'imparable')
        if (int(j.edad) <= 24 and float(j.promedio_nota) >= 6.3 and (int(j.moral) >= 70 or en_forma)
                and int(j.partidos_jugados) > 0 and int(j.potencial) > 0):
            r = azar.random()
            inc = next((p for corte, p in CORTES_POT_TEMPORADA if r < corte), 0)
            if inc and float(j.promedio_nota) >= 7.0:
                inc = min(3, inc + 1)
            if inc:
                j.potencial = min(99, j.potencial + inc)
                textos.append(f"{j.nombre} {j.apellido} +{inc} de potencial")
    if textos:
        try:
            from alpha_football import correo as C
            C.enviar(estado, 'club', f"Suben de potencial: {len(textos)} joven{'es' if len(textos) != 1 else ''}",
                     "Gracias a su buena moral y a una buena temporada, suben de potencial: " + "; ".join(textos) + ".",
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
                         f"Tras la revisión médica, el jugador estará de baja por {E.texto_lesion(inc['dias'])}. Le "
                         "avisaremos cuando reciba el alta.", C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
            elif inc['tipo'] == 'aviso_amarillas':
                C.enviar(estado, 'club', f"En riesgo: {j.nombre} {j.apellido} tiene {S.amarillas(j, comp)} amarillas",
                         f"El jugador acumula {S.amarillas(j, comp)} amarillas {de_comp}: si ve otra, se perderá el "
                         f"próximo partido {de_comp}.",
                         C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
            elif inc.get('motivo') == 'acumulacion':
                C.enviar(estado, 'club', f"Suspensión por acumulación: {j.nombre} {j.apellido}",
                         f"El jugador ha llegado a {S.limite(comp)} amarillas {de_comp} y se perderá el próximo "
                         f"partido {de_comp}.",
                         C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
            else:
                C.enviar(estado, 'club', f"Suspensión: {j.nombre} {j.apellido}",
                         f"Tras su expulsión, el jugador se perderá {inc['partidos']} partido(s) {de_comp}.",
                         C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
        clasico = es_clasico(user_eq, rival)
        jugaron = {jid for jid, m in minutos.items() if int(m or 0) > 0}
        res = actualizar_moral(user_eq, reporte, gf, gc, clasico, jugaron, rng=azar, no_disponibles=no_disp)
        # v0.4.26.0 (ítem 15): ganar después de 3+ partidos sin ganar levanta al vestuario (+10 a todos).
        # 'ult_res' guarda los últimos 3 resultados y se actualiza más abajo, así que aquí aún no cuenta este partido.
        previos = list((estado.get('datos_carrera') or {}).get('ult_res', []) or [])
        if gf > gc and len(previos) >= PARTIDOS_SIN_GANAR and all(r != 'G' for r in previos[-PARTIDOS_SIN_GANAR:]):
            impulso_moral(estado, user_eq, MORAL_RACHA_SIN_GANAR, 'racha_sin_ganar')
        _correos_forma(estado, user_eq, reporte)
        for j in res['quejas']:
            C.enviar(estado, 'jugador', f"{j.nombre} {j.apellido} está molesto",
                     f"Míster, no estoy bien (moral {j.moral}). Entre los minutos, el contrato y cómo me estoy "
                     f"sintiendo, algo no está funcionando. Me gustaría hablarlo con usted.\n{j.nombre} {j.apellido}",
                     C.accion('plantilla_screen', "VER PLANTILLA"), jugador=j)
        for j in res['pide_salir']:
            C.enviar(estado, 'jugador', f"{j.nombre} {j.apellido} quiere irse",
                     f"Míster, llevo semanas sin estar a gusto y creo que lo mejor es que salga del club. "
                     f"Le pido que escuche las ofertas que lleguen por mí.\n{j.nombre} {j.apellido}",
                     C.accion('plantilla_screen', "VER PLANTILLA"), jugador=j)
        dc = estado.setdefault('datos_carrera', {})
        if clasico:
            dc['confianza'] = max(0, min(100, D.confianza(estado) + (6 if gf > gc else -6 if gf < gc else 0)))
            if gf > gc:
                C.enviar(estado, 'presidente', f"¡Ganamos el clásico a {rival.nombre}!",
                         "Míster, hoy da gusto ser presidente de este club. La gente está feliz y yo también. "
                         "Felicite de mi parte a los muchachos.")   # v0.4.10.0
            elif gf < gc:
                D.ajustar_calif(estado, D.CALIF['clasico_perdido'])
            p = D.pedido_activo(estado)
            if p and p.get('tipo') == 'clasico' and rival.nombre in p.get('texto', ''):
                D.resolver_pedido(estado, gf > gc)
        racha = (list(dc.get('racha', [])) + ['G' if gf > gc else 'P' if gf < gc else 'E'])[-3:]
        dc['racha'] = racha
        # v0.4.10.0: últimos 3 resultados SIN reiniciar (racha se vacía al avisar): eventos.va_mal
        dc['ult_res'] = (list(dc.get('ult_res', [])) + ['G' if gf > gc else 'P' if gf < gc else 'E'])[-3:]
        # v0.4.18.0: victorias seguidas contadas aparte (racha_g): felicita solo en los hitos de HITOS_RACHA
        dc['racha_g'] = int(dc.get('racha_g', 0) or 0) + 1 if gf > gc else 0
        if dc['racha_g'] in FELICITACIONES_RACHA:
            asunto, cuerpo = FELICITACIONES_RACHA[dc['racha_g']]
            C.enviar(estado, 'presidente', asunto, cuerpo)
        if racha == ['P'] * 3:
            C.enviar(estado, 'presidente', "Tres derrotas seguidas: tenemos que hablar",
                     "Míster, tres derrotas al hilo. Me paran en la calle para preguntarme qué pasa y ya no sé "
                     "qué contestar. Necesito una reacción ya.",
                     C.accion('objetivos_screen', "VER OBJETIVOS"))
            dc['racha'] = []
    except Exception as e:
        logger.error(f"Error en el cierre de vestuario del partido: {e}")
    return incid
