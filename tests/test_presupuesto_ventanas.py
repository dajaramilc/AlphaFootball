"""v0.4.11.0: mercado sin ventana de cierre ni pretemporada de la IA; presupuesto por temporada."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402
from alpha_football import market as M, prestamos as PR, traspasos_pendientes as TP, finanzas as F
from alpha_football import correo as C


def test_solo_inicio_e_invierno():
    assert M.ventanas_mercado(22) == [(1, 3, 'inicio'), (11, 13, 'invierno')]
    assert [j for j in range(1, 23) if M.ventana_mercado_abierta(j, 22)] == [1, 2, 3, 11, 12, 13]
    assert M.proxima_apertura(5, 22) == 11 and M.proxima_apertura(15, 22) == 1
    assert M.clave_ventana_traspaso(2, 2, 22) == '2-verano'
    assert M.clave_ventana_traspaso(2, 12, 22) == '2-invierno'
    assert M.clave_ventana_traspaso(2, 21, 22) == ''


def test_liga_corta_solo_tiene_inicio():
    assert M.ventanas_mercado(6) == [(1, 3, 'inicio')]
    assert M.proxima_apertura(4, 6) == 1


def test_regreso_de_prestamos_sin_cierre():
    e = estado_carrera(); liga = e['liga']
    liga.jornada_actual = 2                                     # ventana de inicio
    assert PR._regreso(e, 6) == (1, 'invierno', 11)
    assert PR._regreso(e, 12) == (2, 'inicio', 1)
    liga.jornada_actual = 12                                    # ventana de invierno
    assert PR._regreso(e, 6) == (2, 'inicio', 1)
    assert PR._regreso(e, 12) == (2, 'invierno', 11)
    liga.jornada_actual = 18                                    # cerrado, pasado el invierno
    assert PR._regreso(e, 6) == (2, 'invierno', 11)             # arranca en el inicio de la T2
    assert PR._regreso(e, 12) == (3, 'inicio', 1)


def test_prestamo_viejo_con_ventana_de_cierre():
    assert PR._vuelve({'vuelve': [1, 20], 'ventana': 'cierre'}, 22) == [2, 1]
    assert PR._vuelve({'vuelve': [1, 11], 'ventana': 'invierno'}, 22) == [1, 11]
    assert PR._vuelve({'vuelve': [2, 1], 'ventana': 'inicio'}, 22) == [2, 1]


def test_texto_de_lo_acordado_tras_el_invierno():
    e = estado_carrera(); mi = e['mi_equipo']; e['liga'].jornada_actual = 8
    rival = e['liga'].equipos[1]
    assert "en la jornada 11" in TP.diferir_venta(e, mi.jugadores[0], rival, 1_000_000)
    e['liga'].jornada_actual = 16
    txt = TP.diferir_compra(e, rival.jugadores[0], rival, 1_000_000)
    assert "al empezar la próxima temporada" in txt and "jornada 1," not in txt


def test_acordado_no_pierde_contrato_en_el_cierre():
    e = estado_carrera(); mi = e['mi_equipo']; rival = e['liga'].equipos[1]
    e['liga'].jornada_actual = 16
    llega, sale = rival.jugadores[0], mi.jugadores[0]
    llega.contrato_anios, sale.contrato_anios = 3, 1
    TP.diferir_compra(e, llega, rival, 1_000_000)
    TP.diferir_venta(e, sale, rival, 1_000_000)
    e['temporada'] = 2
    F.cierre_temporada(e)
    assert llega.contrato_anios == 3                            # el contrato pactado no pierde un año
    assert sale in mi.jugadores and not getattr(sale, 'fin_de_contrato', False)   # vendido: no queda libre
    e['liga'].jornada_actual = 1
    assert TP.ejecutar(e) == 2
    assert llega in mi.jugadores and sale in rival.jugadores


def _temporada_jugable(tipo='argentina', idx=3):
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    e = estado_carrera(tipo, idx)
    e['copa_user_en_copa'] = False
    inicializar_calendario_liga(e['liga'])
    return e


def test_el_cambio_de_temporada_no_corre_la_ronda_de_pretemporada():
    from alpha_football import mercado_ia as MI
    from alpha_football.ui import resumen_temporada_screen as R
    e = _temporada_jugable()
    modos, original = [], MI.ronda_fichajes_ia
    MI.ronda_fichajes_ia = lambda estado, modo='ventana', rng=None: modos.append(modo) or []
    try:
        R.avanzar_nueva_temporada(e)
    finally:
        MI.ronda_fichajes_ia = original
    assert e['temporada'] == 2 and 'pretemporada' not in modos


def test_la_ventana_de_inicio_mueve_mas_clubes_que_el_invierno():
    from alpha_football import mercado_ia as MI
    e = estado_carrera()
    vistos, original = [], MI._buscar_refuerzo
    MI._buscar_refuerzo = lambda comprador, *a, **k: vistos.append(comprador.nombre)   # devuelve None: no ficha
    try:
        n_inicio = n_invierno = 0
        for semilla in range(1, 11):                    # 10 rondas de cada una: no depende de una semilla
            e['liga'].jornada_actual = 2
            MI.ronda_fichajes_ia(e, 'ventana', random.Random(semilla)); n_inicio += len(vistos); vistos.clear()
            e['liga'].jornada_actual = 12
            MI.ronda_fichajes_ia(e, 'ventana', random.Random(semilla)); n_invierno += len(vistos); vistos.clear()
    finally:
        MI._buscar_refuerzo = original
    assert n_invierno > 0 and n_inicio > n_invierno * 1.4, (n_inicio, n_invierno)


def test_factor_salud_por_tramos():
    b = 100_000_000
    assert F.factor_salud(-1, b) == 0.80
    assert F.factor_salud(0, b) == 0.90 and F.factor_salud(24_999_999, b) == 0.90
    assert F.factor_salud(25_000_000, b) == 1.00 and F.factor_salud(74_999_999, b) == 1.00
    assert F.factor_salud(75_000_000, b) == 1.10 and F.factor_salud(149_999_999, b) == 1.10
    assert F.factor_salud(150_000_000, b) == 1.20 and F.factor_salud(10 ** 10, b) == 1.20
    assert F.factor_salud(50, 0) == 1.20                       # base 0: no divide por cero


def test_el_sobrante_no_pasa_de_temporada():
    p = F.presupuesto_temporada(100_000_000, 900_000_000, 'cumplido')
    assert p['salud'] == 1.20 and p['objetivo'] == 1.10 and p['bonos'] == 0
    assert 131_999_999 <= p['total'] <= 132_000_001
    assert F.presupuesto_temporada(100_000_000, 50_000_000, 'superado')['total'] == 125_000_000
    assert F.presupuesto_temporada(100_000_000, 50_000_000, 'fallado')['total'] == 85_000_000
    assert F.presupuesto_temporada(100_000_000, 50_000_000, '')['total'] == 100_000_000   # sin dato: neutro


def test_topes_del_multiplicador():
    alto = F.presupuesto_temporada(100_000_000, 900_000_000, 'superado', True, True)   # 1.2 × 1.25 × 1.35
    assert alto['mult'] == 1.75 and alto['total'] == 175_000_000
    bajo = F.presupuesto_temporada(100_000_000, -1, 'fallado')                         # 0.8 × 0.85 = 0.68
    assert abs(bajo['mult'] - 0.68) < 1e-9


def test_la_deuda_se_descuenta_con_piso():
    p = F.presupuesto_temporada(100_000_000, -50_000_000, 'fallado')
    assert p['deuda'] == 50_000_000 and 17_999_999 <= p['total'] <= 18_000_001
    assert F.presupuesto_temporada(100_000_000, -500_000_000, 'fallado')['total'] == 10_000_000


def test_el_cierre_fija_el_presupuesto_y_avisa():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = 999_000_000
    e['temporada'] = 2
    e['historial'] = [{'temporada': 1, 'equipo': mi.nombre, 'objetivo_resultado': 'cumplido', 'campeon_liga': 'Otro'}]
    F.cierre_temporada(e)
    base = F.presupuesto_base(mi, e['liga'].tipo, 1)
    esperado = F.presupuesto_temporada(base, 999_000_000, 'cumplido')
    assert mi.balance == esperado['total'] < 999_000_000
    assert e['datos_carrera']['presupuesto_temporada']['total'] == mi.balance
    m = next(x for x in C.bandeja(e) if x['asunto'] == "Presupuesto de la temporada 2")
    assert m['remitente'] == 'directiva' and m['accion']['pantalla'] == 'finanzas_screen'


def test_titulos_e_historial_ajeno():
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = 0
    e['temporada'] = 2
    e['historial'] = [{'temporada': 1, 'equipo': mi.nombre, 'objetivo_resultado': 'superado', 'campeon_liga': mi.nombre}]
    e['datos_carrera']['campeones_copas'] = [{'temporada': 1, 'champions': mi.nombre, 'libertadores': 'Otro'}]
    info = F.aplicar_presupuesto_temporada(e)
    assert info['objetivo'] == 1.25 and abs(info['bonos'] - 0.35) < 1e-9
    e2 = estado_carrera(); e2['temporada'] = 2; e2['mi_equipo'].balance = 0
    e2['historial'] = [{'temporada': 1, 'equipo': 'Otro club', 'objetivo_resultado': 'superado'}]
    assert F.aplicar_presupuesto_temporada(e2)['objetivo'] == 1.0          # ese registro no es de este club
    e3 = estado_carrera(); e3['temporada'] = 2; e3['mi_equipo'].balance = 0
    assert F.aplicar_presupuesto_temporada(e3)['objetivo'] == 1.0          # save viejo, sin historial


def test_en_rojo_sigue_la_sancion_y_descuenta_la_deuda():
    e = estado_carrera(); mi = e['mi_equipo']
    base = F.presupuesto_base(mi, e['liga'].tipo, 1)
    mi.balance = -int(base * 0.2)
    e['temporada'] = 2
    F.cierre_temporada(e)
    assert e['datos_carrera']['temporadas_en_rojo'] == 1 and mi.sancion_puntos == F.PUNTOS_QUIEBRA
    assert mi.balance >= int(base * F.PISO_PRESUPUESTO) and mi.balance > 0


def test_reglas_de_objetivos_entran_en_el_panel():
    from alpha_football.ui import objetivos_screen as OS
    assert OS.R_REGLAS.height >= 18 + 9 * 38
    assert OS.R_REGLAS.bottom <= 690


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
