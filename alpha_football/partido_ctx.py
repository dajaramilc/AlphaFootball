# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — ESTADO VIVO DEL PARTIDO (v4.0.0)
Quién está en cancha, tarjetas, cambios, notas, goles, minutos e incidencias de UN partido.
El motor genera eventos y los aplica aquí; la pantalla en vivo aplica los mismos eventos a su
copia a medida que los revela. `aplicar_evento` es la ÚNICA función que modifica el estado.
Las lesiones/sanciones NO se escriben en el jugador hasta el cierre del partido (incidencias):
si se escribieran antes, `_once_titular` metería un suplente por su cuenta.
Claves: `clave(j)` = identidad del objeto. `jugador.id` solo es único DENTRO de un equipo (dos
rivales pueden compartir ids), así que los eventos llevan los objetos (`jugador`, `asistente`,
`defensor`, `sale`, `entra`) además de `jugador_id` (compatibilidad con la UI).
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

NOTA_BASE = 6.0
DELTA_NOTA = {'gol': 1.0, 'asistencia': 0.5, 'atajada': 0.4, 'tiro': -0.2, 'ocasion': -0.2,
              'amarilla': -0.3, 'roja': -1.5, 'penal_fallado': -0.6, 'batido': -0.3, 'defensa': 0.1}
BONO_VALLA = 0.5            # DEF/POR con >= 60' y su equipo sin goles en contra
BONO_RESULTADO = {'G': 0.5, 'E': 0.0, 'P': -0.4}
RUIDO = 0.3
MAX_CAMBIOS = 5
MULT_EXPULSION = 0.85


@dataclass
class EstadoPartido:
    en_cancha: dict                                 # {'l': [Jugador], 'v': [Jugador]}
    auto_cambios: dict                              # {'l': bool, 'v': bool} (False = lo decide el user)
    ids_equipo: dict                                # {'l': equipo.id, 'v': equipo.id}
    amarillas: dict = field(default_factory=dict)
    expulsados: dict = field(default_factory=lambda: {'l': 0, 'v': 0})
    fuera: set = field(default_factory=set)         # jids expulsados o lesionados
    cambios: dict = field(default_factory=lambda: {'l': 0, 'v': 0})
    notas: dict = field(default_factory=dict)       # deltas acumulados por jid (sin la base)
    goles: dict = field(default_factory=dict)
    asist: dict = field(default_factory=dict)
    entrada: dict = field(default_factory=dict)     # jid -> minuto en que entró (0 = titular)
    salida: dict = field(default_factory=dict)      # jid -> minuto en que salió
    incidencias: list = field(default_factory=list)
    posicion: dict = field(default_factory=dict)    # jid -> 'POR'/'DEF'/'MED'/'DEL'
    lado_jugador: dict = field(default_factory=dict)
    jugadores: dict = field(default_factory=dict)   # clave -> objeto Jugador
    objetivo_cambios: dict = field(default_factory=dict)   # lado -> cambios que hará la IA
    fin: int = 90                                   # v4.4.0: último minuto (90 + adición)

    def copia(self) -> 'EstadoPartido':
        """Copia independiente (listas/dicts nuevos; los Jugador son los mismos objetos)."""
        return EstadoPartido(
            en_cancha={k: list(v) for k, v in self.en_cancha.items()},
            auto_cambios=dict(self.auto_cambios), ids_equipo=dict(self.ids_equipo),
            amarillas=dict(self.amarillas), expulsados=dict(self.expulsados), fuera=set(self.fuera),
            cambios=dict(self.cambios), notas=dict(self.notas), goles=dict(self.goles),
            asist=dict(self.asist), entrada=dict(self.entrada), salida=dict(self.salida),
            incidencias=[dict(i) for i in self.incidencias], posicion=dict(self.posicion),
            lado_jugador=dict(self.lado_jugador), jugadores=dict(self.jugadores),
            objetivo_cambios=dict(self.objetivo_cambios), fin=self.fin)

    def lado_de_equipo(self, equipo_id) -> Optional[str]:
        for lado, eid in self.ids_equipo.items():
            if eid == equipo_id:
                return lado
        return None


def clave(j):
    """Clave de un jugador dentro del partido (None si no hay jugador)."""
    return None if j is None else id(j)


