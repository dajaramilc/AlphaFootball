# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Directiva (v2.8.0)
Objetivo de la temporada según el nivel de la plantilla, confianza de la directiva
(sube y baja con los resultados), premio o multa al cierre y despido si no se cumple.
Al despedido le ofrecen 3 clubes de menor nivel de las 10 ligas.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

TIPOS = ['campeon', 'copa', 'mitad', 'salvarse', 'ascenso']
CONFIANZA_INICIAL = 70         # el primer objetivo fallado es una advertencia; reincidir = despido
CONFIANZA_TRAS_AVISO = 40
PREMIO = {'superado': 0.30, 'cumplido': 0.15, 'fallado': -0.20}
# v3.1.0: calificación de DT (0-100, sigue al DT entre clubes) y pedidos de la directiva.
CALIF_INICIAL = 50
CALIF = {'superado': 8, 'cumplido': 4, 'fallado': -8, 'liga': 10, 'copa': 12, 'descenso': -12,
         'despido': -10, 'pedido_ok': 3, 'pedido_mal': -4, 'clasico_perdido': -2}
PUESTOS_CATASTROFE = 4
PUNTOS_PEDIDO = 8
JORNADAS_PEDIDO = 5


MARGEN_OBJETIVO = 0            # v4.6.0: la meta es el ranking por media (antes +1: ~70-85% de cumplimiento)
VENTAJA_PARA_TITULO = 5        # v4.6.0: se exige el título con 5+ de media sobre el 2º (antes 8)
TOPE_SALARIAL_PCT = 0.70       # v4.6.0: la masa salarial no puede pasar el 70% de los ingresos esperados
SALDO_MIN_PCT = 0.10           # v4.6.0: cerrar con al menos el 10% del presupuesto inicial
MARGEN_MASA_INICIAL = 1.10     # v4.6.0: el tope nunca queda bajo la masa heredada + 10% (no castiga la plantilla que ya tenías)
PUESTO_EXTRA_USER = 2          # v0.4.11.0: en 1ª al user se le piden dos puestos más que su ranking por media
PUESTO_EXTRA_USER_2A = 1       # v0.4.11.0: en 2ª, uno (ya es la más dura: 50-57% con el criterio de la IA)
MITAD_EXTRA_USER = 1           # v0.4.11.0: "terminar entre los N primeros" llega un puesto más abajo de la mitad
VENTAJA_TITULO_USER = 3        # v0.4.11.0: y el título con 3+ de media sobre el 2º
EXIGENTE_SOLO_MITAD_ALTA = False   # v0.4.11.0: ver tests/calibrar_objetivos.py (meta: caída de 10 a 15 puntos)
# Medido en 60 temporadas simuladas por liga (cumplimiento IA → user): Premier 68.3 → 56.2% y BetPlay
# 65.7 → 53.8% en 1ª (caída 12.1 y 11.9); en 2ª, Premier 50.3 → 44.0% y BetPlay 57.4 → 49.7%.
# Con un solo puesto extra en 1ª la caída era de 4 puntos; con tres, 16.4 y 13.7.


def objetivo_por_ranking(r: int, n: int, division: int, cupo: int, ventaja: float = 0.0,
                         exigente: bool = False) -> tuple:
    """
    (tipo, puesto máximo que cumple, texto) según el ranking r de n por media de plantilla.
    Medido en 1000 temporadas: exigir exactamente el ranking era cumplir 23-61%; con +1
    puesto de margen (y el título solo para dominadores) queda en ~70-85%.
    """
    meta = min(n, r + MARGEN_OBJETIVO)
    ventaja_titulo = VENTAJA_PARA_TITULO
    mitad = n // 2
    if exigente:                       # v0.4.11.0: solo el user como DT (la IA sigue como antes)
        ventaja_titulo = VENTAJA_TITULO_USER
        mitad += MITAD_EXTRA_USER
        if not EXIGENTE_SOLO_MITAD_ALTA or r <= n // 2:
            meta = max(1, meta - (PUESTO_EXTRA_USER_2A if division == 2 else PUESTO_EXTRA_USER))
    if division == 2:
        if meta <= 2:
            return 'ascenso', 2, "Ascender a 1ª división (top 2)"
        return 'mitad', meta, f"Terminar entre los {meta} primeros"
    if r == 1 and ventaja >= ventaja_titulo:
        return 'campeon', 1, "Ser campeón de liga"
    if meta <= cupo:
        return 'copa', cupo, f"Clasificar a la copa internacional (top {cupo})"
    if meta <= mitad:
        return 'mitad', meta, f"Terminar entre los {meta} primeros"
    if meta <= n - 2:
        return 'salvarse', max(1, n - 2), "No descender"
    return 'salvarse', max(1, n - 1), "No terminar último"


def _dc(estado) -> dict:
    return estado.setdefault('datos_carrera', {})


def completar_financieros(estado: dict, obj: dict) -> dict:
    """v4.6.0: tope de masa salarial y saldo mínimo del objetivo (también para objetivos de saves viejos)."""
    if not isinstance(obj, dict):
        return obj
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if 'tope_salarial' not in obj and liga is not None and mi is not None:
        from alpha_football.finanzas import ingresos_esperados, masa_salarial
        obj['tope_salarial'] = int(max(TOPE_SALARIAL_PCT * ingresos_esperados(
            mi, getattr(liga, 'tipo', ''), getattr(liga, 'division', 1) or 1),
            MARGEN_MASA_INICIAL * masa_salarial(mi, estado)))
    if 'saldo_minimo' not in obj:
        obj['saldo_minimo'] = int(SALDO_MIN_PCT * max(0, int(obj.get('presupuesto_ref', 0) or 0)))
    return obj


def avisar_tope_salarial(estado: dict) -> None:
    """v4.6.0: correo (una vez por mitad de temporada) si la masa salarial pasa el tope."""
    try:
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        obj = definir_objetivo(estado)
        if not obj or liga is None or mi is None:
            return
        from alpha_football.finanzas import masa_salarial
        masa, tope = masa_salarial(mi, estado), int(obj.get('tope_salarial', 0) or 0)
        if not tope or masa <= tope:
            return
        mitad = 1 if int(getattr(liga, 'jornada_actual', 1) or 1) <= int(getattr(liga, 'num_jornadas', 22) or 22) // 2 else 2
        avisos = obj.setdefault('avisos_tope', [])
        if mitad in avisos:
            return
        avisos.append(mitad)
        from alpha_football import correo as C
        C.enviar(estado, 'directiva', "Te pasaste del tope salarial",
                 f"Le advertimos que la masa salarial asciende a ${masa / 1_000_000:.1f}M y supera el tope "
                 f"de ${tope / 1_000_000:.1f}M fijado para esta temporada. Si la temporada cierra en estas "
                 "condiciones, el objetivo financiero se considerará incumplido.",
                 C.accion('objetivos_screen', "VER OBJETIVOS"))
    except Exception as e:
        logger.error(f"Error al revisar el tope salarial: {e}")


