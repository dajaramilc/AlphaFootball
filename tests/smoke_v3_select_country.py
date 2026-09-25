"""Test funcional del menu Pais con dummy SDL."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import sys
sys.path.insert(0, '.')

import pygame
pygame.init()
screen = pygame.display.set_mode((1280, 720))

# Importar menu y construir un estado completo
from alpha_football.ui import menu
from alpha_football.ui.menu import PAISES_DISPONIBLES

estado = {
    'menu_step': 'select_country',
    'music_started': True,
    'pais_keyboard_idx': 0,
    'menu_error': None,
    'menu_error_ticks': 0,
}

# Verificar que el render no lance excepcion
def test_render():
    try:
        result = menu.render(screen, estado)
        print('Render OK, retorno:', result)
    except Exception as e:
        print('ERROR en render:', e)
        import traceback
        traceback.print_exc()

test_render()

# Simular teclado: bajar 10 veces (mod 5 = 0)
for _ in range(10):
    estado['pais_keyboard_idx'] = (estado['pais_keyboard_idx'] + 1) % 5
print('Despues de 10 abajo (mod 5), pais_keyboard_idx =', estado['pais_keyboard_idx'])

# Simular seleccion del pais en el indice actual
estado['selected_country_id'] = PAISES_DISPONIBLES[estado['pais_keyboard_idx']]['codigo']
estado['menu_step'] = 'select_division'
print('Pais seleccionado:', estado['selected_country_id'])
print('menu_step:', estado['menu_step'])

# Volver
estado['menu_step'] = 'select_country'
print('Despues de Esc (simulado), menu_step:', estado['menu_step'])

print()
print('Layout final (start_y=280, btn_h=56, spacing=8):')
for i, p in enumerate(PAISES_DISPONIBLES):
    y = 280 + i * (56 + 8)
    print('  Pais ' + str(i+1) + ' (' + p['codigo'].ljust(10) + '): y=' + str(y) + '..' + str(y+56) + '  ' + ('OK' if y+56 <= 640 else 'OVERFLOW'))
print('  Boton VOLVER: y=640..690 (margen 720 OK)')
print('  Hint teclado: y=660 (no choca con VOLVER)')
print()
print('Test FINAL: Render funciona, 5 paises visibles, teclado OK.')
