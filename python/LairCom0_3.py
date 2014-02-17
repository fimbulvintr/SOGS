#Written for python 3
#This library is designed to allow for simple user access to the Lair
#prototype board.
#0-1 First version
#0-1b New handshake listener system
#0-2 display version
#0-3 Accessable version

import tkinter as tk
import os
import serial
from psigraph import barGraph
import datetime
import time

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

class LairCom:
    #This object handles communication over the serial port between the
    #board and the PC. It does not do any analysis; this job should be done
    #by the controlling application.
    '''
    There are three important functions within this object: __init__,
    loadController and tick.
    __init__() is of course called automatically whenever a LairCom object is
    created in your program, for example using the following
    lc=LairCom()
    Optionally the constructor can be called with the string ID of the port that
    the arduino is connected to, for example
    >>> lc=LairCom("COM1")
    however you should only need to do this if you have multiple arduinos going
    into the same PC.
    Call tick() maybe every half second. This function is vital for updating and
    monitoring
    the serial connection with the board. If you do not call tick at least three
    times before attempting communication, you will end up not getting any data.
    the loadController function should be passed a controller object, like so:
    >>> c=MCGas()
    >>> lc.loadController(c)
    Each controller object contains information on how to parse and communicate
    with a different subsystem on the actual Lair board itself. A bunch of
    controllers are loaded automatically on startup, but you can clear these
    out with clearControllers() and just load the ones you need afterward.
    Writing your own controllers isn't too difficult; they're just classes with
    four functions in them. Make sure they inherit from the MeasureController
    object.
    The check() function will return the current status of the connection as
    a number:
    0 = No serial connection made.
    1 = Serial connection made, attempting to identify board
    2 = Board identified as Lair, now ready to use.
    Call the retrieve() function to return a list of tuples representing
    strings transmitted or recieved by the PC. Each tuple has two parts, the
    first being a string and the second being a number - 0 if the string was
    transmitted from the PC, 1 if the string was recieved by the PC. After
    calling retrieve, the retrieve buffer is cleared.
    In general, measurements involve calling two functions. You call the request
    function with a string representing the type of measurement you're after -
    in the case of the main gas sensor bank this is
    >>> lc.req("gas")
    which sends a serial packet to the board asking it to take the appropriate
    measurement. Call
    >>> lc.get("gas")
    to retrieve a list of values back. The format of this list is different for
    different measurements, so beware! Calling any of the get functions clears
    the buffer of measurements taken so far, so if you get a blank list it means
    no measurements have been recieved in the meantime. Beware, you MUST have
    called tick inbetween calling the Req and Get functions in order for the
    LairCom object to monitor and retrieve your values.
    '''
    def __init__(self,port=False):
        if str(type(port))=="<class 'str'>":
            self.arduinoPort=port
        else:
            self.arduinoPort=""
        self.messageBuffer=[] #log of input/output
        self.received=[] #array of received serial packets
        self.buffer="" #preencapsulated serial string
        self.controllers=[]
        self.bufferLength=256
        self.messageBufferLength=1000 #maximum number of messages to save
        self.firstFlag=1
        self.updateSec=1 #affects serial timeout
        self.mode=0
        self.verbose=False
        self.instrumentVersion=""
        #load up dem controllers
        self.loadController(MCGas())
        self.loadController(MCVersion())
    def loadController(self,c):
        self.controllers.append(c)
    def clearControllers(self):
        self.controllers=[]
    def listControllers(self):
        for c in self.controllers:
            print(c.name+":")
            print(c.desc)
    def tick(self):
        if self.mode==0: #no connection is made
            #mode 0 is entered when there is no serial response.
            #every cycle the program will try and open one.
            self.serialOpen()
        if self.mode==1:
            #mode 1 is for when the serial port is connected but a handshake
            #is not established. if it stays in this state indefinitely then
            #possibly the arduino isn't responding correctly.
            self.serialFeel()
        if self.mode==2:
            #mode 2 is the main mode for communication back and forth.
            self.main()
        if len(self.messageBuffer)>self.messageBufferLength:
            #snip off the oldest message to save memory.
            self.messageBuffer=self.messageBuffer[1:]
    def main(self):
        self.serialGet()
        #self.serialProcess()
    def get(self,name):
        #checks the recieved buffer, if controller name can be used on a packet
        #it is summoned and the processed packet is returned as some kind of object.
        header=""
        out=""
        if len(self.received)>0:
            for c in self.controllers:
                if c.checkName(name):
                    header=c.header
                    break
            if header=="":
                print("Name "+name+" does not belong to any installed controller")
                return False
            for r in self.received:
                if r[0:2]==header:
                    #the packet is destined for controller c.
                    out=c.parse(r[2:])
                    self.received.remove(r) #snip this out of the list
                    break
            if out==False:
                print("Packet "+r+" was parsed and evaluated false.")
                return False
        else:
            if self.verbose==True:
                print("No packets available")
            return False
        return out
    def req(self,name):
        if self.mode>=1:
            for c in self.controllers:
                if c.checkName(name):
                    out=self.serialPut(c.req())
                    return out
            print("argument was not recognized as a valid command.")
            return False
    def serialProcess(self):
        while len(self.received)>0:
            s=self.getReceived()
            if len(s)<2:
                print("Malformed packet "+s)
            tag=s[0:2]
            packet=s[2:]
            for c in controllers:
                if c.checkHeader(tag):
                    v=c.parse(packet)
                    return v
            print("Tag "+tag+" not recognized, packet "+packet+"discarded")
    def serialOpen(self):
        #This code scans com ports and opens serial connections. If you
        #are planning on multiple serial objects, this code will need revising
        #as it assumes there is only an arduino attached to the computer, an
        #assumption that will have to be fixed.
        
        #if you know the specific port of the arduino, set it here first.
        try:
            self.ch=serial.Serial(self.arduinoPort,9600,timeout=(self.updateSec)/100) #serial channel
            self.mode=1
            print("Opened connection to "+self.arduinoPort)
            return
        except serial.serialutil.SerialException as err:
            self.mode=0
        i=0
        #windows code
        for i in range(0,256):
            try:
                self.ch=serial.Serial("COM"+str(i),9600,timeout=(self.updateSec)) #serial channel
                self.mode=1
                print("Opened connection to COM"+str(i))
                #self.feelSerial()
                return
            except serial.serialutil.SerialException as err:
                self.mode=0
        #linux code
        for i in range(0,255):
            try:
                self.ch=serial.Serial("/dev/ttyUSB"+str(i),9600,timeout=(self.updateSec)) #serial channel
                self.mode=1
                print("Opened connection to /dev/ttyUSB"+str(i))
                #self.feelSerial()
                return
            except serial.serialutil.SerialException as err:
                self.mode=0
    def serialFeel(self):
        #This code feels for a handshake.
        self.serialPut('VV')
        self.serialGet()
        out=self.getReceived()
        if out[0:2]=='VV':
            #retrieve board version
            self.instrumentVersion=out[2:]
            print("Handshake received from board "+self.instrumentVersion)
            self.mode=2
    def serialGet(self):
        #waits for a packeted (ends with chr(13)) string to be
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
                            if self.verbose==True:
                                print("packet received >"+self.buffer)
                            self.received.append(self.buffer)
                            self.messageBuffer.append((self.buffer,1))
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
    def serialPut(self,s):
        #This function should be called when sending serial commands!
        #it encapsulates the packets properly.
        #Returns true if the packet was sent successfully, false otherwise.
        out=s+str(chr(13))
        #s#=str(chr(2))+s+str(chr(13))
        try:
            self.ch.write(out.encode())
            self.messageBuffer.append((s,0))
            return True
        except serial.serialutil.SerialException as err:
            self.mode=0
            print('connection terminated')
            return False
    def getReceived(self):
        #does not scan the messageBuffer.
        #Returns the oldest received packet, and erases it from the queue.
        if len(self.received)>0:
            s=self.received[0]
            if len(self.received)>1:
                self.received=self.received[1:]
            else:
                self.received=[]
            return s
        else:
            return ""

