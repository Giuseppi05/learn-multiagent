# Mando de respuestas (Wokwi)

Simulación del mando físico descrito en la Sección 18.1 del informe: un Arduino UNO con cuatro botones (A, B, C y D), un potenciómetro para indicar la confianza (1 a 5), una pantalla OLED, un LED y un buzzer.

## Cómo ejecutarlo

1. Entra a https://wokwi.com y crea un proyecto nuevo de **Arduino Uno**.
2. Reemplaza el contenido de `sketch.ino` y `diagram.json` por los de esta carpeta.
3. En el Library Manager agrega las librerías de `libraries.txt` (Adafruit SSD1306 y Adafruit GFX Library).
4. Pulsa **Start**. También puedes usar las teclas `a`, `b`, `c` y `d` para los botones.

## Uso

- Pulsa un botón para elegir una alternativa. Si pulsas otro, cambias de respuesta y se cuenta un cambio.
- Gira el potenciómetro para indicar qué tan seguro estás (1 a 5).
- Pulsa el mismo botón otra vez para confirmar.

## Conexiones

| Componente | Pin del Arduino |
| --- | --- |
| Botón A (verde) | 2 |
| Botón B (rojo) | 3 |
| Botón C (amarillo) | 4 |
| Botón D (azul) | 5 |
| Potenciómetro (SIG) | A0 |
| OLED SSD1306 (SDA / SCL) | A4 / A5 |
| LED (con resistencia de 220 Ω) | 13 |
| Buzzer | 8 |

Los botones usan `INPUT_PULLUP`, así que su otro extremo va a GND.

## Mensaje que envía

Con cada respuesta confirmada, el mando imprime por el puerto serial el topic MQTT y el mensaje JSON que la pasarela publicaría en AWS IoT Core (Secciones 14 y 16):

```
Topic: aula/mando01/respuesta
{"dispositivo":"mando01","pregunta":1,"respuesta":"A","tiempo_ms":7650,"confianza":4,"cambios":0}
```

La pasarela agrega el código del estudiante, el material y un identificador de mensaje antes de publicarlo, y Lambda lo reenvía a `POST /devices/events` del backend. La pasarela y Lambda están diseñadas en el informe, pero todavía no se implementan.
