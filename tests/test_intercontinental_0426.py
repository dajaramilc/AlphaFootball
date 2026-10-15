"""v0.4.26.0: el campeón vigente juega la copa siguiente (y libera un cupo de su liga), la Copa Intercontinental
de diciembre y el botón SIMULAR RESTO quitado de la copa."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date
from test_calendario import screen, _e   # noqa: E402  (deja save.guardar_en_slot sin efecto)
from alpha_football import calendario as CAL, competiciones as CP, correo as C, dias as D
from alpha_football import intercontinental as INT


def _premier(clubes):
    return [x for x in clubes if x.get('liga') == 'premier']


def test_campeon_vigente_entra_y_libera_cupo():
    e = _e('premier')
    CP.iniciar_temporada(e, random.Random(1))
    base = CP.clasificados(e, 'champions')
    assert len(_premier(base)) == CP.CUPOS['champions']['premier']
    fuera = [eq.nombre for eq in e['primera_division']['premier'].equipos
             if eq.nombre not in {x['nombre'] for x in base}]
    for campeon in (fuera[-1], _premier(base)[0]['nombre']):          # uno que no entraba y uno que ya entraba
        e['datos_carrera']['copas']['champions']['campeon'] = campeon
        assert CP.campeon_vigente(e, 'champions') == campeon
        nuevos = CP.clasificados(e, 'champions')
        assert nuevos[0]['nombre'] == campeon and nuevos[0]['liga'] == 'premier'
        assert len(_premier(nuevos)) == CP.CUPOS['champions']['premier'] + 1      # su cupo pasa al siguiente
        assert len(nuevos) == CP.N_CLUBES['champions'] and len({x['nombre'] for x in nuevos}) == len(nuevos)


def test_campeon_vigente_desde_el_mundo():
    e = _e('premier')
    e['datos_carrera'].pop('copas', None)
    assert CP.campeon_vigente(e, 'libertadores') is None
    e['datos_carrera']['mundo'] = {'campeones': {'libertadores': 'Club Que No Existe'}}
    assert CP.campeon_vigente(e, 'libertadores') == 'Club Que No Existe'
    assert CP._club_campeon(e, 'libertadores', 'Club Que No Existe') is None       # ya no existe: no se inventa


def test_fecha_base_en_diciembre_y_nunca_en_navidad():
    for anio in range(2026, 2050):
        d = INT.fecha_base(anio)
        assert d.month == 12 and 19 <= d.day <= 27 and d.day not in (24, 25)


def _mundo(e, lib, ucl, hoy):
    """Continentes desfasados, Libertadores 2026 terminada y reloj en `hoy`."""
    dc = e['datos_carrera']
    dc['mundo'] = {'desfase': True, 'anio': {'europa': 2026, 'sudamerica': 2026}, 'campeones': {'champions': ucl}}
    dc['copas'] = {'libertadores': {'tipo': 'libertadores', 'anio': 2026, 'temporada': 1, 'campeon': lib,
                                    'clubes': [], 'partidos': [], 'llaves': [], 'fechas_jornada': []}}
    D._cal(e)['dia'] = hoy.isoformat()


def test_intercontinental_sin_el_user_se_simula_en_su_dia():
    e = _e('premier')
    eqs = e['primera_division']['laliga'].equipos
    ucl = eqs[0]
    lib = e['primera_division']['betplay'].equipos[0]
    saldo = {ucl.nombre: ucl.balance, lib.nombre: lib.balance}
    _mundo(e, lib.nombre, ucl.nombre, date(2026, 12, 20))
    INT.revisar_jornada(e)
    reg = e['datos_carrera']['intercontinental']
    assert reg['anio'] == 2026 and reg['local'] == lib.nombre and reg['visitante'] == ucl.nombre
    assert INT.fecha(e) == date(2026, 12, 27) and not reg['jugado']        # base 26/12, pero 7 días desde hoy
    assert INT.evento_user(e) is None and INT.pendiente_user(e) is None    # no es tuya
    INT.revisar_jornada(e)
    assert not reg['jugado']                                               # todavía no es el día
    D._cal(e)['dia'] = date(2026, 12, 27).isoformat()
    INT.revisar_jornada(e)
    assert reg['jugado'] and reg['campeon'] in (lib.nombre, ucl.nombre) and len(reg['historial']) == 1
    finalista = ucl if reg['campeon'] == lib.nombre else lib
    campeon = lib if finalista is ucl else ucl
    assert campeon.balance - saldo[campeon.nombre] == INT.PREMIO_CAMPEON
    assert finalista.balance - saldo[finalista.nombre] == INT.PREMIO_FINALISTA
    if reg['gl'] == reg['gv']:
        assert reg['penales']['a'] != reg['penales']['b']
    INT.revisar_jornada(e)
    assert len(reg['historial']) == 1                                       # una sola vez por año


def test_intercontinental_del_user_se_juega_desde_jugar():
    from alpha_football.ui import copa_screen as S
    e = _e('premier')
    mi = e['mi_equipo']
    lib = e['primera_division']['betplay'].equipos[0]
    _mundo(e, lib.nombre, mi.nombre, date(2026, 12, 20))
    saldo = mi.balance
    INT.revisar_jornada(e)
    assert any(m.get('asunto', '').startswith("Jugarás la Copa Intercontinental") for m in C.bandeja(e))
    ev = next(x for x in CAL.eventos_user(e) if x['clave'] == 'intercontinental:2026')
    assert ev['fecha'] == date(2026, 12, 27) and not ev['local'] and ev['rival'] == lib.nombre
    assert S.rival_copa_pendiente(e) == (None, None) or S.rival_copa_pendiente(e)[0] != "Intercontinental · Final"
    D._cal(e)['dia'] = date(2026, 12, 27).isoformat()
    INT.revisar_jornada(e)
    assert not e['datos_carrera']['intercontinental']['jugado']             # el día de tu final no se simula sola
    assert S.rival_copa_pendiente(e) == ("Intercontinental · Final", lib.nombre)
    assert S.preparar_partido_copa(e) and e['partido_copa_dict']['tipo'] == 'intercontinental'
    assert S.necesita_penales(e, 1, 1)
    S.registrar_resultado_copa(e, 1, 1, (5, 4))                             # ganas por penales (eres visitante)
    reg = e['datos_carrera']['intercontinental']
    assert reg['jugado'] and reg['campeon'] == mi.nombre and reg['penales'] == {'a': 4, 'b': 5}
    assert mi.balance - saldo == INT.PREMIO_CAMPEON
    assert next(x for x in CAL.eventos_user(e) if x['clave'] == 'intercontinental:2026')['jugado']
    assert INT.pendiente_user(e) is None


def test_pasar_de_fase_y_ganar_la_copa_suben_la_moral(monkeypatch):
    from alpha_football.ui import copa_screen as S
    e = _e('premier')
    mi = e['mi_equipo']
    for j in mi.jugadores:
        j.moral = 50
    fase = {'f': 'Fase de liga'}
    monkeypatch.setattr(CP, 'tipo_copa_user', lambda est: 'champions')
    monkeypatch.setattr(CP, 'fase_user', lambda est: fase['f'])
    S.cobrar_premios_copa(e)
    assert all(j.moral == 50 for j in mi.jugadores)          # entrar a la copa no cuenta
    fase['f'] = 'Octavos'
    S.cobrar_premios_copa(e)
    S.cobrar_premios_copa(e)                                  # la misma fase, una sola vez
    assert all(j.moral == 58 for j in mi.jugadores)
    fase['f'] = 'Campeón'
    S.cobrar_premios_copa(e)
    assert all(j.moral == 83 for j in mi.jugadores)          # el título vale +25


def test_otras_ligas_muestra_la_intercontinental():
    from alpha_football.ui import otras_ligas_screen as O
    e = _e('premier')
    lib = e['primera_division']['betplay'].equipos[0]
    _mundo(e, lib.nombre, e['primera_division']['laliga'].equipos[0].nombre, date(2026, 12, 20))
    e['otras_ligas_copas'] = True
    e['otras_ligas_copa_sel'] = 'libertadores'
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode=''))
    assert O.render(screen, e) is None and e['otras_ligas_copa_sel'] == 'intercontinental'
    assert O._texto_intercontinental(e) == "Se juega en diciembre"
    INT.revisar_jornada(e)
    assert O._texto_intercontinental(e).startswith("Final: ")
    D._cal(e)['dia'] = date(2026, 12, 27).isoformat()
    INT.revisar_jornada(e)
    assert O._texto_intercontinental(e).startswith("Campeón 2026: ")
    pygame.event.clear(); assert O.render(screen, e) is None


def test_sin_desfase_no_hay_intercontinental():
    e = _e('premier')
    D.hoy(e)
    INT.revisar_jornada(e)
    assert not (e['datos_carrera'].get('intercontinental') or {}).get('anio')
