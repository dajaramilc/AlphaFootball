# Calendario real, último día de fichajes, presupuesto por temporada y auto-actualización — diseño (v0.4.11.0)

**Fecha:** 2026-10-06
**Estado:** diseño aprobado en conversación, pendiente de revisión del spec

## Objetivo

Once pedidos de Diego (más el desfase entre continentes que salió al revisar el spec), agrupados
en seis sub-proyectos que se implementan y prueban por separado, en este orden: A, B, C, D, E y F
al final (D depende de B y C; F es el más delicado y va cuando lo demás ya se puede jugar).

| | Sub-proyecto | Pedidos |
|---|---|---|
| A | Ajustes | volver a la notificación, goles de todas las competiciones, ofertas al DT realistas, objetivos más exigentes, boost de canteranos |
| B | Economía y mercado | el saldo no se acumula entre temporadas, sin mercado de pretemporada, sin ventana de cierre |
| C | Calendario real | fechas reales por continente, descanso, reprogramación, pantalla CALENDARIO |
| D | Último día de fichajes | 20 horas el 31 de agosto y el 31 de enero |
| E | Auto-actualización | el juego se actualiza solo desde GitHub al iniciar |
| F | Temporadas por continente | Sudamérica enero–diciembre, Europa agosto–mayo, desfasadas media temporada |

## Decisiones de Diego (2026-10-06)

- El calendario **afecta el descanso**: la energía se recupera según los días entre partidos.
- El último día de fichajes es una **fecha del calendario**: 31 de agosto y 31 de enero.
- Presupuesto nuevo = **base × salud × objetivo**; el sobrante no pasa de temporada.
- La actualización se instala **sola**; una copia de desarrollo con cambios sin commitear solo avisa.
- Las ligas **sudamericanas van de enero a diciembre**; las europeas, de agosto a mayo. Corren
  desfasadas: cuando una empieza, la otra va por la mitad.
- La **temporada 1 europea es la 2026/27**.
- "Mercado de pretemporada" es la ronda de fichajes de la IA entre temporadas, y el boost de
  cantera es para el canterano que subes al primer equipo (confirmados).

## Supuestos míos (corregir si no es así)

- Una carrera sudamericana empieza en **enero de 2027**, con Europa a mitad de la 2026/27. Una
  carrera europea empieza en agosto de 2026, con Sudamérica a mitad de su 2026.
- El Balón de Oro se entrega al cerrar **tu** temporada, entre la temporada que acaba de terminar
  en tu continente y la última que terminó en el otro.
- Edad, retiros y contratos siguen siendo una vez por año para todos, al cerrar tu temporada.

## Fuera de alcance

- Ligas de 38 jornadas (el calendario ya se genera a partir de `num_jornadas`, pero no se cambia).
- Avanzar día por día: se sigue jugando de partido en partido; el único "día" con reloj es el último
  de cada ventana.
- Calendario distinto por país dentro de un continente (Apertura/Clausura, etc.).
- Instalar versiones anteriores, canal beta o notas de la versión dentro del juego.
- Que el presupuesto de la IA se recalcule (sigue con sus ingresos y su quiebra).

---

## A · Ajustes

### A1. Volver a la notificación
Al abrir una pantalla con Enter (o el botón de acción) desde un mensaje, `correo_screen._ir` deja
`estado['volver_notif'] = <pantalla destino>`. Mientras esa marca exista y estés en esa pantalla,
VOLVER/ESC lleva a `correo_screen` (mismo canal y mismo mensaje seleccionado: `correo_canal` y
`correo_sel` ya viven en `estado`) en vez de al hub.

- Se resuelve en un solo punto: el bloque de transición de `main.py` (cuando la pantalla marcada
  devuelve `'volver'` o `'league_screen'`).
- Destinos que son una pestaña del hub (NEGOCIACIONES): ESC en esa pestaña vuelve al correo.
- La marca se borra al volver al correo, al llegar al hub por otro camino o al jugar un partido.
- Si desde el destino navegas más adentro (plantilla → ficha → negociar), la marca se conserva y
  vale cuando regreses a la pantalla marcada.

