# Cantera — diseño

**Fecha:** 2026-10-04
**Estado:** aprobado en conversación, pendiente de revisión del spec

## Objetivo

Dar a cada club una cantera de juveniles. El usuario la ve en **Dirección de equipo → CANTERA**,
aparte de la plantilla. Se renueva cada 6 meses (dos veces por temporada): llegan nuevos, algunos
se van, los que se quedan mejoran, y llega un correo con el resumen. De vez en cuando sale una
**joya** con media cercana a la del once titular. Los clubes de la IA también sacan canteranos,
pero en menor medida y con joyas muy raras.

## Fuera de alcance

- Vender o ceder canteranos directamente desde la cantera (para eso se suben primero).
- Entrenamiento, instalaciones o inversión en cantera.
- Lista de cantera guardada para los clubes de la IA.
- Cambios en los regens por retiro (`retiros.generar_regen`) y en los juveniles de relleno
  (`finanzas.generar_reemplazo`): quedan como están.

## 1. Módulo `alpha_football/cantera.py` (nuevo)

Lógica pura, sin pygame. Constantes al inicio del archivo para poder ajustarlas.

### Datos

- La cantera del usuario es una lista de `Jugador` en `datos_carrera['cantera']`, serializada igual
  que los jugadores de la plantilla. Se guarda con la partida y pertenece al club, no al DT: si el usuario
  cambia de club, la cantera se regenera para el club nuevo.
- Los canteranos no cobran sueldo, no cuentan para la masa salarial ni el tope, no se lesionan y
  no aparecen en el buscador ni en el mercado.
- `cantera(estado) -> list`: devuelve la lista y la crea si no existe (partidas viejas y carreras
  nuevas pasan por el mismo camino). La generación inicial trae `TAMANO_INICIAL = 8`.

### Generación de un canterano

| Campo | Normal | Joya |
|---|---|---|
| Edad | 15–18 | 16–18 |
| Media | media del once − (18 a 28), mínimo 40 | media del once − (0 a 4) |
| Potencial | media + (8 a 20), tope 99 | media + (5 a 12), tope 99 |

- "Media del once" = la media del mejor once del club (la misma que ya calcula `league_screen`
  para no dejar que los juveniles la bajen; se mueve a un sitio reutilizable si hace falta).
- Posición al azar con pesos POR 1, DEF 3, MED 3, DEL 2.
- Nacionalidad: la del país de la liga del club. Nombre con `nombres.nombre_unico` y `reservar`.
- Atributos repartidos con `retiros._atributos_para(posicion, ovr, rng)`.
- La joya lleva la marca `joya=True` en su registro de cantera (solo para destacarla en pantalla
  y correo; al subir es un jugador normal).

### Renovación (cada 6 meses)

`renovar(estado, rng=None) -> dict` con `{'llegan': [...], 'se_van': [...], 'mejoran': [...], 'joya': Jugador|None}`.
En orden:

1. **Crecen:** cada canterano sube +1 a +4 de media sin pasar su potencial (los atributos suben
   en proporción).
2. **Cumplen años:** solo en la renovación de inicio de temporada (+1).
3. **Se van:** todos los que tengan 20 años o más, y del resto cada uno con probabilidad
   `25%` ajustada por potencial (potencial alto → 10%, bajo → 40%). La joya no se va por azar,
   solo por edad.
4. **Llegan:** 2 a 4 nuevos. Con probabilidad `PROB_JOYA_USER = 0.08` uno de ellos es joya
   (máximo una por renovación).
5. **Tope:** si quedan más de `TAMANO_MAX = 12`, se van los de menor potencial hasta 12 (nunca
   la joya recién llegada). Si quedan menos de `TAMANO_MIN = 6`, llegan más hasta 6.

### Cuándo se dispara

`revisar_jornada(estado)` se llama desde `match_screen.finalizar_jornada_liga`, en su propio
`try/except` como los demás hitos. Renueva cuando la jornada recién cerrada deja a la liga en:

- **jornada 1** de la temporada (inicio), y
- **jornada `num_jornadas // 2`** (mitad), haya o no ventana de invierno en esa liga.

Para no repetir, guarda `datos_carrera['cantera_ultima'] = "<temporada>-inicio|mitad"`.

### Acciones del usuario

