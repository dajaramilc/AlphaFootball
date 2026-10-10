"""v0.4.23.0: rumores de mercado 60/40 (los reales se cumplen, el humo se desmiente o se apaga)."""
import sys, os, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(423)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import finanzas as F, mercado_ia as MI, noticias as N, rumores as R, correo as C, save
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams

save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales
RICO = 10**10
CLAVES = {'id', 'clase', 'jugador_id', 'jugador', 'origen', 'destino', 'precio', 'real', 'vence', 'noticia_id'}


class RngFijo(random.Random):
    """random() siempre devuelve `v`."""
    def __init__(self, v): super().__init__(1); self.v = v
    def random(self): return self.v


def estado_chico():
    """Una sola liga (Premier), con dinero de sobra."""
    liga = load_league_teams('premier')
    mi = liga.equipos[0]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    e = {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
         'alineacion_activa': mi.alineacion_activa, 'primera_division': {'premier': liga},
         'segunda_division': {}, 'datos_carrera': {'libres_editor': []}, 'historial': []}
    F.asegurar_contratos(e)
    for c in liga.equipos:
        c.balance = RICO
    return e


def _revisar(e, v=0.99, abierto=True, nuevos=False):
    """Una jornada de rumores con random() fijo en `v` (0.99: sin desmentidos) y el mercado abierto o cerrado
    a mano; sin `nuevos`, no nace ningún rumor."""
    prob, mercado = R.PROB_RUMOR, R._mercado_abierto
    R.PROB_RUMOR = 1.0 if nuevos else -1.0
    R._mercado_abierto = lambda estado: abierto
    try:
        R.revisar_jornada(e, RngFijo(v))
    finally:
        R.PROB_RUMOR, R._mercado_abierto = prob, mercado


def _rumor(e, clase='ia', real=True, vence=1, semilla=5):
    r = R.generar(e, random.Random(semilla), clase=clase)
    assert r is not None and r['clase'] == clase
    r['real'], r['vence'] = real, vence
    return r


def _club(e, nombre):
    return next(c for c in e['liga'].equipos if c.nombre == nombre)


def _jugador(club, r):
    return next((j for j in club.jugadores if j.id == r['jugador_id'] and j.nombre_completo == r['jugador']), None)


def _fichajes(e):
    return [n for n in N.lista(e) if n['tipo'] == 'fichaje']


def test_generar_publica_el_rumor():
    e = estado_chico()
    r = R.generar(e, random.Random(5), clase='ia')
    assert set(r) == CLAVES and r['clase'] == 'ia' and isinstance(r['real'], bool) and 1 <= r['vence'] <= 3
    origen, destino = _club(e, r['origen']), _club(e, r['destino'])
    j = _jugador(origen, r)
    assert j is not None and origen is not e['mi_equipo'] and destino is not e['mi_equipo'] and origen is not destino
    assert 0 < r['precio'] <= destino.balance and R.vivos(e) == [r]
    (n,) = N.lista(e)
    assert n['id'] == r['noticia_id'] and n['tipo'] == 'rumor' and 2 <= n['importancia'] <= 4
    assert n['jugadores_ids'] == [j.id] and n['equipos_ids'] == [destino.id, origen.id]
    assert len(n['titular']) <= 60 and j.apellido in n['titular'] and destino.nombre in n['cuerpo']
    print("  test_generar_publica_el_rumor: OK")


def test_rumor_real_ejecuta_el_traspaso():
    e = estado_chico()
    r = _rumor(e, real=True, vence=1)
    origen, destino = _club(e, r['origen']), _club(e, r['destino'])
    j = _jugador(origen, r)
    saldo_o, saldo_d = origen.balance, destino.balance
    _revisar(e)
    assert j in destino.jugadores and j not in origen.jugadores and R.vivos(e) == []
    assert (origen.balance, destino.balance) == (saldo_o + r['precio'], saldo_d - r['precio'])
    (n,) = _fichajes(e)                                        # la noticia de confirmación
    assert n['titular'].startswith("Confirmado: ") and n['jugadores_ids'] == [j.id]
    h = e['datos_carrera']['historial_pases'][-1]
    assert (h['jugador'], h['de'], h['a'], h['monto']) == (r['jugador'], origen.nombre, destino.nombre, r['precio'])
    print("  test_rumor_real_ejecuta_el_traspaso: OK")


