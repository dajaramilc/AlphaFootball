# Informe de Diagnóstico — Alpha Football v2.3.3
## Análisis de cambios de la sesión 2026-06-26 (minimax)

---

## Resumen Ejecutivo

El changelog reporta 22 fases con ~4000 líneas añadidas, 750 jugadores nuevos, y `compileall: 0 errores`. Sin embargo, el diagnóstico en profundidad revela **4 bugs críticos** que rompen el juego en runtime, **3 bugs altos** que causan pérdida de datos/comportamiento incorrecto, y **varios bugs medios/bajos** de lógica y UX. La mayoría no son detectables por `compileall` porque son errores de lógica y de flujo de datos, no de sintaxis.

---

## Errores detectados (por criticidad)

### 🔴 CRÍTICO #1 — Usuarios en 2ª división nunca pueden ascender
**Archivo:** `alpha_football/ui/resumen_temporada_screen.py:226-230`
**Problema:** El código del swap promo/releg solo se ejecuta si `liga_division == 1` (el usuario está en 1ª). Si el usuario empieza una carrera en 2ª división o desciende a 2ª, la condición nunca se cumple y el swap no corre. El usuario queda atrapado en 2ª para siempre, sin posibilidad de ascender.
```python
# Línea 226 — el guard solo aplica cuando division == 1
if liga_division == 1 and liga_tipo and liga_tipo in segunda:
```
**Además:** Si el usuario está en 2ª, `estado['liga']` apunta a la liga de 2ª, y `estado['segunda_division']` contiene las 2ª divisiones. La 1ª división NO está en el estado, así que aunque el guard se arreglara, el swap no sabe a qué 1ª división ascender. **Falta acceso a la 1ª división desde el contexto de la 2ª.**

---

### 🔴 CRÍTICO #2 — `Alineacion.convocados` NO se persiste (save/load)
**Archivos:** `alpha_football/models.py:420-425` (to_dict), `models.py:495-500` (from_dict)
**Problema:** La serialización de `EstadoJuego.to_dict()` escribe la alineación como:
```python
alin_dict = {
    "titulares": list(self.alineacion_activa.titulares),
    "formacion": str(self.alineacion_activa.formacion)
}
```
**`convocados` NO se incluye.** En `from_dict`, la reconstrucción es:
```python
alineacion_activa = Alineacion(
    titulares=list(alin_datos.get("titulares", [])),
    formacion=str(alin_datos.get("formacion", "4-3-3"))
)
```
Tampoco carga `convocados`. Resultado: cada save/load borra todas las convocatorias que el usuario configuró en el team_screen PES-style.

---

