# Cadena de DTs + editor ampliado (0.4.22.0) y Noticias (0.4.23.0) — diseño

**Fecha:** 2026-10-09 · **Líder:** sesión `lol` · **Ejecutan:** `lol` (~35 %) y `lol2` (~65 %)

## 1. Objetivo

- **Tarea 1 (0.4.22.0):** cuando un club de la IA se queda sin DT se produce una cadena realista de
  contrataciones entre clubes, con un banco de técnicos desempleados como respaldo. El editor permite
  editar DTs y jugadores completos y crear jugadores. Más nombres genéricos para que los regens no se repitan.
- **Tarea 2 (0.4.23.0):** sección de Noticias estilo FIFA alimentada por hechos reales de la partida, con
  feed en el hub, pantalla completa, carga de temporada con titulares, rumores 60/40, conferencias de
  prensa y logros del DT.

Solo modo carrera: todo el estado vive en `datos_carrera`; el editor sigue tocando únicamente la base
editada (`alpha_football_edited_db.json`), que se aplica a carreras **nuevas** y nunca a un guardado.

## 2. Lo que ya existe y se reutiliza

| Ya existe | Dónde | Qué se hace |
|---|---|---|
| Banco de DTs libres (20), DT por club, despidos de la IA, oferta de banquillo al user | `entrenadores.py`, `datos_carrera['dts']` | Se amplía; no se crea otro banco |
| Registro de noticias de eventos de vestuario (sin pantalla) | `eventos.registrar_noticia`, `datos_carrera['noticias']` | Pasa a ser un envoltorio del núcleo nuevo |
| Noticias que llegan como correo de "Prensa" | `mercado_ia` (quiebra, remate), `premios`, `cantera`, `temporadas` | Se mudan a Noticias y dejan de enviarse por correo (decisión de Diego) |
| Pantalla de carga por etapas | `ui/pantalla_carga.py`, `resumen_temporada_screen.avanzar_nueva_temporada` | Se le añaden los titulares |
| Pestañas LIGA/COPA del panel de tabla del hub | `ui/league_screen.py` (`hub_tabla_tab`) | Tercer valor `'noticias'` |
| Crear jugador libre y DT libre en el editor | `ui/edit_screen.py` (`_libres`, `_dts_libres`) | Se extiende a jugadores de club y a todos los campos |

## 3. Núcleo de noticias — `alpha_football/noticias.py` (lol)

Las noticias son **dicts** (como el correo y los DTs: van directo al JSON del guardado), no una clase.

```python
MAX_NOTICIAS = 50; JORNADAS_VIDA = 3; IMPORTANCIA_FEED = 3
TIPOS       # 'resultado','fichaje','dt_cambio','rumor','campeon','descenso','declaracion','lesion',
            # 'vestuario','premio','economia','cantera','promesa','record','logro','otro'
CATEGORIA   # tipo -> categoría de imagen (tabla de abajo)
ETIQUETA    # tipo -> "RESULTADO", "FICHAJE", "RUMOR", ...
COLOR       # categoria -> (r, g, b)   fondo cuando la categoría no tiene imágenes
imagen(noticia) -> Optional[str]      # ruta de la imagen que le toca (estable por id), o None

lista(estado) -> list                 # todas, lo más nuevo primero (normaliza las de saves viejos)
publicar(estado, tipo, titular, cuerpo, importancia=3, categoria=None,
         equipos=(), jugadores=(), dts=(), **extra) -> dict
activas(estado) -> list               # orden: importancia desc, luego más recientes
para_feed(estado) -> list             # activas con importancia >= IMPORTANCIA_FEED
ultimas(estado, n=10) -> list         # para la pantalla de carga
no_leidas(estado) -> int
marcar_leida(estado, noticia_id) -> None
purgar(estado) -> int                 # borra las de JORNADAS_VIDA o más jornadas de antigüedad
cierre_jornada(estado) -> None        # purga + noticias_gen.generar_jornada + rumores.revisar_jornada
```

Campos de cada noticia: `id` (int), `tipo`, `categoria`, `titular` (≤ 60 caracteres, se recorta con "…"),
`cuerpo`, `temporada`, `jornada`, `importancia` (1-5), `equipos_ids`, `jugadores_ids`, `dt_ids`, `leida`,
`fecha_creacion` (fecha del calendario del juego si hay reloj) y los `extra` que pase quien publica.
`temporada=` y `jornada=` explícitos pisan a los actuales (el cierre de temporada publica campeones y descensos
de la temporada que termina cuando el contador ya subió). `accion={'pantalla', 'texto'}` añade un botón en la
pantalla Noticias (p. ej. "VER BUSCADOR" en un remate), igual que las acciones del correo.

