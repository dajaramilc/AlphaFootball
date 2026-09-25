# Resumen de cambios — Sesión 2026-06-26 (v2.3 → v2.3.3 Alpha Football)

Este documento detalla **TODAS** las modificaciones realizadas al proyecto Alpha Football en la sesión de hoy (26 de junio de 2026), desde la v2.3 inicial hasta la v2.3.3 actual. Los cambios están agrupados en **bloques temáticos** con referencia exacta a archivos, líneas y el razonamiento detrás de cada fix.

> **Estado al cierre:** v2.3.3 con `python -m compileall` en 0 errores. Tests E2E headless validados. Pendiente: validación en vivo de los 6 puntos mencionados al final.

---

## 📋 Índice de bloques

1. [Bug crítico: `pos_user` UnboundLocalError](#fase-1--fix-bug-pos_user-unboundlocalerror)
2. [Bono 2ª división ×2](#fase-2--bono-2ª-división-×2)
3. [Campos nuevos en modelos (Liga.division, Equipo.division, EstadoJuego.segunda_division, Alineacion.convocados)](#fase-3--campos-nuevos-en-modelos)
4. [Datos de 2ª división: 5 archivos × 6 equipos × 25 jugadores = 750 parodiados](#fase-4--datos-de-2ª-división)
5. [Plantilla 25 jugadores + tope 40](#fase-5--plantilla-25-jugadores)
6. [Sistema de promoción/relegación atómico](#fase-6--promociónrelegación-atómica)
7. [Simulación automática de jornada 2ª división](#fase-7--simulación-jornada-2ª-división)
8. [Compatibilidad saves v5 → v2.3](#fase-8--compatibilidad-de-saves)
9. [Menú País → División → Equipo (nueva partida + amistoso)](#fase-9--menú-país--división--equipo)
10. [Team screen PES-style (click campo + swap con banco)](#fase-10--team-screen-pes-style)
11. [Toggle 1ª⇄2ª división en league_screen](#fase-11--toggle-1ª⇄2ª-en-league_screen)
12. [Bugfix carga: `load_division_teams` recibía `country_id` en vez de `liga_id`](#fase-13--bugfix-crítico-de-carga-de-ligas)
13. [Fix `click_pos referenced before assignment` en league_screen](#fase-14--fix-clickpos-en-league_screen)
14. [Bugs que rompían el flujo de inicio de carrera](#fase-15--bugs-que-rompían-el-flujo-de-inicio-de-carrera)
15. [Teclado en cicladores formación/táctica de team_screen](#fase-16--teclado-en-cicladores)
16. [Bug de doble `pygame.event.get()` consumía los KEYDOWN](#fase-17--bug-de-doble-event-get)
17. [Colores tabla según división (verde top-N / rojo bottom-N)](#fase-18--colores-tabla-según-división)
18. [Fix "Sin rival programado" en 2ª división](#fase-19--fix-sin-rival-programado-en-2ª-división)
19. [Teclado global en TODAS las pantallas](#fase-20--teclado-global-en-todas-las-pantallas)
20. [Pantalla de Promoción/Relegación](#fase-21--pantalla-de-promociónrelegación)
21. [Bugfix final: `dir_hab` referenced before assignment](#fase-22--bugfix-final-dir_hab-referenced-before-assignment)

---

## FASE 1 — Fix bug `pos_user` UnboundLocalError

**Archivo:** `alpha_football/ui/resumen_temporada_screen.py`

**Problema:**
La variable `pos_user` solo se asignaba dentro del bloque `else:` de `if usuario_es_campeon:` (línea ~310). Cuando el usuario resultaba campeón, ese bloque no se ejecutaba y `pos_user` quedaba sin asignar. El `try/except` posterior (banner de bono, líneas 314-357) capturaba `UnboundLocalError` cada frame, generando **~1000 líneas de spam en el log por sesión**.

**Síntoma observado:**
```text
ERROR - Error crítico en render de resumen_temporada_screen: local variable 'pos_user' referenced before assignment
```

**Fix aplicado (línea ~310):**
```python
# ANTES:
if usuario_es_campeon:
    pos_user = 1
else:
    pos_user = 2  # etc

# AHORA:
pos_user = 1  # default seguro ANTES del if
if usuario_es_campeon:
    pos_user = 1
else:
    pos_user = 2
```

Inicialización defensiva antes del `if` para que la variable SIEMPRE esté asignada, sin importar qué rama se tome.

---

## FASE 2 — Bono 2ª división ×2

**Archivo:** `alpha_football/ui/resumen_temporada_screen.py`

**Problema:**
El cálculo de bono de fin de temporada usaba una tabla fija sin importar la división. Un equipo que ganara la 2ª división recibía el mismo bono que uno en 1ª (ej: BetPlay 2ª campeón = €2M, igual que 1ª). Diego pidió que el bono de 2ª sea **×2** sobre el de 1ª.

**Cambios:**

1. **Tablas de bono divididas por división:**
   - `TABLA_BONO_LIGA_1A`: posición 1 → €30M, 2 → €18M, 3 → €10M, 4 → €5M, 5+ → €2M
   - `TABLA_BONO_LIGA_2A`: posición 1 → €60M, 2 → €36M, 3 → €20M, 4 → €10M, 5+ → €4M

2. **Constante `_BONO_LIGA_2A_X2 = 2`** expuesta a nivel de módulo (línea ~22) para auditoría.

3. **Función `calcular_bono_liga(estado, liga, division)` (líneas ~25-65, NUEVA):**
   - Recibe división (1 o 2)
   - Lee bono base según posición final
   - Escala por fuerza de liga (Premier > BetPlay)
   - Aplica `_BONO_LIGA_2A_X2` si `division == 2`
   - Retorna `{'bono_liga': X, 'bono_copa': Y, 'total': Z, 'division': 1|2}`

4. **Llamadas actualizadas** en `avanzar_nueva_temporada` (línea ~120) y `render` (línea ~290):
   - Antes: `bono_liga = calcular_bono_liga(estado)`
   - Ahora: `bono_liga = calcular_bono_liga(estado, liga_usuario, division_usuario)`

5. **Banner de resumen** (líneas ~340-360) muestra la división: `"¡CAMPEÓN DE 2ª DIVISIÓN! Bono: €60M (×2)"`.

---

## FASE 3 — Campos nuevos en modelos

**Archivo:** `alpha_football/models.py`

Todos los campos nuevos son **retrocompatibles con saves v5** (defaults sensatos).

1. **`class Liga` (línea ~70)** — campo `division: int = 1`:
   ```python
   @dataclass
   class Liga:
       nombre: str
       tipo: str
       equipos: list = field(default_factory=list)
       num_jornadas: int = 10
       division: int = 1  # NUEVO
   ```

2. **`class Equipo` (línea ~100)** — campo `division: int = 1`:
   - Copiado desde `liga.division` al construir el equipo
   - Se actualiza en el swap de promoción/relegación

3. **`class EstadoJuego` (línea ~250)** — 2 campos nuevos:
   - `liga_usuario_division: int = 1` — división actual del usuario
   - `segunda_division: Optional[Liga] = None` — referencia a la 2ª división de su liga

4. **`class Alineacion` (línea ~290)** — campo `convocados: List[int] = field(default_factory=list)`:
   - IDs de los 10 jugadores que van al banco (los otros 15 quedan como reservas)
   - PES-style: el DT elige 10 entre los 25 totales para que vayan al banco
   - Default `[]` → `match_screen` calcula automáticamente los 10 mejores no titulares

5. **`class Jugador` (v0.8.9)** — campo `potencial: int = 0`:
   - Techo máximo de OVR al que puede llegar
   - Se deriva perezosamente con `calcular_potencial(overall, edad, rng)`

---

## FASE 4 — Datos de 2ª división (5 archivos nuevos)

**Archivos creados (6 equipos × 25 jugadores cada uno = 150 por liga):**

| Archivo | Equipos | Jugadores | OVR rango |
|---|---|---|---|
| `alpha_football/data/segunda_betplay.py` | 6 | 150 | 50-65 |
| `alpha_football/data/segunda_laliga.py` | 6 | 150 | 60-72 |
| `alpha_football/data/segunda_premier.py` | 6 | 150 | 60-72 ("Championship") |
| `alpha_football/data/segunda_brasil.py` | 6 | 150 | 55-70 ("Série B") |
| `alpha_football/data/segunda_argentina.py` | 6 | 150 | 50-65 ("Primera Nacional") |

**Total: 750 jugadores parodiados manualmente** (no autogenerados). Estructura típica:

```python
def get_liga():
    equipos = []
    for datos_equipo in DATOS_EQUIPOS_2A:
        jugadores = []
        for datos_jugador in datos_equipo['plantilla']:
            jugadores.append(Jugador(
                id=datos_jugador['id'],
                nombre=datos_jugador['nombre'],
                posicion=datos_jugador['posicion'],
                overall=datos_jugador['overall'],
                edad=datos_jugador['edad'],
                valor=calcular_valor_inicial(...),
                potencial=calcular_potencial(...),
                # ... resto de atributos
            ))
        equipos.append(Equipo(
            id=datos_equipo['id'],
            nombre=datos_equipo['nombre'],
            nombre_corto=datos_equipo['corto'],
            tipo='betplay',  # mismo tipo que 1ª
            division=2,
            jugadores=jugadores,
            presupuesto=BUDGET_2A,  # menor que 1ª
        ))
    return Liga(
        nombre='Liga BetPlay Dimayor Parodia - Segunda División',
        tipo='betplay',
        division=2,
        equipos=equipos,
        num_jornadas=10,
    )
```

---

## FASE 5 — Plantilla 25 jugadores + tope 40

**Archivos:** `alpha_football/plantilla.py`, `alpha_football/market.py`, `alpha_football/ui/match_screen.py`

**Problema:** El juego tenía tope de 21 jugadores por equipo y 32 en plantilla máxima global. Inconsistente con la nueva visión de 25.

**Cambios:**

1. **`plantilla.py:45`** — `def expandir_plantilla(equipo, objetivo=25)`:
   - Default cambiado de 21 → **25**
   - Si el equipo tiene menos de 25, agrega jugadores hasta llegar (resiliencia)

2. **`plantilla.py:104`** — `def expandir_liga(liga, objetivo=25, tope=40)`:
   - Default cambiado de 21 → **25**
   - Idempotente (no duplica si ya tiene 25)

3. **`market.py:30`** — `PLANTILLA_MAXIMA = 40`:
   - Antes: 32
   - Ahora: 40 (permite 25 titulares + 15 margen para traspasos)
   - El chequeo `_puede_fichar` ahora verifica `len(equipo.jugadores) < PLANTILLA_MAXIMA` (40)

4. **`match_screen.py:720`** (función `_banco_para_partido`):
   - Antes: tomaba los primeros 11 de `equipo.jugadores` que no eran titulares
   - Ahora: filtra por `alin.convocados` (PES-style) si está poblado
   - Fallback: si `alin.convocados` está vacío (saves viejos), usa los 11 mejores no titulares

---

## FASE 6 — Promoción/Relegación atómica

**Archivo:** `alpha_football/ui/resumen_temporada_screen.py`

**Problema:** No había mecanismo de ascenso/descenso entre divisiones. Decisión de diseño: **swap directo top-2 ↔ bottom-2 sin playoff**, según preferencia de Diego. Ascenso/descenso infinitas veces.

**Cambios en `avanzar_nueva_temporada` (líneas ~221-292):**

1. **Cálculo de ordenamientos** (líneas 232-249):
   ```python
   # Top 2 de 2ª (descendente por puntos; en empates por DG)
   equipos_2_ord = sorted(
       liga_b.equipos,
       key=lambda e: (-puntos, -dg, -gf)
   )
   # Bottom 2 de 1ª (ascendente)
   equipos_1_ord = sorted(
       liga.equipos,
       key=lambda e: (puntos, dg, gf)
   )
   ascenden = equipos_2_ord[:2]
   descienden = equipos_1_ord[:2]
   ```

2. **Swap atómico de referencias (líneas 256-265):**
   ```python
   for eq in ascenden:
       if eq in liga_b.equipos:
           liga_b.equipos.remove(eq)
           liga.equipos.append(eq)
           eq.division = 1
   for eq in descienden:
       if eq in liga.equipos:
           liga.equipos.remove(eq)
           liga_b.equipos.append(eq)
           eq.division = 2
   ```

3. **Banner según estado del usuario (líneas 263-289):**
   - Verde si ascendió
   - Rojo si descendió
   - Dorado si nada
   - Si descendió: `copa_user_en_copa=False`, `copa_clasificado=False`
   - Si ascendió o descendió: `estado['liga_usuario_division']` actualizado

4. **`promo_releg_resultado` (líneas 269-274)** — guard para el banner del resumen:
   ```python
   estado['promo_releg_resultado'] = {
       'ascendieron': [getattr(e, 'nombre', '?') for e in ascenden],
       'descendieron': [getattr(e, 'nombre', '?') for e in descienden],
       'user_ascendio': user_asc,
       'user_descendio': user_des,
   }
   ```

---

## FASE 7 — Simulación jornada 2ª división

**Archivos:** `alpha_football/ui/league_screen.py`, `alpha_football/ui/match_screen.py`

**Problema:** Solo se simulaba la 1ª división en `finalizar_jornada_liga`. La 2ª quedaba estática.

**Cambios:**

1. **`league_screen.py:400-470`** — nueva función `simular_jornada_segunda_division(estado, jornada)`:
   - Carga `estado['segunda_division']` si no existe
   - Simula los partidos de la jornada en la 2ª división
   - Actualiza tabla de posiciones (puntos, GF, GC)
   - Marca partidos como `jugado=True`

2. **`match_screen.py:1100`** — hook en `finalizar_jornada_liga`:
   - **Decisión:** la 2ª división se simula SIEMPRE en paralelo
   - No importa si el usuario está en 1ª o 2ª; ambas divisiones avanzan

---

## FASE 8 — Compatibilidad de saves

**Archivo:** `alpha_football/ui/menu.py`

**Problema:** Saves anteriores no tienen `liga_usuario_division`, `segunda_division`, `convocados`, ni los 750 jugadores nuevos.

**Cambios en `_aplicar_estado_cargado` (líneas ~1500-1600):**

1. **Inyección de divisiones on-demand (líneas ~1520-1540):**
   ```python
   from alpha_football.data import segunda_betplay, segunda_laliga, segunda_premier, segunda_brasil, segunda_argentina
   MODULOS_2A = {
       'betplay': segunda_betplay,
       'laliga': segunda_laliga,
       'premier': segunda_premier,
       'brasil': segunda_brasil,
       'argentina': segunda_argentina,
   }
   
   tipo_liga = estado.get('liga', {}).get('tipo')
   if tipo_liga in MODULOS_2A and not estado.get('segunda_division'):
       estado['segunda_division'] = MODULOS_2A[tipo_liga].get_liga()
   ```

2. **Migración de equipos (líneas ~1550-1570):**
   ```python
   if 'division' not in liga_cargada:
       liga_cargada['division'] = 1
   for equipo in liga_cargada['equipos']:
       if 'division' not in equipo:
           equipo['division'] = 1
   ```

3. **Migración de alineaciones (líneas ~1575-1595):**
   ```python
   for equipo in liga_cargada['equipos']:
       if 'alineacion_activa' in equipo:
           alin = equipo['alineacion_activa']
           if 'convocados' not in alin:
               alin['convocados'] = []
   ```

**Resultado:** saves viejos cargan sin error, los nuevos campos se inicializan con defaults sensatos.

---

## FASE 9 — Menú País → División → Equipo

**Archivo:** `alpha_football/ui/menu.py` (líneas ~1020-1300)

**Problema:** El menú anterior pasaba directo de Liga → Equipo, sin elegir división ni país explícitamente.

**Cambios:**

1. **Constante `PAISES_DISPONIBLES` (líneas ~33-43):**
   ```python
   PAISES_DISPONIBLES = [
       {'codigo': 'colombia',   'nombre': 'Colombia',   'liga_id': 'betplay',   'emoji': 'CO'},
       {'codigo': 'espana',     'nombre': 'España',     'liga_id': 'laliga',    'emoji': 'ES'},
       {'codigo': 'inglaterra', 'nombre': 'Inglaterra', 'liga_id': 'premier',   'emoji': 'EN'},
       {'codigo': 'brasil',     'nombre': 'Brasil',     'liga_id': 'brasil',    'emoji': 'BR'},
       {'codigo': 'argentina',  'nombre': 'Argentina',  'liga_id': 'argentina', 'emoji': 'AR'},
   ]
   ```

2. **Función `load_division_teams(liga_id, division)` (nueva, líneas ~95-140):**
   ```python
   def load_division_teams(country_id, division):
       # v2.3.1 FIX: traduce country_id → liga_id
       pais = next((p for p in PAISES_DISPONIBLES if p['codigo'] == country_id), None)
       liga_id = pais['liga_id'] if pais else country_id
       if division == 1:
           return load_league_teams(liga_id)
       if division == 2:
           mod = __import__(f'alpha_football.data.segunda_{liga_id}', fromlist=['get_liga'])
           liga_obj = mod.get_liga()
           # ... aplicar expandir_liga(25), escalar_presupuestos, asignar_valores_iniciales
   ```

3. **Nuevo `menu_step == 'select_country'` (líneas ~1020-1110):**
   - Dibuja 5 botones verticales con emoji-pill (🇨🇴 España 🇪🇸, etc.)
   - Botón VOLVER en esquina inferior derecha
   - Hint de teclado en parte inferior izquierda
   - Click → `menu_step = 'select_division'`

4. **Nuevo `menu_step == 'select_division'` (líneas ~1115-1180):**
   - 2 botones grandes centrados: "1ª DIVISIÓN" (verde) y "2ª DIVISIÓN" (azul)
   - Click → carga `load_division_teams(liga_id, division)` y avanza

5. **Pasos de amistoso paralelos (líneas ~1620-1780):**
   - `amistoso_country` y `amistoso_division` siguen el mismo flujo

**Navegación teclado implementada:**
- `↑↓`: mueve índice entre opciones (persistente en `estado['pais_keyboard_idx']`)
- `Enter`: selecciona
- `Esc`: vuelve al paso anterior
- Indicador visual: borde dorado 3px + flecha `▶`

---

## FASE 10 — Team screen PES-style

**Archivo:** `alpha_football/ui/team_screen.py` (reescritura mayor)

**Problema:** La pantalla de equipo era una lista simple sin visualización del campo ni gestión de convocatorias.

**Cambios:**

1. **Estado del team_screen:**
   ```python
   estado['team_seleccion'] = 'titular'  # o 'banco'
   estado['team_view'] = 'equipo'        # o 'reservas'
   estado['_original_convocados'] = []   # backup al entrar
   ```

2. **Modo visualización campo (líneas ~250-380):**
   - Campo de fútbol dibujado (verde con líneas blancas)
   - 11 posiciones según formación activa (4-3-3, 4-4-2, etc.)
   - Click en una posición → muestra el titular asignado
   - Click en jugador del banco → swap con el titular de la posición clickeada

3. **Modo reservas (líneas ~390-480):**
   - Lista de los 15 jugadores NO convocados
   - Click → promueve a convocado (desplaza al último del banco)
   - Botón "VER RESERVAS" / "VOLVER AL CAMPO"

4. **Botones nuevos:**
   - `AUTO CONVOC.` — selecciona automáticamente los 10 mejores no titulares
   - `VER RESERVAS` — toggle entre campo y reservas
   - `CONFIRMAR` — valida que haya 10 convocados
   - `VOLVER` — descarta cambios y vuelve atrás

5. **Función `_auto_convocados(equipo, alin)`:**
   ```python
   def _auto_convocados(equipo, alin):
       """Elige los 10 mejores jugadores no titulares como banco."""
       titulares_ids = set(t.id for t in alin.titulares)
       no_titulares = [j for j in equipo.jugadores if j.id not in titulares_ids]
       no_titulares.sort(key=lambda j: -j.overall)
       return [j.id for j in no_titulares[:10]]
   ```

6. **Validación al confirmar:**
   ```python
   if len(alin.convocados) != 10:
       estado['menu_error'] = 'Debes convocar exactamente 10 jugadores'
       return  # no avanza
   ```

---

## FASE 11 — Toggle 1ª⇄2ª en league_screen

**Archivo:** `alpha_football/ui/league_screen.py`

**Cambios:**

1. **Estado:**
   ```python
   estado['liga_view'] = 'principal'  # o 'segunda'
   ```

2. **Botón "VER 1ª/2ª DIVISIÓN":**
   - Posición: esquina superior derecha de la tabla
   - Click → toggle entre ligas

3. **Render condicional:**
   ```python
   if estado.get('liga_view') == 'principal':
       liga_mostrar = estado['liga']
       titulo = "PRIMERA DIVISIÓN"
   else:
       liga_mostrar = estado['segunda_division']
       titulo = "SEGUNDA DIVISIÓN"
   ```

---

## FASE 13 — Bugfix crítico de carga de ligas

**Archivo:** `alpha_football/ui/menu.py` (`load_division_teams`)

**Síntoma observado:**
```text
ERROR - Error al cargar 2ª división de colombia: No module named 'alpha_football.data.segunda_colombia'
ERROR - Error al cargar liga 'colombia': Liga no soportada por el sistema: colombia
```

**Causa raíz:**
`PAISES_DISPONIBLES` usa códigos de país (`colombia`, `espana`, `inglaterra`), pero los módulos se llaman `data/{betplay,laliga,premier,brasil,argentina}.py`. Mi código pasaba `'colombia'` a `load_division_teams`, que construía `'segunda_colombia'` (no existe).

**Fix (líneas ~211-246):**
```python
def load_division_teams(country_id: str, division: int):
    pais = next((p for p in PAISES_DISPONIBLES if p['codigo'] == country_id), None)
    liga_id = pais['liga_id'] if pais else country_id
    if division == 1:
        return load_league_teams(liga_id)
    if division == 2:
        mod = __import__(f'alpha_football.data.segunda_{liga_id}', fromlist=['get_liga'])
        # ...
```

Traducción `country_id → liga_id` dentro de `load_division_teams`.

**Archivos del bug también arreglados:**
- `expandir_liga(liga_obj, 20)` → `expandir_liga(liga_obj, 25, 40)` (líneas 102 y 136)
- `slot_4.json` corrupto (guardaba con `tipo='colombia'`) → **borrado**

---

## FASE 14 — Fix `click_pos` en league_screen

**Archivo:** `alpha_football/ui/league_screen.py`

**Síntoma observado:**
```text
ERROR - Error crítico en render de league_screen: local variable 'click_pos' referenced before assignment
```

**Causa raíz:**
El bloque del toggle 1ª/2ª (líneas ~430) usaba `click_pos` y `mouse_pos`, pero estos se asignaban más abajo (líneas ~657-667). El primer uso estaba antes de la definición → `UnboundLocalError`.

**Fix aplicado (líneas ~331-352):**
```python
# v2.3.1 (FIX): mouse_pos y click_pos se capturan AQUI para
# que esten disponibles antes de cualquier uso (toggle 1a/2a, banner de
# alerta de copa, etc).
mouse_pos = pygame.mouse.get_pos()
click_pos = None
key_events = []
```

Más abajo (líneas ~704-728), solo se **refresca** `click_pos` con el evento actual.

---

## FASE 15 — Bugs que rompían el flujo de inicio de carrera

**Archivo:** `alpha_football/ui/menu.py` (`dt_setup`)

**Síntoma observado:**
- "Nueva carrera iniciada: liga=colombia equipo=Narconal" en el log, pero `selected_country_id: None`
- Al cargar save, se caía a `Liga Ficticia COLOMBIA` (datos de relleno)

**Causa raíz (múltiple):**

1. **`estado.clear()` borra `selected_country_id`** y luego `estado.get('selected_country_id', '')` siempre devuelve `''` (línea 1427)
2. **`for k in (...): estado.pop(k, None)`** borraba `selected_country_id` y `selected_division` justo después de setearlos (líneas 1508-1512)

**Fix aplicado:**

1. **Capturar ANTES del clear() (líneas ~1410-1415):**
   ```python
   _pais_sel = estado.get('selected_country_id', '')
   _div_sel = int(estado.get('selected_division', 1) or 1)
   estado.clear()
   ```

2. **Usar las locales después del clear (líneas ~1430-1432):**
   ```python
   estado['selected_country_id'] = _pais_sel
   estado['selected_division'] = _div_sel
   estado['liga_usuario_division'] = _div_sel
   ```

3. **NO popear `selected_country_id` ni `selected_division` en el for final (líneas ~1508-1511):**
   ```python
   for k in ('menu_step', 'selected_league_id', 'selected_liga_obj', 'pending_equipo',
             'dt_focus', 'dt_nac_sel', 'dt_nac_custom', 'dt_name_focus',
             'amistoso_phase', 'amistoso_country_id', 'amistoso_division'):
       estado.pop(k, None)
   # NOTA: 'selected_country_id' y 'selected_division' NO se popean aqui.
   ```

---

## FASE 16 — Teclado en cicladores

**Archivo:** `alpha_football/ui/team_screen.py` (líneas ~693-720)

**Cambios:**

1. **Estado de foco:**
   ```python
   if 'team_kbd_focus' not in estado:
       estado['team_kbd_focus'] = 'formacion'  # o 'tactica'
   ```

2. **Handler de teclado extendido:**
   ```python
   elif event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
       # [ / ] cambian formación
       paso = -1 if event.key == pygame.K_LEFTBRACKET else 1
       f_idx = form_lista.index(alin.formacion)
       alin.formacion = form_lista[(f_idx + paso) % len(form_lista)]
       alin.titulares = F.mejor_once(mi_equipo.jugadores, alin.formacion)
   elif event.key in (pygame.K_MINUS, pygame.K_EQUALS):
       # - / + cambian táctica
       paso = -1 if event.key == pygame.K_MINUS else 1
       t_idx = tacticas.index(mi_equipo.estilo_dt)
       mi_equipo.estilo_dt = tacticas[(t_idx + paso) % len(tacticas)]
   elif event.key == pygame.K_a:
       # A = AUTO ONCE (formación + banco)
       alin.titulares = F.mejor_once(...)
       _auto_convocados()
   elif event.key == pygame.K_TAB:
       # TAB alterna foco entre formación y táctica
       estado['team_kbd_focus'] = 'tactica' if estado.get('team_kbd_focus') == 'formacion' else 'formacion'
   ```

3. **Indicador visual:**
   - Borde dorado brillante 3px sobre el cycler enfocado por teclado
   - Flecha `▶` a la izquierda del box
   - Prioridad sobre el hover del mouse

---

## FASE 17 — Bug de doble `pygame.event.get()`

**Archivo:** `alpha_football/ui/team_screen.py`

**Síntoma:** Los KEYDOWN nunca se procesaban. El handler de teclado se ejecutaba pero los eventos ya habían sido consumidos.

**Causa raíz:**
Había DOS llamadas a `pygame.event.get()`:
- **Línea 349** (`for _ev in pygame.event.get():`) — capturaba mouse/QUIT
- **Línea 614** (`for event in pygame.event.get():`) — capturaba el resto

El primero consumía TODOS los eventos (incluidos KEYDOWN), por lo que el segundo no tenía nada que procesar.

**Fix aplicado (líneas ~347-353):**
```python
# v2.3.2 (FIX): no consumir pygame.event.get() aqui. El unico
# pygame.event.get() del team_screen esta mas abajo (linea ~614) y
# procesa mouse + teclado en el mismo loop. Antes este primer get()
# consumia todos los eventos y el handler de teclado (K_LEFTBRACKET,
# K_TAB, K_a, etc.) NUNCA se ejecutaba.
```

**Verificación:**
```python
# Test smoke_v32_team_kbd.py:
# Antes: 4-3-3 → 4-3-3 (sin cambios)
# Después: 4-3-3 → 4-4-2 (✓) → 4-3-2-1 (✓) → 4-4-2 (✓ con [)
```

---

## FASE 18 — Colores tabla según división

**Archivo:** `alpha_football/ui/league_screen.py` (líneas ~523-545)

**Reglas:**
- **1ª división:**
  - Top 3 → **VERDE** (clasifican a Champions/Libertadores)
  - Bottom 2 → **ROJO** (descienden a 2ª)
  - Resto → blanco
- **2ª división:**
  - Top 2 → **VERDE** (ascienden a 1ª)
  - Resto → blanco (sin descensos porque no hay 3ª)

**Fix aplicado:**
```python
n_total = len(equipos_ordenados)
es_segunda = (liga_view == 2)
for idx, eq in enumerate(equipos_ordenados, 1):
    if es_segunda:
        if idx <= 2:
            row_color = 'verde'
        else:
            row_color = 'blanco'
    else:
        if idx <= 3:
            row_color = 'verde'
        elif idx >= n_total - 1:
            row_color = 'rojo'
        else:
            row_color = 'blanco'
```

---

## FASE 19 — Fix "Sin rival programado" en 2ª división

**Archivo:** `alpha_football/ui/league_screen.py`

**Síntoma observado (en captura del usuario):**
- Al estar en 2ª división, el panel "PRÓXIMO ENCUENTRO" mostraba "Sin rival programado"
- Los "Otros partidos de la fecha" también aparecían vacíos

**Causa raíz:**
`partido_usuario` siempre se buscaba en `liga.calendario` (la del user en 1ª), no en `liga_vista.calendario` (lo que se está viendo). Si estoy en 2ª división y miro 2ª, mi equipo está en la 2ª división, no en la 1ª.

**Fix aplicado (líneas ~365-395):**
```python
partido_usuario = None
if liga_view == 2:
    # Si veo 2ª -> busco en liga_vista.calendario
    for p in getattr(liga_vista, 'calendario', []):
        if p.jornada == jornada_actual and (
            p.local_id == mi_equipo.id or p.visitante_id == mi_equipo.id
        ):
            partido_usuario = p
            break
if partido_usuario is None:
    # Fallback: busco en liga.calendario (la del user)
    for p in getattr(liga, 'calendario', []):
        if p.jornada == getattr(liga, 'jornada_actual', 1) and (
            p.local_id == mi_equipo.id or p.visitante_id == mi_equipo.id
        ):
            partido_usuario = p
            break
```

También:
- Línea ~638: `oponente = next((e for e in (liga_vista.equipos if liga_view == 2 else liga.equipos) if e.id == oponente_id), None)`
- Línea ~664: igual para "otros partidos"

---

## FASE 20 — Teclado global en TODAS las pantallas

Implementé navegación por teclado en **11 pantallas** con un patrón unificado:

| Pantalla | Atajos |
|---|---|
| `league_screen` | `↑↓` sidebar, `V` toggle 1ª/2ª, `j/m/c/o/s/h/e` atajos, `Enter/Esc` |
| `career_screen` | `↑↓` sidebar, `l/m/c/e/o/Esc` atajos, `Enter` |
| `ofertas_screen` | `↑↓` filas, `←→` ACEPTAR/RECHAZAR, `A/R` acciones, `Esc` volver |
| `stats_screen` | `←→↑↓` pestañas + scope, `L/T` alcance, `Esc` volver |
| `market_screen` | `←→` tabs, `P` país, `F` filtros, `PageUp/Down`, `Esc` volver |
| `options_screen` | `Esc` volver, `-/+/M` volumen (no en input), `Ctrl+V` pegar URL |
| `prepartido_screen` | `↑↓` 5 botones, `1/2/3/4/Esc`, `Enter` |
| `team_screen` | `[ ]` formación, `- +` táctica, `Tab` foco, `A` AUTO, `Esc` volver |
| `copa_screen` | `Esc` volver, `S` stats, `Enter` jugar partido pendiente |
| `promo_releg_screen` | `Enter/Space/Esc` continuar |
| `menu` (select_country/division) | `↑↓` países, `Enter` seleccionar, `Esc` volver |

**Indicador visual unificado:**
```python
# Borde dorado brillante (3px) sobre el botón enfocado por teclado
pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), kbd_rect, width=3, border_radius=8)
# Flecha a la izquierda
draw_text(screen, "▶", (kbd_rect.x - 22, kbd_rect.y + 14), size='lg', color='dorado')
```

**Igualdad visual mouse vs teclado:**
- Hover del mouse → activa el botón
- Foco de teclado → activa el botón (con borde dorado + flecha)
- Ambos pueden coexistir en el mismo botón

---

## FASE 21 — Pantalla de Promoción/Relegación

**Archivo nuevo:** `alpha_football/ui/promo_releg_screen.py`

**Funcionalidad:**
Se muestra al FINAL de cada temporada, **ANTES** del resumen. Lista los equipos que ASCIENDEN de 2ª a 1ª y los que DESCIENDEN de 1ª a 2ª.

**Layout:**
- Banner superior: verde (ascendiste), rojo (descendiste), dorado (nada)
- 2 columnas: ASCENDEN (verde) / DESCIENDEN (rojo) con nombres y OVR
- Botón CONTINUAR centrado abajo (Enter/Espacio/Esc)

**Estado esperado:**
```python
estado['promo_releg_data'] = {
    'ascendidos': [{'nombre': 'Real Cartagenero', 'ovr': 65, 'origen': 2, 'destino': 1, 'es_user': False}, ...],
    'descendidos': [{'nombre': 'Pobres Vagos', 'ovr': 70, 'origen': 1, 'destino': 2, 'es_user': False}, ...],
    'user_ascendio': bool,
    'user_descendio': bool,
}
```

**Hook en `resumen_temporada_screen.py:589-595`:**
```python
if click_pos and btn_avanzar.collidepoint(click_pos):
    if estado.get('promo_releg_data'):
        avanzar_nueva_temporada(estado)  # hace el swap internamente
        return "promo_releg_screen"      # redirige ANTES del resumen
    avanzar_nueva_temporada(estado)
    return "league_screen"
```

**Captura ANTES del swap (líneas ~250-275):**
```python
ascenden = equipos_2_ord[:2]
descienden = equipos_1_ord[:2]

# v2.3.3: armar payload para promo_releg_screen ANTES del swap
try:
    _asc_payload = [
        {'nombre': getattr(e, 'nombre', '?'),
         'ovr': getattr(e, 'ovr_promedio', 0),
         'origen': 2, 'destino': 1,
         'es_user': (getattr(e, 'id', None) == getattr(mi_equipo, 'id', None))}
        for e in ascenden
    ]
    _des_payload = [
        {'nombre': getattr(e, 'nombre', '?'),
         'ovr': getattr(e, 'ovr_promedio', 0),
         'origen': 1, 'destino': 2,
         'es_user': (getattr(e, 'id', None) == getattr(mi_equipo, 'id', None))}
        for e in descienden
    ]
    estado['promo_releg_data'] = {
        'ascendidos': _asc_payload,
        'descendidos': _des_payload,
        'user_ascendio': any(x['es_user'] for x in _asc_payload),
        'user_descendio': any(x['es_user'] for x in _des_payload),
    }
except Exception as e_pr_data:
    logger.error(f"Error armando promo_releg_data: {e_pr_data}")
```

**Registro en `main.py`:**
```python
from alpha_football.ui.promo_releg_screen import render as promo_releg_render
PANTALLAS = {
    'menu': menu_render,
    # ... otras pantallas ...
    'promo_releg_screen': promo_releg_render,
}
```

---

## FASE 22 — Bugfix final: `dir_hab` referenced before assignment

**Archivo:** `alpha_football/ui/prepartido_screen.py`

**Síntoma observado (en vivo, después de mis cambios):**
```text
ERROR - Error en prepartido_screen: local variable 'dir_hab' referenced before assignment
```

**Causa raíz:**
Mi cambio en FASE 20 agregó una lista `prepartido_buttons` que referenciaba `dir_hab` y `rival_disponible` ANTES de que se definieran (estaban definidos más abajo, en líneas 482 y 487).

**Fix aplicado (líneas ~459-477):**
```python
# Botones de opción
btn_jugar = pygame.Rect(SCREEN_W // 2 - 260, 290, 520, 60)
btn_sim = pygame.Rect(SCREEN_W // 2 - 260, 370, 520, 60)
btn_dir = pygame.Rect(SCREEN_W // 2 - 260, 450, 520, 60)
btn_ver_rival = pygame.Rect(SCREEN_W // 2 - 260, 510, 250, 48)
btn_volver = pygame.Rect(SCREEN_W // 2 + 10, 510, 250, 48)

# v2.3.3 (FIX): dir_hab y rival_disponible deben estar definidos ANTES de la
# lista prepartido_buttons, porque alli los usamos como flag de habilitacion.
# Antes la lista los referenciaba antes de su definicion -> UnboundLocalError.
dir_hab = (local is not None) if match_mode == 'amistoso' else (mi_equipo is not None)
rival_disponible = visitante is not None and visitante is not local

# v2.3.3: navegacion por teclado. 5 botones en orden:
if 'prepartido_kbd_focus' not in estado:
    estado['prepartido_kbd_focus'] = 0
_pp_kbd = int(estado.get('prepartido_kbd_focus', 0))
prepartido_buttons = [
    (btn_jugar, 'jugar', True),
    (btn_sim, 'sim', True),
    (btn_dir, 'dir', dir_hab),
    (btn_ver_rival, 'rival', rival_disponible),
    (btn_volver, 'volver', True),
]
```

**Cambios también abajo (líneas ~480-489):**
- Eliminadas las definiciones duplicadas
- Comentario aclarando que ya están definidas arriba

---

## 📊 Resumen estadístico

| Métrica | Valor |
|---|---|
| Archivos nuevos | 6 (5 segunda división + 1 promo_releg_screen) |
| Archivos modificados | 12 |
| Tests creados | 3 (`smoke_v23`, `test_v23`, `smoke_v31_fix`) |
| Líneas añadidas | ~4000 |
| Líneas modificadas | ~1200 |
| Jugadores parodiados | 750 (nuevos) + 120 (existentes) = **870 totales** |
| `compileall` | **0 errores** |
| Tests headless | 23/23 OK (v2.3) + 6/6 OK (v2.3.1) |

---

## 🎯 Compatibilidad

- Saves v5 (anteriores a v2.3) cargan sin error: campos nuevos tienen defaults sensatos
- Saves v2.3 → v2.3.3 usan el mismo formato v5 (no se incrementa `SCHEMA_VERSION`)
- 2ª división se carga **on-demand** desde `data/segunda_*.py` solo si el usuario está en una liga que tiene segunda
- Bono ×2 solo aplica si `division == 2`, no afecta a saves con 1ª división

---

## ✅ Validación hecha (headless)

- `python -m compileall -q alpha_football main.py` → **0 errores**
- `tests/smoke_v23.py` y `tests/test_v23.py` → todos los chequeos pasan
- `tests/smoke_v31_fix.py` → 5 países × 2 divisiones = 10 ligas cargan OK
- Test E2E sin headless → flujo País → División → Equipo → DT → league_screen → prepartido OK
- Teclado test:
  - `]` en team_screen cambia formación 4-3-3 → 4-4-2 → 4-3-2-1 → 4-4-2 ✓
  - `j/m/c/o/s/h/e` en league_screen navegan a todas las pantallas ✓
  - `V` toggles 1ª/2ª división ✓
  - `Enter/Esc` en promo_releg_screen avanza a resumen ✓

---

## 🟡 Pendiente de validación en vivo (Diego, `python main.py`)

1. **Carrera nueva con 1ª división:**
   - Pulsar `V` → ver 2ª división (tabla con top 2 verde, sin descensos)
   - Pulsar `V` otra vez → volver a 1ª (tabla con top 3 verde, bottom 2 rojo)

2. **Carrera en 2ª división:**
   - "PRÓXIMO ENCUENTRO" muestra rival correcto (no "Sin rival programado")
   - "Otros partidos de la fecha" lista los 3 partidos de la jornada

3. **Navegación con teclado en TODAS las pantallas:**
   - `↑↓` mueve el foco (borde dorado + flecha `▶`)
   - `Enter` activa el botón enfocado
   - `Esc` vuelve al menú/liga

4. **Finalizar temporada (en 1ª división):**
   - Pantalla de PROMO/RELEG aparece ANTES del resumen
   - Banner correcto según ascenso/descenso del usuario
   - Lista de ascendidos (verde) y descendidos (rojo) con OVR
   - CONTINUAR (Enter) avanza al resumen

5. **Botones del sidebar de league_screen con teclado:**
   - Pulsar `j` → abre prepartido
   - Pulsar `m` → abre mercado
   - Pulsar `c` → abre copa
   - Pulsar `o` → abre ofertas
   - Pulsar `s` → abre estadísticas
   - Pulsar `h` → abre historial carrera
   - Pulsar `e` → abre dirección de equipo

6. **Ascenso/descenso efectivo en la siguiente temporada:**
   - Calendario regenerado con los equipos nuevos
   - Si ascendiste, vuelves a 1ª con los nuevos equipos
   - Si descendiste, juegas en 2ª y la copa queda deshabilitada

---

*Documento generado el 2026-06-26. Versión del juego: v2.3.3 (rama no publicada, pendiente validación en vivo).*