# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Préstamos de jugadores (spec 2026-09-25-prestamos-design.md)
Pedir a préstamo y ceder por 6 meses o 1 año con el sueldo repartido en %. El jugador juega y
progresa en el club donde está. Idas y vueltas solo con el mercado abierto: si se acuerda con el
mercado cerrado, queda en datos_carrera['prestamos_pendientes'] para la próxima ventana. Sin UI.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

DURACIONES = (6, 12)
PCT_PASO = 10
PCT_MIN_SUPLENTE, PCT_MIN_TITULAR = 30, 60
MARGEN_ANALISIS_PEDIDO = 20
MARGEN_ANALISIS_CONTRA = 15
PROB_OFERTA_PRESTAMO = 0.30
PROB_ACEPTA_ANALISIS = 0.5
DIF_NIVEL_JUGADOR = 6
MOTIVO_FIN_CONTRATO = "se le termina el contrato"


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _pendientes(estado: dict) -> list:
    return _dc(estado).setdefault('prestamos_pendientes', [])


def _nombre(j) -> str:
    return getattr(j, 'nombre_completo', None) or f"{getattr(j, 'nombre', '')} {getattr(j, 'apellido', '')}".strip()


def _momento(estado: dict) -> tuple:
    liga = estado.get('liga')
    return (int(estado.get('temporada', 1) or 1), int(getattr(liga, 'jornada_actual', 1) or 1),
            int(getattr(liga, 'num_jornadas', 22) or 22))


def _abierto(estado: dict) -> bool:
    from alpha_football.traspasos_pendientes import mercado_abierto
    return mercado_abierto(estado)


def _equipos(estado: dict) -> list:
    from alpha_football.traspasos_pendientes import _equipos as equipos
    return equipos(estado)


def _club(estado: dict, nombre: Optional[str]):
    from alpha_football.traspasos_pendientes import _club as club
    return club(estado, nombre)


def _mi(estado: dict):
    return estado.get('mi_equipo')


def _es_internacional(club) -> bool:
    """Los clubes de relleno de las copas no se guardan (se regeneran): no entran en préstamos."""
    try:
        from alpha_football.negociacion import es_club_internacional
        return es_club_internacional(club)
    except Exception as e:
        logger.error(f"No se pudo saber si {getattr(club, 'nombre', '?')} es internacional: {e}")
        return False


def _llegan_a(estado: dict, nombre_club: str) -> int:
    """Jugadores acordados que todavía no llegaron a ese club (préstamos y compras diferidas)."""
    n = sum(1 for p in _pendientes(estado) if p.get('tipo') == 'inicio' and p.get('club') == nombre_club)
    n += sum(1 for p in _dc(estado).get('traspasos_pendientes') or []
             if p.get('tipo') == 'compra' and p.get('destino') == nombre_club)
    return n


def regreso(estado: dict, meses: int) -> list:
    """[temporada, jornada] del regreso: primer día de la ventana que corresponde a la duración."""
    t, _k, j = _regreso(estado, meses)
    return [t, j]


def _regreso(estado: dict, meses: int) -> tuple:
    """(temporada, nombre de la ventana, jornada) del regreso."""
    from alpha_football.market import ventanas_mercado
    t, j, n = _momento(estado)
    vs = ventanas_mercado(n)
    if _abierto(estado):
        k = next(i for i, v in enumerate(vs) if v[0] <= j <= v[1])
    else:
        k = next((i for i, v in enumerate(vs) if v[0] > j), None)
        if k is None:
            k, t = 0, t + 1
    if int(meses) >= 12:
        return t + 1, vs[k][2], vs[k][0]
    k += 1
    if k >= len(vs):
        # desde el cierre, 6 meses = el invierno de la temporada siguiente (el inicio es la misma
        # ventana de verano); sin invierno, el cierre siguiente
        k, t = (1 if len(vs) > 2 else len(vs) - 1), t + 1
    return t, vs[k][2], vs[k][0]


