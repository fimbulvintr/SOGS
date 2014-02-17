#include <XBee.h>

unsigned long msNow, msLast;  
XBee xbee = XBee();

ZBTxRequest zbTx = ZBTxRequest();
ZBTxStatusResponse txStatus = ZBTxStatusResponse();
ZBRxResponse rx = ZBRxResponse();
ModemStatusResponse msr = ModemStatusResponse();

XBeeAddress64 Broadcast = XBeeAddress64(0x00000000, 0x0000ffff);
int newMes=0;
char Hello[] = "All Okay";
char Goodbye[] = "Goodbye World";
//char Buffer[128];  // this needs to be longer than your longest packet.

void setup() { 
  // Start Arduino<-->PC Serial Connection
  Serial.begin(9600);
  // Start Arduino<-->XBee Serial Connection
  Serial3.begin(9600);
  xbee.setSerial(Serial3);
  // Send Initialisation message to PC
  Serial.print("Initialized\n");
}

void loop() {
  msNow = millis();
  readXBee();
 // delay(100);
  if (msNow > msLast + 10000) {                   //transmit pachube data every 60 sec
  xbeeTX2();
  msLast = msNow;
        }
}


void xbeeTX() {
    //build the tx request
    zbTx.setAddress64(Broadcast);
    zbTx.setAddress16(0xFFFE);
    zbTx.setPayload((uint8_t *)Hello);
    zbTx.setPayloadLength(strlen(Hello));
    xbee.send(zbTx);
}

void xbeeTX2() {
    //build the tx request
    zbTx.setAddress64(Broadcast);
    zbTx.setAddress16(0xFFFE);
    zbTx.setPayload((uint8_t *)Goodbye);
    zbTx.setPayloadLength(strlen(Goodbye));
    xbee.send(zbTx);
    Serial.print("Message Sent\n");
}

String readXBee(){ 
 int i = 0; //check four times in case a message was missed 
 for(i=0;i<2;i++){ 
 newMes = 0; 
 xbee.readPacket(); 
 if(xbee.getResponse().isAvailable()){ 
 //got some message 
 if(xbee.getResponse().getApiId() == ZB_RX_RESPONSE){ 
   Serial.print("Message Received:\n");
 //got a zb rx packet 
 //fill the zb rx class 
 xbee.getResponse().getZBRxResponse(rx); 
 
 int len = rx.getDataLength(); //number of char received 
 char buff [len+2]; 
 int i = 0; 
 for(i = 0; i<len;i++){ 
 buff[i] = (char)rx.getData(i); 
 } 
 buff[i+1] = '\0'; 
 Serial.print(buff[0]);
 Serial.print("\n");
 //determine if the received data is a message, or coordinate 
 if(buff[0] == 'R'){
  newMes = 1;
  Serial.print("Message Content: Request Data\n"); 
}
else if(buff[0] == 'q'){
  newMes = 1; 
  Serial.print("Message Content: Check Status\n");
  xbeeTX();
}
else { 
 //sent data is a message 
 newMes = 1; 
 } 
 return buff; 
 
 
 } 
 } 
 } 
 //else //if no packet received 
 return NULL; 
} 