### 🔴 CRÍTICO #3 — Team screen bloquea sin convocados
**Archivo:** `alpha_football/ui/team_screen.py`
**Problema:** La validación al confirmar en team_screen exige EXACTAMENTE 10 convocados:
```python
if len(alin.convocados) != 10:
    estado['menu_error'] = 'Debes convocar exactamente 10 jugadores'
    return  # no avanza
```
Si el usuario entra a team_screen sin haber configurado convocados nunca (saves viejos, carrera nueva, o después de save/load por bug #2), `convocados` está vacío `[]`. El usuario queda bloqueado sin poder salir. Debe hacer clic en "AUTO CONVOC." primero, pero nada le indica esto.

---

### 🔴 CRÍTICO #4 — `engine.actualizar_tabla_simple` no existe
**Archivo:** `alpha_football/ui/league_screen.py:194, alpha_football/engine.py`
**Problema:** `simular_jornada_segunda_division` llama a:
```python
engine.actualizar_tabla_simple(local, visitante, res.goles_local, res.goles_visitante)
```
Esta función **no existe** en `engine.py`. El try/except lo captura y usa código manual duplicado. Cada partido de 2ª división lanza una excepción. Aunque funciona por el fallback, genera spam en logs y es frágil. Además, el bloque manual **no actualiza `pg`/`pe`/`pp` correctamente en caso de empate** (solo actualiza `pe` para ambos, pero no incrementa `pj` en todos los caminos).

---

### 🟠 ALTO #1 — Bono de 2ª división es 1/5 de 1ª (no ×2)
**Archivo:** `alpha_football/ui/resumen_temporada_screen.py:41-48`
**Problema:** El changelog dice que Diego pidió bono ×2. Los valores en `_BONO_LIGA_2A_X2`:
| Liga | 1ª posición 1 | 2ª posición 1 | Ratio |
|------|--------------|--------------|-------|
| Premier | 150M | 30M | **1/5** |
| BetPlay | 20M | 4M | **1/5** |

Son 1/5, no ×2. O el changelog está mal, o los valores están mal implementados.

---

### 🟠 ALTO #2 — `Equipo.division` inconsistente tras swap
**Archivo:** `alpha_football/ui/resumen_temporada_screen.py:240-262`
**Problema:** En el swap de promo/releg, se setea `eq.division = 1` o `eq.division = 2` en los equipos movidos. Pero `liga.equipos` ahora tiene equipos con `division=1` y también equipos que recién ascendieron (con `division=1`). Si luego se vuelve a ejecutar el swap la siguiente temporada, el guard `liga_division == 1` funciona, pero el código usa `liga.equipos` (la 1ª) y `liga_b.equipos` (la 2ª) para ordenar. Si un equipo tiene `division=2` pero está en `liga.equipos` (porque acaba de ascender), podría causar inconsistencia en los ordenamientos.

---

### 🟠 ALTO #3 — `simular_jornada_segunda_division` no actualiza correctamente las stats
**Archivo:** `alpha_football/ui/league_screen.py:150-235`
**Problema:** El bloque manual de stats tracking tiene bugs sutiles:
- En el try-except principal, cuando `engine.actualizar_tabla_simple` falla (siempre), el código manual maneja victoria/derrota/empate. PERO en caso de victoria local, **NO actualiza `pp` del visitante**. En caso de victoria visitante, **NO actualiza `pp` del local**. Y el `pj` se actualiza dentro de cada rama condicional pero no en un lugar común, lo que puede causar decrementos si hay excepciones parciales.

---

### 🟡 MEDIO #1 — 750 jugadores de 2ª sin desarrollo ni envejecimiento
**Archivo:** `alpha_football/data/segunda_*.py`
**Problema:** Las 2ª divisiones se recargan frescas desde los módulos en cada save/load. No reciben `progresar_liga_pasivo`, no envejecen, no desarrollan. Tras 5 temporadas, los equipos de 2ª son idénticos a como empezaron. Si el usuario asciende/desciende, los equipos intercambiados mantienen sus stats reales de una liga pero no de la otra.

---

### 🟡 MEDIO #2 — `selected_country_id` no se persiste entre saves
**Archivo:** `alpha_football/ui/menu.py:820-870`
**Problema:** `_aplicar_estado_cargado` no restaura `selected_country_id` ni `selected_division`. Si el save se carga y el usuario va al menú principal, estos campos faltan, lo que puede causar errores si se usa el flow de país→división.

---

### 🟡 MEDIO #3 — `promo_releg_screen` usa `pygame.event.get()` directamente
**Archivo:** `alpha_football/ui/promo_releg_screen.py:63`
**Problema:** La pantalla de promo/releg llama a `pygame.event.get()` directamente en lugar de usar los eventos cacheados del frame (como hace el resto del juego). En el monkeypatch de `main.py`, `pygame.event.get` fue reemplazado con una versión cacheada que retorna los eventos del frame. Pero la pantalla itera sobre `pygame.event.get()` — esto funciona pero es inconsistente con el resto del código.

---

### 🟢 BAJO #1 — `convocados` validación debería auto-completar
**Archivo:** `alpha_football/ui/team_screen.py`
**Problema:** En vez de bloquear con error cuando `convocados` está vacío, el código debería ejecutar `_auto_convocados()` automáticamente como fallback.

---

### 🟢 BAJO #2 — `engine.py` tiene dataclasses duplicados
**Archivo:** `alpha_football/engine.py:60-170`
**Problema:** `engine.py` define sus propias clases `Jugador`, `Equipo`, `Resultado`, `Standing` que son copias parciales de `models.py`. Esto funciona por duck-typing pero es frágil — si se añade un campo a `models.Jugador`, `engine.Jugador` no lo tiene. Es código muerto que solo sirve para el modo standalone del engine.

---

### 🟢 BAJO #3 — 3750 objetos jugador cargados siempre en memoria
**Archivo:** `alpha_football/ui/menu.py:1446`
**Problema:** Al iniciar carrera nueva, se cargan las 5 segundas divisiones (5×6×25 = 750 jugadores expandidos a 25 cada uno = 3750). Esto es innecesario — solo se necesita la 2ª división del país del usuario. Las otras 4 son basura en RAM.

---

## Métricas del diagnóstico

| Métrica | Valor |
|---|---|
| Archivos analizados | 17 |
| Tests de importación | 15/15 OK |
| Tests de runtime | 18/18 OK |
| Bugs críticos encontrados | 4 |
| Bugs altos encontrados | 3 |
| Bugs medios encontrados | 3 |
| Bugs bajos encontrados | 3 |
| **Total bugs** | **13** |

---

## Plan de reparación propuesto

### Fase 1 — Críticos (rompen el juego)
1. Arreglar promo/releg bidireccional (2ª → 1ª)
2. Persistir `convocados` en save/load
3. Auto-completar convocados en team_screen
4. Eliminar llamada a `engine.actualizar_tabla_simple` (usar el fallback como código primario)

### Fase 2 — Altos (datos incorrectos)
5. Corregir bono de 2ª división o documentar valores reales
6. Arreglar tracking de stats en simulación de 2ª
7. Normalizar `Equipo.division` post-swap

### Fase 3 — Medios/Bajos (UX y mantenibilidad)
8. Cargar solo la 2ª división relevante (no las 5)
9. Persistir `selected_country_id` entre saves
10. Unificar event handling en promo_releg_screen
11. Documentar o eliminar dataclasses duplicados en engine.py
12. Añadir desarrollo pasivo a equipos de 2ª división

Cada fase incluye tests exhaustivos para la feature reparada.
