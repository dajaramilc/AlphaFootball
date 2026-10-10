# Ejecución nativa de G1, G2 y G3 (avance por días → temporada por fechas → las 20 horas)

Método elegido por Diego: **NATIVO** (superpowers:executing-plans), tú solo, sin subagentes, **sin commits**. Una sesión nueva por plan, con Sonnet 5.5. Orden obligatorio: **G1 → G2 → G3** (cada uno se apoya en el código del anterior). Entre una sesión y otra, Diego prueba a mano y da el OK.

| # | Plan | Spec | Versión | Antes de empezar |
|---|---|---|---|---|
| G1 | `docs/superpowers/plans/2026-10-07-avance-por-dias-g1.md` | `docs/superpowers/specs/2026-10-07-avance-por-dias-g1-design.md` | 0.4.12.0 | C (calendario real) implementado — ya lo está |
| G2 | `docs/superpowers/plans/2026-10-07-temporada-por-fechas-g2.md` | `docs/superpowers/specs/2026-10-07-temporada-por-fechas-g2-design.md` | 0.4.13.0 | G1 implementado y probado por Diego |
| G3 | `docs/superpowers/plans/2026-10-07-ultimo-dia-20-horas-g3.md` | `docs/superpowers/specs/2026-10-07-ultimo-dia-20-horas-g3-design.md` | 0.4.14.0 | G2 implementado y probado por Diego |

El plan y los specs están sin commitear: no los reviertas. Los planes de G2 y G3 se escribieron antes de que exista el código de G1/G2: si un bloque citado no existe tal cual, adapta lo mínimo y anota la desviación.

---

## Prompt para G1 (pegar en una sesión nueva)

```
Ejecuta el plan docs/superpowers/plans/2026-10-07-avance-por-dias-g1.md
(v0.4.12.0, sub-proyecto G1: reloj, agenda y botones CONTINUAR / +1 DÍA) en modo
nativo: tú solo, en esta sesión, sin subagentes ni workflows.

El diseño y el plan ya están aprobados por mí: no hagas brainstorming ni
reescribas el plan. Usa la skill superpowers:executing-plans y sigue las tareas
en orden, paso por paso.

Antes de tocar código:
1. Lee el plan entero, incluidas las "Desviaciones del spec decididas al
   planificar" y el "Review Focus".
2. Lee el spec docs/superpowers/specs/2026-10-07-avance-por-dias-g1-design.md.
3. Lee context.md (bitácora de C, "Calendario real").

Reglas:
- Git: sin commit, push, stash, reset ni checkout de archivos. El plan y los
  specs están sin commitear: no los reviertas.
- Solo G1. G2, G3, E y F no se tocan.
- Edit parcial; no reescribas archivos ni toques código alrededor del cambio.
  Comentarios nuevos con "# v0.4.12.0".
- Tests: PYTHONIOENCODING=utf-8 python tests/<archivo>.py, deben terminar en
  "N/N tests pasaron". Hay tests que salen con código 0 aunque impriman FAIL:
  mira siempre la salida. Los tests del hub son lentos (minutos): córrelos de uno
  en uno y en segundo plano si hace falta.
- Corre solo los tests que cada tarea indica; la suite completa va una sola vez,
  al final (Task 7), con la opción de segundo plano de la herramienta, no con
  nohup.
- TDD: cada test se escribe primero y se ve fallar por la razón esperada.
- Los números de línea del plan son aproximados: ubica cada cambio por el código
  citado. Si un bloque no existe tal cual, adapta lo mínimo y anota la desviación.
- Si falla un test de la suite: si daba por hecho que JUGAR del hub abre el
  partido de inmediato, ajústalo como dice el plan (Task 7). Si no, es un bug del
  cambio: busca la causa raíz. No debilites tests para que pasen.
- Si quedas bloqueado o aparece una decisión que es mía, no adivines: sigue con
  lo que no dependa de eso y dímelo.

Al terminar, dame: estado por tarea, resultado de la suite completa, desviaciones
del plan con su motivo, tests existentes que ajustaste y por qué, y lo que me
queda por probar a mano. No hagas commit: yo doy el OK final.
```

## Prompt para G2

