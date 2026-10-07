# Nacionalidades reales, aviso de renovación, eventos aleatorios y notificaciones — diseño (v0.4.10.0)

**Fecha:** 2026-10-04
**Estado:** diseño aprobado en conversación, pendiente de revisión del spec

## Objetivo

Hacer el juego más realista y más vivo entre partidos:

1. Cada jugador y cada DT tiene su **nacionalidad real** (la de la persona a la que parodia).
2. Un jugador contento al que se le acaba el contrato **escribe pidiendo renovar**.
3. **21 eventos aleatorios de vestuario** (la riña del polémico + 20 más) que llegan por correo,
   piden una decisión del DT y tienen consecuencias en moral, forma, energía, sanción, lesión,
   dinero, confianza y desarrollo.
4. "CORREO" pasa a ser **NOTIFICACIONES**, separado en **MENSAJES** (jugadores y presidente) y
   **CORREO** (club), con vista previa de los últimos 5 de cada lado. La tecla M abre ahí.

## ⚠ IMPORTANTE — consecuencias en la futura sección NOTICIAS

**Las consecuencias de cada decisión salen en la futura sección NOTICIAS.** Es un requisito
explícito de Diego y condiciona el diseño:

- Toda consecuencia de un evento se registra como **noticia** en `datos_carrera['noticias']`
  (ver §3.5), no solo como un cambio silencioso de números ni solo como texto del correo.
- La sección NOTICIAS (pantalla) **no existe todavía y no se construye en esta versión**; cuando
  se construya, lee de ese registro sin tocar `eventos.py`.
- Mientras no exista la pantalla, el correo del evento muestra un resumen de una línea de lo que
  pasó tras decidir, para que la decisión no quede a ciegas. *(Supuesto mío: si Diego prefiere que
  la consecuencia se vea SOLO en noticias, se quita esa línea.)*
- Cada noticia se redacta como titular + cuerpo en tono de prensa, no como log técnico.

## Numeración de versiones

Desde esta versión el número se divide por 10: el juego está lejos de la 1.0. La 4.9.2 es la
**0.4.9.2** y este trabajo es la **0.4.10.0**. Regla: la vieja `vX.Y.Z` equivale a `0.X.Y.Z`.
Los comentarios `# vX.Y.Z` del código, los nombres de los tests y los commits ya hechos no se
reescriben; lo nuevo (comentarios, commits, README, título de la ventana, `context.md`) usa la
numeración nueva.

## Fuera de alcance

- La pantalla NOTICIAS.
- Eventos para los clubes de la IA: solo le pasan al club del user.
- Editar la nacionalidad desde el editor.
- Banderas o imágenes: la nacionalidad es texto.
- Cupos de extranjeros o cualquier regla de juego ligada a la nacionalidad.

## 1. Nacionalidad real

### 1.1 Datos

Archivo nuevo `alpha_football/data/nacionalidades.py`:

- `NACIONALIDAD_JUGADOR: dict[str, str]` — `"Nombre Apellido"` (nombre parodia completo, tal
  cual está en los datos) → país en español (`"Francia"`, `"Brasil"`, …). Se escribe agrupada por
  país (`_POR_PAIS = {"Francia": [nombres…]}`) y se invierte al importar. **Solo lleva a los
  extranjeros** (nacionalidad real ≠ país de la liga donde arrancan): el local ya recibe el país
  de su liga por la regla de §1.2, así que no hace falta listarlo.
- `PAIS_CLUB: dict[str, str]` — país de los 18 clubes de Champions y Libertadores (no tienen
  liga jugable): es su "país de la liga" para la regla de §1.2.
- `NACIONALIDAD_DT: dict[str, str]` — nombre parodia del DT → país.
- `nacionalidad_real(nombre_completo) -> str` — busca exacto y, si falla, normalizado (sin
  tildes, minúsculas, espacios colapsados). Devuelve `""` si no está.