def _registrar(ctx: EstadoPartido, lado: str, j, minuto: int) -> None:
    jid = clave(j)
    ctx.jugadores[jid] = j
    ctx.entrada.setdefault(jid, minuto)
    ctx.posicion[jid] = getattr(j, 'posicion', 'MED')
    ctx.lado_jugador[jid] = lado


def nuevo_estado(local, visitante, once_l: list, once_v: list, auto_l: bool = True,
                 auto_v: bool = True) -> EstadoPartido:
    ctx = EstadoPartido(en_cancha={'l': list(once_l), 'v': list(once_v)},
                        auto_cambios={'l': auto_l, 'v': auto_v},
                        ids_equipo={'l': getattr(local, 'id', None), 'v': getattr(visitante, 'id', None)})
    for lado in ('l', 'v'):
        for j in ctx.en_cancha[lado]:
            _registrar(ctx, lado, j, 0)
    return ctx


def _sumar(ctx: EstadoPartido, jid, clave: str) -> None:
    if jid is not None:
        ctx.notas[jid] = ctx.notas.get(jid, 0.0) + DELTA_NOTA[clave]


def _sacar(ctx: EstadoPartido, lado: str, jid, minuto: int) -> None:
    ctx.en_cancha[lado] = [j for j in ctx.en_cancha[lado] if clave(j) != jid]
    ctx.salida[jid] = minuto


def aplicar_evento(ctx: EstadoPartido, ev: dict) -> None:
    """Aplica UN evento al estado. Eventos sin efecto (caotico, mentalidad, falta) no hacen nada."""
    try:
        t = ev.get('tipo')
        jid = clave(ev.get('jugador'))
        m = int(ev.get('minuto', 0) or 0)
        lado = ev.get('lado') or ctx.lado_de_equipo(ev.get('equipo_id'))
        if t == 'gol':
            ctx.goles[jid] = ctx.goles.get(jid, 0) + 1
            _sumar(ctx, jid, 'gol')
            if ev.get('asistente') is not None:
                a = clave(ev['asistente'])
                ctx.asist[a] = ctx.asist.get(a, 0) + 1
                _sumar(ctx, a, 'asistencia')
            _sumar(ctx, clave(ev.get('defensor')), 'batido')
        elif t in ('tiro', 'ocasion', 'atajada', 'defensa', 'penal_fallado', 'amarilla'):
            _sumar(ctx, jid, t)
            if t == 'amarilla':
                ctx.amarillas[jid] = ctx.amarillas.get(jid, 0) + 1
        elif t == 'roja':
            _sumar(ctx, jid, 'roja')
            ctx.fuera.add(jid)
            ctx.expulsados[lado] = ctx.expulsados.get(lado, 0) + 1
            _sacar(ctx, lado, jid, m)
            ctx.incidencias.append({'tipo': 'sancion', 'jugador_id': jid, 'partidos': int(ev.get('partidos', 1))})
        elif t == 'lesion':
            ctx.fuera.add(jid)
            _sacar(ctx, lado, jid, m)
            ctx.incidencias.append({'tipo': 'lesion', 'jugador_id': jid, 'partidos': int(ev.get('partidos', 1))})
        elif t == 'cambio':
            sale = clave(ev.get('sale'))
            entra = ev.get('entra')
            if sale is not None and sale not in ctx.fuera:
                _sacar(ctx, lado, sale, m)
            if entra is not None:
                ctx.en_cancha[lado].append(entra)
                _registrar(ctx, lado, entra, m)
            ctx.cambios[lado] = ctx.cambios.get(lado, 0) + 1
    except Exception as e:
        logger.error(f"aplicar_evento: evento inválido {ev.get('tipo')}: {e}")


def minutos_jugados(ctx: EstadoPartido, fin: Optional[int] = None) -> dict:
    """{clave: minutos en cancha} de todos los que jugaron (titulares y los que entraron)."""
    fin = int(getattr(ctx, 'fin', 90) or 90) if fin is None else fin   # v4.4.0: incluye la adición
    return {jid: max(0, int(ctx.salida.get(jid, fin)) - int(ent)) for jid, ent in ctx.entrada.items()}


def nota_en_vivo(ctx: EstadoPartido, jid) -> float:
    """Nota durante el partido: base + eventos (sin resultado ni ruido)."""
    return round(NOTA_BASE + ctx.notas.get(jid, 0.0), 1)


