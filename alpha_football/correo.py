# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Correo de la oficina (v3.1.0)
Mensajes de la directiva, los jugadores, el cuerpo médico y otros clubes. Se guardan con la
partida en datos_carrera['correo'] (lo más nuevo primero, tope MAX_CORREOS). Cada mensaje
puede traer una acción: la pantalla a la que lleva su botón.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

MAX_CORREOS = 200
REMITENTES = {'directiva': "Directiva", 'jugador': "Jugador", 'medico': "Cuerpo médico", 'club': "Club"}


def bandeja(estado: dict) -> list:
    return estado.setdefault('datos_carrera', {}).setdefault('correo', [])


def accion(pantalla: str, texto: str) -> dict:
    return {'pantalla': pantalla, 'texto': texto}


def enviar(estado: dict, remitente: str, asunto: str, cuerpo: str, accion: Optional[dict] = None) -> dict:
    lista = bandeja(estado)
    liga = estado.get('liga')
    msg = {'id': max((int(m.get('id', 0)) for m in lista), default=0) + 1,
           'temporada': int(estado.get('temporada', 1) or 1),
           'jornada': int(getattr(liga, 'jornada_actual', 1) or 1),
           'remitente': remitente, 'asunto': str(asunto)[:80], 'cuerpo': str(cuerpo),
           'leido': False, 'accion': accion}
    lista.insert(0, msg)
    del lista[MAX_CORREOS:]
    return msg


def no_leidos(estado: dict) -> int:
    return sum(1 for m in bandeja(estado) if not m.get('leido'))


def marcar_leido(estado: dict, msg_id: int) -> None:
    for m in bandeja(estado):
        if m.get('id') == msg_id:
            m['leido'] = True