Cobertura: se revisan los ~4.267 nombres únicos de la base (1ª, 2ª, Champions, Libertadores), los
22 agentes libres de `data/free_agents.py` (todos van a la tabla: no tienen liga) y los 69 DTs de
`data/entrenadores.py`. Entra a la tabla todo extranjero que parodia a una persona real reconocible.
Limitación conocida: un jugador local movido a un club de otro país **en el editor** toma el país
de su liga nueva. **No entran** los nombres inventados (gran parte
de la 2ª de Colombia, Ecuador y Brasil: "Julián Sofoco", "Wilmer Encebollado") ni aquellos donde la
persona parodiada sea dudosa: esos conservan el país de su liga. Mejor local que inventado.

Los nombres de país coinciden con los de `paises.PAISES` para los 8 países jugables, para que los
regens encuentren su lista de nombres.

### 1.2 Aplicación

`retiros.asignar_nacionalidades(estado)` pasa a:

1. Para cada jugador de cada liga, de `free_agents_list` y de la cantera: si
   `nacionalidad_real(nombre)` devuelve país, se asigna.
2. Si no, y la nacionalidad está vacía, país de la liga (como hoy).

La tabla manda sobre el valor guardado **una sola vez por partida**: se marca
`datos_carrera['nac_reales'] = True`. Así los saves viejos (que tienen el país de la liga en
todos) se corrigen al cargar, y después no se pisa nada. Los agentes libres que aparecen cada
jornada reciben la suya al crearse (`get_free_agents`).

### 1.3 DTs

- `entrenadores._nuevo(...)` acepta `nacionalidad` y la guarda en el dict del DT.
- `asegurar_dts`: DT real → `NACIONALIDAD_DT`; DT generado o interino → país de la liga del club.
  DTs de saves viejos sin el campo se completan con la misma regla.
- Se muestra junto al nombre del DT donde ya aparece (visor del rival, ofertas de banquillo,
  OTRAS LIGAS). El user ya tiene `dt_nacionalidad`.

### 1.4 Regens y cantera

`retiros` genera el regen con la nacionalidad del retirado. Si esa nacionalidad no tiene lista en
`NOMBRES_POR_PAIS` (p. ej. Francia), el regen toma **el país de la liga del club** (nombre y
nacionalidad coherentes) en vez de caer en 'España'.

## 2. Jugador que pide renovar

Ya existe la acción de correo `{'renovar': id}` (`correo_screen._ir`) que abre la negociación de
renovación. Se reutiliza.

Nuevo `salidas.revisar_renovaciones(estado)`, llamado desde `salidas.cierre_jornada`:

- Condiciones: jugador del user, `contrato_anios == 1`, `moral >= 75`, no `pide_salir`, no
  `salida_forzada`, sin `prestamo`, y jornada actual ≥ mitad de la temporada.
- Máximo **un correo por jornada** (el de mayor OVR primero) y **uno por jugador y contrato**:
  campo nuevo `Jugador.renovacion_avisada: bool` (se guarda; se limpia en `negociacion.renovar`
  y al cambiar de club).
- Correo de remitente `jugador`, asunto `"{nombre} quiere renovar"`, texto en primera persona
  (varias plantillas según personalidad) y botón **RENOVAR**.
- Si renueva con `renovacion_avisada` activo: +5 de moral además de lo que ya da `al_renovar`.
- Si no renueva, al cierre de temporada se va libre como hoy.

## 3. Eventos aleatorios

Módulo nuevo `alpha_football/eventos.py`, sin UI.

### 3.1 Sorteo

`eventos.cierre_jornada(estado, rng)` se llama una vez por jornada de **liga** del user, en
`match_screen.finalizar_jornada_liga` justo después de `salidas.cierre_jornada`. Primero resuelve
por defecto el evento que quedó sin responder, luego revisa las promesas y por último sortea.

- `PROB_BASE = 0.12`; `PROB_MAL = 0.45` si el equipo va mal.
- **Va mal** = 2+ derrotas en los últimos 3 partidos (historial propio `datos_carrera['ult_res']`,
  porque `racha` se reinicia) **o** `entrenadores._va_mal(liga, mi_equipo)`.
- Si sale evento: se filtran los del catálogo cuya condición se cumple y se elige por peso.
- **Riña:** si va mal y hay un `polemico` disponible, su peso es 60 (los demás, 3–10), así que
  es lo más probable con diferencia.
- Límites: máximo 1 evento por jornada; el mismo evento no se repite en 6 jornadas
  (`datos_carrera['eventos_vistos']`); no se sortea si hay un evento sin responder.

