# Prompt para una sesión nueva — lote siguiente (sin empezar)

Pégalo tal cual en una sesión nueva. Lo redactó el subagente de `lol2` el 2026-10-09 a partir del pedido de
Diego; `lol2` solo resolvió la duda de la versión. Nada de esta lista está implementado.

```text
Vas a implementar un lote nuevo de cambios en AlphaFootball, un juego de fútbol en Python 3 + Pygame.
Repo: C:\Users\diego\Downloads\AlphaFootball. Trabaja en español (código, comentarios y respuestas).

## Contexto

- El estado del juego es un dict `estado`; lo persistente vive en `estado['datos_carrera']`.
- La última versión hecha es la v0.4.17.0 (sanción de la liga por tope salarial y premios por fecha).
  Su revisión de código ya quedó corregida y en verde; no la rehagas.
- `VERSION`, el badge del README y el título de `context.md` ya están en 0.4.17.0 (eso era "la versión
  más actual del lote": ya está hecho). Este lote sería la 0.4.18.0, la próxima libre según la nota de
  memoria de numeración (formato 0.X.Y.Z). Confírmame el número antes de marcar comentarios.
- El árbol tiene mucho trabajo sin commit de varias versiones (0.4.11.0 a 0.4.17.0). No hagas commit,
  stash, reset ni checkout salvo que yo lo pida. Puede haber otras sesiones abiertas sobre este repo
  (`lol` y `lol2`): antes de editar, pregúntame si ya las cerré.
- La suite completa de 0.4.14.1–0.4.17.0 NO se corrió (decisión mía del 2026-10-09). No la corras salvo
  que te lo pida.

## Mi pedido, tal como lo escribí

"haz que la simulacion vaya un poco mas lento, dia por dia, un segundo por dia en la normal, en
calendario 0.5 sec, y que las ofertas sean en cifras cerradas, las unidades, decenas y centenas y unidad
de miles, deben ser cero. los canteranos tienen que tener almenos 10 de diferencia entre su media y
potencial, si sube su media, tambien su potencial, pero nerfea un porquito el boost de canteranos, hazlo
un poco mas que los jugadores normales pero aja, no tan chetado. en historial de pases tambien aparece la
fecha real, y haz menos por pagina, haz 8 por pagina y mas organizado, lo mismo en menu plantilla. cuando
se haga un fichaje efectivo en el ultimo dia, que aparezca una animacion de las 3 horas corriendo, o de
las horas que corren cuando pasa alguna venta/fichaje. que en los correos de partidos reprogramados, no
diga "para respetar los 3 dias de descanso". haz que el mensaje 3 victorias seguidas, se actualice y no
diga eso todo el rato por cada multiplo de 3, puede felicitar por 3 victorias, 5, 10, 15, 20, 25, 30,
cada vez con un mensaje mejor y mas asombrado"

## Los cambios, uno por uno

Las rutas y líneas son puntos de partida de un reconocimiento de solo lectura: verifícalas antes de
editar, porque pueden haberse movido.

1. Simulación más lenta, día por día.
   - Avance normal (CONTINUAR en el hub): 1 segundo por día. Hoy: `alpha_football/ui/league_screen.py`,
     `MS_DIA_AVANCE = 40` (línea ~391), usado por `_paso_avance`.
   - En el calendario: 0.5 segundos por día. Hoy: `alpha_football/ui/calendario_screen.py`,
     `MS_PASO_SIM, MS_TRAS_PARTIDO = 70, 450` (línea ~41).
   - Revisa qué tests dependen de esos ritmos antes de cambiarlos.

2. Ofertas en cifras cerradas: unidades, decenas, centenas y unidad de mil en cero, o sea múltiplos
   de 10.000.
   - Montos que hoy salen sin redondear: `alpha_football/market.py` líneas ~664, ~750 y ~954
     (`monto = int(valor * azar.uniform(...))`), y `alpha_football/salidas.py` línea ~262 y el `remate`
     de la ~272.
   - Sin revisar todavía: `contraofertas.py`, `mercado_ia.py` y `prestamos.py`. Búscalos tú.
   - Como mínimo aplica a las ofertas que recibo; si dudas de si incluir contraofertas y pedidos de la
     IA, pregúntame.

3. Canteranos.
   - Al menos 10 de diferencia entre media y potencial. Hoy nacen con `ovr + rng.randint(5, 12)` o
     `ovr + rng.randint(8, 20)` (`alpha_football/cantera.py`, líneas ~61 y ~64) y el potencial se topa
     en 99 (línea ~72), así que pueden quedar con menos de 10.
   - Si sube la media, sube también el potencial. Hoy `_crecer` (línea ~107) sube +1 a +4 de media con
     tope en el potencial.
   - Bajar un poco el boost de canteranos: que crezcan algo más que los jugadores normales, pero sin
     ser exagerado. No se ubicó ninguna constante de "boost" en `cantera.py`, ni cómo crecen los
     jugadores normales (mira `desarrollo.py`). Búscalo y, antes de tocar números, dime qué encontraste
     y qué propones.

4. Historial de pases y menú de plantilla.
   - Historial: mostrar la fecha real. Hoy muestra `T{temporada} J{jornada}`
     (`alpha_football/ui/historial_pases_screen.py`, línea ~130). No se verificó si los registros
     guardan una fecha; si no la guardan, hay que empezar a guardarla y dejar un respaldo para los
     registros viejos.
   - 8 por página y mejor organizado. Hoy `FILAS_VISIBLES` se calcula según la altura del panel (línea
     ~34).
   - Lo mismo en plantilla: `alpha_football/ui/plantilla_screen.py`, `FILAS_VISIBLES` (línea ~43).

5. Animación de las horas en el último día de mercado.
   - Cuando se concreta un fichaje (3 horas) o una venta (2 horas), mostrar las horas corriendo.
   - Lógica actual: `alpha_football/dia_final.py`, `gastar(estado, h)` (línea ~80), con
     `HORAS_FICHAJE = 3`, `HORAS_VENTA = 2` y `HORAS_ANALISIS = 3`. Hoy no hay animación y no se ubicó
     dónde se dibuja el reloj de horas (empieza por el panel ÚLTIMO DÍA del hub en `league_screen.py`).

6. Correo de partido reprogramado: quitar la frase "Para respetar los {MIN_DIAS} días de descanso
   entre partidos". Está en `alpha_football/calendario.py`, `_avisar_cambio` (línea ~298). El resto del
   correo se queda.

7. Racha de victorias.
   - Hoy `alpha_football/vestuario.py` (líneas ~205-212) guarda los últimos 3 resultados en
     `dc['racha']` y la vacía al avisar, por eso el mensaje "Tres victorias seguidas" sale en cada
     múltiplo de 3.
   - Quiero felicitación solo al llegar a 3, 5, 10, 15, 20, 25 y 30 victorias seguidas, cada una con un
     mensaje mejor y más asombrado que el anterior.
   - No rompas el aviso de tres derrotas seguidas ni `dc['ult_res']`, que usa `eventos.va_mal`.

## Duda que tienes que resolver conmigo antes de tocar números

- Punto 3: a qué boost de canteranos me refiero, una vez que veas cómo crecen hoy ellos y los demás.

## Cómo trabajar

- TDD: para cada punto, primero el test, míralo fallar por la razón correcta, después el código mínimo.
- Los tests son archivos con funciones `test_*`, una lista `TESTS` al final y un bloque `__main__`.
  Para montar un estado: `from test_revision_v291 import estado_carrera`.
- Para iterar: `python -m pytest tests/<archivo>.py -q -p no:cacheprovider -k "<nombre>"`. Al final,
  cada archivo con su runner: `python tests/<archivo>.py`.
- No corras `pytest tests` entero ni más de un proceso de tests a la vez: la máquina está corta de CPU.
- Usa `PYTHONIOENCODING=utf-8` al correr tests: `tests/test_finanzas_v290.py` falla en la consola
  cp1252 solo por imprimir "→".
- En Windows no pegues código con heredocs de Bash (se comen las barras invertidas): usa Write/Edit.
- Para lo visual (puntos 1, 4 y 5): renderiza con `SDL_VIDEODRIVER=dummy`, guarda un PNG con
  `pygame.image.save` y míralo antes de darlo por bueno. La pantalla es de 1280x720.
- Comentarios en español con la densidad del código vecino, y lo nuevo marcado con el número de
  versión del lote.

## Qué quiero al final

Por cada punto: qué cambiaste (archivo y función), el test y lo que viste al fallar y al pasar, y
cualquier desviación con su motivo. Después: el resultado de cada archivo de tests que corriste, qué
viste en cada captura, la lista exacta de archivos tocados y lo que haya quedado sin hacer.
```
