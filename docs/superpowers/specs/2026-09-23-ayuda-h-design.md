# Sub-proyecto 8 — Ayuda con la tecla H (v3.9.0)

**Fecha:** 2026-09-23 · **Decidido por Diego:** en todas las pantallas; un overlay que señale y explique
todo. Va al final porque depende de las pantallas definitivas (sub-proyectos 3-6).

## Diseño
- `alpha_football/ui/ayuda.py`: registro `AYUDA: dict[str, list[Item] | Callable[[dict], list[Item]]]`
  con `Item = (rect: pygame.Rect, titulo: str, texto: str)`. Una función por pantalla cuando el
  contenido depende del estado (pestaña del hub, modo de contrato, fase de copa, etapa de negociación).
  Los rects se toman de las constantes/funciones de rects que ya exponen las pantallas (no se copian
  números a mano cuando existe la constante).
- `main.py`: H alterna `estado['ayuda_abierta']` salvo cuando hay un campo de texto activo (buscador por
  nombre, editor, montos: se marca con `estado['texto_activo'] = True`). Con la ayuda abierta:
  1. la pantalla se dibuja normal pero **no recibe eventos** (main los consume);
  2. se oscurece todo (negro 60%);
  3. cada item: su rect recortado de la sombra con borde dorado y un círculo numerado;
  4. panel de leyenda (lado con más espacio libre, o paginado si no entra): "N · Título — texto";
  5. H o ESC cierra; ←/→ pagina la leyenda si hay más de 10 items.
- Textos: español, cortos (≤ 110 caracteres), explican qué hace y los atajos de ese elemento.
- La barra de atajos del sub-proyecto 4 ya anuncia "H Ayuda".

## Cobertura
Todas las pantallas registradas en `main.PANTALLAS` (incluidas las del partido en vivo, prepartido,
editor, copa, negociación, contrato, veredicto, ofertas DT, finanzas, correo, otras ligas…) y cada
pestaña del hub.

## Pruebas
`tests/test_ayuda_v390.py`: cada pantalla de `main.PANTALLAS` tiene entrada; cada una produce ≥ 3
items (menú y pantallas de un solo botón ≥ 2) con rect dentro de 1280×720, título y texto no vacíos y
≤ 110 caracteres; dibujar el overlay de cada pantalla no lanza excepciones (headless); H abre/cierra,
con texto activo no abre; con la ayuda abierta los clics no llegan a la pantalla.