class MeasureController:
    #A controller
    def __init__(self):
        #The header is sent at the beginning of a packet. It should be unique.
        #Name is used only in the python scripts and should also be unique to
        #each module.
        self.header=""
        self.name=""
        self.desc="Returns zero"
    def checkHeader(self,header):
        #Check to see if a packet header is for this module, return true if so
        if header==self.header:
            return True
        return False
    def checkName(self,name):
        #Check to see if a req/get string is for this module, return true if so
        if name==self.name:
            return True
        return False
    def req(self,aux=0):
        #Returns the string that must be transmitted to initiate a measurement.
        #aux is optional but may contain additional information if desired.
        return self.header
    def parse(self,packet):
        #parse the contents of a packet and return it to the calling function.
        return 0

class MCGas(MeasureController):
    def __init__(self):
        self.header="M0"
        self.name="gas"
        self.desc="Returns a list of eight numbers"
    def parse(self,packet):
    #returns voltages for now.
        v=[]
        for i in range(0,8):
            v.append(alphahexToNumber(packet[i*3:(i*3+3)],3)/204.8)
        return v

class MCVersion(MeasureController):
    def __init__(self):
        self.header="VV"
        self.name="version"
        self.desc="Returns a string containing board version number"
    def parse(self,packet):
        #This controller is particular to LAir; SOGS and Tinnitus will not be
        #recognized
        if packet[0:4]=="LAir":
            out=packet[4:]
            out=out.strip()
            return out
        return False

