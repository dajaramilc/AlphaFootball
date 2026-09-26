"""Préstamos: menores diferidos de la revisión final + correos de cedidos (sesión 2026-09-25 pulido)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(5)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, prestamos as P, correo as C
from alpha_football.models import Jugador

save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def _abierto(e, j=1):
    e['liga'].jornada_actual = j


class Si:
    random = staticmethod(lambda: 0.0)


def _club(e, desde=4):
    """Un club de liga que no es el clásico del user."""
    from alpha_football.data.clasicos import es_clasico
    return next(eq for eq in e['liga'].equipos[desde:] if not es_clasico(eq, e['mi_equipo']))


def _suplente(club):
    """Uno que el club presta: fuera del top 3 y del mejor once."""
    from alpha_football.formaciones import mejor_once
    tit = {club.jugadores[i].nombre_completo for i in mejor_once(club.jugadores, "4-3-3")}
    top3 = {x.nombre_completo for x in sorted(club.jugadores, key=lambda x: -x.overall)[:3]}
    return next(x for x in club.jugadores if x.nombre_completo not in tit | top3)


def test_retiro_de_cedido_regen_va_al_dueno():
    from alpha_football.retiros import procesar_retiros
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    destino = e['liga'].equipos[5]
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    P.iniciar(e, j, mi, destino, 12, 50)
    j.edad = 45
    n_mi, n_dest = len(mi.jugadores), len(destino.jugadores)
    azar = random.Random(3); azar.random = lambda: 0.0
    retiros = procesar_retiros(e, azar)
    r = next(x for x in retiros if x['nombre'] == j.nombre_completo)
    assert any(x.nombre_completo == r['regen'] for x in mi.jugadores), "el regen va al dueño"
    assert not any(x.nombre_completo == r['regen'] for x in destino.jugadores)
    assert len(destino.jugadores) == n_dest - 1 and len(mi.jugadores) >= n_mi + 1 - sum(
        1 for x in retiros if x['equipo'] == mi.nombre and x['nombre'] != j.nombre_completo)
    print("  test_retiro_de_cedido_regen_va_al_dueno: OK")


def test_ofertas_aceptar_prestamo_cerrado_dice_la_jornada():
    from alpha_football.ui import ofertas_screen as OS
    e = estado_carrera(); _abierto(e, 6); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[1]
    of = {'jugador': j, 'comprador': e['liga'].equipos[8], 'monto': 0, 'prestamo': {'meses': 6, 'pct_ellos': 60}}
    e['ofertas_recibidas'] = [of]
    OS._aceptar_sel(e, of)
    assert 'jornada 11' in e['oferta_msg'][0], e['oferta_msg']
    print("  test_ofertas_aceptar_prestamo_cerrado_dice_la_jornada: OK")


def test_rechazar_prestamo_no_castiga_como_venta():
    from alpha_football.ui import ofertas_screen as OS
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[1]
    j.pide_salir, j.moral = True, 60
    of = {'jugador': j, 'comprador': e['liga'].equipos[8], 'monto': 0, 'prestamo': {'meses': 6, 'pct_ellos': 60}}
    e['ofertas_recibidas'] = [of]
    OS._rechazar_sel(e, of)
    assert j.moral == 60 and int(getattr(j, 'escalon_salida', 0) or 0) == 0
    print("  test_rechazar_prestamo_no_castiga_como_venta: OK")


def test_aviso_de_contrato_por_vencer_del_cedido():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    destino = e['liga'].equipos[5]
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    P.iniciar(e, j, mi, destino, 12, 50)
    j.contrato_anios = 1
    n = e['liga'].num_jornadas
    e['liga'].jornada_actual = n - 2                             # abre la ventana de cierre
    P.revisar_jornada(e)
    avisos = [m for m in C.bandeja(e) if 'contrato' in m['asunto'].lower() and j.apellido in m['asunto']]
    assert len(avisos) == 1, [m['asunto'] for m in C.bandeja(e)]
    assert 'CONCLUIR' in avisos[0]['cuerpo'] and 'renov' in avisos[0]['cuerpo'].lower(), avisos[0]['cuerpo']
    e['liga'].jornada_actual = n - 1
    P.revisar_jornada(e)
    assert len([m for m in C.bandeja(e) if 'contrato' in m['asunto'].lower() and j.apellido in m['asunto']]) == 1
    print("  test_aviso_de_contrato_por_vencer_del_cedido: OK")


def test_panel_prestamos_scroll_y_pendientes():
    from alpha_football.ui import plantilla_screen as PS
    e = estado_carrera(); _abierto(e, 6); mi = e['mi_equipo']
    for j in mi.jugadores[:12]:
        j.prestamo = {'dueno': 'Otro', 'club': mi.nombre, 'pct_dueno': 50, 'vuelve': [2, 1], 'meses': 12}
    club = e['liga'].equipos[4]
    llega = _suplente(club)
    P.iniciar(e, llega, club, mi, 6, 50)                         # cerrado: queda acordado
    filas = PS._filas_prestamos(e)
    assert len(filas) == 13 and 'ACORDADO' in filas[-1][1], [f[1] for f in filas]
    e['prestamos_abierto'] = True
    pygame.event.clear(); PS.render(screen, e)
    for _ in range(3):
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=5, pos=PS.R_OVERLAY_PR.center))
    PS.render(screen, e)
    assert e.get('prestamos_scroll') == 3
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=PS.rects_overlay_prestamos(10)[9][1].center))
    PS.render(screen, e)
    assert P.pendiente_de(e, llega) is None and llega in club.jugadores
    print("  test_panel_prestamos_scroll_y_pendientes: OK")


def test_cancelar_regreso_acordado():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    club = e['liga'].equipos[5]; j = _suplente(club)
    P.iniciar(e, j, club, mi, 12, 50)
    e['liga'].jornada_actual = 5
    P.terminar(e, j)
    fin = next(p for p in P._pendientes(e) if p.get('tipo') == 'fin')
    P.cancelar_pendiente(e, fin)
    e['liga'].jornada_actual = 11
    P.revisar_jornada(e)
    assert j in mi.jugadores and j.prestamo
    print("  test_cancelar_regreso_acordado: OK")


class _Cuenta(list):
    iteraciones = 0

    def __iter__(self):
        _Cuenta.iteraciones += 1
        return super().__iter__()


def test_cedidos_no_recorre_todas_las_plantillas_cada_vez():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    destino = e['liga'].equipos[5]
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    P.iniciar(e, j, mi, destino, 12, 50)
    for eq in P._equipos(e):
        eq.jugadores = _Cuenta(eq.jugadores)
    assert [x for x, _ in P.cedidos(e)] == [j]
    _Cuenta.iteraciones = 0
    assert [x for x, _ in P.cedidos(e)] == [j]
    assert _Cuenta.iteraciones == 0, _Cuenta.iteraciones
    P.terminar(e, j)
    assert P.cedidos(e) == []
    print("  test_cedidos_no_recorre_todas_las_plantillas_cada_vez: OK")


def test_analisis_no_llega_al_club_nuevo_del_dt():
    e = estado_carrera(); _abierto(e, 1)
    club = _club(e); j = _suplente(club)
    assert P.evaluar_pedido(e, j, club, 6, 20)[0] == 'analiza'
    nuevo = next(eq for eq in e['liga'].equipos if eq is not club and eq is not e['mi_equipo'])
    e['mi_equipo'] = nuevo                                        # el DT cambió de club
    e['liga'].jornada_actual = 2
    P.resolver_analisis(e, Si())
    assert j in club.jugadores and j not in nuevo.jugadores
    print("  test_analisis_no_llega_al_club_nuevo_del_dt: OK")


def test_regreso_si_la_liga_cambia_de_tamano():
    e = estado_carrera(); liga = e['liga']; mi = e['mi_equipo']
    liga.num_jornadas = 38; _abierto(e, 1)
    club = liga.equipos[3]; j = _suplente(club)
    P.iniciar(e, j, club, mi, 6, 50)
    assert j.prestamo['vuelve'] == [1, 19]
    liga.num_jornadas = 22                                         # ahora el invierno es J11-13
    liga.jornada_actual = 11
    P.revisar_jornada(e)
    assert j in club.jugadores and j.prestamo is None
    print("  test_regreso_si_la_liga_cambia_de_tamano: OK")


def test_correo_de_oferta_de_prestamo_abre_ofertas():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    P.alternar_lista(e, j)
    azar = random.Random(2); azar.random = lambda: 0.0
    assert P.generar_ofertas(e, azar)
    m = C.bandeja(e)[0]
    assert m['accion'] == {'pantalla': 'ofertas_screen', 'texto': 'VER OFERTAS'}, m['accion']
    print("  test_correo_de_oferta_de_prestamo_abre_ofertas: OK")


def test_club_corto_de_plantilla_no_presta():
    from alpha_football.mercado_ia import PLANTILLA_MIN_VENDEDOR
    e = estado_carrera(); _abierto(e, 1)
    club = _club(e)
    j = _suplente(club)
    while len(club.jugadores) > PLANTILLA_MIN_VENDEDOR:
        x = next(x for x in sorted(club.jugadores, key=lambda x: x.overall) if x is not j)
        club.jugadores.remove(x)
    club.alineacion_activa = None
    res, msg = P.evaluar_pedido(e, j, club, 6, 100)
    assert res == 'rechaza' and 'plantilla' in msg.lower(), msg
    print("  test_club_corto_de_plantilla_no_presta: OK")


def test_vestuario_no_pone_transferible_al_que_esta_a_prestamo():
    from alpha_football.vestuario import actualizar_moral
    e = estado_carrera(); mi = e['mi_equipo']
    j = mi.jugadores[-1]
    j.prestamo = {'dueno': 'Otro', 'club': mi.nombre, 'pct_dueno': 50, 'vuelve': [2, 1], 'meses': 12}
    j.moral, j.jornadas_moral_baja, j.transferible, j.pide_salir = 5, 20, False, False
    actualizar_moral(mi, [], 0, 1, False, set(), rng=random.Random(1))
    assert not j.transferible
    print("  test_vestuario_no_pone_transferible_al_que_esta_a_prestamo: OK")


def _correos_de(e, j):
    return [m for m in C.bandeja(e) if j.apellido in m['asunto'] or j.apellido in m['cuerpo']]


def test_correos_del_que_llega_a_prestamo():
    e = estado_carrera(); _abierto(e, 2); mi = e['mi_equipo']
    club = _club(e); j = _suplente(club)
    P.iniciar(e, j, club, mi, 6, 40)                              # abierto: llega ya
    ms = _correos_de(e, j)
    assert len(ms) == 1 and 'llegó' in ms[0]['asunto'].lower(), [m['asunto'] for m in ms]
    c = ms[0]['cuerpo']
    assert '6 meses' in c and 'J2 T1' in c and 'J11 T1' in c and 'pagas el 60%' in c.lower(), c
    e['liga'].jornada_actual = 11
    P.revisar_jornada(e)
    ms = _correos_de(e, j)
    assert len(ms) == 2 and 'vuelve' in ms[0]['asunto'].lower(), [m['asunto'] for m in ms]
    assert '6 meses' in ms[0]['cuerpo'] and 'J2 T1' in ms[0]['cuerpo'] and 'J11 T1' in ms[0]['cuerpo'], ms[0]['cuerpo']
    print("  test_correos_del_que_llega_a_prestamo: OK")


def test_correos_del_cedido_acordado_con_mercado_cerrado():
    e = estado_carrera(); _abierto(e, 6); mi = e['mi_equipo']
    destino = _club(e)
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    P.iniciar(e, j, mi, destino, 12, 30)                          # cerrado: se va en J11
    ms = _correos_de(e, j)
    assert len(ms) == 1 and 'acordado' in ms[0]['asunto'].lower(), [m['asunto'] for m in ms]
    c = ms[0]['cuerpo']
    assert '1 año' in c and 'J11 T1' in c and 'J11 T2' in c and '70%' in c and '30%' in c, c
    e['liga'].jornada_actual = 11
    P.revisar_jornada(e)
    ms = _correos_de(e, j)
    assert len(ms) == 2 and 'cedido' in ms[0]['asunto'].lower(), [m['asunto'] for m in ms]
    assert '1 año' in ms[0]['cuerpo'] and 'J11 T1' in ms[0]['cuerpo'] and 'J11 T2' in ms[0]['cuerpo'], ms[0]['cuerpo']
    print("  test_correos_del_cedido_acordado_con_mercado_cerrado: OK")


def test_correo_de_vuelta_por_fin_de_contrato_dice_que_queda_libre():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    P.iniciar(e, j, mi, _club(e), 12, 50)
    j.contrato_anios = 1
    P.cierre_contratos(e)
    m = _correos_de(e, j)[0]
    assert 'libre' in m['cuerpo'] and '100%' not in m['cuerpo'], m['cuerpo']
    print("  test_correo_de_vuelta_por_fin_de_contrato_dice_que_queda_libre: OK")


def test_correo_de_concluir_muestra_la_fecha_real():
    e = estado_carrera(); _abierto(e, 2); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    P.iniciar(e, j, mi, _club(e), 12, 50)                        # vuelve J2 T2
    e['liga'].jornada_actual = 3
    P.terminar(e, j)                                              # abierto: vuelve ya
    m = _correos_de(e, j)[0]
    assert 'hasta J3 T1' in m['cuerpo'], m['cuerpo']
    print("  test_correo_de_concluir_muestra_la_fecha_real: OK")


def test_correo_de_vuelta_sin_dueno_dice_que_queda_libre():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    club = _club(e); j = _suplente(club)
    P.iniciar(e, j, club, mi, 6, 50)
    j.prestamo['dueno'] = 'Club Que No Existe'
    P.terminar(e, j)
    m = _correos_de(e, j)[0]
    assert 'libre' in m['cuerpo'] and 'volvió a' not in m['cuerpo'], m['cuerpo']
    print("  test_correo_de_vuelta_sin_dueno_dice_que_queda_libre: OK")


def test_dato_malformado_no_corta_los_regresos():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    club = _club(e)
    a, b = sorted(club.jugadores, key=lambda x: x.overall)[:2]
    P.iniciar(e, a, club, mi, 6, 50); P.iniciar(e, b, club, mi, 6, 50)
    a.prestamo['desde'] = 7                                       # no indexable
    e['liga'].jornada_actual = 11
    P.revisar_jornada(e)
    assert a in club.jugadores and b in club.jugadores
    print("  test_dato_malformado_no_corta_los_regresos: OK")


def test_regreso_por_nombre_de_ventana_si_la_liga_se_achica():
    e = estado_carrera(); liga = e['liga']; mi = e['mi_equipo']
    liga.num_jornadas = 38; _abierto(e, 37)                       # ventana de cierre
    club = _club(e); j = _suplente(club)
    P.iniciar(e, j, club, mi, 12, 50)
    assert j.prestamo['vuelve'] == [2, 36]
    liga.num_jornadas = 8; e['temporada'] = 2; liga.jornada_actual = 6   # 8 jornadas: cierre J6-8, sin invierno
    P.revisar_jornada(e)
    assert j in club.jugadores and j.prestamo is None
    print("  test_regreso_por_nombre_de_ventana_si_la_liga_se_achica: OK")


def test_prestamo_de_save_viejo_sin_ventana_ni_desde():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    club = _club(e); j = _suplente(club)
    club.jugadores.remove(j); mi.jugadores.append(j)
    j.prestamo = {'dueno': club.nombre, 'club': mi.nombre, 'pct_dueno': 50, 'vuelve': [1, 11], 'meses': 6}
    P._invalidar()
    e['liga'].jornada_actual = 11
    P.revisar_jornada(e)
    assert j in club.jugadores and j.prestamo is None
    m = _correos_de(e, j)[0]
    assert 'Periodo: 6 meses (hasta J11 T1)' in m['cuerpo'], m['cuerpo']
    print("  test_prestamo_de_save_viejo_sin_ventana_ni_desde: OK")


def test_club_no_presta_si_ya_le_compraste_y_queda_corto():
    from alpha_football.mercado_ia import PLANTILLA_MIN_VENDEDOR
    e = estado_carrera(); _abierto(e, 1)
    club = _club(e); j = _suplente(club)
    while len(club.jugadores) > PLANTILLA_MIN_VENDEDOR + 1:
        club.jugadores.remove(next(x for x in sorted(club.jugadores, key=lambda x: x.overall) if x is not j))
    club.alineacion_activa = None
    otro = next(x for x in sorted(club.jugadores, key=lambda x: x.overall) if x is not j)
    e['datos_carrera']['traspasos_pendientes'] = [{'tipo': 'compra', 'jugador': otro.nombre_completo,
                                                   'origen': club.nombre, 'destino': e['mi_equipo'].nombre}]
    res, msg = P.evaluar_pedido(e, j, club, 6, 100)
    assert res == 'rechaza' and 'plantilla' in msg.lower(), msg
    print("  test_club_no_presta_si_ya_le_compraste_y_queda_corto: OK")


def test_regen_movido_al_dueno_toma_su_region():
    from alpha_football.retiros import procesar_retiros
    from alpha_football import market as M
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']      # dueño europeo (premier)
    latam = next(l for l in e['primera_division'].values() if l.tipo in M.TIPOS_LATAM)
    destino = latam.equipos[0]
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    P.iniciar(e, j, mi, destino, 12, 50)
    j.edad = 45
    azar = random.Random(3); azar.random = lambda: 0.0
    r = next(x for x in procesar_retiros(e, azar) if x['nombre'] == j.nombre_completo)
    regen = next(x for x in mi.jugadores if x.nombre_completo == r['regen'])
    assert M._REGION_LATAM.get(id(regen)) is False, M._REGION_LATAM.get(id(regen))
    print("  test_regen_movido_al_dueno_toma_su_region: OK")


def test_retiro_del_que_tienes_a_prestamo_deja_tu_plantilla():
    from alpha_football.retiros import procesar_retiros
    from alpha_football.market import PLANTILLA_MINIMA
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    club = _club(e); j = _suplente(club)
    P.iniciar(e, j, club, mi, 12, 50)
    j.edad = 45
    n_club = len(club.jugadores)
    azar = random.Random(3); azar.random = lambda: 0.0
    r = next(x for x in procesar_retiros(e, azar) if x['nombre'] == j.nombre_completo)
    assert not any(x.nombre_completo == r['regen'] for x in mi.jugadores)
    assert any(x.nombre_completo == r['regen'] for x in club.jugadores) and len(mi.jugadores) >= PLANTILLA_MINIMA
    assert r['equipo'] == club.nombre and not r['es_user'] and len(club.jugadores) >= n_club
    print("  test_retiro_del_que_tienes_a_prestamo_deja_tu_plantilla: OK")


def test_cedidos_sin_club_propio_es_vacio():
    e = estado_carrera(); e['mi_equipo'] = None
    assert P.cedidos(e) == []
    print("  test_cedidos_sin_club_propio_es_vacio: OK")


def test_panel_una_sola_fila_con_regreso_acordado():
    from alpha_football.ui import plantilla_screen as PS
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    club = _club(e); j = _suplente(club)
    P.iniciar(e, j, club, mi, 12, 50)
    e['liga'].jornada_actual = 5
    P.terminar(e, j)
    filas = [f for f in PS._filas_prestamos(e) if j.nombre_completo[:22] in f[1]]
    assert len(filas) == 1 and isinstance(filas[0][0], dict) and filas[0][0]['tipo'] == 'fin', filas
    print("  test_panel_una_sola_fila_con_regreso_acordado: OK")


TESTS = [test_correo_de_vuelta_por_fin_de_contrato_dice_que_queda_libre, test_correo_de_concluir_muestra_la_fecha_real,
         test_correo_de_vuelta_sin_dueno_dice_que_queda_libre, test_dato_malformado_no_corta_los_regresos,
         test_regreso_por_nombre_de_ventana_si_la_liga_se_achica, test_prestamo_de_save_viejo_sin_ventana_ni_desde,
         test_club_no_presta_si_ya_le_compraste_y_queda_corto, test_regen_movido_al_dueno_toma_su_region,
         test_retiro_del_que_tienes_a_prestamo_deja_tu_plantilla, test_cedidos_sin_club_propio_es_vacio,
         test_panel_una_sola_fila_con_regreso_acordado,
         test_correos_del_que_llega_a_prestamo, test_correos_del_cedido_acordado_con_mercado_cerrado,
         test_retiro_de_cedido_regen_va_al_dueno, test_ofertas_aceptar_prestamo_cerrado_dice_la_jornada,
         test_rechazar_prestamo_no_castiga_como_venta, test_aviso_de_contrato_por_vencer_del_cedido,
         test_panel_prestamos_scroll_y_pendientes, test_cancelar_regreso_acordado,
         test_cedidos_no_recorre_todas_las_plantillas_cada_vez, test_analisis_no_llega_al_club_nuevo_del_dt,
         test_regreso_si_la_liga_cambia_de_tamano, test_correo_de_oferta_de_prestamo_abre_ofertas,
         test_club_corto_de_plantilla_no_presta, test_vestuario_no_pone_transferible_al_que_esta_a_prestamo]


if __name__ == '__main__':
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
