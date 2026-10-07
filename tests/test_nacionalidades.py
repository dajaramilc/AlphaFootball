"""v0.4.10.0: nacionalidad real de jugadores y DTs."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

import json
from alpha_football.data import nacionalidades as N
from alpha_football.data.free_agents import NOMBRES_LIBRES
from alpha_football.data.entrenadores import DT_REALES
from alpha_football import retiros as R
from alpha_football.models import Jugador

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _nombres_base():
    d = json.load(open(os.path.join(RAIZ, 'alpha_football_edited_db.json'), encoding='utf-8'))
    base = {f"{j['nombre']} {j['apellido']}" for v in d.values() if isinstance(v, list)
            for e in v for j in e['jugadores']} | {f"{a} {b}" for a, b in NOMBRES_LIBRES}
    from alpha_football.data.internacional import get_pool_champions, get_pool_libertadores
    for eq in get_pool_champions() + get_pool_libertadores():    # banco internacional completo
        base |= {j.nombre_completo for j in eq.jugadores}
    return base


def test_tabla_sin_huerfanos():
    base = {N._norm(n) for n in _nombres_base()}
    huerfanos = [n for n in N.NACIONALIDAD_JUGADOR if N._norm(n) not in base]
    assert len(N.NACIONALIDAD_JUGADOR) >= 600, len(N.NACIONALIDAD_JUGADOR)
    assert len(huerfanos) <= 0.05 * len(N.NACIONALIDAD_JUGADOR), huerfanos[:10]


def test_muestras_conocidas():
    assert N.nacionalidad_real("Thibaut Murois") == "Bélgica"
    assert N.nacionalidad_real("Lisandro El Carnicero") == "Argentina"
    assert N.nacionalidad_real("thibaut  murois") == "Bélgica"        # normalizado
    assert N.nacionalidad_real("Julián Sofoco") == ""                  # inventado


def test_libres_y_dts_cubiertos():
    assert all(N.nacionalidad_real(f"{a} {b}") for a, b in NOMBRES_LIBRES)
    assert all(N.nacionalidad_dt(dt) for dt, _estilo in DT_REALES.values())


def test_asignar_real_local_y_una_sola_vez():
    e = estado_carrera('premier')
    todos = [j for eq in e['liga'].equipos for j in eq.jugadores]
    for j in todos:
        j.nacionalidad = 'Inglaterra'                 # save viejo: todos con el país de la liga
    R.asignar_nacionalidades(e)
    ext = next(j for j in todos if N.nacionalidad_real(f"{j.nombre} {j.apellido}"))
    assert ext.nacionalidad == N.nacionalidad_real(f"{ext.nombre} {ext.apellido}") != 'Inglaterra'
    assert any(j.nacionalidad == 'Inglaterra' for j in todos)
    assert e['datos_carrera']['nac_reales'] is True
    ext.nacionalidad = 'Marte'                        # ya migrado: no se vuelve a pisar
    R.asignar_nacionalidades(e)
    assert ext.nacionalidad == 'Marte'


def test_regen_de_pais_sin_lista_toma_el_del_club():
    viejo = Jugador(nombre="Jean", apellido="Dupont", posicion="DEL", ataque=70, defensa=40, fisico=65,
                    tecnica=70, mental=65, id=991, edad=36, nacionalidad="Francia")
    regen = R.generar_regen(viejo, random.Random(1), 992, set(), pais_club="Inglaterra")
    assert regen.nacionalidad == "Inglaterra"
    viejo.nacionalidad = "Brasil"
    assert R.generar_regen(viejo, random.Random(1), 993, set(), pais_club="Inglaterra").nacionalidad == "Brasil"


def test_pool_internacional_nacionalizado():
    from alpha_football import competiciones as CP
    e = estado_carrera('premier')
    pool = CP._pool(e, 'champions')
    kane = next(j for eq in pool.values() for j in eq.jugadores if j.nombre_completo == "Harry Kane-gol")
    assert kane.nacionalidad == "Inglaterra"
    assert all(j.nacionalidad for eq in pool.values() for j in eq.jugadores)


def test_dts_con_nacionalidad():
    from alpha_football import entrenadores as EN
    e = estado_carrera('premier', idx=5)
    EN.asegurar_dts(e)
    d = EN.dts(e)
    assert all(dt.get('nacionalidad') for dt in d['por_club'].values())
    assert all(dt.get('nacionalidad') for dt in d['libres'])
    pep = next(dt for dt in d['por_club'].values() if dt['nombre'] == "Pep Guardiolo")
    assert pep['nacionalidad'] == "España"
    for dt in d['por_club'].values():                 # save viejo: sin el campo
        dt.pop('nacionalidad')
    EN.asegurar_dts(e)
    assert all(dt.get('nacionalidad') for dt in d['por_club'].values())


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
