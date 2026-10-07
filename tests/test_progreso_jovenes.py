"""v0.4.10.0: los menores de 21 progresan un poco más rápido."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
from alpha_football.desarrollo import _factor_progreso_edad as f


def test_menores_de_21_progresan_mas():
    assert f(16) == f(20) == 0.90
    assert f(21) == 0.75                     # los de 21 no cambian
    assert f(20) > f(21) > f(24) > f(27) > f(30) > f(31)


def test_resto_de_tramos_igual():
    assert (f(24), f(27), f(30), f(35)) == (0.55, 0.40, 0.25, 0.08)


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
