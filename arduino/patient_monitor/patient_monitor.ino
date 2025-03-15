#define SENSOR_BUFFER_SIZE 100  // Add this line to define the sensor buffer size

#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"
#include "spo2_algorithm.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <esp_sleep.h>

#define ONE_WIRE_BUS 4
#define STATUS_LED 2
#define ERROR_LED 13

// WiFi Credentials
const char* ssid = "tsr";
const char* password = "1234567890";

// ThingSpeak Configuration
const char* apiKey = "SJPIKXSQ27L3H5K2";
const char* thingSpeakUrl = "http://api.thingspeak.com/update";
const int channelID = 2839570;

MAX30105 particleSensor;

const char* apiRoute="http://192.168.112.24:5000/sensorData?temp=";

const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute;
int beatAvg;
uint32_t irBuffer[SENSOR_BUFFER_SIZE];  // Change buffer size to SENSOR_BUFFER_SIZE
uint32_t redBuffer[SENSOR_BUFFER_SIZE]; // Change buffer size to SENSOR_BUFFER_SIZE
int bufferLength = SENSOR_BUFFER_SIZE;
int32_t spo2;
int8_t validSPO2;
int32_t heartRate;
int8_t validHeartRate;

// DS18B20 Temperature Sensor
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// Global variables
float temperature;
float systolic, diastolic;
int32_t hrBuffer[5];
int32_t spo2Buffer[5];
float tempBuffer[5];
int bufferIndex = 0;

// Function declarations
bool connectWiFi();
void checkWiFiConnection();
bool sendDataToThingSpeak(float temp, int hr, int spo2, float systolic, float diastolic);
void checkSensorStatus();
void filterReadings(int32_t *heartRate, int32_t *spo2, float *temperature);
void estimateBloodPressure(float heartRate, float spo2);
bool isValidReading(float value, float min, float max);

void setup() {
    Serial.begin(115200);
    Serial.println("Initializing sensors...");

    pinMode(STATUS_LED, OUTPUT);
    pinMode(ERROR_LED, OUTPUT);
    digitalWrite(STATUS_LED, LOW);
    digitalWrite(ERROR_LED, LOW);

    // Initialize MAX30105 Pulse Oximeter
    if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        Serial.println("MAX30105 sensor not found. Check wiring!");
        while (1);
    }
    particleSensor.setup();
    particleSensor.setPulseAmplitudeRed(0x1F);
    particleSensor.setPulseAmplitudeIR(0x1F);
    Serial.println("MAX30105 Pulse Oximeter Initialized");

    // Initialize temperature sensor
    sensors.begin();

    // Connect to WiFi
    if (!connectWiFi()) {
        Serial.println("Failed to connect to WiFi");
        digitalWrite(ERROR_LED, HIGH);
        while (1);
    }

    Serial.println("Setup complete!");
}

#define SENSOR_BUFFER_SIZE 100  // Ensure this is defined, otherwise the code will fail

void loop() {
    checkSensorStatus();
    checkWiFiConnection();
    
    // Read sensor data from MAX30105
    for (int i = 0; i < SENSOR_BUFFER_SIZE; i++) {
        while (!particleSensor.available()) particleSensor.check();
        redBuffer[i] = particleSensor.getRed();
        irBuffer[i] = particleSensor.getIR();
        particleSensor.nextSample();
    }

    // Process data from MAX30105 sensor
    maxim_heart_rate_and_oxygen_saturation(irBuffer, SENSOR_BUFFER_SIZE, redBuffer, &spo2, &validSPO2, &heartRate, &validHeartRate);

    // Read temperature data from DS18B20 sensor
    sensors.requestTemperatures();
    temperature = sensors.getTempCByIndex(0);


    // Filter and smooth out sensor readings
    filterReadings(&heartRate, &spo2, &temperature);

    // Estimate Blood Pressure (BP)
    estimateBloodPressure(heartRate, spo2);

    // Print the results to Serial Monitor
    Serial.print("Heart Rate: ");
    Serial.print(validHeartRate ? heartRate : -1);
    Serial.println(" BPM");
    
    Serial.print("SpO2: ");
    Serial.print(validSPO2 ? spo2 : -1);
    Serial.println(" %");
    
    Serial.print("Temp: ");
    Serial.print(temperature);
    Serial.println(" C");
    
    Serial.print("BP: ");
    Serial.print(systolic);
    Serial.print("/ ");
    Serial.print(diastolic);
    Serial.println(" mmHg");

  sendDataToThingSpeak(temperature,heartRate,spo2,systolic,diastolic);
  sendDataToApi(temperature,heartRate,spo2,systolic,diastolic);
  delay(5000);
}

