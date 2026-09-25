# v4.4.0 — Nivel al cierre de temporada, salidas de jugadores y aviso de mercado

**Fecha:** 2026-09-24 · **Autor:** claude (sesión "mercado", en paralelo con la sesión "bebito" de partido/teclado/copa v4.0-4.3)
**Estado:** diseño aprobado por Diego en el chat, sección por sección. Sin commit (Diego prueba y aprueba al final).

## Objetivo

1. El nivel del plantel responde a la temporada: el que desciende pierde media, el que asciende la gana, y el club que no cumple **ningún** objetivo también la pierde. Siempre según el rendimiento de cada jugador.
2. Los jugadores descontentos se hacen notar: escriben, piden salir y se ponen en transferibles bloqueados. Llegan ofertas sí o sí, y rechazarlas enoja al jugador y a la directiva, con una escalada de correos. Cuando un grande desciende, sus 3 mejores piden salir.
3. La apertura y el cierre del mercado se anuncian en INICIO con un cartel destacado y una franja con la cuenta regresiva, no solo por correo.

## Coordinación con la otra sesión (bebito)

- **Módulos nuevos:** `alpha_football/nivel_temporada.py`, `alpha_football/salidas.py`, `alpha_football/ui/aviso_mercado.py` y `tests/test_mercado_v440.py`, con la cabecera de `tests/test_ux_v360.py`.
- **Archivos que bebito no toca y edito directo:** `mercado_ia.py`, `market.py`, `ui/resumen_temporada_screen.py`, `ui/ofertas_screen.py`, `ui/plantilla_screen.py` y `models.py` (campos nuevos del jugador).
- **Hooks de una línea en su propio try/except, en los archivos de bebito** (se relee la zona antes de cada Edit):
  - `ui/match_screen.finalizar_jornada_liga`: `salidas.cierre_jornada(estado)` justo después del bloque de ofertas. bebito agrega el suyo al final de la función.
  - `ui/league_screen`, render del hub INICIO: `aviso_mercado.dibujar(...)` y el consumo de eventos al final del render. **No tapar la barra ni `R_SOBRE` (y<76).**
  - `directiva.resolver_pedido`: registrar el pedido resuelto en `datos_carrera['pedidos_temporada']`. bebito no toca esta función.
  - `vestuario.actualizar_moral`: ediciones puntuales (§2). bebito confirmó que no la cambia; `post_partido_user` solo ganó kwargs opcionales.
- **Motor nuevo de notas (bebito):** `partidos_jugados` cuenta a todos los que pisaron la cancha, incluidos los suplentes que entraron, y la nota va de 3.0 a 10.0 según los eventos. La fórmula de `promedio_nota` no cambia.
- Comentarios `# v4.4.0: ...` en español. Todo hook lleva try/except + `logger.error`.

## §1 Nivel al cierre de temporada (`nivel_temporada.py`)

### Rendimiento
- **Elegibles:** jugadores con `partidos_jugados >= num_jornadas / 3` en la liga de la temporada que termina.
- **Puntaje:** `promedio_nota − media_puesto`, donde `media_puesto` es la media de `promedio_nota` de los elegibles de ese puesto (POR/DEF/MED/DEL) en **toda su liga**, calculada antes del swap.
  - **Por qué:** medido con el motor nuevo, en una temporada de 22 jornadas los promedios quedan entre 5.7 y 6.9, y los porteros llevan un sesgo de +0.5 a +0.6 por las atajadas. Unos cortes fijos no distinguirían a nadie, y sin corregir por puesto el portero sería siempre "el mejor".
- Los elegibles del plantel se ordenan por puntaje de mayor a menor. El jugador del índice `i` de `n` cae en el tramo `floor(i * k / n)`, donde `k` es la cantidad de tramos.

| Caso | Tramos (mejor → peor) | No elegible |
|---|---|---|
| Descenso | −2 / −3 / −4 / −5 (k=4) | −3 |
| Ascenso | +6 / +5 / +4 / +3 (k=4) | +4 |
| Ningún objetivo cumplido | 0 / −1 / −2 (k=3) | −1 |

### Reglas
- **Ascenso:** si `overall >= 83`, el ascenso suma 0. Si no, suma `min(delta, 83 − overall)`. El potencial sube lo mismo que subió la media: `min(99, max(pot + aplicado, overall + 1))`.
- **Descenso y objetivos:** el potencial no cambia.
- La media se mueve con `mercado_ia._mover_media`, que reparte el delta entre los 5 atributos.
- **No se suman entre sí:** el que desciende recibe solo el bajón de descenso y el que asciende solo la subida. El bajón por objetivos es para los clubes que no subieron ni bajaron.
- **Se aplica a todos los clubes de las 16 ligas**, no solo al del user.

