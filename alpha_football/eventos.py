# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Eventos aleatorios de vestuario (v0.4.10.0)
Un sorteo por jornada de liga del user. El evento llega por correo (MENSAJES si lo escribe el
jugador, CORREO si lo informa el club) y pide una decisión; cada opción tiene efectos en moral,
forma, energía, sanción, lesión, dinero, confianza y desarrollo. Sin responder, a la jornada
siguiente se aplica la opción por defecto.
IMPORTANTE: toda resolución deja una noticia en datos_carrera['noticias'] (titular + cuerpo en
tono de prensa): de ahí leerá la futura sección NOTICIAS. Sin UI.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from alpha_football import correo as C

logger = logging.getLogger(__name__)

PROB_BASE = 0.12
PROB_MAL = 0.45
ENFRIAMIENTO = 6            # jornadas sin repetir el mismo evento
JORNADAS_MIN_TABLA = 4      # antes de esto la tabla no dice si el equipo va mal


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _nom(j) -> str:
    return f"{getattr(j, 'nombre', '')} {getattr(j, 'apellido', '')}".strip()


def _plantel(estado: dict) -> list:
    return list(getattr(estado.get('mi_equipo'), 'jugadores', []) or [])


def _disp(estado: dict) -> list:
    return [j for j in _plantel(estado) if j.disponible]


def _jornada(estado: dict) -> list:
    from alpha_football.salidas import _clave_jornada
    return _clave_jornada(estado)


def _abs(estado: dict) -> int:
    t, j = _jornada(estado)
    return t * 100 + j


def va_mal(estado: dict) -> bool:
    """2+ derrotas en los últimos 3 partidos, o muy por debajo del puesto esperado en la tabla."""
    if list(_dc(estado).get('ult_res', []))[-3:].count('P') >= 2:
        return True
    try:
        from alpha_football.entrenadores import _va_mal
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        return bool(liga is not None and mi is not None and _jornada(estado)[1] >= JORNADAS_MIN_TABLA
                    and _va_mal(liga, mi))
    except Exception as e:
        logger.debug(f"No se pudo leer la tabla para los eventos: {e}")
        return False


# ---------------------------------------------------------------- noticias
def noticias(estado: dict) -> list:
    from alpha_football import noticias as _noticias
    return _noticias.lista(estado)


def registrar_noticia(estado: dict, titular: str, cuerpo: str, tipo: str = 'vestuario',
                      jugadores: Optional[list] = None, evento: str = '', opcion: Optional[int] = None) -> dict:
    """v0.4.23.0: envoltorio del núcleo (noticias.publicar): la consecuencia del evento sale en NOTICIAS."""
    from alpha_football import noticias as _noticias
    ids = list(jugadores or [])
    mi = estado.get('mi_equipo')
    n = _noticias.publicar(estado, tipo, titular, cuerpo, jugadores=ids,
                           equipos=[mi] if mi is not None else (), evento=evento, opcion=opcion)
    n['jugadores'] = ids
    return n


# ---------------------------------------------------------------- efectos
def _objetivos(estado: dict, quien, prot: list, rng: random.Random) -> list:
    if quien == 'j':
        return prot[:1]
    if quien == 'j2':
        return prot[1:2]
    if quien == 'plantel':
        return _plantel(estado)
    if isinstance(quien, str) and quien.startswith('otros:'):
        otros = [j for j in _disp(estado) if j not in prot]
        return rng.sample(otros, min(int(quien[6:]), len(otros)))
    return []


def _dinero(monto: int) -> str:
    return f"${abs(int(monto)):,}".replace(',', '.')


def _frase(clave: str, quien: str, v) -> str:
    if clave == 'moral':
        return f"{quien}: moral {v:+d}"
    if clave == 'energia':
        return f"{quien}: energía {v:+d}"
    if clave == 'forma':
        return f"{quien}: forma {'al alza' if v >= 6.5 else 'a la baja'}"
    if clave == 'sancion':
        return f"{quien}: apartado {v} partido{'s' if v != 1 else ''} de liga"
    if clave == 'lesion':
        from alpha_football.energia import texto_lesion      # v0.4.19.0: los valores son semanas de baja (x7 = días)
        return f"{quien}: baja {texto_lesion(int(v) * 7)}"
    if clave == 'progreso':
        return f"{quien}: acelera su desarrollo"
    return f"{quien}: le diste tu palabra"