def _vuelve(p: dict, n: int) -> list:
    """Regreso con la jornada recalculada por su ventana (la liga pudo cambiar de tamaño). La ventana
    se guarda por nombre; si la liga ya no tiene invierno, vale el cierre. Índices = saves de antes."""
    from alpha_football.market import ventanas_mercado
    v = list(p.get('vuelve') or [0, 0])
    k = p.get('ventana')
    vs = ventanas_mercado(n)
    if isinstance(k, str):
        w = next((x for x in vs if x[2] == k), vs[-1])
        v[1] = w[0]
    elif isinstance(k, int) and 0 <= k < len(vs):
        v[1] = vs[k][0]
    return v


def entrantes(estado: dict) -> list:
    """Jugadores que el user tiene a préstamo (están en su plantilla)."""
    return [j for j in getattr(_mi(estado), 'jugadores', []) or [] if getattr(j, 'prestamo', None)]


_CACHE_CEDIDOS: dict = {}     # (id(estado), dueño) -> (firma de las plantillas, [(jugador, club)])


def _invalidar() -> None:
    _CACHE_CEDIDOS.clear()


def cedidos(estado: dict, nombre_club: Optional[str] = None) -> list:
    """(jugador, club donde juega) de los que `nombre_club` (por defecto el del user) tiene cedidos.
    Se llama cada frame (PLANTILLA, negociación, finanzas): se cachea mientras ninguna plantilla
    cambie de tamaño y los cacheados sigan cedidos en el mismo club."""
    dueno = nombre_club or getattr(_mi(estado), 'nombre', None)
    if not dueno:
        return []
    equipos = _equipos(estado)
    firma = tuple((id(eq), len(eq.jugadores)) for eq in equipos)
    clave = (id(estado), dueno)
    hit = _CACHE_CEDIDOS.get(clave)
    # validación por identidad y posición (sin recorrer plantillas ni usar el __eq__ del dataclass)
    if hit and hit[0] == firma and all((getattr(j, 'prestamo', None) or {}).get('dueno') == dueno
                                       and i < len(eq.jugadores) and eq.jugadores[i] is j
                                       for (j, eq), i in zip(hit[1], hit[2])):
        return list(hit[1])
    res, pos = [], []
    for eq in equipos:
        for i, j in enumerate(eq.jugadores):
            if (getattr(j, 'prestamo', None) or {}).get('dueno') == dueno:
                res.append((j, eq)); pos.append(i)
    for k in [k for k in _CACHE_CEDIDOS if k[0] != id(estado)]:     # no retener otra carrera
        del _CACHE_CEDIDOS[k]
    _CACHE_CEDIDOS[clave] = (firma, res, pos)
    return list(res)


def _correo(estado: dict, asunto: str, cuerpo: str, pantalla: str = 'plantilla_screen') -> None:
    try:
        from alpha_football import correo as C
        C.enviar(estado, 'club', asunto, cuerpo,
                 C.accion(pantalla, "VER OFERTAS" if pantalla == 'ofertas_screen' else "VER PLANTILLA"))
    except Exception as e:
        logger.error(f"No se pudo enviar el correo del préstamo: {e}")


def _afecta_al_user(estado: dict, *clubes) -> bool:
    mi = getattr(_mi(estado), 'nombre', None)
    return mi is not None and mi in clubes


def _texto_regreso(vuelve: list) -> str:
    return f"la jornada {vuelve[1]} de la temporada {vuelve[0]}"


def _periodo(p: dict) -> str:
    """'Periodo: 6 meses (desde J3 T1 hasta J11 T1).'"""
    d, v = p.get('desde'), p.get('vuelve') or ['?', '?']
    dur = "1 año" if int(p.get('meses', 6) or 6) >= 12 else "6 meses"
    desde = f"desde J{d[1]} T{d[0]} " if d else ""          # préstamos de saves previos no la tienen
    return f"Periodo: {dur} ({desde}hasta J{v[1]} T{v[0]})."


def _sueldo(estado: dict, p: dict) -> str:
    pct = int(p.get('pct_dueno', 0) or 0)
    if p.get('club') == getattr(_mi(estado), 'nombre', None):
        return f"Pagas el {100 - pct}% del sueldo; {p.get('dueno')} paga el {pct}%."
    return f"{p.get('club')} paga el {100 - pct}% del sueldo; tú sigues pagando el {pct}%."


