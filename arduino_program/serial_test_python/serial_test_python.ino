void setup() {
  Serial.begin(115200); // Start serial communication at 115200 baud rate
}

void loop() {
  Serial.println("Hello, WeMos D1!");
  delay(1000); // Wait for a second
}