class LairUI:
    #normal mode: runs a full ui, saves to file every two seconds,
    def __init__(self,mode="normal",delay=2,ui="graph",saveDir="lairMeasurements",aggFile="lairAggregated",addAggDate=True):
        self.com=LairCom()
        self.updatems=30
        self.aggFile=aggFile
        self.beginDate=datetime.datetime.now()
        self.lastMeasureDate=self.beginDate
        self.addAggDate=addAggDate
        if ui=="graph":
            self.uid=0
            self.gui=GraphGUI()
        elif ui=="terminal":
            self.uid=1
            self.gui=TermGUI()
        else:
            self.uid=-1
            self.gui=NullGUI()
        if saveDir=="none": #Give "none" as the savedir string to prevent saving.
            self.dir=""
            self.save=False
        else:
            self.save=True
            self.dir=saveDir
        self.measureDelay=delay
        if mode=="normal":
            if self.uid!=-1:
                self.normalMain()
                self.gui.master.mainloop()
            else:
                try:
                    while True:
                        self.normalMain()
                except KeyboardInterrupt:
                    print("beendet")
        if mode=="readout":
            self.readoutMain()
        if mode=="null":
            print("Null mode: no loop engaged")
        else:
            if aggFile!="none" and saveDir!="none":
                self.aggregate(self.aggFile)
    def normalMain(self):
        if self.uid==-1:
            time.sleep(self.updatems/1000)
        self.com.tick()
        if self.com.mode==0:
            self.gui.log("No connection",2)
        if self.com.mode==1:
            self.gui.log("Serial open, awaiting handshake",2)
        if self.com.mode==2:
            self.gui.log("Connected to board ID "+self.com.instrumentVersion,2)
            if (self.lastMeasureDate+datetime.timedelta(seconds=self.measureDelay))<datetime.datetime.now():
                #take a measurement
                print("requested")
                self.com.req("gas")
                self.lastMeasureDate=datetime.datetime.now()
            v=self.com.get("gas")
            if v!=False and v!="":
                self.gui.log("Voltages "+str(v),0)
                if self.dir!="":
                    self.saveMeasurement(v,datetime.datetime.now())
                v=False
        #Engage the tk.
        if self.uid!=-1:
            self.gui.master.after(self.updatems,self.normalMain)
    def readoutMain(self):
        try:
            while True:
                time.sleep(self.measureDelay)
                self.com.tick()
                self.com.req("gas")
                v=self.com.get("gas")
                if v!=False and v!="":
                    self.gui.log("Voltages "+str(v),0)
                    v=False
        except KeyboardInterrupt:
            print("Beendet")
    def saveMeasurement(self,v,dt):
        if not os.path.exists(self.dir+'/'+dt.date().isoformat()):
            os.makedirs(self.dir+"/"+dt.date().isoformat())
        s=dt.time().isoformat().replace(":","-")
        s=s.replace(".","_")
        file=open(self.dir+"/"+dt.date().isoformat()+"/"+s,"a+")
        file.write("comment#\n")
        file.write("delineator/\n")
        file.write("#This is a data file for SOGS recorded on\n")
        file.write("date/"+dt.date().isoformat()+"\n")
        file.write("#at time\n")
        file.write("time/"+dt.time().isoformat()+"\n")
        file.write("v/"+str(v[0])+"/"+str(v[1])+"/"+str(v[2])+"/"+str(v[3])+"/"+str(v[4])+"/"+str(v[5])+"/"+str(v[6])+"/"+str(v[7])+"\n")
        file.close()
    def aggregate(self,path):
        dirlist=os.walk(self.dir)
        measurements=[]
        for (aggpath1,scrap,aggpath2) in dirlist:
            for aggpathc in aggpath2:
                aggfile=open(aggpath1+"/"+aggpathc,"r")
                snag=0
                comment=""
                delin=""
                tags=[]
                #<!!!!
                while snag==0:
                    line=aggfile.readline()
                    if line[-1:]=="\n":
                        line=line[:-1] #strip off the newline character if there is one.
                    if line=="":
                        snag=1
                    else:
                        if comment=="" or delin=="":
                            if line[:-1]=="comment":
                                comment=line[-1:]
                            if line[:-1]=="delineator":
                                delin=line[-1:]
                        else:
                            tags=chopString(line,delin,comment)
                            if len(tags)>0:
                                if tags[0]=="date":
                                    outdate=str(tags[1])
                                if tags[0]=="time":
                                    outtime=str(tags[1])
                                if tags[0]=="v":
                                    out=[float(tags[1]), float(tags[2]), float(tags[3]), float(tags[4]), float(tags[5]), float(tags[6]), float(tags[7]), float(tags[8])]
                aggfile.close()
                if comment!='' and delin!='':
                    measurements.append(Measurement(out,outdate+"T"+outtime))
        outmeasurements=sorted(measurements,key=lambda Measurement:Measurement.datetime())
        if self.addAggDate==True:
            s=datetime.datetime.now().isoformat().replace(":","-")
            s=s.replace(".","_")
            outfile=open(path+s+".csv",'w')
        else:
            outfile=open(path+".csv",'w')
        outdel=",\t"
        outfile.write('#SOGS aggregate measurements CSV\n')
        outfile.write('#Date_and_time'+outdel+'Ch0'+outdel+'Ch1'+outdel+'Ch2'+outdel+'Ch3'+outdel+'Ch4'+outdel+'Ch5'+outdel+'Ch6'+outdel+'Ch7\n')
        for meas in outmeasurements:
            outfile.write(meas.dt+outdel+str(meas.v[0])+outdel+str(meas.v[1])+outdel+str(meas.v[2])+outdel+str(meas.v[3])+outdel+str(meas.v[4])+outdel+str(meas.v[5])+outdel+str(meas.v[6])+outdel+str(meas.v[7])+"\n")
        outfile.close()

