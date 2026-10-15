# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Salidas de jugadores (v4.4.0)
Descontento por correo, pide salir (transferible bloqueado), salida forzada del grande que
desciende, ofertas garantizadas y escalada aviso → advertencia → recordatorio → regaño.
Sin UI.
"""
from __future__ import annotations

import logging
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)


def limpiar(j: Any) -> None:
    """Al vender, fichar o liberar: el jugador deja de pedir salir y se borra su escalada."""
    try:
        j.transferible = j.pide_salir = False
        j.salida_forzada = j.descontento_avisado = False
        j.renovacion_avisada = False       # v0.4.10.0
        j.escalon_salida = 0
    except Exception as e:
        logger.error(f"No se pudo limpiar la salida de {getattr(j, 'nombre', '?')}: {e}")


SALIDA_FORZADA_N = 3


def marcar_salida_forzada(estado: dict, equipo) -> list:
    """Grande que desciende: sus 3 mejores piden salir (el user no puede retenerlos por moral)."""
    js = sorted([j for j in getattr(equipo, 'jugadores', []) or []
                 if not getattr(j, 'prestamo', None)],   # a préstamo: no se toca
                key=lambda x: -x.overall)[:SALIDA_FORZADA_N]
    mi = estado.get('mi_equipo') if isinstance(estado, dict) else None
    es_user = mi is not None and equipo is mi
    for j in js:
        j.salida_forzada = True
        if es_user:
            j.pide_salir = j.transferible = True
            j.escalon_salida = 0
    if es_user and js:
        try:
            from alpha_football import correo as C
            nombres = ", ".join(_nombre(j) for j in js)
            # el asunto se corta a 80 caracteres: lo importante va primero y los nombres también en el cuerpo
            C.enviar(estado, 'directiva', f"Tras el descenso piden salir: {nombres}",
                     f"Tras el descenso, {nombres} han manifestado su deseo de seguir en 1ª división. Llegarán "
                     "ofertas por ellos; le advertimos que rechazarlas generará malestar en la directiva.",
                     C.accion('plantilla_screen', "VER PLANTILLA"))
        except Exception as e:
            logger.error(f"No se pudo avisar la salida forzada: {e}")
        anunciar_pide_salir(estado)         # v0.4.26.0: sus noticias salen en el momento del descenso
    return js


UMBRAL_DESCONTENTO = 50
MORAL_POR_RECHAZO = 8
MORAL_RENOVAR_BIEN = 10
MORAL_RENOVAR_AVISO = 5          # v0.4.10.0: extra si renuevas después de que te lo pidió
UMBRAL_QUIERE_RENOVAR = 75
MARGEN_OFERTA = (0.9, 1.2)
EFECTO_ESCALON = {2: (-5, 0), 3: (-5, -2), 4: (-10, -4)}      # (confianza, calificación DT)

CIERRE_DESCONTENTO = {   # v4.7.0: los correos de los jugadores, un poco más largos
    'minutos': "Le pido que lo tenga en cuenta en los próximos partidos; estoy listo para cuando me necesite.",
    'equipo': "Lo digo porque quiero a este club y me duele verlo así. Cuente conmigo para cambiarlo.",
    'sueldo': "Espero que podamos sentarnos a hablarlo pronto, con respeto y sin prisas.",
}
TEXTOS_DESCONTENTO = {
    'minutos': (
        "No estoy teniendo minutos y así no puedo demostrar lo que valgo. Necesito jugar.",
        "Entreno como el que más y el fin de semana miro desde el banco. Quiero jugar más.",
        "Vine a este club para ser importante, no para calentar el banco. Dame minutos.",
        "Si no juego, pierdo ritmo y pierdo mi lugar en la selección. Necesito continuidad.",
        "Me dijeron que iba a ser parte del proyecto. Hoy no lo siento: quiero jugar.",
    ),
    'equipo': (
        "Así no se puede: perdemos una y otra vez. Quiero que el equipo mejore.",
        "No vine a pelear abajo. Necesitamos refuerzos y otra actitud.",
        "La mala racha me está afectando. Quiero un equipo que compita de verdad.",
        "Me frustra ver cómo se nos escapan los partidos. Esto tiene que cambiar.",
        "Necesito sentir que el club tiene ambición. Hoy el equipo no está a la altura.",
    ),
    'sueldo': (
        "Rindo como titular y cobro como suplente. Quiero un contrato acorde.",
        "Mi sueldo está muy por debajo de lo que paga el mercado. Hablemos de renovar.",
        "Otros clubes pagan el doble por jugadores como yo. Quiero que se me valore.",
        "No es solo dinero, es respeto: mi contrato no refleja lo que aporto.",
        "Si el club no mejora mi contrato, voy a tener que escuchar otras ofertas.",
    ),
}


def _nombre(j) -> str:
    return f"{getattr(j, 'nombre', '')} {getattr(j, 'apellido', '')}".strip()


def _clave_jornada(estado: dict) -> list:
    """Temporada + partidos de liga jugados por el user (en la última fecha jornada_actual no avanza)."""
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    jugadas = int(getattr(liga, 'jornada_actual', 1) or 1)
    try:
        if liga is not None and mi is not None and getattr(liga, 'calendario', None):
            from alpha_football.directiva import _jugadas
            jugadas = _jugadas(liga, mi)
    except Exception as e:
        logger.debug(f"No se pudieron contar las jornadas jugadas: {e}")
    return [int(estado.get('temporada', 1) or 1), jugadas]


def _ventana_abierta(estado: dict) -> bool:
    liga = estado.get('liga')
    if liga is None:
        return False
    from alpha_football.market import ventana_mercado_abierta
    return ventana_mercado_abierta(int(getattr(liga, 'jornada_actual', 1) or 1),
                                   int(getattr(liga, 'num_jornadas', 22) or 22), estado=estado)


def causa_principal(j) -> str:
    tot = {'minutos': 0, 'equipo': 0, 'sueldo': 0}
    for c in getattr(j, 'causas_moral', []) or []:
        for k in tot:
            tot[k] += int((c or {}).get(k, 0) or 0)
    peor = min(tot.values())
    if peor >= 0:
        return 'equipo'
    for k in ('sueldo', 'minutos', 'equipo'):          # desempate
        if tot[k] == peor:
            return k
    return 'equipo'


def revisar_descontento(estado: dict, rng: Optional[random.Random] = None) -> list:
    """Tras 1 jornada con moral < 50, el jugador escribe (una vez por episodio) según la causa."""
    from alpha_football import correo as C
    azar = rng or random.Random()
    mi = estado.get('mi_equipo')
    dc = estado.setdefault('datos_carrera', {})
    ultimos = dc.setdefault('descontento_ultimo', {})
    avisados = []
    for j in list(getattr(mi, 'jugadores', []) or []):
        try:
            if int(j.moral) >= UMBRAL_DESCONTENTO:
                j.descontento_avisado = False
                continue
            if j.descontento_avisado or j.pide_salir:
                continue
            causa = causa_principal(j)
            opciones = [i for i in range(5) if i != ultimos.get(causa)]
            idx = azar.choice(opciones)
            ultimos[causa] = idx
            if causa == 'sueldo' and not getattr(j, 'prestamo', None):   # a préstamo: no se renueva
                acc = {'pantalla': 'negociacion_screen', 'texto': "RENOVAR", 'renovar': j.id}
            else:
                acc = C.accion('plantilla_screen', "VER PLANTILLA")
            C.enviar(estado, 'jugador', f"{_nombre(j)} está descontento",
                     "Míster, " + TEXTOS_DESCONTENTO[causa][idx][0].lower() + TEXTOS_DESCONTENTO[causa][idx][1:]
                     + " " + CIERRE_DESCONTENTO[causa] + f"\n{_nombre(j)}", acc, jugador=j)
            j.descontento_avisado = True
            avisados.append(j)
        except Exception as e:
            logger.error(f"No se pudo revisar el descontento de {getattr(j, 'nombre', '?')}: {e}")
    return avisados


TEXTOS_QUIERE_RENOVAR = {      # v0.4.10.0
    'lider': "Míster, este vestuario es mi casa y no me veo en otro lado. Se me acaba el contrato en verano "
             "y quiero seguir liderando este grupo. Siéntese con mi agente cuando pueda.",
    'profesional': "Míster, estoy a gusto, trabajo bien aquí y mi contrato termina al final de la temporada. "
                   "Me gustaría dejarlo resuelto pronto para concentrarme solo en jugar.",
    'mercenario': "Míster, estoy contento aquí, no le voy a mentir. Se me acaba el contrato y prefiero firmar "
                  "con ustedes antes de escuchar a otros… si los números acompañan, claro.",
    'polemico': "Míster, mire que no soy de decir estas cosas, pero aquí estoy bien. Se me vence el contrato: "
                "renuévenme antes de que cambie de opinión.",
    'normal': "Míster, estoy muy contento en el club y mi contrato termina al final de la temporada. "
              "Me encantaría quedarme. ¿Podemos hablar de la renovación?",
}


def revisar_renovaciones(estado: dict, rng: Optional[random.Random] = None) -> list:
    """v0.4.10.0: un jugador contento (moral ≥ 75) en su último año escribe pidiendo renovar.
    Desde la mitad de la temporada, uno por jornada (el mejor primero) y una vez por contrato."""
    from alpha_football import correo as C
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if liga is None or mi is None:
        return []
    from alpha_football import temporada as T      # v0.4.13.0: desde la mitad de la temporada (por fecha)
    if not T.segunda_mitad(estado):
        return []
    cand =[j for j in list(getattr(mi, 'jugadores', []) or [])
            if int(getattr(j, 'contrato_anios', 0) or 0) == 1 and int(j.moral) >= UMBRAL_QUIERE_RENOVAR
            and not j.pide_salir and not j.salida_forzada and not getattr(j, 'prestamo', None)
            and not getattr(j, 'renovacion_avisada', False)]
    if not cand:
        return []
    j = max(cand, key=lambda x: x.overall)
    texto = TEXTOS_QUIERE_RENOVAR.get(j.personalidad, TEXTOS_QUIERE_RENOVAR['normal'])
    C.enviar(estado, 'jugador', f"{_nombre(j)} quiere renovar", f"{texto}\n{_nombre(j)}",
             {'pantalla': 'negociacion_screen', 'texto': "RENOVAR", 'renovar': j.id}, jugador=j)
    j.renovacion_avisada = True
    return [j]


def revisar_curados(estado: dict) -> list:
    """El que pidió salir por moral y la recuperó (≥ 50) se queda (la salida forzada no se cura)."""
    from alpha_football import correo as C
    mi = estado.get('mi_equipo')
    curados = []
    for j in list(getattr(mi, 'jugadores', []) or []):
        if j.pide_salir and not j.salida_forzada and int(j.moral) >= UMBRAL_DESCONTENTO:
            limpiar(j)
            curados.append(j)
            try:
                C.enviar(estado, 'jugador', f"{_nombre(j)} se queda contento",
                         f"Míster, quería decirle que ya estoy bien. Recuperé la confianza y ya no pido salir: "
                         f"quiero seguir aquí y darlo todo.\n{_nombre(j)}", C.accion('plantilla_screen', "VER PLANTILLA"),
                         jugador=j)
            except Exception as e:
                logger.error(f"No se pudo avisar que {j.nombre} se queda: {e}")
    return curados


def _compradores(estado: dict, j) -> list:
    mi = estado.get('mi_equipo')
    clubes = [eq for l in (estado.get('primera_division') or {}).values() if l is not None for eq in l.equipos]
    if not j.salida_forzada and estado.get('liga') is not None:
        clubes += list(estado['liga'].equipos)
    vistos, out = set(), []
    for eq in clubes:
        if id(eq) in vistos or eq is mi or (mi is not None and eq.nombre == mi.nombre):
            continue
        vistos.add(id(eq))
        out.append(eq)
    if int(getattr(j, 'moral', 70)) >= 40 and mi is not None:     # v3.5.0: el clásico solo por cláusula
        try:
            from alpha_football.data.clasicos import es_clasico
            out = [eq for eq in out if not es_clasico(eq, mi)]
        except Exception as e:
            logger.error(f"No se pudo filtrar el clásico: {e}")
    return out


def ofertas_garantizadas(estado: dict, rng: Optional[random.Random] = None) -> list:
    """Con la ventana abierta, cada jugador que pide salir sin oferta pendiente recibe una."""
    if not _ventana_abierta(estado):
        return []
    from alpha_football import correo as C
    from alpha_football.market import calcular_valor, cifra_cerrada, factor_contrato, traspasado_en_ventana
    azar = rng or random.Random()
    mi = estado.get('mi_equipo')
    pendientes = estado.setdefault('ofertas_recibidas', [])
    nuevas = []
    for j in list(getattr(mi, 'jugadores', []) or []):
        if not j.pide_salir or any(o.get('jugador') is j for o in pendientes):
            continue
        if getattr(j, 'prestamo', None) or traspasado_en_ventana(estado, j):   # a préstamo / recién llegado
            continue
        try:
            valor = int(getattr(j, 'valor', 0) or 0) or calcular_valor(j)
            monto = cifra_cerrada(valor * azar.uniform(*MARGEN_OFERTA) * factor_contrato(j))   # v0.4.18.0: cifra cerrada
            clubes = _compradores(estado, j)
            pueden = [eq for eq in clubes if int(getattr(eq, 'balance', 0) or 0) >= monto]
            if pueden:
                comprador = azar.choice(pueden)
            elif clubes:
                comprador = max(clubes, key=lambda eq: int(getattr(eq, 'balance', 0) or 0))
                remate = cifra_cerrada(max(0, int(comprador.balance)) * 0.95, abajo=True)   # v0.4.18.0: sin pasar el balance
                if remate < monto * PISO_REMATE:
                    continue     # una oferta ridícula no sirve de salida: se espera a la próxima jornada
                monto = remate
            else:
                continue
            if monto <= 0:
                continue
            of = {'jugador': j, 'comprador': comprador, 'monto': monto}
            pendientes.append(of)
            nuevas.append(of)
            C.enviar(estado, 'club', f"Oferta por {j.nombre} {j.apellido}",
                     f"{comprador.nombre} ofrece ${monto:,} por el jugador, que ha manifestado su deseo de salir.",
                     C.accion('ofertas_screen', "VER OFERTAS"))
        except Exception as e:
            logger.error(f"No se pudo crear la oferta garantizada por {getattr(j, 'nombre', '?')}: {e}")
    return nuevas


# si nadie puede pagar, el más rico ofrece lo que tiene solo si llega a este % de lo que vale
PISO_REMATE = 0.5
CUERPO_ESCALON_1_TIEMPO = ("Míster, sigo esperando una salida y no llega. Le pido de corazón que me deje ir: "
                           "necesito un cambio y creo que es lo mejor para los dos.")

_CORREO_ESCALON = {
    1: ('jugador', "{n}: quiero irme", "Míster, rechazó la oferta y sigo esperando. Quiero salir del club; "
                                          "no es nada personal, pero necesito otro destino.\n{n}"),
    2: ('directiva', "Advertencia: la situación de {n}",
        "El vestuario está incómodo: {n} quiere irse y sigue en el club. Esta situación reduce la confianza "
        "de la directiva."),
    3: ('directiva', "Recordatorio: {n} quiere salir",
        "Le recordamos que {n} ha pedido salir. Le rogamos que lo resuelva: la situación está afectando a "
        "la confianza de la directiva y a su calificación."),
    4: ('directiva', "Llamado de atención por {n}",
        "La directiva está molesta: {n} sigue en el club contra su voluntad. Esto reduce su calificación."),
}


def subir_escalon(estado: dict, j, pasos: int = 1, por_rechazo: bool = False) -> None:
    """Sube la escalada del jugador; efectos por cada escalón; un solo correo por jornada."""
    from alpha_football import correo as C, directiva as D
    dc = estado.setdefault('datos_carrera', {})
    for _ in range(max(0, int(pasos))):
        j.escalon_salida = int(getattr(j, 'escalon_salida', 0) or 0) + 1
        conf, calif = EFECTO_ESCALON.get(min(4, j.escalon_salida), (0, 0))
        if conf:
            D._dc(estado)['confianza'] = max(0, min(100, D.confianza(estado) + conf))
        if calif:
            D.ajustar_calif(estado, calif)
    enviados = dc.setdefault('salidas_correo', {})
    clave = _clave_jornada(estado)
    if enviados.get(str(j.id)) == clave:
        return
    enviados[str(j.id)] = clave
    rem, asunto, cuerpo = _CORREO_ESCALON[min(4, max(1, j.escalon_salida))]
    if j.escalon_salida <= 1 and not por_rechazo:
        cuerpo = CUERPO_ESCALON_1_TIEMPO     # nadie rechazó nada: solo pasó el tiempo
    n = _nombre(j)
    C.enviar(estado, rem, asunto.format(n=n), cuerpo.format(n=n), C.accion('ofertas_screen', "VER OFERTAS"))


def oferta_rechazada(estado: dict, jugador) -> None:
    """Rechazar una oferta por un jugador que pide salir: −8 de moral y un escalón."""
    try:
        mi = estado.get('mi_equipo')
        if jugador is None or not getattr(jugador, 'pide_salir', False) or jugador not in getattr(mi, 'jugadores', []):
            return
        if not _ventana_abierta(estado):        # fuera de la ventana no hay escalada
            return
        jugador.moral = max(0, int(jugador.moral) - MORAL_POR_RECHAZO)
        subir_escalon(estado, jugador, 1, por_rechazo=True)
    except Exception as e:
        logger.error(f"Error al registrar el rechazo de la oferta: {e}")


MOTIVO_PIDE_SALIR = {      # v0.4.26.0: causa_principal(j) -> cómo lo cuenta la prensa
    'minutos': "porque no tiene los minutos que esperaba",
    'equipo': "porque no ve ambición deportiva en el proyecto",
    'sueldo': "porque no está conforme con su contrato",
}


def anunciar_pide_salir(estado: dict) -> list:
    """v0.4.26.0: una noticia "X pide salir" por cada jugador del user que acaba de pedirlo (o a quien el
    descenso empuja a irse). Se recuerda en datos_carrera['pide_salir_noticiado']; el que deja de pedirlo
    (se curó, se vendió) sale de la lista y, si vuelve a pedirlo, hay otra noticia. Devuelve los anunciados."""
    anunciados = []
    try:
        from alpha_football import noticias, correo as C
        mi = estado.get('mi_equipo')
        if mi is None:
            return anunciados
        lista = estado.setdefault('datos_carrera', {}).setdefault('pide_salir_noticiado', [])
        plantel = list(getattr(mi, 'jugadores', []) or [])
        piden = [j for j in plantel if getattr(j, 'pide_salir', False) and not getattr(j, 'prestamo', None)]
        ids_piden = {j.id for j in piden}
        lista[:] = [i for i in lista if i in ids_piden]          # el que ya no pide salir se olvida
        for j in piden:
            if j.id in lista:
                continue
            lista.append(j.id)
            nombre = _nombre(j)
            if getattr(j, 'salida_forzada', False):
                cuerpo = (f"Tras el descenso de {mi.nombre}, {nombre} ({j.posicion}, media {j.overall}) ha pedido "
                          "salir para seguir jugando en 1ª división. Sus representantes ya sondean el mercado.")
            else:
                cuerpo = (f"{nombre} ({j.posicion}, media {j.overall}) ha comunicado que quiere dejar {mi.nombre} "
                          f"{MOTIVO_PIDE_SALIR.get(causa_principal(j), MOTIVO_PIDE_SALIR['equipo'])}. "
                          "Sus representantes ya sondean el mercado.")
            noticias.publicar(estado, 'vestuario',
                              noticias.titular(f"{nombre} pide salir de {mi.nombre}", f"{nombre} pide salir del club",
                                               f"{nombre} pide salir"),
                              cuerpo, importancia=4 if int(j.overall) >= 80 else 3, equipos=[mi], jugadores=[j],
                              accion=C.accion('plantilla_screen', "VER PLANTILLA"))
            anunciados.append(j)
    except Exception as e:
        logger.error(f"No se pudo anunciar a los que piden salir: {e}", exc_info=True)
    return anunciados


def cierre_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Cierre de jornada de liga del user: cura, descontento, escalada por tiempo y ofertas."""
    try:
        revisar_curados(estado)
        anunciar_pide_salir(estado)         # v0.4.26.0: la noticia del que acaba de pedir salir
        from alpha_football import dias as _dias      # v0.4.12.0: los avisos de jugadores llegan en días sueltos
        with _dias.diferir_correos(estado):
            revisar_descontento(estado, rng)
            revisar_renovaciones(estado, rng)       # v0.4.10.0
        if _ventana_abierta(estado):
            mi = estado.get('mi_equipo')
            pendientes = estado.get('ofertas_recibidas') or []
            for j in list(getattr(mi, 'jugadores', []) or []):
                if j.pide_salir and (int(j.escalon_salida or 0) > 0 or any(o.get('jugador') is j for o in pendientes)):
                    subir_escalon(estado, j, 1)
            if _dias.activo(estado):        # v0.4.12.0: la oferta llega en un día del hueco
                if any(getattr(j, 'pide_salir', False) for j in getattr(mi, 'jugadores', []) or []):
                    _dias.programar(estado, 'garantizadas')
            else:
                ofertas_garantizadas(estado, rng)
    except Exception as e:
        logger.error(f"Error en el cierre de jornada de salidas: {e}")