def notas_finales(ctx: EstadoPartido, goles_l: int, goles_v: int, rng=None) -> dict:
    """Nota final de cada jugador que pisó la cancha, en [3.0, 10.0]."""
    azar = rng or random.Random()
    out = {}
    for jid, mm in minutos_jugados(ctx).items():
        if mm <= 0 and jid not in ctx.fuera:
            continue
        lado = ctx.lado_jugador.get(jid, 'l')
        gf, gc = (goles_l, goles_v) if lado == 'l' else (goles_v, goles_l)
        n = NOTA_BASE + ctx.notas.get(jid, 0.0)
        n += BONO_RESULTADO['G' if gf > gc else 'P' if gf < gc else 'E']
        if gc == 0 and ctx.posicion.get(jid) in ('DEF', 'POR') and mm >= 60:
            n += BONO_VALLA
        n += azar.uniform(-RUIDO, RUIDO)
        out[jid] = max(3.0, min(10.0, round(n, 1)))
    return out


def resincronizar_user(ctx: EstadoPartido, lado: str, once: list, minuto: int) -> tuple:
    """
    v4.0.0: el lado del user en vivo toma su once de la alineación (el menú táctico hace los
    cambios ahí). Quien ya no está sale en `minuto`; quien aparece entra en `minuto`; los que
    están en `fuera` (expulsados/lesionados) nunca vuelven. Devuelve (salen, entran).
    """
    nuevos = [j for j in once if clave(j) not in ctx.fuera]
    claves_nuevas = {clave(j) for j in nuevos}
    claves_antes = {clave(j) for j in ctx.en_cancha[lado]}
    salen = [j for j in ctx.en_cancha[lado] if clave(j) not in claves_nuevas]
    entran = [j for j in nuevos if clave(j) not in claves_antes]
    for j in salen:
        ctx.salida[clave(j)] = minuto
    for j in entran:
        ctx.salida.pop(clave(j), None)
        if clave(j) not in ctx.entrada:
            _registrar(ctx, lado, j, minuto)
    ctx.en_cancha[lado] = nuevos
    return salen, entran


def minutos_por_id(ctx: EstadoPartido, lado: str) -> dict:
    """{jugador.id: minutos} de un lado (los ids son únicos dentro de un equipo)."""
    return {getattr(ctx.jugadores[k], 'id', None): m for k, m in minutos_jugados(ctx).items()
            if ctx.lado_jugador.get(k) == lado}


def incidencias_de(ctx: EstadoPartido, lado: str) -> list:
    """Incidencias (lesión/sanción) de un lado, con el objeto jugador en 'jugador', más una
    'amarilla' por cada amonestado que terminó el partido (la doble amarilla ya es roja y no suma
    a la acumulación: sanciones.py)."""
    out = [dict(i, jugador=ctx.jugadores.get(i['jugador_id'])) for i in ctx.incidencias
           if ctx.lado_jugador.get(i['jugador_id']) == lado]
    expulsados = {i['jugador_id'] for i in ctx.incidencias if i.get('tipo') == 'sancion'}
    for k, n in ctx.amarillas.items():
        if n > 0 and k not in expulsados and ctx.lado_jugador.get(k) == lado:
            out.append({'tipo': 'amarilla', 'jugador_id': k, 'partidos': 0, 'jugador': ctx.jugadores.get(k)})
    return out


def stats_de_equipo(ctx: EstadoPartido, notas: dict, lado: str) -> dict:
    """
    v4.0.0: lo que pasó en el partido para un lado, por clave de jugador (lo usa el desarrollo):
    jugaron (claves), goles, asist, notas, minutos, amarillas, rojas y lesiones.
    """
    mins = minutos_jugados(ctx)
    propias = [k for k, ld in ctx.lado_jugador.items() if ld == lado]
    jugaron = [k for k in propias if mins.get(k, 0) > 0 or k in ctx.fuera]
    inc = {i['jugador_id']: i['tipo'] for i in ctx.incidencias}
    return {'jugaron': jugaron,
            'goles': {k: ctx.goles.get(k, 0) for k in jugaron},
            'asist': {k: ctx.asist.get(k, 0) for k in jugaron},
            'notas': {k: notas[k] for k in jugaron if k in notas},
            'minutos': {k: mins.get(k, 0) for k in jugaron},
            'amarillas': {k: ctx.amarillas.get(k, 0) for k in jugaron},
            'roja': {k for k in jugaron if inc.get(k) == 'sancion'},
            'lesion': {k for k in jugaron if inc.get(k) == 'lesion'}}