def test_rumor_humo_no_mueve_a_nadie():
    for v, desmentidos in ((0.0, 1), (0.99, 0)):               # 50 %: lo desmiente / desaparece sin más
        e = estado_chico()
        r = _rumor(e, real=False, vence=1)
        origen, destino = _club(e, r['origen']), _club(e, r['destino'])
        j = _jugador(origen, r)
        saldos = origen.balance, destino.balance
        _revisar(e, v)
        assert j in origen.jugadores and j not in destino.jugadores and R.vivos(e) == []
        assert (origen.balance, destino.balance) == saldos and _fichajes(e) == []
        assert not e['datos_carrera'].get('historial_pases')
        nuevos = [n for n in N.lista(e) if n['id'] != r['noticia_id']]
        assert len(nuevos) == desmentidos and all(n['tipo'] == 'rumor' and "desm" in n['titular'].lower() for n in nuevos)
    print("  test_rumor_humo_no_mueve_a_nadie: OK")


def test_jugador_ya_no_esta_se_resuelve_como_humo():
    for caso in ('vendido', 'tuyo', 'retirado'):
        e = estado_chico()
        r = _rumor(e, real=True, vence=1)
        origen, destino = _club(e, r['origen']), _club(e, r['destino'])
        j = _jugador(origen, r)
        origen.jugadores.remove(j)
        otro = next(c for c in e['liga'].equipos[1:] if c not in (origen, destino))
        if caso != 'retirado':
            (otro if caso == 'vendido' else e['mi_equipo']).jugadores.append(j)
        saldo = destino.balance
        _revisar(e)                                            # sin excepción
        assert j not in destino.jugadores and destino.balance == saldo and R.vivos(e) == [], caso
        assert _fichajes(e) == [] and not e['datos_carrera'].get('historial_pases'), caso
    print("  test_jugador_ya_no_esta_se_resuelve_como_humo: OK")


def test_comprador_sin_dinero_no_ejecuta():
    for caso in ('sin_dinero', 'plantilla_llena', 'vendedor_en_el_minimo', 'cedido'):
        e = estado_chico()
        r = _rumor(e, real=True, vence=1)
        origen, destino = _club(e, r['origen']), _club(e, r['destino'])
        j = _jugador(origen, r)
        if caso == 'sin_dinero':
            destino.balance = r['precio'] - 1
        elif caso == 'plantilla_llena':
            destino.jugadores.extend([destino.jugadores[0]] * (MI.PLANTILLA_MAX_IA - len(destino.jugadores)))
        elif caso == 'vendedor_en_el_minimo':
            origen.jugadores[:] = [j] + [x for x in origen.jugadores if x is not j][:MI.PLANTILLA_MIN_VENDEDOR - 1]
        else:
            j.prestamo = {'dueno': "Otro", 'club': origen.nombre}
        _revisar(e)
        assert j in origen.jugadores and j not in destino.jugadores and R.vivos(e) == [] and _fichajes(e) == [], caso
    print("  test_comprador_sin_dinero_no_ejecuta: OK")


def test_rumor_del_user_real_trae_oferta():
    e = estado_chico(); mi = e['mi_equipo']
    r = _rumor(e, clase='user', real=True, vence=1)
    j = _jugador(mi, r)
    destino = _club(e, r['destino'])
    assert j is not None and r['origen'] == mi.nombre and destino is not mi
    assert N.lista(e)[0]['importancia'] >= N.IMPORTANCIA_FEED          # es de los tuyos: entra al feed
    _revisar(e)
    (of,) = e['ofertas_recibidas']                             # la oferta formal, por el cauce de siempre
    assert of['jugador'] is j and of['comprador'] is destino and of['monto'] == r['precio']
    msg = C.bandeja(e)[0]
    assert j.apellido in msg['asunto'] and msg['accion']['pantalla'] == 'ofertas_screen'
    assert j in mi.jugadores and R.vivos(e) == [] and _fichajes(e) == []     # decidir sigue siendo cosa tuya
    # humo sobre un jugador tuyo: ni oferta ni correo
    e2 = estado_chico()
    _rumor(e2, clase='user', real=False, vence=1)
    _revisar(e2)
    assert not e2.get('ofertas_recibidas') and C.bandeja(e2) == [] and R.vivos(e2) == []
    # real, pero ya lo vendiste: nada
    e3 = estado_chico()
    r3 = _rumor(e3, clase='user', real=True, vence=1)
    e3['mi_equipo'].jugadores.remove(_jugador(e3['mi_equipo'], r3))
    _revisar(e3)
    assert not e3.get('ofertas_recibidas') and R.vivos(e3) == []
    print("  test_rumor_del_user_real_trae_oferta: OK")