```
Ejecuta el plan docs/superpowers/plans/2026-10-07-temporada-por-fechas-g2.md
(v0.4.13.0, sub-proyecto G2: la temporada por fechas) en modo nativo: tú solo, en
esta sesión, sin subagentes ni workflows.

G1 ya está implementado (alpha_football/dias.py) y probado por mí. El diseño y el
plan están aprobados: no hagas brainstorming ni reescribas el plan. Usa la skill
superpowers:executing-plans y sigue las tareas en orden, paso por paso.

Antes de tocar código:
1. Lee el plan entero, incluidas las "Desviaciones del spec decididas al
   planificar" y el "Review Focus".
2. Lee el spec docs/superpowers/specs/2026-10-07-temporada-por-fechas-g2-design.md.
3. Lee alpha_football/dias.py y alpha_football/calendario.py tal como quedaron, y
   la bitácora de G1 en context.md: el plan se escribió antes de que existieran.

Reglas:
- Git: sin commit, push, stash, reset ni checkout de archivos. Los planes y
  specs están sin commitear: no los reviertas.
- Solo G2. G3, E y F no se tocan.
- Edit parcial; no reescribas archivos ni toques código alrededor del cambio.
  Comentarios nuevos con "# v0.4.13.0".
- Tests: PYTHONIOENCODING=utf-8 python tests/<archivo>.py, deben terminar en
  "N/N tests pasaron". Hay tests que salen con código 0 aunque impriman FAIL:
  mira siempre la salida. Los tests del hub y de mercado son lentos: córrelos de
  uno en uno.
- Corre solo los tests que cada tarea indica; las tareas 2 a 6 dejan a propósito
  algunos tests viejos en rojo que se ajustan en la Task 10 (anótalos). La suite
  completa va una sola vez, al final (Task 10), en segundo plano, no con nohup.
- TDD: cada test se escribe primero y se ve fallar por la razón esperada.
- Los números de línea del plan son aproximados: ubica cada cambio por el código
  citado. Si un bloque no existe tal cual, adapta lo mínimo y anota la desviación.
- Si falla un test de la suite: si daba por hecho que el mercado se decide por
  jornada, que la mitad es una jornada, que el reloj nace el 1 de agosto o los
  textos "en la jornada N", ajústalo como dice el plan. Si no, es un bug del
  cambio: busca la causa raíz. No debilites tests para que pasen.
- Si quedas bloqueado o aparece una decisión que es mía, no adivines: sigue con
  lo que no dependa de eso y dímelo.

Al terminar, dame: estado por tarea, resultado de la suite completa, desviaciones
del plan con su motivo, tests existentes que ajustaste y por qué, y lo que me
queda por probar a mano. No hagas commit: yo doy el OK final.
```

## Prompt para G3

```
Ejecuta el plan docs/superpowers/plans/2026-10-07-ultimo-dia-20-horas-g3.md
(v0.4.14.0, sub-proyecto G3: el último día de fichajes con 20 horas) en modo
nativo: tú solo, en esta sesión, sin subagentes ni workflows.

G1 (dias.py) y G2 (temporada.py) ya están implementados y probados por mí. El
diseño y el plan están aprobados: no hagas brainstorming ni reescribas el plan.
Usa la skill superpowers:executing-plans y sigue las tareas en orden, paso por
paso.

Antes de tocar código:
1. Lee el plan entero, incluidas las "Desviaciones del spec decididas al
   planificar" y el "Review Focus".
2. Lee el spec docs/superpowers/specs/2026-10-07-ultimo-dia-20-horas-g3-design.md.
3. Lee alpha_football/dias.py, alpha_football/temporada.py y
   alpha_football/ui/aviso_mercado.py tal como quedaron, y las bitácoras de G1 y
   G2 en context.md: el plan se escribió antes de que existieran.

Reglas:
- Git: sin commit, push, stash, reset ni checkout de archivos. Los planes y
  specs están sin commitear: no los reviertas.
- Solo G3. E y F no se tocan.
- Edit parcial; no reescribas archivos ni toques código alrededor del cambio.
  Comentarios nuevos con "# v0.4.14.0".
- Tests: PYTHONIOENCODING=utf-8 python tests/<archivo>.py, deben terminar en
  "N/N tests pasaron". Hay tests que salen con código 0 aunque impriman FAIL:
  mira siempre la salida.
- Corre solo los tests que cada tarea indica; la suite completa va una sola vez,
  al final (Task 6), en segundo plano, no con nohup.
- TDD: cada test se escribe primero y se ve fallar por la razón esperada.
- Los números de línea del plan son aproximados: ubica cada cambio por el código
  citado. Si un bloque no existe tal cual, adapta lo mínimo y anota la desviación.
- Si falla un test de la suite: si daba por hecho que se puede operar o avanzar
  el 31 sin cerrar el mercado o esperaba el hito 'cierra', ajústalo como dice el
  plan (Task 6). Si no, es un bug del cambio: busca la causa raíz. No debilites
  tests para que pasen.
- Si quedas bloqueado o aparece una decisión que es mía, no adivines: sigue con
  lo que no dependa de eso y dímelo.

Al terminar, dame: estado por tarea, resultado de la suite completa, desviaciones
del plan con su motivo, tests existentes que ajustaste y por qué, y lo que me
queda por probar a mano. No hagas commit: yo doy el OK final.
```

---

## Después de G3

Quedan por hacer del paquete 0.4.11.0: **E** (auto-actualización desde GitHub) y **F** (temporadas por continente, que usa `datos_carrera['mundo']['anio']`, ya leído por `calendario.anio`). Cuando Diego decida cerrar el paquete: subir `VERSION`/título de la ventana/badge del README (siguen en 0.4.10.0), commit y push.

---

## Prompt en cadena (G1 → G2 → G3 en una sola ejecución)

