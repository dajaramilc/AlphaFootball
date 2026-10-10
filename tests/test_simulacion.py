"""v0.4.14.1: simulación automática desde CALENDARIO (clic en un día: el segundo entrenador dirige hasta ahí)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date, timedelta
from test_calendario import screen, key, _e, _jugar, _con_copa   # noqa: E402  (deja save.guardar_en_slot sin efecto)
from alpha_football import calendario as CAL, correo as C, dias as D, simulacion as SIM, temporada as T


def _correr(e, hasta, tope=500):
    """Da pasos hasta que la simulación termina. Devuelve (pasos, el último)."""
    pasos = []
    for _ in range(tope):
        r = SIM.paso(e, hasta)
        pasos.append(r)
        if r['tipo'] == 'fin':
            return pasos, r
    raise AssertionError("la simulación no terminó")


def _partido(e, jornada):
    mi = e['mi_equipo']
    return next(p for p in e['liga'].calendario if p.jornada == jornada and mi.id in (p.local_id, p.visitante_id))


# --- Lógica ───────────────────────────────────────────────────────────────────

def test_hasta_que_dias_se_puede_simular():
    e = _e(); hoy = D.hoy(e)
    assert not SIM.puede_simular_hasta(e, hoy) and not SIM.puede_simular_hasta(e, hoy - timedelta(days=1))
    assert SIM.puede_simular_hasta(e, hoy + timedelta(days=1)) and SIM.puede_simular_hasta(e, T.fin(e))
    assert not SIM.puede_simular_hasta(e, T.fin(e) + timedelta(days=1))
    assert SIM.partidos_hasta(e, CAL.fecha_liga(e, 1)) == 0                # el del día elegido lo juegas tú
    assert SIM.partidos_hasta(e, CAL.fecha_liga(e, 2)) == 1


def test_un_paso_sin_partido_avanza_un_dia():
    e = _e(); hoy = D.hoy(e)
    r = SIM.paso(e, CAL.fecha_liga(e, 1))
    assert r['tipo'] == 'dia' and D.hoy(e) == hoy + timedelta(days=1)


def test_al_llegar_al_dia_elegido_se_detiene_sin_jugar_ese_partido():
    e = _e(); D.hoy(e)
    hasta = CAL.fecha_liga(e, 1)
    pasos, fin = _correr(e, hasta)
    assert D.hoy(e) == hasta and fin['motivo'] == 'llego' and not _partido(e, 1).jugado
    assert all(p['tipo'] == 'dia' for p in pasos[:-1])


def test_el_partido_de_un_dia_intermedio_lo_juega_el_segundo_entrenador():
    e = _e(); D.hoy(e)
    hasta = CAL.fecha_liga(e, 1) + timedelta(days=2)
    pasos, fin = _correr(e, hasta)
    p = _partido(e, 1)
    assert p.jugado and e['liga'].jornada_actual == 2 and D.hoy(e) == hasta and fin['motivo'] == 'llego'
    jugados = [x['partido'] for x in pasos if x['tipo'] == 'partido']
    assert len(jugados) == 1 and jugados[0]['etiqueta'] == 'J1'
    loc = p.local_id == e['mi_equipo'].id
    assert (jugados[0]['gf'], jugados[0]['gc']) == ((p.goles_local, p.goles_visitante) if loc else (p.goles_visitante, p.goles_local))
    for k in ('prepartido_resultado', 'match_mode', 'postpartido', 'prepartido_paso'):
        assert k not in e, k                                               # no deja a medias la pantalla del partido


def test_el_segundo_entrenador_no_alinea_lesionados_y_rota_a_los_cansados():
    from alpha_football.models import alineacion_por_defecto
    e = _e(); mi = e['mi_equipo']
    alin = getattr(mi, 'alineacion_activa', None)
    if alin is None:
        alin = mi.alineacion_activa = alineacion_por_defecto(mi)
    lesionado = mi.jugadores[alin.titulares[1]]
    lesionado.lesion_dias = 3
    cansado = mi.jugadores[alin.titulares[2]]
    cansado.energia = 5.0
    SIM.once_del_segundo(e)
    once = [mi.jugadores[i] for i in alin.titulares]
    assert len(once) == 11 == len(set(alin.titulares)) and lesionado not in once
    assert sum(1 for j in once if j.posicion == 'POR') == 1
    assert not set(alin.titulares) & set(alin.convocados)
    suplentes = [j for j in mi.jugadores if j not in once and j.posicion == cansado.posicion and not j.lesion_dias]
    if any(j.overall > cansado.overall - 19 and j.energia >= 70 for j in suplentes):
        assert cansado not in once                                         # con un suplente fresco a mano, el cansado descansa


def test_el_ultimo_dia_de_fichajes_se_cierra_solo():
    from alpha_football import dia_final as DF
    e = _e(); D.hoy(e); _jugar(e, 1); _jugar(e, 2)                         # el próximo partido es la J3 (5 de septiembre)
    e['liga'].jornada_actual = 3
    CAL.asegurar(e)['dia'] = '2026-08-30'
    _correr(e, date(2026, 9, 3))
    assert D.hoy(e) == date(2026, 9, 3)
    assert CAL.asegurar(e)['dia_final']['cierre'] and not T.ventana_abierta(e)
    assert not e.get('aviso_mercado_activo')                               # sin cartel viejo esperando en el hub
    f = _e(); D.hoy(f); _jugar(f, 1); _jugar(f, 2); f['liga'].jornada_actual = 3
    CAL.asegurar(f)['dia'] = '2026-08-30'
    _correr(f, date(2026, 8, 31))                                          # si el día elegido ES el último, queda abierto para ti
    assert D.hoy(f) == date(2026, 8, 31) and DF.activo(f) and DF.horas(f) == 20


def test_no_se_detiene_por_una_oferta_ni_por_un_evento():
    e = _e(); D.hoy(e); D.hasta_el_partido(e); _jugar(e, 1); e['liga'].jornada_actual = 2
    D.programar(e, 'oferta')
    with D.diferir_correos(e):
        C.enviar(e, 'club', "Riña", "x")['evento'] = {'id': 'x', 'resuelto': None}
    D.asignar_dias(e)
    hasta = CAL.fecha_liga(e, 2)
    pasos, fin = _correr(e, hasta)
    assert D.hoy(e) == hasta and fin['motivo'] == 'llego'
    assert len(e['ofertas_recibidas']) == 1                                # la oferta queda esperando en la bandeja
    assert [m for m in C.bandeja(e) if m.get('evento')]


def test_un_despido_pendiente_detiene_la_simulacion():
    e = _e(); hoy = D.hoy(e)
    e['despido_pendiente'] = {'motivo': 'x', 'opciones': []}
    r = SIM.paso(e, hoy + timedelta(days=5))
    assert r == {'tipo': 'fin', 'motivo': 'despido'} and D.hoy(e) == hoy


def test_con_la_temporada_terminada_no_hay_nada_que_simular():
    e = _e(); D.hoy(e)
    for j in range(1, 23):
        _jugar(e, j)
    e['liga'].jornada_actual = 22
    CAL.asegurar(e)['dia'] = (T.fin(e) - timedelta(days=2)).isoformat()
    pasos, fin = _correr(e, T.fin(e))
    assert D.hoy(e) == T.fin(e) and fin['motivo'] == 'llego' and len(pasos) == 3
    assert SIM.paso(e, T.fin(e) + timedelta(days=3)) == {'tipo': 'fin', 'motivo': 'temporada'}


# --- Pantalla CALENDARIO ──────────────────────────────────────────────────────

def _clic_en(KS, e, d):
    a, m = e['cal_mes']
    i = KS.celdas_mes(a, m).index(d)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=KS.rect_celda(i).center, button=1))


def _abrir(e):
    from alpha_football.ui import calendario_screen as KS
    D.hoy(e); D.hasta_el_partido(e)                                        # hoy = el día de la J1 (agosto)
    pygame.event.clear(); assert KS.render(screen, e) is None
    return KS


def test_clic_en_un_dia_futuro_pide_confirmacion_y_esc_cancela():
    e = _e(); KS = _abrir(e)
    hoy = D.hoy(e)
    _clic_en(KS, e, hoy); assert KS.render(screen, e) is None and 'cal_sim' not in e            # hoy: nada que simular
    _clic_en(KS, e, hoy - timedelta(days=1)); KS.render(screen, e); assert 'cal_sim' not in e   # ni el pasado
    destino = hoy + timedelta(days=3)
    _clic_en(KS, e, destino); assert KS.render(screen, e) is None
    assert e['cal_sim'] == {'fase': 'confirmar', 'hasta': destino.isoformat()}
    key(pygame.K_RIGHT); KS.render(screen, e); assert e['cal_mes'] == [hoy.year, hoy.month]     # el diálogo se come las teclas
    key(pygame.K_ESCAPE); assert KS.render(screen, e) is None                                   # cancela, no sale
    assert 'cal_sim' not in e and D.hoy(e) == hoy and not _partido(e, 1).jugado


def test_el_dialogo_dice_hasta_cuando_y_cuantos_partidos():
    e = _e(); KS = _abrir(e)
    destino = D.hoy(e) + timedelta(days=3)
    _clic_en(KS, e, destino); KS.render(screen, e)
    dib, original = [], KS.draw_text
    KS.draw_text = lambda scr, txt, *a, **k: (dib.append(txt), original(scr, txt, *a, **k))[1]
    try:
        pygame.event.clear(); KS.render(screen, e)
    finally:
        KS.draw_text = original
    assert any(CAL.texto_fecha(destino).upper() in t for t in dib), dib    # el título va en mayúsculas
    assert any("segundo entrenador" in t and "1 partido" in t for t in dib), dib


def test_confirmar_simula_dia_por_dia_en_la_misma_pantalla():
    e = _e(); KS = _abrir(e)
    hoy = D.hoy(e)
    destino = hoy + timedelta(days=3)
    _clic_en(KS, e, destino); KS.render(screen, e)
    key(pygame.K_RETURN); assert KS.render(screen, e) is None
    assert e['cal_sim']['fase'] == 'corriendo'
    fechas = [D.hoy(e)]
    for _ in range(40):
        if 'cal_sim' not in e:
            break
        e['cal_sim']['sig'] = 0                                            # sin esperar el reloj real
        pygame.event.clear(); assert KS.render(screen, e) is None          # nunca sale de la pantalla
        fechas.append(D.hoy(e))
    assert 'cal_sim' not in e and D.hoy(e) == destino and _partido(e, 1).jugado
    saltos = [(b - a).days for a, b in zip(fechas, fechas[1:])]
    assert max(saltos) == 1                                                # se ve pasar de a un día
    assert "3 días" in e['cal_msg'][0] and "1 partido" in e['cal_msg'][0]


def test_esc_detiene_la_simulacion_sin_salir_del_calendario():
    e = _e(); KS = _abrir(e)
    hoy = D.hoy(e)
    destino = hoy + timedelta(days=6)
    _clic_en(KS, e, destino); KS.render(screen, e)
    key(pygame.K_RETURN); KS.render(screen, e)
    e['cal_sim']['sig'] = 0
    pygame.event.clear(); KS.render(screen, e)                             # juega la J1
    key(pygame.K_ESCAPE); assert KS.render(screen, e) is None
    assert 'cal_sim' not in e and D.hoy(e) < destino and "detenida" in e['cal_msg'][0].lower()
    key(pygame.K_ESCAPE); assert KS.render(screen, e) == 'league_screen'   # el siguiente ESC ya sale


def test_la_simulacion_sigue_el_mes_del_dia_en_que_va():
    e = _e(); KS = _abrir(e)
    CAL.asegurar(e)['dia'] = '2026-09-29'; _jugar(e, 1); _jugar(e, 2); _jugar(e, 3); _jugar(e, 4)
    e['liga'].jornada_actual = 5                                           # el próximo partido es la J5 (3 de octubre o después)
    e['cal_mes'] = [2026, 9]
    e['cal_sim'] = {'fase': 'corriendo', 'hasta': '2026-10-02', 'sig': 0}
    for _ in range(10):
        if 'cal_sim' not in e:
            break
        e['cal_sim']['sig'] = 0
        pygame.event.clear(); KS.render(screen, e)
    assert D.hoy(e) == date(2026, 10, 2) and e['cal_mes'] == [2026, 10]


def test_atajos_y_ayuda_explican_la_simulacion():
    from alpha_football.ui import atajos, ayuda, calendario_screen as KS
    assert "Clic en un día" in atajos.ATAJOS['calendario_screen']
    its = ayuda.items('calendario_screen', _e())
    assert any(r == KS.R_GRILLA and "simula" in x.lower() and len(x) <= 110 for r, _t, x in its)


if __name__ == '__main__':
    TESTS = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    fail = 0
    for t in TESTS:
        try:
            t()
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"\n{len(TESTS) - fail}/{len(TESTS)} tests pasaron")
    if fail:
        sys.exit(1)