def aplicar(estado: dict, efectos: list, prot: list, rng: Optional[random.Random] = None) -> list:
    """Aplica los efectos y devuelve una línea por efecto (para el resumen del correo)."""
    from alpha_football import sanciones as S
    azar = rng or random.Random()
    mi = estado.get('mi_equipo')
    out = []
    for ef in efectos or []:
        clave = ef[0]
        if clave == 'azar':
            out += aplicar(estado, ef[2] if azar.random() < ef[1] else ef[3], prot, azar)
            continue
        if clave == 'texto':
            out.append(ef[1])
            continue
        if clave == 'confianza':
            from alpha_football import directiva as D
            _dc(estado)['confianza'] = max(0, min(100, D.confianza(estado) + int(ef[2])))
            out.append(f"Confianza de la directiva {int(ef[2]):+d}")
            continue
        _, quien, valor = ef
        objs = _objetivos(estado, quien, prot, azar)
        if not objs:
            continue
        etiqueta = "El plantel" if quien == 'plantel' else ", ".join(_nom(j) for j in objs)
        if clave == 'dinero':
            monto = int(sum(int(getattr(j, 'salario', 0) or 0) for j in objs) * valor)
            mi.balance = int(mi.balance) + monto
            try:   # v0.4.27.0: historial de transacciones (solo el historial: el libro de la temporada no lo cuenta)
                from alpha_football.finanzas import anotar_movimiento
                anotar_movimiento(estado, "Multa cobrada por la directiva" if monto >= 0 else "Gasto del club (evento)",
                                  monto, 'evento')
            except Exception as e_hist:
                logger.error(f"No se pudo anotar el evento en el historial de transacciones: {e_hist}")
            out.append(("Multa cobrada: " if monto >= 0 else "Gasto del club: ") + _dinero(monto))
            continue
        v = azar.randint(*valor) if isinstance(valor, tuple) else valor
        for j in objs:
            if clave == 'moral':
                j.moral = max(0, min(100, int(j.moral) + v))
            elif clave == 'energia':
                j.energia = max(0.0, min(100.0, float(j.energia) + v))
            elif clave == 'forma':
                j.notas_recientes = (list(getattr(j, 'notas_recientes', []) or []) + [float(v)])[-5:]
            elif clave == 'sancion':
                S.sumar_sancion(j, int(v), 'liga')
            elif clave == 'lesion':
                j.lesion_dias = int(getattr(j, 'lesion_dias', 0) or 0) + int(v) * 7
            elif clave == 'progreso':
                j.progreso_desarrollo = float(getattr(j, 'progreso_desarrollo', 0.0) or 0.0) + float(v)
            elif clave == 'promesa':
                ahora = _abs(estado)
                _dc(estado).setdefault('promesas', []).append(
                    {'tipo': v['tipo'], 'jugador': j.id, 'creada': ahora, 'vence': ahora + int(v['jornadas']),
                     'falla': int(v['falla']), 'salario': int(getattr(j, 'salario', 0) or 0)})
        out.append(_frase(clave, etiqueta, v))
    return out


# ---------------------------------------------------------------- promesas
def revisar_promesas(estado: dict) -> None:
    """Promesas del DT (minutos, aumento): cumplidas se borran; vencidas sin cumplir, el jugador estalla."""
    ahora = _abs(estado)
    por_id = {j.id: j for j in _plantel(estado)}
    quedan = []
    for p in list(_dc(estado).get('promesas', [])):
        j = por_id.get(p.get('jugador'))
        if j is None:
            continue
        if p['tipo'] == 'aumento' and int(getattr(j, 'salario', 0) or 0) > int(p.get('salario', 0)):
            continue
        if p['tipo'] == 'minutos' and ahora > int(p.get('creada', ahora)) and not int(getattr(j, 'jornadas_sin_jugar', 0) or 0):
            continue
        if ahora < int(p['vence']):
            quedan.append(p)
            continue
        j.moral = max(0, min(100, int(j.moral) + int(p['falla'])))
        que = "los minutos que me prometió" if p['tipo'] == 'minutos' else "el aumento que me prometió"
        C.enviar(estado, 'jugador', f"{_nom(j)}: usted no cumplió",
                 f"Míster, sigo esperando {que}. Yo cumplí mi parte y usted no la suya. Que conste.\n{_nom(j)}",
                 jugador=j)
        registrar_noticia(estado, f"{_nom(j)}, molesto con el técnico",
                          f"El jugador asegura en su entorno que el entrenador no cumplió {que.replace('me prometió', 'le prometió')}.",
                          jugadores=[j.id], evento='promesa_rota')
    _dc(estado)['promesas'] = quedan


# ---------------------------------------------------------------- catálogo
def _uno(estado: dict, rng: random.Random, filtro=lambda j: True) -> Optional[list]:
    c = [j for j in _disp(estado) if filtro(j)]
    return [rng.choice(c)] if c else None


def _dos(estado: dict, rng: random.Random, f1=lambda j: True, f2=lambda j: True) -> Optional[list]:
    a = _uno(estado, rng, f1)
    if not a:
        return None
    b = [j for j in _disp(estado) if j is not a[0] and f2(j)]
    return a + [rng.choice(b)] if b else None


def _pais_liga(estado: dict) -> str:
    try:
        from alpha_football.cantera import _tipo_liga
        from alpha_football.retiros import PAIS_POR_LIGA
        return PAIS_POR_LIGA.get(_tipo_liga(estado, estado.get('mi_equipo')), '')
    except Exception:
        return ''


def _media(estado: dict) -> float:
    js = _plantel(estado)
    return sum(j.overall for j in js) / len(js) if js else 0


def _figura(estado: dict, rng: random.Random) -> Optional[list]:
    d = _disp(estado)
    return [max(d, key=lambda j: j.overall)] if d else None


def _extranjero(estado: dict, rng: random.Random) -> Optional[list]:
    pais = _pais_liga(estado)
    return _uno(estado, rng, lambda j: bool(j.nacionalidad) and bool(pais) and j.nacionalidad != pais)


def _seleccionable(estado: dict, rng: random.Random) -> Optional[list]:
    top = sorted(_disp(estado), key=lambda j: -j.overall)[:8]
    c = [j for j in top if j.nacionalidad]
    return [rng.choice(c)] if c else None


