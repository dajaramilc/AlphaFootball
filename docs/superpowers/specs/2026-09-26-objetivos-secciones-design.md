# Objetivos por secciones (Local · Internacional · Finanzas · Marca · Juveniles) — diseño

**Fecha:** 2026-09-26 · **Estado:** aprobado en chat por Diego (pendiente revisión del spec)

## Objetivo

Reorganizar la pantalla OBJETIVOS en secciones, quitar el historial, sacar de ahí las ofertas de otros
clubes (solo en OFERTAS DT) y agregar dos objetivos nuevos por temporada: **Marca** y **Juveniles**.
Los nuevos solo mueven la calificación de DT (como el internacional): sin dinero ni despido.

## 1. Pantalla `ui/objetivos_screen.py`

- **Franja superior** (ancho completo): barra de confianza de la directiva, barra de calificación de DT y
  el pedido activo de la directiva (texto).
- **Fila 1**, 3 tarjetas: **LOCAL** (meta de liga, "vas Xº", botón "?" de reglas — igual que hoy),
  **INTERNACIONAL** (meta de copa y fase alcanzada, o "sin competición esta temporada"),
  **FINANZAS** (barras de masa salarial/tope y saldo/mínimo; deuda del espaldarazo si hay).
- **Fila 2**, 2 tarjetas anchas: **MARCA** y **JUVENILES**: texto de la meta, progreso con barra y
  estado (EN CURSO / CUMPLIDO / FALLADO al cierre).
- **Se elimina**: el panel HISTORIAL DE OBJETIVOS (los datos siguen en `estado['historial']`) y todo lo
  de la oferta de otro club (texto, botón VER OFERTA, overlay aceptar/rechazar).
- Ayuda (H) y barra de atajos actualizadas a las zonas nuevas.

## 2. Ofertas de otros clubes solo en OFERTAS DT

- `ui/ofertas_dt_screen.py` muestra también la oferta vigente de `ofertas_dt` (la de la calificación,
  v4.6.0) como una fila más, con ACEPTAR (`ODT.aceptar` → `contrato_dt_screen`, modo `alta`) y
  RECHAZAR (`ODT.rechazar`). Las de `entrenadores` siguen igual.
- El correo de esa oferta (`ofertas_dt.py`) enlaza a `ofertas_dt_screen` en vez de `objetivos_screen`.
- El badge de OFERTAS DT en el hub cuenta también esa oferta.
- **Los correos dicen por qué te quieren**, y ambos citan tu calificación (las de banquillo ya se
  filtran por calificación con `en_banda`):
  - Banquillo (`entrenadores._ofrecer_al_user`): "Tras despedir a nuestro entrenador (iba Xº y se
    esperaba Yº) y en vista de su calificación como DT (N/100), ...". El motivo se guarda en la oferta.
  - Calificación (`ofertas_dt.revisar_jornada`): "Su calificación como DT (N/100) y su trabajo en
    <tu club> no han pasado desapercibidos...", y se responde desde OFERTAS DT.
- En OFERTAS DT cada fila muestra el motivo: "Despidieron a su DT" o "Por tu calificación".

## 3. Reglas de Marca y Juveniles (`directiva.py`)

Se fijan una vez por temporada (como `definir_objetivo_copa`, guardadas en `datos_carrera` con la
temporada; saves viejos las crean al primer acceso). Se guarda `ids_inicio` (ids de la plantilla al
fijarla) para detectar fichajes: jugador nuevo = id que no estaba (fichaje o libre, no cedidos que
vuelven porque ya estaban).

**Marca** (`objetivo_marca`), una al azar:
- `valor`: "Llegar a $X de valor del club", X = valor del club al fijarla × 1.10.
  Valor del club = suma de `valor` de la plantilla + saldo (se mueve a `finanzas.valor_club(equipo)`;
  FINANZAS lo usa también).
- `estrella`: "Fichar un jugador de media ≥ X", X = media de la plantilla (redondeada) + 5.

**Juveniles** (`objetivo_juveniles`):
- Si la edad media de la plantilla ≥ 27.5: `edad`: "Bajar la edad media a X", X = edad media − 1.0
  (1 decimal).
- Si no, al azar entre:
  - `partidos_u21`: "Que los menores de 21 sumen N partidos", N = max(10, 2 × nº de menores de 21 × 
    jornadas / 22) redondeado; cuenta `partidos_jugados` (se resetea cada temporada) de los < 21 actuales.
  - `fichar_joven`: "Fichar un jugador de 21 años o menos".

**Progreso** (fracción 0..1 para la barra): valor actual / meta; estrella y fichar_joven 0 o 1;
edad: 1 si edad media ≤ meta, si no proporcional a lo que se bajó; partidos: suma / N.

**Cumplido en curso**: al detectarlo se envía una vez el correo "Objetivo cumplido: ..." (reusa
`_ya_avisado`). Se revisa en el mismo punto donde hoy se revisan liga/copa.

**Cierre** (`evaluar_temporada`, junto a `evaluar_objetivo_copa`): cumplido +4 / fallado −3 de
calificación (`CALIF_SECUNDARIO`). El resultado va en `info['marca']` / `info['juveniles']` y en el
correo de evaluación (`texto_evaluacion`).

**Correo de objetivos** al empezar la temporada: agrega una línea para Marca y otra para Juveniles.

## 4. Tests

- Elección de meta: edad alta → `edad`; edad normal → `partidos_u21` o `fichar_joven`; Marca → valor o
  estrella con los valores calculados.
- Cumplimiento: fichaje nuevo con media ≥ X cumple estrella; joven ≤ 21 cumple fichar_joven; valor y
  edad según números; aviso de cumplido una sola vez.
- Cierre: +4 / −3 en calificación e info en el correo de evaluación.
- Pantallas: objetivos se dibuja con y sin copa y sin panel de historial; la oferta de `ofertas_dt`
  aparece en OFERTAS DT y ACEPTAR lleva a `contrato_dt_screen`; el correo enlaza a `ofertas_dt_screen`.
- Tests existentes que usen el overlay de oferta en objetivos se mueven a OFERTAS DT.

## Fuera de alcance

Minutos reales por jugador (se usan partidos jugados), historial visible en otra pantalla, premios en
dinero por Marca/Juveniles.