def chopString(_line,delin,comment):
    #strips comments, returns a string array of delineator seperated values.
    out=[]
    snag=0
    line=_line
    if line.find(comment)>-1:
        line=line[:line.find(comment)]
    if line!="":
        while snag==0:
            if line.find(delin)>-1:
                out.append(line[:line.find(delin)])
                line=line[line.find(delin)+1:]
            else:
                out.append(line)
                snag=1
    return out


class Measurement:
    def __init__(self):
        self.dt=datetime()
        self.v=[0,0,0,0,0,0,0,0]
    def __init__(self,v):
        self.dt=datetime()
        self.v=v
    def __init__(self,v,dt):
        self.dt=dt
        self.v=v
    def datetime(self):
        return self.dt

class NullGUI:
    def __init__(self):
        self.logType=1
    def log(self,s,sw=0):
        #sw=0 for in, 1 for out
        if self.logType==1 and sw!=2:
            print(s)
        
class TermGUI:
    '''
    This object is a container for tkinter ui objects and contains no program logic.
    Some of its fields are called from the lairCom object and so it must not be ommitted.
    '''
    def __init__(self):
        self.logType=1#can be 0 for no logging, 1 for print logging or 2 for ui logging
        self.master=tk.Tk()
        self.alarmid=0
        self.initWidgets()
    def initWidgets(self):
        self.frame=tk.Frame(self.master)
        self.frame.pack(expand=1,fill=tk.BOTH)
        self.messageFrame=tk.Frame(self.frame)
        self.messageFrame.pack(side=tk.TOP,expand=1,fill=tk.BOTH)
        self.controlFrame=tk.Frame(self.frame)
        self.controlFrame.pack(side=tk.BOTTOM,expand=1,fill=tk.BOTH)
        self.terminalFrame=tk.Frame(self.messageFrame)
        self.terminalFrame.pack(side=tk.BOTTOM,expand=1,fill=tk.BOTH)
        self.outIndVar=tk.StringVar()
        self.outInd=tk.Label(self.messageFrame,textvariable=self.outIndVar)
        self.outInd.pack(side=tk.BOTTOM)
        self.inIndVar=tk.StringVar()
        self.inInd=tk.Label(self.messageFrame,textvariable=self.inIndVar)
        self.inInd.pack(side=tk.BOTTOM)
        self.modeIndVar=tk.StringVar()
        self.modeInd=tk.Label(self.messageFrame,textvariable=self.modeIndVar)
        self.modeInd.pack(side=tk.BOTTOM)
        #terminal
        self.terminalScroll=tk.Scrollbar(self.terminalFrame,orient=tk.VERTICAL)
        self.terminal=tk.Listbox(self.terminalFrame,yscrollcommand=self.terminalScroll.set)
        self.terminalScroll.config(command=self.terminal.yview)
        self.terminalScroll.pack(side=tk.RIGHT,expand=1,fill=tk.Y)
        self.terminal.pack(side=tk.LEFT,expand=1,fill=tk.BOTH)
    def log(self,s,sw=0):
        #sw=0 for in, 1 for out
        if self.logType==1 and sw!=2:
            print(s)
        if sw==0:
            self.inIndVar.set(s)
        elif sw==1:
            self.outIndVar.set(s)
        elif sw==2:
            self.modeIndVar.set(s)


