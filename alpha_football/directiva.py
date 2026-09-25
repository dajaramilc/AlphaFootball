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


MARGEN_OBJETIVO = 1            # la meta es el ranking por media + 1 puesto
VENTAJA_PARA_TITULO = 8        # solo se exige el título con 8+ de media sobre el 2º


def objetivo_por_ranking(r: int, n: int, division: int, cupo: int, ventaja: float = 0.0) -> tuple:
    """
    (tipo, puesto máximo que cumple, texto) según el ranking r de n por media de plantilla.
    Medido en 1000 temporadas: exigir exactamente el ranking era cumplir 23-61%; con +1
    puesto de margen (y el título solo para dominadores) queda en ~70-85%.
    """
    meta = min(n, r + MARGEN_OBJETIVO)
    if division == 2:
        if meta <= 2:
            return 'ascenso', 2, "Ascender a 1ª división (top 2)"
        return 'mitad', meta, f"Terminar entre los {meta} primeros"
    if r == 1 and ventaja >= VENTAJA_PARA_TITULO:
        return 'campeon', 1, "Ser campeón de liga"
    if meta <= cupo:
        return 'copa', cupo, f"Clasificar a la copa internacional (top {cupo})"
    if meta <= n // 2:
        return 'mitad', meta, f"Terminar entre los {meta} primeros"
    if meta <= n - 2:
        return 'salvarse', max(1, n - 2), "No descender"
    return 'salvarse', max(1, n - 1), "No terminar último"


def _dc(estado) -> dict:
    return estado.setdefault('datos_carrera', {})


def definir_objetivo(estado: dict) -> Optional[dict]:
    """El objetivo de la temporada actual (se fija una sola vez por temporada)."""
    try:
        dc = _dc(estado)
        temporada = int(estado.get('temporada', 1) or 1)
        obj = dc.get('objetivo')
        if isinstance(obj, dict) and obj.get('temporada') == temporada:
            return obj
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
        tipo, pos_max, texto = objetivo_por_ranking(r, len(ranking), division, cupo, ventaja)
        obj = dc['objetivo'] = {'temporada': temporada, 'tipo': tipo, 'pos_max': pos_max, 'texto': texto,
                                'ranking_inicial': r, 'presupuesto_ref': int(getattr(mi, 'balance', 0) or 0)}
        dc.setdefault('confianza', CONFIANZA_INICIAL)
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
        C.enviar(estado, 'directiva', "La directiva está preocupada",
                 f"La confianza cayó a {dc['confianza']}. Necesitamos resultados ya.",
                 C.accion('objetivos_screen', "VER OBJETIVOS"))
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
    monto = int(int(obj.get('presupuesto_ref', 0) or 0) * PREMIO[resultado])
    if mi is not None:
        mi.balance = int(getattr(mi, 'balance', 0) or 0) + monto
    from alpha_football import correo as C
    despido = False
    ajustar_calif(estado, CALIF[resultado])
    if posicion == 1:
        ajustar_calif(estado, CALIF['liga'])
    if estado.get('copa_mejor_fase_temp') == 'Campeón':
        ajustar_calif(estado, CALIF['copa'])
    if _desciende(estado, posicion):
        ajustar_calif(estado, CALIF['descenso'])
    temporada_fin = int(obj.get('temporada') or estado.get('temporada', 1) or 1)
    if resultado == 'fallado':
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
    from alpha_football import carrera_dt as CD
    indem = 0
    if despido:
        veredicto = 'despido'
        indem = marcar_despido(estado, f"No cumpliste: {obj.get('texto', 'el objetivo')} (terminaste {posicion}º).",
                               temporada_fin=temporada_fin)
    elif CD.contrato_vencido(estado, temporada_fin):
        veredicto = 'fin_contrato'
        marcar_despido(estado, "Terminó tu contrato y no hubo renovación.", temporada_fin=temporada_fin,
                       indemnizar=False, titulo="FIN DE CONTRATO")
    elif resultado == 'fallado':
        veredicto = 'regano'
    elif resultado == 'superado' or posicion == 1 or estado.get('copa_mejor_fase_temp') == 'Campeón':
        veredicto = 'felicitacion'
    else:
        veredicto = 'neutro'
    info = {'temporada': obj.get('temporada'), 'texto': obj.get('texto', ''), 'posicion': posicion,
            'resultado': resultado, 'monto': monto, 'despido': despido, 'veredicto': veredicto,
            'copa': copa_ev, 'calif': calif_dt(estado), 'confianza': confianza(estado), 'indemnizacion': indem}
    dc['directiva_ultimo'] = info
    # v3.2.0: correo de rendimiento + veredicto pendiente (pantalla veredicto_screen)
    msg = C.enviar(estado, 'directiva', f"Evaluación de la temporada {temporada_fin}", texto_evaluacion(info),
                   C.accion('objetivos_screen', "VER OBJETIVOS"))
    estado['veredicto_pendiente'] = {'correo_id': msg['id'], 'tipo': veredicto, 'info': info}
    return info


