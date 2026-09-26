import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame; pygame.init()

errors = []
mods = [
    'alpha_football.ui.menu', 'alpha_football.ui.league_screen',
    'alpha_football.ui.match_screen',
    'alpha_football.ui.copa_screen', 'alpha_football.ui.career_screen',
    'alpha_football.ui.team_screen', 'alpha_football.ui.options_screen',
    'alpha_football.ui.prepartido_screen', 'alpha_football.ui.ofertas_screen',
    'alpha_football.ui.stats_screen', 'alpha_football.ui.save_slots_screen',
    'alpha_football.ui.resumen_temporada_screen', 'alpha_football.ui.edit_screen',
    'alpha_football.ui.promo_releg_screen',
]
for m in mods:
    try:
        __import__(m)
        print(f'  OK: {m}')
    except Exception as e:
        errors.append(f'{m}: {e}')
        print(f'  FAIL: {m} - {e}')
print(f'\nTotal errors: {len(errors)}')
if errors:
    sys.exit(1)