**Categorías e imágenes.** Diego deja las imágenes en `alpha_football/assets/noticias/` con el nombre
`<categoria><n>.jpg` (`fichaje1.jpg`, `fichaje2.jpg`…), verticales 9:16 (720 × 1280 recomendado, el titular va
sobre un degradado oscuro en el tercio inferior). Cada noticia usa siempre la misma imagen de su categoría
(elegida por su id); sin imágenes, el color de la categoría. Las 16 categorías:

| Categoría | Noticias | Categoría | Noticias |
|---|---|---|---|
| `resultado` | goleadas, sorpresas, clásicos | `vestuario` | eventos de vestuario, polémicos, filtraciones |
| `fichaje` | traspasos confirmados | `premio` | Balón de Oro, candidatos, equipo del año |
| `rumor` | rumores y desmentidos | `promesa` | jóvenes promesas, joyas de cantera |
| `entrenador` | despidos y fichajes de DT | `record` | récords de goles y asistencias |
| `titulo` | campeones de liga y copa | `logro` | hitos del DT |
| `ascenso` | ascensos | `economia` | quiebras, remates, sanciones |
| `descenso` | descensos | `general` | todo lo demás |
| `lesion` | lesiones graves | `prensa` | declaraciones y conferencias |

- Antigüedad = `(temporada_actual − temporada) × num_jornadas + (jornada_actual − jornada)`: así las de la
  última jornada siguen vivas al empezar la temporada siguiente y están disponibles para la pantalla de carga.
- `cierre_jornada` se engancha **una sola vez** en el bloque de cierre de jornada de `ui/match_screen.py`
  (lo pone lol). Cada generador va en su `try` propio: uno que falla se registra y los demás siguen.
- `eventos.registrar_noticia` queda como envoltorio de `publicar` (tipo `'vestuario'`, conserva `evento`,
  `opcion` y la clave `jugadores`), así se cumple el pedido de que las consecuencias de los eventos salgan en Noticias.
- Las noticias se publican **después** del hecho real; nunca se inventan resultados. El segundo entrenador no las comenta.

## 4. Cadena de DTs y banco — `entrenadores.py` (lol)

- **DT:** se añaden `edad` y `ex_jugador`. Prestigio = etiqueta derivada de la calificación:
  bajo < 50, medio 50-69, alto ≥ 70 (`prestigio(dt)`).
- **Vacante** (despido en jornada, despido de cierre de temporada o DT que se fue por la cadena) →
  `cubrir_vacante`:
  1. Si la vacante entra en la banda del user y no tiene otra oferta, con la probabilidad actual el club
     pone interino y le ofrece el banquillo (ya existe; ahora vale para **toda** vacante, no solo despidos).
  2. Si no, intenta **robar** un DT: candidatos = DTs de clubes de la IA de menor nivel (media del club
     inferior, o división inferior), con mejor calificación que el mejor libre que el club puede pagar, no
     interinos y que no se hayan movido en esta jornada. Prioridad: misma liga → mismo país → mismo
     continente; a igualdad, el de estilo igual al del DT saliente (identidad del club). Hasta 3 candidatos,
     cada uno acepta con 60 %. El sueldo se renegocia al alza y el club debe poder pagarlo (`puede_pagar`).
  3. Si lo consigue, el club de origen queda vacante y repite el proceso.
  4. Si no, contrata del banco (`mejor_libre`, como hoy).
- **Límites:** máximo 4 movimientos de cadena por jornada (contador común a todas las ligas); un DT se mueve
  una sola vez por jornada; ningún club termina la jornada sin DT (agotado el cupo, la vacante va directo al banco).
- **Banco:** el despedido entra con calificación −10 (ya existe). Se añaden parodias de técnicos reales sin
  club (`DT_LIBRES_REALES` en `data/entrenadores.py`, una vez por carrera, también en saves viejos). Si el banco
  baja de 8 se rellena hasta 20 con técnicos de nivel medio-bajo; tope de 40 (salen los de peor calificación).
