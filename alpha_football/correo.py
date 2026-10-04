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
REMITENTES = {'directiva': "Directiva", 'jugador': "Jugador", 'medico': "Cuerpo médico", 'club': "Club",
              'prensa': "Prensa",   # v4.6.0: noticias (quiebras de la IA)
              'cantera': "Cantera",   # v4.8.0: informe semestral
              'patrocinador': "Patrocinador"}   # v4.9.0


def bandeja(estado: dict) -> list:
    return estado.setdefault('datos_carrera', {}).setdefault('correo', [])


def accion(pantalla: str, texto: str) -> dict:
    return {'pantalla': pantalla, 'texto': texto}


# v4.7.0: firma de cada remitente (los jugadores escriben a su manera: sin plantilla)
FIRMAS = {'directiva': "La Directiva de {club}", 'medico': "Cuerpo médico de {club}",
          'club': "Secretaría técnica de {club}", 'prensa': "Redacción deportiva",
          'cantera': "Coordinación de cantera de {club}",
          'patrocinador': "Departamento comercial de {club}"}


def enviar(estado: dict, remitente: str, asunto: str, cuerpo: str, accion: Optional[dict] = None,
           firma: Optional[str] = None) -> dict:
    """`firma`: quién firma si no es tu club (p. ej. la directiva de otro club que te ofrece el banquillo)."""
    lista = bandeja(estado)
    liga = estado.get('liga')
    msg = {'id': max((int(m.get('id', 0)) for m in lista), default=0) + 1,
           'temporada': int(estado.get('temporada', 1) or 1),
           'jornada': int(getattr(liga, 'jornada_actual', 1) or 1),
           'remitente': remitente, 'asunto': str(asunto)[:80], 'cuerpo': str(cuerpo),
           'leido': False, 'accion': accion,
           'club': getattr(estado.get('mi_equipo'), 'nombre', '')}
    if firma:
        msg['firma'] = str(firma)
    lista.insert(0, msg)
    del lista[MAX_CORREOS:]
    return msg


def formatear(estado: dict, msg: dict) -> str:
    """v4.7.0: el correo como se lee: saludo, cuerpo y firma (los de jugadores, tal cual)."""
    cuerpo = str(msg.get('cuerpo', ''))
    remitente = msg.get('remitente')
    if remitente == 'jugador' or remitente not in FIRMAS:
        return cuerpo
    partes = str(estado.get('dt_nombre', '') or '').split()
    saludo = f"Estimado míster {partes[-1]}:" if partes else "Estimado míster:"
    club = msg.get('club') or getattr(estado.get('mi_equipo'), 'nombre', '') or 'el club'
    firma = msg.get('firma') or FIRMAS[remitente].format(club=club)
    despedida = "Saludos cordiales," if remitente == 'prensa' else "Atentamente,"
    return f"{saludo}\n\n{cuerpo}\n\n{despedida}\n{firma}"


def borrar(estado: dict, msg_id: int) -> None:
    """v4.7.0: borra un correo de la bandeja."""
    lista = bandeja(estado)
    lista[:] = [m for m in lista if m.get('id') != msg_id]


def limpiar_temporadas_anteriores(estado: dict) -> None:
    """v4.7.0: al empezar la temporada se borran los correos de las anteriores."""
    t = int(estado.get('temporada', 1) or 1)
    lista = bandeja(estado)
    lista[:] = [m for m in lista if int(m.get('temporada', t) or t) >= t]


def no_leidos(estado: dict) -> int:
    return sum(1 for m in bandeja(estado) if not m.get('leido'))


def marcar_leido(estado: dict, msg_id: int) -> None:
    for m in bandeja(estado):
        if m.get('id') == msg_id:
            m['leido'] = True