### A2. Goles de todas las competiciones
`premios.py` ya suma goles de copa por `(club, nombre)`. Se expone un helper
`competiciones.goles_copa_de(estado, jugador, club)` y la tarjeta de Dirección de equipo
(`team_screen`, línea "Goles") muestra liga + copa. La ficha compartida (`ficha_jugador`) y la
columna de PLANTILLA usan el mismo total. `Jugador.goles` sigue siendo solo liga (goleadores de
liga, Balón de Oro y objetivos de patrocinio no cambian).

### A3. Ofertas al DT realistas
Causa: `entrenadores.en_banda` solo tiene techo (`suyo <= tope`), así que cualquier club más flojo
entra, aunque esté 20 puntos de media por debajo. Se agrega un piso por calificación:

| Calificación | Media del club que ofrece (respecto de la tuya) |
|---|---|
| ≥ 70 | −2 a +10 |
| 55–69 | −4 a +5 |
| < 55 | −6 a 0 |

`ofertas_dt.NIVELES` ya tiene bandas con piso y no cambia. La pantalla de despido
(`directiva.opciones_de_club`) tampoco: ahí sigue valiendo "siempre hay al menos una oferta".

### A4. Objetivos más exigentes
Solo para ti como DT. `objetivo_por_ranking` recibe un parámetro `exigente`; lo pasan
`directiva.definir_objetivo` y `ofertas_dt._objetivo_de` (el objetivo que te pondría el club que te
ofrece). `nivel_temporada` (subidas y bajones de nivel de los clubes de la IA) sigue con el criterio
actual, para no mover el equilibrio de las ligas.

- Con `exigente`, en 1ª: la meta es **dos puestos** por encima de tu ranking por media (mínimo 1º),
  "terminar entre los N primeros" se pide hasta un puesto por debajo de la mitad de la tabla y el
  título se exige con 3 o más de ventaja sobre el 2º (hoy 5). En 2ª es un solo puesto extra, porque
  ya es la división más dura (50–57% de cumplimiento con el criterio de la IA).
- Calibrado con 60 temporadas simuladas por liga; la meta era que el cumplimiento bajara entre 10 y
  15 puntos. Medido en 1ª: Premier 68.3 → 56.2% (−12.1) y BetPlay 65.7 → 53.8% (−11.9). En 2ª:
  Premier 50.3 → 44.0% y BetPlay 57.4 → 49.7%. La primera versión (un puesto extra) bajaba solo 4.

### A5. Boost de canteranos
- `Jugador.canterano: bool` (nuevo; se guarda). `cantera.subir` lo pone en `True`.
- En `desarrollo` (línea del `_factor_progreso_edad`), el canterano de 23 años o menos progresa
  ×1.5. Vale mientras siga en el club que lo formó: al venderlo o cederlo se apaga.
- La ficha muestra "Canterano" junto al rasgo.

---

## B · Economía y mercado

### B1. Presupuesto por temporada
Al pasar de temporada el saldo no se arrastra. En `finanzas.cierre_temporada`, después del control
de números rojos (que no cambia: −6 puntos la primera vez, despido la segunda):

```
presupuesto = presupuesto_base(club, liga, división nueva) × salud × objetivo × (1 + bonos)
```

| Factor | Valor |
|---|---|
| **salud** (saldo de cierre ÷ base) | en rojo 0.80 · menos de 25% 0.90 · 25–75% 1.00 · 75–150% 1.10 · más de 150% 1.20 |
| **objetivo** de liga | superado 1.25 · cumplido 1.10 · fallado 0.85 |
| **bonos** | campeón de liga +0.15 · campeón de copa +0.20 |

- Tope del multiplicador total: 1.75. Piso: 0.60.
- Si cerraste en rojo, la deuda se descuenta entera del presupuesto nuevo (piso: 10% de la base).
- `presupuesto_base` ya depende de la liga, la división y las estrellas ("calidad"); con ascenso o
  descenso se usa la división nueva.
- Los premios de liga, copa y directiva se siguen acreditando al saldo durante el cierre: ya no
  se acumulan, pero mejoran la salud con la que el club calcula.
- Correo "Presupuesto de la temporada N" (remitente directiva, acción VER FINANZAS) con el
  desglose: sobrante que se queda el club, base, salud, objetivo, bonos y total.
