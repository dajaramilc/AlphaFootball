# Pendientes tras G1-G2-G3 (retoques de G3, E auto-actualización, F temporadas por continente, cierre)

Para una sesión nueva. Pegar solo esta línea:

> Ejecuta el prompt de la sección «Prompt» de `docs/superpowers/plans/EJECUCION-PENDIENTES.md`.

Si Diego ya probó a mano G1-G3 y tiene bugs, pegarlos justo debajo de esa línea: la sesión los atiende primero.

---

## Prompt

```
Continúa el proyecto AlphaFootball (C:\Users\diego\Downloads\AlphaFootball) en modo nativo: tú solo, en esta
sesión, sin subagentes ni workflows. Responde y escribe todo (textos del juego, comentarios, planes) en español.

CONTEXTO
Están implementados, SIN commit y con la suite completa en verde (72/72 archivos, rc=0 y FAIL=0), el calendario
real (C) y los sub-proyectos G1 (v0.4.12.0, avance por días), G2 (v0.4.13.0, temporada por fechas) y G3 (v0.4.14.0,
último día de fichajes con 20 horas). Diego los está probando a mano. Antes de hacer nada lee, en paralelo:
  1. context.md: las bitácoras del final ("Calendario real", "Avance por días", "La temporada por fechas",
     "Último día de fichajes: las 20 horas") y la sección del paquete 0.4.11.0.
  2. docs/superpowers/plans/PROGRESO-G1-G2-G3.md: desviaciones, tests que se ajustaron y por qué.
  3. docs/superpowers/specs/2026-10-06-calendario-mercado-actualizador-design.md, secciones E y F.
  4. El código vivo: alpha_football/calendario.py, dias.py, temporada.py, dia_final.py.
Crea docs/superpowers/plans/PROGRESO-PENDIENTES.md (sin commitear) con la primera línea "# Progreso de los
pendientes". Es tu memoria: una línea "<etapa> Task <k>: completa (tests: <comando> -> <resultado>)" por tarea
terminada y una línea "Desviación: <qué> — <por qué>" por cada desviación. Si pierdes el contexto, léelo y retoma
en la primera tarea sin línea (no hay commits que sirvan de bitácora).

ETAPAS, EN ESTE ORDEN
0. Si Diego pegó bugs de su prueba manual de G1-G3, arréglalos primero con superpowers:systematic-debugging
   (causa raíz, test que falle antes del arreglo, sin debilitar tests).

1. Dos retoques menores de G3 (comentarios "# v0.4.14.0"; TDD):
   a) En el panel ÚLTIMO DÍA de alpha_football/ui/league_screen.py la línea 2 (fecha y horas, en R_JUGAR.y + 48)
      roza unos 2 px los botones R_HORA / R_CERRAR (R_JUGAR.bottom - 32). Que no choquen ni salgan de R_JUGAR.
   b) estado['confirmar_cierre_mercado'] sobrevive al cambiar de pestaña o salir del hub: debe cancelarse al
      cambiar de pestaña, al salir del hub y al pasar una hora o un día.
   Verifica con tests/test_dia_final.py, test_ux_v360.py, test_ayuda_v390.py y test_hub_v240.py.

2. Sub-proyecto E: auto-actualización (spec: sección E del documento del 2026-10-06; el diseño ya está aprobado,
   no hagas brainstorming). Usa superpowers:writing-plans para escribir
   docs/superpowers/plans/2026-10-08-actualizador-e.md y luego superpowers:executing-plans. Versión del plan: la
   siguiente libre según la memoria "numeración de versiones" (0.4.15.0); si dudas, pregunta.
   - Seguridad: durante el desarrollo y los tests NUNCA toques la red real, ni ejecutes git pull, ni descargues ni
     copies un ZIP real sobre el repo. Todo con consulta y descarga falsas (como test_musica_actualiza_ytdlp).
     Respeta la lista de archivos que nunca se pisan (saves/, preferencias.json, music/, musica.txt,
     alpha_football_save.json*, alpha_football_edited_db.json, alpha_football_db_custom.json, context.md) y la
     validación del ZIP (main.py + VERSION igual al consultado, sin rutas fuera de la carpeta, carpeta temporal).
   - Crea el archivo VERSION con el valor que hoy muestran el título de la ventana y el badge (0.4.10.0): no
     adelantes el bump, lo decide Diego en la etapa 4. alpha_football.__version__ lee VERSION y el título lo usa.
   - Test nuevo tests/test_actualizador.py (sin red).

3. Sub-proyecto F: temporadas por continente (spec: sección F, F1-F6, mismo documento). Ese spec es anterior a G2.
   Antes de planificar compáralo con el código real y anota las diferencias en PROGRESO-PENDIENTES.md:
   - G2 ya dio a cada continente sus fechas (Europa 1 jul - 30 jun, Sudamérica 1 ene - 31 dic: desfasadas ~6 meses
     en el calendario), calendario.anio ya lee datos_carrera['mundo']['anio'], y las ligas de fondo avanzan una
     jornada por cada jornada tuya. El spec habla de "n // 2 jornadas" de desfase: tradúcelo a fechas.
   - Piezas del spec: temporadas.py con arrancar_desfase / cerrar_continente; extraer de
     resumen_temporada_screen.avanzar_nueva_temporada los pasos por liga, con filtro opcional de países y sin filtro =
     comportamiento de hoy; la Champions sigue a las ligas europeas y la Libertadores a las sudamericanas; cambiar de
     continente; saves viejos con datos_carrera['mundo']['desfase'] (sin esa marca todo se comporta como hoy).
   Escribe el plan (writing-plans, docs/superpowers/plans/2026-10-08-temporadas-continente-f.md) dividido en tareas
   pequeñas y verificables, con "Review Focus", y ejecútalo con executing-plans (versión: la siguiente libre,
   0.4.16.0). Si aparece una decisión de diseño que es de Diego (por ejemplo, cómo conviven tu reloj de días con el
   cierre a mitad de temporada del otro continente), párate y pregúntale con una recomendación.

4. Cierre. NO hagas commit ni push sin el OK de Diego. Cuando E y F tengan la suite completa en verde, haz una
   autorevisión del diff contra los "Review Focus" y pregúntale: (a) qué versión final poner en VERSION, el título de
   la ventana y el badge del README (hoy 0.4.10.0); (b) cómo agrupar los commits (C, G1-G3, E, F; los planes, specs y
   PROGRESO están sin commitear; context.md no se commitea) y si hace el push. Solo con su OK, commitea y sube.

REGLAS (las mismas de la cadena G1-G2-G3)
- Git: nunca atribuyas a Claude ni a una IA en commits, PRs ni en ningún lugar de git (regla de Diego: el commit
  sale solo a su nombre, sin Co-Authored-By). Sin stash, reset ni checkout de archivos; sin worktree. Los planes y
  specs sin commitear no se revierten.
- Edit parcial; no reescribas archivos ni toques código alrededor del cambio. Comentarios nuevos con la versión de
  cada sub-proyecto ("# v0.4.15.0", "# v0.4.16.0"). Textos y comentarios en español.
- TDD: cada test se escribe primero y se ve fallar por la razón esperada.
- Tests: PYTHONIOENCODING=utf-8 python tests/<archivo>.py, deben terminar en "N/N tests pasaron". Hay tests que
  salen con código 0 aunque impriman FAIL: mira siempre la salida. Los del hub y de mercado son lentos: de UNO en
  uno, nunca en paralelo. La suite completa va una vez por sub-proyecto, al final, en segundo plano con la opción de
  la herramienta (no nohup), un archivo a la vez, con un resumen "<archivo> rc=<n> FAIL=<n>" en una carpeta
  temporal fuera del repo. Puerta: rc=0 y FAIL=0 en todos (test_motor_v400 mide tiempos y puede fallar una vez por
  carga: repítelo antes de investigar).
- Si falla un test viejo: si daba por hecho algo que el plan cambia a propósito, ajústalo sin debilitarlo y anótalo;
  si no, es un bug del cambio: causa raíz. Nunca debilites un test para que pase.
- Lecciones de G1-G3 para los tests: usa los helpers de tests/test_calendario.py (screen, key, _e, _jugar,
  _con_copa); en los tests del hub arma el calendario (league_screen.inicializar_calendario_liga) antes de
  dias.hoy; el cartel del mercado es por fecha: para silenciarlo pon
  e['datos_carrera']['aviso_mercado_visto'] = [1, '2026-07-01']; el nombre de la liga cambia entre cargas, no
  aserciones sobre él; sin reloj, temporada.fecha es la fecha de la jornada actual.
- Comprobación sin pantalla al terminar cada sub-proyecto (SDL_VIDEODRIVER=dummy, capturas con pygame.image.save y
  míralas), sin excepciones ni líneas ERROR en el log. Scripts temporales en el scratchpad, no en el repo.
- Solo te detienes por: una operación destructiva o irreversible, una acción de seguridad, un efecto fuera del repo
  (red, push, publicar), un plan tan roto que todo camino es adivinar, o una decisión que es de Diego. Si te
  bloqueas, sigue con lo que no dependa de eso y díselo; no adivines.

Al terminar entrega: estado por tarea, resultado de la suite completa de cada sub-proyecto, desviaciones con su
motivo, tests existentes que ajustaste y por qué, y lo que le queda a Diego por probar a mano. Actualiza
context.md (bitácora de cada sub-proyecto y fecha del encabezado). No hagas commit hasta que Diego dé el OK.
```
