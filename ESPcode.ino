#include <Adafruit_Fingerprint.h>
#include <SoftwareSerial.h>
#include <WiFi.h>
#include <PubSubClient.h>

#define FINGERPRINT_TX 17
#define FINGERPRINT_RX 16

const char* ssid = "x";
const char* password = "x";
const char* mqtt_server = "x";

SoftwareSerial mySerial(FINGERPRINT_RX, FINGERPRINT_TX);
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);

WiFiClient espClient;
PubSubClient client(espClient);

uint8_t id;
String fingerprintTemplate = "";

void setup_wifi() {
  delay(10);
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  mySerial.begin(57600);
  finger.begin(57600);
  finger.LEDcontrol(FINGERPRINT_LED_ON, 0, FINGERPRINT_LED_PURPLE);

  setup_wifi();
  client.setServer(mqtt_server, 1883);

  if (finger.verifyPassword()) {
    Serial.println("Found fingerprint sensor!");
  } else {
    Serial.println("Did not find fingerprint sensor :(");
    while (1) { delay(1); }
  }

  finger.getParameters();
  Serial.print("Capacity: "); Serial.println(finger.capacity);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  Serial.println("Ready to enroll a fingerprint!");
  Serial.println("Please type in the ID # (from 1 to 127) you want to save this finger as...");
  id = readnumber();
  if (id == 0) {
    return;
  }
  Serial.print("Enrolling ID #");
  Serial.println(id);

  if (getFingerprintEnroll()) {
    // Generate a random 4-digit number
    int randomNumber = random(1000, 10000);

    // Prepare the message
    String msg = String(id) + "," + fingerprintTemplate + "," + String(randomNumber);

    // Publish to MQTT topic
    if (client.publish("esp32/fingerprint", msg.c_str())) {
      Serial.println("Fingerprint data sent successfully");
    } else {
      Serial.println("Failed to send fingerprint data");
    }
  }
}

uint8_t getFingerprintEnroll() {
  int p = -1;
  Serial.print("Waiting for valid finger to enroll as #"); Serial.println(id);
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    switch (p) {
      case FINGERPRINT_OK:
        Serial.println("Image taken");
        break;
      case FINGERPRINT_NOFINGER:
        Serial.print(".");
        break;
      case FINGERPRINT_PACKETRECIEVEERR:
        Serial.println("Communication error");
        break;
      case FINGERPRINT_IMAGEFAIL:
        Serial.println("Imaging error");
        break;
      default:
        Serial.println("Unknown error");
        break;
    }
  }

  p = finger.image2Tz(1);
  switch (p) {
    case FINGERPRINT_OK:
      Serial.println("Image converted");
      break;
    case FINGERPRINT_IMAGEMESS:
      Serial.println("Image too messy");
      return p;
    case FINGERPRINT_PACKETRECIEVEERR:
      Serial.println("Communication error");
      return p;
    case FINGERPRINT_FEATUREFAIL:
    case FINGERPRINT_INVALIDIMAGE:
      Serial.println("Could not find fingerprint features");
      return p;
    default:
      Serial.println("Unknown error");
      return p;
  }
  
  Serial.println("Remove finger");
  delay(2000);
  p = 0;
  while (p != FINGERPRINT_NOFINGER) {
    p = finger.getImage();
  }
  Serial.println("Place same finger again");
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
  }

  p = finger.image2Tz(2);
  if (p != FINGERPRINT_OK) {
    Serial.println("Error in second scan");
    return p;
  }

  p = finger.createModel();
  if (p != FINGERPRINT_OK) {
    Serial.println("Error creating model");
    return p;
  }

  p = finger.getModel();
  if (p != FINGERPRINT_OK) {
    Serial.println("Error getting model");
    return p;
  }

  p = finger.get_template(id);
  if (p != FINGERPRINT_OK) {
    Serial.println("Error getting template");
    return p;
  }

  uint8_t templateBuffer[256];
  memset(templateBuffer, 0xFF, 256);
  uint16_t templateSize = 256;
  p = finger.get_template_buffer(templateBuffer, &templateSize);
  if (p != FINGERPRINT_OK) {
    Serial.println("Error getting template buffer");
    return p;
  }

  // Convert template to hex string
  fingerprintTemplate = "";
  for (int i = 0; i < templateSize; i++) {
    if (templateBuffer[i] < 0x10) fingerprintTemplate += "0";
    fingerprintTemplate += String(templateBuffer[i], HEX);
  }

  Serial.println("Fingerprint enrolled successfully!");
  return true;
}

uint8_t readnumber(void) {
  uint8_t num = 0;
  while (num == 0) {
    while (!Serial.available());
    num = Serial.parseInt();
  }
  return num;
}
