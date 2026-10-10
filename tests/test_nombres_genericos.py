"""0.4.22.0: nombres y apellidos genéricos para los 8 países (regens, canteranos, libres)."""
import sys, os, re, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from alpha_football.paises import PAISES
from alpha_football.models import Jugador
from alpha_football import retiros as R

LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñãõçâêôàèìòùï' -]+$")


def _banco():
    from alpha_football.data.nombres_genericos import NOMBRES_POR_PAIS
    return NOMBRES_POR_PAIS


def test_ocho_paises_con_100_o_mas():
    N = _banco()
    assert set(N) == {p['nombre'] for p in PAISES}
    for pais, (nombres, apellidos) in N.items():
        assert len(nombres) >= 100, (pais, len(nombres))
        assert len(apellidos) >= 100, (pais, len(apellidos))


def test_sin_repetidos():
    for pais, (nombres, apellidos) in _banco().items():
        assert len(set(nombres)) == len(nombres), f"{pais}: nombres repetidos"
        assert len(set(apellidos)) == len(apellidos), f"{pais}: apellidos repetidos"


def test_texto_limpio():
    for pais, listas in _banco().items():
        for lista in listas:
            for x in lista:
                assert x and x == x.strip() and LETRAS.match(x), (pais, x)


def test_retiros_usa_el_banco_nuevo():
    from alpha_football.data import nombres_genericos
    assert R.NOMBRES_POR_PAIS is nombres_genericos.NOMBRES_POR_PAIS


def test_regen_uruguayo_no_sale_con_nombre_espanol():
    N = _banco()
    viejo = Jugador(nombre="Luis", apellido="Gómez", posicion="DEL", ataque=70, defensa=40, fisico=65,
                    tecnica=70, mental=65, id=991, edad=36, nacionalidad="Uruguay")
    for semilla in range(30):
        regen = R.generar_regen(viejo, random.Random(semilla), 992, set(), pais_club='Uruguay')
        assert regen.nacionalidad == 'Uruguay'
        assert regen.nombre in N['Uruguay'][0] and regen.apellido in N['Uruguay'][1], \
            (regen.nombre, regen.apellido)


def test_nombre_unico_respeta_el_pais():
    from alpha_football import nombres as NM
    N = _banco()
    for pais in ('Italia', 'Ecuador', 'Uruguay'):
        n, a = NM.nombre_unico(pais, random.Random(3), reservar=False)
        assert n in N[pais][0] and a in N[pais][1], (pais, n, a)


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
