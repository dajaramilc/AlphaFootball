"""v0.4.17.0: Balón de Oro en octubre y Jugador Sudamericano del Año en enero (premios por fecha)."""
import sys, os, random
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(23)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, correo as C, premios as PR, temporada as T
from alpha_football.paises import SUDAMERICA
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def _jugados(e, n=20):
    for mapa in (e['primera_division'], e['segunda_division']):
        for liga in mapa.values():
            for eq in getattr(liga, 'equipos', None) or []:
                for j in eq.jugadores:
                    j.partidos_jugados = n


def _datos(equipo_ganador, equipo_2="Otro FC", temporada=1):
    f = lambda nombre, eq: {'nombre': nombre, 'equipo': eq, 'liga': 'Liga', 'posicion': 'DEL', 'ovr': 80,
                            'goles': 20, 'asistencias': 5, 'nota': 7.5, 'pj': 20, 'goles_copa': 0,
                            'asistencias_copa': 0, 'puntaje': 100.0}
    podio = [f("Uno Primero", equipo_ganador), f("Dos Segundo", equipo_2), f("Tres Tercero", "Tercer FC")]
    return {'temporada': temporada, 'ganador': podio[0], 'podio': podio}


def _pendiente(e, premio, fecha, equipo, equipo_2="Otro FC"):
    e['datos_carrera'].setdefault('premios_pendientes', []).append(
        {'premio': premio, 'fecha_entrega': fecha, 'datos': _datos(equipo, equipo_2)})


# ── Task 5: lógica ───────────────────────────────────────────────────────────────

def test_fechas_de_gala():
    e = estado_carrera('premier'); e['temporada'] = 2
    ini = T.inicio(e)
    bo, sa = PR.fecha_entrega(e, 'balon_oro'), PR.fecha_entrega(e, 'sudamericano')
    assert (bo.year, bo.month, bo.weekday()) == (ini.year, 10, 0) and bo.day >= 25    # último lunes de octubre
    assert sa == date(ini.year + 1, 1, 15)                                           # Europa: el enero siguiente
    e = estado_carrera('betplay'); e['temporada'] = 2
    ini = T.inicio(e)
    assert PR.fecha_entrega(e, 'sudamericano') == date(ini.year, 1, 15)              # Sudamérica: a los 15 días
    bo = PR.fecha_entrega(e, 'balon_oro')
    assert (bo.year, bo.month, bo.weekday()) == (ini.year, 10, 0) and bo.day >= 25
    print("  test_fechas_de_gala: OK")


def test_sudamericano_solo_ligas_sudamericanas():
    e = estado_carrera('premier'); _jugados(e)
    crack = e['primera_division']['premier'].equipos[0].jugadores[-1]
    crack.goles = 60                                              # el mejor del mundo juega en Europa
    crack.ataque = crack.defensa = crack.fisico = crack.tecnica = crack.mental = 95   # v0.4.26.0: el Balón pide media >= 85.5
    balon = PR.calcular_balon_de_oro(e['primera_division'], e['segunda_division'], 1)
    sud = PR.calcular_sudamericano(e['primera_division'], e['segunda_division'], 1)
    assert balon['ganador']['nombre'] == crack.nombre_completo
    clubes_sa = {eq.nombre for mapa in (e['primera_division'], e['segunda_division'])
                 for t, liga in mapa.items() if t in SUDAMERICA and liga is not None for eq in liga.equipos}
    assert sud and sud['temporada'] == 1 and all(p['equipo'] in clubes_sa for p in sud['podio'])
    print("  test_sudamericano_solo_ligas_sudamericanas: OK")


