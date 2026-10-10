# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Correo de la oficina (v3.1.0)
Mensajes de la directiva, los jugadores, el cuerpo médico y otros clubes. Se guardan con la
partida en datos_carrera['correo'] (lo más nuevo primero, tope MAX_CORREOS). Cada mensaje
puede traer una acción: la pantalla a la que lleva su botón.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

MAX_CORREOS = 200
REMITENTES = {'directiva': "Directiva", 'jugador': "Jugador", 'medico': "Cuerpo médico", 'club': "Club",
              'prensa': "Prensa",   # v4.6.0: noticias (quiebras de la IA)
              'cantera': "Cantera",   # v4.8.0: informe semestral
              'patrocinador': "Patrocinador",   # v4.9.0
              'presidente': "Presidente"}   # v0.4.10.0: personal y directo (canal MENSAJES)


def bandeja(estado: dict) -> list:
    return estado.setdefault('datos_carrera', {}).setdefault('correo', [])


def accion(pantalla: str, texto: str) -> dict:
    return {'pantalla': pantalla, 'texto': texto}


# v0.4.10.0: NOTIFICACIONES = MENSAJES (lo personal) + CORREO (lo institucional del club)
CANAL_MENSAJE = ('jugador', 'presidente')


def canal(msg: dict) -> str:
    return msg.get('canal') or ('mensaje' if msg.get('remitente') in CANAL_MENSAJE else 'correo')


def de_canal(estado: dict, cual: str) -> list:
    return [m for m in bandeja(estado) if canal(m) == cual]


# v4.7.0: firma de cada remitente (los jugadores escriben a su manera: sin plantilla)
FIRMAS = {'directiva': "La Directiva de {club}", 'medico': "Cuerpo médico de {club}",
          'club': "Secretaría técnica de {club}", 'prensa': "Redacción deportiva",
          'cantera': "Coordinación de cantera de {club}",
          'patrocinador': "Departamento comercial de {club}"}


def _nombre_jugador(j) -> str:
    return f"{getattr(j, 'nombre', '')} {getattr(j, 'apellido', '')}".strip()


def _refs(msg: dict) -> list:
    """v0.4.14.1: [(id, nombre)] de los jugadores de los que trata el mensaje: su 'jugador' y los
    protagonistas de su evento (de estos solo se guarda el id)."""
    refs = []
    ref = msg.get('jugador')
    if isinstance(ref, dict):
        refs.append((ref.get('id'), ref.get('nombre') or ''))
    for i in (msg.get('evento') or {}).get('protagonistas') or []:
        refs.append((i, ''))
    return refs


def _buscar(estado: dict, ref: tuple):
    """El jugador de tu plantilla con ese id (y ese nombre: el id solo es único dentro de un club)."""
    i, nombre = ref
    for j in getattr(estado.get('mi_equipo'), 'jugadores', []) or []:
        if getattr(j, 'id', None) == i and (not nombre or _nombre_jugador(j) == nombre):
            return j
    return None


def jugador_de(estado: dict, msg: dict):
    """v0.4.14.1: el jugador del que trata el mensaje, si sigue en tu plantilla (None si no trata de
    ninguno o si ya se fue)."""
    refs = _refs(msg)
    return _buscar(estado, refs[0]) if refs else None


def vigente(estado: dict, msg: dict) -> bool:
    """v0.4.14.1: False si el mensaje trata de un jugador que ya no está en tu plantilla."""
    return all(_buscar(estado, ref) is not None for ref in _refs(msg))


def _hoy_iso(estado: dict) -> Optional[str]:
    """v0.4.14.1: la fecha de hoy ('AAAA-MM-DD') para sellar el mensaje. Con reloj se lee tal cual, sin pasar
    por calendario.asegurar: un correo enviado a mitad de un cambio de temporada no debe rearmar el bloque."""
    try:
        cal = (estado.get('datos_carrera') or {}).get('calendario')
        dia = cal.get('dia') if isinstance(cal, dict) else None
        if dia:
            return date.fromisoformat(str(dia)).isoformat()
        if estado.get('liga') is None or estado.get('mi_equipo') is None:
            return None
        from alpha_football import temporada as T
        return T.fecha(estado).isoformat()
    except Exception as e:
        logger.error(f"correo: no se pudo leer la fecha de hoy: {e}")
        return None