def _correo_objetivos(estado: dict, obj: dict) -> None:
    """v4.7.0: la directiva comunica los objetivos de la temporada (deportivo y financieros)."""
    try:
        from alpha_football import correo as C
        ref = int(obj.get('presupuesto_ref', 0) or 0)
        m = lambda v: f"${v / 1_000_000:.1f}M"
        om, oj = definir_objetivo_marca(estado), definir_objetivo_juveniles(estado)   # v4.7.0
        extra = (f"Marca: {om['texto']}.\n" if om else "") + (f"Juveniles: {oj['texto']}.\n" if oj else "")
        C.enviar(estado, 'directiva', f"Objetivos de la temporada {obj.get('temporada', estado.get('temporada', 1))}",
                 "Le comunicamos los objetivos que la directiva fija para esta temporada.\n\n"
                 f"Objetivo deportivo: {obj.get('texto', '')}. Ranking de la plantilla por media: "
                 f"{obj.get('ranking_inicial', '?')}º.\n"
                 f"Tope de masa salarial: {m(int(obj.get('tope_salarial', 0) or 0))}.\n"
                 f"Saldo mínimo al cierre: {m(int(obj.get('saldo_minimo', 0) or 0))}.\n"
                 f"{extra}\n"
                 f"Si supera el objetivo deportivo recibirá un premio de {m(ref * PREMIO['superado'])}; si lo "
                 f"cumple, {m(ref * PREMIO['cumplido'])}. Fallar cualquiera de los objetivos supone una "
                 "advertencia, y reincidir, la rescisión de su contrato.\n\n"
                 "El saldo no pasa de una temporada a otra: superar el objetivo sube el presupuesto de la "
                 "próxima un 25%; cumplirlo, un 10%; fallarlo lo baja un 15%.",
                 C.accion('objetivos_screen', "VER OBJETIVOS"))
    except Exception as e:
        logger.error(f"No se pudo enviar el correo de objetivos: {e}")


def definir_objetivo(estado: dict) -> Optional[dict]:
    """El objetivo de la temporada actual (se fija una sola vez por temporada)."""
    try:
        dc = _dc(estado)
        temporada = int(estado.get('temporada', 1) or 1)
        obj = dc.get('objetivo')
        if isinstance(obj, dict) and obj.get('temporada') == temporada:
            return completar_financieros(estado, obj)
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if liga is None or mi is None:
            return None
        ranking = sorted(liga.equipos, key=lambda e: -getattr(e, 'ovr_promedio', 0))
        r = next((i + 1 for i, e in enumerate(ranking) if e is mi or e.id == mi.id), len(ranking))
        division = getattr(liga, 'division', 1) or 1
        try:
            from alpha_football.ui.copa_screen import cupos_copa
            cupo = cupos_copa(getattr(liga, 'tipo', ''))
        except Exception:
            cupo = 3
        ventaja = (ranking[0].ovr_promedio - ranking[1].ovr_promedio) if len(ranking) > 1 else 0
        tipo, pos_max, texto = objetivo_por_ranking(r, len(ranking), division, cupo, ventaja, exigente=True)
        obj = dc['objetivo'] = {'temporada': temporada, 'tipo': tipo, 'pos_max': pos_max, 'texto': texto,
                                'ranking_inicial': r, 'presupuesto_ref': int(getattr(mi, 'balance', 0) or 0)}
        dc.setdefault('confianza', CONFIANZA_INICIAL)
        completar_financieros(estado, obj)
        _correo_objetivos(estado, obj)          # v4.7.0: lo primero que ves de la temporada
        return obj
    except Exception as e:
        logger.error(f"Error al definir el objetivo: {e}")
        return None


def confianza(estado: dict) -> int:
    return int(_dc(estado).get('confianza', CONFIANZA_INICIAL))


def texto_confianza(c: int) -> str:
    return ("Total" if c >= 85 else "Alta" if c >= 70 else "Media" if c >= 45
            else "Baja" if c >= 25 else "Crítica")


def actualizar_confianza(estado: dict, gf: int, gc: int) -> None:
    """+3 por victoria, −3 por derrota (0..100)."""
    delta = 3 if gf > gc else (-3 if gf < gc else 0)
    dc = _dc(estado)
    dc['confianza'] = max(0, min(100, confianza(estado) + delta))
    if dc['confianza'] < 40 and not dc.get('aviso_confianza'):   # v3.1.0: aviso por correo
        dc['aviso_confianza'] = True
        from alpha_football import correo as C
        C.enviar(estado, 'presidente', "Estoy preocupado",
                 f"Míster, le soy sincero: la confianza de la directiva en usted cayó a {dc['confianza']}. "
                 "Yo lo sigo defendiendo, pero necesito resultados para seguir haciéndolo.",
                 C.accion('objetivos_screen', "VER OBJETIVOS"))   # v0.4.10.0
    elif dc['confianza'] >= 40:
        dc['aviso_confianza'] = False


def calif_dt(estado: dict) -> int:
    return int(_dc(estado).get('calif_dt', CALIF_INICIAL))


def ajustar_calif(estado: dict, delta: int) -> int:
    _dc(estado)['calif_dt'] = max(0, min(100, calif_dt(estado) + int(delta)))
    return calif_dt(estado)


def _desciende(estado: dict, posicion: int) -> bool:
    liga = estado.get('liga')
    return getattr(liga, 'division', 1) == 1 and posicion >= len(getattr(liga, 'equipos', []) or []) - 1


def es_catastrofico(estado: dict, posicion: int, pos_max: int) -> bool:
    """Descender o quedar 4+ puestos por debajo de la meta: despido sin segunda oportunidad."""
    return _desciende(estado, posicion) or posicion - pos_max >= PUESTOS_CATASTROFE