def test_cerrar_temporada_deja_pendientes():
    e = estado_carrera('premier'); _jugados(e); e['temporada'] = 2       # la 1 acaba de terminar
    pend = PR.cerrar_temporada(e, e['primera_division'], e['segunda_division'], 1, {})
    assert [p['premio'] for p in pend] == ['balon_oro', 'sudamericano']
    assert pend is e['datos_carrera']['premios_pendientes']
    assert all(p['datos']['temporada'] == 1 and p['datos']['ganador']['nombre'] for p in pend)
    assert pend[0]['fecha_entrega'] == PR.fecha_entrega(e, 'balon_oro').isoformat()
    assert pend[1]['fecha_entrega'] == PR.fecha_entrega(e, 'sudamericano').isoformat()
    assert 'balon_oro' not in e['datos_carrera'] and 'sudamericano' not in e['datos_carrera']
    assert 'balon_oro_ultimo' not in e and not C.bandeja(e)
    print("  test_cerrar_temporada_deja_pendientes: OK")


def test_entrega_en_la_fecha_una_sola_vez():
    e = estado_carrera('premier'); e['temporada'] = 2
    hoy = T.fecha(e)
    _pendiente(e, 'balon_oro', (hoy + timedelta(days=1)).isoformat(), "Otro FC")
    assert PR.revisar_jornada(e) == 0 and 'balon_oro' not in e['datos_carrera']      # todavía no es la gala
    e['datos_carrera']['premios_pendientes'][0]['fecha_entrega'] = hoy.isoformat()
    assert PR.revisar_jornada(e) == 1
    assert e['datos_carrera']['balon_oro'][-1]['ganador']['nombre'] == "Uno Primero"
    from alpha_football import noticias as NO
    (n,) = NO.lista(e)                                         # v0.4.23.0: es una noticia, ya no un correo de Prensa
    assert (n['tipo'], n['importancia'], n['titular']) == ('premio', 5, "Balón de Oro: Uno Primero")
    assert n['accion'] == C.accion('career_screen', "VER PALMARÉS") and n in NO.para_feed(e)
    assert "Dos Segundo" in n['cuerpo'] and "Tres Tercero" in n['cuerpo']
    assert not e['datos_carrera'].get('gala_premio_pendiente') and not e.get('_parar_avance')   # nadie de tu club
    assert PR.revisar_jornada(e) == 0 and len(e['datos_carrera']['balon_oro']) == 1
    assert len(NO.lista(e)) == 1 and not C.bandeja(e)
    print("  test_entrega_en_la_fecha_una_sola_vez: OK")


def test_gala_solo_si_hay_alguien_de_tu_club():
    e = estado_carrera('premier'); e['temporada'] = 2; mi = e['mi_equipo']
    hoy = T.fecha(e).isoformat()
    _pendiente(e, 'sudamericano', hoy, "Otro FC", equipo_2=mi.nombre)                # tu jugador quedó 2º
    assert PR.revisar_jornada(e) == 1
    galas = e['datos_carrera']['gala_premio_pendiente']
    assert len(galas) == 1 and galas[0]['premio'] == 'sudamericano' and galas[0]['fecha'] == hoy
    assert galas[0]['tuyos'] == ["Dos Segundo"]                                      # a quién pinta de verde la gala
    assert e['_parar_avance'] is True
    assert e['datos_carrera']['sudamericano'][-1]['ganador']['nombre'] == "Uno Primero"
    from alpha_football import noticias as NO
    assert NO.lista(e)[0]['titular'] == "Jugador Sudamericano del Año: Uno Primero"
    print("  test_gala_solo_si_hay_alguien_de_tu_club: OK")


def test_gala_si_el_del_podio_ya_juega_en_tu_club():
    e = estado_carrera('premier'); e['temporada'] = 2; mi = e['mi_equipo']
    fichado = mi.jugadores[0].nombre_completo
    _pendiente(e, 'balon_oro', T.fecha(e).isoformat(), "Otro FC")                    # al cierre nadie era tuyo...
    e['datos_carrera']['premios_pendientes'][0]['datos']['podio'][1]['nombre'] = fichado   # ...y compraste al 2º
    assert PR.revisar_jornada(e) == 1
    galas = e['datos_carrera']['gala_premio_pendiente']
    assert len(galas) == 1 and galas[0]['tuyos'] == [fichado] and e['_parar_avance'] is True
    assert e['datos_carrera']['balon_oro'][-1]['podio'][1]['equipo'] == "Otro FC"    # el palmarés conserva su club
    print("  test_gala_si_el_del_podio_ya_juega_en_tu_club: OK")