### 3.2 Catálogo

`EVENTOS`: lista de dicts `{id, peso, condicion(estado, ctx) -> protagonistas | None, remitente,
asunto, cuerpo, opciones}`. Cada opción: `{texto, efectos, noticia}`. La primera opción marcada
`por_defecto` es la de "dejarlo pasar".

| # | id | Condición | Opciones → efectos |
|---|---|---|---|
| 1 | `rina` | va mal + polémico | Multar: él −10 moral, plantel +2, +dinero · Apartar 2 partidos: sanción interna 2, él −15, plantel +4 · *Dejarlo pasar*: plantel −6, confianza −3 |
| 2 | `pelea_entreno` | 2 jugadores | Sancionar al agresor: sanción 1, lesión 1–2 del otro · *Mediar*: lesión 1–2, ambos −4 |
| 3 | `salida_nocturna` | — | Multar: él −6, +dinero, energía −20 · *Perdonar*: energía −20, plantel −2 |
| 4 | `llega_tarde` | polémico/mercenario | Banquillo: sanción interna 1, él −6 · *Charla*: él −2 |
| 5 | `critica_prensa` | moral < 50 | Sancionar: sanción 1, él −10, confianza +2 · Hablar: él +6 · *Ignorar*: confianza −4 |
| 6 | `charla_lider` | va mal + líder | Apoyarla: plantel +6 · *Cortarla*: líder −8 |
| 7 | `exige_titular` | bueno con 3+ jornadas sin jugar | Prometer minutos: él +8 (y −12 si en 3 jornadas no juega) · *Negarse*: él −8 |
| 8 | `lesion_entreno` | — | Reposo: lesión 2–3 · *Infiltrar*: lesión 1, 30% recaída +3 |
| 9 | `gripe` | — | Aislar a 3: se pierden 1 partido · *Que entrenen*: 6 jugadores energía −15 |
| 10 | `nace_hijo` | — | Dar permiso: se pierde 1 partido, él +15 · *Negarlo*: él −10 |
| 11 | `seleccion` | OVR alto; usa su nacionalidad | Dejarlo ir: energía −25, él +8 · *Retenerlo*: él −8 |
| 12 | `nostalgia` | nacionalidad ≠ país de la liga | Días libres: se pierde 1 partido, él +10 · *Negarse*: él −6, forma − |
| 13 | `entreno_extra` | profesional | Permitir: forma +, energía −12 · *Frenar*: nada |
| 14 | `escandalo_redes` | — | Multar: él −6, confianza +2, +dinero · *Defenderlo*: él +6, confianza −3 |
| 15 | `rumor_oferta` | mercenario | Prometer aumento: él +6 (y −10 si en 6 jornadas no le subiste el sueldo) · *Ignorar*: él −6, forma − |
| 16 | `prima_capitan` | — | Pagar: −dinero, plantel +5 · *Negarse*: plantel −3 |
| 17 | `asado` | — | Pagarlo: −dinero, plantel +4, energía −5 · *Prohibirlo*: plantel −2 |
| 18 | `hinchas` | va mal | Dar la cara: confianza +4, plantel +2 · *Esconderse*: confianza −4 |
| 19 | `juvenil_deslumbra` | edad ≤ 21 | Darle bola: progreso de desarrollo +, él +6 · *Calma*: nada |
| 20 | `mentor` | veterano ≥ 31 + joven ≤ 21 | Fomentarlo: progreso del joven +, veterano +4 · *Nada*: nada |
| 21 | `insulta_arbitro` | — | Apelar: 50% sin sanción, 50% sanción 2 · *Aceptar*: sanción 1 |

En cursiva, la opción por defecto. Los números son de partida y se calibran en el plan; los
montos de dinero son un % del sueldo del jugador o del ingreso por jornada.

### 3.3 Efectos

`eventos.aplicar(estado, efectos, protagonistas, rng) -> list[str]` entiende estas claves y
devuelve las líneas de lo que pasó (para la noticia y el resumen):