- OBJETIVOS y el correo de objetivos agregan una línea: "Superarlo sube el presupuesto de la
  próxima temporada 25%; cumplirlo, 10%; fallarlo lo baja 15%".

### B2. Sin mercado de pretemporada
- `avanzar_nueva_temporada` ya no llama a `ronda_fichajes_ia(estado, 'pretemporada')`. El paso de
  la barra de carga pasa a llamarse "Ingresos de los clubes".
- Para que la IA no quede quieta, en la ventana de inicio `ronda_fichajes_ia('ventana')` es más
  activa: participa el 50% de los clubes (25% en invierno) y los recién ascendidos hacen hasta 2
  intentos. Fichan a la vez que tú, jornada a jornada.
- `vender_salidas_forzadas` (jugadores que piden salir tras descender) se queda donde está.

### B3. Sin ventana de cierre
`market.ventanas_mercado(n)` devuelve solo `inicio` (J1–3) e `invierno` (J n/2 a n/2+2). Ajustes:

- `clave_ventana_traspaso`: `inicio` → `T-verano`, `invierno` → `T-invierno`.
- Préstamos (`prestamos._regreso`): 6 meses desde inicio → invierno de la misma temporada; desde
  invierno → inicio de la siguiente; 1 año → la misma ventana de la temporada siguiente. Un
  préstamo guardado con ventana `'cierre'` vuelve en el inicio de la temporada siguiente.
- `prestamos._avisar_contratos` (cedidos con contrato por vencer) pasa a las 3 últimas jornadas.
- `negociacion` (ventana por defecto `'cierre'`) y `aviso_mercado` (cartel de apertura en J n−2).
- Traspasos acordados con el mercado cerrado después del invierno: se concretan en la J1 de la
  temporada siguiente (`proxima_apertura` ya devuelve 1).

---

## C · Calendario real

Módulo nuevo `alpha_football/calendario.py` (sin UI) y pantalla `ui/calendario_screen.py`.

### C1. Generación
El calendario se arma **a partir de las ventanas de mercado**, para que las fechas de cierre
caigan exactas sin tocar la lógica por jornada. Con `inicio = (1, k1)` e `invierno = (a, k2)`:

| Tramo | Jornadas | Europa (agosto–mayo) | Sudamérica (enero–diciembre) |
|---|---|---|---|
| 1 | 1 … k1−1 | últimos fines de semana de agosto, antes del 31 | últimos de enero, antes del 31 |
| — | cierre de inicio | **31 de agosto** | **31 de enero** |
| 2 | k1 … a−1 | primer sábado de septiembre → 21 de diciembre | primer sábado de febrero → 20 de julio |
| 3 | a … k2−1 | enero, antes del 31 | agosto, antes del 31 |
| — | cierre de invierno | **31 de enero** | **31 de agosto** |
| 4 | k2 … n | primer sábado de febrero → último de mayo | primer sábado de septiembre → 13 de diciembre |

Los dos cierres del mercado son las mismas dos fechas del mundo para todos (31 de enero y 31 de
agosto); solo cambia cuál es el de inicio y cuál el de mitad de temporada. En Sudamérica la
ventana de mitad de temporada también cae en invierno, así que conserva el nombre.

Con 22 jornadas en Europa: J1–J2 en agosto, J3–J10 de septiembre a diciembre, J11–J12 en enero,
J13–J22 de febrero a mayo. En Sudamérica: J1–J2 en enero, J3–J10 de febrero a julio, J11–J12 en
agosto, J13–J22 de septiembre a diciembre. Con 38 se reparte igual sin tocar el código; si un
tramo no tiene suficientes fines de semana, se alarga hacia adelante.

- **Año:** `datos_carrera['mundo']['anio']` guarda el año de la temporada en curso de cada
  continente (Europa 2026 = "2026/27"; Sudamérica 2027 = "2027") y suma uno cuando ese continente
  cierra su temporada. El calendario del user usa el de su continente.

