# QUMARA — jefe cinemático (Minecraft 1.21.1 · Fabric)

**v3 — corrección del modelo y animaciones fluidas.** Modelo orgánico (OBJ `carnivorous_plant`), un solo brazo, ~24 bloques de alto,
**20 ataques** (garra que agarra/lanza/estrella, 4 de veneno y el **ataque arrastrado**), veneno acumulable, sonidos y fases cinematográficas.

Versiones: Minecraft 1.21.1, Fabric Loader 0.16.14, Fabric API 0.116.10+1.21.1, Fabric Loom 1.9.2, Yarn 1.21.1+build.3, Java 21, Gradle 8.11+.
**Ya no necesita GeckoLib** (solo admite cubos): el modelo se dibuja con un renderer propio (`client/render/QumaraRenderer`).

## Compilar
```
gradle wrapper --gradle-version 8.11.1
./gradlew build            # build/libs/qumara-1.0.0.jar
./gradlew runClient
```
`/summon qumara:qumara ~ ~ ~` o el huevo generador. Solo requiere Fabric API.

## Modelo y animaciones (tools/)
`python3 tools/build_model.py ruta/carnivorous_plant.obj [celdas=90] [textura=2048]` (numpy, scipy, pillow) genera:
- `assets/qumara/model/qumara.mesh` — malla decimada (50k vértices / 32k cuads) con 4 pesos por vértice.
- `assets/qumara/model/qumara.qani` — esqueleto + 41 animaciones a 30 fps + trayectoria de la mano.
- `textures/entity/qumara.png` y `qumara_fury.png` (la emisión se hornea en el albedo; la furia es un tinte rojo).
Los archivos generados ya están incluidos; solo hay que ejecutarlo si cambias el modelo o las animaciones.

| archivo | qué hace |
|---|---|
| `qumara_rig.py` | huesos (pivotes), FK |
| `parts.py` | **segmentación en piezas** + pesos (cuerpo/brazo, lengua de 8 huesos, piezas rígidas) |
| `anims.py` | **todas las animaciones** (edítalas aquí); el brazo usa IK hacia objetivos en bloques |
| `animlib.py`, `mesh_tools.py` | IK, cuaterniones, exportadores |

Huesos (32): `raiz, raices_o/e/n/s, tronco, cuello, cabeza, mandibula, lengua_1..8, petalo_sup/izq/der/fizq/fder, hoja_1/2, flor_1/2,
brazo, antebrazo, mano, dedo_1, dedo_2, pulgar`. Convención: +Z frente, −X lado del brazo (derecha del jefe).

**Agarres sincronizados:** `QumaraEntity.handPos(anim, clock)` devuelve la posición real de la palma en esa animación (sale de la
trayectoria exportada), por eso la víctima agarrada se mueve exactamente con la garra que ve el jugador.

## Tamaño
`combat/Scale.java` → `RENDER` (1.3 = ~24 bloques de alto, el brazo alcanza ~17). Es el único valor a tocar: hitbox, alcances, zonas y
cámara se recalculan. Si lo cambias, cambia también `RENDER` en `tools/anims.py` y vuelve a ejecutar `build_model.py`
(los objetivos del brazo están en bloques).

## Qué se arregló y por qué (v3)
**Causa raíz del modelo roto.** El OBJ es una malla «kitbash»: piezas que se tocan o se atraviesan (lengua dentro de la mandíbula, cabeza
dentro de los pétalos…) y que estaban soldadas. La decimación fusionaba vértices de piezas distintas y el skinning las separaba al animar:
cientos de aristas «puente» se estiraban 7–21× (medido: la lengua ya con 10° de flexión rompía ~200 aristas; cabeza 1055, pétalos 600).
También había un error de animación: los desplazamientos locales de la lengua se acumulaban por la jerarquía (crecían al cuadrado).

**Corrección.** (1) Cada triángulo se etiqueta con su **pieza antes de decimar** (`parts.py`), así nunca se fusionan vértices de piezas
independientes: cabeza, mandíbula, 5 pétalos, hojas y flores son piezas rígidas sin triángulos puente. (2) **Lengua de 8 huesos** con pesos
continuos (dos huesos vecinos por vértice, función suave a lo largo de la curva medida), conectada a la boca. (3) Cuerpo/brazo con pesos por
distancia + difusión por la malla, pie del tronco anclado a la raíz. (4) La extensión de la lengua usa desplazamiento local constante.
**Resultado medido** (rotando cada hueso 30° y contando aristas estiradas >2.2×): cabeza, mandíbula, pétalos, hojas, flores y los 8 huesos de
la lengua → **0**; hombro/antebrazo/mano pasaron de 100–500 a <10; mano 501 → 2. Pivotes verificados contra la geometría por render.

