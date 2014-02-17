#include "SPI.h"
#include <SoftwareSerial.h>
#include <Wire.h>
//#include <SdFat.h> //the sdfat library is buggy and can't be used
//#include <SdFatUtil.h> //in this program.

String buffer;
const String progID="LAir 0.1";//version information
byte strobe=true;
int fade=0,fadeT=10000;
unsigned long oldMillis;

/*
This program sets up a protocol for commands to be sent from a
computer's python script to an arduino and back. Numbers can be sent
using alpha-hex, which does not suffer python's bug of ignoring
unprintable characters sent over serial. The getSerial function
listens for commands and the processSerial function executes them.

Initialization:
When the device first boots up it should send no serial packets
until it has recieved a handshake from the computer on the other
end of the serial line. Then it can send messages safely back and
forth to the interface software. Don't send serial messages until
a handshake is established!

*/
//SdFat sd; //file system object
//ArduinoOutStream SPStream;
SoftwareSerial ss(3,8);

const byte pinCon=6; //analog switch control pin
byte pinConOld;

void setup(){
  Wire.begin(); //join I2C as master
  Serial.begin(9600);
  ss.begin(9600);
  //if(!sd.begin(0,SPI_HALF_SPEED)){/*Throw error*/} //sdfat does not seem to be working on my arduino nano!
  //delay(400); //'catch due reset problem' not required?
  //set up pins
  pinMode(pinCon,OUTPUT);
  millisSet();
  pinMode(13,OUTPUT); //LED pin
  //startupM41T83();
  pinConOld=LOW;
  digitalWrite(pinCon,pinConOld);
}

void pinConSet(int c){
  digitalWrite(pinCon,c);
  if(c!=pinConOld){
    delay(10);
    pinConOld=c;
  }
}

void millisSet(){
  oldMillis=millis();
}

unsigned long millisPassed(){
  if (oldMillis<=millis()) {
    return millis()-oldMillis;
  } else {
    unsigned long limit=4294966396; //2^32-1000
    return ((limit-(oldMillis-1000))+millis()+2000);
  }
}

void waitUntilMillis(int wait){
  //call this after you've used millisSet. It delays the software until a the requested number of microseconds have passed.
  while(millisPassed()<wait){}
  millisSet();
}

void getSerial() {
  //scans for serial info. If any characters are recieved they are added to the buffer string.
  //once a line break is recieved, the buffer is handed off for processing.
  //this code doesn't search for the start of a packet, however.
  if (Serial.available()!=0){
    char s=Serial.read();
    //putSerial("imm");
    if (s==13){
      processSerial(buffer);
      buffer=String();
    } else {
      buffer.concat(s);
    }
  }
}

void processSerial(String s){
  //this function first discards malformed packets as represented
  //by the string s, and then can be used to call functions based
  //on packet contents.
  //putSerial("LN"+String(s.length()));
  if(s.length()>1){ //the program will ignore packets of length 1.
    char t0=s.charAt(0); //these variables contain the tag of the packet.
    char t1=s.charAt(1); //ie what information or request it contains
    if (t0=='V') {
      if (t1=='V') {
        putSerial("VV"+progID);//the program returns a packet containing version information.
      }
    }else if (t0=='H') {
      if (t1=='T') {
        String out=readCC2D25();//This don't work, it freezes the system for some reason.
        putSerial("HT"+out);//the program returns temperature and humidity data.
      }
    }else if (t0=='t') {
      if (t1=='S') {//time, set
        setTimeM41T83(slice(s,3,s.length()));
        putSerial("OK");//alright, the wire library didn't crash!
      }else if (t1=='G') {//time, get
        String in=getTimeM41T83();
        putSerial("tG"+in);
      }
    }else if (t0=='M') {
      if (t1=='0') {//measure bank zero
        pinConSet(LOW);
        String out=measure();
        putSerial("M0"+out);
      }else if(t1=='1'){//measure bank one
        pinConSet(HIGH);
        String out=measure();
        putSerial("M1"+out);
      }
    }else if (t0=='R'){ //Radio
      if (t1=='r'){//recieve
      }else if (t1=='t'){//transmit
      }
    }
  }
}

String slice(String s,int from,int to){
  //returns a string comprised of the string s letter between
  //from and to. bounding values are 0 to s.length().
  char t[to-from];
  t[to]='\0'; //null terminate
  for (int i=from;i<to;i++){
    t[i]=s[i];
  }
  return String(t);
}

byte alphahexToByte(char s0,char s1) {
  //turns a pair of alphahex chars into a byte
  byte b;
  b=(s0-97)+((s1-97)<<4);
  return b;
}

String byteToAlphahex(byte b){
  String out="xx";
  out.setCharAt(0,(b&0xf0)+97);
  out.setCharAt(1,(b&0x0f)+97);
  return out;
}

String u12ToAlphahex(int i){
  //converts a 12 bit number to alphahex. a=0, p=f
  //to pass an array: fn(int array[]){};
  char c[4];
  c[0]=((i>>8)&0x000f)+97;
  c[1]=((i>>4)&0x000f)+97;
//  c[1]=(i&0x00f0)+97;
  c[2]=(i&0x000f)+97;
  c[3]=0;
  String out=String(c);
  return out;
}