def test_respaldo_al_cerrar_la_temporada_siguiente():
    e = estado_carrera('premier'); _jugados(e); e['temporada'] = 3; mi = e['mi_equipo']
    _pendiente(e, 'balon_oro', "2999-10-25", mi.nombre)                               # nadie lo entregó
    pend = PR.cerrar_temporada(e, e['primera_division'], e['segunda_division'], 2, {})
    assert e['datos_carrera']['balon_oro'][-1]['ganador']['nombre'] == "Uno Primero"  # entra al palmarés
    assert not e['datos_carrera'].get('gala_premio_pendiente')                        # sin gala atrasada
    assert [p['premio'] for p in pend] == ['balon_oro', 'sudamericano']
    assert all(p['datos']['temporada'] == 2 for p in pend)                            # sin duplicar el viejo
    print("  test_respaldo_al_cerrar_la_temporada_siguiente: OK")


def test_save_viejo_y_datos_danados():
    e = estado_carrera('premier')
    assert PR.revisar_jornada(e) == 0                                                 # sin la clave
    e['datos_carrera']['premios_pendientes'] = ["basura", {'premio': 'no_existe', 'fecha_entrega': "2000-01-01"},
                                                 {'premio': 'balon_oro', 'fecha_entrega': "2000-01-01", 'datos': {}}]
    PR.revisar_jornada(e)
    assert e['datos_carrera']['premios_pendientes'] == []
    assert not e['datos_carrera'].get('balon_oro') and not C.bandeja(e)
    assert PR.revisar_jornada({'datos_carrera': {'premios_pendientes': [{}]}}) == 0   # sin liga ni club
    print("  test_save_viejo_y_datos_danados: OK")


def test_pendientes_que_no_son_una_lista():
    e = estado_carrera('premier'); e['temporada'] = 2
    for basura in ("basura", {'premio': 'balon_oro', 'fecha_entrega': "2000-01-01"}, 7):
        e['datos_carrera']['premios_pendientes'] = basura
        assert PR.revisar_jornada(e) == 0, basura                                     # ni lanza ni entrega nada
        assert e['datos_carrera']['premios_pendientes'] == [], basura                 # y queda como lista
    assert not e['datos_carrera'].get('balon_oro') and not C.bandeja(e)
    print("  test_pendientes_que_no_son_una_lista: OK")


# ── Task 6: enganches ────────────────────────────────────────────────────────────

def test_el_reloj_entrega_el_dia_de_la_gala():
    from alpha_football import dias
    e = estado_carrera('premier'); e['temporada'] = 2; mi = e['mi_equipo']
    hoy = dias.hoy(e)                                             # crea el reloj
    _pendiente(e, 'balon_oro', hoy.isoformat(), mi.nombre)
    assert dias.revisar_dia(e, hoy) is not False                  # devuelve el hito del día (o None)
    assert e['datos_carrera']['balon_oro'][-1]['ganador']['equipo'] == mi.nombre
    assert e['datos_carrera']['premios_pendientes'] == [] and e['datos_carrera']['gala_premio_pendiente']
    print("  test_el_reloj_entrega_el_dia_de_la_gala: OK")


def test_frenar_false_entrega_y_deja_la_gala_sin_frenar():
    e = estado_carrera('premier'); e['temporada'] = 2; mi = e['mi_equipo']
    _pendiente(e, 'balon_oro', T.fecha(e).isoformat(), "Otro FC", equipo_2=mi.nombre)
    assert PR.revisar_jornada(e, frenar=False) == 1                           # entrega igual...
    assert len(e['datos_carrera']['gala_premio_pendiente']) == 1              # ...deja la gala para el hub...
    assert '_parar_avance' not in e                                           # ...y no frena a CONTINUAR
    assert e['datos_carrera']['balon_oro'][-1]['ganador']['nombre'] == "Uno Primero"
    print("  test_frenar_false_entrega_y_deja_la_gala_sin_frenar: OK")