- **Liga:** tu partido cae sábado (55%), domingo (40%) o lunes (5%).
- **Copa:** la fecha `i` se sigue jugando tras la jornada `fechas_jornada[i]` (el orden no
  cambia). Cae martes (40%), miércoles (45%) o jueves (15%) de una semana entre esas dos jornadas,
  nunca antes del 31 de agosto / 31 de enero si le toca ese hueco. La final es el sábado
  siguiente a la última jornada.
- Azar con semilla (temporada + club + jornada): el calendario no cambia al guardar y cargar.

### C2. Reprogramación
Dos partidos tuyos necesitan al menos 3 días entre sí (sábado→martes vale; domingo→martes y
jueves→sábado no). `calendario.revisar_choques(estado)` corre al empezar la temporada y al cerrar
cada partido, mira tus próximos partidos confirmados y, si chocan:

1. mueve el de liga dentro de su fin de semana (sábado ↔ domingo ↔ lunes);
2. si no alcanza, mueve el de copa dentro de martes–jueves;
3. si no alcanza, pasa el de liga al fin de semana siguiente libre.

Cada cambio manda un correo "Partido reprogramado" (qué partido, de qué día a qué día y por qué).

### C3. Descanso y energía
Hoy todos recuperan una vez por jornada de liga (`energia.recuperar_todos`) y nada tras la copa.
Ahora la recuperación es proporcional a los días que pasan:

```
recuperación = recuperacion(j) × días / días_por_jornada
días_por_jornada = (fecha de la última jornada − fecha de la primera) / (n − 1)     # ≈ 13 con 22
```

- En una temporada entera se recupera lo mismo que hoy; cambia el reparto: un hueco de 3 días
  recupera poco y uno de 2 semanas recupera de más (tope 100).
- `finalizar_jornada_liga`: recupera los días hasta el próximo partido de cualquier competición
  antes de simular la copa de fondo, y el resto después. Si tienes un partido de copa pendiente en
  ese hueco, el resto se aplica al cerrar ese partido.
- `recuperar_todos(estado)` sin días conserva el comportamiento actual (tests y saves sin calendario).

### C4. Datos e interfaz
`datos_carrera['calendario'] = {'clave': [año, continente, jornadas, club], 'mov': {partido:
'AAAA-MM-DD'}}`. Se arma la primera vez que se consulta (`calendario.asegurar`), también en saves
viejos, y se rearma solo al cambiar de temporada, de liga o de club.

- `fecha_liga`, `fecha_copa`, `hoy` (el día de tu próximo partido: donde estás parado antes de
  jugar), `proximo_evento`, `texto_fecha` ("sáb 15 ago 2026").
- **Fecha del partido:** arriba a la derecha del botón JUGAR y en el pre-partido. No va en la
  cabecera del hub porque no tiene lugar (ya está al límite con la franja del mercado).
- **Pantalla CALENDARIO** (tarjeta en DIRECCIÓN DE EQUIPO; OFICINA ya está llena con 8): mes en
  cuadrícula de 7 columnas con tus partidos de liga (rival, L/V, resultado si ya se jugó), los de
  copa, los dos cierres de mercado y el día de tu próximo partido resaltado. ← → cambia de mes,
  ESC vuelve. Con ayuda (H) y barra de atajos.
- Lo único que se guarda es lo reprogramado (`mov`): las fechas base salen de una semilla.

---

## D · Último día de fichajes

Módulo nuevo `alpha_football/dia_final.py` (sin UI); la interfaz vive en el hub.

### D1. Cuándo
Al llegar a la última jornada de una ventana (J3 y J13 con 22 jornadas) empieza el último día:
31 de agosto o 31 de enero según el continente (ver C1), con **20 horas**. Las jornadas anteriores de la ventana siguen como
hoy, sin reloj. Estado en `datos_carrera['dia_final'] = {'clave': 'T-inicio', 'horas': 20}` y, al
terminar, `datos_carrera['mercado_cerrado'] = 'T-inicio'`.

### D2. El reloj

| Acción | Horas |
|---|---|
| AVANZAR 1 HORA | 1 |
| Fichaje inscrito (compra, agente libre o préstamo que llega) | 3 |
| Venta o cesión concretada | 2 |
| "Lo analizamos" (club, jugador o préstamo) | responde a las 3 horas |

