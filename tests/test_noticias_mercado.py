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


def _precio(j):
    """v0.4.27.0: el precio normal de mercado de ese jugador (110 % de su valor): ni ganga ni pago generoso. Con tope
    de $200M para que los pases de los tests de topes no toquen el récord de traspaso ($222M)."""
    return min(int(NG._valor_de_referencia(j) * 1.10), 200_000_000)


def test_fichaje_grande_publica_importancia_5():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    j = crack(90)
    assert j.overall == 90
    monto = _precio(j)
    NG.registrar_pase(e, j, a.nombre, b.nombre, monto, False)
    (n,) = _fichajes(e)
    assert (n['importancia'], n['categoria'], n['jugadores_ids']) == (5, 'fichaje', [j.id])
    assert n['equipos_ids'] == [b.id, a.id]                    # destino y origen
    assert (n['media'], n['propio'], n['puntaje']) == (90, False, 90 + NG.BONO_TU_LIGA)
    assert "Crack De-prueba" in n['titular'] and len(n['titular']) <= 60 and not n['titular'].startswith("Confirmado")
    assert a.nombre in n['cuerpo'] and b.nombre in n['cuerpo'] and NG.dinero_exacto(monto) in n['cuerpo']
    # entre clubes de la IA: 85-89 -> 4 · el resto -> 3
    for k, (ovr, imp) in enumerate(((89, 4), (85, 4), (84, 3), (76, 3))):
        del N.lista(e)[:]                                      # cada uno en limpio: aquí no se prueba el tope
        c = crack(ovr, 880001 + k)
        NG.registrar_pase(e, c, a.nombre, b.nombre, _precio(c), False)
        assert _fichajes(e)[0]['importancia'] == imp, ovr
    assert len(e['datos_carrera']['historial_pases']) == 5
    print("  test_fichaje_grande_publica_importancia_5: OK")


def test_fichaje_menor_de_la_ia_no_publica():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    j = crack(75)
    NG.registrar_pase(e, j, a.nombre, b.nombre, _precio(j), False)
    assert N.lista(e) == [] and len(e['datos_carrera']['historial_pases']) == 1      # el pase sí queda en el historial
    assert j.ventana_traspaso
    # fuera de tu liga hace falta media 80; con un club de tu liga basta 76
    c79, c77, c80 = crack(79, 2), crack(77, 3), crack(80, 4)
    NG.registrar_pase(e, c79, "Club de Otra Liga", "Otro de Otra Liga", _precio(c79), False)
    assert N.lista(e) == []
    NG.registrar_pase(e, c77, "Club de Otra Liga", b.nombre, _precio(c77), False)
    NG.registrar_pase(e, c80, "Club de Otra Liga", "Otro de Otra Liga", _precio(c80), False)
    de_fuera, con_los_tuyos = _fichajes(e)
    assert (con_los_tuyos['media'], con_los_tuyos['puntaje'], con_los_tuyos['importancia']) == (77, 77 + NG.BONO_TU_LIGA, 3)
    assert (de_fuera['media'], de_fuera['puntaje'], de_fuera['equipos_ids']) == (80, 80, [])
    print("  test_fichaje_menor_de_la_ia_no_publica: OK")


def _ia(e, ovr, jid, de="Club de Otra Liga", a="Otro de Otra Liga", **kw):
    """Un pase entre clubes de la IA (por defecto, de otra liga: el puntaje es la media) a precio normal de mercado."""
    j = crack(ovr, jid, apellido=f"N{jid}")
    NG.registrar_pase(e, j, de, a, _precio(j), False, **kw)


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
    # v0.4.27.0: que un club suelte a un jugador sí es noticia (tipo 'otro', marca `liberacion`); el fin de
    # contrato no, y ninguna de las dos cuenta como fichaje
    assert _fichajes(e) == [] and len(e['datos_carrera']['historial_pases']) == 2
    (lib,) = N.lista(e)
    assert lib['liberacion'] and lib['tipo'] == 'otro' and lib['categoria'] == 'fichaje' and lib['importancia'] == 5
    assert N.etiqueta(lib) == "LIBERADO" and lib['jugadores_ids'] == [1] and lib['jugadores_nombres'] == ["Crack De-prueba"]
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
        NG.registrar_pase(e, j, a.nombre, b.nombre, _precio(j), False, confirmado=confirmado)
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