def _correo_prestamo(estado: dict, jugador_o_nombre, p: dict, evento: str, motivo: str = "",
                     salida: str = 'vuelve') -> None:
    """Único correo de préstamos para el user: 'acordado' (espera la ventana), 'ida' (se movió) o
    'vuelta' (salida: 'vuelve' | 'contrato' = vuelve sin contrato | 'libre' = el dueño ya no existe).
    Siempre con el periodo y el reparto del sueldo. Un dato raro nunca corta el cierre de jornada."""
    try:
        if not _afecta_al_user(estado, p.get('dueno'), p.get('club')):
            return
        nombre = jugador_o_nombre if isinstance(jugador_o_nombre, str) else _nombre(jugador_o_nombre)
        llega = p.get('club') == getattr(_mi(estado), 'nombre', None)
        if evento == 'acordado':
            asunto = f"Préstamo acordado: {nombre}"
            cuerpo = (f"{nombre} {'llegará desde ' + str(p.get('dueno')) if llega else 'se irá a ' + str(p.get('club'))} "
                      f"a préstamo en la jornada {(p.get('desde') or ['?', '?'])[1]}, en cuanto se abra el mercado.")
        elif evento == 'ida':
            asunto = f"{nombre} {'llegó a préstamo' if llega else 'se fue cedido'}"
            cuerpo = (f"{nombre} {'llegó desde ' + str(p.get('dueno')) if llega else 'se fue a ' + str(p.get('club'))} "
                      f"a préstamo hasta {_texto_regreso(p.get('vuelve') or ['?', '?'])}.")
        else:
            inicio = f"{(motivo or 'terminó el préstamo').capitalize()}: {nombre} dejó {p.get('club', 'el club')}"
            if salida == 'libre':
                asunto = f"{nombre} queda libre"
                cuerpo = f"{inicio}; su club ({p.get('dueno')}) ya no existe y queda libre. {_periodo(p)}"
            elif salida == 'contrato':
                asunto = f"{nombre} vuelve a {p.get('dueno', 'su club')}"
                cuerpo = f"{inicio} y vuelve a {p.get('dueno', 'su club')}; si no renueva, queda libre. {_periodo(p)}"
            else:
                asunto = f"{nombre} vuelve a {p.get('dueno', 'su club')}"
                cuerpo = (f"{inicio} y volvió a {p.get('dueno', 'su club')}. {_periodo(p)} "
                          + ("Ya no pagas su sueldo." if llega else "Vuelves a pagar el 100% de su sueldo."))
            if llega and salida != 'vuelve':
                cuerpo += " Ya no pagas su sueldo."
            _correo(estado, asunto, cuerpo)
            return
        _correo(estado, asunto, f"{cuerpo} {_periodo(p)} {_sueldo(estado, p)}")
    except Exception as e:
        logger.error(f"No se pudo armar el correo del préstamo ({evento}): {e}")


def _mover_ida(estado: dict, jugador, dueno, destino, reg: dict) -> None:
    from alpha_football.finanzas import quitar_de_plantilla, completar_plantilla
    quitar_de_plantilla(dueno, jugador)
    destino.jugadores.append(jugador)
    if destino is not _mi(estado):
        destino.alineacion_activa = None
    t, jor, _n = _momento(estado)
    jugador.prestamo = {k: reg[k] for k in ('dueno', 'club', 'pct_dueno', 'vuelve', 'meses', 'ventana') if k in reg}
    jugador.prestamo['desde'] = [t, jor]
    _invalidar()
    jugador.transferible = False
    lista = _dc(estado).get('lista_prestamo') or []
    if jugador.nombre_completo in lista:
        lista.remove(jugador.nombre_completo)
    if dueno is _mi(estado):
        completar_plantilla(dueno)
    _correo_prestamo(estado, jugador, jugador.prestamo, 'ida')