def evaluar_temporada(estado: dict, posicion: int) -> dict:
    """
    Cierre de temporada: compara el puesto final con el objetivo, aplica premio o multa
    sobre el presupuesto con que empezó la temporada y decide el despido.
    """
    dc = _dc(estado)
    # El objetivo guardado es el de la temporada que termina (al cerrar, estado['temporada']
    # ya puede apuntar a la siguiente).
    obj = dc.get('objetivo') or definir_objetivo(estado) or {}
    mi = estado.get('mi_equipo')
    pos_max = int(obj.get('pos_max', 99))
    resultado = 'superado' if posicion < pos_max else 'cumplido' if posicion <= pos_max else 'fallado'
    # abs(): con un presupuesto de referencia negativo el premio seguía siendo multa (y al revés)
    monto = int(abs(int(obj.get('presupuesto_ref', 0) or 0)) * PREMIO[resultado])
    if mi is not None:
        mi.balance = int(getattr(mi, 'balance', 0) or 0) + monto
    deuda = int((obj.get('espaldarazo') or {}).get('deuda', 0) or 0)
    if deuda and mi is not None:   # v4.6.0: el espaldarazo se devuelve de las ganancias (puede dejarte en rojo)
        mi.balance = int(mi.balance) - deuda
        try:
            from alpha_football.finanzas import registrar
            registrar(estado, 'directiva', -deuda, int(obj.get('temporada') or estado.get('temporada', 1) or 1))
        except Exception as e:
            logger.error(f"No se pudo registrar la deuda del espaldarazo: {e}")
    completar_financieros(estado, obj)
    fallos_fin = []
    if mi is not None:     # v4.6.0: objetivos financieros (tope salarial y saldo mínimo al cierre)
        from alpha_football.finanzas import masa_salarial
        masa, tope = masa_salarial(mi, estado), int(obj.get('tope_salarial', 0) or 0)
        if tope and masa > tope:
            fallos_fin.append(f"masa salarial ${masa / 1_000_000:.1f}M sobre el tope de ${tope / 1_000_000:.1f}M")
        minimo = int(obj.get('saldo_minimo', 0) or 0)
        if int(mi.balance) < minimo:
            fallos_fin.append(f"saldo ${mi.balance / 1_000_000:.1f}M bajo el mínimo de ${minimo / 1_000_000:.1f}M")
    fallo = resultado == 'fallado' or bool(fallos_fin)
    from alpha_football import correo as C
    despido = False
    ajustar_calif(estado, CALIF[resultado])
    if fallos_fin and resultado != 'fallado':
        ajustar_calif(estado, CALIF['fallado'])
    if posicion == 1:
        ajustar_calif(estado, CALIF['liga'])
    if estado.get('copa_mejor_fase_temp') == 'Campeón':
        ajustar_calif(estado, CALIF['copa'])
    if _desciende(estado, posicion):
        ajustar_calif(estado, CALIF['descenso'])
    temporada_fin = int(obj.get('temporada') or estado.get('temporada', 1) or 1)
    if fallo:
        # v3.1.0: segunda oportunidad salvo reincidencia o catástrofe
        if es_catastrofico(estado, posicion, pos_max) or dc.get('advertencia_dt'):
            despido = True
            ajustar_calif(estado, CALIF['despido'])
        else:
            # v3.2.0: la advertencia ya no va en un correo aparte: va en el de rendimiento
            dc['advertencia_dt'] = True
            dc['confianza'] = CONFIANZA_TRAS_AVISO
    else:
        dc['advertencia_dt'] = False
        dc['confianza'] = min(100, confianza(estado) + (15 if resultado == 'superado' else 8))
    copa_ev = evaluar_objetivo_copa(estado, temporada_fin)       # v3.2.0
    marca_ev = evaluar_objetivo_secundario(estado, 'objetivo_marca', temporada_fin)          # v4.7.0
    juveniles_ev = evaluar_objetivo_secundario(estado, 'objetivo_juveniles', temporada_fin)
    from alpha_football import carrera_dt as CD
    indem = 0
    if despido:
        veredicto = 'despido'
        indem = marcar_despido(estado, f"No cumpliste: {obj.get('texto', 'el objetivo')} (terminaste {posicion}º)."
                               + (f" Finanzas: {'; '.join(fallos_fin)}." if fallos_fin else ""),
                               temporada_fin=temporada_fin)
    elif CD.contrato_vencido(estado, temporada_fin):
        veredicto = 'fin_contrato'
        ren = dc.get('renovacion_dt') or {}
        # tenías una oferta de renovación sin responder: todavía puedes aceptarla en la pantalla de fin de contrato
        renovable = ren.get('estado') == 'ofrecida' and int(ren.get('temporada', -1)) == temporada_fin
        marcar_despido(estado, "Terminó tu contrato." + (" Tu club mantiene su oferta de renovación."
                                                           if renovable else " No hubo renovación."),
                       temporada_fin=temporada_fin, indemnizar=False, titulo="FIN DE CONTRATO",
                       renovable=renovable)
    elif fallo:
        veredicto = 'regano'
    elif resultado == 'superado' or posicion == 1 or estado.get('copa_mejor_fase_temp') == 'Campeón':
        veredicto = 'felicitacion'
    else:
        veredicto = 'neutro'
    info = {'temporada': obj.get('temporada'), 'texto': obj.get('texto', ''), 'posicion': posicion,
            'resultado': resultado, 'monto': monto, 'despido': despido, 'veredicto': veredicto,
            'copa': copa_ev, 'marca': marca_ev, 'juveniles': juveniles_ev, 'calif': calif_dt(estado), 'confianza': confianza(estado), 'indemnizacion': indem,
            'fallos_financieros': fallos_fin, 'deuda': deuda}
    dc['directiva_ultimo'] = info
    # v3.2.0: correo de rendimiento + veredicto pendiente (pantalla veredicto_screen)
    msg = C.enviar(estado, 'directiva', f"Evaluación de la temporada {temporada_fin}", texto_evaluacion(info),
                   C.accion('objetivos_screen', "VER OBJETIVOS"))
    estado['veredicto_pendiente'] = {'correo_id': msg['id'], 'tipo': veredicto, 'info': info}
    return info


def marcar_despido(estado: dict, motivo: str, temporada_fin: Optional[int] = None,
                   indemnizar: bool = True, titulo: str = "¡DESPEDIDO!", renovable: bool = False) -> int:
    """
    v2.9.1: deja el despido pendiente en memoria y en datos_carrera (se guarda con la
    partida). v3.2.0: paga la indemnización al patrimonio y guarda el título de la pantalla
    ("FIN DE CONTRATO" cuando no renuevan). Retorna la indemnización cobrada.
    """
    monto = 0
    if indemnizar and not estado.get('despido_pendiente'):   # v4.6.0: un solo cobro por despido
        try:
            from alpha_football import carrera_dt as CD
            monto = CD.cobrar_indemnizacion(estado, temporada_fin or int(estado.get('temporada', 1) or 1))
        except Exception as e:
            logger.error(f"Error al cobrar la indemnización: {e}")
    pend = estado.get('despido_pendiente')
    if pend:
        pend['motivo'] = (pend.get('motivo', '') + " " + motivo).strip()
        if titulo == "¡DESPEDIDO!" and not renovable:   # v4.6.0: un despido por causa manda sobre el fin de contrato
            pend['titulo'] = titulo
            pend.pop('renovable', None)
    else:
        pend = estado['despido_pendiente'] = {'motivo': motivo, 'opciones': opciones_de_club(estado),
                                              'titulo': titulo}
    if renovable:
        pend['renovable'] = True         # despido_screen ofrece RENOVAR CON TU CLUB
    _dc(estado)['despido_pendiente'] = {'motivo': pend['motivo'], 'titulo': pend.get('titulo', titulo),
                                        'opciones_ids': [o.id for o in pend['opciones']],
                                        'renovable': bool(pend.get('renovable'))}
    return monto


