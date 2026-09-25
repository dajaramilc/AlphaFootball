"""v4.0.0: motor del partido — tarjetas, lesiones, cambios, notas desde eventos."""
import sys, os, random, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(40)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
from alpha_football.models import asegurar_ids_unicos
from alpha_football.ui.menu import load_league_teams
from alpha_football import partido_ctx as PC
from alpha_football.engine import _once_titular

save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales
K = PC.clave


def dos_equipos(tipo='premier'):
    liga = load_league_teams(tipo)
    a, b = liga.equipos[0], liga.equipos[1]
    for e in (a, b):
        asegurar_ids_unicos(e)
    return liga, a, b


def ctx_basico():
    liga, a, b = dos_equipos()
    return a, b, PC.nuevo_estado(a, b, _once_titular(a), _once_titular(b))


# ---------------------------------------------------------------- Task 1: partido_ctx
def test_amarilla_doble_es_roja():
    a, b, ctx = ctx_basico(); j = ctx.en_cancha['l'][3]
    PC.aplicar_evento(ctx, {'minuto': 10, 'tipo': 'amarilla', 'equipo_id': a.id, 'lado': 'l',
                            'jugador': j, 'jugador_id': j.id, 'detalle': ''})
    assert ctx.amarillas[K(j)] == 1 and j in ctx.en_cancha['l']
    PC.aplicar_evento(ctx, {'minuto': 50, 'tipo': 'roja', 'equipo_id': a.id, 'lado': 'l', 'jugador': j,
                            'motivo': 'doble amarilla', 'partidos': 1, 'detalle': ''})
    assert j not in ctx.en_cancha['l'] and K(j) in ctx.fuera and ctx.expulsados['l'] == 1
    assert ctx.salida[K(j)] == 50
    assert any(i['tipo'] == 'sancion' and i['jugador_id'] == K(j) for i in ctx.incidencias)
    print("  test_amarilla_doble_es_roja: OK")


def test_cambio_y_minutos():
    a, b, ctx = ctx_basico()
    sale = ctx.en_cancha['v'][5]
    entra = next(j for j in b.jugadores if j not in ctx.en_cancha['v'])
    PC.aplicar_evento(ctx, {'minuto': 70, 'tipo': 'cambio', 'equipo_id': b.id, 'lado': 'v',
                            'jugador': entra, 'entra': entra, 'sale': sale, 'detalle': ''})
    assert entra in ctx.en_cancha['v'] and sale not in ctx.en_cancha['v'] and ctx.cambios['v'] == 1
    m = PC.minutos_jugados(ctx)
    assert m[K(sale)] == 70 and m[K(entra)] == 20
    assert m[K(ctx.en_cancha['l'][0])] == 90
    print("  test_cambio_y_minutos: OK")


def test_notas_desde_eventos():
    a, b, ctx = ctx_basico()
    del_ = next(j for j in ctx.en_cancha['l'] if j.posicion == 'DEL')
    med = next(j for j in ctx.en_cancha['l'] if j.posicion == 'MED')
    df = next(j for j in ctx.en_cancha['v'] if j.posicion == 'DEF')
    por_l = next(j for j in ctx.en_cancha['l'] if j.posicion == 'POR')
    PC.aplicar_evento(ctx, {'minuto': 20, 'tipo': 'gol', 'equipo_id': a.id, 'lado': 'l', 'jugador': del_,
                            'asistente': med, 'defensor': df, 'penal': False, 'detalle': ''})
    assert ctx.goles[K(del_)] == 1 and ctx.asist[K(med)] == 1
    assert abs(PC.nota_en_vivo(ctx, K(del_)) - 7.0) < 1e-9
    assert abs(PC.nota_en_vivo(ctx, K(df)) - 5.7) < 1e-9
    notas = PC.notas_finales(ctx, 1, 0, rng=random.Random(1))
    assert 3.0 <= min(notas.values()) and max(notas.values()) <= 10.0
    assert notas[K(del_)] > notas[K(df)]
    assert notas[K(por_l)] >= 6.0 + 0.5 + 0.5 - 0.3      # valla invicta + victoria - ruido máx
    print("  test_notas_desde_eventos: OK")


def test_copia_independiente():
    a, b, ctx = ctx_basico(); c2 = ctx.copia(); j = ctx.en_cancha['l'][2]
    PC.aplicar_evento(c2, {'minuto': 5, 'tipo': 'lesion', 'equipo_id': a.id, 'lado': 'l', 'jugador': j,
                           'partidos': 2, 'detalle': ''})
    assert j in ctx.en_cancha['l'] and j not in c2.en_cancha['l'] and K(j) not in ctx.fuera
    assert j.lesion_partidos == 0          # la lesión se escribe al cierre, no durante el partido
    print("  test_copia_independiente: OK")