EVENTOS: list = [
    {'id': 'rina', 'peso': 4, 'peso_mal': 60, 'solo_mal': True, 'remitente': 'jugador', 'defecto': 2,
     'elige': lambda e, r: _uno(e, r, lambda j: j.personalidad == 'polemico'),
     'asunto': "{j} armó una riña en el vestuario",
     'cuerpo': "A ver, {dt}, se lo digo por escrito porque en el vestuario ya me oyeron todos: este equipo da "
               "pena y el primer responsable es usted. Hoy casi nos vamos a las manos y la próxima no me agarra "
               "nadie. Usted de fútbol sabe lo que yo de ballet. Si no le gusta lo que lee, ya sabe dónde "
               "encontrarme: en la cancha no, porque ahí usted ni aparece.\n{j}",
     # v0.4.26.0: la redacción se sortea entre estas (asunto, cuerpo); la de arriba es la primera
     'variantes': [
         ("{j} armó una riña en el vestuario",
          "A ver, {dt}, se lo digo por escrito porque en el vestuario ya me oyeron todos: este equipo da "
          "pena y el primer responsable es usted. Hoy casi nos vamos a las manos y la próxima no me agarra "
          "nadie. Usted de fútbol sabe lo que yo de ballet. Si no le gusta lo que lee, ya sabe dónde "
          "encontrarme: en la cancha no, porque ahí usted ni aparece.\n{j}"),
         ("{j} explotó en el vestuario",
          "{dt}, para que no se entere por terceros: hoy exploté. Le dije a medio plantel lo que pienso de "
          "este equipo y de cómo lo maneja usted. Hubo gritos, empujones y un botiquín por el suelo. No me "
          "arrepiento de nada, así que no espere disculpas.\n{j}"),
         ("Escándalo en el vestuario: {j} se fue a las manos",
          "Míster, lo escribo en caliente: tras el entrenamiento me agarré a gritos con tres compañeros y a "
          "usted le tengo guardadas un par de frases también. Este equipo juega como si no le importara nada "
          "y alguien tenía que decirlo. Si quiere sancionarme, adelante; las verdades no se multan.\n{j}"),
         ("{j} se encara con todos en el vestuario",
          "{dt}, hoy en el vestuario dije lo que nadie se anima a decir y la cosa terminó en tumulto. Usted "
          "arma las alineaciones como quien tira los dados y después le toca al jugador dar la cara. Yo ya "
          "la di. Ahora le toca a usted.\n{j}"),
         ("Bronca en el vestuario: {j} perdió los papeles",
          "Míster, seré breve: perdí los papeles. Me cruzaron un comentario sobre mi rendimiento y contesté "
          "con lo que tenía a mano. Pero no se equivoque: la culpa de que estemos así no es mía, es de su "
          "manera de manejar al grupo.\n{j}"),
         ("Se calentó el vestuario: {j}, en el centro de la riña",
          "Se lo cuento yo antes de que se lo cuenten: hubo riña y yo estaba en el medio. Me llamaron «el "
          "problema del grupo» y no lo voy a permitir. Si hay que repartir culpas, empiece por usted, {dt}, "
          "que es quien decide quién juega.\n{j}"),
         ("{j} desafía al técnico tras una riña en el vestuario",
          "{dt}, hoy casi termino a los golpes con un compañero y no fue por nada personal: fue por cómo se "
          "está llevando este equipo. Dicen que soy un conflictivo. Yo digo que soy el único que dice las "
          "cosas de frente.\n{j}"),
     ],
     'opciones': [
         {'texto': "MULTARLO", 'efectos': [('moral', 'j', -10), ('moral', 'plantel', 2), ('dinero', 'j', 0.02)],
          'titular': "{club} multa a {j} por la riña del vestuario",
          'noticia': "El club sancionó económicamente a {j} tras el altercado y el mensaje subido de tono que "
                     "envió al entrenador. El plantel respalda la medida."},
         {'texto': "APARTARLO 2 PARTIDOS", 'efectos': [('sancion', 'j', 2), ('moral', 'j', -15), ('moral', 'plantel', 4)],
          'titular': "{j}, apartado dos partidos tras insultar al técnico",
          'noticia': "Mano dura en {club}: {j} no estará en los dos próximos partidos de liga por la riña del "
                     "vestuario. El grupo cierra filas con el entrenador."},
         {'texto': "DEJARLO PASAR", 'efectos': [('moral', 'plantel', -6), ('confianza', None, -3)],
          'titular': "Riña en el vestuario de {club} y nadie pone orden",
          'noticia': "{j} se encaró con sus compañeros e insultó al técnico, que optó por mirar a otro lado. "
                     "En el plantel y en la directiva cayó mal."},
     ]},
    {'id': 'pelea_entreno', 'peso': 6, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _dos(e, r),
     'asunto': "Pelea en el entrenamiento: {j} y {j2}",
     'cuerpo': "En el entrenamiento de hoy {j} entró muy fuerte a {j2} y terminaron a los empujones. {j2} "
               "salió lastimado y pasó por la enfermería. El cuerpo técnico espera su decisión.",
     # v0.4.26.0: la redacción se sortea entre estas (asunto, cuerpo); la de arriba es la primera
     'variantes': [
         ("Pelea en el entrenamiento: {j} y {j2}",
          "En el entrenamiento de hoy {j} entró muy fuerte a {j2} y terminaron a los empujones. {j2} "
          "salió lastimado y pasó por la enfermería. El cuerpo técnico espera su decisión."),
         ("{j} y {j2} se fueron a las manos en la práctica",
          "Durante el ejercicio de hoy, una entrada de {j} sobre {j2} encendió los ánimos y terminaron "
          "agarrados. Los separaron entre varios compañeros. {j2} tiene un golpe y fue revisado por el "
          "cuerpo médico. Necesitamos su decisión."),
         ("Incidente en el entrenamiento: {j} golpeó a {j2}",
          "Nos informa el cuerpo técnico que en el partidillo de esta mañana {j} golpeó a {j2} tras una "
          "jugada discutida. {j2} se retiró dolorido del campo y pasó por la enfermería. Queda a su "
          "criterio cómo proceder."),
         ("Se calentó la práctica: {j} contra {j2}",
          "El entrenamiento se cortó cuando {j} y {j2} se enfrentaron a empujones por una falta. Hubo que "
          "separarlos y {j2} quedó resentido por el golpe. El cuerpo técnico aguarda sus instrucciones."),
         ("Roces en el entrenamiento entre {j} y {j2}",
          "Hoy el ensayo terminó antes de tiempo: {j} y {j2} discutieron, se empujaron y {j2} salió con "
          "molestias. En el vestuario hay tensión y los compañeros esperan que el club diga algo."),
         ("{j2} sale lastimado de una pelea con {j}",
          "Mala noticia desde la ciudad deportiva: {j2} terminó en la enfermería después de una pelea con "
          "{j} en pleno entrenamiento. Los dos quedaron enfrentados y el plantel está pendiente de lo que "
          "usted decida."),
         ("Gresca en la práctica: {j} y {j2} no se hablan",
          "En el último ejercicio, {j} y {j2} se enredaron en una disputa que acabó en golpes. {j2} salió "
          "con dolor y {j} no quiso dar explicaciones. El cuerpo técnico le pide que tome una decisión."),
     ],
     'opciones': [
         {'texto': "SANCIONAR AL AGRESOR", 'efectos': [('lesion', 'j2', (1, 2)), ('sancion', 'j', 1), ('moral', 'j', -6), ('moral', 'plantel', 2)],
          'titular': "{j}, sancionado por lesionar a un compañero",
          'noticia': "{club} apartó un partido a {j} tras la entrada que dejó tocado a {j2} en el entrenamiento."},
         {'texto': "MEDIAR ENTRE LOS DOS", 'efectos': [('lesion', 'j2', (1, 2)), ('moral', 'j', -4), ('moral', 'j2', -4)],
          'titular': "Tensión en {club}: {j} y {j2}, a los empujones",
          'noticia': "El técnico reunió a {j} y {j2} para limar asperezas. {j2} será baja por el golpe y ninguno "
                     "quedó conforme."},
     ]},
    {'id': 'salida_nocturna', 'peso': 7, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "{j} fue visto de fiesta antes del partido",
     'cuerpo': "Nos llegan fotos de {j} en una discoteca a altas horas de la madrugada. Hoy llegó al "
               "entrenamiento con ojeras y arrastrando los pies.",
     'opciones': [
         {'texto': "MULTARLO", 'efectos': [('energia', 'j', -20), ('moral', 'j', -6), ('dinero', 'j', 0.01)],
          'titular': "Multa a {j} por su noche de fiesta",
          'noticia': "{club} multó a {j} tras ser fotografiado de madrugada en una discoteca en plena semana de partido."},
         {'texto': "PERDONARLO", 'efectos': [('energia', 'j', -20), ('moral', 'plantel', -2)],
          'titular': "{j} sale de fiesta y no pasa nada",
          'noticia': "Las fotos de {j} de madrugada circularon por todos lados. El club no tomó medidas y en el "
                     "vestuario hubo caras largas."},
     ]},
    {'id': 'llega_tarde', 'peso': 6, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: j.personalidad in ('polemico', 'mercenario')),
     'asunto': "{j} llegó una hora tarde a entrenar",
     'cuerpo': "{j} se presentó una hora tarde al entrenamiento, sin avisar y con gafas oscuras. Dijo que "
               "había tráfico. Vive a cinco minutos.",
     'opciones': [
         {'texto': "AL BANQUILLO", 'efectos': [('sancion', 'j', 1), ('moral', 'j', -6), ('moral', 'plantel', 1)],
          'titular': "{j} se queda fuera por indisciplina",
          'noticia': "El técnico de {club} dejó a {j} fuera del próximo partido de liga por llegar tarde al entrenamiento."},
         {'texto': "UNA CHARLA Y YA", 'efectos': [('moral', 'j', -2)],
          'titular': "Llamado de atención a {j}",
          'noticia': "{j} llegó tarde a entrenar y todo quedó en una charla privada con el técnico."},
     ]},
    {'id': 'critica_prensa', 'peso': 6, 'remitente': 'prensa', 'defecto': 2,
     'elige': lambda e, r: _uno(e, r, lambda j: int(j.moral) < 50),
     'asunto': "{j} critica al técnico en una entrevista",
     'cuerpo': "En una entrevista publicada hoy, {j} declaró: «No entiendo los planteamientos del técnico, "
               "y no soy el único». Le pedimos su versión antes de publicar la segunda parte.",
     'opciones': [
         {'texto': "SANCIONARLO", 'efectos': [('sancion', 'j', 1), ('moral', 'j', -10), ('confianza', None, 2)],
          'titular': "{club} castiga a {j} por sus declaraciones",
          'noticia': "Las críticas públicas de {j} al entrenador le costaron un partido de sanción interna. La "
                     "directiva respaldó al técnico."},
         {'texto': "HABLAR CON ÉL", 'efectos': [('moral', 'j', 6)],
          'titular': "{j} y el técnico hacen las paces",
          'noticia': "Tras sus polémicas declaraciones, {j} se reunió con el entrenador. «Está todo aclarado», dijo al salir."},
         {'texto': "IGNORARLO", 'efectos': [('confianza', None, -4), ('moral', 'plantel', -2)],
          'titular': "Silencio del técnico ante las críticas de {j}",
          'noticia': "El entrenador de {club} no respondió a las críticas de {j}. En la directiva no gustó la falta de autoridad."},
     ]},
    {'id': 'charla_lider', 'peso': 5, 'peso_mal': 12, 'solo_mal': True, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: j.personalidad == 'lider'),
     'asunto': "{j}: quiero reunir al vestuario",
     'cuerpo': "Míster, esto no puede seguir así. Quiero juntar a los muchachos, solos, sin cuerpo técnico, "
               "y decirnos las cosas a la cara. Necesito su permiso.\n{j}",
     'opciones': [
         {'texto': "APOYAR LA CHARLA", 'efectos': [('moral', 'plantel', 6)],
          'titular': "{j} reúne al plantel de {club}",
          'noticia': "El capitán sin brazalete, {j}, juntó al vestuario a puerta cerrada con el aval del técnico. "
                     "«Salimos más unidos», contó un jugador."},
         {'texto': "CORTARLA", 'efectos': [('moral', 'j', -8), ('moral', 'plantel', -2)],
          'titular': "El técnico frena la reunión que pedía {j}",
          'noticia': "{j} quiso reunir al plantel de {club} para hablar de la mala racha y el entrenador se lo impidió."},
     ]},
    {'id': 'exige_titular', 'peso': 7, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: int(getattr(j, 'jornadas_sin_jugar', 0) or 0) >= 3 and j.overall >= _media(e)),
     'asunto': "{j}: quiero jugar",
     'cuerpo': "Míster, llevo semanas mirando los partidos desde el banco y no vine a {club} a eso. Estoy "
               "mejor que varios de los que juegan. Póngame o dígame de frente que no cuenta conmigo.\n{j}",
     'opciones': [
         {'texto': "PROMETERLE MINUTOS", 'efectos': [('moral', 'j', 8), ('promesa', 'j', {'tipo': 'minutos', 'jornadas': 3, 'falla': -12})],
          'titular': "{j} tendrá su oportunidad",
          'noticia': "El técnico de {club} le prometió minutos a {j}, que venía reclamando un lugar en el equipo."},
         {'texto': "NEGARSE", 'efectos': [('moral', 'j', -8)],
          'titular': "{j} seguirá en el banco",
          'noticia': "{j} pidió ser titular y el entrenador de {club} le respondió que el puesto se gana entrenando."},
     ]},
    {'id': 'lesion_entreno', 'peso': 6, 'remitente': 'medico', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "{j} se resintió entrenando",
     'cuerpo': "{j} sintió un pinchazo muscular en el entrenamiento. Podemos darle reposo completo o "
               "infiltrarlo para que vuelva antes, con riesgo de recaída.",
     'opciones': [
         {'texto': "REPOSO COMPLETO", 'efectos': [('lesion', 'j', (2, 3))],
          'titular': "{j}, baja por una lesión muscular",
          'noticia': "{club} no quiso arriesgar: {j} hará reposo completo tras resentirse en un entrenamiento."},
         {'texto': "INFILTRARLO", 'efectos': [('lesion', 'j', 1), ('azar', 0.3, [('lesion', 'j', 3), ('texto', "Recaída: la lesión se agravó.")], [])],
          'titular': "{j} fuerza para volver cuanto antes",
          'noticia': "{j} fue infiltrado para acortar los plazos de su lesión muscular. En el cuerpo médico de {club} cruzan los dedos."},
     ]},
    {'id': 'gripe', 'peso': 5, 'remitente': 'medico', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "Brote de gripe en el vestuario",
     'cuerpo': "{j} llegó con fiebre y ya hay otros dos con síntomas. Podemos aislarlos unos días o dejar "
               "que entrenen con el grupo.",
     'opciones': [
         {'texto': "AISLARLOS", 'efectos': [('lesion', 'j', 1), ('lesion', 'otros:2', 1)],
          'titular': "Gripe en {club}: tres jugadores aislados",
          'noticia': "Un brote de gripe dejó fuera de combate a {j} y a otros dos compañeros, que no estarán en el próximo partido."},
         {'texto': "QUE ENTRENEN IGUAL", 'efectos': [('energia', 'j', -15), ('energia', 'otros:5', -15)],
          'titular': "La gripe se extiende por el vestuario de {club}",
          'noticia': "{j} entrenó con fiebre y el virus corrió por el vestuario: medio plantel llega tocado al fin de semana."},
     ]},
    {'id': 'nace_hijo', 'peso': 4, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: 22 <= int(j.edad) <= 34),
     'asunto': "{j}: voy a ser papá",
     'cuerpo': "Míster, mi hijo nace esta semana. Sé que hay partido, pero quiero estar ahí. Le pido permiso "
               "para ausentarme; vuelvo enseguida y con más ganas que nunca.\n{j}",
     'opciones': [
         {'texto': "DARLE PERMISO", 'efectos': [('lesion', 'j', 1), ('moral', 'j', 15)],
          'titular': "{j} fue papá y se pierde un partido",
          'noticia': "{club} le dio permiso a {j} para estar en el nacimiento de su hijo. «Nunca voy a olvidar el gesto del técnico», dijo."},
         {'texto': "NEGARLO", 'efectos': [('moral', 'j', -10)],
          'titular': "{j} no tuvo permiso para el nacimiento de su hijo",
          'noticia': "El técnico de {club} no liberó a {j}, que se enteró del nacimiento de su hijo en la concentración."},
     ]},
    {'id': 'seleccion', 'peso': 5, 'remitente': 'club', 'defecto': 1,
     'elige': _seleccionable,
     'asunto': "{pais} convoca a {j}",
     'cuerpo': "La federación de {pais} nos pide a {j} para un amistoso entre semana. No es fecha oficial: "
               "podemos negarnos. Si viaja, volverá cansado.",
     'opciones': [
         {'texto': "DEJARLO IR", 'efectos': [('energia', 'j', -25), ('moral', 'j', 8)],
          'titular': "{j} viaja con {pais}",
          'noticia': "{club} cedió a {j} a su selección para un amistoso. El jugador volvió feliz y con muchas horas de vuelo encima."},
         {'texto': "RETENERLO", 'efectos': [('moral', 'j', -8)],
          'titular': "{club} no cede a {j} a {pais}",
          'noticia': "El club se negó a liberar a {j} para el amistoso de {pais}. El jugador no ocultó su malestar."},
     ]},
    {'id': 'nostalgia', 'peso': 5, 'remitente': 'jugador', 'defecto': 1,
     'elige': _extranjero,
     'asunto': "{j}: extraño mi casa",
     'cuerpo': "Míster, llevo meses sin ver a mi familia y se me está haciendo cuesta arriba. Necesito unos "
               "días en {pais} para recargar. Le prometo que vuelvo otro.\n{j}",
     'opciones': [
         {'texto': "DARLE DÍAS LIBRES", 'efectos': [('lesion', 'j', 1), ('moral', 'j', 10)],
          'titular': "{j} viaja a {pais} con permiso del club",
          'noticia': "{club} le dio unos días libres a {j}, que extrañaba a su familia. Se perderá un partido."},
         {'texto': "NEGARSE", 'efectos': [('moral', 'j', -6), ('forma', 'j', 5.0)],
          'titular': "{j}, con la cabeza en {pais}",
          'noticia': "{j} pidió permiso para viajar a su país y no lo consiguió. En los entrenamientos se lo nota apagado."},
     ]},
    {'id': 'entreno_extra', 'peso': 5, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: j.personalidad == 'profesional'),
     'asunto': "{j}: quiero quedarme a entrenar más",
     'cuerpo': "Míster, quiero hacer doble turno esta semana por mi cuenta: definición y físico. Sé que "
               "llegaré más cargado al partido, pero siento que lo necesito.\n{j}",
     'opciones': [
         {'texto': "PERMITIRLO", 'efectos': [('forma', 'j', 7.5), ('energia', 'j', -12), ('progreso', 'j', 0.15)],
          'titular': "{j}, el último en irse del entrenamiento",
          'noticia': "{j} hace doble turno por voluntad propia. «Es un ejemplo para los más jóvenes», dicen en {club}."},
         {'texto': "FRENARLO", 'efectos': [('texto', "Nada cambia: descansa como el resto.")],
          'titular': "El técnico cuida las cargas de {j}",
          'noticia': "{j} quería entrenar doble turno, pero el cuerpo técnico de {club} prefirió no sobrecargarlo."},
     ]},
    {'id': 'escandalo_redes', 'peso': 6, 'remitente': 'prensa', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "Escándalo: el video de {j} en redes",
     'cuerpo': "Un video de {j} burlándose de los hinchas rivales se hizo viral y hay pedidos de sanción. "
               "¿Cuál es la postura del club?",
     'opciones': [
         {'texto': "MULTARLO", 'efectos': [('moral', 'j', -6), ('confianza', None, 2), ('dinero', 'j', 0.01)],
          'titular': "{club} multa a {j} por su video viral",
          'noticia': "El club tomó distancia del video de {j} y lo sancionó económicamente. «No representa nuestros valores», dice el comunicado."},
         {'texto': "DEFENDERLO", 'efectos': [('moral', 'j', 6), ('confianza', None, -3)],
          'titular': "El técnico sale a defender a {j}",
          'noticia': "«Es un chico, se equivocó y ya está», dijo el entrenador de {club} sobre el video de {j}. A la directiva no le hizo gracia."},
     ]},
    {'id': 'rumor_oferta', 'peso': 5, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: j.personalidad == 'mercenario'),
     'asunto': "{j}: me están llamando de afuera",
     'cuerpo': "Míster, mi agente dice que hay un club dispuesto a pagarme el doble. Yo aquí estoy bien, pero "
               "uno tiene familia. Si me mejoran el contrato, me olvido del tema.\n{j}",
     'opciones': [
         {'texto': "PROMETER UN AUMENTO", 'efectos': [('moral', 'j', 6), ('promesa', 'j', {'tipo': 'aumento', 'jornadas': 6, 'falla': -10})],
          'titular': "{club} le mejorará el contrato a {j}",
          'noticia': "Ante el interés de otros clubes, el técnico le prometió a {j} una mejora salarial en las próximas semanas."},
         {'texto': "IGNORARLO", 'efectos': [('moral', 'j', -6), ('forma', 'j', 5.0)],
          'titular': "{j}, distraído por los rumores",
          'noticia': "{j} dejó saber que tiene ofertas y en {club} no se dieron por enterados. Su rendimiento lo está notando."},
     ]},
    {'id': 'prima_capitan', 'peso': 5, 'remitente': 'jugador', 'defecto': 1,
     'elige': _figura,
     'asunto': "{j}: el plantel pide una prima",
     'cuerpo': "Míster, hablo en nombre de todos: los muchachos piden una prima por ganar el próximo partido. "
               "No es mucho y el grupo lo tomaría como un gesto.\n{j}",
     'opciones': [
         {'texto': "PAGAR LA PRIMA", 'efectos': [('dinero', 'plantel', -0.01), ('moral', 'plantel', 5)],
          'titular': "{club} premia a su plantel",
          'noticia': "La directiva aprobó la prima que pidió el plantel por boca de {j}. El vestuario, encantado."},
         {'texto': "NEGARSE", 'efectos': [('moral', 'plantel', -3)],
          'titular': "No habrá prima en {club}",
          'noticia': "El plantel pidió una prima a través de {j} y la respuesta fue no. «Para eso están los sueldos», dijeron desde el club."},
     ]},
    {'id': 'asado', 'peso': 6, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "{j}: ¿hacemos un asado de equipo?",
     'cuerpo': "Míster, con los muchachos queremos hacer un asado esta semana, todos juntos con las familias. "
               "¿El club invita? Prometemos no pasarnos… mucho.\n{j}",
     'opciones': [
         {'texto': "EL CLUB INVITA", 'efectos': [('dinero', 'plantel', -0.002), ('moral', 'plantel', 4), ('energia', 'plantel', -5)],
          'titular': "Asado de camaradería en {club}",
          'noticia': "El plantel compartió un asado organizado por {j} y pagado por el club. Hubo risas, guitarra y más de uno llegó pesado al entrenamiento."},
         {'texto': "PROHIBIRLO", 'efectos': [('moral', 'plantel', -2)],
          'titular': "El técnico de {club} cancela el asado del plantel",
          'noticia': "{j} había organizado un asado de equipo y el entrenador lo prohibió: «Primero hay que ganar»."},
     ]},
    {'id': 'hinchas', 'peso': 4, 'peso_mal': 10, 'solo_mal': True, 'remitente': 'club', 'defecto': 1,
     'elige': _figura,
     'asunto': "Hinchas esperan al plantel a la salida",
     'cuerpo': "Un grupo de hinchas se plantó en la puerta del entrenamiento para reclamar por los resultados. "
               "Increparon a varios jugadores, sobre todo a {j}. Piden que alguien dé la cara.",
     'opciones': [
         {'texto': "DAR LA CARA", 'efectos': [('confianza', None, 4), ('moral', 'plantel', 2)],
          'titular': "El técnico de {club} habla con los hinchas",
          'noticia': "El entrenador salió a hablar con los hinchas que reclamaban en la puerta y se llevó hasta algún aplauso. {j} lo acompañó."},
         {'texto': "SALIR POR ATRÁS", 'efectos': [('confianza', None, -4), ('moral', 'plantel', -2)],
          'titular': "El plantel de {club} esquiva a su hinchada",
          'noticia': "Los hinchas esperaron en vano: técnico y jugadores, con {j} a la cabeza, salieron por la puerta trasera."},
     ]},
    {'id': 'juvenil_deslumbra', 'peso': 5, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: int(j.edad) <= 21),
     'asunto': "{j} la está rompiendo en los entrenamientos",
     'cuerpo': "Queremos avisarle que {j} lleva dos semanas siendo el mejor de las prácticas. Con trabajo "
               "específico y confianza puede dar un salto.",
     'opciones': [
         {'texto': "DARLE BOLA", 'efectos': [('progreso', 'j', 0.4), ('moral', 'j', 6)],
          'titular': "{j}, la joya que ilusiona a {club}",
          'noticia': "El cuerpo técnico le armó un plan especial a {j}, que viene deslumbrando en los entrenamientos."},
         {'texto': "PEDIR CALMA", 'efectos': [('texto', "Nada cambia: sigue su curso normal.")],
          'titular': "Paciencia con {j}",
          'noticia': "«Hay que llevarlo de a poco», dijo el técnico de {club} sobre {j}, la sensación de las prácticas."},
     ]},
    {'id': 'mentor', 'peso': 5, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _dos(e, r, lambda j: int(j.edad) >= 31, lambda j: int(j.edad) <= 21),
     'asunto': "{j} se ofrece a apadrinar a {j2}",
     'cuerpo': "{j} se quedó después del entrenamiento trabajando con {j2} y propone hacerlo todas las "
               "semanas. Solo necesitan que les organicemos el espacio.",
     'opciones': [
         {'texto': "FOMENTARLO", 'efectos': [('progreso', 'j2', 0.4), ('moral', 'j', 4), ('moral', 'j2', 4)],
          'titular': "{j}, maestro de {j2}",
          'noticia': "El veterano {j} tomó bajo su ala a {j2}: se quedan a trabajar juntos después de cada entrenamiento de {club}."},
         {'texto': "NO METERSE", 'efectos': [('texto', "Nada cambia: cada uno a lo suyo.")],
          'titular': "{j} y {j2}, cada uno por su lado",
          'noticia': "{j} quiso apadrinar a {j2}, pero el cuerpo técnico de {club} prefirió no cambiar las rutinas."},
     ]},
    {'id': 'insulta_arbitro', 'peso': 5, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "La liga sanciona a {j} por insultar al árbitro",
     'cuerpo': "{j} publicó en redes que el árbitro del último partido «tenía la camiseta rival debajo». La "
               "liga le abrió expediente: un partido. Podemos apelar, pero si sale mal serán dos.",
     'opciones': [
         {'texto': "APELAR", 'efectos': [('azar', 0.5, [('texto', "Apelación ganada: sin sanción.")], [('sancion', 'j', 2)])],
          'titular': "{club} apela la sanción a {j}",
          'noticia': "El club recurrió el castigo a {j} por sus dichos contra el árbitro. El comité ya resolvió y en {club} lo acatan."},
         {'texto': "ACEPTAR LA SANCIÓN", 'efectos': [('sancion', 'j', 1)],
          'titular': "Un partido de suspensión para {j}",
          'noticia': "{j} cumplirá un partido de sanción por sus publicaciones contra el árbitro. {club} no apelará."},
     ]},
]
POR_ID = {ev['id']: ev for ev in EVENTOS}