class GraphGUI:
    '''
    This object is a container for tkinter ui objects and contains no program logic.
    Some of its fields are called from the lairCom object and so it must not be ommitted.
    '''
    def __init__(self):
        self.logType=1#can be 0 for no logging, 1 for print logging or 2 for ui logging
        self.master=tk.Tk()
        self.alarmid=0
        self.initWidgets()
    def initWidgets(self):
        self.frame=tk.Frame(self.master)
        self.frame.pack(expand=1,fill=tk.BOTH)
        self.messageFrame=tk.Frame(self.frame)
        self.messageFrame.pack(side=tk.TOP,expand=1,fill=tk.BOTH)
        self.controlFrame=tk.Frame(self.frame)
        self.controlFrame.pack(side=tk.BOTTOM,expand=1,fill=tk.BOTH)
        self.terminalFrame=tk.Frame(self.messageFrame)
        self.terminalFrame.pack(side=tk.BOTTOM,expand=1,fill=tk.BOTH)
        self.outIndVar=tk.StringVar()
        self.outInd=tk.Label(self.messageFrame,textvariable=self.outIndVar)
        self.outInd.pack(side=tk.BOTTOM)
        self.inIndVar=tk.StringVar()
        self.inInd=tk.Label(self.messageFrame,textvariable=self.inIndVar)
        self.inInd.pack(side=tk.BOTTOM)
        self.modeIndVar=tk.StringVar()
        self.modeInd=tk.Label(self.messageFrame,textvariable=self.modeIndVar)
        self.modeInd.pack(side=tk.BOTTOM)
        #terminal
        self.terminalScroll=tk.Scrollbar(self.terminalFrame,orient=tk.VERTICAL)
        self.terminal=tk.Listbox(self.terminalFrame,yscrollcommand=self.terminalScroll.set)
        self.terminalScroll.config(command=self.terminal.yview)
        self.terminalScroll.pack(side=tk.RIGHT,expand=1,fill=tk.Y)
        self.terminal.pack(side=tk.LEFT,expand=1,fill=tk.BOTH)
        #graph
        self.graphWindow=tk.Toplevel(self.master)
        self.graphCanvas=tk.Canvas(self.graphWindow,width=1024,height=620)
        self.graphCanvas.pack()
        self.bars=barGraph(self.graphCanvas,8)
        self.bars.prep(50,50,970,570,[0,1,2,3,4,5])
        self.bars.set_yunits("V")
        self.bars.set_xlabels(["BCR","Pa","LDR","CH","NH3","NO2","CO","O3"])
    def log(self,s,sw=0):
        #sw=0 for in, 1 for out
        if self.logType==1 and sw!=2:
            print(s)
        if sw==0:
            self.inIndVar.set(s)
        elif sw==1:
            self.outIndVar.set(s)
        elif sw==2:
            self.modeIndVar.set(s)