- `moral` (jugador) / `moral_plantel` — acotado a 0–100.
- `forma` — añade una nota a `notas_recientes` (alta o baja).
- `energia` — a uno o a N jugadores.
- `sancion` — "expulsión"/apartado: `sanciones.sumar_sancion(j, n, 'liga')`.
- `lesion` — `lesion_partidos += n`.
- `dinero` — `mi_equipo.balance` (+multa / −gasto).
- `confianza` — confianza de la directiva (0–100).
- `progreso` — `progreso_desarrollo`.
- `promesa` — compromisos con plazo (eventos 7 y 15), guardados en `datos_carrera['promesas']`
  y revisados en el sorteo de cada jornada.

### 3.4 Correo con decisión

- `eventos.sortear` envía el correo con `msg['evento'] = {'id', 'protagonistas': [ids],
  'opciones': [textos], 'resuelto': None}`. El remitente es `jugador` cuando escribe él (la riña:
  correo insultante del polémico, con humor y sin groserías fuertes) o `club` cuando informa la
  secretaría.
- `ui/correo_screen.py`: si el mensaje tiene `evento` sin resolver, dibuja 2–3 botones (uno por
  opción) en lugar del botón de acción; teclado ←/→ + Enter. Al elegir llama a
  `eventos.resolver(estado, msg_id, indice)`.
- `eventos.resolver`: aplica efectos, registra la noticia (§3.5), guarda en el mensaje
  `evento['resuelto'] = indice` y el resumen de una línea; los botones desaparecen.
- Sin responder: al cierre de la siguiente jornada de liga del user,
  `eventos.resolver_pendientes(estado)` aplica la opción por defecto. Si el protagonista ya no
  está en la plantilla, el evento se cierra sin efectos pero deja igual su noticia (§3.5, `opcion` = −1).

### 3.5 Registro de noticias (para la futura sección NOTICIAS)

`eventos.registrar_noticia(estado, titular, cuerpo, tipo='vestuario', jugadores=None)` añade a
`datos_carrera['noticias']` (lo más nuevo primero, tope 100):

```python
{'id': int, 'temporada': int, 'jornada': int, 'tipo': 'vestuario',
 'titular': str, 'cuerpo': str, 'jugadores': [ids], 'evento': 'rina', 'opcion': 0}
```

Cada opción del catálogo trae su plantilla de `noticia` (titular + cuerpo en tono de prensa, con
el nombre del jugador y del club). **Toda resolución de evento —elegida o por defecto— genera
exactamente una noticia.** Se guarda con la partida (va dentro de `datos_carrera`).

## 4. NOTIFICACIONES: mensajes y correo separados

"CORREO" pasa a llamarse **NOTIFICACIONES** y se divide en dos canales:

- **MENSAJES** — lo personal: lo que te escriben los jugadores y el presidente.
- **CORREO** — lo institucional del club: directiva, secretaría técnica, cuerpo médico, cantera,
  patrocinadores, prensa y otros clubes.

### 4.1 Clasificación

- `correo.canal(msg) -> 'mensaje' | 'correo'`: usa `msg['canal']` si existe; si no, lo deduce del
  remitente (`jugador` y `presidente` → `mensaje`; el resto → `correo`). Los saves viejos quedan
  clasificados solos, sin migración.
- Remitente nuevo **`presidente`** ("Presidente"): tono personal y directo, sin la plantilla
  formal de "Estimado míster… Atentamente"; firma con "El presidente". Pasan a `presidente` los
  correos personales que hoy salen como `directiva`: felicitación por el clásico, racha de tres
  victorias, advertencia por tres derrotas y los avisos/ultimátums personales de `directiva.py`.
  Lo formal (objetivos, veredicto de temporada, presupuesto, pedidos) sigue como `directiva` en
  CORREO. La lista exacta se fija en el plan revisando las 44 llamadas a `enviar`.
- Eventos (§3): los que escribe el jugador (riña, exige titular, nace su hijo…) van a MENSAJES;
  los que informa el club (lesión entrenando, gripe, escándalo…) van a CORREO. Los botones de
  decisión funcionan igual en los dos.
- `correo.no_leidos(estado, canal=None)` acepta filtro por canal.

### 4.2 Pantalla `notificaciones_screen` (nueva)

Dos paneles lado a lado, **MENSAJES a la izquierda y CORREO a la derecha**. Cada uno muestra:

