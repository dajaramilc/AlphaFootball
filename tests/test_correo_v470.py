"""v4.7.0: correos formales (saludo y firma), borrar correo, limpieza al empezar la temporada,
despedidas de los retirados, correo de objetivos, final de copa al cierre y arreglos de v4.6.0."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(47)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import correo as C, save
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1, 'dt_nombre': 'Diego Jaramillo',
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


def _click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


# ---------------------------------------------------------------- formato, borrar y limpieza
def test_formato_formal_por_remitente():
    e = estado_carrera(); club = e['mi_equipo'].nombre
    m = C.enviar(e, 'directiva', "Asunto", "Texto del cuerpo.")
    t = C.formatear(e, m)
    assert t.startswith("Estimado míster Jaramillo:") and "Texto del cuerpo." in t
    assert t.rstrip().endswith(f"La Directiva de {club}")
    otro = C.enviar(e, 'club', "Oferta", "Te queremos.", firma="La Directiva del Otro FC")
    assert C.formatear(e, otro).rstrip().endswith("La Directiva del Otro FC")
    j = C.enviar(e, 'jugador', "Hola", "Míster, gracias por todo.")
    assert C.formatear(e, j) == "Míster, gracias por todo."          # los jugadores escriben a su manera
    print("  test_formato_formal_por_remitente: OK")


def test_envolver_respeta_parrafos():
    from alpha_football.ui.correo_screen import _envolver
    lineas = _envolver("Hola:\n\nPárrafo uno.\nPárrafo dos.", 600)
    assert lineas == ["Hola:", "", "Párrafo uno.", "Párrafo dos."]
    print("  test_envolver_respeta_parrafos: OK")


def test_borrar_correo_con_boton_y_tecla():
    from alpha_football.ui import correo_screen as CS
    e = estado_carrera()
    for i in range(3):
        C.enviar(e, 'directiva', f"Aviso {i}", "x")
    e['correo_sel'] = 0
    pygame.event.clear(); CS.render(screen, e)
    _click(CS.R_BORRAR.center); CS.render(screen, e)
    assert [m['asunto'] for m in C.bandeja(e)] == ["Aviso 1", "Aviso 0"]
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DELETE, mod=0, unicode=''))
    CS.render(screen, e)
    assert [m['asunto'] for m in C.bandeja(e)] == ["Aviso 0"]
    print("  test_borrar_correo_con_boton_y_tecla: OK")


def test_limpiar_temporada_anterior():
    e = estado_carrera()
    C.enviar(e, 'directiva', "Viejo", "x")
    e['temporada'] = 2
    C.enviar(e, 'directiva', "Nuevo", "x")
    C.limpiar_temporadas_anteriores(e)
    assert [m['asunto'] for m in C.bandeja(e)] == ["Nuevo"]
    print("  test_limpiar_temporada_anterior: OK")


# ---------------------------------------------------------------- despedidas y objetivos
class _Siempre(random.Random):
    def random(self):
        return 0.0


def test_retirado_se_despide():
    from alpha_football import retiros as R
    e = estado_carrera(); mi = e['mi_equipo']
    viejo = mi.jugadores[0]; viejo.edad = 40
    nombre = viejo.nombre_completo
    R.procesar_retiros(e, _Siempre(1))
    carta = next(m for m in C.bandeja(e) if m['remitente'] == 'jugador' and nombre in m['cuerpo'] + m['asunto'])
    assert len(carta['cuerpo']) > 200 and mi.nombre in carta['cuerpo']
    print("  test_retirado_se_despide: OK")


def test_correo_de_objetivos_una_vez():
    from alpha_football import directiva as D
    e = estado_carrera()
    D.definir_objetivo(e); D.definir_objetivo(e)
    objs = [m for m in C.bandeja(e) if m['asunto'].startswith("Objetivos de la temporada")]
    assert len(objs) == 1 and C.bandeja(e)[0] is objs[0]
    cuerpo = objs[0]['cuerpo']
    assert 'tope' in cuerpo.lower() and 'saldo' in cuerpo.lower()
    assert objs[0]['accion']['pantalla'] == 'objetivos_screen'
    print("  test_correo_de_objetivos_una_vez: OK")


# ---------------------------------------------------------------- final de copa al cierre
def test_final_despues_de_la_ultima_jornada():
    from alpha_football import competiciones as CP
    for n, J in ((17, 22), (13, 22), (13, 38)):
        fechas = [CP.jornada_de_fecha(i, n, J) for i in range(n)]
        assert fechas[-1] == J and max(fechas[:-1]) <= J - 1
    e = estado_carrera()
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    liga = e['liga']; inicializar_calendario_liga(liga)
    liga.jornada_actual = liga.num_jornadas
    assert CP._jornada_actual(e) == liga.num_jornadas
    for p in liga.calendario:
        p.jugado = True
    assert CP._jornada_actual(e) == liga.num_jornadas + 1          # liga terminada: vence la final
    print("  test_final_despues_de_la_ultima_jornada: OK")


# ---------------------------------------------------------------- arreglos de v4.6.0
def test_totales_de_carrera_sin_doble_temporada():
    from alpha_football.ui.career_screen import _resumen_historial
    hist = [{'temporada': 1, 'pts': 20, 'gf': 10, 'gc': 5, 'pos': 5, 'se_fue': True},
            {'temporada': 1, 'pts': 15, 'gf': 8, 'gc': 4, 'pos': 3}]
    tot = _resumen_historial(hist)
    assert tot['temporadas'] == 1 and tot['pts'] == 35
    print("  test_totales_de_carrera_sin_doble_temporada: OK")


def test_puntos_del_club_nuevo_desde_que_llegaste():
    from alpha_football import ofertas_dt as O, directiva as D
    e = estado_carrera(); nuevo = e['liga'].equipos[3]
    nuevo.puntos, nuevo.gf, nuevo.gc = 12, 9, 6
    e['datos_carrera']['oferta_dt'] = {'club_id': nuevo.id, 'club': nuevo.nombre, 'liga': '', 'media': 70,
                                       'temporada': 1, 'vence': 99}
    O.aceptar(e)
    nuevo.puntos, nuevo.gf, nuevo.gc = 30, 20, 10
    assert O.desde_llegada(e, nuevo) == {'pts': 18, 'gf': 11, 'gc': 4}
    print("  test_puntos_del_club_nuevo_desde_que_llegaste: OK")


def test_sin_correo_de_rojo_si_ya_te_echaron():
    from alpha_football import finanzas as F, directiva as D
    e = estado_carrera(); mi = e['mi_equipo']
    for j in mi.jugadores:
        j.contrato_anios = 3
    D.marcar_despido(e, "No cumpliste.", indemnizar=False)
    mi.balance = -1
    F.cierre_temporada(e)
    assert not any('rojo' in m['asunto'].lower() for m in C.bandeja(e))
    print("  test_sin_correo_de_rojo_si_ya_te_echaron: OK")


def test_una_sola_oferta_de_club_a_la_vez():
    from alpha_football import ofertas_dt as O, directiva as D, entrenadores as EN
    e = estado_carrera()
    EN.dts(e)['ofertas'].append({'club_id': 'x', 'club': 'Otro', 'liga': '', 'jornadas': 3, 'temporada': 1})
    orig = D._jugadas
    D._jugadas = lambda l, m: 3
    try:
        from alpha_football.ui.league_screen import inicializar_calendario_liga
        inicializar_calendario_liga(e['liga'])
        e['datos_carrera']['calif_dt'] = 80
        O.revisar_jornada(e, _Siempre(2))
        assert O.oferta_vigente(e) is None                         # ya hay una de banquillo
        EN.dts(e)['ofertas'].clear()
        O.revisar_jornada(e, _Siempre(3))
        assert O.oferta_vigente(e) is not None
        assert not EN.puede_ofrecer_al_user(e)                     # y al revés
    finally:
        D._jugadas = orig
    print("  test_una_sola_oferta_de_club_a_la_vez: OK")


def test_migracion_cubre_fichajes_pendientes():
    from alpha_football import finanzas as F
    e = estado_carrera(); F.asegurar_contratos(e)
    e['datos_carrera']['traspasos_pendientes'] = [{'tipo': 'compra', 'jugador': 'X', 'datos': {'salario': 1_000_000}}]
    e['datos_carrera']['contratos_v290'] = True
    F.migrar_economia(e)
    assert e['datos_carrera']['traspasos_pendientes'][0]['datos']['salario'] == 1_600_000
    print("  test_migracion_cubre_fichajes_pendientes: OK")


TESTS = [f for n, f in list(globals().items()) if n.startswith('test_') and callable(f)]


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