# ------------------------------------------------------------------ v0.4.27.0: ganga, pago generoso, traición y récord
def test_ganga_y_pago_generoso_son_el_mismo_fichaje_con_otra_etiqueta():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    j = crack(88, 1)
    valor = NG._valor_de_referencia(j)
    NG.registrar_pase(e, j, a.nombre, b.nombre, int(valor * 0.50), False)         # la mitad de lo que vale
    (n,) = _fichajes(e)
    assert n['variante'] == 'ganga' and N.etiqueta(n) == "GANGA" and n['tipo'] == 'fichaje'
    assert n['importancia'] == 5                                                   # 88 → 4, +1 por atípico
    assert n['puntaje'] == 88 + NG.BONO_TU_LIGA + NG.BONO_PUNTAJE_ATIPICO
    assert "Ganga" in n['titular'] and len(n['titular']) <= 60 and "50 %" in n['cuerpo']
    del N.lista(e)[:]
    k = crack(84, 2)
    NG.registrar_pase(e, k, a.nombre, b.nombre, int(NG._valor_de_referencia(k) * 1.60), False)
    (n,) = _fichajes(e)
    assert n['variante'] == 'generoso' and N.etiqueta(n) == "PAGO GENEROSO" and n['importancia'] == 4   # 84 → 3, +1
    assert "Pago generoso" in n['titular'] and "160 %" in n['cuerpo']
    del N.lista(e)[:]
    m = crack(88, 3)
    NG.registrar_pase(e, m, a.nombre, b.nombre, _precio(m), False)                 # precio normal: nada especial
    (n,) = _fichajes(e)
    assert 'variante' not in n and N.etiqueta(n) == "FICHAJE" and n['importancia'] == 4
    print("  test_ganga_y_pago_generoso_son_el_mismo_fichaje_con_otra_etiqueta: OK")


def test_ganga_exige_monto_minimo_y_un_lesionado_se_compara_con_su_valor_de_hoy():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    barato = crack(58, 4)                                                          # vale < $5M: no es ganga ni pago generoso
    assert NG._valor_de_referencia(barato) < NG.MONTO_MINIMO_ATIPICO
    NG.registrar_pase(e, barato, a.nombre, b.nombre, 100_000, True)
    assert 'variante' not in _fichajes(e)[0]
    del N.lista(e)[:]
    sano, lesionado = crack(86, 5), crack(86, 6)
    lesionado.lesion_dias = 120                                                    # baja larga: vale bastante menos
    assert NG._valor_de_referencia(lesionado) < NG._valor_de_referencia(sano)
    # el precio normal de un lesionado (110 % de su valor de hoy) no es ganga aunque sea mucho menos que el sano
    NG.registrar_pase(e, lesionado, a.nombre, b.nombre, _precio(lesionado), False)
    assert 'variante' not in _fichajes(e)[0]
    del N.lista(e)[:]
    NG.registrar_pase(e, lesionado, a.nombre, b.nombre, int(NG._valor_de_referencia(lesionado) * 0.5), False)
    assert _fichajes(e)[0]['variante'] == 'ganga'                                  # y pagar la mitad de su valor de hoy, sí
    print("  test_ganga_exige_monto_minimo_y_un_lesionado_se_compara_con_su_valor_de_hoy: OK")


def test_traicion_entre_rivales_manda_sobre_la_ganga():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    a.rival, b.rival = b.nombre, a.nombre                                          # rivales de clásico
    j = crack(86, 7)
    NG.registrar_pase(e, j, a.nombre, b.nombre, _precio(j), False)
    (n,) = _fichajes(e)
    assert n['variante'] == 'traicion' and N.etiqueta(n) == "TRAICIÓN" and n['importancia'] == 5
    assert "Traición" in n['titular'] and a.nombre in n['cuerpo'] and b.nombre in n['cuerpo']
    del N.lista(e)[:]
    k = crack(86, 8)
    NG.registrar_pase(e, k, a.nombre, b.nombre, int(NG._valor_de_referencia(k) * 0.4), False)   # además es una ganga
    assert _fichajes(e)[0]['variante'] == 'traicion'
    print("  test_traicion_entre_rivales_manda_sobre_la_ganga: OK")


