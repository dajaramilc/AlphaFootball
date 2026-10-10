"""v0.4.21.0: los rematados de un club quebrado esperan 7 días (el user puede ficharlos antes que la IA)
y la bolsa de agentes libres es real: se guarda, se alimenta de los que la IA suelta y la IA también ficha."""
import sys, os, random
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(421)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import finanzas as F, mercado_ia as MI, negociacion as N, correo as C, save
from alpha_football.data.free_agents import NOMBRES_LIBRES
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams

save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales
RICO = 10**10
PARODIAS = {f"{n} {a}" for n, a in NOMBRES_LIBRES}


def estado_chico():
    """Una sola liga (Premier): las rondas de la IA corren en segundos."""
    liga = load_league_teams('premier')
    mi = liga.equipos[0]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    e = {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
         'alineacion_activa': mi.alineacion_activa, 'primera_division': {'premier': liga},
         'segunda_division': {}, 'datos_carrera': {'libres_editor': []}, 'historial': []}   # sin los libres de tu base editada
    F.asegurar_contratos(e)
    for c in liga.equipos:
        c.balance = RICO
    return e


def _rival(e):
    """Un club de la IA de tu liga que no es tu clásico."""
    from alpha_football.data.clasicos import es_clasico
    return next(c for c in e['liga'].equipos[1:] if not es_clasico(c, e['mi_equipo']))


def _prensa(e):
    """v0.4.23.0: las quiebras y los remates son noticias de economía (ya no correos de Prensa)."""
    from alpha_football import noticias as NO
    assert not [m for m in e['datos_carrera'].get('correo', []) if m['remitente'] == 'prensa']
    return [n for n in NO.lista(e) if n['tipo'] == 'economia']


def _vencer(e):
    for r in e['datos_carrera']['remates']:
        r['vence'] = '2000-01-01'


def _soltar(e, club, j, desde=None):
    club.jugadores.remove(j)
    club.alineacion_activa = None
    N.liberar(e, j, desde)


# ---------------------------------------------------------------- 1: remates con plazo
def test_la_quiebra_deja_a_las_figuras_en_remate_con_plazo():
    e = estado_chico(); eq = _rival(e)
    tops = sorted(eq.jugadores, key=lambda j: -j.overall)[:3]
    rem = MI.quiebra_ia(e, eq, random.Random(1))
    assert 2 <= len(rem) <= 3
    assert all(j in eq.jugadores and j.remate and j in tops for j, _comp, _p in rem)      # nadie se fue todavía
    vence = (date.fromisoformat(C._hoy_iso(e)) + timedelta(days=MI.DIAS_REMATE)).isoformat()
    pend = e['datos_carrera']['remates']
    assert [(r['club'], r['jugador'], r['vence']) for r in pend] == [(eq.nombre, j.nombre_completo, vence) for j, _c, _p in rem]
    noticia = _prensa(e)[-1]
    assert eq.nombre in noticia['titular'] and all(j.apellido in noticia['cuerpo'] for j, _c, _p in rem)
    assert noticia['importancia'] == 4 and noticia['accion'] == C.accion('buscador_screen', "VER BUSCADOR")
    from alpha_football.calendario import texto_fecha
    assert texto_fecha(date.fromisoformat(vence)) in noticia['cuerpo']
    print("  test_la_quiebra_deja_a_las_figuras_en_remate_con_plazo: OK")


def test_en_tu_cierre_el_plazo_corre_desde_el_inicio_de_la_temporada_nueva():
    from alpha_football import temporada as T
    e = estado_chico(); eq = _rival(e)
    inicio = T.inicio(e)
    # al cerrar tu temporada el reloj todavía marca un día de la que termina
    e['datos_carrera']['calendario'] = {'dia': (inicio - timedelta(days=40)).isoformat()}
    MI.quiebra_ia(e, eq, random.Random(1))
    vence = (inicio + timedelta(days=MI.DIAS_REMATE)).isoformat()
    assert {r['vence'] for r in e['datos_carrera']['remates']} == {vence}
    print("  test_en_tu_cierre_el_plazo_corre_desde_el_inicio_de_la_temporada_nueva: OK")


def test_antes_del_plazo_no_se_los_lleva_nadie():
    e = estado_chico(); eq = _rival(e)
    rem = MI.quiebra_ia(e, eq, random.Random(1))
    assert MI.resolver_remates(e, random.Random(1)) == []
    MI.ronda_fichajes_ia(e, 'pretemporada', random.Random(2))
    assert all(j in eq.jugadores and j.remate for j, _c, _p in rem)
    assert len(e['datos_carrera']['remates']) == len(rem)
    print("  test_antes_del_plazo_no_se_los_lleva_nadie: OK")