### "Ningún objetivo cumplido"
- **User:** se cumplen las tres condiciones:
  - la liga quedó `fallado` (`directiva.evaluar_temporada`, `info['resultado']`);
  - la copa quedó `fallado`, o el club no tenía objetivo de copa;
  - ningún pedido de la temporada quedó cumplido (`datos_carrera['pedidos_temporada']`, filtrado por temporada).
- **IA:** posición final `> pos_max` de `directiva.objetivo_por_ranking(r, n, division, cupo, ventaja)`, con `r` el ranking por media del club.
  - La foto se guarda en `datos_carrera['objetivos_ia'] = {'temporada': t, 'pos_max': {equipo_id: pos_max}}` al final de `avanzar_nueva_temporada`, después del mercado de pretemporada.
  - Sin foto de esa temporada (1ª temporada de la carrera o save viejo) se usa el ranking al cierre.

### Tope con la curva por edad
- La pérdida total de la temporada (bajón + delta de `desarrollo.progresar_pasivo`) no pasa de **−6** si descendió, ni de **−3** si incumplió los objetivos.
- El exceso se devuelve con `_mover_media(+)`.
- Las subidas por edad sí se suman.
- **Implementación:**
  - Al aplicar el bajón se guarda, en `estado['_nivel_tmp']`, `id(j) → (bajon, overall_tras_bajon, tope)`.
  - Después de `progresar_liga_pasivo`, `aplicar_topes(estado)` compara y corrige, y luego borra `_nivel_tmp`.

### Orden en `resumen_temporada_screen.avanzar_nueva_temporada`
1. Después de `evaluar_temporada` y de `entrenadores.cierre_temporada`, `nivel_temporada.preparar(estado)` calcula, para todas las ligas en `primera_division` y `segunda_division`:
   - las medias por puesto,
   - los tramos por club,
   - la bandera `objetivo_fallado` por club,
   - la bandera `grande` por club: estaba en el top 6 de 12 por media antes del bajón.

   Todo queda en `estado['_nivel_plan']`.
2. En el swap, `mercado_ia.aplicar_ascenso(eq, tipo)` y `aplicar_descenso(eq)` delegan el cambio de media en `nivel_temporada.aplicar(eq, 'ascenso'|'descenso', estado)`.
   - Si no hay plan (llamadas de tests viejos o fallo), usa el fallback: todos no elegibles (+4/−3).
   - El premio de ascenso no cambia.
   - `SUBE_ASCENSO` y `BAJA_DESCENSO` quedan solo para el fallback.
   - Antes del bajón, `salidas.marcar_salida_forzada` marca a los 3 mejores del grande que desciende (§2).
3. Después del swap, `nivel_temporada.aplicar_objetivos(estado)` aplica el bajón por objetivos a los clubes que no se movieron.
4. El reset y `progresar_liga_pasivo` no cambian.
5. `nivel_temporada.aplicar_topes(estado)` y el correo al user.
6. Al final, `nivel_temporada.foto_objetivos_ia(estado)`.

### Correo al user (remitente `club`, acción VER PLANTILLA)
- **Descenso:** "Descenso: los jugadores están en mala forma y perdieron nivel".
- **Objetivos:** "Temporada sin objetivos: los jugadores están en mala forma y perdieron nivel".
- **Ascenso:** "Ascenso: el plantel da un salto de nivel".
- **Cuerpo:** cambio promedio y lista `Nombre Apellido ±N` con el valor final, ya con el tope aplicado.

## §2 Moral, descontento y pedidos de salida (`salidas.py` + `vestuario.actualizar_moral`)

### Moral: ediciones puntuales en `actualizar_moral`
- **Toda baja se multiplica ×2** (constante `MULT_BAJA_MORAL = 2`):
  - derrota −4; clásico perdido −12 (más la derrota);
  - nota <5.5 −6;
  - top 5 sin jugar −6 (profesional −2);
  - mala forma −4.
- **Sueldo** menor al **80%** del de mercado (antes 60%): −4 (profesional −2, mercenario −8).
- **Nuevo:** −2 por jornada si lleva 3 o más partidos seguidos sin jugar y `overall >= media del plantel`. Contador `j.jornadas_sin_jugar`.
- **Vuelta a 70:** solo desde abajo (+1). Ya no resta a quien está por encima de 70.
- **Causas:** cada componente negativo se anota en `j.causas_moral`, una lista de las últimas 4 jornadas con un dict `{'minutos': x, 'equipo': y, 'sueldo': z}` cada una.
  - **minutos:** top 5 sin jugar, 3 o más partidos sin jugar.
  - **equipo:** derrota, clásico, nota baja, mala forma, contagio del polémico.
  - **sueldo:** sueldo bajo.