def marcar_despido(estado: dict, motivo: str, temporada_fin: Optional[int] = None,
                   indemnizar: bool = True, titulo: str = "¡DESPEDIDO!") -> int:
    """
    v2.9.1: deja el despido pendiente en memoria y en datos_carrera (se guarda con la
    partida). v3.2.0: paga la indemnización al patrimonio y guarda el título de la pantalla
    ("FIN DE CONTRATO" cuando no renuevan). Retorna la indemnización cobrada.
    """
    monto = 0
    if indemnizar:
        try:
            from alpha_football import carrera_dt as CD
            monto = CD.cobrar_indemnizacion(estado, temporada_fin or int(estado.get('temporada', 1) or 1))
        except Exception as e:
            logger.error(f"Error al cobrar la indemnización: {e}")
    pend = estado.get('despido_pendiente')
    if pend:
        pend['motivo'] = (pend.get('motivo', '') + " " + motivo).strip()
    else:
        pend = estado['despido_pendiente'] = {'motivo': motivo, 'opciones': opciones_de_club(estado),
                                              'titulo': titulo}
    _dc(estado)['despido_pendiente'] = {'motivo': pend['motivo'], 'titulo': pend.get('titulo', titulo),
                                        'opciones_ids': [o.id for o in pend['opciones']]}
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
                                   'titulo': guardado.get('titulo', "¡DESPEDIDO!")}
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
    dc['advertencia_dt'] = False
    dc.pop('pedido', None)
    dc.pop('racha', None)
    dc.pop('despido_pendiente', None)
    dc.pop('renovacion_dt', None)          # v3.2.0
    dc.pop('objetivo_copa', None)
    dc['jornadas_en_rojo'] = 0
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
             "La directiva toma nota." + (" Bien hecho." if cumplido else " Esto baja tu calificación."),
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
             "Cumplirlo sube tu calificación de DT; fallarlo la baja.", C.accion('objetivos_screen', "VER OBJETIVOS"))


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
    r = 1 con 8+ de ventaja → Campeón; r ≤ n/8 → Finalista; r ≤ n/4 → Semifinal; r ≤ n/2 → Cuartos;
    si no → Octavos.
    """
    if n < 2:
        return 'Octavos'
    if r == 1 and ventaja >= VENTAJA_PARA_TITULO:
        return 'Campeón'
    if r <= n / 8:
        return 'Finalista'
    if r <= n / 4:
        return 'Semifinal'
    if r <= n / 2:
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


# --- v4.3.0: avisos de objetivo cumplido (uno por objetivo y temporada) ---
def _ya_avisado(estado: dict, clave: str) -> bool:
    avisados = _dc(estado).setdefault('objetivos_avisados', [])
    marca = f"{clave}:{int(estado.get('temporada', 1) or 1)}"
    if marca in avisados:
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
                 f"Llegaste a {alcanzada}. La directiva está satisfecha con la campaña internacional.",
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
                 "Pase lo que pase en lo que queda de temporada, ya cumpliste la meta de liga. ¡Felicitaciones!",
                 C.accion('objetivos_screen', "VER OBJETIVOS"))
        return True
    except Exception as e:
        logger.error(f"Error al revisar el objetivo de liga: {e}")
        return False


# --- v3.2.0: espaldarazo financiero (más presupuesto a cambio de una meta más alta) ---
ESPALDARAZO = [(0.15, 1), (0.30, 2), (0.50, 3)]
CALIF_ESPALDARAZO = 40


def _texto_meta(pos_max: int) -> str:
    return "Ser campeón de liga" if pos_max <= 1 else f"Terminar entre los {pos_max} primeros"


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
    obj['espaldarazo'] = {'pct': op['pct'], 'puestos': op['puestos']}
    obj['texto'] = _texto_meta(obj['pos_max']) + " (espaldarazo)"
    try:
        from alpha_football.finanzas import registrar
        registrar(estado, 'directiva', op['monto'])
    except Exception as e:
        logger.error(f"Error al registrar el espaldarazo: {e}")
    from alpha_football import correo as C
    C.enviar(estado, 'directiva', "Espaldarazo aprobado",
             f"Te damos ${op['monto'] / 1_000_000:.1f}M. A cambio, la meta ahora es: {obj['texto']}.",
             C.accion('objetivos_screen', "VER OBJETIVOS"))
    return True, f"Aprobado: +${op['monto'] / 1_000_000:.1f}M · nueva meta: puesto {obj['pos_max']}."


def texto_evaluacion(info: dict) -> str:
    """Cuerpo del correo de rendimiento."""
    partes = [f"Liga: terminaste {info['posicion']}º (meta: {info.get('texto', '')}) → {info['resultado'].upper()}."]
    m = int(info.get('monto', 0) or 0)
    partes.append(f"{'Premio' if m >= 0 else 'Multa'} de la directiva: ${abs(m) / 1_000_000:.1f}M.")
    if info.get('copa'):
        cp = info['copa']
        partes.append(f"Copa: {cp['alcanzada']} (meta: {cp['texto']}) → {cp['resultado'].upper()}.")
    partes.append(f"Calificación de DT: {info.get('calif')} · confianza: {info.get('confianza')}.")
    v = info.get('veredicto')
    partes.append({'felicitacion': "¡Felicitaciones! Superaste lo que esperábamos.",
                   'neutro': "Cumpliste. Seguimos con el plan.",
                   'regano': "No cumpliste. Te damos una segunda oportunidad: si vuelves a fallar, te despedimos.",
                   'despido': "Decidimos prescindir de tus servicios.",
                   'fin_contrato': "Tu contrato terminó y no seguirás en el club."}.get(v, ""))
    if info.get('indemnizacion'):
        partes.append(f"Indemnización: ${info['indemnizacion'] / 1_000_000:.2f}M a tu patrimonio.")
    return " ".join(partes)