def test_los_fichajes_atipicos_respetan_el_tope_de_la_jornada():
    e = estado_chico()
    for k in range(8):                                         # ocho gangas de la IA en la misma jornada
        j = crack(80 + k, 900 + k, apellido=f"G{k}")
        NG.registrar_pase(e, j, "Club de Otra Liga", "Otro de Otra Liga", int(NG._valor_de_referencia(j) * 0.4), False)
    ia = [n for n in _fichajes(e) if not n['propio']]
    assert len(ia) == NG.MAX_FICHAJES_IA_JORNADA and all(n['variante'] == 'ganga' for n in ia)
    assert sorted(n['media'] for n in ia) == [84, 85, 86, 87]
    print("  test_los_fichajes_atipicos_respetan_el_tope_de_la_jornada: OK")


def test_record_de_traspaso_arranca_en_neymar_y_se_actualiza():
    from alpha_football import noticias_gen as G
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    assert G.record_traspaso(e)['valor'] == 222_000_000 and G.record_traspaso(e)['nombre'] == "Neymar"
    j = crack(95, 10, nombre="Kylian", apellido="Mbape")
    NG.registrar_pase(e, j, a.nombre, b.nombre, 222_000_000, False)               # igualar no es superar
    assert [n['tipo'] for n in N.lista(e)] == ['fichaje'] and G.record_traspaso(e)['nombre'] == "Neymar"
    del N.lista(e)[:]
    NG.registrar_pase(e, j, a.nombre, b.nombre, 230_000_000, False)
    assert _fichajes(e) == []                                                      # el fichaje no se repite
    (r,) = N.lista(e)
    assert r['tipo'] == 'record' and r['importancia'] == 5 and N.etiqueta(r) == "RÉCORD" and r['propio'] is False
    assert "Récord de traspaso" in r['titular'] and "Neymar" in r['cuerpo'] and "$222M" in r['cuerpo']
    assert G.record_traspaso(e)['valor'] == 230_000_000 and G.record_traspaso(e)['nombre'] == "Kylian Mbape"
    k = crack(94, 11, nombre="Otro", apellido="Crack")
    NG.registrar_pase(e, k, b.nombre, a.nombre, 225_000_000, False)               # no supera al nuevo récord
    assert [n['tipo'] for n in N.lista(e)].count('record') == 1 and G.record_traspaso(e)['valor'] == 230_000_000
    NG.registrar_pase(e, k, b.nombre, a.nombre, 240_000_000, False)
    nuevo = [n for n in N.lista(e) if n['tipo'] == 'record'][0]
    assert "Kylian Mbape" in nuevo['cuerpo'] and "$230M" in nuevo['cuerpo']
    assert 'traspaso' in e['datos_carrera']['records']
    import json; json.dumps(e['datos_carrera']['records'])                         # solo tipos JSON
    # una partida vieja sin el récord lo recibe al primer uso
    e2 = estado_chico(); e2['datos_carrera']['records'] = {'goles': {'valor': 30, 'nombre': 'X', 'temporada': 1}}
    assert G.record_traspaso(e2)['valor'] == 222_000_000
    print("  test_record_de_traspaso_arranca_en_neymar_y_se_actualiza: OK")


def test_el_record_sale_aunque_no_pase_el_filtro_ni_el_tope():
    e = estado_chico(); a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    for k in range(6):                                                              # tope lleno de fichajes normales
        _ia(e, 90 + k, 700 + k)
    j = crack(70, 20)                                                               # media 70: normalmente no sería noticia
    NG.registrar_pase(e, j, a.nombre, b.nombre, 300_000_000, False)
    assert len([n for n in N.lista(e) if n['tipo'] == 'record']) == 1
    assert len([n for n in _fichajes(e) if not n['propio']]) == NG.MAX_FICHAJES_IA_JORNADA     # el récord no cuenta
    print("  test_el_record_sale_aunque_no_pase_el_filtro_ni_el_tope: OK")


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