- Negociar, ofertar y contraofertar no gastan horas; solo lo que se concreta.
- Con menos horas de las que cuesta, el trato no llega a inscribirse hoy: queda **acordado para la
  próxima ventana**, igual que con el mercado cerrado (`traspasos_pendientes`).
- Un "lo analizamos" pedido con menos de 3 horas se responde en el momento: "no hay tiempo".
- Cada hora que pasa: llegan las respuestas que vencen y puede entrar una oferta por un jugador
  tuyo (10% por hora; 25% si tienes transferibles o alguien que pide salir).
- A las 0 horas, o con CERRAR MERCADO (pide confirmación): se retiran las ofertas sin responder,
  los análisis pendientes se caen con un correo, la IA hace su ronda de cierre y aparece el cartel
  MERCADO CERRADO. Recién entonces se puede jugar.

### D3. Integración
- `traspasos_pendientes.mercado_abierto(estado)` es la única pregunta "¿puedo operar ya?": además
  de la ventana por jornada, mira `mercado_cerrado`. Los llamados directos a
  `ventana_mercado_abierta` que deciden por el user (contraofertas, negociación, salidas, ojeador)
  pasan a usarla.
- `contraofertas` y `prestamos`: los análisis guardan la hora de respuesta cuando hay reloj.
- **Hub:** en INICIO la tarjeta JUGAR se reemplaza por el panel del día (fecha, horas, AVANZAR 1
  HORA, CERRAR MERCADO); la franja de mercado dice "ÚLTIMO DÍA · quedan 14 h". Cartel al empezar
  el día ("tienes 20 horas") y al terminar. El cartel de cierre ya no sale en la J4.
- Un save viejo cargado en J3 o J13 arranca el día con 20 horas.

---

## E · Auto-actualización

Módulo nuevo `alpha_football/actualizador.py`; se llama una vez en `main()`, con la ventana ya
creada y antes del menú.

1. **Versión:** archivo `VERSION` en la raíz (`0.4.11.0`). `alpha_football.__version__` lo lee y el
   título de la ventana lo usa.
2. **Consulta:** baja `VERSION` de `raw.githubusercontent.com/dajaramilc/AlphaFootball/main` con 4 s
   de espera. Sin red o con error: se sigue jugando sin avisar (queda en el log).
3. **Si la remota es mayor,** según la copia:

| Copia | Qué hace |
|---|---|
| Sin `.git` (ZIP descargado) | baja el ZIP de `main`, lo valida y copia los archivos encima |
| Con `.git` y limpia | `git pull --ff-only` |
| Con `.git` y cambios sin commitear o commits sin subir | no instala; aviso en el menú: "Hay una versión nueva (X)" |

4. **Nunca se pisan** (datos del jugador): `saves/`, `preferencias.json`, `music/`, `musica.txt`,
   `alpha_football_save.json*`, `alpha_football_edited_db.json`, `alpha_football_db_custom.json`,
   `context.md`.
5. **Validación del ZIP:** trae `main.py` y un `VERSION` igual al consultado; ninguna ruta sale de
   la carpeta de instalación; se descomprime en una carpeta temporal y recién después se copia. Si
   algo falla, no se toca nada.
6. **Después:** si cambió `requirements.txt`, `pip install -r` (como con yt-dlp); el juego se
   reinicia solo. Pantalla de carga "ACTUALIZANDO A X" con pasos reales (`ui/pantalla_carga`).

Para que una versión llegue a los jugadores, Diego sube `VERSION` y hace push a `main`.

---

## F · Temporadas por continente

Hoy las 16 ligas arrancan juntas en la J1 y cierran juntas en `avanzar_nueva_temporada`. Ahora cada
continente tiene su temporada y van desfasados media temporada (`n // 2` jornadas): tu J1 es la
J12 del otro continente, y tu J12 es su J1.

Las ligas de fondo ya avanzan cada una por su propio calendario (una jornada suya por cada jornada
tuya), así que el desfase no cambia el ritmo: cambia **dónde empiezan** y **cuándo cierran**.

### F1. Al crear la carrera
`temporadas.arrancar_desfase(estado)` (módulo nuevo `alpha_football/temporadas.py`): las ligas del
otro continente juegan de fondo su primera mitad (J1–J11) y su copa las fechas que correspondan.
Quedan con tabla, goleadores y copa a medio camino. Paso propio en la barra de carga.