def texto_fecha(msg: dict) -> str:
    """v0.4.14.1: 'sáb 15 ago 2026'. Los mensajes sin fecha (saves viejos) siguen con 'T1 J5'."""
    try:
        if msg.get('fecha'):
            from alpha_football.calendario import texto_fecha as _texto
            return _texto(date.fromisoformat(str(msg['fecha'])))
    except ValueError as e:
        logger.debug(f"correo: fecha ilegible en el mensaje {msg.get('id')}: {e}")
    return f"T{msg.get('temporada', 1)} J{msg.get('jornada', 1)}"


def enviar(estado: dict, remitente: str, asunto: str, cuerpo: str, accion: Optional[dict] = None,
           firma: Optional[str] = None, jugador=None) -> dict:
    """`firma`: quién firma si no es tu club (p. ej. la directiva de otro club que te ofrece el banquillo).
    `jugador` (v0.4.14.1): el jugador de tu plantilla del que trata el mensaje."""
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
    hoy = _hoy_iso(estado)                       # v0.4.14.1: fecha exacta
    if hoy:
        msg['fecha'] = hoy
    if jugador is not None:                      # v0.4.14.1
        msg['jugador'] = {'id': getattr(jugador, 'id', None), 'nombre': _nombre_jugador(jugador)}
    cola = estado.get('_diferir_correos')        # v0.4.12.0: dentro de dias.diferir_correos va a la agenda
    if cola is not None:
        msg['id'] = 0                            # el id se asigna al entregarlo (correo.entregar)
        cola.append({'fecha': None, 'tipo': 'correo', 'datos': msg})
        return msg
    lista.insert(0, msg)
    del lista[MAX_CORREOS:]
    return msg


def entregar(estado: dict, msg: dict) -> dict:
    """v0.4.12.0: pasa a la bandeja un mensaje que esperaba en la agenda (dias.py)."""
    lista = bandeja(estado)
    msg['id'] = max((int(m.get('id', 0)) for m in lista), default=0) + 1
    hoy = _hoy_iso(estado)                       # v0.4.14.1: la fecha es la del día en que llega
    if hoy:
        msg['fecha'] = hoy
    lista.insert(0, msg)
    del lista[MAX_CORREOS:]
    return msg


def formatear(estado: dict, msg: dict) -> str:
    """v4.7.0: el correo como se lee: saludo, cuerpo y firma (los de jugadores, tal cual)."""
    cuerpo = str(msg.get('cuerpo', ''))
    remitente = msg.get('remitente')
    if remitente == 'presidente':          # v0.4.10.0: personal, sin "Estimado míster… Atentamente"
        return f"{cuerpo}\n\nEl presidente"
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
    try:   # v0.4.10.0: un evento sin responder no se pierde al limpiar: se aplica su opción por defecto
        from alpha_football import eventos as EV
        EV.resolver_pendientes(estado)
    except Exception as e:
        logger.error(f"No se pudieron cerrar los eventos pendientes: {e}")
    t = int(estado.get('temporada', 1) or 1)
    lista = bandeja(estado)
    lista[:] = [m for m in lista if int(m.get('temporada', t) or t) >= t]


def no_leidos(estado: dict, cual: Optional[str] = None) -> int:
    return sum(1 for m in bandeja(estado) if not m.get('leido') and (cual is None or canal(m) == cual))


def marcar_leido(estado: dict, msg_id: int) -> None:
    for m in bandeja(estado):
        if m.get('id') == msg_id:
            m['leido'] = True


def retorno(estado: dict, actual: str, siguiente: Optional[str]) -> Optional[str]:
    """v0.4.11.0: la pantalla abierta desde un mensaje (estado['volver_notif']) vuelve a ese mensaje
    al salir con VOLVER/ESC, en vez de al hub. Devuelve la pantalla a la que hay que ir."""
    marca = estado.get('volver_notif')
    if not marca or not siguiente:
        return siguiente
    if actual == marca and siguiente in ('volver', 'league_screen'):
        estado.pop('volver_notif', None)
        return 'correo_screen'
    # ya estaba en el hub y siguió por otro camino: la marca era de una visita anterior
    if actual == 'league_screen' and marca != 'league_screen' and siguiente != 'correo_screen':
        estado.pop('volver_notif', None)
    return siguiente