- `subir(estado, jugador) -> (ok, mensaje)`: lo saca de la cantera y lo agrega a
  `mi_equipo.jugadores` con `finanzas.contrato_inicial` (mínimo 2 años). Falla con mensaje si la
  plantilla ya tiene `market.PLANTILLA_MAXIMA`. Se puede subir en cualquier jornada, no depende
  de la ventana de mercado.
- `liberar(estado, jugador)`: lo quita de la cantera (su nombre queda reservado: `nombres.py` no
  tiene forma de devolverlo y no hace falta).

## 2. Correo

Un correo por renovación, remitente nuevo `'cantera'` → "Cantera" en `correo.REMITENTES`, firma
"Coordinación de cantera de {club}" en `correo.FIRMAS`, acción `accion('cantera_screen', "VER CANTERA")`.

- Asunto normal: "Informe de cantera: N altas, M bajas".
- Asunto con joya: "Una joya en la cantera: {nombre}".
- Cuerpo: quién llega (posición, edad, media), quién se va y por qué (edad / no renovó), quiénes
  mejoraron más. Si hay joya, un párrafo aparte que diga que está casi al nivel del primer equipo.

## 3. Pantalla `ui/cantera_screen.py` (nueva) y hub

- Tarjeta nueva en `league_screen.TARJETAS['direccion']`:
  `("CANTERA", "Juveniles del club: súbelos o libéralos", 'cantera_screen')`.
- Lista ordenada por media: posición, nombre, edad, media, potencial, y una marca dorada para la
  joya. Navegación con teclado y ratón como `plantilla_screen`.
- Al elegir uno: ver ficha (`ficha_jugador`), **SUBIR AL PRIMER EQUIPO** y **LIBERAR** (este con
  confirmación). Tras la acción, mensaje breve y la lista se actualiza.
- Texto al pie con cuándo es la próxima renovación ("Próximo informe: jornada X").
- Registro de la pantalla en el enrutador de pantallas y entrada en `ui/ayuda.py`.

## 4. Clubes de la IA (menor medida)

Sin lista guardada. En cada renovación, `renovar_ia(estado, rng)` recorre todos los clubes que no
son el del usuario, en todas las ligas vivas:

- `PROB_CANTERANO_IA = 0.15`: el club sube un canterano normal directo a su plantilla, con
  contrato inicial.
- `PROB_JOYA_IA = 0.01`: en vez del normal, sube una joya. Muy raro: con ~400 clubes y dos
  renovaciones por temporada son unas pocas en todo el mundo por temporada, casi nunca en la
  liga del usuario.
- Si el club está en `mercado_ia.PLANTILLA_MAX_IA`, el canterano reemplaza al suplente de peor
  media; si no cabe ni así, no sube.
- Las joyas de la IA de la liga del usuario salen como noticia en el correo (remitente `'prensa'`),
  una línea, sin acción.

## 5. Efectos colaterales (sin tocar código)

- Subir un canterano de 21 o menos cumple el objetivo de directiva `fichar_joven`, y sus partidos
  suman al de `partidos_u21`: ambos ya cuentan por id de jugador nuevo / por edad.
- El canterano subido entra al desarrollo normal (`desarrollo.py`) como cualquier joven.

## 6. Manejo de errores

- Todo punto de entrada (`revisar_jornada`, `subir`, `liberar`, carga de partida vieja) con
  `try/except` y `logger.error`, como el resto del cierre de jornada: un fallo en la cantera no
  puede romper la jornada ni el guardado.
- Cantera ausente o corrupta en el guardado → se regenera.

## 7. Tests (`tests/test_cantera.py`)

- Generación: tamaños, rangos de edad/media/potencial respecto a la media del once.
- Renovación con semilla: crecen sin pasar el potencial, se van los de 20+, llegan 2–4, se
  respetan los topes 6–12, no se repite en la misma mitad de temporada.
- Joya: forzada con `rng` falso → media dentro de 0–4 del once; máximo una; no se va por azar.
- `subir`: entra a la plantilla con contrato, sale de la cantera, falla con plantilla llena.
- `liberar`: sale de la cantera.
- IA: con probabilidades forzadas sube uno; respeta `PLANTILLA_MAX_IA`; no toca al club del usuario.
- Correo: uno por renovación, asunto de joya cuando corresponde.
- Guardado: ida y vuelta conserva la cantera; partida sin cantera la genera al cargar.

## Versión

v4.8.0. Actualizar `context.md` y la ayuda al terminar.