# ---------------------------------------------------------------- sorteo y resolución
def pendiente(estado: dict) -> Optional[dict]:
    return next((m for m in C.bandeja(estado) if (m.get('evento') or {}).get('resuelto', 0) is None), None)


def _candidatos(estado: dict, rng: random.Random, forzar: Optional[str] = None) -> list:
    mal = va_mal(estado)
    ahora = _abs(estado)
    vistos = _dc(estado).setdefault('eventos_vistos', {})
    res = []
    for ev in EVENTOS:
        if forzar:
            if ev['id'] != forzar:
                continue
        elif (ev.get('solo_mal') and not mal) or ahora - int(vistos.get(ev['id'], -999)) < ENFRIAMIENTO:
            continue
        try:
            prot = ev['elige'](estado, rng)
        except Exception as e:
            logger.error(f"Evento {ev['id']}: no se pudo elegir protagonista: {e}")
            prot = None
        if prot:
            res.append((ev, prot, ev.get('peso_mal', ev['peso']) if mal else ev['peso']))
    return res


def _fmt(texto: str, estado: dict, prot: list) -> str:
    mi = estado.get('mi_equipo')
    return texto.format(
        j=_nom(prot[0]), j2=_nom(prot[1]) if len(prot) > 1 else '',
        club=getattr(mi, 'nombre', 'el club'), pais=getattr(prot[0], 'nacionalidad', '') or 'su país',
        dt=(str(estado.get('dt_nombre', '') or '').split() or ['míster'])[-1])