def test_el_user_ficha_a_un_rematado_aunque_el_club_este_en_el_minimo():
    e = estado_chico(); eq = _rival(e); mi = e['mi_equipo']
    rem = MI.quiebra_ia(e, eq, random.Random(1))
    j = rem[0][0]
    quedan = [x for x, _c, _p in rem] + [x for x in eq.jugadores if not x.remate]
    eq.jugadores[:] = quedan[:MI.PLANTILLA_MIN_IA]
    precio = N.precio_fichaje(j)
    assert precio < int(j.clausula)
    assert N.evaluar_compra(e, j, eq, precio)[0] == 'acepta'
    ok, msg = N.fichar(e, j, eq, precio)
    assert ok, msg
    assert j in mi.jugadores and not j.remate
    print("  test_el_user_ficha_a_un_rematado_aunque_el_club_este_en_el_minimo: OK")


def test_vencido_el_plazo_la_ia_se_lleva_a_los_que_el_user_no_ficho():
    e = estado_chico(); eq = _rival(e); mi = e['mi_equipo']
    rem = MI.quiebra_ia(e, eq, random.Random(1))
    mio, resto = rem[0][0], [j for j, _c, _p in rem[1:]]
    ok, msg = N.fichar(e, mio, eq, N.precio_fichaje(mio))
    assert ok, msg
    _vencer(e)
    antes = len(_prensa(e))
    vendidos = MI.resolver_remates(e, random.Random(1))
    assert [j for j, _comp, _p in vendidos] == resto and all(comp is not None for _j, comp, _p in vendidos)
    assert all(j not in eq.jugadores and j not in mi.jugadores and not j.remate for j in resto)
    assert all(j in comp.jugadores for j, comp, _p in vendidos) and mio in mi.jugadores
    assert e['datos_carrera']['remates'] == []
    noticia = next(m for m in _prensa(e) if m['titular'] == f"Remate de {eq.nombre}")
    assert noticia['importancia'] == 3 and noticia['accion']['pantalla'] == 'buscador_screen'
    assert len(_prensa(e)) == antes + 1 and all(j.apellido in noticia['cuerpo'] for j in resto)
    assert mio.apellido not in noticia['cuerpo']
    print("  test_vencido_el_plazo_la_ia_se_lleva_a_los_que_el_user_no_ficho: OK")


def test_el_rematado_sin_comprador_sigue_en_remate():
    e = estado_chico(); eq = _rival(e)
    rem = MI.quiebra_ia(e, eq, random.Random(1))
    for c in e['liga'].equipos:
        c.balance = 0                                  # nadie puede pagar
    _vencer(e)
    assert all(comp is None for _j, comp, _p in MI.resolver_remates(e, random.Random(1)))
    assert all(j in eq.jugadores and j.remate for j, _c, _p in rem)
    assert e['datos_carrera']['remates'] == []
    print("  test_el_rematado_sin_comprador_sigue_en_remate: OK")


# ---------------------------------------------------------------- 2: la bolsa de libres
def test_la_bolsa_de_libres_se_guarda_y_se_carga():
    e = estado_chico(); eq = _rival(e)
    j = eq.jugadores[-1]
    _soltar(e, eq, j)
    guardado = save.campos_divisiones(e)['datos_carrera']
    assert [d['apellido'] for d in guardado['libres']] == [j.apellido]
    e2 = {'temporada': 1, 'datos_carrera': guardado}
    N.cargar_libres(e2)
    cargados = N.libres_reales(e2)
    assert [(x.nombre_completo, x.overall, x.libre_desde) for x in cargados] == [(j.nombre_completo, j.overall, 1)]
    print("  test_la_bolsa_de_libres_se_guarda_y_se_carga: OK")


def test_guardar_sin_haber_abierto_la_bolsa_no_la_borra():
    e = {'temporada': 1, 'datos_carrera': {'libres': [{'nombre': 'A', 'apellido': 'B'}]}}
    assert save.campos_divisiones(e)['datos_carrera']['libres'] == [{'nombre': 'A', 'apellido': 'B'}]
    print("  test_guardar_sin_haber_abierto_la_bolsa_no_la_borra: OK")


def test_el_relleno_es_el_mismo_toda_la_temporada():
    e = estado_chico(); liga = e['liga']

    def foto():
        return sorted((j.nombre_completo, j.posicion, j.overall, j.edad) for j in N.asegurar_agentes_libres(e))
    antes = foto()
    assert len(antes) == N.MIN_LIBRES and {x[0] for x in antes} <= PARODIAS
    liga.jornada_actual += 1
    assert foto() == antes
    print("  test_el_relleno_es_el_mismo_toda_la_temporada: OK")


def test_con_la_bolsa_llena_no_hay_relleno():
    e = estado_chico(); eq = _rival(e); liga = e['liga']
    sueltos = []
    for c in liga.equipos[1:N.MIN_LIBRES + 2]:
        sueltos.append(c.jugadores[-1]); _soltar(e, c, c.jugadores[-1])
    lista = N.asegurar_agentes_libres(e)
    assert sorted(j.nombre_completo for j in lista) == sorted(j.nombre_completo for j in sueltos)
    liga.jornada_actual += 1
    assert sorted(j.nombre_completo for j in N.asegurar_agentes_libres(e)) == sorted(j.nombre_completo for j in sueltos)
    print("  test_con_la_bolsa_llena_no_hay_relleno: OK")