bool connectWiFi() {
    WiFi.begin(ssid, password);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        digitalWrite(ERROR_LED, !digitalRead(ERROR_LED));
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected");
        digitalWrite(ERROR_LED, LOW);
        return true;
    }
    return false;
}

void checkWiFiConnection() {
    if (WiFi.status() != WL_CONNECTED) {
        if (!connectWiFi()) {
            Serial.println("Failed to reconnect WiFi.");
        }
    }
}

bool isValidReading(float value, float min, float max) {
    return value >= min && value <= max;
}

void filterReadings(int32_t *heartRate, int32_t *spo2, float *temperature) {
    hrBuffer[bufferIndex] = *heartRate;
    spo2Buffer[bufferIndex] = *spo2;
    tempBuffer[bufferIndex] = *temperature;
    bufferIndex = (bufferIndex + 1) % 5;
    
    float hrSum = 0, spo2Sum = 0, tempSum = 0;
    for (int i = 0; i < 5; i++) {
        hrSum += hrBuffer[i];
        spo2Sum += spo2Buffer[i];
        tempSum += tempBuffer[i];
    }
    *heartRate = (int32_t)(hrSum / 5);
    *spo2 = (int32_t)(spo2Sum / 5);
    *temperature = tempSum / 5;
}

bool sendDataToThingSpeak(float temp, int hr, int spo2, float systolic, float diastolic) {
    if (WiFi.status() != WL_CONNECTED) {
        if (!connectWiFi()) {
            Serial.println("Failed to reconnect WiFi.");
            return false;
        }
    }

    HTTPClient http;
    
    // Construct the ThingSpeak API request URL
    String url = String(thingSpeakUrl) + "?api_key=" + apiKey +
                 "&field1=" + String(temp) +
                 "&field2=" + String(hr) +
                 "&field3=" + String(spo2) +
                 "&field4=" + String(systolic) +
                 "&field5=" + String(diastolic);

    http.begin(url);  // Use the constructed URL with parameters
    int httpCode = http.GET();  // Send GET request
    
    if (httpCode > 0) {
        Serial.println("ThingSpeak Response: " + http.getString());
        digitalWrite(STATUS_LED, HIGH);
        http.end();
        return true;
    } else {
        Serial.println("HTTP Error: " + String(httpCode));
        digitalWrite(ERROR_LED, HIGH);
        http.end();
        return false;
    }
}

void checkSensorStatus() {
    Serial.println("Checking sensor status...");
    // Add actual sensor status checking logic if needed
}

void estimateBloodPressure(float heartRate, float spo2) {
    // Simple estimation formula (You can adjust this)
    systolic = 120 + (heartRate - 75) * 0.5;
    diastolic = 80 + (spo2 - 95) * 0.2;
}
void sendDataToApi(float temp, int hr, int spo2, float systolic, float diastolic) {
    if (WiFi.status() != WL_CONNECTED) {
        if (!connectWiFi()) {
            Serial.println("Failed to reconnect WiFi.");
            return;
        }
    }

    HTTPClient http;
    String url = String(apiRoute) + temp + "&hr=" + hr + "&spo2=" + spo2 + "&systolic=" + systolic + "&diastolic=" + diastolic+"&wallet=0xB83f47eCE6e49a3A6061D0f7c33E746AF4662966";
    http.begin(url);
    int httpCode = http.GET();
    if (httpCode > 0) {
        Serial.println("API Response: " + http.getString());
        digitalWrite(STATUS_LED, HIGH);
        http.end();
    } else {
        Serial.println("HTTP Error: " + String(httpCode));
        digitalWrite(ERROR_LED, HIGH);
        http.end();
    }
}