def restaurar_despido(estado: dict) -> bool:
    """True si hay un despido pendiente (lo reconstruye desde datos_carrera si hace falta)."""
    if estado.get('despido_pendiente'):
        return True
    guardado = _dc(estado).get('despido_pendiente')
    if not guardado:
        return False
    equipos = {}
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            for eq in getattr(liga, 'equipos', []) or []:
                equipos.setdefault(eq.id, eq)
    opciones = [equipos[i] for i in guardado.get('opciones_ids', []) if i in equipos] or opciones_de_club(estado)
    estado['despido_pendiente'] = {'motivo': guardado.get('motivo', ''), 'opciones': opciones,
                                   'titulo': guardado.get('titulo', "¡DESPEDIDO!"),
                                   'renovable': bool(guardado.get('renovable'))}
    return True


def opciones_de_club(estado: dict, n: int = 3) -> list:
    """n clubes de menor nivel que el actual, de las 10 ligas (uno de tu país si hay)."""
    mi = estado.get('mi_equipo')
    if mi is None:
        return []
    ovr = getattr(mi, 'ovr_promedio', 70)
    todos = []
    for clave in ('primera_division', 'segunda_division'):
        for tipo, liga in (estado.get(clave) or {}).items():
            for eq in getattr(liga, 'equipos', []) or []:
                if eq is not mi and eq.id != mi.id:
                    todos.append((eq, tipo))
    azar = random.Random(f"{getattr(mi, 'nombre', '')}-{estado.get('temporada', 1)}")
    c = calif_dt(estado)     # v3.1.0: la calificación define el nivel de los clubes que llaman
    if c >= 70:
        bandas = [(ovr - 6, ovr + 3), (ovr - 12, ovr + 3), (-999, ovr + 3)]
    elif c >= 40:
        bandas = [(ovr - 12, ovr - 2), (ovr - 20, ovr - 2), (-999, ovr - 2)]
    else:
        bandas = [(ovr - 25, ovr - 8), (ovr - 35, ovr - 8), (-999, ovr - 2)]
    for lo, hi in bandas:
        banda = [(eq, t) for eq, t in todos if lo <= eq.ovr_promedio < hi]
        if len(banda) >= n:
            break
    if len(banda) < n:
        banda = sorted([(eq, t) for eq, t in todos if eq.ovr_promedio < ovr], key=lambda x: -x[0].ovr_promedio)
    if not banda:   # v3.2.0: siempre hay al menos una oferta, aunque sea de los clubes más flojos
        banda = sorted(todos, key=lambda x: x[0].ovr_promedio)[:n]
    tipo_user = getattr(estado.get('liga'), 'tipo', '')
    propios = [x for x in banda if x[1] == tipo_user]
    elegidos = [azar.choice(propios)] if propios else []
    resto = [x for x in banda if x not in elegidos]
    azar.shuffle(resto)
    elegidos += resto[:n - len(elegidos)]
    return [eq for eq, _t in sorted(elegidos, key=lambda x: -x[0].ovr_promedio)][:n]


def cambiar_de_club(estado: dict, nuevo) -> None:
    """El DT despedido toma `nuevo`: liga, equipo, once, copa y objetivo nuevos."""
    from alpha_football.models import alineacion_por_defecto
    liga_nueva = None
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            if liga is not None and any(e is nuevo for e in liga.equipos):
                liga_nueva = liga
    if liga_nueva is None:
        logger.error(f"cambiar_de_club: {getattr(nuevo, 'nombre', '?')} no está en ninguna liga")
        return
    viejo = estado.get('mi_equipo')
    if viejo is not None and viejo is not nuevo:
        viejo.alineacion_activa = None      # v2.9.1: la IA vuelve a su mejor 4-3-3
    estado['liga'] = liga_nueva
    estado['mi_equipo'] = nuevo
    estado['equipos'] = liga_nueva.equipos
    estado['liga_usuario_division'] = getattr(liga_nueva, 'division', 1)
    if viejo is not None and viejo is not nuevo:
        try:  # v4.4.0: el club viejo (ya de la IA) suelta a los que pedían salir; la IA vende a los forzados
            from alpha_football.salidas import al_cambiar_de_club
            al_cambiar_de_club(estado, viejo)
        except Exception as e_sal:
            logger.error(f"cambiar_de_club: no se pudieron resolver las salidas del club viejo: {e_sal}")
    nuevo.alineacion_activa = alineacion_por_defecto(nuevo)
    estado['alineacion_activa'] = nuevo.alineacion_activa
    # v3.8.0: la copa sale del motor: si el club nuevo está en una copa de esta temporada, la
    # sigue jugando el user desde su próxima fecha (lo ya jugado lo simuló la IA).
    estado['copa_clasificado_motivo'] = "Nuevo club: sin copa esta temporada."
    try:
        from alpha_football.ui.copa_screen import actualizar_claves
        actualizar_claves(estado)
    except Exception as e_cp:
        logger.error(f"cambiar_de_club: no se pudo actualizar la copa: {e_cp}")
        estado['copa_clasificado'] = estado['copa_user_en_copa'] = False
    for k in ('despido_pendiente', 'ofertas_recibidas', 'plantilla_sel', 'busq', 'busq_resultados',
              '_hub_copa_sync', 'aviso_finanzas'):
        estado.pop(k, None)
    dc = _dc(estado)
    dc.pop('objetivo', None)
    dc.pop('objetivo_marca', None)       # v4.7.0: se vuelven a fijar para el club nuevo
    dc.pop('objetivo_juveniles', None)
    dc['advertencia_dt'] = False
    dc.pop('pedido', None)
    dc.pop('racha', None)
    dc.pop('despido_pendiente', None)
    dc.pop('renovacion_dt', None)          # v3.2.0
    dc.pop('objetivo_copa', None)
    dc['jornadas_en_rojo'] = 0
    dc['temporadas_en_rojo'] = 0          # v4.6.0: la quiebra era del club viejo
    dc.pop('oferta_dt', None)             # v4.6.0: la oferta era para el DT del club viejo
    dc['confianza'] = CONFIANZA_INICIAL
    dc.setdefault('clubes_dirigidos', []).append(
        {'temporada': estado.get('temporada', 1), 'de': getattr(viejo, 'nombre', '?'), 'a': nuevo.nombre})
    try:  # v3.4.0: DTs de la IA (tu club viejo contrata, el DT del nuevo queda libre)
        from alpha_football.entrenadores import al_cambiar_club
        al_cambiar_club(estado, viejo, nuevo)
    except Exception as e_dt:
        logger.error(f"cambiar_de_club: error con los DTs: {e_dt}")
    estado['hub_tab'] = 'inicio'
    logger.info(f"Cambio de club: {getattr(viejo, 'nombre', '?')} → {nuevo.nombre} ({liga_nueva.nombre})")


