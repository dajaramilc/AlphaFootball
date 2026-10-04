# Patrocinios — diseño

**Fecha:** 2026-10-04
**Estado:** diseño conversado, pendiente de revisión del spec

## Objetivo

Reemplazar el patrocinio plano (un ingreso fijo por jornada) por hasta **3 contratos de patrocinio**
con marcas parodia de las reales. Cada contrato tiene años, un fijo, un bono y un objetivo. Al
vencer llegan ofertas; si cumpliste el objetivo, la marca ofrece renovar por más dinero, o puedes
cambiar de marca. Un club puede quedarse sin patrocinador si rechaza las ofertas o, casi imposible,
si nadie lo quiere. Los ingresos del club pasan a depender más de los patrocinios.

## Fuera de alcance

- Contratos de patrocinio simulados para los clubes de la IA: siguen con su ingreso de fórmula.
- Patrocinios de jugadores individuales, merchandising o derechos de TV.
- Logos o imágenes de marca: solo nombre y rubro en texto.

## 1. Peso del patrocinio en los ingresos

Hoy (`finanzas.py`): `PATROCINIO_FRAC = 0.40` y `TAQUILLA_FRAC = 0.50` de `base_ingresos`.

Cambia a `PATROCINIO_FRAC = 0.55` y `TAQUILLA_FRAC = 0.35`. La suma sigue en 0.90, así que
`ingresos_esperados` (base del tope salarial y de la IA) **no cambia** y el balance general del
juego se mantiene; lo que cambia es que el patrocinio pasa de ser el 44% al 61% del ingreso
recurrente. Con los tres espacios firmados a valor de referencia el club cobra lo mismo que antes
en total; sin patrocinadores pierde ese 61%.

`finanzas.procesar_jornada` deja de calcular el patrocinio con la fórmula para el club del
usuario y cobra `patrocinios.cobro_jornada(estado)`. La taquilla usa la nueva fracción.

## 2. Módulo `alpha_football/patrocinios.py` (nuevo)

Lógica pura. Estado en `datos_carrera['patrocinios']`:

```
{'club': <nombre del club>, 'reputacion': 50,
 'contratos': {'camiseta': {...}|None, 'manga': {...}|None, 'estadio': {...}|None},
 'ofertas': [ {...}, ... ],
 'ultimo_cierre': <temporada ya evaluada>, 'ultima_ventana': '<temporada>-<inicio|invierno>'}
```

### Espacios

| Espacio | Peso |
|---|---|
| `camiseta` | 50% |
| `manga` | 30% |
| `estadio` | 20% |

**Valor de referencia** de un espacio = `base_ingresos(club) × PATROCINIO_FRAC × peso`.

### Marcas

Catálogo fijo de ~28 marcas parodia en el módulo, 4 por rubro, en 7 rubros: aerolínea, ropa
deportiva, bebidas, tecnología, apuestas, banca, autos. Ejemplos: "Fly Emirados", "Qatar
Airguais", "Adibas", "Naik", "Pumba", "Coca-Kola", "Pepsy", "Red Bul", "Sansumg", "Spotifai",
"Bet366", "Santénder", "Mastercar", "Chevrolé". Cada marca tiene un perfil fijo.

### Contrato

```
{'marca', 'rubro', 'espacio', 'perfil', 'fijo': <anual>, 'bono': <por temporada>,
 'objetivo': {'tipo', 'meta', 'texto'}, 'anios': <restantes>, 'cumplido_ultima': bool|None}
```

### Perfiles

| Perfil | Fijo (× valor de referencia) | Bono (× valor de referencia) | Dificultad del objetivo |
|---|---|---|---|
| `conservadora` | 1.00 | 0.10 | fácil |
| `equilibrada` | 0.90 | 0.25 | media |
| `ambiciosa` | 0.75 | 0.50 | difícil |

### Objetivos

Se fijan al firmar según el club y la dificultad, y valen para cada temporada del contrato.

| Tipo | Cómo se mide | Fácil / media / difícil |
|---|---|---|
| `posicion` | Posición final en liga ≤ meta | puesto esperado +3 / puesto esperado / puesto esperado −3 (mínimo 1) |
| `copa` | Fase alcanzada en la copa internacional | jugarla / pasar la primera fase / llegar a semifinales. Solo se ofrece si el club juega copa esa temporada. |
| `goles` | Goles a favor en liga ≥ meta | 1.2 / 1.5 / 1.9 por jornada |
| `local` | Victorias de local en liga ≥ meta | 40% / 55% / 70% de los partidos de local |
| `u21` | Partidos sumados por menores de 21 ≥ meta | 10 / 25 / 45 (escalado a ligas de 22 jornadas) |