void putAlphahexByte(byte b){
  //does not terminate the string.
  Serial.write((b&0xf0)+97);
  Serial.write((b&0x0f)+97);
}

void putSerial(String s) {
  //serial codes must be encapsulated with 2 and 13.
  //Serial.write(2);
  Serial.print(s);
  Serial.write(13);
}

void putInt(int i){
  //sends an alphahex packet representing an int to a controlling computer.
  String s;byte j;
  Serial.write(2);
  j=(i&0xff000000)>>24;
  putAlphahexByte(j);
  j=(i&0x00ff0000)>>16;  
  putAlphahexByte(j);
  j=(i&0x0000ff00)>>8;
  putAlphahexByte(j);
  j=(i&0x000000ff);
  putAlphahexByte(j);
  Serial.write(13);
}

void startupCC2D25(){
  //CC2D25 setup procedure
  //
  Wire.beginTransmission(0x28);
  Wire.write(0x1c);
  Wire.endTransmission();
}

String readCC2D25(){
  //pauses until completed! This function parses the output
  //into alphahex, HHTT.
  byte snag=0,b0,b1,b2,b3;
  char c0,c1,c2,c3;
  String out,ts;
  Wire.beginTransmission(0x28); //wake command
  Wire.endTransmission();
  //while(snag==0){
    Wire.requestFrom(0x28,4); //send data read request
    delay(100);
    while(Wire.available()){
      c0=Wire.read();
      c1=Wire.read();
      c2=Wire.read();
      c3=Wire.read();
      if(c0&0xc0==00){snag=1;}
    }
  //}
  out=byteToAlphahex(c0&0x3f);
  out.concat(byteToAlphahex(c1));
  out.concat(byteToAlphahex((c2&0xfc)/4));
  out.concat(byteToAlphahex(c3/4+(c2&0x03)*64));
  return out;
}

void startupM41T83(){
  //clears the halt bit for when the M41T83 starts up
  Wire.beginTransmission(0xd0);
  Wire.write(0x0c);
  Wire.write(0x00); //clear halt bit, along with it alarm1 time.
  Wire.endTransmission();
}

String getTimeM41T83(){
  //address 0xd0. Using the longer read sequence from page 13.
  //delivers a string YMDHMSm
  byte b[7];
  Wire.beginTransmission(0xd0);
  Wire.write(0x00);
  Wire.endTransmission();
  //now we read our data
  Wire.requestFrom(0xd0,8); //send data read request
  //delay(5); //a bit of a delay might be necessary, right?
  b[6]=Wire.read();
  b[5]=Wire.read();
  b[4]=Wire.read();
  b[3]=Wire.read();
  b[2]=Wire.read();//day of week, which is discarded.
  b[2]=Wire.read();
  b[1]=Wire.read();
  b[0]=Wire.read();
  //we now have a char array. We must convert this to alphahex.
  //not using strings might save memory space
  String out="";
  for(int i=0;i<7;i++){
    out+=b[i];
  }
  return out;
  //return String(b[0]); //hopefully a simple operation!
}

//String chainHex(byte[] b){
  //pass an array of 
//}

String setTimeM41T83(String s){
  //python cannot recieve bytes properly, but it can transmit them.
  //the string will be sent in form tSxxxxxxx\n where x=YMDHMSm
  Wire.write(0x00);//initial address
  Wire.write(s[6]-20);
  Wire.write(s[5]-20);//watch that you don't set the stop bit (0x80) to 1.
  Wire.write(s[4]-20);
  Wire.write(s[3]-20);//remember to set the century bits correctly
                      //in the control program
  Wire.write(0); //who cares whether it's Sunday? Every day is blessed!
  Wire.write(s[2]-20);
  Wire.write(s[1]-20);
  Wire.write(s[0]-20);
  Wire.endTransmission();
}

String measure(){
  //returns a string containing alphahex of each value.
  String out;
  out+=u12ToAlphahex(analogRead(A0));
  out+=u12ToAlphahex(analogRead(A1));
  out+=u12ToAlphahex(analogRead(A2));
  out+=u12ToAlphahex(analogRead(A3));
  out+=u12ToAlphahex(analogRead(A4));
  out+=u12ToAlphahex(analogRead(A5));
  out+=u12ToAlphahex(analogRead(A6));
  out+=u12ToAlphahex(analogRead(A7));
  return out;
}

void doStrobe(){
  if (fade<fadeT){fade++;} else {fade=0;}
  if (strobe==false&&fade==0){
    digitalWrite(13,HIGH);
    strobe=true;
  }else if(strobe==true&&fade==0){
    digitalWrite(13,LOW);
    strobe=false;
  }
}

void loop(){
  //putSerial("help");
  //waitUntilMillis(1000);
  doStrobe();
  getSerial();
  //putAlphahexByte(1);
  //Serial.write(13);
}