# --- v3.1.0: pedidos de la directiva (uno por mitad de temporada) ---

def pedido_activo(estado: dict) -> Optional[dict]:
    p = _dc(estado).get('pedido')
    return p if isinstance(p, dict) and not p.get('resuelto') else None


def _jugadas(liga, mi) -> int:
    return sum(1 for p in getattr(liga, 'calendario', []) or []
               if p.jugado and mi.id in (p.local_id, p.visitante_id))


def resolver_pedido(estado: dict, cumplido: bool) -> None:
    p = pedido_activo(estado)
    if not p:
        return
    from alpha_football import correo as C
    p['resuelto'], p['cumplido'] = True, bool(cumplido)
    try:  # v4.4.0: historial de pedidos de la temporada (nivel_temporada: "ningún objetivo")
        hist = _dc(estado).setdefault('pedidos_temporada', [])
        hist.append({'temporada': int(p.get('temporada', 0) or 0), 'cumplido': bool(cumplido)})
        del hist[:-10]
    except Exception as e_ph:
        logger.error(f"No se pudo registrar el pedido de la temporada: {e_ph}")
    ajustar_calif(estado, CALIF['pedido_ok'] if cumplido else CALIF['pedido_mal'])
    dc = _dc(estado)
    dc['confianza'] = max(0, min(100, confianza(estado) + (5 if cumplido else -5)))
    C.enviar(estado, 'directiva', ("Pedido cumplido: " if cumplido else "Pedido fallado: ") + p['texto'],
             "La directiva toma nota. " + ("Le felicitamos por haber cumplido lo solicitado." if cumplido
                                           else "Lamentamos que no se haya cumplido; esto afecta a su calificación."),
             C.accion('objetivos_screen', "VER OBJETIVOS"))


def _crear_pedido(estado: dict, jugadas: int, azar: random.Random) -> None:
    liga, mi = estado['liga'], estado['mi_equipo']
    mitad = liga.num_jornadas // 2
    fin_mitad = mitad if jugadas < mitad else liga.num_jornadas
    opciones = []
    riv = next((e for e in liga.equipos if e.nombre == getattr(mi, 'rival', '')), None)
    if riv is not None and any(not p.jugado and p.jornada <= fin_mitad and {p.local_id, p.visitante_id} == {mi.id, riv.id}
                               for p in liga.calendario):
        opciones.append(('clasico', f"Ganar el clásico contra {riv.nombre}", fin_mitad))
    if liga.num_jornadas - jugadas >= JORNADAS_PEDIDO:
        opciones.append(('puntos', f"Sumar {PUNTOS_PEDIDO} puntos en las próximas {JORNADAS_PEDIDO} jornadas",
                         jugadas + JORNADAS_PEDIDO))
        if any(int(j.edad) <= 21 for j in mi.jugadores):
            opciones.append(('sub21', f"Dar 3 partidos a un sub-21 en las próximas {JORNADAS_PEDIDO} jornadas",
                             jugadas + JORNADAS_PEDIDO))
    if not opciones:
        return
    tipo, texto, hasta = azar.choice(opciones)
    temporada = int(estado.get('temporada', 1) or 1)
    _dc(estado)['pedido'] = {
        'temporada': temporada, 'tipo': tipo, 'texto': texto, 'hasta': hasta,
        'puntos_ini': int(mi.puntos), 'pj_ini': {str(j.id): int(j.partidos_jugados) for j in mi.jugadores},
        'resuelto': False, 'cumplido': False, 'creado_en': [temporada, jugadas]}
    from alpha_football import correo as C
    C.enviar(estado, 'directiva', f"Pedido de la directiva: {texto}",
             "La directiva le encarga este objetivo a corto plazo. Cumplirlo mejorará su calificación como "
             "entrenador; no hacerlo la reducirá.", C.accion('objetivos_screen', "VER OBJETIVOS"))


