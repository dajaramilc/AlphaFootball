"""v0.4.23.0: noticias de fichajes (negociacion.registrar_pase), el único punto por el que pasan todos."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(423)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import finanzas as F, negociacion as NG, noticias as N, save
from alpha_football.models import Jugador, alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams

save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales
RICO = 10**10


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


def crack(ovr, jid=880000, nombre="Crack", apellido="De-prueba"):
    return Jugador(nombre=nombre, apellido=apellido, posicion='DEL', ataque=ovr, defensa=ovr, fisico=ovr,
                   tecnica=ovr, mental=ovr, moral=70, id=jid, edad=27)


def _fichajes(e):
    return [n for n in N.lista(e) if n['tipo'] == 'fichaje']


def test_fichaje_grande_publica_importancia_5():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    j = crack(90)
    assert j.overall == 90
    NG.registrar_pase(e, j, a.nombre, b.nombre, 90_000_000, False)
    (n,) = _fichajes(e)
    assert (n['importancia'], n['categoria'], n['jugadores_ids']) == (5, 'fichaje', [j.id])
    assert n['equipos_ids'] == [b.id, a.id]                    # destino y origen
    assert (n['media'], n['propio'], n['puntaje']) == (90, False, 90 + NG.BONO_TU_LIGA)
    assert "Crack De-prueba" in n['titular'] and len(n['titular']) <= 60 and not n['titular'].startswith("Confirmado")
    assert a.nombre in n['cuerpo'] and b.nombre in n['cuerpo'] and "$90,000,000" in n['cuerpo']
    # entre clubes de la IA: 85-89 -> 4 · el resto -> 3
    for k, (ovr, imp) in enumerate(((89, 4), (85, 4), (84, 3), (76, 3))):
        del N.lista(e)[:]                                      # cada uno en limpio: aquí no se prueba el tope
        NG.registrar_pase(e, crack(ovr, 880001 + k), a.nombre, b.nombre, 1_000_000, False)
        assert _fichajes(e)[0]['importancia'] == imp, ovr
    assert len(e['datos_carrera']['historial_pases']) == 5
    print("  test_fichaje_grande_publica_importancia_5: OK")


def test_fichaje_menor_de_la_ia_no_publica():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    j = crack(75)
    NG.registrar_pase(e, j, a.nombre, b.nombre, 5_000_000, False)
    assert N.lista(e) == [] and len(e['datos_carrera']['historial_pases']) == 1      # el pase sí queda en el historial
    assert j.ventana_traspaso
    # fuera de tu liga hace falta media 80; con un club de tu liga basta 76
    NG.registrar_pase(e, crack(79, 2), "Club de Otra Liga", "Otro de Otra Liga", 5_000_000, False)
    assert N.lista(e) == []
    NG.registrar_pase(e, crack(77, 3), "Club de Otra Liga", b.nombre, 5_000_000, False)
    NG.registrar_pase(e, crack(80, 4), "Club de Otra Liga", "Otro de Otra Liga", 5_000_000, False)
    de_fuera, con_los_tuyos = _fichajes(e)
    assert (con_los_tuyos['media'], con_los_tuyos['puntaje'], con_los_tuyos['importancia']) == (77, 77 + NG.BONO_TU_LIGA, 3)
    assert (de_fuera['media'], de_fuera['puntaje'], de_fuera['equipos_ids']) == (80, 80, [])
    print("  test_fichaje_menor_de_la_ia_no_publica: OK")


def _ia(e, ovr, jid, de="Club de Otra Liga", a="Otro de Otra Liga", **kw):
    """Un pase entre clubes de la IA (por defecto, de otra liga: el puntaje es la media)."""
    NG.registrar_pase(e, crack(ovr, jid, apellido=f"N{jid}"), de, a, 1_000_000, False, **kw)


def _medias(e):
    return sorted(n['media'] for n in _fichajes(e))


def test_tope_de_fichajes_de_la_ia_por_jornada():
    e = estado_chico(); mi, rival = e['mi_equipo'], e['liga'].equipos[2]
    orden = list(range(80, 100)); random.Random(7).shuffle(orden)
    for k, ovr in enumerate(orden):                            # 20 pases de la IA en la misma jornada
        _ia(e, ovr, k)
    assert _medias(e) == [96, 97, 98, 99] and NG.MAX_FICHAJES_IA_JORNADA == 4       # quedan los 4 de más puntaje
    assert len(e['datos_carrera']['historial_pases']) == 20                         # el historial no se toca
    del N.lista(e)[:]
    for k, ovr in enumerate((84, 82, 86, 83)):
        _ia(e, ovr, 100 + k)
    _ia(e, 81, 200)                                            # peor que el más flojo: no entra
    _ia(e, 82, 201)                                            # empata con el más flojo: tampoco
    assert _medias(e) == [82, 83, 84, 86] and not [n for n in _fichajes(e) if n['jugadores_ids'] == [201]]
    _ia(e, 85, 202)                                            # mejor: reemplaza al más flojo
    assert _medias(e) == [83, 84, 85, 86]
    _ia(e, 81, 203, a=rival.nombre)                            # con un club de tu liga pesa 3 más: 84 > 83
    assert _medias(e) == [81, 84, 85, 86]
    # los tuyos y los confirmados por un rumor se publican siempre, no cuentan y nadie los reemplaza
    NG.registrar_pase(e, crack(60, 300), rival.nombre, mi.nombre, 300_000, True)
    _ia(e, 77, 301, de=rival.nombre, confirmado=True)
    _ia(e, 99, 302)                                            # a igual puntaje (84) sale el más viejo
    assert _medias(e) == [60, 77, 81, 85, 86, 99]
    assert sum(1 for n in _fichajes(e) if not n['propio'] and not n['confirmado']) == 4
    e['liga'].jornada_actual += 1                              # jornada nueva: el tope empieza de cero
    for k in range(5):
        _ia(e, 80 + k, 400 + k)
    assert _medias(e) == [60, 77, 81, 81, 82, 83, 84, 85, 86, 99]
    print("  test_tope_de_fichajes_de_la_ia_por_jornada: OK")


def test_fichaje_del_user_siempre_publica():
    e = estado_chico(); mi, rival = e['mi_equipo'], e['liga'].equipos[3]
    NG.registrar_pase(e, crack(60, 1), rival.nombre, mi.nombre, 300_000, True)       # compra
    NG.registrar_pase(e, crack(61, 2), mi.nombre, rival.nombre, 400_000, True)       # venta
    venta, compra = _fichajes(e)
    assert compra['importancia'] == venta['importancia'] == 3
    assert compra['equipos_ids'] == [mi.id, rival.id] and venta['equipos_ids'] == [rival.id, mi.id]
    NG.registrar_pase(e, crack(86, 3), rival.nombre, mi.nombre, 95_000_000, True)    # una figura: manda su media
    assert _fichajes(e)[0]['importancia'] == 5
    print("  test_fichaje_del_user_siempre_publica: OK")


def test_liberado_no_publica():
    e = estado_chico(); a = e['liga'].equipos[1]
    NG.registrar_pase(e, crack(90, 1), a.nombre, 'Libre', 0, False)
    NG.registrar_pase(e, crack(90, 2), e['mi_equipo'].nombre, 'Libre (fin de contrato)', 0, True)
    assert N.lista(e) == [] and len(e['datos_carrera']['historial_pases']) == 2
    NG.registrar_pase(e, crack(82, 3), NG.LIBRES_PASE, a.nombre, 0, False)           # un libre que firma: sí es noticia
    (n,) = _fichajes(e)
    assert n['importancia'] == 3 and n['equipos_ids'] == [a.id] and "libre" in n['cuerpo'] and "$" not in n['cuerpo']
    print("  test_liberado_no_publica: OK")


def test_confirmado_antepone_confirmado():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    NG.registrar_pase(e, crack(83), a.nombre, b.nombre, 40_000_000, False, confirmado=True)
    (n,) = _fichajes(e)
    assert n['titular'].startswith("Confirmado: ") and "Crack De-prueba" in n['titular'] and len(n['titular']) <= 60
    assert n['confirmado'] is True and n['importancia'] == 3
    # lo que adelantó un rumor se confirma siempre, aunque la media no dé para noticia
    NG.registrar_pase(e, crack(70, 2), "Club de Otra Liga", "Otro de Otra Liga", 1_000_000, False, confirmado=True)
    assert _fichajes(e)[0]['media'] == 70 and _fichajes(e)[0]['titular'].startswith("Confirmado: ")
    print("  test_confirmado_antepone_confirmado: OK")


def test_titular_largo_no_se_corta():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    a.nombre, b.nombre = "Independiente del Valle de Lagrimas", "Paris Saint-Germain Sin Champions"
    j = crack(88, nombre="Maximiliano", apellido="Rodríguez-Fernández")
    for confirmado in (False, True):
        NG.registrar_pase(e, j, a.nombre, b.nombre, 70_000_000, False, confirmado=confirmado)
        t = _fichajes(e)[0]['titular']
        assert len(t) <= 60 and not t.endswith('…') and "Rodríguez-Fernández" in t, t
    print("  test_titular_largo_no_se_corta: OK")


def test_fallo_al_publicar_no_rompe_el_pase():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    j = crack(90); j.remate = True
    real = N.publicar

    def rota(*args, **kw):
        raise RuntimeError("noticias rotas")

    N.publicar = rota
    try:
        NG.registrar_pase(e, j, a.nombre, b.nombre, 99_000_000, False)        # no propaga
    finally:
        N.publicar = real
    (h,) = e['datos_carrera']['historial_pases']
    assert (h['jugador'], h['de'], h['a'], h['monto']) == ("Crack De-prueba", a.nombre, b.nombre, 99_000_000)
    assert j.ventana_traspaso and j.remate is False and N.lista(e) == []
    print("  test_fallo_al_publicar_no_rompe_el_pase: OK")


def test_el_user_ficha_y_sale_la_noticia():
    e = estado_chico(); mi = e['mi_equipo']
    club = e['liga'].equipos[4]
    j = min(club.jugadores, key=lambda x: x.overall)
    ok, msg = NG.fichar(e, j, club, int(j.clausula))
    assert ok, msg
    (n,) = _fichajes(e)
    assert n['jugadores_ids'] == [j.id] and n['equipos_ids'] == [mi.id, club.id] and n['importancia'] >= 3
    assert n in N.para_feed(e)
    print("  test_el_user_ficha_y_sale_la_noticia: OK")


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
