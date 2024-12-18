//inisaialisasi input
//modifikasi hanya kirim sinyal trigger saja
#define start_trigger 8 //TCR REQUEST
#define reset_trigger 9 //input LS internal

//inisialisasi output  
#define ok_trigger 4 // Untuk reset TCR dan output jika deteksi OK
#define ng_trigger 5 // 

/********
 * kirim data ke arduino dengan data serial 
 * deteksi_ok => jika hasil OK
 * deteksi_ng => jika hasil NG
 * deteksi_reset => jika akan reset
 */
void matikan_lampu(int pin_out = -1){
    // matikan semua output
    if (pin_out == -1){
        digitalWrite(ng_trigger, LOW);
        digitalWrite(ok_trigger, LOW);
      }
    else{
        digitalWrite(pin_out, LOW);
      }
}

void setup() {
  // definisi pin INPUT
  pinMode(reset_trigger, INPUT_PULLUP);
  pinMode(start_trigger, INPUT_PULLUP);

  //definisi pin output
  pinMode(ng_trigger, OUTPUT);
  pinMode(ok_trigger, OUTPUT);

  // inisialisasi serial
  Serial.begin(115200);

  //tungggu hingga serial terhubung, berkedip jika belum terhubung
  while(!Serial){
    blink_output(ng_trigger, 3, 5);
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
   
  //bagian reset didalamnya di tambahkan lagi kondisi bypass dan trigger karena biar gak ngunci loop nya
  if(digitalRead(reset_trigger) == LOW){
    Serial.println("reset_scan");
    matikan_lampu();
    delay(100);
  }
  else if (digitalRead(start_trigger) == LOW) {
    Serial.println("start_scan");
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
      //membaca hasil deteksi dari python
      if(data == "deteksi_ok"){ //jika hasil deteksi nya OK
        digitalWrite(ng_trigger, LOW);
        digitalWrite(ok_trigger, HIGH);
        delay(500);
//        Serial.println("mau masuk while");
        while(digitalRead(start_trigger)==false)//kalo sinyal TCR nya on nyalain ini
              { 
//                Serial.println("udah masuk while");
                digitalWrite(ok_trigger, LOW);delay(1);
                }
//        Serial.println("dah lewat while");
        digitalWrite(ok_trigger, HIGH);
        Serial.println("hasil nya oke");
//      delay(5);
        }
      else if(data == "deteksi_ng"){ //jika hasil deteksi nya NG
        digitalWrite(ok_trigger, LOW);
        blink_output(ng_trigger, 3, 5);
        Serial.println("hasil nya jelek");
        }
      else if(data == "deteksi_reset"){ //jika hasil deteksi nya di reset
        matikan_lampu();
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
    digitalWrite(pin_out, LOW);
    delay(interval);
    digitalWrite(pin_out, HIGH);
    delay(interval);
  }
}