def test_maximo_dos_vivos():
    e = estado_chico()
    a, b = R.generar(e, random.Random(1)), R.generar(e, random.Random(2))
    assert a and b and R.generar(e, random.Random(3)) is None and len(R.vivos(e)) == R.MAX_VIVOS == 2
    assert a['jugador_id'] != b['jugador_id'] and a['id'] != b['id']
    a['vence'] = b['vence'] = 3
    _revisar(e, nuevos=True)                                   # con dos vivos no nace un tercero
    assert len(R.vivos(e)) == 2
    print("  test_maximo_dos_vivos: OK")


def test_mercado_cerrado_los_apaga():
    e = estado_chico()
    r = _rumor(e, real=True, vence=3)
    r2 = _rumor(e, clase='user', real=True, vence=3, semilla=6)
    origen = _club(e, r['origen'])
    j = _jugador(origen, r)
    _revisar(e, abierto=False, nuevos=True)                    # cerró el mercado: humo, y no nace ninguno
    assert R.vivos(e) == [] and j in origen.jugadores and _fichajes(e) == []
    assert not e.get('ofertas_recibidas') and r2['real'] is True
    print("  test_mercado_cerrado_los_apaga: OK")


def test_plazo_baja_solo_con_mercado_abierto():
    e = estado_chico()
    r = _rumor(e, real=True, vence=3)
    origen, destino = _club(e, r['origen']), _club(e, r['destino'])
    j = _jugador(origen, r)
    for queda in (2, 1):
        _revisar(e)
        assert r['vence'] == queda and R.vivos(e) == [r] and j in origen.jugadores
    _revisar(e)                                                # tercera jornada de mercado: vence
    assert R.vivos(e) == [] and j in destino.jugadores
    print("  test_plazo_baja_solo_con_mercado_abierto: OK")


def test_revisar_jornada_puede_crear_un_rumor():
    e = estado_chico()
    _revisar(e, v=0.99, nuevos=False)
    assert R.vivos(e) == []
    _revisar(e, v=0.0, nuevos=True)
    assert len(R.vivos(e)) == 1 and N.lista(e)[0]['tipo'] == 'rumor'
    R.revisar_jornada({})                                      # sin carrera: no hace nada ni revienta
    print("  test_revisar_jornada_puede_crear_un_rumor: OK")


def test_proporcion_60_40():
    e = estado_chico()
    azar = random.Random(60)
    reales, plazos = 0, set()
    for _ in range(1000):
        r = R.generar(e, azar, clase='user')
        reales += r['real']; plazos.add(r['vence'])
        del R.vivos(e)[:]; del N.lista(e)[:]
    assert 550 <= reales <= 650, reales
    assert plazos == {1, 2, 3}
    print("  test_proporcion_60_40: OK")


def test_json():
    e = estado_chico()
    R.generar(e, random.Random(1), clase='ia'); R.generar(e, random.Random(2), clase='user')
    vuelta = json.loads(json.dumps(e['datos_carrera']['rumores']))
    assert vuelta == e['datos_carrera']['rumores'] and all(set(r) == CLAVES for r in R.vivos(e))
    e['datos_carrera']['rumores'] = "basura"                   # guardado dañado: se rehace vacío
    assert R.vivos(e) == [] and R.generar(e, random.Random(3)) is not None
    print("  test_json: OK")


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