- **Retirados:** `retirados_a_banco(estado, retiros, azar)` desde `retiros.procesar_retiros`: cada retirado con
  OVR ≥ 81 tiene 20 % de entrar al banco con su nombre, nacionalidad y edad, calificación de novato
  (45-65 según su OVR) y estilo según su posición.
- **Noticias** (`dt_cambio`, importancia 4): "El {club} despide a {DT}", "{DT} firma por el {club}",
  "{jugador} se convierte en entrenador". Reemplazan al correo "Cambio de DT". Los cambios en 2ª división de
  otros países salen con importancia 2 (se ven en la pantalla Noticias, no en el feed) para no saturar.
- Más nombres y apellidos genéricos de DT (hoy 20 × 20).

## 5. Mercado: noticias de fichajes y rumores (lol)

- **Fichajes:** noticia al concretarse un traspaso relevante (IA↔IA o del user), desde el único punto por el que
  pasan todos (`negociacion.registrar_pase`). Los del user se publican siempre: media ≥ 85 → importancia 5,
  ≥ 80 → 4, resto → 3. Entre clubes de la IA (una sola ronda de pretemporada mueve ~370 jugadores) hay un tope
  de **4 por jornada**: se publican desde media 80 (76 si participa un club de tu liga), con importancia
  ≥ 90 → 5, ≥ 85 → 4, resto → 3, y quedan los 4 de mayor puntaje (media + 3 si participa un club de tu liga);
  uno mejor reemplaza al más flojo de esa jornada. Las confirmaciones de rumores no cuentan para el tope.
  Quiebras y remates pasan de correo a noticia.
- **Cierre del otro continente** (`temporadas.py`, lol): noticia del campeón de copa y resumen de campeones,
  ascensos y descensos. El cierre de la temporada del user lo publica lol2 (sección 7).
- **Rumores — `alpha_football/rumores.py`**, estado en `datos_carrera['rumores']`:
  - Con el mercado abierto, cada jornada puede nacer un rumor (máximo 2 vivos), tipo `'rumor'`, importancia 2-4.
    Se guarda `real` (60 %) y un plazo de 1-3 jornadas de mercado.
  - Entre clubes de la IA: si es real y al vencer sigue siendo viable (el jugador sigue en su club, el
    comprador puede pagarlo, cupos de plantilla), el traspaso **se ejecuta** y sale la noticia de confirmación.
  - Sobre un jugador del user: si es real, al vencer llega la **oferta formal** por el cauce normal.
  - Humo, o real que dejó de ser viable: 50 % noticia de desmentido ("negó el rumor"), 50 % desaparece.
  - Si el mercado cierra con rumores vivos, se resuelven como humo.

## 6. Interfaz de noticias (lol2)

- **Feed del hub** (`ui/league_screen.py`): `hub_tabla_tab = 'noticias'` como tercer modo del panel de tabla
  (`R_TABLA`, 640 × 400). La pestaña NOTICIAS va a la izquierda de LIGA y COPA, que no se mueven. Tecla **N**
  alterna noticias ↔ la pestaña anterior (`hub_tabla_prev`) con fundido de ~180 ms. Tarjeta 9:16 de 198 × 352
  (bajo la fila de pestañas), centrada, fondo del color de su categoría, etiqueta del tipo y titular en fuente
  mediana (hasta 5 líneas); a los lados, la anterior y la siguiente atenuadas. Una noticia a la vez, rota cada
  5 s (`get_ticks`), solo importancia ≥ 3, orden de `para_feed`. Clic → pantalla Noticias. Superficies
  cacheadas por id: sin trabajo por cuadro. El texto de atajos del hub se recorta para que quepa "N Noticias".
- **Pantalla Noticias** (`ui/noticias_screen.py`): lista a la izquierda (orden de `activas`), detalle a la
  derecha (titular, cuerpo, "Temporada X – Jornada Y"). Flechas o clic; al abrir una se marca leída.
  Tarjeta NOTICIAS en OFICINA (segunda, tras NOTIFICACIONES) con el contador de no leídas; OFICINA ya tiene
  8 tarjetas y no cabe una novena en 2 columnas, así que con más de 8 pasa a 3 columnas. Registro en `main.py`,
  `ui/ayuda.py`, `ui/atajos.py` y actualización de los tests que fijan las 8 tarjetas de OFICINA.
