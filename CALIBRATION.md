# Calibración por equipo y varios monitores

La calibración se guarda localmente en `data/cursor_calibration.json`. Cada
equipo conserva sus propios valores si tiene su propia copia del proyecto. Si
usas la misma carpeta en otro computador, vuelve a calibrar antes de controlar
el escritorio.

## Preparación

1. En **Configuración de Windows > Sistema > Pantalla**, selecciona
   **Extender estas pantallas**. El modo Duplicar no crea un escritorio amplio.
2. Ordena las pantallas como están físicamente: izquierda, derecha, arriba o
   abajo. Marca la pantalla principal que prefieras.
3. Conecta todos los monitores que usarás antes de abrir Jarvis. Si cambias la
   conexión después, pulsa `F8` para pausar y otra vez `F8` para recargar la
   geometría del escritorio virtual.
4. Ejecuta `uv run asistente-jarvis control` y pulsa `F8` para activar.

## Ajuste del cursor

1. Pulsa `F9`. El panel bloquea las acciones mientras ajustas.
2. Empieza con los valores guardados. Si es un equipo nuevo, prueba como base:

   | Situación | Sensibilidad | Estabilidad | Zona muerta |
   |---|---:|---:|---:|
   | Notebook sin monitor externo | 1.0 | 0.55 | 2.0 px |
   | Monitor externo 1080p | 1.2–1.4 | 0.55 | 2.5 px |
   | Dos o más pantallas o ultrawide | 1.3–1.7 | 0.55 | 2.5–3.0 px |

3. Señala con el índice y comprueba que puedes recorrer una pantalla con un
   movimiento cómodo de muñeca y antebrazo. Sube **sensibilidad** si te falta
   alcance; bájala si cuesta apuntar a controles pequeños.
4. Deja el índice quieto sobre un botón pequeño. Sube **estabilidad** si vibra;
   bájala si el cursor responde tarde a un movimiento decidido.
5. Sube **zona muerta** hasta que desaparezca el temblor mínimo. Si el cursor
   tarda en arrancar, redúcela en pasos de 0.5 px.
6. Pulsa `F9` para guardar. Pulsa `F10` si quieres ver el punto bruto,
   filtrado, destino y posición real mientras afinas.

## Comprobación con varios monitores

1. Deja el cursor en la pantalla principal y mueve el índice hasta cruzar cada
   borde. El control usa el escritorio virtual completo y admite coordenadas
   negativas, por ejemplo si tienes un monitor a la izquierda.
2. Prueba una pinza y un arrastre en cada monitor. El origen del clic se toma
   de la posición real del cursor, por lo que no debe saltar al monitor
   principal.
3. Toma una ventana con la garra y llévala al borde derecho. El programa envía
   `Win+Shift+Derecha`, que Windows usa para moverla a la pantalla adyacente.
   Vuelve con un lanzamiento al borde izquierdo (`Win+Shift+Izquierda`).
4. Con tres o más pantallas en fila, cada lanzamiento cruza una pantalla. Para
   recorrer varias, toma la ventana de nuevo y repite el gesto hacia el mismo
   lado.

El lanzamiento de ventana sigue la disposición de Windows en sentido izquierdo
o derecho. Para una disposición vertical, Windows puede requerir ajustes con el
mouse o con sus propios atajos, porque el gesto actual solo expresa izquierda y
derecha. El traslado funciona con ventanas normales de escritorio; una
aplicación en modo pantalla completa propio, como un navegador en `F11`, debe
salir primero de ese modo.
