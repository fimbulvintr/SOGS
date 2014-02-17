#written for python 3
#0-1 First version
#0-1b New handshake listener system
#display version

import tkinter as tk #user interface library
import os 
import serial #pyserial library
from psigraph import * #change for release

class trimmedUI:
    #You can use this if you prefer a minimal UI.
    def __init__(self):
        self.logType=1
        self.master=tk.Tk()
        self.frame=tk.Frame(self.master)
        self.frame.pack(expand=1,fill=tk.BOTH)
    def log(self,s,sw=0):
        #sw=0 for in, 1 for out, 2 for mode indicator
        if self.logType==1:
            print(s)
            
def alphahexToByte(s):
    #returns an integer equal to the 2-digit alphahex string (a=0, p=f)
    return ((ord(s[0])-97)*16+(ord(s[1])-97))

def byteToAlphahex(b):
    #returns a 2-digit alphahex string from the byte value b.
    return chr((b&15)+97)+chr((b&240)//16+97)
def alphahexToNumber(s,n):
    #returns the unsigned integer conversion from an n digit alphahex string s
    out=0
    for i in range(0,n-1):
        out+=(ord(s[i])-97)*16**(n-i-1)
    return out
def pad(s,n):
    #appends zeros the front of a string until it is n characters long.
    out=s
    while len(out)<n:
        out="0"+out
    return out


#-----------------------------------------------------------------------
class lairCom:
    def __init__(self):
        self.gui=fullUI()
        self.buffer='' #current serial packet
        self.received=[] #array of received serial packets
        self.arduinoPort="COM0"
        self.mode=0
        self.measureCount=0
        self.measureID=0
        self.measureInterval=30
        #put all the measurement functions you want to call in measureDict, they'll be called in order.
        #self.measureDict={0:self.getCC2D25,1:self.getMeasurement,2:self.getM41T83}
        self.measureDict={0:self.getMeasurement}
        self.packetDict={"HT":self.processCC2D25,"M0":self.processMeasurement,"tG":self.processM41T83}
        self.bufferLength=256
        self.updatems=30
        self.updatesec=self.updatems/1000.0
        self.firstFlag=1
        self.loop() #mainloop will return control to loop every 100ms
        self.gui.master.mainloop() #call the interface library's mainloop function
    def loop(self):
        if self.mode==0: #no connection is made
            #mode 0 is entered when there is no serial response.
            #every cycle the program will try and open one.
            self.gui.log("No connection",2)
            if self.measureCount>self.measureInterval/4:
                self.openSerial()
                self.measureCount=0
        if self.mode==1:
            #mode 1 is for when the serial port is connected but a handshake
            #is not established. if it stays in this state indefinitely then
            #possibly the arduino isn't responding correctly.
            self.gui.log("Serial open, awaiting handshake",2)
            if self.measureCount>self.measureInterval/4:
                self.feelSerial()
                self.measureCount=0
        if self.mode==2:
            #mode 2 is the main mode for communication back and forth.
            self.gui.log("Connected to board, ID "+self.instrumentVersion,2) #check whether you are passing a function handle or a function's response. Brackets matter.
            self.main()
        self.measureCount+=1
        self.gui.master.after(self.updatems,self.loop) #return control to gui.
    def main(self):
        #The main function contains program actions, like measurements.
        #The getSerial function is used throughout to sniff for packets.
        #it will return a string containing packet contents, if any
        #are delivered. Packets have a maximum length of bufferLength.
        if self.firstFlag==1: #things to do on the first call of main()
            self.firstFlag=0
            #self.setM41T83(13,11,10,9,8,255,50)
        if self.measureCount>self.measureInterval:
            #print("Starting measurement")
            self.measureDict[self.measureID]()
            self.measureID+=1
            if self.measureID>=len(self.measureDict):
                self.measureID=0
            self.measureCount=0
        self.getSerial()
        self.processSerial() #call every tick
    def processSerial(self):
        while len(self.received)>0:
            s=self.getReceived()
            if s=="":
                return
            if len(s)<2:
                print("Did not process malformed packet")
            tag=s[0:2]
            packet=s[2:]
            print("Processing packet "+packet+" with tag "+tag)
            #s should be a trimmed serial string
            try:
                self.packetDict[tag](packet)
                return
            except KeyError:
                print("Tag not recognized, packet discarded")
                return
    def processCC2D25(self,packet):
        b0=alphahexToByte(packet[-4:-2])
        b1=alphahexToByte(packet[-2:])
        tenperature=(b0*256+b1)/16384*165-40 #TENperature
        print("Temperature in degrees C "+str(tenperature))
        return
    def processM41T83(self,packet):
        print(str(alphahexToByte(packet[0:2])))
        return
    def processMeasurement(self,packet):
        #print(alphahexToNumber(packet[0:3],3))
        v=[]
        for i in range(0,8):
            v.append(alphahexToNumber(packet[i*3:(i*3+3)],3)/204.8)
        try:
            #print(packet[0:3]+","+packet[3:6]+","+packet[6:9]+","+packet[9:12]+","+packet[12:15]+","+packet[15:18]+","+packet[18:21]+","+packet[21:24])
            out="Measured V:"
            out+=str(alphahexToNumber(packet[0:3],3)/204.8)+", "
            out+=str(alphahexToNumber(packet[3:6],3)/204.8)+", "
            out+=str(alphahexToNumber(packet[6:9],3)/204.8)+", "
            out+=str(alphahexToNumber(packet[9:12],3)/204.8)+", "
            out+=str(alphahexToNumber(packet[12:15],3)/204.8)+", "
            out+=str(alphahexToNumber(packet[15:18],3)/204.8)+", "
            out+=str(alphahexToNumber(packet[18:21],3)/204.8)+", "
            out+=str(alphahexToNumber(packet[21:24],3)/204.8)
            print(out)
        except:
            print("Error")
            #handle the bar graph
        self.gui.bars.set_values(v)
        return
    def getReceived(self):
        if len(self.received)>0:
            s=self.received[0]
            if len(self.received)>1:
                self.received=self.received[1:]
            else:
                self.received=[]
            return s
        else:
            return ""
    def getCC2D25(self):
        self.putSerial("HT")
    def setM41T83(self,YY,MM,DD,HH,MN,SS,MS):
        out="tS"+chr(YY+20)+chr(MM+20)+chr(DD+20)+chr(HH+20)+chr(MN+20)+chr(SS+20)+chr(MS+20)
        self.putSerial(out)
        #print(out)
    def getM41T83(self):
        self.putSerial("tG")
    def getMeasurement(self):
        self.putSerial("M0")
    def openSerial(self):
        #This code scans com ports and opens serial connections. If you
        #are planning on multiple serial objects, this code will need revising
        #as it assumes there is only an arduino attached to the computer, an
        #assumption that will have to be fixed.
        
        #if you know the specific port of the arduino, set it here first.
        try:
            self.ch=serial.Serial(self.arduinoPort,9600,timeout=(self.updatesec)/100) #serial channel
            self.mode=1
            print("Opened connection to "+self.arduinoPort)
            return
        except serial.serialutil.SerialException as err:
            self.mode=0
        i=0
        #windows code
        for i in range(0,256):
            try:
                self.ch=serial.Serial("COM"+str(i),9600,timeout=(self.updatesec)) #serial channel
                self.mode=1
                print("Opened connection to COM"+str(i))
                #self.feelSerial()
                return
            except serial.serialutil.SerialException as err:
                self.mode=0
        #linux code
        for i in range(0,255):
            try:
                self.ch=serial.Serial("/dev/ttyUSB"+str(i),9600,timeout=(self.updatesec)) #serial channel
                self.mode=1
                print("Opened connection to /dev/ttyUSB"+str(i))
                #self.feelSerial()
                return
            except serial.serialutil.SerialException as err:
                self.mode=0
    def feelSerial(self):
        #This code feels for a handshake.
        self.putSerial('VV')
        self.getSerial()
        out=self.getReceived()
        if out[0:2]=='VV':
            #retrieve board version
            self.instrumentVersion=out[2:]
            print("Handshake received from board "+self.instrumentVersion)
            self.mode=2
    def closeSerial(self):
        #neatly closing the serial channel is important especially on windows,
        #in case of exceptions. I'm not sure that this code is unbugged.
        try:
            self.ch.close()
            print("closed connection")
            self.mode=0
        except serial.serialutil.SerialException as err:
            self.mode=0
            print("Cannot close serial port, error: "+format(err.strerror))
        except:
            print("Cannot close serial port.")
    def putSerial(self,s):
        #This function should be called when sending serial commands!
        #it encapsulates the packets properly.
        out=s+str(chr(13))
        #s#=str(chr(2))+s+str(chr(13))
        try:
            self.ch.write(out.encode())
        except serial.serialutil.SerialException as err:
            self.mode=0
            print('connection terminated')
        self.gui.log('Serial out >'+out,1)
    def getSerial(self):
        #waits for a packeted (starts with chr(2), ends with chr(13)) to be
        #sent over serial. unpacketed data is added to self.buffer, completed
        #packets are added to the list self.received.
        snag=0
        begun=0
        try:
            while(snag==0):# and len(buffer)<self.bufferLength):
                if self.ch.inWaiting()>0:
                    #the way python handles strings and characters is flat-out
                    #fucking insane. Just so you know.
                    c_buffer=self.ch.read(1)
                    s_buffer=str(c_buffer)
                    #if s_buffer[2:6]=="\\x02":
                    begun=1
                    if begun==1:
                        if s_buffer[2:4]=="\\r":
                            #self.buffer=self.buffer[1:]#snip
                            print("packet received >"+self.buffer)
                            self.received.append(self.buffer)
                            self.buffer=""
                            self.begun=0
                        else:
                            self.buffer=self.buffer+s_buffer[2:3]
                            #if there's a char error (ie a non printed character), you'll just get a slash.
                else:
                    snag=1
        except IOError:
            self.gui.log("Connection lost",2)
            mode=0
'''    def getSerial(self):
        #hopefully just adds a line to received.
        s=self.ch.readline()
        if s!="":
            self.received.append(s)
            #self.getSerial()'''

class App:
    def __init__(self):
        self.com=lairCom()
        self.com.closeSerial()

#print(alphahexToNumber("aba",3))
run=App()
print("Beendet")