def test_cerrar_un_partido_no_deja_frenado_el_siguiente_continuar():
    from alpha_football.ui.match_screen import finalizar_jornada_liga
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    e = estado_carrera('premier'); mi, liga = e['mi_equipo'], e['liga']
    inicializar_calendario_liga(liga)
    _pendiente(e, 'sudamericano', "2000-01-15", mi.nombre)                    # ya vencido: lo entrega el cierre
    p = next(p for p in liga.calendario if p.jornada == 1 and mi.id in (p.local_id, p.visitante_id))
    finalizar_jornada_liga(e, liga, mi, p, 1, 0)
    assert e['datos_carrera']['premios_pendientes'] == [] and e['datos_carrera']['gala_premio_pendiente']
    assert '_parar_avance' not in e                    # la marca es del reloj: aquí frenaría un día después
    print("  test_cerrar_un_partido_no_deja_frenado_el_siguiente_continuar: OK")


# ── Task 7: pantallas ────────────────────────────────────────────────────────────

def test_gala_screen_flujo():
    from alpha_football.ui import gala_balon_screen as G
    e = estado_carrera('premier'); mi = e['mi_equipo']
    e['datos_carrera']['gala_premio_pendiente'] = [
        {'premio': 'balon_oro', 'fecha': "2027-10-25", 'datos': _datos(mi.nombre)},
        {'premio': 'sudamericano', 'fecha': "2028-01-15", 'datos': _datos("Otro FC", equipo_2=mi.nombre)}]
    pygame.event.clear(); assert G.render(screen, e) is None                  # se queda en la gala
    assert len(e['datos_carrera']['gala_premio_pendiente']) == 2
    key(pygame.K_RETURN); assert G.render(screen, e) is None                   # pasa a la segunda
    assert [g['premio'] for g in e['datos_carrera']['gala_premio_pendiente']] == ['sudamericano']
    key(pygame.K_RETURN); assert G.render(screen, e) == 'league_screen'
    assert e['datos_carrera']['gala_premio_pendiente'] == []
    print("  test_gala_screen_flujo: OK")


def test_gala_screen_no_se_traba():
    from alpha_football.ui import gala_balon_screen as G
    e = estado_carrera('premier')
    pygame.event.clear(); assert G.render(screen, e) == 'league_screen'        # sin galas
    e['datos_carrera']['gala_premio_pendiente'] = ["basura", {'premio': 'balon_oro'}, {'datos': {'ganador': {}}}]
    pygame.event.clear(); assert G.render(screen, e) == 'league_screen'        # datos dañados: se descartan
    assert e['datos_carrera']['gala_premio_pendiente'] == []
    e['datos_carrera']['gala_premio_pendiente'] = [{'premio': 'otro', 'fecha': "ayer",
                                                    'datos': {'ganador': {'nombre': "X"}}}]
    pygame.event.clear(); assert G.render(screen, e) is None                   # incompleta pero dibujable
    print("  test_gala_screen_no_se_traba: OK")


def _colores_gala(e):
    """{texto dibujado: color} de la gala que está en pantalla (espía el draw_text de la pantalla)."""
    from alpha_football.ui import gala_balon_screen as G
    vistos, orig = {}, G.draw_text

    def espia(scr, txt, pos, **k):
        vistos[txt] = k.get('color')
        return orig(scr, txt, pos, **k)
    G.draw_text = espia
    try:
        pygame.event.clear(); assert G.render(screen, e) is None
    finally:
        G.draw_text = orig
    return vistos