def _mover_vuelta(estado: dict, jugador, motivo: str = "terminó el préstamo") -> None:
    """Devuelve al jugador a su dueño (o a agentes libres si el dueño ya no existe)."""
    from alpha_football.finanzas import quitar_de_plantilla, completar_plantilla
    p = dict(jugador.prestamo or {})
    t, jor, _n = _momento(estado)
    p['vuelve'] = [t, jor]                 # para el correo: la fecha real (CONCLUIR, fin de contrato)
    club = next((eq for eq in _equipos(estado) if jugador in eq.jugadores), None)
    dueno = _club(estado, p.get('dueno'))
    if club is not None:
        quitar_de_plantilla(club, jugador)
        if club is _mi(estado):
            completar_plantilla(club)
    jugador.prestamo = None
    _invalidar()
    if dueno is not None:
        dueno.jugadores.append(jugador)
        if dueno is not _mi(estado):
            dueno.alineacion_activa = None
    else:
        logger.warning(f"El dueño de {_nombre(jugador)} ({p.get('dueno')}) no existe: queda libre")
        jugador.fin_de_contrato = True
        estado.setdefault('free_agents_list', []).append(jugador)
    salida = 'libre' if dueno is None else 'contrato' if motivo == MOTIVO_FIN_CONTRATO else 'vuelve'
    _correo_prestamo(estado, jugador, p, 'vuelta', motivo, salida)


def iniciar(estado: dict, jugador, dueno, destino, meses: int, pct_dueno: int) -> str:
    """Préstamo acordado. Con el mercado abierto se mueve ya; si no, espera la ventana. Texto para el correo/UI."""
    from alpha_football.traspasos_pendientes import jornada_apertura
    t, k, jv = _regreso(estado, meses)
    reg = {'jugador': _nombre(jugador), 'jugador_id': getattr(jugador, 'id', None),
           'dueno': dueno.nombre, 'club': destino.nombre, 'pct_dueno': int(pct_dueno),
           'vuelve': [t, jv], 'ventana': k, 'meses': int(meses)}
    if _abierto(estado):
        _mover_ida(estado, jugador, dueno, destino, reg)
        return f"{_nombre(jugador)} juega en {destino.nombre} a préstamo hasta {_texto_regreso(reg['vuelve'])}."
    ap = jornada_apertura(estado)
    t_hoy, jor_hoy, _n = _momento(estado)
    reg['desde'] = [t_hoy if ap > jor_hoy else t_hoy + 1, ap]
    _pendientes(estado).append(dict(reg, tipo='inicio'))
    _correo_prestamo(estado, jugador, reg, 'acordado')
    return (f"{_nombre(jugador)} se irá a {destino.nombre} a préstamo en la jornada {ap}, "
            "en cuanto se abra el mercado.")


def pendiente_de(estado: dict, jugador) -> Optional[dict]:
    return next((p for p in _pendientes(estado) if p.get('jugador') == _nombre(jugador)), None)


def terminar(estado: dict, jugador) -> str:
    """CONCLUIR PRÉSTAMO: vuelve ya con el mercado abierto; si no, en la próxima ventana."""
    from alpha_football.traspasos_pendientes import jornada_apertura
    if not getattr(jugador, 'prestamo', None):
        return "Ese jugador no está a préstamo."
    if _abierto(estado):
        _mover_vuelta(estado, jugador, "se concluyó el préstamo")
        return f"{_nombre(jugador)} volvió a su club."
    if not any(p.get('tipo') == 'fin' and p.get('jugador') == _nombre(jugador) for p in _pendientes(estado)):
        _pendientes(estado).append({'tipo': 'fin', 'jugador': _nombre(jugador)})
    return f"{_nombre(jugador)} vuelve a su club en la jornada {jornada_apertura(estado)}, cuando se abra el mercado."


def cancelar_pendiente(estado: dict, p: dict) -> str:
    """Panel PRÉSTAMOS: anula un préstamo acordado que espera la ventana o un regreso acordado."""
    if p in _pendientes(estado):
        _pendientes(estado).remove(p)
    if p.get('tipo') == 'fin':
        return f"{p.get('jugador')} sigue a préstamo."
    return f"Cancelaste el préstamo de {p.get('jugador')}."