def revisar_pedido(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Cierre de jornada de liga: resuelve el pedido vencido y crea el de cada mitad."""
    try:
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if liga is None or mi is None:
            return
        jugadas = _jugadas(liga, mi)
        p = pedido_activo(estado)
        if p and jugadas >= int(p.get('hasta', 99)):
            if p['tipo'] == 'puntos':
                resolver_pedido(estado, mi.puntos - int(p.get('puntos_ini', 0)) >= PUNTOS_PEDIDO)
            elif p['tipo'] == 'sub21':
                ini = p.get('pj_ini') or {}
                resolver_pedido(estado, any(
                    int(j.edad) <= 21 and j.partidos_jugados - int(ini.get(str(j.id), j.partidos_jugados)) >= 3
                    for j in mi.jugadores))
            else:
                resolver_pedido(estado, False)
        actual = _dc(estado).get('pedido') or {}
        clave = [int(estado.get('temporada', 1) or 1), jugadas]
        if jugadas in (1, liga.num_jornadas // 2) and actual.get('creado_en') != clave and not pedido_activo(estado):
            _crear_pedido(estado, jugadas, rng or random.Random())
    except Exception as e:
        logger.error(f"Error al revisar el pedido de la directiva: {e}")


def cerrar_pedido_temporada(estado: dict) -> None:
    if pedido_activo(estado):
        resolver_pedido(estado, False)


# --- v3.2.0: objetivo internacional (solo si estás en la copa) ---
# v3.8.0: fases del motor de competiciones (Playoff solo en Champions; 'Fase de grupos' de la
# Libertadores equivale a 'Fase de liga').
FASES_COPA = ['Fase de liga', 'Playoff', 'Octavos', 'Cuartos', 'Semifinal', 'Finalista', 'Campeón']
TEXTO_META_COPA = {'Octavos': "Llegar a octavos de final", 'Cuartos': "Llegar a cuartos de final",
                   'Semifinal': "Llegar a semifinales", 'Finalista': "Llegar a la final",
                   'Campeón': "Ser campeón de la copa"}
CALIF_COPA = {'superado': 6, 'cumplido': 3, 'fallado': -4}


def _indice_fase_copa(fase) -> int:
    """v3.8.0: posición en FASES_COPA ('Fase de grupos' ≡ 'Fase de liga'; desconocida = 0)."""
    fase = 'Fase de liga' if fase == 'Fase de grupos' else fase
    return FASES_COPA.index(fase) if fase in FASES_COPA else 0


def meta_copa(r: int, n: int, ventaja: float = 0.0) -> str:
    """
    v3.8.0: meta de copa según el ranking r de n por media entre los clubes de la copa:
    r = 1 con 5+ de ventaja → Campeón; v4.7.0 (metas más altas): r ≤ n/6 → Finalista; r ≤ n/3 → Semifinal;
    r ≤ 2n/3 → Cuartos; si no → Octavos.
    """
    if n < 2:
        return 'Octavos'
    if r == 1 and ventaja >= VENTAJA_PARA_TITULO:
        return 'Campeón'
    if r <= n / 6:
        return 'Finalista'
    if r <= n / 3:
        return 'Semifinal'
    if r <= 2 * n / 3:
        return 'Cuartos'
    return 'Octavos'


def definir_objetivo_copa(estado: dict) -> Optional[dict]:
    """El objetivo internacional de la temporada (None si no estás en la copa)."""
    dc = _dc(estado)
    t = int(estado.get('temporada', 1) or 1)
    oc = dc.get('objetivo_copa')
    if isinstance(oc, dict) and oc.get('temporada') == t:
        return oc if oc.get('fase') else None
    mi = estado.get('mi_equipo')
    try:  # v3.8.0: los clubes y medias salen del motor de competiciones
        from alpha_football import competiciones as CP
        tipo = CP.tipo_copa_user(estado)
        clubes = list((CP.copa(estado, tipo) or {}).get('clubes', [])) if tipo else []
    except Exception as e_cp:
        logger.error(f"definir_objetivo_copa: no se pudo leer la copa: {e_cp}")
        tipo, clubes = None, []
    if not tipo or mi is None or not clubes:
        dc['objetivo_copa'] = {'temporada': t, 'fase': None}
        return None
    medias = {c['nombre']: float(c.get('ovr', 0) or 0) for c in clubes}
    medias[mi.nombre] = float(getattr(mi, 'ovr_promedio', medias.get(mi.nombre, 0)) or 0)
    ranking = sorted(medias, key=lambda n: -medias[n])
    r = ranking.index(mi.nombre) + 1
    ventaja = (medias[ranking[0]] - medias[ranking[1]]) if len(ranking) > 1 else 0
    fase = meta_copa(r, len(ranking), ventaja)
    oc = dc['objetivo_copa'] = {'temporada': t, 'fase': fase, 'texto': TEXTO_META_COPA[fase],
                                'ranking': r, 'n': len(ranking), 'tipo': tipo}
    return oc


def evaluar_objetivo_copa(estado: dict, temporada_fin: int) -> Optional[dict]:
    """Al cierre: superado +6 / cumplido +3 / fallado −4 de calificación (sin dinero ni despido)."""
    oc = _dc(estado).get('objetivo_copa')
    if not isinstance(oc, dict) or oc.get('temporada') != temporada_fin or not oc.get('fase'):
        return None
    alcanzada = estado.get('copa_mejor_fase_temp') or 'Fase de liga'
    ia = _indice_fase_copa(alcanzada)
    im = _indice_fase_copa(oc['fase'])
    resultado = 'superado' if ia > im else 'cumplido' if ia == im else 'fallado'
    ajustar_calif(estado, CALIF_COPA[resultado])
    return {'texto': oc['texto'], 'fase': oc['fase'], 'alcanzada': alcanzada, 'resultado': resultado}


# --- v4.7.0: objetivos de Marca y Juveniles (solo calificación, como el internacional) ---
CALIF_SECUNDARIO = {'cumplido': 4, 'fallado': -3}
EDAD_ALTA = 27.5
NOMBRE_SECUNDARIO = {'objetivo_marca': 'Marca', 'objetivo_juveniles': 'Juveniles'}


def _edad_media(equipo) -> float:
    js = getattr(equipo, 'jugadores', []) or []
    return round(sum(int(getattr(j, 'edad', 25) or 25) for j in js) / len(js), 1) if js else 0.0


def _vigente(estado: dict, clave: str) -> Optional[dict]:
    oc = _dc(estado).get(clave)
    mi = estado.get('mi_equipo')
    if (isinstance(oc, dict) and oc.get('temporada') == int(estado.get('temporada', 1) or 1)
            and oc.get('club') == getattr(mi, 'nombre', None)):
        return oc
    return None


def _base_secundario(estado: dict, mi) -> dict:
    ids = [j.id for j in mi.jugadores]
    try:   # los cedidos también son del club: volver del préstamo no es un fichaje
        from alpha_football.prestamos import cedidos
        ids += [j.id for j, _club in cedidos(estado, mi.nombre)]
    except Exception as e:
        logger.error(f"No se pudieron leer los cedidos para el objetivo: {e}")
    return {'temporada': int(estado.get('temporada', 1) or 1), 'club': mi.nombre,
            'ids_inicio': ids, 'cumplido': False}


def definir_objetivo_marca(estado: dict, rng: Optional[random.Random] = None) -> Optional[dict]:
    """Una meta de marca por temporada: valor del club +10% o fichar una estrella (media +5)."""
    oc = _vigente(estado, 'objetivo_marca')
    if oc is not None:
        return oc
    mi = estado.get('mi_equipo')
    if mi is None:
        return None
    from alpha_football.finanzas import valor_club
    oc = _base_secundario(estado, mi)
    if (rng or random.Random()).random() < 0.5 and valor_club(mi) > 0:   # en rojo: la meta de valor no tiene sentido
        meta = int(valor_club(mi) * 1.10)
        oc.update(tipo='valor', meta=meta, texto=f"Llegar a ${meta / 1_000_000:.1f}M de valor del club")
    else:
        meta = round(float(getattr(mi, 'ovr_promedio', 0) or 0)) + 5
        oc.update(tipo='estrella', meta=meta, texto=f"Fichar un jugador de media {meta} o más")
    _dc(estado)['objetivo_marca'] = oc
    return oc


def definir_objetivo_juveniles(estado: dict, rng: Optional[random.Random] = None) -> Optional[dict]:
    """Edad media alta → bajarla 1 año; si no, partidos de menores de 21 o fichar un joven."""
    oc = _vigente(estado, 'objetivo_juveniles')
    if oc is not None:
        return oc
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    if mi is None:
        return None
    oc = _base_secundario(estado, mi)
    edad = _edad_media(mi)
    if edad >= EDAD_ALTA:
        meta = round(edad - 1.0, 1)
        oc.update(tipo='edad', meta=meta, edad_inicio=edad, texto=f"Bajar la edad media a {meta} años")
    elif (rng or random.Random()).random() < 0.5:
        n_u21 = sum(1 for j in mi.jugadores if int(getattr(j, 'edad', 25) or 25) < 21)
        jornadas = int(getattr(liga, 'num_jornadas', 22) or 22)
        meta = max(10, round(2 * n_u21 * jornadas / 22))
        oc.update(tipo='partidos_u21', meta=meta, texto=f"Que los menores de 21 sumen {meta} partidos")
    else:
        oc.update(tipo='fichar_joven', meta=21, texto="Fichar un jugador de 21 años o menos")
    _dc(estado)['objetivo_juveniles'] = oc
    return oc


def _nuevos(estado: dict, oc: dict) -> list:
    mi = estado.get('mi_equipo')
    ids = set(oc.get('ids_inicio') or [])
    return [j for j in getattr(mi, 'jugadores', []) or [] if j.id not in ids]


def progreso_secundario(estado: dict, oc: dict) -> float:
    """Fracción 0..1 para la barra de la pantalla."""
    mi = estado.get('mi_equipo')
    if not oc or mi is None:
        return 0.0
    if oc.get('cumplido'):
        return 1.0
    t, meta = oc.get('tipo'), oc.get('meta') or 0
    if t == 'valor':     # el aporte del espaldarazo es deuda: no sube el valor
        from alpha_football.finanzas import valor_club
        f = (valor_club(mi) - deuda_espaldarazo(estado)) / meta if meta > 0 else 0.0
    elif t == 'estrella':
        f = 1.0 if any(int(j.overall) >= int(meta) for j in _nuevos(estado, oc)) else 0.0
    elif t == 'fichar_joven':
        f = 1.0 if any(int(getattr(j, 'edad', 99)) <= int(meta) for j in _nuevos(estado, oc)) else 0.0
    elif t == 'edad':
        ini = float(oc.get('edad_inicio', meta + 1.0))
        f = (ini - _edad_media(mi)) / (ini - float(meta)) if ini > meta else 1.0
    elif t == 'partidos_u21':
        suma = sum(int(getattr(j, 'partidos_jugados', 0) or 0) for j in mi.jugadores
                   if int(getattr(j, 'edad', 25) or 25) < 21)
        f = suma / meta if meta > 0 else 1.0
    else:
        f = 0.0
    return max(0.0, min(1.0, f))


def cumplido_secundario(estado: dict, oc: dict) -> bool:
    return bool(oc and (oc.get('cumplido') or progreso_secundario(estado, oc) >= 1.0))


def revisar_objetivos_secundarios(estado: dict) -> None:
    """Tras cada jornada: si Marca o Juveniles se cumplen, quedan cumplidos y avisa una vez."""
    for clave in ('objetivo_marca', 'objetivo_juveniles'):
        try:
            oc = (definir_objetivo_marca if clave == 'objetivo_marca' else definir_objetivo_juveniles)(estado)
            if not oc or oc.get('cumplido') or not cumplido_secundario(estado, oc):
                continue
            oc['cumplido'] = True
            if _ya_avisado(estado, clave):
                continue
            from alpha_football import correo as C
            C.enviar(estado, 'directiva', f"Objetivo cumplido: {oc['texto']}",
                     f"Objetivo de {NOMBRE_SECUNDARIO[clave].lower()} cumplido. La directiva le felicita.",
                     C.accion('objetivos_screen', "VER OBJETIVOS"))
        except Exception as e:
            logger.error(f"Error al revisar el objetivo {clave}: {e}")


def evaluar_objetivo_secundario(estado: dict, clave: str, temporada_fin: int) -> Optional[dict]:
    """Al cierre: cumplido +4 / fallado −3 de calificación (sin dinero ni despido)."""
    oc = _dc(estado).get(clave)
    if not isinstance(oc, dict) or oc.get('temporada') != temporada_fin:
        return None
    # 'valor' se juzga con lo logrado en las jornadas: los premios de cierre ya entraron al saldo
    hecho = bool(oc.get('cumplido')) if oc.get('tipo') == 'valor' else cumplido_secundario(estado, oc)
    resultado = 'cumplido' if hecho else 'fallado'
    ajustar_calif(estado, CALIF_SECUNDARIO[resultado])
    return {'texto': oc.get('texto', ''), 'resultado': resultado}


# --- v4.3.0: avisos de objetivo cumplido (uno por objetivo y temporada) ---
def _ya_avisado(estado: dict, clave: str) -> bool:
    avisados = _dc(estado).setdefault('objetivos_avisados', [])
    marca_vieja = f"{clave}:{int(estado.get('temporada', 1) or 1)}"
    # el club va en la marca: si cambias de club a mitad de temporada, el objetivo del nuevo también avisa
    marca = f"{marca_vieja}:{getattr(estado.get('mi_equipo'), 'nombre', '')}"
    if marca in avisados or marca_vieja in avisados:
        return True
    avisados.append(marca)
    return False


def revisar_objetivo_copa_cumplido(estado: dict) -> bool:
    """Si la fase alcanzada en la copa ya llega a la meta, avisa por correo (una vez). True si avisó."""
    try:
        oc = _dc(estado).get('objetivo_copa')
        t = int(estado.get('temporada', 1) or 1)
        if not isinstance(oc, dict) or oc.get('temporada') != t or not oc.get('fase'):
            return False
        from alpha_football import competiciones as CP
        alcanzada = CP.fase_user(estado)
        if not alcanzada or _indice_fase_copa(alcanzada) < _indice_fase_copa(oc['fase']):
            return False
        if _ya_avisado(estado, 'copa'):
            return False
        from alpha_football import correo as C
        C.enviar(estado, 'directiva', f"Objetivo cumplido: {oc.get('texto', oc['fase'])}",
                 f"El equipo ha alcanzado {alcanzada}. La directiva está satisfecha con la campaña internacional "
                 "y le felicita por ello.",
                 C.accion('objetivos_screen', "VER OBJETIVOS"))
        return True
    except Exception as e:
        logger.error(f"Error al revisar el objetivo de copa: {e}")
        return False


def peor_posicion_posible(liga, equipo) -> int:
    """Peor puesto final posible: cuenta a los rivales que aún pueden igualar o superar tus puntos
    ganando todo lo que les queda (el empate cuenta en contra: criterio conservador)."""
    restantes = {}
    for p in getattr(liga, 'calendario', []) or []:
        if not p.jugado:
            for eid in (p.local_id, p.visitante_id):
                restantes[eid] = restantes.get(eid, 0) + 1
    mis = int(getattr(equipo, 'puntos', 0) or 0)
    return 1 + sum(1 for e in liga.equipos if e.id != equipo.id
                   and int(getattr(e, 'puntos', 0) or 0) + 3 * restantes.get(e.id, 0) >= mis)


def revisar_objetivo_liga_asegurado(estado: dict) -> bool:
    """Si la meta de liga ya no se puede perder, avisa por correo (una vez). True si avisó."""
    try:
        obj = definir_objetivo(estado)
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if not obj or liga is None or mi is None:
            return False
        if peor_posicion_posible(liga, mi) > int(obj.get('pos_max', 0) or 0):
            return False
        if _ya_avisado(estado, 'liga'):
            return False
        from alpha_football import correo as C
        C.enviar(estado, 'directiva', f"Objetivo asegurado: {obj.get('texto', '')}",
                 "Pase lo que pase en lo que queda de temporada, el objetivo de liga ya está cumplido. "
                 "Reciba nuestras felicitaciones.",
                 C.accion('objetivos_screen', "VER OBJETIVOS"))
        return True
    except Exception as e:
        logger.error(f"Error al revisar el objetivo de liga: {e}")
        return False


# --- v3.2.0: espaldarazo financiero (más presupuesto a cambio de una meta más alta) ---
ESPALDARAZO = [(0.15, 1), (0.30, 2), (0.50, 3)]
CALIF_ESPALDARAZO = 40
DEVOLUCION_ESPALDARAZO = 0.5    # v4.7.0: al cierre solo se descuenta la mitad del aporte


def _texto_meta(pos_max: int) -> str:
    return "Ser campeón de liga" if pos_max <= 1 else f"Terminar entre los {pos_max} primeros"


def deuda_espaldarazo(estado: dict) -> int:
    """v4.6.0: lo que se debe a la directiva por el espaldarazo de esta temporada (se paga al cierre)."""
    obj = (_dc(estado).get('objetivo') or {})
    return int((obj.get('espaldarazo') or {}).get('deuda', 0) or 0)


def opciones_espaldarazo(estado: dict) -> list:
    obj = definir_objetivo(estado) or {}
    ref = int(obj.get('presupuesto_ref', 0) or 0)
    pos_max = int(obj.get('pos_max', 1))
    return [{'nivel': i, 'pct': pct, 'puestos': p, 'monto': int(ref * pct), 'disponible': pos_max - p >= 1}
            for i, (pct, p) in enumerate(ESPALDARAZO)]


def pedir_espaldarazo(estado: dict, nivel: int) -> tuple:
    """(ok, mensaje). Una vez por temporada, hasta la mitad de la liga, con calif ≥ 40."""
    obj = definir_objetivo(estado)
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if not obj or liga is None or mi is None:
        return False, "No hay objetivo esta temporada."
    if obj.get('espaldarazo'):
        return False, "Ya pediste un espaldarazo esta temporada."
    if int(getattr(liga, 'jornada_actual', 1) or 1) > int(getattr(liga, 'num_jornadas', 10) or 10) // 2:
        return False, "Solo se puede pedir hasta la mitad de la temporada."
    if calif_dt(estado) < CALIF_ESPALDARAZO:
        return False, f"La directiva se niega: tu calificación ({calif_dt(estado)}) es muy baja."
    op = opciones_espaldarazo(estado)[int(nivel)]
    if not op['disponible']:
        return False, "La meta no puede subir tanto."
    mi.balance = int(getattr(mi, 'balance', 0) or 0) + op['monto']
    obj['pos_max'] = int(obj['pos_max']) - op['puestos']
    obj['espaldarazo'] = {'pct': op['pct'], 'puestos': op['puestos'], 'deuda': int(op['monto'] * DEVOLUCION_ESPALDARAZO)}   # v4.7.0: se devuelve la mitad
    obj['texto'] = _texto_meta(obj['pos_max']) + " (espaldarazo)"
    try:
        from alpha_football.finanzas import registrar
        registrar(estado, 'directiva', op['monto'])
    except Exception as e:
        logger.error(f"Error al registrar el espaldarazo: {e}")
    from alpha_football import correo as C
    C.enviar(estado, 'directiva', "Espaldarazo financiero aprobado",
             f"La directiva aprueba un aporte de ${op['monto'] / 1_000_000:.1f}M. A cambio, el objetivo pasa "
             f"a ser: {obj['texto']}. Le recordamos que la mitad de este importe "
             f"(${obj['espaldarazo']['deuda'] / 1_000_000:.1f}M) se descontará de las ganancias del club al cierre "
             "de la temporada.",
             C.accion('objetivos_screen', "VER OBJETIVOS"))
    return True, f"Aprobado: +${op['monto'] / 1_000_000:.1f}M · nueva meta: puesto {obj['pos_max']} · al cierre se devuelve la mitad."


def texto_evaluacion(info: dict) -> str:
    """Cuerpo del correo de rendimiento."""
    partes = [f"Le trasladamos la evaluación de la temporada.\n\nLiga: el equipo terminó {info['posicion']}º "
              f"(objetivo: {info.get('texto', '')}) → {info['resultado'].upper()}."]
    m = int(info.get('monto', 0) or 0)
    partes.append(f"{'Premio' if m >= 0 else 'Multa'} de la directiva: ${abs(m) / 1_000_000:.1f}M.")
    ff = info.get('fallos_financieros') or []
    partes.append("Finanzas: " + ("FALLADO (" + "; ".join(ff) + ")." if ff else "CUMPLIDO."))
    if info.get('deuda'):
        partes.append(f"Se descontó la deuda del espaldarazo: ${info['deuda'] / 1_000_000:.1f}M.")
    if info.get('copa'):
        cp = info['copa']
        partes.append(f"Copa: {cp['alcanzada']} (meta: {cp['texto']}) → {cp['resultado'].upper()}.")
    for clave, nombre in (('marca', 'Marca'), ('juveniles', 'Juveniles')):     # v4.7.0
        ev = info.get(clave)
        if ev:
            partes.append(f"{nombre}: {ev['texto']} → {ev['resultado'].upper()}.")
    partes.append(f"Calificación de DT: {info.get('calif')} · confianza: {info.get('confianza')}.")
    v = info.get('veredicto')
    partes.append({'felicitacion': "\nLe felicitamos: ha superado lo que esperábamos de esta temporada.",
                   'neutro': "\nHa cumplido con lo esperado. Seguimos adelante con el proyecto.",
                   'regano': "\nNo se han cumplido los objetivos. Le concedemos una segunda oportunidad: si "
                             "vuelve a fallar, prescindiremos de sus servicios.",
                   'despido': "\nLamentamos comunicarle que hemos decidido prescindir de sus servicios.",
                   'fin_contrato': "\nSu contrato ha finalizado y no continuará en el club."}.get(v, ""))
    if info.get('indemnizacion'):
        partes.append(f"Indemnización: ${info['indemnizacion'] / 1_000_000:.2f}M a tu patrimonio.")
    return " ".join(partes)