def sortear(estado: dict, rng: Optional[random.Random] = None, forzar: Optional[str] = None) -> Optional[dict]:
    """Sortea el evento de la jornada y envía su correo. `forzar`: id de evento (tests / depuración)."""
    azar = rng or random.Random()
    if pendiente(estado) is not None:
        return None
    if not forzar and azar.random() >= (PROB_MAL if va_mal(estado) else PROB_BASE):
        return None
    cands = _candidatos(estado, azar, forzar)
    if not cands:
        return None
    ev, prot, _peso = azar.choices(cands, weights=[c[2] for c in cands])[0]
    asunto, cuerpo = azar.choice(ev['variantes']) if ev.get('variantes') else (ev['asunto'], ev['cuerpo'])   # v0.4.26.0
    msg = C.enviar(estado, ev['remitente'], _fmt(asunto, estado, prot), _fmt(cuerpo, estado, prot))
    msg['evento'] = {'id': ev['id'], 'protagonistas': [j.id for j in prot],
                     'nombres': [_nom(j) for j in prot],      # v0.4.10.0: para la noticia si ya no están
                     'opciones': [o['texto'] for o in ev['opciones']], 'resuelto': None, 'resumen': []}
    _dc(estado).setdefault('eventos_vistos', {})[ev['id']] = _abs(estado)
    return msg