"Puesto esperado" = el puesto del club al ordenar la liga por `market.nivel_club`.
`progreso(estado, contrato) -> float 0..1` para la barra de la pantalla.

### Cobro

- `cobro_jornada(estado) -> int`: suma de `fijo // num_jornadas` de los contratos vigentes.
- Bonos y primas se suman al saldo y al libro bajo la misma clave `'patrocinio'`.

### Contratos iniciales

`asegurar(estado)`: si no hay estado de patrocinios o es de otro club (cambio de club, partida
vieja, carrera nueva), genera los 3 contratos del club actual: marcas de rubros distintos, perfil
de la marca, **años restantes al azar entre 1 y 3** y reputación 50. Así los iniciales también
tienen objetivo y vencimiento, y no vencen todos a la vez.

## 3. Cierre de temporada

`cierre_temporada(estado)` (llamado desde `finanzas.cierre_temporada`, una vez por temporada):

1. Por cada contrato vigente: evalúa su objetivo. Cumplido → paga el bono, reputación +6,
   `cumplido_ultima = True`. Fallado → sin bono, reputación −5, `cumplido_ultima = False`.
2. Reputación por resultado deportivo: título de liga o ascenso +8; descenso −10; cierre en
   quiebra (los "números rojos" que ya detecta `finanzas`) −15. Siempre acotada a 0–100.
3. Cláusula de división en los contratos que siguen vigentes: descenso → fijo y bono ×0.60;
   ascenso → ×1.30.
4. `anios -= 1`. Los que llegan a 0 vencen: el espacio queda vacío y se generan sus ofertas.
5. Un correo de resumen (objetivos cumplidos/fallados, bonos cobrados, contratos vencidos).

## 4. Ofertas

`generar_ofertas(estado, espacio, rng)` para cada espacio vacío:

- **Renovación:** solo si el contrato que acaba de vencer tenía `cumplido_ultima = True`. Misma
  marca, mismo perfil, fijo +10% a +20% sobre el fijo anterior, objetivo recalculado.
- **Marcas nuevas:** 2 ofertas de marcas cuyo rubro no esté ya en otro espacio vigente
  (exclusividad) ni repetido entre las ofertas del mismo espacio.
- Valor de cada oferta = valor de referencia × factores del perfil × **multiplicador de
  reputación** (lineal: reputación 0 → ×0.80, 50 → ×1.00, 100 → ×1.30) × variación al azar ±5%.
- Años: 1 a 3 al azar.
- **Sin interesados (casi imposible):** con reputación por debajo de 15, cada marca nueva tiene
  50% de no presentarse; puede que un espacio no reciba ninguna oferta. Con reputación 15 o más
  siempre llegan las 2.
- Las ofertas vencen al cerrar la ventana de mercado en la que llegaron.

**Cuándo llegan:** al cierre de temporada (para la ventana de inicio) y, para los espacios que
sigan vacíos, al abrir la ventana de invierno, con valor ×0.85. `revisar_jornada(estado)` se
llama desde `match_screen.finalizar_jornada_liga` y controla la apertura de invierno y el
vencimiento de ofertas, guardando `ultima_ventana` para no repetir.

**Quedarse sin patrocinador:** si el usuario rechaza todas las ofertas de un espacio, o no llega
ninguna, el espacio queda vacío y no cobra hasta la próxima ventana. Con los tres vacíos el club
no cobra patrocinio. Al quedar un espacio vacío con el mercado cerrado se envía un correo de aviso.

## 5. Acciones del usuario

- `firmar(estado, oferta_id, con_prima=False) -> (ok, mensaje)`: crea el contrato y descarta las
  demás ofertas de ese espacio. Con `con_prima=True`: cobra al contado el 30% de un año de fijo
  y el fijo queda ×0.88 durante todo el contrato.
