// Mando de respuestas (Sección 18.1 del informe)
// Arduino UNO + 4 botones (A, B, C, D) + potenciómetro de confianza + OLED SSD1306 + LED + buzzer.
//
// Flujo por pregunta:
//   1. La pantalla muestra la pregunta y las cuatro alternativas.
//   2. El estudiante pulsa un botón para elegir. Si pulsa otro botón, cambia su respuesta (cuenta como cambio).
//   3. Pulsa el mismo botón otra vez para confirmar. Antes de confirmar ajusta el potenciómetro (confianza 1 a 5).
//   4. El mando da retroalimentación (pantalla, LED y buzzer) y envía por serial el mensaje JSON
//      que la pasarela publica por MQTT en AWS IoT Core (Secciones 14 y 16).

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const char* DISPOSITIVO = "mando01";
const char* TOPIC = "aula/mando01/respuesta";

const uint8_t PIN_BOTON[4] = {2, 3, 4, 5};  // A, B, C, D (con INPUT_PULLUP: pulsado = LOW)
const uint8_t PIN_LED = 13;
const uint8_t PIN_BUZZER = 8;
const uint8_t PIN_POT = A0;
const char LETRA[4] = {'A', 'B', 'C', 'D'};

Adafruit_SSD1306 pantalla(128, 64, &Wire, -1);

struct Pregunta {
  const char* enunciado;
  const char* opcion[4];
  uint8_t correcta;  // índice 0..3
};

const Pregunta PREGUNTAS[] = {
  {"7 x 3 = ?", {"21", "24", "18", "10"}, 0},
  {"1/4 + 2/4 = ?", {"3/8", "3/4", "1/2", "2/4"}, 1},
  {"12 : 4 = ?", {"2", "4", "8", "3"}, 3},
};
const uint8_t TOTAL = sizeof(PREGUNTAS) / sizeof(PREGUNTAS[0]);

uint8_t actual = 0;           // pregunta en pantalla
int8_t seleccion = -1;        // alternativa elegida, -1 = ninguna
uint8_t cambios = 0;          // veces que cambió de alternativa
unsigned long inicio = 0;     // momento en que apareció la pregunta
uint8_t confianzaMostrada = 0;
bool estabaPulsado[4] = {false, false, false, false};

uint8_t leerConfianza() {
  // 0..1023 -> 1..5
  return map(analogRead(PIN_POT), 0, 1024, 1, 6);
}

void dibujarPregunta() {
  const Pregunta& p = PREGUNTAS[actual];
  confianzaMostrada = leerConfianza();
  pantalla.clearDisplay();
  pantalla.setTextSize(1);
  pantalla.setTextColor(SSD1306_WHITE);
  pantalla.setCursor(0, 0);
  pantalla.print(p.enunciado);
  for (uint8_t i = 0; i < 4; i++) {
    pantalla.setCursor((i % 2) * 64, 14 + (i / 2) * 11);
    pantalla.print(i == seleccion ? '>' : ' ');
    pantalla.print(LETRA[i]);
    pantalla.print(") ");
    pantalla.print(p.opcion[i]);
  }
  pantalla.setCursor(0, 40);
  pantalla.print("Confianza: ");
  pantalla.print(confianzaMostrada);
  pantalla.print("/5");
  pantalla.setCursor(0, 54);
  if (seleccion < 0) {
    pantalla.print("Pulsa A, B, C o D");
  } else {
    pantalla.print("Pulsa ");
    pantalla.print(LETRA[seleccion]);
    pantalla.print(" para confirmar");
  }
  pantalla.display();
}

void nuevaPregunta() {
  seleccion = -1;
  cambios = 0;
  inicio = millis();
  dibujarPregunta();
}

void enviarRespuesta(unsigned long tiempoMs, uint8_t confianza) {
  // Mismo formato que recibe la pasarela (Sección 16)
  Serial.print("Topic: ");
  Serial.println(TOPIC);
  Serial.print("{\"dispositivo\":\"");
  Serial.print(DISPOSITIVO);
  Serial.print("\",\"pregunta\":");
  Serial.print(actual + 1);
  Serial.print(",\"respuesta\":\"");
  Serial.print(LETRA[seleccion]);
  Serial.print("\",\"tiempo_ms\":");
  Serial.print(tiempoMs);
  Serial.print(",\"confianza\":");
  Serial.print(confianza);
  Serial.print(",\"cambios\":");
  Serial.print(cambios);
  Serial.println("}");
  Serial.println();
}

void retroalimentar(bool correcta) {
  const Pregunta& p = PREGUNTAS[actual];
  pantalla.clearDisplay();
  pantalla.setTextSize(2);
  pantalla.setCursor(0, 8);
  pantalla.print(correcta ? "Muy bien!" : "Casi...");
  pantalla.setTextSize(1);
  pantalla.setCursor(0, 40);
  if (correcta) {
    pantalla.print("Respuesta correcta.");
  } else {
    pantalla.print("Era la ");
    pantalla.print(LETRA[p.correcta]);
    pantalla.print(") ");
    pantalla.print(p.opcion[p.correcta]);
  }
  pantalla.display();

  if (correcta) {
    digitalWrite(PIN_LED, HIGH);
    tone(PIN_BUZZER, 880, 200);
    delay(1500);
    digitalWrite(PIN_LED, LOW);
  } else {
    tone(PIN_BUZZER, 220, 400);
    for (uint8_t i = 0; i < 3; i++) {
      digitalWrite(PIN_LED, HIGH);
      delay(250);
      digitalWrite(PIN_LED, LOW);
      delay(250);
    }
  }
}

void confirmar() {
  unsigned long tiempoMs = millis() - inicio;
  uint8_t confianza = leerConfianza();
  bool correcta = seleccion == PREGUNTAS[actual].correcta;
  enviarRespuesta(tiempoMs, confianza);
  retroalimentar(correcta);

  actual++;
  if (actual >= TOTAL) {
    pantalla.clearDisplay();
    pantalla.setTextSize(1);
    pantalla.setCursor(0, 20);
    pantalla.print("Fin de la practica.");
    pantalla.setCursor(0, 34);
    pantalla.print("Reiniciando...");
    pantalla.display();
    delay(3000);
    actual = 0;
  }
  nuevaPregunta();
}

void pulsado(uint8_t boton) {
  if (seleccion == boton) {
    confirmar();
    return;
  }
  if (seleccion >= 0) {
    cambios++;
  }
  seleccion = boton;
  tone(PIN_BUZZER, 600, 40);
  dibujarPregunta();
}

void setup() {
  Serial.begin(9600);
  for (uint8_t i = 0; i < 4; i++) {
    pinMode(PIN_BOTON[i], INPUT_PULLUP);
  }
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);

  if (!pantalla.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("No se encontró la pantalla OLED");
    while (true) {}
  }
  Serial.println("Mando 01 listo. Enviando por serial a la pasarela...");
  Serial.println();
  nuevaPregunta();
}

void loop() {
  for (uint8_t i = 0; i < 4; i++) {
    bool ahora = digitalRead(PIN_BOTON[i]) == LOW;
    if (ahora && !estabaPulsado[i]) {
      delay(30);  // antirrebote
      if (digitalRead(PIN_BOTON[i]) == LOW) {
        estabaPulsado[i] = true;
        pulsado(i);
      }
    } else if (!ahora) {
      estabaPulsado[i] = false;
    }
  }

  // La confianza se actualiza en pantalla mientras el estudiante gira el potenciómetro
  if (leerConfianza() != confianzaMostrada) {
    dibujarPregunta();
  }
}
