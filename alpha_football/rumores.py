# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Rumores de mercado (v0.4.23.0)
Con el mercado abierto, cada jornada puede nacer un rumor (noticia de tipo 'rumor'). Seis de cada diez son
reales: al vencer su plazo (1-3 jornadas de mercado) el traspaso entre clubes de la IA se ejecuta y sale la
noticia "Confirmado: …"; si el rumor era sobre un jugador tuyo, te llega la oferta formal por OFERTAS. El
resto es humo: la mitad se desmiente y la otra mitad desaparece. Si el mercado cierra, todos son humo.
Estado en datos_carrera['rumores'] (solo ids y nombres: va tal cual al guardado). Sin UI.
"""
from __future__ import annotations

import logging
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)

PROB_RUMOR = 0.35               # por jornada con el mercado abierto
MAX_VIVOS = 2
PROB_REAL = 0.6
PLAZO = (1, 3)                  # jornadas de mercado hasta que se resuelve
PROB_DESMENTIDO = 0.5           # humo (o real que dejó de ser viable): se desmiente o desaparece sin más
PROB_SOBRE_USER = 0.3           # rumores sobre un jugador tuyo
COMPRADORES_A_MIRAR = 6         # clubes de la IA que se sondean para armar un rumor (queda el de la mejor figura)
FIGURAS_USER = 11               # un rumor sobre tu plantilla apunta a uno de tus mejores


def _datos(estado: dict) -> dict:
    dc = estado.setdefault('datos_carrera', {})
    d = dc.get('rumores')
    if not isinstance(d, dict) or not isinstance(d.get('vivos'), list):
        d = dc['rumores'] = {'vivos': [], 'sig_id': 1}
    return d


def vivos(estado: dict) -> list:
    """Rumores sin resolver (la lista del guardado)."""
    return _datos(estado)['vivos']


def _mercado_abierto(estado: dict) -> bool:
    from alpha_football.market import ventana_mercado_abierta
    liga = estado.get('liga')
    return ventana_mercado_abierta(int(getattr(liga, 'jornada_actual', 1) or 1),
                                   int(getattr(liga, 'num_jornadas', 22) or 22), estado=estado)


def _clubes(estado: dict) -> list:
    """[(club, tipo de liga, división)] de toda la partida."""
    from alpha_football.mercado_ia import ligas_de_la_partida
    return [(eq, tipo, div) for liga, tipo, div in ligas_de_la_partida(estado) for eq in liga.equipos]


def _club(estado: dict, nombre: str) -> tuple:
    return next(((eq, tipo) for eq, tipo, _div in _clubes(estado) if eq.nombre == nombre), (None, ''))


def _jugador(club: Any, rumor: dict) -> Any:
    return next((j for j in getattr(club, 'jugadores', None) or [] if str(j.id) == str(rumor.get('jugador_id'))
                 and j.nombre_completo == rumor.get('jugador')), None)


def _objetivo_ia(estado: dict, rng: random.Random, ocupados: set) -> Optional[tuple]:
    """(jugador, vendedor, comprador, precio): el fichaje que haría un club de la IA, con el mismo criterio
    que una ronda real (mercado_ia._buscar_refuerzo). De los clubes sondeados queda la mejor figura."""
    from alpha_football import mercado_ia as MI
    mi = estado.get('mi_equipo')
    equipos = _clubes(estado)
    temporada = int(estado.get('temporada', 1) or 1)
    compradores = [c for c in equipos if c[0] is not mi and int(getattr(c[0], 'sin_fichajes_hasta', 0) or 0) < temporada
                   and len(c[0].jugadores) < MI.PLANTILLA_MAX_IA]
    rng.shuffle(compradores)
    mejor = None
    for comprador, tipo_c, div_c in compradores[:COMPRADORES_A_MIRAR]:
        limite = max(0, int(getattr(comprador, 'balance', 0) or 0)) * MI.FRACCION_VENTANA
        ingresos, gasto, margen = MI.cuentas(estado, comprador, tipo_c, div_c)
        if limite <= 0 or margen <= 0 or gasto >= ingresos:
            continue
        hallado = MI._buscar_refuerzo(comprador, tipo_c, div_c, equipos, mi, limite, False, rng, estado,
                                      margen, ingresos - gasto)
        if hallado is None or hallado[0].id in ocupados:
            continue
        if mejor is None or hallado[0].overall > mejor[0].overall:
            mejor = (hallado[0], hallado[1], comprador, int(hallado[2]))
    return mejor


def _objetivo_user(estado: dict, rng: random.Random, ocupados: set) -> Optional[tuple]:
    """(jugador, tu club, comprador, precio): una de tus figuras (ni cedida ni recién llegada) y un club de
    la IA que puede pagarla."""
    from alpha_football import market
    from alpha_football.mercado_ia import PLANTILLA_MAX_IA
    from alpha_football.data.clasicos import es_clasico
    mi = estado.get('mi_equipo')
    propios = [j for j in getattr(mi, 'jugadores', None) or [] if not getattr(j, 'prestamo', None)
               and not market.traspasado_en_ventana(estado, j) and j.id not in ocupados]
    if not propios or len(mi.jugadores) <= market.PLANTILLA_MINIMA:
        return None
    j = rng.choice(sorted(propios, key=lambda x: -x.overall)[:FIGURAS_USER])
    valor = int(getattr(j, 'valor', 0) or 0) or market.calcular_valor(j)
    precio = market.cifra_cerrada(valor * rng.uniform(1.0, 1.4) * market.factor_contrato(j))
    pueden = [eq for eq, _t, _d in _clubes(estado) if eq is not mi and not es_clasico(eq, mi)
              and int(getattr(eq, 'balance', 0) or 0) >= precio and len(eq.jugadores) < PLANTILLA_MAX_IA]
    if not pueden:
        return None
    return j, mi, rng.choice(pueden), precio


def _importancia(media: int, clase: str) -> int:
    base = 4 if media >= 85 else 3 if media >= 80 else 2
    return max(3, base) if clase == 'user' else base      # lo que toca a tu plantilla entra al feed


def generar(estado: dict, rng: Optional[random.Random] = None, clase: Optional[str] = None) -> Optional[dict]:
    """Crea un rumor y publica su noticia (None si ya hay MAX_VIVOS o no hay de quién hablar). `clase`
    ('ia' | 'user') fuerza el tipo; sin ella, PROB_SOBRE_USER de que sea sobre un jugador tuyo."""
    from alpha_football import noticias
    from alpha_football.negociacion import dinero_exacto
    azar = rng or random.Random()
    d = _datos(estado)
    if len(d['vivos']) >= MAX_VIVOS:
        return None
    ocupados = {r.get('jugador_id') for r in d['vivos']}
    clase = clase or ('user' if azar.random() < PROB_SOBRE_USER else 'ia')
    hallado = (_objetivo_user if clase == 'user' else _objetivo_ia)(estado, azar, ocupados)
    if hallado is None:
        return None
    j, origen, destino, precio = hallado
    nombre, media = j.nombre_completo, int(j.overall)
    n = noticias.publicar(
        estado, 'rumor',
        noticias.titular(f"Rumor: {destino.nombre} quiere a {nombre}", f"Rumor: {nombre} suena en {destino.nombre}",
                         f"Rumor: quieren a {nombre}", f"Rumor: {nombre} puede cambiar de club"),
        f"Según la prensa, {destino.nombre} prepara una oferta de unos {dinero_exacto(precio)} por {nombre} "
        f"({j.posicion}, media {media}), de {origen.nombre}. Ninguno de los dos clubes lo confirma.",
        importancia=_importancia(media, clase), equipos=[destino, origen], jugadores=[j])
    rumor = {'id': int(d.get('sig_id', 1) or 1), 'clase': clase, 'jugador_id': j.id, 'jugador': nombre,
             'origen': origen.nombre, 'destino': destino.nombre, 'precio': int(precio),
             'real': azar.random() < PROB_REAL, 'vence': azar.randint(*PLAZO), 'noticia_id': n['id']}
    d['sig_id'] = rumor['id'] + 1
    d['vivos'].append(rumor)
    return rumor


def _cumplir_ia(estado: dict, r: dict) -> bool:
    """El traspaso entre clubes de la IA, si sigue siendo viable: el jugador sigue en su club, el comprador
    puede pagarlo y hay cupo en las dos plantillas."""
    from alpha_football import mercado_ia as MI
    from alpha_football.market import traspasado_en_ventana
    from alpha_football.negociacion import registrar_pase
    mi = estado.get('mi_equipo')
    vendedor = _club(estado, r.get('origen'))[0]
    comprador, tipo_c = _club(estado, r.get('destino'))
    j = _jugador(vendedor, r)
    precio = int(r.get('precio', 0) or 0)
    if j is None or comprador is None or mi in (vendedor, comprador):
        return False
    if getattr(j, 'prestamo', None) or traspasado_en_ventana(estado, j):
        return False
    if (int(getattr(comprador, 'balance', 0) or 0) < precio or len(comprador.jugadores) >= MI.PLANTILLA_MAX_IA
            or len(vendedor.jugadores) <= MI.PLANTILLA_MIN_VENDEDOR
            or int(getattr(comprador, 'sin_fichajes_hasta', 0) or 0) >= int(estado.get('temporada', 1) or 1)):
        return False
    MI._traspasar(j, vendedor, comprador, precio, tipo_c)
    registrar_pase(estado, j, vendedor.nombre, comprador.nombre, precio, False, confirmado=True)
    estado.setdefault('mercado_ia_log', []).append(
        f"{comprador.nombre} ficha a {j.nombre_completo} ({j.posicion} {j.overall}) de {vendedor.nombre} por ${precio:,}")
    return True


def _cumplir_user(estado: dict, r: dict) -> bool:
    """La oferta formal por tu jugador, por el cauce de siempre (OFERTAS + correo), si sigue siendo viable."""
    from alpha_football import market
    mi = estado.get('mi_equipo')
    comprador = _club(estado, r.get('destino'))[0]
    j = _jugador(mi, r)
    precio = int(r.get('precio', 0) or 0)
    if j is None or comprador is None or comprador is mi or getattr(j, 'prestamo', None):
        return False
    if (market.traspasado_en_ventana(estado, j) or len(mi.jugadores) <= market.PLANTILLA_MINIMA
            or int(getattr(comprador, 'balance', 0) or 0) < precio):
        return False
    oferta = {'jugador': j, 'comprador': comprador, 'monto': precio}
    estado.setdefault('ofertas_recibidas', []).append(oferta)
    try:
        from alpha_football.ui.match_screen import _correo_oferta
        _correo_oferta(estado, oferta, "Oferta por")
    except Exception as e:
        logger.error(f"rumores: no se pudo enviar el correo de la oferta: {e}")
    return True


def _resolver(estado: dict, r: dict, rng: random.Random, humo: bool = False) -> None:
    """Saca el rumor de los vivos y lo cumple (si es real y viable) o, con PROB_DESMENTIDO, lo desmiente."""
    from alpha_football import noticias
    lista = vivos(estado)
    if r in lista:
        lista.remove(r)
    if r.get('real') and not humo:
        try:
            if (_cumplir_user if r.get('clase') == 'user' else _cumplir_ia)(estado, r):
                return
        except Exception as e:
            logger.error(f"rumores: no se pudo cumplir el rumor de {r.get('jugador', '?')}: {e}", exc_info=True)
    if rng.random() >= PROB_DESMENTIDO:
        return
    nombre, destino = r.get('jugador', '?'), r.get('destino', '?')
    noticias.publicar(
        estado, 'rumor',
        noticias.titular(f"{nombre} desmiente su salida al {destino}", f"{nombre} desmiente su salida",
                         "Desmentido: el fichaje del rumor no se hará"),
        f"«No hay nada», dijo {nombre} sobre el supuesto interés de {destino}. En {r.get('origen', 'su club')} "
        "dan el asunto por cerrado.", importancia=3 if r.get('clase') == 'user' else 2)


def revisar_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Cierre de jornada (lo llama noticias.cierre_jornada): los rumores pierden una jornada de plazo y los
    vencidos se resuelven; con el mercado cerrado se apagan todos. Con el mercado abierto puede nacer uno."""
    if estado.get('liga') is None or estado.get('mi_equipo') is None:
        return
    azar = rng or random.Random()
    abierto = _mercado_abierto(estado)
    for r in list(vivos(estado)):
        if not abierto:
            _resolver(estado, r, azar, humo=True)
            continue
        r['vence'] = int(r.get('vence', 1) or 1) - 1
        if r['vence'] <= 0:
            _resolver(estado, r, azar)
    if abierto and azar.random() < PROB_RUMOR:
        generar(estado, azar)