**Fluidez de las animaciones.** 30 fps (antes 20). Cada animación se muestrea a 120 Hz y pasa por: muelles subamortiguados (peso y ligera
sobreoscilación en tronco/cuello/cabeza, coleo en la lengua), seguimiento retrasado con acoplamiento inercial en pétalos/flores/hojas
(follow-through), y suavizado gaussiano que elimina las paradas en cada keyframe; la IK del brazo se resuelve después, fotograma a fotograma.
Los golpes llevan **embestida** (la planta se desliza ~3 bloques hacia delante) para que la garra llegue de verdad al círculo rojo:
error de la palma en los impactos medido <0.6 bloques. El idle usa varias frecuencias (respiración, cambio de peso, mirada, onda viajera por
la lengua) en bucle perfecto. Fundidos entre animaciones de 0.25 s.

## Ataques (20) y fases
Fase 0 normal · 1 FURIA (<50 % vida, x1.25) · 2 IRA (<25 %, x1.45).
Antiguos (13): raíces atrapadoras, lengua depredadora (+agarre encadenado), brazo aplastante, barrido, jardín maldito, enredadera, martillo,
grieta de raíces, ciclón, devorar, lluvia de espinas, abanico de lengua, rugido. Con un solo brazo, los ataques «del otro lado» cruzan el brazo.

**ATAQUE ARRASTRADO** (`DragAttack`): clava el brazo a su derecha y lo arrastra en línea recta 13 bloques por delante, con peso. La **franja
roja es exactamente la trayectoria de la palma** (constantes compartidas con `tools/anims.py`) y el daño lo hace la mano: la posición sale de
`QumaraEntity.handPos`, así que solo golpea donde el brazo está en ese instante (15 de daño, empuje y raíz corta); se esquiva saliendo de la
franja o saltando. Deja surco de tierra, hojas, raíces que brotan a su paso y raspado continuo. En furia/ira encadena el arrastre de vuelta.

Nuevos de la v2: **garra mortal** (lanzar / estrellar, furia+), **escupitajo**, **nube**, **aliento** y **lluvia de veneno**. El veneno hace daño
real, se acumula hasta nivel 3 y se cura con leche.

## Efectos y sonido
- **Estela del brazo automática** (`QumaraEntity.handFx`): hojas y viento cuando la mano se mueve rápido, polvo/tierra cuando roza el suelo,
  sonido de «whoosh»; siempre sincronizado porque usa la trayectoria real de la animación.
- **Fases cinematográficas**: espiral de hojas ascendente, anillos de tierra, corona de raíces que estallan, sonido propio (`phase_shift`),
  y tras el cambio **desbloquea/abre con un ataque nuevo** (furia → arrastre; ira → nube tóxica). Muerte en 4 tiempos (rugido, anillos, colapso, floración).
- **Ambiente vivo**: respiración sincronizada con el ciclo del idle (sonido + esporas por la boca), cambio de peso con temblor de tierra, hojas y esporas.
- **Sonido**: 15 eventos nuevos (respiración, chasquido/extensión/retracción de lengua, raspado, whoosh, golpe colosal, raíces, plantas, agarre, estrujón,
  cambio de fase, rugido de muerte, escupitajo, paso pesado), todos capas graves de sonidos vanilla con **varias variantes aleatorias** por evento.
  Cada IMPACT lleva además la capa `slam_heavy` con tono variable. Se pueden sustituir por .ogg propios en `sounds.json`.
- Todo el combate, los efectos y los sonidos se generan **en el servidor** y se envían a todos por igual (no hay duplicados en multijugador);
  los indicadores rojos son los mismos para todos y se calculan con la misma forma que usa el servidor para el daño.

## Multitud, daño
Sin cambios: vida base 3000, daño dividido por participantes^0.75, tope 2 % por golpe, daño que ignora armadura, partículas adaptativas.

## Estado de la verificación (sin maquillar)
Comprobado aquí: el pipeline completo, las métricas de estiramiento por hueso, la IK (error en impactos), las trayectorias de la mano (la del
arrastre es recta), el cargador/animador/skinning en Java puro (coincide con Python, 2.5 ms por fotograma) y que **todo el código Java parsea sin
errores de sintaxis** y que los símbolos propios del proyecto que usa el código nuevo existen.
**No se pudo compilar contra Minecraft ni ejecutar el juego** (sin acceso a las dependencias de Gradle en este entorno): puede que haya que corregir
algún nombre de API de Yarn al compilar, y los tiempos, daños, intensidades de sonido y poses habrá que afinarlos en juego. Los sonidos son capas de
sonidos vanilla (no hay audio propio); si un nombre vanilla no existe en 1.21.1, simplemente no suena y se registra una advertencia.