- **Carga de temporada** (`ui/pantalla_carga.py` + `resumen_temporada_screen.py`): la carga muestra las
  últimas 8-10 noticias con fundido cada 3-4 s y los textos de estado por etapa ("Cerrando temporada…",
  "Actualizando clasificaciones y descensos…", "Procesando mercado de pases…", "Generando agentes libres…",
  "Preparando nueva temporada…"). Los pasos largos bloquean sin redibujar, así que los titulares se animan
  sobre todo en la espera final: `cerrar()` recibe un mínimo de 3 s solo para el cambio de temporada (0 en
  tests; guardar y cargar conservan su mínimo actual).

## 7. Generadores de noticias — `alpha_football/noticias_gen.py` (lol2)

`generar_jornada(estado)` (lo llama el núcleo) y `generar_cierre_temporada(estado, ...)`:

| Noticia | Tipo · importancia | Cuándo |
|---|---|---|
| Goleada, sorpresa o clásico de tu liga | resultado · 3-5 | cada jornada |
| Resultado impactante de otras ligas (solo lo más destacado) | resultado · 4-5 | cada jornada |
| Lesión grave de una figura | lesion · 3-4 | al ocurrir |
| Campeón de liga o copa | campeon · 5 | cierre de temporada / de continente |
| Ascensos y descensos | descenso · 5 | cierre de temporada / de continente |
| Jóvenes promesas que apuntan a romper (≤ 21 años, mucho potencial, poca media) | promesa · 3 | cada ~6 jornadas |
| Candidatos al Balón de Oro | premio · 4 | mitad de temporada y antes de la gala |
| Equipo del año | premio · 4 | cierre de temporada |
| Jugador cerca de romper el récord de goles o asistencias | record · 4 | cuando queda a ≤ 3 del récord |
| Polémico con moral baja filtra a la prensa (−1 de moral al plantel) | vestuario · 3 | probabilidad por jornada |

Los récords se guardan en `datos_carrera['records']`.

## 8. Conferencias de prensa — `alpha_football/prensa.py` + UI (lol2)

- Se **ofrece** (opcional, nunca obligatoria) en partidos importantes: clásico, partido de título, siendo
  líder o estando en zona de descenso, semifinal o final de copa. Máximo una por partido.
- Es un **overlay**, no una pantalla: antes del partido sobre el prepartido (preguntas sobre el rival y la
  previa) y después sobre el postpartido (preguntas sobre el resultado), con botón SALTAR. La lógica vive en
  `prensa.py` (`evaluar`, `preguntas`, `responder`) y el dibujo en `ui/prensa_overlay.py`, que llaman
  `ui/prepartido_screen.py` y la vista de postpartido.
- Tensión del tono agresivo: `factor_tarjetas` en `partido_ctx.EstadoPartido`, que ensancha solo el tramo de
  tarjetas del sorteo de incidencias de `engine.py`; vale para el siguiente partido del user y se guarda en
  `datos_carrera['prensa_tension']`.
- La moral se aplica como delta directo al jugador y se anota en `causas_moral` para que el vestuario la explique.
- Banco de preguntas por situación; cada pregunta trae 4 respuestas, una por tono:
  **Motivador** (+moral propia) · **Provocador** (−moral del rival, noticia de importancia 4) ·
  **Humilde** (neutro o +1 de moral) · **Agresivo** (más tarjetas en el próximo partido, para los dos equipos).
- Los DTs rivales también declaran antes de partidos grandes (−moral de tu plantel).
- Toda declaración publica una noticia `'declaracion'`.

## 9. Logros del DT — `alpha_football/logros.py` + overlay en `ui/career_screen.py` (lol2)

Lista inicial: primer título de liga, primera final continental, 50 / 100 / 200 partidos dirigidos, racha de
8+ victorias, salvarse en la última jornada, ganar 3 clásicos seguidos, fichar un jugador de media ≥ 84.
Estado en `datos_carrera['logros']`. Cada logro desbloqueado publica una noticia `'logro'` de importancia 5.
`logros.revisar` se llama desde `noticias_gen.generar_jornada` y desde el cierre de temporada; el fichaje de
media ≥ 84 se detecta revisando la plantilla, sin enganchar el mercado.
Overlay con scroll: obtenidos (con temporada y jornada) y pendientes (atenuados, con su descripción).

## 10. Editor — `ui/edit_screen.py` (lol2)