- Título con el número de no leídos.
- **Vista previa de los últimos 5**: remitente · T/J, asunto (dorado si no está leído) y una
  línea del comienzo del texto. Los que esperan una decisión llevan la marca "DECISIÓN PENDIENTE".
- Botón **VER TODOS**.

Clic en un elemento (o Enter) abre la lista completa de ese canal con ese mensaje seleccionado;
VER TODOS abre la lista en el más reciente. Teclado: ←/→ cambia de panel, ↑/↓ elige, Enter abre,
Esc vuelve al hub.

### 4.3 Lista completa

Se reutiliza `correo_screen` con `estado['correo_canal']`: filtra la bandeja por canal, titula
"MENSAJES" o "CORREO" y Esc/VOLVER regresa a NOTIFICACIONES. Lectura, botón de acción, borrar y
los botones de decisión no cambian.

### 4.4 Accesos

- La tecla **M** abre NOTIFICACIONES (`main.py`).
- En el hub, OFICINA > "CORREO" pasa a "NOTIFICACIONES"; el número rojo y el sobre suman los no
  leídos de los dos canales; el aviso dice "N notificaciones sin leer".
- Los regresos que hoy vuelven a `correo_screen` (p. ej. tras negociar desde un correo) se
  mantienen: vuelven a la lista del canal de donde salieron.
- Ayuda (H) y barra de atajos de las dos pantallas.

## 4bis. Los menores de 21 progresan un poco más rápido

`desarrollo._factor_progreso_edad`: tramo nuevo **edad ≤ 20 → 0.90** (hoy 0.75, un 20% más de
progreso por partido). Los de 21 siguen en 0.75 y el resto no cambia. La curva pasiva por
temporada (`_delta_ovr_por_edad`) y el techo de potencial no se tocan: suben antes, no más alto.

## 5. Guardado y compatibilidad

- Campos nuevos con valor por defecto: `Jugador.renovacion_avisada`, `dt['nacionalidad']`,
  `msg['canal']`, `msg['evento']`,
  `datos_carrera['nac_reales' | 'ult_res' | 'eventos_vistos' | 'promesas' | 'noticias']`.
- Saves viejos cargan sin migración manual: nacionalidades se corrigen una vez (§1.2) y los
  correos existentes se reparten por remitente (§4.1).

## 6. Archivos

- **Nuevos:** `data/nacionalidades.py`, `eventos.py`, `ui/notificaciones_screen.py`,
  `tests/test_nacionalidades.py`, `tests/test_eventos.py`, `tests/test_notificaciones.py`.
- **Modificados:** `retiros.py`, `entrenadores.py`, `data/free_agents.py`, `models.py`,
  `salidas.py`, `negociacion.py`, `vestuario.py`, `desarrollo.py`, `ui/match_screen.py`, `directiva.py`, `correo.py`,
  `ui/correo_screen.py`, `ui/league_screen.py`, `ui/ayuda.py`, `ui/atajos.py`, `main.py`, las
  pantallas que muestran al DT, y la versión/`context.md`.

## 7. Pruebas

- Notificaciones: `canal` reparte bien por remitente y respeta `msg['canal']`; un save viejo queda
  repartido; `no_leidos` por canal; la vista previa da los 5 más recientes de cada lado; la lista
  filtrada no muestra el otro canal; M abre NOTIFICACIONES.

- Nacionalidades: toda clave de la tabla existe en los datos (sin claves huérfanas); muestras
  conocidas dan el país correcto; un nombre inventado conserva el país de su liga; un save viejo
  se corrige una sola vez; regen de nacionalidad sin lista de nombres toma el país de la liga.
- Renovación: avisa con las condiciones, no avisa dos veces, no avisa a cedidos ni a quien pide
  salir, +5 de moral al renovar tras el aviso.
- Eventos: probabilidad mayor cuando va mal; con polémico y mala racha la riña domina; no se
  repite en 6 jornadas; cada opción de los 21 eventos aplica sus efectos dentro de rangos válidos;
  el pendiente se resuelve por defecto; **cada resolución deja una noticia** con titular y cuerpo;
  el catálogo completo se recorre sin excepciones.