def test_los_sobrantes_de_la_ia_van_a_la_bolsa():
    e = estado_chico(); eq, otro = e['liga'].equipos[3], e['liga'].equipos[4]
    eq.jugadores += otro.jugadores[:7]
    del otro.jugadores[:7]
    sobran = len(eq.jugadores) - MI.PLANTILLA_MAX_IA
    assert sobran > 0
    MI._liberar_sobrantes(eq, e)
    libres = N.libres_reales(e)
    assert len(eq.jugadores) == MI.PLANTILLA_MAX_IA and len(libres) == sobran
    assert all(j not in eq.jugadores and j.libre_desde == 1 for j in libres)
    print("  test_los_sobrantes_de_la_ia_van_a_la_bolsa: OK")


def test_al_cierre_quedan_libres_suplentes_veteranos_de_la_ia():
    from alpha_football.formaciones import mejor_once
    e = estado_chico(); e['temporada'] = 2; mi = e['mi_equipo']
    for j in mi.jugadores:
        j.contrato_anios = 5                           # los tuyos no entran en esta prueba
    onces, veteranos = set(), set()
    for c in e['liga'].equipos[1:]:
        onces |= {id(c.jugadores[i]) for i in mejor_once(c.jugadores, "4-3-3")}
        for k, j in enumerate(c.jugadores):
            j.contrato_anios = 1                       # a todos se les acaba
            j.edad = 30 if k % 2 else 22
            if j.edad >= F.EDAD_LIBRE_IA:
                veteranos.add(id(j))
    F.cierre_temporada(e)
    libres = [j for j in N.libres_reales(e)]
    assert libres
    assert all(id(j) in veteranos and id(j) not in onces and j.libre_desde == 1 for j in libres)
    assert all(len(c.jugadores) >= MI.PLANTILLA_MIN_VENDEDOR for c in e['liga'].equipos if c is not mi)
    assert not any(j in c.jugadores for j in libres for c in e['liga'].equipos)
    print("  test_al_cierre_quedan_libres_suplentes_veteranos_de_la_ia: OK")


def test_tras_una_temporada_entera_sin_club_se_retiran():
    e = estado_chico(); eq = _rival(e)
    viejo, nuevo = eq.jugadores[-1], eq.jugadores[-2]
    _soltar(e, eq, viejo, 1)
    _soltar(e, eq, nuevo, 2)
    e['temporada'] = 3                                 # se cierra la temporada 2
    for c in e['liga'].equipos:
        for j in c.jugadores:
            j.contrato_anios = 5                       # nadie más queda libre
    F.cierre_temporada(e)
    assert N.libres_reales(e) == [nuevo]
    print("  test_tras_una_temporada_entera_sin_club_se_retiran: OK")


def test_la_ia_ficha_a_un_agente_libre_que_le_sirve():
    e = estado_chico(); liga = e['liga']
    origen, corto = liga.equipos[5], liga.equipos[6]
    crack = max(origen.jugadores, key=lambda j: j.overall)
    _soltar(e, origen, crack)
    del corto.jugadores[21:]                           # plantilla corta: busca fondo de armario
    corto.alineacion_activa = None
    MI.ronda_fichajes_ia(e, 'pretemporada', random.Random(2))
    club = next((c for c in liga.equipos[1:] if crack in c.jugadores), None)
    assert club is not None and crack not in N.libres_reales(e)
    assert crack.salario > 0 and crack.contrato_anios >= 1 and not getattr(crack, 'fin_de_contrato', False)
    pase = next(h for h in N.historial(e, propio=False) if h['jugador'] == f"{crack.nombre} {crack.apellido}")
    assert pase['de'] == N.LIBRES_PASE and pase['a'] == club.nombre and pase['monto'] == 0
    print("  test_la_ia_ficha_a_un_agente_libre_que_le_sirve: OK")


def test_la_ia_no_se_lleva_al_libre_que_negocia_contigo():
    e = estado_chico(); liga = e['liga']
    origen = liga.equipos[5]
    crack = max(origen.jugadores, key=lambda j: j.overall)
    _soltar(e, origen, crack)
    e['datos_carrera']['analisis_contratos'] = [{'club_id': None, 'jugador_id': crack.id, 'jugador': crack.nombre_completo}]
    for semilla in range(2, 5):
        MI.ronda_fichajes_ia(e, 'pretemporada', random.Random(semilla))
    assert crack in N.libres_reales(e)
    print("  test_la_ia_no_se_lleva_al_libre_que_negocia_contigo: OK")


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