- **DT:** nombre, estilo, calificación (muestra el prestigio), nacionalidad, edad. **Quitar** el DT de un club
  lo manda a `_dts_libres`; **asignar** trae uno de `_dts_libres` al club (el anterior pasa a libres).
  Contrato con la carrera (lo lee `entrenadores.asegurar_dts`, lol): club → `dt_nombre`, `dt_estilo`,
  `dt_calif`, `dt_nacionalidad`, `dt_edad`, `dt_sin` (club sin DT: arranca con uno generado);
  `_dts_libres` → `nombre`, `estilo`, `calif`, `nacionalidad`, `edad`.
- **Jugador (segunda página del formulario):** ataque, defensa, físico, técnica y mental por separado (el campo
  OVR queda como atajo "todos iguales"), penales, resistencia, potencial, edad, posición, rasgo, personalidad,
  nacionalidad, moral, energía, salario, años de contrato y cláusula. El valor de mercado no se edita: el juego
  lo recalcula siempre a partir de los atributos, la edad y el potencial.
- **Crear jugador:** botón para crearlo en un club (respeta el máximo de plantilla) o como agente libre, con el formulario completo.
- **Fuera de alcance:** "posiciones que puede jugar" y "rol preferido" no existen en el modelo ni en el motor
  (cada jugador tiene una sola posición); añadirlos es una mecánica de partido nueva, no un campo del editor.

## 11. Nombres genéricos (lol2)

`alpha_football/data/nombres_genericos.py`: ≥ 100 nombres y ≥ 100 apellidos por país para los 8 países
(hoy 20 × 22 y solo 5 países; un regen uruguayo sale con nombre español). `retiros.NOMBRES_POR_PAIS` lo importa.

## 12. Reparto y archivos

| Sesión | Archivos |
|---|---|
| **lol** | `noticias.py` (nuevo), `rumores.py` (nuevo), `entrenadores.py`, `data/entrenadores.py`, `eventos.py` (solo `registrar_noticia`), `mercado_ia.py`, `negociacion.py` (solo `registrar_pase`), `premios.py`, `cantera.py`, `temporadas.py` (correos de Prensa → noticia), `retiros.py` (solo `procesar_retiros`), `ui/match_screen.py` (solo el bloque de cierre de jornada), `__init__.py`, `README.md`, cabecera de `context.md` |
| **lol2** | `noticias_gen.py`, `prensa.py`, `logros.py`, `data/nombres_genericos.py`, `ui/noticias_screen.py`, `ui/prensa_overlay.py` (nuevos); `ui/league_screen.py`, `ui/pantalla_carga.py`, `ui/resumen_temporada_screen.py`, `ui/career_screen.py`, `ui/edit_screen.py`, `ui/prepartido_screen.py`, `ui/postpartido.py`, `ui/match_screen.py` (solo la vista de postpartido y la creación del ctx), `main.py`, `ui/ayuda.py`, `ui/atajos.py`, `models.py` (campos `dt_*` de `Equipo`), `retiros.py` (solo `NOMBRES_POR_PAIS`), `partido_ctx.py` y `engine.py` (solo `factor_tarjetas`), y los tests viejos que fijan las tarjetas de OFICINA y el texto de atajos |

Reglas: lista de archivos antes de empezar; `Edit` puntual (nunca `Write`) en archivos existentes; avisar antes y
después de tocar un archivo del otro o uno compartido; tests propios en archivos nuevos; sin commits, stash,
checkout ni reset; cada uno escribe su sección de bitácora y lol integra versiones y corre la suite completa.

## 13. Orden

1. **lol:** núcleo `noticias.py` con tests → avisa "contrato listo". **lol2** en paralelo: nombres genéricos y editor.
2. **lol:** cadena de DTs y banco. **lol2:** pantalla Noticias, feed del hub, tarjeta de OFICINA.
3. **lol:** Prensa → Noticias, noticias de fichajes, rumores. **lol2:** generadores, carga de temporada, conferencias, logros.
4. **lol:** integración, suite completa, versiones 0.4.22.0 y 0.4.23.0, README y `context.md`.

## 14. Pruebas

Cada módulo nuevo con su archivo de tests (lógica pura con `estado` mínimo y `random.Random` con semilla):
caducidad y tope de noticias; saves viejos; cadena (tope de 4, un movimiento por DT, ningún club sin DT, el user
nunca es robado); retirados 20 %; rumores (reales se ejecutan, humo no, cierre de mercado); efectos de cada tono;
cada logro; registro de la pantalla nueva. La suite completa debe quedar en verde antes de subir las versiones.