# ---------------------------------------------------------------- Task 2: el motor genera incidencias
MEDIA_GOLES_BASE = 2.88    # con adición v4.4.0 (2.725 sin adición, v3.9.1), 600 partidos premier, seed 7
TIEMPO_BASE = 2.32         # 2.16 s del motor v3.9.1 × 96.5/90 (minutos promedio con la adición v4.4.0)


_TIEMPO = {}


def _muestra(n=600, seed=7):
    from alpha_football.engine import simular_partido
    random.seed(seed); liga = load_league_teams('premier'); rs = []
    t0 = time.perf_counter()          # solo la simulación (la carga de la liga no cuenta)
    for _ in range(n):
        a, b = random.sample(liga.equipos, 2)
        rs.append(simular_partido(a, b, aplicar_fisico=False))
    _TIEMPO['ultimo'] = time.perf_counter() - t0
    return rs


def _cronometrar(n=200, seed=7, veces=3):
    """Tiempo equivalente a 600 partidos: mínimo de `veces` corridas de n (la carga de la máquina
    hace variar una sola medición entre 2.6 s y 7.7 s), sin retener resultados."""
    from alpha_football.engine import simular_partido
    random.seed(seed); liga = load_league_teams('premier'); mejor = None
    for _ in range(veces):
        t0 = time.perf_counter()
        for _ in range(n):
            a, b = random.sample(liga.equipos, 2)
            simular_partido(a, b, aplicar_fisico=False)
        dt = time.perf_counter() - t0
        mejor = dt if mejor is None else min(mejor, dt)
    return mejor * 600 / n


def test_frecuencias_y_goles():
    dt = _cronometrar(); rs = _muestra()
    n = len(rs)
    cuenta = lambda t: sum(1 for r in rs for e in r.eventos if e['tipo'] == t) / n
    media = sum(r.goles_local + r.goles_visitante for r in rs) / n
    assert abs(media - MEDIA_GOLES_BASE) <= 0.2, media
    assert 2.8 <= cuenta('amarilla') <= 4.2, cuenta('amarilla')
    directas = sum(1 for r in rs for e in r.eventos if e['tipo'] == 'roja' and e.get('motivo') == 'directa') / n
    assert 0.08 <= directas <= 0.25, directas
    assert 0.15 <= cuenta('lesion') <= 0.40, cuenta('lesion')
    penales = sum(1 for r in rs for e in r.eventos
                  if e['tipo'] == 'penal_fallado' or (e['tipo'] == 'gol' and e.get('penal'))) / n
    assert 0.15 <= penales <= 0.40, penales
    assert cuenta('atajada') > 1 and cuenta('cambio') >= 5, (cuenta('atajada'), cuenta('cambio'))
    assert dt <= TIEMPO_BASE * 1.3 + 0.5, dt        # la jornada de 16 ligas no se vuelve lenta
    print(f"  test_frecuencias_y_goles: OK (goles {media:.2f}, {dt:.2f}s)")


def test_resultado_consistente():
    for r in _muestra(150, seed=3):
        goles_ev = [e for e in r.eventos if e['tipo'] == 'gol']
        assert len(goles_ev) == r.goles_local + r.goles_visitante
        assert sum(r.ctx.goles.values()) == len(goles_ev)
        for lado in ('l', 'v'):
            entraron = sum(1 for k, m in r.ctx.entrada.items() if m > 0 and r.ctx.lado_jugador[k] == lado)
            salieron = sum(1 for k in r.ctx.salida if r.ctx.lado_jugador[k] == lado)
            assert len(r.ctx.en_cancha[lado]) == 11 + entraron - salieron   # nadie desaparece sin evento
            assert r.ctx.cambios[lado] <= 5 and entraron == r.ctx.cambios[lado]
        for e in r.eventos:
            if e['tipo'] in ('gol', 'tiro', 'ocasion', 'amarilla') and e.get('jugador') is not None:
                assert e['minuto'] <= r.ctx.salida.get(K(e['jugador']), 999), f"{e['tipo']} de alguien que ya salió"
        assert r.notas and all(3.0 <= v <= 10.0 for v in r.notas.values())
    print("  test_resultado_consistente: OK")