def _cerrar_sin_efectos(estado: dict, msg: dict, ids: list, por_id: dict) -> list:
    """v0.4.10.0: el protagonista ya no está en el club (o el evento ya no existe): se cierra sin
    efectos pero deja igual su noticia (opcion = -1, igual que `resuelto`)."""
    evd = msg['evento']
    nombres = list(evd.get('nombres') or [])
    faltan = [nombres[k] if k < len(nombres) and nombres[k] else "Un jugador"
              for k, i in enumerate(ids) if i not in por_id]
    club = msg.get('club') or getattr(estado.get('mi_equipo'), 'nombre', '') or 'el club'
    caso = msg.get('asunto', '')
    if faltan:
        quien = " y ".join(faltan)
        verbo = "ya no forma" if len(faltan) == 1 else "ya no forman"
        resumen = f"El asunto se cerró solo: {quien} ya no {'está' if len(faltan) == 1 else 'están'} en el club."
        titular = f"Sin {quien} en {club}, el asunto del vestuario se cierra solo"
        cuerpo = (f"El caso «{caso}» no llegó a resolverse: {quien} {verbo} parte de la plantilla de {club}, "
                  "así que el técnico se quedó sin decisión que tomar.")
    else:
        resumen = "El asunto se cerró solo: ya no tiene sentido."
        titular = f"Asunto archivado en {club}"
        cuerpo = f"El caso «{caso}» quedó sin resolver y se archivó sin consecuencias."
    evd['resuelto'], evd['resumen'] = -1, [resumen]
    registrar_noticia(estado, titular, cuerpo, jugadores=list(ids), evento=str(evd.get('id', '')), opcion=-1)
    return evd['resumen']


