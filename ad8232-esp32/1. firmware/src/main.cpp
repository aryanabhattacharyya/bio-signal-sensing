#define ANALOG_PIN 36  // The AD8232 OUT pin

// Create a pointer for the hardware timer
hw_timer_t * timer = NULL;
portMUX_TYPE timerMux = portMUX_INITIALIZER_UNLOCKED;

// This is the Interrupt Service Routine (ISR)
// It executes instantly every time the timer alarms
void IRAM_ATTR onTimer() {
  portENTER_CRITICAL_ISR(&timerMux);
  
  // Read the ADC (12-bit value: 0 to 4095)
  //int val = analogRead(ANALOG_PIN);
  int val = analogRead(A7);
  
  // Blast it out the serial port immediately
  Serial.println(val);
  
  portEXIT_CRITICAL_ISR(&timerMux);
}

void setup() {
  Serial.begin(115200);
  pinMode(ANALOG_PIN, INPUT);

  // Configure the hardware timer:
  // Timer 0, prescaler of 80. Since ESP32 base clock is 80MHz, 
  // an 80 prescaler means the timer ticks exactly 1,000,000 times per second (1MHz).
  timer = timerBegin(0, 80, true);

  // Attach our onTimer function to the timer
  timerAttachInterrupt(timer, &onTimer, true);

  // Set the alarm to go off every 1,000 ticks (1,000 microseconds = 1 millisecond = 1000Hz)
  timerAlarmWrite(timer, 2000, true);

  // Start the engine!
  timerAlarmEnable(timer);
}

void loop() {
  // Main loop stays completely empty! 
  // The hardware timer handles everything in the background.
}