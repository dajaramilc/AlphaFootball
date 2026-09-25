# -*- coding: utf-8 -*-
"""
v3.1.0: clásicos reales por liga. Cada par = (fragmento del nombre del club, fragmento del rival),
en minúsculas, para reconocer las parodias. El primer par que menciona a un club define su rival;
un partido es clásico si CUALQUIERA de los dos tiene al otro de rival. Editable en el editor.
"""
from __future__ import annotations

CLASICOS = [
    ('real vadrid', 'farcelona'), ('patetico', 'real vadrid'), ('flaco de bilbao', 'suciedad'),
    ('gordona', 'farcelona'),
    ('desunido', 'billete'), ('higado', 'desunido'), ('pechofrio', 'spurs'), ('chelsea', 'pechofrio'),
    ('flamenguito', 'flumando'), ('palmerinha', 'don pablo'), ('botaagua', 'flamenguito'),
    ('boca grande', 'river au'), ('desindependiente', 'corriendo'), ('san lorenzont', 'boca grande'),
    ('talleres', 'belgrano'),
    ('pobres vagos', 'chanda fe'), ('aberica', 'deportivo casi'), ('narconal', 'junior daddy'),
    # v3.7.0 Europa: ligas de 12 (Premier, LaLiga, Serie A y sus 2ª).
    ('real madriz', 'farcelona'), ('athletic de bilbao', 'suciedad'),
    ('manque pierda', 'sin monchi'), ('oxidado', 'sin estadio'), ('celta de viejo', 'depor tivo'),
    ('caramelo', 'higado'), ('petrodolar', 'sunderland'), ('algoritmo', 'palacete'),
    ('inter de milan', 'milan abuelo'), ('piamonte', 'inter de milan'), ('granate triste', 'piamonte'),
    ('imperio caido', 'aguila calva'), ('pizzeria', 'imperio caido'), ('violeta marchita', 'mortadela'),
    ('pesto', 'sampdoria'), ('tractorista', 'canarito'),
    # v3.7.0 Sudamérica A: ligas de 12 (Brasil, Argentina, BetPlay y sus 2ª).
    ('corinchados', 'palmerinha'), ('colorado desteñido', 'gremiont'),
    ('galo cansado', 'cruzeiro endeudado'), ('vasco da goma', 'flamenguito'), ('furacão', 'coxa branca'),
    ('huracán brisa', 'san lorenzont'), ('rosario canalla', 'newells'), ('chacarita', 'atlanta bohemio'),
    ('vélez sarsfall', 'ferro carril'),
    ('montaña rusa', 'narconal'), ('matecaña', 'once faldas'), ('leopardos', 'cúcuta motilón'),
    ('huila opita', 'llorima'), ('patriotas sin patria', 'chicó'),
    # v3.7.0 Uruguay/Ecuador: ligas de 12 (Liga AUF, LigaPro y sus 2ª).
    ('penarol roto', 'nacionall'), ('defensor esporting', 'danubio seco'),
    ('wanderers perdidos', 'river platita'), ('liverpul uruguayo', 'cerro bajo'),
    ('rampla juniors', 'cerro bajo'), ('villa espanola', 'central espanol'),
    ('barcelona falso', 'emelec sin luz'), ('liga de quito rota', 'el nacional importado'),
    ('independiente del valle', 'liga de quito rota'), ('aucas ausentes', 'universidad catolica atea'),
    ('tecnico universitario', 'macara macarena'), ('mushuc ruina', 'tecnico universitario'),
    ('cumbaya bailongo', 'independiente juniors'), ('9 de octubre', 'guayaquil city'),
]


def _buscar(equipos: list, fragmento: str):
    return next((e for e in equipos if fragmento in str(getattr(e, 'nombre', '')).lower()), None)


def asignar_rivales(equipos: list) -> None:
    for eq in equipos:
        if getattr(eq, 'rival', ''):
            continue
        nombre = str(getattr(eq, 'nombre', '')).lower()
        for a, b in CLASICOS:
            otro = b if a in nombre else a if b in nombre else None
            rival = _buscar(equipos, otro) if otro else None
            if rival is not None and rival is not eq:
                eq.rival = rival.nombre
                break


def es_clasico(a, b) -> bool:
    ra, rb = getattr(a, 'rival', ''), getattr(b, 'rival', '')
    return bool((ra and ra == getattr(b, 'nombre', None)) or (rb and rb == getattr(a, 'nombre', None)))