### F2. Cierre del otro continente (a mitad de tu temporada)
Cuando sus ligas terminan su última jornada (tras tu J11), `temporadas.cerrar_continente(estado,
continente)` hace solo para sus países lo que hoy hace el cierre general:

1. termina su copa y guarda el campeón;
2. congela sus candidatos al Balón de Oro;
3. guarda la tabla final de cada 1ª (clasificados a su próxima copa);
4. nivel de temporada y objetivos de sus clubes, y despidos de DTs de fin de temporada;
5. ascensos y descensos;
6. tablas, estadísticas de temporada, sanciones y calendario nuevos (vuelven a la J1);
7. ingresos de temporada de sus clubes y sorteo de su copa nueva;
8. suma un año a ese continente y te llega un correo con sus campeones, ascensos y descensos.

### F3. Tu cierre de temporada
`avanzar_nueva_temporada` hace esos mismos pasos **solo para tu continente**, más lo que sigue
siendo anual para todos: edad y desarrollo pasivo, retiros y regens, contratos, tus finanzas,
objetivos, historial y Balón de Oro. Ya no completa ni reinicia las ligas del otro continente.

Para no duplicar lógica, los pasos por liga se extraen de `avanzar_nueva_temporada` a
`temporadas.py` y las funciones que hoy recorren todas las ligas (`nivel_temporada`,
`entrenadores.cierre_temporada`, `mercado_ia.ingresos_fin_temporada`, `guardar_ranking_copas`,
`completar_ligas_de_fondo`) reciben un filtro opcional de países. Sin filtro se comportan como hoy.

### F4. Copas
La Champions sigue la jornada de las ligas europeas y la Libertadores la de las sudamericanas
(hoy las dos siguen la tuya). Cada una se sortea al empezar la temporada de su continente y
termina al cerrarla.

### F5. Cambiar de continente
Si aceptas un club del otro continente, sigues desde la jornada en la que va esa liga y con su
calendario y su año. Tu temporada termina cuando termina esa liga; el desfase con el continente
que dejaste se mantiene solo. `estado['temporada']` sigue contando tus cierres.

### F6. Partidas guardadas
Una partida vieja sigue con todas las ligas a la par hasta tu próximo cierre de temporada; justo
después corre `arrancar_desfase` y desde ahí va desfasada. Hasta entonces usa el calendario de su
continente con los años de C1. El desfase se marca en `datos_carrera['mundo']['desfase']`; sin esa
marca todo el código se comporta como hoy (así los tests actuales siguen valiendo).

---

## Compatibilidad con saves

- Campos nuevos con valor por defecto: `Jugador.canterano`, `datos_carrera['calendario']`,
  `['dia_final']`, `['mercado_cerrado']`, `['mundo']`.
- Un save a mitad de temporada genera su calendario al cargarse; lo ya jugado toma sus fechas.
- Un save en las 3 últimas jornadas (antes ventana de cierre) carga con el mercado cerrado; los
  tratos acordados se concretan en la J1 siguiente.
- El saldo acumulado de un save viejo se recalcula recién al pasar de temporada.

## Tests

Archivos nuevos: `test_ajustes_v0411.py` (A), `test_presupuesto_ventanas.py` (B),
`test_calendario.py` (C), `test_dia_final.py` (D), `test_actualizador.py` (E, sin red: consulta y
descarga falsas, como `test_musica_actualiza_ytdlp`), `test_temporadas_continente.py` (F: arranque
desfasado, cierre del otro continente a mitad de temporada, dos temporadas seguidas sin perder el
desfase, cambio de continente y conversión de un save viejo).

Se ajustan los que dan por hecha la ventana de cierre, la ronda de pretemporada, la recuperación
fija por jornada, el margen de objetivos o `en_banda` sin piso. Suite completa con
`PYTHONIOENCODING=utf-8`, revisando los logs (hay tests que salen con 0 aunque impriman FAIL).

## Versión

0.4.11.0: `VERSION`, título de la ventana, badge del README, comentarios `# v0.4.11.0` y bitácora
en `context.md`.