- **Pide salir:** `moral < 50` durante 4 jornadas seguidas (polémico 3, **líder 5**; antes ≤30 durante 6 y el líder nunca). Contador `j.jornadas_moral_baja` con el umbral nuevo.
- **Se cura** si la moral llega a 50 o más, excepto con `salida_forzada`.
- **Renovar** (negociación de v2.9.0) con un sueldo de al menos el 100% del de mercado da +10 de moral y limpia la causa `sueldo`. Hook en el punto donde se confirma la renovación, en `negociacion.py`, que bebito no toca.

### Descontento (`salidas.revisar_descontento`, desde `cierre_jornada`)
- Tras **1 jornada con moral <50**, el jugador escribe una vez por episodio (`j.descontento_avisado`). El episodio se cierra con moral ≥50.
- La causa que elige el mensaje es la de mayor suma en `causas_moral`. Si empatan, el orden es sueldo > minutos > equipo.
- **5 textos por causa**, sorteados sin repetir el último:
  - **minutos:** "quiere jugar más". Acción: VER PLANTILLA.
  - **equipo:** "quiere que el equipo mejore". Acción: VER PLANTILLA.
  - **sueldo:** "quiere un contrato acorde". Acción: RENOVAR, que abre la renovación de ese jugador.
- Reemplaza al correo actual "Su moral bajó a X": `actualizar_moral` deja de llenar `salida['quejas']`, así que `post_partido_user` no se toca.

### Pide salir
- `actualizar_moral` lo marca además como `transferible = True` **bloqueado**: `plantilla_screen.alternar_transferible` no lo quita, y el botón y la tecla T muestran "PIDE SALIR".
- Correo del jugador: el de pide salir que ya existe en `post_partido_user` ("Lleva semanas descontento y pide salir").
- Al curarse (sin salida forzada) sale de transferibles, `escalon_salida = 0` y llega un correo "X se queda contento".

### Salida forzada (grande que desciende)
- En el swap, antes del bajón: los 3 mejores por `overall` de cada club que desciende con la bandera `grande`.
- **User:**
  - `pide_salir = transferible = salida_forzada = True`;
  - no se curan por moral y solo se van vendidos;
  - correo de la directiva: "Tras el descenso, X, Y y Z piden salir".
- **IA:** `mercado_ia.ronda_fichajes_ia(estado, 'pretemporada')` los vende primero a clubes de 1ª que puedan pagar su valor. Si ninguno puede, al de mayor presupuesto por el 80% del valor. Se usan las funciones de traspaso que ya existen en `mercado_ia`.

### Campos nuevos en `models.Jugador`
Todos con default y persistidos en `to_dict` y `from_dict`: `salida_forzada: bool`, `escalon_salida: int`, `causas_moral: list`, `jornadas_sin_jugar: int`, `descontento_avisado: bool`. Al vender, fichar o liberar se limpian junto con `transferible` y `pide_salir`, en los mismos puntos de v3.1.0.

## §3 Ofertas garantizadas y escalada (`salidas.py`)

### Ofertas garantizadas
- Mientras la ventana está abierta (`market.ventana_mercado_abierta`), en cada `cierre_jornada`, cada jugador del user que pide salir y no tiene oferta pendiente en `ofertas_recibidas` recibe una.
- **Formato:** el de `crear_oferta_ui`, `{jugador, comprador, monto}`.
- **Comprador:** un club con `balance >= monto`.
  - Con `salida_forzada`: solo clubes de 1ª, de su país o de otro.
  - Sin `salida_forzada`: su liga u otra 1ª.
- **Monto:** `valor × U(0.9, 1.2) × factor_contrato`.
- **Clásico:** se respeta la regla de v3.5.0: el rival de clásico no oferta salvo que la moral sea <40.
- Llega el correo de "Oferta por X" que ya existe.
- Los de salida forzada reciben su primera oferta al comenzar la temporada, en `avanzar_nueva_temporada`, después de marcarlos.

### Escalada (se retoma entre ventanas)
- **Por rechazo:** `ofertas_screen._rechazar_sel`, si la oferta es por un jugador que pide salir, llama a `salidas.oferta_rechazada(estado, jugador)`. Resta −8 de moral y sube un escalón.
- **Por tiempo:** en cada `cierre_jornada` con la ventana abierta en que el jugador sigue en el club, sube otro escalón.

| Escalón | Remitente | Correo | Efecto |
|---|---|---|---|
| 1 Aviso | jugador | "Rechazaste la oferta / sigo esperando: quiero irme" | — |
| 2 Advertencia | directiva | "El vestuario está incómodo con la situación de X" | confianza −5 |
| 3 Recordatorio | directiva | "Te recordamos que X quiere salir" | confianza −5, calif DT −2 |
| 4+ Regaño | directiva | "Estamos molestos: X sigue en el club" (se repite en cada escalón siguiente) | confianza −10, calif DT −4 |