- `rechazar(estado, oferta_id)`: descarta esa oferta.
- `negociar(estado, oferta_id, nivel, rng=None) -> (ok, mensaje)`: una sola vez por oferta.
  `nivel` 1 pide +10% de fijo (60% de éxito), `nivel` 2 pide +20% (30%). La probabilidad se ajusta
  con la reputación: +0.3 puntos porcentuales por cada punto sobre 50 y −0.3 por cada punto por
  debajo, acotada a 5%–90%. Si falla, la marca retira la oferta.
- `rescindir(estado, espacio) -> (ok, mensaje)`: multa = 50% del fijo que le queda al contrato
  (lo que falta de esta temporada más las temporadas restantes), reputación −8. El espacio queda
  vacío y recibe ofertas en la próxima ventana (si el mercado está abierto, de inmediato). No se
  permite si el saldo no alcanza para la multa.

## 6. Pantalla `ui/patrocinios_screen.py` (nueva)

- Tarjeta nueva en `league_screen.TARJETAS['finanzas']`:
  `("PATROCINIOS", "Marcas, objetivos y ofertas", 'patrocinios_screen')`.
- Arriba: reputación comercial (barra 0–100) e ingreso anual por patrocinios.
- Tres paneles, uno por espacio: marca, rubro, perfil, fijo anual, bono, objetivo con barra de
  progreso, años restantes y botón RESCINDIR (con confirmación y la multa a la vista). Espacio
  vacío: "Sin patrocinador" y cuánto se deja de cobrar por jornada.
- Abajo, las ofertas del espacio elegido: marca, fijo, bono, objetivo, años, y botones FIRMAR,
  FIRMAR CON PRIMA, NEGOCIAR +10% / +20% y RECHAZAR.
- Teclado y ratón, entrada en `ui/ayuda.py`, `ui/atajos.py` y `main.MODULOS_PANTALLA`.
- `finanzas_screen` sigue mostrando la línea "Patrocinio" del libro; su estimado por jornada usa
  `patrocinios.cobro_jornada` en vez de la fórmula.

## 7. Correo

Remitente nuevo `'patrocinador'` → "Patrocinador", firma "Departamento comercial de {club}",
acción `accion('patrocinios_screen', "VER PATROCINIOS")`. Mensajes: resumen de cierre de
temporada, ofertas nuevas, espacio vacío sin ofertas, y aviso a 3 jornadas del cierre de ventana
si quedan ofertas sin responder.

## 8. Lo que no cambia

- `ingresos_esperados` y el tope salarial: fórmula base, independiente de los contratos reales.
- Clubes de la IA: ingreso de fórmula, sin contratos.
- El objetivo de directiva "Marca" (`directiva.definir_objetivo_marca`) queda como está.

## 9. Manejo de errores

- Puntos de entrada (`cobro_jornada`, `cierre_temporada`, `revisar_jornada`, acciones) con
  `try/except` y `logger.error`. Si `cobro_jornada` falla, se cobra el patrocinio de fórmula de
  esa jornada para no dejar al club sin ingresos por un error.
- Estado ausente, corrupto o de otro club → `asegurar` lo regenera.

## 10. Tests (`tests/test_patrocinios.py`)

- Contratos iniciales: 3 espacios, rubros distintos, años 1–3, y la suma de fijos a valor de
  referencia igual al patrocinio de fórmula.
- `cobro_jornada` con 3, 1 y 0 contratos; `procesar_jornada` registra ese monto en el libro.
- Cada tipo de objetivo: cumplido y fallado; `progreso` entre 0 y 1.
- Cierre de temporada: bono solo si cumple, reputación, años, vencimiento y ofertas.
- Renovación solo con `cumplido_ultima`; exclusividad de rubro; multiplicador de reputación.
- Sin interesados con reputación baja (azar forzado) y espacio vacío tras rechazar todo.
- Negociar: éxito y fracaso forzados, una sola vez por oferta.
- Firmar con y sin prima; rescindir: multa, reputación, saldo insuficiente.
- Cláusulas de ascenso y descenso.
- Cambio de club y partida vieja: se regeneran; ida y vuelta por JSON.
- Ventana de invierno: ofertas ×0.85 y vencimiento de las no respondidas.
- Pantalla: render, firmar, negociar, rechazar, rescindir con confirmación, espacio vacío.
- Regresión: `ingresos_esperados` devuelve lo mismo que antes del cambio de fracciones.

## Versión

v4.9.0. Actualizar `context.md` y la ayuda al terminar.
