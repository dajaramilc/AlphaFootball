# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Cantera (v4.8.0)
Juveniles del club aparte de la plantilla. La cantera del user vive en datos_carrera['cantera']
(lista de dicts, va con el guardado) y se renueva dos veces por temporada: inicio y mitad.
Los clubes de la IA no guardan lista: en cada renovación sortean un alta directa a su plantilla.
"""
from __future__ import annotations

import logging
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)

TAMANO_INICIAL, TAMANO_MIN, TAMANO_MAX = 8, 6, 12
EDAD_SALIDA = 20                 # a esta edad sin subir, se va
PROB_JOYA_USER = 0.08            # por renovación (máximo una)
PROB_CANTERANO_IA = 0.15         # por club de la IA y renovación
PROB_JOYA_IA = 0.01              # muy raro
PESOS_POSICION = (('POR', 1), ('DEF', 3), ('MED', 3), ('DEL', 2))


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _tipo_liga(estado: dict, equipo: Any) -> str:
    """Tipo ('premier', 'laliga'...) de la liga donde juega el club; '' si no se encuentra."""
    from alpha_football.mercado_ia import ligas_de_la_partida
    for liga, tipo, _div in ligas_de_la_partida(estado):
        if any(e is equipo for e in liga.equipos):
            return tipo
    return ''


def _siguiente_id(estado: dict) -> int:
    """Mismo contador que los regens (datos_carrera['regen_id']): ids únicos en la carrera."""
    dc = _dc(estado)
    nuevo = int(dc.get('regen_id', 700000) or 700000)
    dc['regen_id'] = nuevo + 1
    return nuevo


def _hito(estado: dict) -> str:
    """'<temporada>-inicio' hasta la mitad de la liga y '<temporada>-mitad' desde ahí."""
    liga = estado.get('liga')
    n = int(getattr(liga, 'num_jornadas', 22) or 22)
    j = int(getattr(liga, 'jornada_actual', 1) or 1)
    return f"{int(estado.get('temporada', 1) or 1)}-{'mitad' if j >= max(2, n // 2) else 'inicio'}"


def generar_canterano(estado: dict, equipo: Any, rng: random.Random, joya: bool = False,
                      posicion: Optional[str] = None) -> Any:
    """Juvenil del club. Normal: lejos del once. Joya: casi al nivel del once."""
    from alpha_football.models import Jugador
    from alpha_football.market import nivel_club
    from alpha_football.nombres import nombre_unico
    from alpha_football.retiros import PAIS_POR_LIGA, _atributos_para
    nivel = int(nivel_club(equipo))
    if joya:
        ovr = max(40, nivel - rng.randint(0, 4))
        potencial, edad = ovr + rng.randint(5, 12), rng.randint(16, 18)
    else:
        ovr = max(40, nivel - rng.randint(18, 28))
        potencial, edad = ovr + rng.randint(8, 20), rng.randint(15, 18)
    if posicion is None:
        posicion = rng.choices([p for p, _ in PESOS_POSICION], weights=[w for _, w in PESOS_POSICION])[0]
    pais = PAIS_POR_LIGA.get(_tipo_liga(estado, equipo), '')
    nombre, apellido = nombre_unico(pais, rng)
    ataque, defensa, fisico, tecnica, mental = _atributos_para(posicion, ovr, rng)
    return Jugador(nombre=nombre, apellido=apellido, posicion=posicion,
                   ataque=ataque, defensa=defensa, fisico=fisico, tecnica=tecnica, mental=mental,
                   id=_siguiente_id(estado), edad=edad, potencial=min(99, potencial),
                   nacionalidad=pais, joya=joya)


def _guardar(estado: dict, jugadores: list) -> None:
    _dc(estado)['cantera'] = [j.to_dict() for j in jugadores]


def cantera(estado: dict) -> list:
    """Canteranos del club del user (objetos nuevos en cada llamada: identificar por id).
    Si no hay cantera, está corrupta o es de otro club, se genera para el club actual."""
    from alpha_football.models import Jugador
    mi = estado.get('mi_equipo')
    if mi is None:
        return []
    dc = _dc(estado)
    crudos = dc.get('cantera')
    valida = (isinstance(crudos, list) and dc.get('cantera_club') == mi.nombre
              and all(isinstance(c, dict) and c.get('nombre') and 'ataque' in c for c in crudos))
    if not valida:
        rng = random.Random()
        jugadores = [generar_canterano(estado, mi, rng) for _ in range(TAMANO_INICIAL)]
        dc['cantera_club'] = mi.nombre
        dc['cantera_ultima'] = _hito(estado)     # recién creada: no se renueva en esta misma mitad
        _guardar(estado, jugadores)
        return jugadores
    return [Jugador.from_dict(c) for c in crudos]


def _prob_salida(j: Any) -> float:
    """Los de más potencial se quedan más."""
    pot = int(getattr(j, 'potencial', 0) or 0)
    return 0.10 if pot >= 80 else (0.25 if pot >= 70 else 0.40)


def _crecer(j: Any, rng: random.Random) -> int:
    """Sube de +1 a +4 de media sin pasar su potencial. Retorna cuánto subió."""
    sube = min(rng.randint(1, 4), max(0, int(j.potencial) - int(j.overall)))
    for attr in ('ataque', 'defensa', 'fisico', 'tecnica', 'mental'):
        setattr(j, attr, min(99, getattr(j, attr) + sube))
    return sube


def renovar(estado: dict, rng: Optional[random.Random] = None) -> dict:
    """Renovación semestral de la cantera del user: crecen, cumplen años (solo al inicio de
    temporada), algunos se van y llegan nuevos. Retorna el resumen para el correo."""
    azar = rng or random.Random()
    mi = estado.get('mi_equipo')
    inicio = _hito(estado).endswith('inicio')
    mejoran, se_van, quedan = [], [], []
    for j in cantera(estado):
        sube = _crecer(j, azar)
        if inicio:
            j.edad += 1
        if j.edad >= EDAD_SALIDA:
            se_van.append((j, 'edad'))
        elif not j.joya and azar.random() < _prob_salida(j):
            se_van.append((j, 'no_renovo'))
        else:
            quedan.append(j)
            if sube:
                mejoran.append((j, sube))
    hay_joya = azar.random() < PROB_JOYA_USER
    llegan = [generar_canterano(estado, mi, azar, joya=(hay_joya and i == 0)) for i in range(azar.randint(2, 4))]
    ids_nuevos = {j.id for j in llegan}
    quedan += llegan
    while len(quedan) > TAMANO_MAX:                      # sobran: se van los de menor potencial (ni nuevos ni joyas)
        viejos = [j for j in quedan if j.id not in ids_nuevos and not j.joya]
        if not viejos:
            break
        sobra = min(viejos, key=lambda j: j.potencial)
        quedan.remove(sobra)
        se_van.append((sobra, 'no_renovo'))
        mejoran = [(j, s) for j, s in mejoran if j.id != sobra.id]
    while len(quedan) < TAMANO_MIN:
        nuevo = generar_canterano(estado, mi, azar)
        quedan.append(nuevo)
        llegan.append(nuevo)
    _guardar(estado, quedan)
    return {'llegan': llegan, 'se_van': se_van, 'mejoran': mejoran, 'joya': llegan[0] if hay_joya else None}


_MOTIVO = {'edad': "cumplió la edad límite", 'no_renovo': "no siguió en el club"}


def _linea(j: Any) -> str:
    return f"{j.nombre_completo} ({j.posicion}, {j.edad} años, media {j.overall})"


def _correo_informe(estado: dict, res: dict) -> None:
    from alpha_football import correo as C
    joya = res.get('joya')
    partes = []
    if joya is not None:
        partes.append(f"Tenemos una joya: {_linea(joya)}. Está casi al nivel del primer equipo; le "
                      "recomendamos verlo cuanto antes.")
    altas = [j for j in res['llegan'] if j is not joya]
    if altas:
        partes.append("Altas: " + "; ".join(_linea(j) for j in altas) + ".")
    if res['se_van']:
        partes.append("Bajas: " + "; ".join(f"{j.nombre_completo} ({_MOTIVO[m]})" for j, m in res['se_van']) + ".")
    mejores = sorted(res['mejoran'], key=lambda t: -t[1])[:3]
    if mejores:
        partes.append("Los que más progresaron: "
                      + "; ".join(f"{j.nombre_completo} (+{s}, media {j.overall})" for j, s in mejores) + ".")
    asunto = (f"Una joya en la cantera: {joya.nombre_completo}" if joya is not None
              else f"Informe de cantera: {len(res['llegan'])} altas, {len(res['se_van'])} bajas")
    C.enviar(estado, 'cantera', asunto, "\n".join(partes), C.accion('cantera_screen', "VER CANTERA"))


def revisar_jornada(estado: dict, rng: Optional[random.Random] = None) -> Optional[dict]:
    """Tras cada jornada: renueva la cantera al entrar en un hito nuevo (inicio o mitad de
    temporada) y avisa por correo. None si no tocaba."""
    try:
        if estado.get('mi_equipo') is None:
            return None
        cantera(estado)                    # partidas viejas: la crea y marca el hito actual
        dc, clave = _dc(estado), _hito(estado)
        if dc.get('cantera_ultima') == clave:
            return None
        dc['cantera_ultima'] = clave
        azar = rng or random.Random()
        res = renovar(estado, azar)
        _correo_informe(estado, res)
        res['ia'] = renovar_ia(estado, azar)
        return res
    except Exception as e:
        logger.error(f"Error en la renovación de la cantera: {e}", exc_info=True)
        return None


def proximo_informe(estado: dict) -> str:
    """Cuándo llega el próximo informe (texto para la pantalla)."""
    liga = estado.get('liga')
    mitad = max(2, int(getattr(liga, 'num_jornadas', 22) or 22) // 2)
    j = int(getattr(liga, 'jornada_actual', 1) or 1)
    return f"jornada {mitad}" if j < mitad else "inicio de la próxima temporada"


def subir(estado: dict, jugador_id: int) -> tuple:
    """Sube al canterano al primer equipo con contrato nuevo. (ok, mensaje para la pantalla)."""
    try:
        from alpha_football import market
        from alpha_football.finanzas import contrato_inicial
        mi = estado.get('mi_equipo')
        lista = cantera(estado)
        j = next((x for x in lista if x.id == jugador_id), None)
        if mi is None or j is None:
            return False, "Ese canterano ya no está en la cantera."
        if len(mi.jugadores) >= market.PLANTILLA_MAXIMA:
            return False, f"Plantilla llena ({market.PLANTILLA_MAXIMA}). Libera un cupo antes de subirlo."
        j.joya = False                       # en el primer equipo es un jugador normal
        j.canterano = getattr(mi, 'nombre', '') or ''     # v0.4.11.0: progresa más rápido en su club
        tipo = _tipo_liga(estado, mi)
        if tipo:
            market.registrar_region_jugador(j, tipo)
        j.valor = market.calcular_valor(j)
        j.salario, j.contrato_anios, j.clausula = contrato_inicial(j)
        j.contrato_anios = max(2, j.contrato_anios)
        mi.jugadores.append(j)               # al final: los índices de la alineación no cambian
        _guardar(estado, [x for x in lista if x.id != jugador_id])
        return True, f"{j.nombre_completo} sube al primer equipo."
    except Exception as e:
        logger.error(f"No se pudo subir al canterano {jugador_id}: {e}", exc_info=True)
        return False, "No se pudo subir al canterano."


def liberar(estado: dict, jugador_id: int) -> bool:
    """Saca al canterano de la cantera. True si estaba."""
    try:
        lista = cantera(estado)
        quedan = [x for x in lista if x.id != jugador_id]
        if len(quedan) == len(lista):
            return False
        _guardar(estado, quedan)
        return True
    except Exception as e:
        logger.error(f"No se pudo liberar al canterano {jugador_id}: {e}", exc_info=True)
        return False


def renovar_ia(estado: dict, rng: Optional[random.Random] = None) -> list:
    """Clubes de la IA (menor medida): cada uno puede subir un canterano directo a su plantilla;
    muy rara vez, una joya. Con la plantilla llena reemplaza al de peor media, en su misma posición."""
    from alpha_football import correo as C
    from alpha_football.mercado_ia import ligas_de_la_partida, PLANTILLA_MAX_IA
    from alpha_football.market import calcular_valor, registrar_region_jugador
    from alpha_football.finanzas import contrato_inicial, quitar_de_plantilla
    azar = rng or random.Random()
    mi = estado.get('mi_equipo')
    altas = []
    for liga, tipo, _div in ligas_de_la_partida(estado):
        en_mi_liga = mi is not None and any(e is mi for e in liga.equipos)
        for eq in liga.equipos:
            if eq is mi:
                continue
            try:
                r = azar.random()
                if r >= PROB_JOYA_IA + PROB_CANTERANO_IA:
                    continue
                joya = r < PROB_JOYA_IA
                peor = None
                if len(eq.jugadores) >= PLANTILLA_MAX_IA:
                    propios = [j for j in eq.jugadores if not getattr(j, 'prestamo', None)]
                    if not propios:
                        continue
                    peor = min(propios, key=lambda j: j.overall)
                nuevo = generar_canterano(estado, eq, azar, joya=joya,
                                          posicion=peor.posicion if peor is not None else None)
                nuevo.joya = False               # la marca solo sirve en la cantera del user
                if peor is not None:
                    if nuevo.overall <= peor.overall:
                        continue
                    quitar_de_plantilla(eq, peor)
                    peor.fin_de_contrato = True          # queda libre: sigue en el mercado
                    estado.setdefault('free_agents_list', []).append(peor)
                registrar_region_jugador(nuevo, tipo)
                nuevo.valor = calcular_valor(nuevo)
                nuevo.salario, nuevo.contrato_anios, nuevo.clausula = contrato_inicial(nuevo)
                nuevo.contrato_anios = max(2, nuevo.contrato_anios)
                eq.jugadores.append(nuevo)
                eq.alineacion_activa = None      # la IA rearma su once
                altas.append({'club': eq.nombre, 'jugador': nuevo.nombre_completo, 'media': nuevo.overall,
                              'joya': joya})
                if joya and en_mi_liga:
                    C.enviar(estado, 'prensa', f"{eq.nombre} presenta a una joya de su cantera",
                             f"{nuevo.nombre_completo} ({nuevo.posicion}, {nuevo.edad} años, media "
                             f"{nuevo.overall}) sube al primer equipo de {eq.nombre}.")
            except Exception as e:
                logger.error(f"Cantera de {getattr(eq, 'nombre', '?')}: {e}")
    return altas