def al_cambiar_de_club(estado: dict, viejo) -> None:
    """El DT se va (despido u oferta): el club viejo pasa a la IA y suelta a los que pedían salir."""
    for j in list(getattr(viejo, 'jugadores', []) or []):
        if j.salida_forzada:
            j.pide_salir = j.transferible = False       # la IA los vende ya (sigue salida_forzada)
            j.escalon_salida = 0
        elif j.pide_salir:
            limpiar(j)
    from alpha_football.mercado_ia import vender_salidas_forzadas
    vender_salidas_forzadas(estado)


def al_renovar(estado: dict, jugador, salario: int) -> None:
    """Renovar al 100% del mercado o más: +10 de moral y se borra la queja por sueldo."""
    from alpha_football.finanzas import salario_mercado
    if int(salario or 0) >= salario_mercado(jugador):
        jugador.moral = min(100, int(jugador.moral) + MORAL_RENOVAR_BIEN)
        for c in getattr(jugador, 'causas_moral', []) or []:
            if isinstance(c, dict):
                c['sueldo'] = 0
    if getattr(jugador, 'renovacion_avisada', False):      # v0.4.10.0: nos lo pidió y cumplimos
        jugador.moral = min(100, int(jugador.moral) + MORAL_RENOVAR_AVISO)
        jugador.renovacion_avisada = False
