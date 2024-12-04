//inisaialisasi input
//modifikasi hanya kirim sinyal trigger saja
#define start_trigger 12 //diff down di plc karena pc delay
#define reset_trigger 11 //diff up di plc biar continous loop di python
#define man_ok_trigger 10 //paksa oke manual 

//inisialisasi output  
#define ok_trigger 4 //untuk trigger plc
#define out_ok 5
#define out_ng 6

void matikan_lampu(int pin_out = -1){
    // matikan semua output
    if (pin_out == -1){
        digitalWrite(out_ok, HIGH);
        digitalWrite(out_ng, HIGH);
        digitalWrite(ok_trigger, HIGH);
      }
    else{
        digitalWrite(pin_out, HIGH);
      }
}

void setup() {
  // definisi pin INPUT
  pinMode(reset_trigger, INPUT_PULLUP);
  pinMode(start_trigger, INPUT_PULLUP);
  pinMode(man_ok_trigger, INPUT_PULLUP);

  //definisi pin output
  pinMode(out_ok, OUTPUT);
  pinMode(out_ng, OUTPUT);
  pinMode(ok_trigger, OUTPUT);

  // inisialisasi serial
  Serial.begin(115200);

  //tungggu hingga serial terhubung, berkedip jika belum terhubung
  while(!Serial){
    blink_output(out_ok, 3, 5);
  }

  // matikan semua output
  matikan_lampu();
}

void loop() {
  read_data_python();
  read_pin_input();
}
//****************** ini yang kirim serial ke python ***************************
void read_pin_input() {
  if(digitalRead(man_ok_trigger) == LOW){
    Serial.println("manual_ok");
    matikan_lampu();
    digitalWrite(out_ok, LOW);
    digitalWrite(ok_trigger, LOW);
    digitalWrite(out_ng, LOW);
    delay(100);
  }
  
  if (digitalRead(start_trigger) == LOW) {
    Serial.println("start_scan");
    delay(100);
  } 
  //bagian reset didalamnya di tambahkan lagi kondisi bypass dan trigger karena biar gak ngunci loop nya
  else if(digitalRead(reset_trigger) == LOW){
      Serial.println("reset_scan");
      matikan_lampu();
      delay(100);
  }

  else {
    Serial.println("no_trigger");
    delay(100);
  }
}

//****************** ini yang baca dari python ***************************
void read_data_python() {
  //jika ada data di serial lakukan pembacaan
  if (Serial.available() > 0) {
      // Membaca data yang masuk
      String data = Serial.readString();
      data.trim();
      if(data == "out_ok"){
        digitalWrite(out_ok, LOW);
        digitalWrite(ok_trigger, LOW);
        digitalWrite(out_ng, HIGH);
        Serial.println("hasil nya oke");
//        delay(2000);
        }
      else if(data == "out_ng"){
        digitalWrite(out_ok, HIGH);
        blink_output(out_ng, 3, 5);
        digitalWrite(ok_trigger, HIGH);
        Serial.println("hasil nya jelek");
        }
      // Mengembalikan data yang diterima ke port serial
      Serial.print("Pesan yang diterima arduino: ");
      Serial.println(data);
    }
}

void blink_output(int pin_out, int repetisi, int interval) {
  interval = interval * 100;
  for (int i = 0; i < repetisi; i++) {
    digitalWrite(pin_out, HIGH);
    delay(interval);
    digitalWrite(pin_out, LOW);
    delay(interval);
  }
}