def resolver(estado: dict, msg_id: int, indice: int, rng: Optional[random.Random] = None) -> list:
    """Aplica la opción elegida, registra la noticia y devuelve el resumen ([] si ya estaba resuelto)."""
    msg = next((m for m in C.bandeja(estado) if m.get('id') == msg_id), None)
    evd = (msg or {}).get('evento')
    if not evd or evd.get('resuelto') is not None:
        return []
    ev = POR_ID.get(evd.get('id'))
    ids = list(evd.get('protagonistas', []))
    por_id = {j.id: j for j in _plantel(estado)}
    prot = [por_id[i] for i in ids if i in por_id]
    if ev is None or len(prot) < len(ids):
        return _cerrar_sin_efectos(estado, msg, ids, por_id)
    indice = max(0, min(int(indice), len(ev['opciones']) - 1))
    op = ev['opciones'][indice]
    lineas = aplicar(estado, op['efectos'], prot, rng)
    evd['resuelto'], evd['resumen'] = indice, lineas
    registrar_noticia(estado, _fmt(op['titular'], estado, prot), _fmt(op['noticia'], estado, prot),
                      jugadores=list(evd['protagonistas']), evento=ev['id'], opcion=indice)
    return lineas


def resolver_pendientes(estado: dict, rng: Optional[random.Random] = None) -> int:
    """Los eventos sin responder se resuelven con su opción por defecto ("dejarlo pasar")."""
    n = 0
    for m in list(C.bandeja(estado)):
        evd = m.get('evento') or {}
        if evd and evd.get('resuelto') is None:
            resolver(estado, m['id'], (POR_ID.get(evd.get('id')) or {}).get('defecto', 0), rng)
            n += 1
    return n


def cierre_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Cierre de jornada de liga del user: pendientes por defecto, promesas y sorteo del evento."""
    try:
        resolver_pendientes(estado, rng)
        revisar_promesas(estado)
        from alpha_football import dias as _dias      # v0.4.12.0: el evento llega en un día del hueco
        with _dias.diferir_correos(estado):
            sortear(estado, rng)
    except Exception as e:
        logger.error(f"Error en los eventos de la jornada: {e}", exc_info=True)
