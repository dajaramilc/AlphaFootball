# Sub-proyecto 5 — 8 países, ligas de 12 y editor de ligas (v3.7.0)

**Fecha:** 2026-09-23 · **Decidido por Diego:** clubes Y jugadores reales parodiados; 12 equipos ida y
vuelta en 1ª y 2ª; añadir Italia, Uruguay y Ecuador ("misma lógica"). Resto decidido por Claude.

## 1. Países y ligas
- `PAISES_DISPONIBLES` / `TIPOS_LIGA` / `CONFIGURACION_LIGAS` (menu.py) pasan de 5 a 8 países:
  premier, laliga, **seriea** (Italia), betplay, brasil, argentina, **uruguay**, **ecuador**.
  Cada país con 1ª y 2ª → **16 ligas vivas**. Módulos `data/<tipo>.py` y `data/segunda_<tipo>.py` para los
  3 nuevos (mismo formato que `data/premier.py` / `segunda_premier.py`).
- Nombres: "Serie A Parodia", "Liga AUF Uruguaya Parodia", "LigaPro Ecuador Parodia" (editables, ver 5).
- Región: Europa = premier, laliga, seriea; Sudamérica = betplay, brasil, argentina, uruguay, ecuador
  (todas las listas `TIPOS_LATAM`, `TIPOS_SUDAMERICA`, `es_sud`, `_es_europa`, `LIGAS_COPA`,
  `PESO_LIGA_1A`, `FUERZA_LIGA`, `PRESUPUESTO_RANGO`, `PAIS_CORTO`, `CUPOS_COPA`… se centralizan en
  `alpha_football/paises.py` y se importan de ahí). Techo de media sudamericano (81) aplica a uruguay y
  ecuador.

## 2. 12 equipos, ida y vuelta
- Todas las 1ª y 2ª tienen 12 clubes → 22 jornadas (`num_jornadas = 2·(n−1)`, derivado del número de
  equipos, no fijo por liga). `generar_fixture` ya soporta n par.
- Ascensos/descensos: siguen 2 y 2 por país.
- Las cosas que dependen de `num_jornadas` (ventana de mercado: primeras 3 y últimas 3; pedidos de la
  directiva; mitad de temporada; copa) ya son relativas; se revisan las que tengan números fijos.
- Rendimiento: simular una jornada de las 16 ligas debe tardar < 1.5 s headless.

## 3. Datos (reales, parodiados)
- Cada liga: los 12 clubes reales 2025-26 de esa categoría (1ª: top 12 por nivel/popularidad; 2ª: 12 de
  la segunda categoría real), con nombre parodia en el estilo actual, ciudad, estrellas, balance,
  estilo, y **20-25 jugadores reales parodiados** (nombre y apellido parodia reconocible, posición, media
  realista para la escala del juego, rasgo, edad real).
- Se conservan los clubes y jugadores que ya existen (se agregan los que faltan hasta 12).
- 2ª de ligas chicas (Uruguay, Ecuador, Colombia…): si no se conoce el plantel real, jugadores con
  nombres plausibles del país (la regla es que suenen reales y parodiados).
- Clásicos de las ligas nuevas en `data/clasicos.py`; DTs reales de las 1ª nuevas en
  `data/entrenadores.py` (`DT_REALES`).
- Los clubes de Uruguay/Ecuador/Italia que hoy están en `data/internacional.py` (Peñarol, Nacional,
  Barcelona SC, LDU, Juventus, Milan…) pasan a su liga y salen del pool internacional (sin duplicados).

## 4. Base editada y partidas guardadas
- `alpha_football_edited_db.json` sigue siendo la principal, pero `load_league_teams` **agrega** los
  clubes de los datos que no estén en la base editada (por nombre), hasta 12. Las ligas nuevas se cargan
  de los datos si la base editada no las tiene.
- Partidas guardadas: al empezar la temporada siguiente (`avanzar_nueva_temporada`), cada liga se
  completa hasta 12 con los clubes que falten y se cargan los países que falten. La temporada en curso
  del save viejo termina con su formato.

## 5. Editor de ligas
- Pestañas del editor por país (8) con selector 1ª / 2ª (hoy solo 5 pestañas de 1ª + copas).
- **Renombrar liga:** campo "Nombre de la liga" tecleable; se guarda en la base editada en
  `"_ligas": {tipo: {"nombre": ..., "nombre_2a": ...}}` y lo usan todas las pantallas (hub, OTRAS LIGAS,
  alta de carrera, resumen).
- Menús del alta de carrera (país → división → club) con los 8 países (grilla 4×2) y el texto correcto
  de equipos/jornadas por liga (arregla el pendiente "8 equipos · 14 jornadas" para todas).

## Pruebas
`tests/test_ligas_v370.py`: 8 países × 2 divisiones cargan 12 equipos con ≥ 20 jugadores válidos;
`num_jornadas == 22`; sin nombres de club repetidos en todo el juego ni con el pool internacional;
medias dentro de la escala (Sudamérica ≤ 81); cada 1ª con DT real y cada club con clásico cuando existe;
merge de base editada (club editado conservado + faltantes agregados); save viejo de 6 equipos se
completa al avanzar temporada; renombrar liga persiste y se ve; rendimiento de una jornada < 1.5 s.