def _ejecutar_pendientes(estado: dict) -> None:
    for p in list(_pendientes(estado)):
        _pendientes(estado).remove(p)
        try:
            nombre = p.get('jugador')
            if p.get('tipo') == 'fin':
                j = next((x for eq in _equipos(estado) for x in eq.jugadores
                          if _nombre(x) == nombre and getattr(x, 'prestamo', None)), None)
                if j is not None:
                    _mover_vuelta(estado, j, "se concluyó el préstamo")
                continue
            dueno, destino = _club(estado, p.get('dueno')), _club(estado, p.get('club'))
            j = next((x for x in getattr(dueno, 'jugadores', []) or [] if _nombre(x) == nombre), None)
            if dueno is None or destino is None or j is None:
                if _afecta_al_user(estado, p.get('dueno'), p.get('club')):
                    _correo(estado, f"Se cayó el préstamo de {nombre}",
                            f"{nombre} ya no está disponible: el préstamo quedó sin efecto.")
                continue
            from alpha_football.market import PLANTILLA_MAXIMA
            if destino is _mi(estado) and len(destino.jugadores) >= PLANTILLA_MAXIMA:
                _correo(estado, f"Se cayó el préstamo de {nombre}",
                        f"Tu plantilla está llena ({PLANTILLA_MAXIMA}): {nombre} no pudo llegar y el préstamo quedó sin efecto.")
                continue
            _mover_ida(estado, j, dueno, destino, p)
        except Exception as e:
            logger.error(f"No se pudo concretar el préstamo pendiente de {p.get('jugador')}: {e}", exc_info=True)


def _vencidos(estado: dict) -> None:
    t, jor, n = _momento(estado)
    for eq in _equipos(estado):
        for j in list(eq.jugadores):
            p = getattr(j, 'prestamo', None)
            if not p:
                continue
            p['vuelve'] = _vuelve(p, n)
            if [t, jor] >= p['vuelve']:
                _mover_vuelta(estado, j)


def _avisar_contratos(estado: dict) -> None:
    """Ventana de cierre: aviso (una vez por temporada) de los cedidos a los que se les termina el
    contrato; al cerrar la temporada vuelven a su dueño (cierre_contratos) y ahí renuevan o quedan libres."""
    from alpha_football.market import ventanas_mercado
    t, jor, n = _momento(estado)
    vs = ventanas_mercado(n)
    if len(vs) < 2 or not vs[-1][0] <= jor <= vs[-1][1]:
        return
    mi = getattr(_mi(estado), 'nombre', None)
    avisados = _dc(estado).setdefault('avisos_contrato_prestamo', [])
    for j in entrantes(estado) + [x for x, _eq in cedidos(estado)]:
        p = j.prestamo or {}
        clave = f"{t}:{_nombre(j)}"
        if int(getattr(j, 'contrato_anios', 1) or 1) > 1 or clave in avisados:
            continue
        avisados.append(clave)
        _correo(estado, f"Contrato por vencer: {_nombre(j)}",
                f"A {_nombre(j)} se le termina el contrato: al cerrar la temporada deja {p.get('club')} "
                f"y vuelve a {p.get('dueno')}." + (" Para renovarlo, usa CONCLUIR en PLANTILLA → PRÉSTAMOS mientras "
                                                   "el mercado está abierto y luego RENOVAR; si no, quedará libre."
                                                   if p.get('dueno') == mi else ""))


def limpiar_ofertas(estado: dict) -> None:
    """Un jugador a préstamo no recibe ofertas de traspaso (ni por él ni por los tuyos cedidos)."""
    estado['ofertas_recibidas'] = [o for o in estado.get('ofertas_recibidas') or []
                                   if o.get('prestamo') or not getattr(o.get('jugador'), 'prestamo', None)]


def cierre_contratos(estado: dict) -> None:
    """Antes de descontar contratos: el cedido cuyo contrato vence vuelve a su dueño (ahí queda libre o renueva)."""
    for eq in _equipos(estado):
        for j in list(eq.jugadores):
            if getattr(j, 'prestamo', None) and int(getattr(j, 'contrato_anios', 1) or 1) <= 1:
                _mover_vuelta(estado, j, MOTIVO_FIN_CONTRATO)


