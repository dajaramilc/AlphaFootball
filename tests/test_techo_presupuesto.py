"""0.4.25.0: ningún club puede tener más de 350 M€ de presupuesto (migración al cargar + red de seguridad diaria) y
todos los clubes de la IA reajustan su presupuesto al empezar cada temporada, con la misma fórmula que el user."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import finanzas as F
from alpha_football import dias as D
from alpha_football import mercado_ia as MIA
from alpha_football import nivel_temporada as NT

TECHO = 350_000_000


def _clubes(e):
    vistos, out = set(), []
    for clave in ('primera_division', 'segunda_division'):
        for liga in (e.get(clave) or {}).values():
            for eq in liga.equipos:
                if id(eq) not in vistos:
                    vistos.add(id(eq))
                    out.append(eq)
    return out


def _club_ia_modesto(e):
    """El club de la IA con la base de presupuesto más baja: ahí el techo nunca interviene."""
    mi = e['mi_equipo']
    candidatos = [(F.presupuesto_base(c, t, d), c, t, d) for liga, t, d in MIA.ligas_de_la_partida(e)
                  for c in liga.equipos if c is not mi]
    base, club, tipo, division = min(candidatos, key=lambda x: x[0])
    return club, tipo, division, base


def test_el_techo_es_de_350_millones():
    assert F.TECHO_PRESUPUESTO == TECHO


def test_limitar_presupuestos_recorta_a_los_clubes_pasados():
    e = estado_carrera()
    mi_equipo = e['mi_equipo']
    clubes = [eq for eq in _clubes(e) if eq is not mi_equipo]
    grande, otro, chico = clubes[0], clubes[1], clubes[2]
    grande.balance, otro.balance = 3_121_808_205, TECHO + 1
    chico.balance = 150_000_000
    mi_equipo.balance = 600_000_000                                      # el tuyo también
    n = F.limitar_presupuestos(e)
    assert n >= 3
    assert grande.balance == TECHO and otro.balance == TECHO and mi_equipo.balance == TECHO
    assert chico.balance == 150_000_000                                  # los que no pasan, intactos
    assert all(int(eq.balance) <= TECHO for eq in _clubes(e))
    assert F.limitar_presupuestos(e) == 0                                # idempotente


def test_un_club_justo_en_el_techo_no_se_toca_y_un_saldo_negativo_tampoco():
    e = estado_carrera()
    a, b = [eq for eq in _clubes(e) if eq is not e['mi_equipo']][:2]
    e['mi_equipo'].balance = 10_000_000
    a.balance, b.balance = TECHO, -5_000_000
    assert F.limitar_presupuestos(e) == 0
    assert a.balance == TECHO and b.balance == -5_000_000


def test_sin_partida_no_lanza():
    assert F.limitar_presupuestos({}) == 0
    assert F.limitar_presupuestos({'primera_division': None, 'mi_equipo': None}) == 0


def test_el_reloj_lo_aplica_cada_dia():
    e = estado_carrera()
    club = _clubes(e)[0]
    club.balance = 900_000_000
    D.hoy(e)                                                              # crea el reloj
    D.revisar_dia(e, D.hoy(e))
    assert club.balance == TECHO


def test_el_cobro_de_fin_de_temporada_respeta_el_techo():
    import random
    e = estado_carrera()
    club = _clubes(e)[0]
    club.balance = TECHO - 1_000                                          # cobra un ingreso enorme y se pasaría
    MIA.ingresos_fin_temporada(e, random.Random(1))
    assert all(int(eq.balance) <= TECHO for eq in _clubes(e))


def test_el_presupuesto_nuevo_del_user_tampoco_pasa_del_techo():
    info = F.presupuesto_temporada(500_000_000, 900_000_000, 'superado', True, True)    # ×1.65 × 1.20 = 990 M€ sin techo
    assert info['total'] == TECHO
    assert F.presupuesto_temporada(100_000_000, 20_000_000, 'cumplido')['total'] < TECHO   # el techo no toca a los normales


def test_la_ia_reajusta_su_presupuesto_en_cada_temporada():
    import random
    e = estado_carrera()
    club, tipo, division, base = _club_ia_modesto(e)
    club.balance = 340_000_000                  # bajo el techo: antes esta fortuna se arrastraba entera año tras año
    MIA.ingresos_fin_temporada(e, random.Random(1))
    assert club.balance <= int(base * 2), "el presupuesto se reajusta sobre su base (máximo ×1.98), no se acumula"


def _cobertura(e, club, tipo, division):
    """Lo que le falta al club para pagar sus sueldos en una temporada mala (el margen de mercado_ia.cuentas)."""
    ingresos, gasto, _margen = MIA.cuentas(e, club, tipo, division)
    return max(0, gasto - int(ingresos * MIA.VARIACION_INGRESOS_IA[0]))


def test_el_club_de_la_ia_en_quiebra_queda_con_su_presupuesto_minimo():
    import random
    e = estado_carrera()
    club, tipo, division, base = _club_ia_modesto(e)
    club.balance = -500_000_000
    quebrados = MIA.ingresos_fin_temporada(e, random.Random(1))
    assert club.nombre in quebrados                                       # la quiebra se decide antes del reajuste
    # como el user: deuda descontada y piso del 10% de la base; la directiva cubre además el hueco de sueldos
    assert club.balance == max(int(base * F.PISO_PRESUPUESTO), _cobertura(e, club, tipo, division))


def test_ningun_club_de_la_ia_arranca_sin_poder_pagar_los_sueldos_de_una_temporada_mala():
    """El reajuste le quita a la IA el colchón que le daba acumular saldo (recién descendidos y clubes de 2ª con más
    sueldos que ingresos quebraban año tras año): la directiva cubre el hueco, salvo que el techo no lo permita."""
    import random
    e = estado_carrera()
    mi = e['mi_equipo']
    MIA.ingresos_fin_temporada(e, random.Random(1))
    for liga, tipo, division in MIA.ligas_de_la_partida(e):
        for club in liga.equipos:
            if club is mi:
                continue
            _ing, _gasto, margen = MIA.cuentas(e, club, tipo, division)
            assert margen >= 0 or club.balance == TECHO, (club.nombre, margen, club.balance)


def test_la_cobertura_sube_el_presupuesto_pero_nunca_pasa_del_techo():
    e = estado_carrera()
    club, tipo, division, base = _club_ia_modesto(e)
    club.balance = base
    formula = F.presupuesto_nuevo_ia(club, tipo, division)
    assert F.presupuesto_nuevo_ia(club, tipo, division, cobertura=0) == formula
    assert F.presupuesto_nuevo_ia(club, tipo, division, cobertura=formula // 2) == formula   # ya lo cubre
    assert F.presupuesto_nuevo_ia(club, tipo, division, cobertura=formula * 3) == formula * 3
    assert F.presupuesto_nuevo_ia(club, tipo, division, cobertura=TECHO * 4) == TECHO


def test_el_resultado_de_la_temporada_pesa_en_el_presupuesto_de_la_ia():
    e = estado_carrera()
    club, tipo, division, base = _club_ia_modesto(e)
    club.balance = base
    campeon = F.presupuesto_nuevo_ia(club, tipo, division, 'superado', True)
    cumplido = F.presupuesto_nuevo_ia(club, tipo, division, 'cumplido', False)
    fallado = F.presupuesto_nuevo_ia(club, tipo, division, 'fallado', False)
    sin_dato = F.presupuesto_nuevo_ia(club, tipo, division)
    assert campeon > cumplido > fallado
    assert fallado < sin_dato < campeon                                   # sin dato del objetivo: la parte neutra


def test_preparar_guarda_el_resultado_de_cada_club_de_la_ia():
    e = estado_carrera()
    mi = e['mi_equipo']
    NT.preparar(e)
    res = e['datos_carrera']['resultados_ia']
    assert mi.nombre not in res                                           # el user se evalúa por su directiva
    for liga, _tipo, division in MIA.ligas_de_la_partida(e):
        ia = [c for c in liga.equipos if c is not mi]
        assert all(c.nombre in res and res[c.nombre][0] in ('superado', 'cumplido', 'fallado') for c in ia)
        campeones = [c for c in ia if res[c.nombre][1]]
        if division != 1:
            assert not campeones                                          # solo se corona el campeón de 1ª
            continue
        lider = max(liga.equipos, key=NT._clave_tabla)
        if lider is mi:
            assert not campeones
        else:
            assert campeones == [lider]


def test_el_cobro_consume_el_resultado_guardado():
    import random
    e = estado_carrera()
    club, _tipo, _division, _base = _club_ia_modesto(e)
    e['datos_carrera']['resultados_ia'] = {club.nombre: ['superado', True]}
    MIA.ingresos_fin_temporada(e, random.Random(1))
    assert club.nombre not in e['datos_carrera']['resultados_ia']         # no queda para la temporada siguiente


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
