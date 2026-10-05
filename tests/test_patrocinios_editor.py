"""v4.9.2: patrocinios de la primera temporada editables en el modo edición (pestaña CLUBES) y
renovación permitida cuando la misma marca ocupa otro espacio (p. ej. camiseta y estadio)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(492)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, patrocinios as P
from alpha_football.models import Equipo
from alpha_football.ui import edit_screen as ED
from alpha_football.ui.menu import load_league_teams
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

CLUB_REAL = "Manchester Billete"      # club 0 de premier: misma marca en camiseta y estadio


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_equipo_guarda_patrocinios():
    eq = load_league_teams('premier').equipos[0]
    assert eq.patrocinios == {}
    eq.patrocinios = {'camiseta': 'Naik'}
    assert Equipo.from_dict(eq.to_dict()).patrocinios == {'camiseta': 'Naik'}
    print("  test_equipo_guarda_patrocinios: OK")


def test_patrocinios_editados_mandan_sobre_los_reales():
    e = estado_carrera(); mi = e['mi_equipo']
    assert mi.nombre == CLUB_REAL
    real = P.PATROCINIOS_REALES[CLUB_REAL]
    sudamericana = next(m[0] for m in P.MARCAS if m[3] == 'sudamerica')
    mi.patrocinios = {'camiseta': 'Naik', 'manga': sudamericana, 'estadio': 'Marca Que No Existe'}
    cs = P.datos(e)['contratos']
    assert cs['camiseta']['marca'] == 'Naik'                           # lo editado manda
    assert cs['manga']['marca'] == real['manga']                       # marca de otra región: se ignora
    assert cs['estadio']['marca'] == real['estadio']                   # marca inexistente: se ignora
    print("  test_patrocinios_editados_mandan_sobre_los_reales: OK")


def test_renovacion_con_la_misma_marca_en_otro_espacio():
    e = estado_carrera(); e['liga'].jornada_actual = 5; p = P.datos(e); cs = p['contratos']
    assert cs['camiseta']['marca'] == cs['estadio']['marca']           # así llega el club en la vida real
    viejo = cs['camiseta']; cs['camiseta'] = None; viejo['cumplido_ultima'] = True
    ofertas = P.generar_ofertas(e, 'camiseta', random.Random(4), anterior=viejo)
    ren = [o for o in ofertas if o['renovacion']]
    assert len(ren) == 1 and ren[0]['marca'] == viejo['marca']         # antes el rubro repetido la bloqueaba
    assert viejo['rubro'] not in {o['rubro'] for o in ofertas if not o['renovacion']}
    ok, _msg = P.firmar(e, ren[0]['id'])
    assert ok and cs['camiseta']['marca'] == viejo['marca']
    cs['manga'] = None                                                 # otra marca del mismo rubro sigue vetada
    o = P.generar_ofertas(e, 'manga', random.Random(5))[0]
    o['rubro'] = viejo['rubro']
    ok, msg = P.firmar(e, o['id'])
    assert not ok and "rubro" in msg
    print("  test_renovacion_con_la_misma_marca_en_otro_espacio: OK")


def test_opciones_y_fijar_patrocinio_en_el_editor():
    europeas = {m[0]: m for m in P.marcas_de_region('europa')}
    assert europeas and all(m[3] in ('global', 'europa') for m in europeas.values())
    assert ED.patrocinio_editor({'nombre': CLUB_REAL}, 'camiseta') == P.PATROCINIOS_REALES[CLUB_REAL]['camiseta']
    club = {'nombre': 'Club Inventado'}
    assert ED.patrocinio_editor(club, 'camiseta') is None              # sin dato: al azar
    rubros = ED.opciones_patro(club, 'camiseta', 'europa', 'rubro')
    assert rubros == sorted({m[1] for m in europeas.values()})
    assert ED.opciones_patro(club, 'camiseta', 'europa', 'marca') == [None, P.SIN_PATROCINIO]   # sin rubro: al azar o ninguno
    vistos = set()
    for rubro in rubros:                                               # cada rubro lista solo sus marcas
        ED.fijar_rubro(club, 'camiseta', 'europa', rubro)
        marcas = ED.opciones_patro(club, 'camiseta', 'europa', 'marca')
        assert marcas[:2] == [None, P.SIN_PATROCINIO] and club['patrocinios']['camiseta'] == marcas[2]
        assert all(europeas[m][1] == rubro for m in marcas[2:])
        vistos |= set(marcas[2:])
    assert vistos == set(europeas)                                     # todas alcanzables y ninguna sudamericana
    ED.fijar_patrocinio(club, 'camiseta', 'Naik')
    assert club['patrocinios'] == {'camiseta': 'Naik'}
    ED.fijar_rubro(club, 'camiseta', 'europa', europeas['Naik'][1])    # mismo rubro: no pisa la marca elegida
    assert club['patrocinios'] == {'camiseta': 'Naik'}
    ED.fijar_patrocinio(club, 'camiseta', None)                        # "al azar" borra lo editado
    assert 'patrocinios' not in club
    ED.fijar_rubro(club, 'manga', 'sudamerica', ED.opciones_patro(club, 'manga', 'sudamerica', 'rubro')[0])
    assert club['patrocinios']['manga'] in {m[0] for m in P.marcas_de_region('sudamerica')}
    print("  test_opciones_y_fijar_patrocinio_en_el_editor: OK")


def test_editor_clubes_dropdown_de_patrocinios():
    liga = load_league_teams('premier')
    db = {'premier': [eq.to_dict() for eq in liga.equipos], 'segunda_premier': [], '_ligas': {}}
    e = {'edited_db': db}
    rubro_de = {m[0]: m[1] for m in P.MARCAS}
    europeas = {m[0] for m in P.marcas_de_region('europa')}
    pygame.event.clear()
    assert ED.render(screen, e) is None
    click(ED.rect_seccion(1).center); ED.render(screen, e)             # CLUBES
    club = db['premier'][e['edit_equipo_idx']]
    click(ED.rect_patro_campo('manga', 'marca').center); ED.render(screen, e)
    assert e['edit_dropdown_activo'] == 'patro_marca_manga'
    ops = ED._opciones_dropdown('patro_marca_manga', e)
    assert [v for v, _t, _r in ops[:2]] == [None, P.SIN_PATROCINIO] and len(ops) > 3
    assert all(r.y >= 0 and r.bottom <= 720 for _v, _t, r in ops) and {v for v, _t, _r in ops[2:]} <= europeas
    pygame.event.clear(); assert ED.render(screen, e) is None          # se dibuja con la lista abierta
    elegido = next(v for v, _t, _r in ops[2:] if v != ED.patrocinio_editor(club, 'manga'))
    click(next(r for v, _t, r in ops if v == elegido).center); ED.render(screen, e)
    assert club['patrocinios']['manga'] == elegido and e['edit_dropdown_activo'] is None
    click(ED.rect_patro_campo('estadio', 'rubro').center); ED.render(screen, e)
    assert e['edit_dropdown_activo'] == 'patro_rubro_estadio'
    rubro, _t, r = ED._opciones_dropdown('patro_rubro_estadio', e)[-1]
    click(r.center); ED.render(screen, e)
    assert rubro_de[club['patrocinios']['estadio']] == rubro           # elegir rubro deja su primera marca
    click(ED.rect_patro_campo('manga', 'marca').center); ED.render(screen, e)
    click(ED._opciones_dropdown('patro_marca_manga', e)[0][2].center); ED.render(screen, e)
    assert 'manga' not in club['patrocinios']                          # "Al azar" borra lo editado
    antes = dict(club['patrocinios'])
    click(ED.rect_patro_campo('estadio', 'marca').center); ED.render(screen, e)
    click((20, 700)); ED.render(screen, e)                             # clic fuera: cierra sin cambiar
    assert e['edit_dropdown_activo'] is None and club['patrocinios'] == antes
    assert Equipo.from_dict(club).patrocinios == club['patrocinios']   # llega al club que carga el juego
    print("  test_editor_clubes_dropdown_de_patrocinios: OK")


def test_lista_de_rubros_sobre_restaurar_no_restaura():
    """La lista de rubros tapa RESTAURAR BASE: con ella abierta, el clic es solo de la lista."""
    liga = load_league_teams('premier')
    db = {'premier': [eq.to_dict() for eq in liga.equipos], 'segunda_premier': [], '_ligas': {}}
    e = {'edited_db': db}
    llamado = []
    orig = ED.restaurar_base
    ED.restaurar_base = lambda *a, **k: llamado.append(1)
    try:
        pygame.event.clear(); ED.render(screen, e)
        click(ED.rect_seccion(1).center); ED.render(screen, e)
        club = db['premier'][e['edit_equipo_idx']]
        click(ED.rect_patro_campo('estadio', 'rubro').center); ED.render(screen, e)
        ops = ED._opciones_dropdown('patro_rubro_estadio', e)
        fila = next(r for _v, _t, r in ops if ED.R_RESTAURAR.top <= r.centery < ED.R_RESTAURAR.bottom)
        punto = (fila.x + 30, fila.centery)                            # dentro de la lista Y del botón
        assert ED.R_RESTAURAR.collidepoint(punto)
        rubro = next(v for v, _t, r in ops if r.collidepoint(punto))
        click(punto); ED.render(screen, e)
        assert not llamado and e['edit_dropdown_activo'] is None
        assert {m[0]: m[1] for m in P.MARCAS}[ED.patrocinio_editor(club, 'estadio')] == rubro
    finally:
        ED.restaurar_base = orig
    print("  test_lista_de_rubros_sobre_restaurar_no_restaura: OK")


def test_estadio_sin_naming_arranca_vacio():
    e = estado_carrera('premier', 2); mi = e['mi_equipo']; n = e['liga'].num_jornadas
    assert mi.nombre == "Pool de Higado" and P.PATROCINIOS_REALES[mi.nombre]['estadio'] is None
    cs = P.datos(e)['contratos']
    assert cs['estadio'] is None and cs['camiseta'] and cs['manga']    # el estadio real no tiene naming
    assert P.cobro_jornada(e) == cs['camiseta']['fijo'] // n + cs['manga']['fijo'] // n
    e['liga'].jornada_actual = n // 2                                  # ventana de invierno: llegan ofertas
    P.revisar_jornada(e, random.Random(1))
    assert P.ofertas_de(e, 'estadio') and not P.ofertas_de(e, 'camiseta')
    e2 = estado_carrera('betplay', 10)                                 # club sin datos reales: arranca con los 3
    assert e2['mi_equipo'].nombre not in P.PATROCINIOS_REALES
    assert all(P.datos(e2)['contratos'].values())
    print("  test_estadio_sin_naming_arranca_vacio: OK")


def test_ninguno_en_el_editor():
    assert ED.patrocinio_editor({'nombre': 'Pool de Higado'}, 'estadio') == P.SIN_PATROCINIO
    assert ED.patrocinio_editor({'nombre': 'Club Inventado'}, 'estadio') is None      # sin datos: al azar
    club = {'nombre': 'Club Inventado'}
    ED.fijar_patrocinio(club, 'camiseta', P.SIN_PATROCINIO)
    assert club['patrocinios'] == {'camiseta': P.SIN_PATROCINIO}
    assert ED.patrocinio_editor(club, 'camiseta') == P.SIN_PATROCINIO
    e = estado_carrera(); mi = e['mi_equipo']                          # Manchester Billete
    try:
        mi.patrocinios = {'camiseta': P.SIN_PATROCINIO}                # "ninguno" editado: arranca vacío
        cs = P.datos(e)['contratos']
        assert cs['camiseta'] is None and cs['estadio']['marca'] == P.PATROCINIOS_REALES[CLUB_REAL]['estadio']
    finally:
        mi.patrocinios = {}
    e = estado_carrera('premier', 2); mi = e['mi_equipo']              # y al revés: darle naming a un estadio sin él
    try:
        mi.patrocinios = {'estadio': 'Naik'}
        assert P.datos(e)['contratos']['estadio']['marca'] == 'Naik'
    finally:
        mi.patrocinios = {}
    liga = load_league_teams('premier')                                # el dropdown ofrece "Ninguno"
    db = {'premier': [eq.to_dict() for eq in liga.equipos], 'segunda_premier': [], '_ligas': {}}
    ed = {'edited_db': db}
    pygame.event.clear(); ED.render(screen, ed)
    click(ED.rect_seccion(1).center); ED.render(screen, ed)
    c = db['premier'][ed['edit_equipo_idx']]
    click(ED.rect_patro_campo('estadio', 'marca').center); ED.render(screen, ed)
    ops = ED._opciones_dropdown('patro_marca_estadio', ed)
    assert ops[1][0] == P.SIN_PATROCINIO and "Ninguno" in ops[1][1]
    click(ops[1][2].center); ED.render(screen, ed)
    assert c['patrocinios']['estadio'] == P.SIN_PATROCINIO
    assert Equipo.from_dict(c).patrocinios == {'estadio': P.SIN_PATROCINIO}
    pygame.event.clear(); assert ED.render(screen, ed) is None         # se dibuja con "Ninguno"
    print("  test_ninguno_en_el_editor: OK")


TESTS = [test_equipo_guarda_patrocinios, test_patrocinios_editados_mandan_sobre_los_reales,
         test_renovacion_con_la_misma_marca_en_otro_espacio, test_opciones_y_fijar_patrocinio_en_el_editor,
         test_editor_clubes_dropdown_de_patrocinios,
         test_lista_de_rubros_sobre_restaurar_no_restaura,
         test_estadio_sin_naming_arranca_vacio, test_ninguno_en_el_editor]

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