def revisar_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Cierre de jornada (y J1 de cada temporada): con mercado abierto concreta pendientes y regresos."""
    try:
        if _abierto(estado):
            _ejecutar_pendientes(estado)
            _vencidos(estado)
            _avisar_contratos(estado)
    except Exception as e:
        logger.error(f"Error revisando los préstamos: {e}", exc_info=True)


# --- Pedir a préstamo ──────────────────────────────────────────────────────────

def _titular_en(equipo, jugador) -> bool:
    """True si el jugador está en el mejor once (4-3-3) de su equipo."""
    from alpha_football.formaciones import mejor_once
    js = list(getattr(equipo, 'jugadores', []) or [])
    return any(js[i] is jugador for i in mejor_once(js, "4-3-3"))


def evaluar_pedido(estado: dict, jugador, club, meses: int, pct_user: int) -> tuple:
    """('acepta'|'analiza'|'rechaza', mensaje) del club dueño ante tu pedido de préstamo."""
    mi = _mi(estado)
    pct_user = max(0, min(100, int(pct_user)))
    if getattr(jugador, 'prestamo', None) or pendiente_de(estado, jugador) is not None:
        return 'rechaza', f"{_nombre(jugador)} ya está a préstamo: no se vuelve a prestar."
    if _es_internacional(club):
        return 'rechaza', f"{club.nombre} es un club del exterior: no presta jugadores."
    from alpha_football.mercado_ia import PLANTILLA_MIN_VENDEDOR
    salen = sum(1 for p in _pendientes(estado) if p.get('tipo') == 'inicio' and p.get('dueno') == club.nombre)
    salen += sum(1 for p in _dc(estado).get('traspasos_pendientes') or []      # compras diferidas a ese club
                 if p.get('tipo') == 'compra' and p.get('origen') == club.nombre)
    if len(club.jugadores) - salen <= PLANTILLA_MIN_VENDEDOR:
        return 'rechaza', f"{club.nombre} tiene la plantilla corta: no presta jugadores."
    if jugador in sorted(club.jugadores, key=lambda x: -x.overall)[:3]:
        return 'rechaza', f"{club.nombre}: {_nombre(jugador)} es pieza clave, no se presta."
    try:
        from alpha_football.data.clasicos import es_clasico
        if mi is not None and es_clasico(club, mi):
            return 'rechaza', f"{club.nombre} no le presta jugadores a su clásico."
    except Exception as e:
        logger.error(f"No se pudo revisar el clásico en el préstamo: {e}")
    minimo = PCT_MIN_TITULAR if _titular_en(club, jugador) else PCT_MIN_SUPLENTE
    if pct_user >= minimo:
        return 'acepta', f"{club.nombre} acepta: pagas el {pct_user}% del sueldo."
    if pct_user >= minimo - MARGEN_ANALISIS_PEDIDO:
        t, jor, _n = _momento(estado)
        # un solo análisis por jugador: el nuevo pedido reemplaza al anterior
        pend = [a for a in _dc(estado).get('analisis_prestamos', []) if a.get('jugador') != _nombre(jugador)]
        pend.append({'jugador': _nombre(jugador), 'club': club.nombre, 'meses': int(meses), 'pct': pct_user,
                     'jornada': jor, 'temporada': t, 'destino': getattr(mi, 'nombre', None)})
        _dc(estado)['analisis_prestamos'] = pend
        return 'analiza', f"{club.nombre}: \"Lo analizamos\". Te responden por correo en la próxima jornada."
    return 'rechaza', f"{club.nombre} rechaza: quiere que pagues al menos el {minimo}% del sueldo."


def acepta_jugador(estado: dict, jugador, club) -> tuple:
    """El jugador acepta si tu club no es mucho peor que el suyo o si va a ser titular contigo."""
    from alpha_football.market import nivel_club
    mi = _mi(estado)
    if nivel_club(mi) >= nivel_club(club) - DIF_NIVEL_JUGADOR:
        return True, f"{_nombre(jugador)} acepta ir a préstamo."
    rivales = [x for x in mi.jugadores if x.posicion == jugador.posicion]
    peor_titular = min((x.overall for x in rivales if _titular_en(mi, x)), default=0)
    if jugador.overall > peor_titular:
        return True, f"{_nombre(jugador)} acepta: sabe que va a jugar."
    return False, f"{_nombre(jugador)} no quiere ir: cree que no va a tener minutos."


def cerrar_pedido(estado: dict, jugador, club, meses: int, pct_user: int) -> tuple:
    """Acuerdo con club y jugador: arranca el préstamo (ya o en la próxima ventana)."""
    from alpha_football.market import PLANTILLA_MAXIMA
    mi = _mi(estado)
    if len(mi.jugadores) + _llegan_a(estado, mi.nombre) >= PLANTILLA_MAXIMA:   # cuenta los que ya vienen
        return False, f"Plantilla llena ({PLANTILLA_MAXIMA}): libera un lugar antes de pedir a préstamo."
    if pendiente_de(estado, jugador) is not None or getattr(jugador, 'prestamo', None):
        return False, f"{_nombre(jugador)} ya tiene un préstamo acordado."
    return True, iniciar(estado, jugador, club, mi, meses, 100 - int(pct_user))


def resolver_analisis(estado: dict, azar) -> None:
    """Respuesta (50/50) a los pedidos en análisis de jornadas anteriores; si el club acepta y el
    jugador también, el préstamo arranca solo."""
    t, jor, _n = _momento(estado)
    pend = _dc(estado).setdefault('analisis_prestamos', [])
    for a in list(pend):
        if int(a.get('temporada', t)) == t and jor <= int(a.get('jornada', 0)):
            continue
        pend.remove(a)
        try:
            if a.get('destino') and a['destino'] != getattr(_mi(estado), 'nombre', None):
                logger.info(f"Pedido de préstamo de {a.get('jugador')} descartado: el DT ya no dirige {a['destino']}")
                continue
            club = _club(estado, a.get('club'))
            j = next((x for x in getattr(club, 'jugadores', []) or [] if _nombre(x) == a.get('jugador')), None)
            if club is None or j is None:
                _correo(estado, f"Préstamo sin efecto: {a.get('jugador')}", "El jugador ya no está en ese club.")
                continue
            if azar.random() >= PROB_ACEPTA_ANALISIS:
                _correo(estado, f"{club.nombre} no presta a {a['jugador']}",
                        f"No acepta que pagues el {a['pct']}% del sueldo.")
                continue
            ok_j, msg_j = acepta_jugador(estado, j, club)
            if not ok_j:
                _correo(estado, f"{a['jugador']} no acepta el préstamo", msg_j)
                continue
            ok, msg = cerrar_pedido(estado, j, club, a['meses'], a['pct'])
            asunto = (f"{club.nombre} acepta prestarte a {a['jugador']}" if ok
                      else f"Préstamo de {a['jugador']} sin efecto")
            _correo(estado, asunto, msg)
        except Exception as e:
            logger.error(f"No se pudo resolver el análisis del préstamo de {a.get('jugador')}: {e}", exc_info=True)
    _resolver_contras(estado, azar)      # contraofertas de préstamo (Ceder)


# --- Ceder: lista de préstamo y ofertas de la IA ──────────────────────────────

def _lista(estado: dict) -> list:
    return _dc(estado).setdefault('lista_prestamo', [])


def en_lista(estado: dict, j) -> bool:
    return _nombre(j) in _lista(estado)


def alternar_lista(estado: dict, j) -> bool:
    """Agrega/quita de la lista de préstamo. Uno que ya está a préstamo no se puede listar."""
    if getattr(j, 'prestamo', None):
        return False
    if en_lista(estado, j):
        _lista(estado).remove(_nombre(j))
        return False
    _lista(estado).append(_nombre(j))
    return True


def generar_ofertas(estado: dict, azar) -> list:
    """Con el mercado abierto, cada jugador en lista sin oferta de préstamo pendiente recibe una (30%)."""
    if not _abierto(estado):
        return []
    mi = _mi(estado)
    pendientes = estado.setdefault('ofertas_recibidas', [])
    clubes = [eq for eq in _equipos(estado) if eq is not mi and getattr(eq, 'nombre', None) != mi.nombre
              and not _es_internacional(eq)]
    nuevas = []
    for j in list(getattr(mi, 'jugadores', []) or []):
        if not en_lista(estado, j) or any(o.get('jugador') is j and o.get('prestamo') for o in pendientes):
            continue
        if azar.random() >= PROB_OFERTA_PRESTAMO or not clubes:
            continue
        comp = azar.choice(clubes)
        of = {'jugador': j, 'comprador': comp, 'monto': 0,
              'prestamo': {'meses': azar.choice(DURACIONES), 'pct_ellos': azar.randint(4, 10) * PCT_PASO}}
        pendientes.append(of)
        nuevas.append(of)
        _correo(estado, f"Oferta de préstamo por {_nombre(j)}",
                f"{comp.nombre} lo quiere a préstamo por {of['prestamo']['meses']} meses y paga el "
                f"{of['prestamo']['pct_ellos']}% del sueldo.", 'ofertas_screen')
    return nuevas


def aceptar_oferta(estado: dict, of: dict) -> str:
    """Acepta una oferta de préstamo de la IA: se borran las ofertas por ese jugador y arranca la cesión."""
    j, comp = of['jugador'], of['comprador']
    estado['ofertas_recibidas'] = [o for o in estado.get('ofertas_recibidas') or [] if o.get('jugador') is not j]
    return iniciar(estado, j, _mi(estado), comp, of['prestamo']['meses'], 100 - int(of['prestamo']['pct_ellos']))


def contraofertar(estado: dict, of: dict, pct_pedido: int) -> tuple:
    """Pedir que paguen más %: dentro del tope acepta, hasta +15 puntos lo analiza, más se retira."""
    pct_pedido = int(pct_pedido)
    base = int(of['prestamo']['pct_ellos'])
    comp = getattr(of.get('comprador'), 'nombre', 'El club')
    if of.get('contra'):
        return 'invalida', "Ya contraofertaste por esta oferta."
    if pct_pedido <= base or pct_pedido > 100:
        return 'invalida', f"Pide más del {base}% (hasta 100%)."
    # tope oculto: lo que el club está dispuesto a pagar (se fija la primera vez)
    tope = int(of.setdefault('tope_pct', min(100, base + random.randint(0, 2) * PCT_PASO)))
    if pct_pedido <= tope:
        of['prestamo']['pct_ellos'] = pct_pedido
        return 'aceptada', f"{comp} acepta pagar el {pct_pedido}%. " + aceptar_oferta(estado, of)
    if pct_pedido <= tope + MARGEN_ANALISIS_CONTRA:
        _t, jor, _n = _momento(estado)
        of['contra'] = {'pedido': pct_pedido, 'estado': 'analizando', 'jornada': jor}
        return 'analizando', f"{comp}: \"Lo analizamos\". Te responden por correo en la próxima jornada."
    estado['ofertas_recibidas'] = [o for o in estado.get('ofertas_recibidas') or [] if o is not of]
    return 'rechazada', f"{comp} considera excesivo el {pct_pedido}% y retira la oferta."


def _resolver_contras(estado: dict, azar) -> None:
    """Respuesta (50/50) a las contraofertas de préstamo en análisis de jornadas anteriores."""
    _t, jor, _n = _momento(estado)
    for of in list(estado.get('ofertas_recibidas') or []):
        c = of.get('contra') or {}
        if not of.get('prestamo') or c.get('estado') != 'analizando' or jor <= int(c.get('jornada', 0)):
            continue
        try:
            comp = getattr(of.get('comprador'), 'nombre', 'El club')
            if azar.random() < PROB_ACEPTA_ANALISIS and of['jugador'] in getattr(_mi(estado), 'jugadores', []):
                of['prestamo']['pct_ellos'] = int(c['pedido'])
                _correo(estado, f"{comp} acepta tu contraoferta de préstamo", aceptar_oferta(estado, of))
            else:
                estado['ofertas_recibidas'] = [o for o in estado.get('ofertas_recibidas') or [] if o is not of]
                _correo(estado, f"{comp} se retira", f"No pagará el {c['pedido']}% por {_nombre(of['jugador'])}.")
        except Exception as e:
            logger.error(f"No se pudo resolver la contraoferta de préstamo: {e}", exc_info=True)