- **Un solo correo por jugador por jornada**, el del escalón más alto alcanzado. Los escalones se acumulan en la jornada y el correo sale en `cierre_jornada`. Un rechazo fuera del cierre manda su correo en el momento y marca la jornada como avisada.
- **Cierre del caso:** al venderlo, o al curarse sin salida forzada. `escalon_salida = 0`.
- **Fuera de la ventana:** no sube el escalón ni llegan ofertas.
- La confianza y la calificación usan `directiva.confianza`/`ajustar_calif` y `_dc(estado)['confianza']`, acotadas a 0-100.

## §4 Aviso de mercado (`ui/aviso_mercado.py`)

### Eventos
- **Abre:** en la J1 y en la J `n − 2` (primera jornada de la ventana final, según `ventana_mercado_abierta`).
- **Cierra:** en la J4.
- **No se anuncia** el cierre al terminar la temporada.
- `evento_pendiente(estado) -> Optional[tuple[str, int]]`: compara `(temporada, jornada_evento)` con `datos_carrera['aviso_mercado_visto']`. Cada evento se muestra una sola vez.
- Al detectarlo, se envía también un correo del club: "Se abrió el mercado de pases" o "Se cerró el mercado de pases".

### Cartel modal
- Al entrar a INICIO con un evento pendiente, y sin la ayuda H ni otro overlay abiertos.
- Fondo oscurecido y recuadro centrado de ~560×260.
- **Abierto:** "MERCADO ABIERTO" en verde, "Hasta la jornada X: fichajes, ofertas y cláusulas", y "N jugadores piden salir" si hay.
- **Cerrado:** "MERCADO CERRADO" en rojo, "Reabre en la jornada Y".
- **Botones** IR AL MERCADO (→ `market_screen`) y CONTINUAR:
  - ←/→ elige;
  - Enter confirma;
  - Esc = CONTINUAR.
- Mientras está abierto consume los eventos del hub, igual que el overlay de ayuda.

### Franja
- Mientras la ventana está abierta, una línea de ~22 px en **y≈78-100**: debajo de la barra y de `R_SOBRE` (y<76) y encima de las columnas del hub.
- Texto: "MERCADO ABIERTO · cierra en N jornadas" en verde, o "· ÚLTIMA JORNADA" en dorado.
- Antes de fijarla se mide en el render real que no choque con nada. Si choca, va dentro del panel superior de INICIO, sin mover nada.

## Tests (`tests/test_mercado_v440.py`)
Se corre con `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONIOENCODING=utf-8 python tests/test_mercado_v440.py`.
- **§1:**
  - tramos por cuartos y tercios;
  - corrección por puesto (un portero con nota alta pero igual a la media de los porteros no queda primero);
  - valor de los no elegibles;
  - tope de 83 del ascenso;
  - tope −6/−3 con la curva;
  - que no se sumen los bajones;
  - objetivo de la IA con foto y sin foto;
  - condiciones de "ningún objetivo" del user;
  - temporada completa de punta a punta (`avanzar_nueva_temporada`), con correo al user.
- **§2:**
  - bajas ×2 y vuelta a 70 solo hacia arriba;
  - penalización por sueldo bajo al 80%;
  - causas y mensaje elegido (incluido el de sueldo);
  - 5 textos distintos por causa;
  - pide salir con <50 durante 4/3/5 jornadas;
  - transferible bloqueado;
  - curación;
  - salida forzada (user e IA vendidos en pretemporada).
- **§3:**
  - oferta garantizada por jornada con la ventana abierta y ninguna con la ventana cerrada;
  - escalones por rechazo y por jornada;
  - un solo correo por jornada;
  - efectos en confianza y calificación;
  - cierre al vender.
- **§4:**
  - eventos con 14 y con 22 jornadas;
  - cada evento sale una sola vez;
  - Enter → mercado y Esc → cierra;
  - render dummy sin excepciones;
  - la franja no se cruza con `R_SOBRE` ni con la barra.
- **Regresión:** se vuelven a correr `test_vestuario_v310`, `test_mercado_v350`, `test_plantilla_v260`, `test_integracion_v290` y los tests de ascenso y descenso (`test_v236`, `test_integridad_v300`), ajustando los que dependían del +4/−2 fijo o de los umbrales viejos de moral.

## Fuera de alcance
- Moral de los planteles de la IA (el sistema de moral es solo del user).
- Cambios en el motor de partido y en las notas (sesión bebito).
- Rebalanceo de la economía de la IA.