def test_gala_screen_pinta_de_verde_a_los_tuyos():
    e = estado_carrera('premier'); mi = e['mi_equipo']
    de = lambda c, nombre: next(col for t, col in c.items() if nombre in t)
    gala = {'premio': 'balon_oro', 'fecha': "2027-10-25", 'datos': _datos("Otro FC"), 'tuyos': ["Dos Segundo"]}
    e['datos_carrera']['gala_premio_pendiente'] = [gala]
    c = _colores_gala(e)                               # con 'tuyos' manda el nombre, no el club del cierre
    assert (de(c, "Uno Primero"), de(c, "Dos Segundo"), de(c, "Tres Tercero")) == ('blanco', 'verde', 'blanco')
    del gala['tuyos']; gala['datos'] = _datos(mi.nombre)
    c = _colores_gala(e)                               # gala guardada sin la clave: por club, como antes
    assert (de(c, "Uno Primero"), de(c, "Dos Segundo")) == ('verde', 'blanco')
    gala['tuyos'] = 7
    c = _colores_gala(e)                               # 'tuyos' dañado: no rompe ni descarta la gala
    assert de(c, "Uno Primero") == 'verde' and e['datos_carrera']['gala_premio_pendiente'] == [gala]
    print("  test_gala_screen_pinta_de_verde_a_los_tuyos: OK")


def test_hub_abre_la_gala_y_esta_registrada():
    orig_get = pygame.event.get                      # main reemplaza pygame.event.get al importarse
    try:
        import main
    finally:
        pygame.event.get = orig_get
    assert 'gala_balon_screen' in main.nombres_pantallas() and 'gala_balon_screen' in main.SIN_ATAJOS_GLOBALES
    from alpha_football.ui import league_screen as L, atajos as A, ayuda as AY
    assert 'gala_balon_screen' in A.ATAJOS and len(AY.items('gala_balon_screen', {})) >= 3
    e = estado_carrera('premier')
    e['datos_carrera']['gala_premio_pendiente'] = [{'premio': 'balon_oro', 'fecha': "2027-10-25",
                                                    'datos': _datos(e['mi_equipo'].nombre)}]
    pygame.event.clear(); assert L.render(screen, e) == 'gala_balon_screen'
    print("  test_hub_abre_la_gala_y_esta_registrada: OK")


def test_ascensos_sin_balon_y_palmares_doble():
    from alpha_football.ui import promo_releg_screen as P, career_screen as K, ayuda as AY
    assert 'balon' not in P.rects_promo()
    e = estado_carrera('premier')
    assert not any(t == "Balón de Oro" for _r, t, _x in AY.items('promo_releg_screen', e))
    e['promo_releg_data'] = {'ascendidos': [], 'descendidos': []}
    pygame.event.clear(); assert P.render(screen, e) is None                   # dibuja sin la caja
    e['datos_carrera']['balon_oro'] = [_datos("A", temporada=t) for t in (1, 2, 3, 4)]
    e['datos_carrera']['sudamericano'] = [_datos("B", temporada=1)]
    pal = K.palmares(e)
    assert [t for t, _l in pal] == ["BALÓN DE ORO", "SUDAMERICANO DEL AÑO"]
    assert [b['temporada'] for b in pal[0][1]] == [4, 3, 2] and [b['temporada'] for b in pal[1][1]] == [1]
    pygame.event.clear(); assert K.render(screen, e) is None
    assert K.palmares({'datos_carrera': {}}) == [("BALÓN DE ORO", []), ("SUDAMERICANO DEL AÑO", [])]
    print("  test_ascensos_sin_balon_y_palmares_doble: OK")


TESTS = [test_fechas_de_gala, test_sudamericano_solo_ligas_sudamericanas, test_cerrar_temporada_deja_pendientes,
         test_entrega_en_la_fecha_una_sola_vez, test_gala_solo_si_hay_alguien_de_tu_club,
         test_gala_si_el_del_podio_ya_juega_en_tu_club, test_respaldo_al_cerrar_la_temporada_siguiente,
         test_save_viejo_y_datos_danados, test_pendientes_que_no_son_una_lista,
         test_el_reloj_entrega_el_dia_de_la_gala, test_frenar_false_entrega_y_deja_la_gala_sin_frenar,
         test_cerrar_un_partido_no_deja_frenado_el_siguiente_continuar,
         test_gala_screen_flujo, test_gala_screen_no_se_traba, test_gala_screen_pinta_de_verde_a_los_tuyos,
         test_hub_abre_la_gala_y_esta_registrada, test_ascensos_sin_balon_y_palmares_doble]

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
