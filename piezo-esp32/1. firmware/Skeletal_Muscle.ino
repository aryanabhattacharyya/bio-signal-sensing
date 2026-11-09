void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200); 
  
  analogReadResolution(12); // High detail (0-4095)
}

void loop() {
  // read the main disc and the control disc
  int sensorValueA0 = analogRead(A0);
  int sensorValueA7 = analogRead(A7);
  
// Send raw values separated simply by a comma
// to keep overheads low
  Serial.print(sensorValueA0);
  Serial.print(",");
  Serial.println(sensorValueA7);
  
  // Small delay to keep the data stream manageable
  // and good enough for a skeletal muscle movement tracker
  delay(5); 
}