def test_expulsion_pesa():
    """Un equipo que juega casi todo el partido con 10 anota menos que con 11."""
    from alpha_football.engine import simular_rango
    liga, a, b = dos_equipos(); random.seed(5); g10 = g11 = 0
    for _ in range(300):
        c = PC.nuevo_estado(a, b, _once_titular(a), _once_titular(b))
        j = c.en_cancha['l'][5]
        PC.aplicar_evento(c, {'minuto': 1, 'tipo': 'roja', 'lado': 'l', 'equipo_id': a.id, 'jugador': j,
                              'jugador_id': j.id, 'motivo': 'directa', 'partidos': 1})
        g10 += simular_rango(a, b, 2, 90, ctx=c)[0]
        g11 += simular_rango(a, b, 2, 90, ctx=PC.nuevo_estado(a, b, _once_titular(a), _once_titular(b)))[0]
    assert g10 < g11 * 0.92, (g10, g11)
    print(f"  test_expulsion_pesa: OK ({g10} con 10 vs {g11} con 11)")


def test_sin_auto_cambios_no_reemplaza():
    """Lado del user en vivo (auto=False): el motor no mete suplentes por él."""
    from alpha_football.engine import simular_rango
    liga, a, b = dos_equipos()
    c = PC.nuevo_estado(a, b, _once_titular(a), _once_titular(b), auto_l=False)
    random.seed(11); _gl, _gv, evs = simular_rango(a, b, 1, 90, ctx=c)
    assert c.cambios['l'] == 0 and not any(e['tipo'] == 'cambio' and e['lado'] == 'l' for e in evs)
    assert c.cambios['v'] >= 1
    print("  test_sin_auto_cambios_no_reemplaza: OK")


# ---------------------------------------------------------------- Task 3: una sola fuente de verdad
def test_desarrollo_usa_goleadores_reales():
    from alpha_football.engine import simular_partido
    from alpha_football.desarrollo import desarrollar_plantilla_post_partido
    liga, a, b = dos_equipos(); random.seed(21)
    for _ in range(30):
        r = simular_partido(a, b, aplicar_fisico=False)
        if r.goles_local:
            break
    antes = {id(j): j.goles for j in a.jugadores}
    rep = desarrollar_plantilla_post_partido(a, r.goles_local, r.goles_visitante,
                                             stats_partido=PC.stats_de_equipo(r.ctx, r.notas, 'l'))
    for j in a.jugadores:
        assert j.goles - antes[id(j)] == r.ctx.goles.get(K(j), 0), j.apellido
    for fila in rep:
        assert fila['nota'] == r.notas[K(fila['obj'])]
        assert {'jugador_id', 'amarillas', 'roja', 'lesion', 'minutos', 'posicion'} <= set(fila)
    print("  test_desarrollo_usa_goleadores_reales: OK")


def test_desarrollo_sin_stats_compat():
    from alpha_football.desarrollo import desarrollar_plantilla_post_partido
    liga, a, b = dos_equipos()
    rep = desarrollar_plantilla_post_partido(a, 2, 1)
    assert len(rep) == 11 and sum(r['goles'] for r in rep) == 2
    print("  test_desarrollo_sin_stats_compat: OK")


def test_incidencias_del_partido_se_aplican():
    from alpha_football.energia import cerrar_partido
    liga, a, b = dos_equipos(); j = _once_titular(a)[0]; j.lesion_partidos = 0
    inc = cerrar_partido(a, {x.id: 90 for x in _once_titular(a)},
                         incidencias=[{'tipo': 'lesion', 'jugador': j, 'jugador_id': K(j), 'partidos': 3}])
    assert j.lesion_partidos == 3 and inc[0]['jugador'] is j and inc[0]['tipo'] == 'lesion'
    otros = [x for x in a.jugadores if x is not j]
    random.seed(0)
    for _ in range(50):
        cerrar_partido(a, {x.id: 90 for x in _once_titular(a)}, incidencias=[])
    assert all(x.partidos_sancion == 0 for x in otros)   # con incidencias=[] no sortea rojas
    print("  test_incidencias_del_partido_se_aplican: OK")


def test_partido_ia_con_fisico():
    """simular_partido(aplicar_fisico=True) escribe en los jugadores las lesiones del partido."""
    from alpha_football.engine import simular_partido
    liga, a, b = dos_equipos(); random.seed(2)
    for eq in (a, b):
        for j in eq.jugadores:
            j.lesion_partidos = 0; j.partidos_sancion = 0
    for _ in range(40):
        r = simular_partido(a, b)
        les = [i for i in r.ctx.incidencias if i['tipo'] == 'lesion']
        if les:
            break
    assert les and all(r.ctx.jugadores[i['jugador_id']].lesion_partidos >= 1 for i in les)
    print("  test_partido_ia_con_fisico: OK")


if __name__ == '__main__':
    for _n, _f in list(globals().items()):
        if _n.startswith('test_') and callable(_f):
            _f()
    print("OK test_motor_v400")
