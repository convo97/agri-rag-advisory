// esp32_post_sensor.ino
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "DHT.h"

// Replace with your WiFi credentials
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";

// Server endpoint (FastAPI)
const char* serverUrl = "http://YOUR_SERVER_IP:8000/sensor"; // e.g., http://192.168.1.100:8000/sensor

// Sensor pins
#define DHTPIN 14       // DHT22 data pin
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

const int SOIL_PIN = 34; // ADC pin for soil moisture
const int LIGHT_PIN = 35; // ADC pin for light sensor
const int BATTERY_PIN = 39; // ADC pin for battery voltage (via divider)

const char* device_id = "farmplot-001";

void setup() {
  Serial.begin(115200);
  dht.begin();

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi connected");
}

float readBatteryVoltage() {
  // If you use a voltage divider, scale accordingly
  int raw = analogRead(BATTERY_PIN);
  float voltage = (raw / 4095.0) * 3.3; // raw ADC scaling to 3.3V reference
  // Adjust for voltage divider factor if used
  // e.g., if divider halves voltage, multiply by 2:
  // voltage *= 2.0;
  return voltage;
}

int readSoilPercent() {
  int raw = analogRead(SOIL_PIN);
  // raw range depends on sensor. Convert to percent: example mapping
  float perc = (1.0 - (raw / 4095.0)) * 100.0; // adjust depending on wiring
  if (perc < 0) perc = 0;
  if (perc > 100) perc = 100;
  return (int)perc;
}

int readLightLuxApprox() {
  int raw = analogRead(LIGHT_PIN);
  // crude mapping; for real lux use proper sensor
  int lux = map(raw, 0, 4095, 0, 1000);
  return lux;
}

void postSensorData(float temperature, float humidity, int soilPerc, int lightLux, float batteryV) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected!");
    return;
  }

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<512> doc;
  doc["device_id"] = device_id;
  JsonObject payload = doc.createNestedObject("payload");
  payload["temperature"] = temperature;
  payload["humidity"] = humidity;
  payload["soil_moisture_percent"] = soilPerc;
  payload["light_lux_approx"] = lightLux;
  payload["battery_voltage"] = batteryV;

  String body;
  serializeJson(doc, body);

  int httpCode = http.POST(body);
  if (httpCode > 0) {
    Serial.printf("POST %s => %d\n", serverUrl, httpCode);
    String resp = http.getString();
    Serial.println(resp);
  } else {
    Serial.printf("POST failed, error: %s\n", http.errorToString(httpCode).c_str());
  }
  http.end();
}

void loop() {
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();

  if (isnan(temp) || isnan(hum)) {
    Serial.println("Failed to read DHT sensor");
  } else {
    int soil = readSoilPercent();
    int lightLux = readLightLuxApprox();
    float batt = readBatteryVoltage();

    Serial.printf("T: %.2f H: %.2f Soil: %d Light: %d Batt: %.2f\n", temp, hum, soil, lightLux, batt);
    postSensorData(temp, hum, soil, lightLux, batt);
  }

  // send every 60 seconds (adjust as needed)
  delay(60 * 1000);
}