Úsalo si Diego quiere probar todo al final. Se pega en este chat o en una sesión nueva (`/clear` antes es lo mejor: todo lo que necesita está en disco).

```
Ejecuta en cadena, en modo nativo (tú solo, en esta sesión, sin subagentes ni
workflows), los tres planes de avance por días, EN ESTE ORDEN y sin saltarte
ninguno:

  1. G1 · docs/superpowers/plans/2026-10-07-avance-por-dias-g1.md        (v0.4.12.0)
  2. G2 · docs/superpowers/plans/2026-10-07-temporada-por-fechas-g2.md   (v0.4.13.0)
  3. G3 · docs/superpowers/plans/2026-10-07-ultimo-dia-20-horas-g3.md    (v0.4.14.0)

El diseño y los planes ya están aprobados por mí: no hagas brainstorming ni
reescribas los planes. Para cada plan usa la skill superpowers:executing-plans y
sigue sus tareas en orden, paso por paso. No pares a preguntarme entre tareas ni
entre planes: sigue hasta el final.

Antes de empezar:
1. Lee docs/superpowers/plans/EJECUCION-G1-G2-G3.md y context.md (bitácora de C).
2. Crea docs/superpowers/plans/PROGRESO-G1-G2-G3.md (sin commitear) con la
   primera línea "# Progreso de la cadena G1-G2-G3". Es tu memoria: cada vez que
   termines una tarea, agrega UNA línea "G<n> Task <k>: completa (tests: <comando>
   -> <resultado>)" y cada desviación como "Desviación: <qué> — <por qué>". Si
   perdieras el contexto, léelo y retoma en la primera tarea sin línea (git no
   sirve de bitácora porque no hay commits).

Al empezar CADA plan:
- Léelo entero (incluidas "Desviaciones del spec decididas al planificar" y
  "Review Focus") y lee su spec en docs/superpowers/specs/.
- G2 y G3: lee también el código real que dejó el plan anterior (dias.py,
  calendario.py, temporada.py, aviso_mercado.py) y la bitácora de ese plan en
  context.md. Los planes de G2 y G3 se escribieron antes de que existiera ese
  código: si un bloque citado no existe tal cual, adapta lo mínimo y anota la
  desviación en el archivo de progreso.

Reglas:
- Git: sin commit, push, stash, reset ni checkout de archivos. Trabaja en el árbol
  actual, sin worktree. Los planes, specs y PROGRESO están sin commitear: no los
  reviertas.
- Solo G1, G2 y G3. Los sub-proyectos E y F no se tocan.
- Edit parcial; no reescribas archivos ni toques código alrededor del cambio.
  Comentarios nuevos con "# v0.4.12.0" (G1), "# v0.4.13.0" (G2) y "# v0.4.14.0"
  (G3). Textos y comentarios en español.
- TDD: cada test se escribe primero y se ve fallar por la razón esperada.
- Tests: PYTHONIOENCODING=utf-8 python tests/<archivo>.py, deben terminar en
  "N/N tests pasaron". Hay tests que salen con código 0 aunque impriman FAIL:
  mira siempre la salida. Los tests del hub y de mercado son lentos (minutos):
  córrelos de UNO en uno, nunca en paralelo.
- Corre solo los tests que cada tarea indica. La suite completa va UNA vez por
  plan, en su última tarea (G1 Task 7, G2 Task 10, G3 Task 6), con la opción de
  segundo plano de la herramienta (no nohup), un archivo a la vez. Si el sistema
  mata un proceso en segundo plano por poca memoria, relánzalo una vez, de uno en
  uno, y si vuelve a morir dímelo y sigue con lo demás.
- Los números de línea de los planes son aproximados: ubica cada cambio por el
  código citado.
- Puerta entre planes: no empieces el siguiente hasta que la suite completa del
  actual dé rc=0 y FAIL=0 en todos los archivos (test_motor_v400 mide tiempos y
  puede fallar una vez por carga: repítelo antes de investigar) y su bitácora esté
  en context.md. Los planes dejan algunos tests viejos en rojo a propósito entre
  tareas; se ajustan donde el plan lo dice.
- Si falla un test de la suite: si daba por hecho algo que el plan cambia a
  propósito, ajústalo como dice el plan, sin debilitarlo; si no, es un bug del
  cambio: busca la causa raíz (systematic-debugging). No debilites tests para que
  pasen.
- Solo te detienes por: una operación destructiva o irreversible, una acción de
  seguridad, un efecto fuera del repo, un plan tan roto que todo camino es
  adivinar, o una decisión que es mía. Si te bloqueas, sigue con lo que no dependa
  de eso y dímelo; no adivines.

Al terminar la cadena, haz una autorevisión de todo el diff contra los "Review
Focus" de los tres planes y dame: estado por tarea de cada plan, resultado de la
suite completa de cada uno, desviaciones con su motivo, tests existentes que
ajustaste y por qué, y lo que me queda por probar a mano (las listas de pendientes
de las tres bitácoras). No hagas commit: yo doy el OK final.
```
