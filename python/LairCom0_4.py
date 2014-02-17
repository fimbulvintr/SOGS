#Written for python 3
#This library is designed to allow for simple user access to the Lair
#prototype board.
#0_1 First version
#0_1b New handshake listener system
#0_2 display version
#0_3 Accessable version
#0_4 Modified for multiple measurements per file

import tkinter as tk
import os
import serial
from psigraph import barGraph
import datetime
import time
import math

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

def floatToAlphahex(f):
    #returns a sixteen digit alphahex string representing double precision floating point.
    #unfinished.
    hfs=str(float(f).hex())
    #0x     0  .     0      000000    000000
    hf=hfs[2:3]+hfs[4:5]+hfs[5:11]+hfs[11:17]
    if hfs[17:18]=="+":
        if len(hfs[18:])==1:
            pass
        else:
            hf+=hex(hfs)
    else:
        pass

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
    In general, measurements involve calling two functions. You call the request
    function with a string representing the type of measurement you're after -
    in the case of the main gas sensor bank this is
    >>> lc.req("gas")
    which sends a serial packet to the board asking it to take the appropriate
    measurement. Call
    >>> lc.get("gas")
    to retrieve a list of values back. The format of this list is different for
    different measurement controllers, so beware! Calling any of the get functions clears
    the buffer of measurements taken so far, so if you get a blank list it means
    no measurements have been recieved in the meantime. Beware, you MUST have
    called tick inbetween calling the Req and Get functions in order for the
    LairCom object to monitor and retrieve your values.
    '''
    def __init__(self,port=False,verbose=False):
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
        self.verbose=verbose
        self.instrumentVersion=""
        self.loadControllers()
    def loadControllers(self):
        for c in controllerList:
            self.controllers.append(c)
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
    def get(self,name):
        #checks the recieved buffer, if controller name can be used on a packet
        #it is summoned and the processed packet is returned as some kind of object.
        out=""
        if len(self.received)>0:
            c=self.scanControllers(name)
            if c==False:
                print("Name "+name+" does not belong to any installed controller")
                return False
            for r in self.received:
                if r[0:2]==c.header:
                    #the packet is destined for controller c.
                    out=c.parsePacketToData(r[2:])
                    self.received.remove(r) #snip this out of the list
                    break
            if out==False:
                print("Packet "+r+" was parsed and evaluated false.")
                return False
        else:
            if self.verbose==True:
                print("No packets available")
            return False
        if out=="":
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
    def scanControllers(self,name):
        #returns a measurecontroller with that name, or False if none are found.
        out=False
        for c in self.controllers:
            if c.checkName(name):
                out=c
                break
        return out
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
            print("Connection lost",2)
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
    def stampID(self,s):
        #applys a 10-digit ID number to the Arduino
        if len(s)>10:
            print("The stamp length must be less than ten digits")
        else:
            self.serialPut("SS"+s)
    def stampCalibration(self,cid,cLinear,cFactor,cSquare):
        #stamps three floating point numbers into the board
        if type(cLinear)==float():
            pass
            

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
    def parsePacketToData(self,packet):
        #parse the contents of a packet and return it to the calling function in whatever format
        return 0
    def parseDataToString(self,data,delin):
        #converts measurement data made with this controller into a string.
        return ""
    def parseStringToData(self,s,delin):
        #converts a string s into data
        return 0
    def nullData(self):
        #returns null data
        return 0
    def dataID(self,delin):
        return ""

class MCV0(MeasureController):
    def __init__(self):
        self.header="M0"
        self.name="V0"
        self.desc="Returns a list of eight voltages from bank 0"
    def parsePacketToData(self,packet):
    #returns voltages for now.
        v=[]
        for i in range(0,8):
            v.append(alphahexToNumber(packet[i*3:(i*3+3)],3)/204.8)
        return v
    def parseDataToString(self,data,delin):
        #The data argument should be from the data field of a Measurement object
        out=str(data[0])+delin+str(data[1])+delin+str(data[2])+delin+str(data[3])+delin+str(data[4])+delin+str(data[5])+delin+str(data[6])+delin+str(data[7])
        return out
    def parseStringToData(self,s,delin):
        tags=chopString(s,delin,"")
        out=[]
        for t in tags:
            out.append(float(t))
        return out
    def nullData(self):
        return [0,0,0,0,0,0,0,0]
    def dataID(self,delin):
        return "V0"+delin+"V1"+delin+"V2"+delin+"V3"+delin+"V4"+delin+"V5"+delin+"V6"+delin+"V7"

class MCV1(MCV0):
    def __init__(self):
        self.header="M1"
        self.name="V1"
        self.desc="Returns a list of eight voltages from bank 1"

class MCGas(MCV1):
    def __init__(self):
        self.header="M0"
        self.name="gas"
        self.desc="Returns a labelled list of gas voltages"
    def dataID(self,delin):
        return "Battery"+delin+"Pressure"+delin+"LDR"+delin+"CH(5524)"+delin+"NH3(5914)"+delin+"NO2(2714)"+delin+"CO(5525)"+delin+"O3(2610)"

class MCTHB(MCV1):
    def __init__(self):
        self.header="M1"
        self.name="THB"
        self.desc="Returns approximate temperature, humidity and bus voltage ratings"
    def parsePacketToData(self,packet):
    #returns voltages for now.
        v=[]
        v.append((alphahexToNumber(packet[15:18],3)+(alphahexToNumber(packet[18:21],3)))/409.6)#temperature
        v.append((alphahexToNumber(packet[3:6],3)+(alphahexToNumber(packet[6:9],3)))/409.6)#humidity
        v.append((alphahexToNumber(packet[9:12],3)+(alphahexToNumber(packet[12:15],3)))/409.6)#bus
        #now v has voltages.
        #Let's convert this to calibrated values.
        out=[0,0,0]
        out[2]=v[2]#direct voltage reading
        T_Rinert=10000
        T_R25=10000
        T_a=-4.7
        T_V=out[2]
        out[0]=math.log(T_Rinert/T_R25*(T_V/v[1]-1))/math.log((100+T_a)/100)+298
        H_offset=0.826
        H_slope=0.0315
        out[1]=(v[1]-H_offset)/H_slope
        return out
    def parseDataToString(self,data,delin):
        #The data argument should be from the data field of a Measurement object
        out=str(data[0])+delin+str(data[1])+delin+str(data[2])
        return out
    def nullData(self):
        return [0,0,0]
    def dataID(self,delin):
        return "Temperature(K)"+delin+"Humidity(%RH)"+delin+"Bus(V)"

class MCVersion(MeasureController):
    #not loaded by default. Will become useful when taking measurements from multiple board types.
    def __init__(self):
        self.header="VV"
        self.name="version"
        self.desc="Returns a string containing board version number"
    def parsePacketToData(self,packet):
        #This controller is particular to LAir; SOGS and Tinnitus will not be
        #recognized
        if packet[0:4]=="LAir":
            out=packet[4:]
            out=out.strip()
            return out
        return False
    def nullData(self):
        return ""

class LairUI:
    #normal mode: runs a full ui, saves to file every two seconds,
    def __init__(self,mode="normal",delay=2,ui="graph",saveDir="SOGSMeasurements",aggFile="SOGSAggregated",addAggDate=True,MCs=[]):
        self.com=LairCom()
        self.updatems=30 #time between each tick function cal and ui update in milliseconds
        self.aggFile=aggFile #custom aggregation filename
        self.beginDate=datetime.datetime.now()
        self.lastMeasureDate=self.beginDate
        self.addAggDate=addAggDate #boolean whether to add aggregation date onto the end of aggregate file.
        if MCs==[]:
            self.MCs=[]
            for c in self.com.controllers:
                self.MCs.append(c.name)
        else:
            self.MCs=MCs
        self.measList=[False]*len(self.MCs) #measurement list, false when not filled with a Measurement object
        self.measureDelay=delay #time between measurements in seconds
        if ui=="graph":
            self.uid=0
            self.gui=GraphGUI()
        elif ui=="terminal":
            self.uid=1
            self.gui=TermGUI()
        else:
            self.uid=-1
            self.gui=NullGUI()
        if saveDir=="": #Give "" as the savedir string to prevent saving.
            self.dir=""
            self.save=False
        else:
            self.save=True
            self.dir=saveDir
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
            if aggFile!="" and saveDir!="":
                self.aggregate()
        if mode=="null":
            print("Null mode: no loop engaged")
        if mode=="aggregate":
            if aggFile!="" and saveDir!="":
                print("Aggregating files")
                self.aggregate()
            else:
                print("The aggFile and saveDir arguments must not be an empty string for this mode to work")
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
            #check measurement interval
            if (self.lastMeasureDate+datetime.timedelta(seconds=self.measureDelay))<datetime.datetime.now():
                #If there are any unrecorded measurements, save them now.
                #print("New measurement")
                snag=False
                okay=False
                for mci in self.measList:
                    if mci==False:
                        snag=True
                    else:
                        okay=True
                #if there are some unrecorded, save.
                if snag==True and okay==True:
                    #print("Saving partial data file; maybe measurement delay is too low?")
                    for mci in range(len(self.MCs)):
                        if self.measList[mci]==False:
                            self.gui.log("<"+self.MCs[mci]+"> no data found")
                        else:
                            self.gui.log("<"+self.MCs[mci]+"> "+str(self.measList[mci].MC)+" SAVING: "+self.com.scanControllers(self.measList[mci].MC).parseDataToString(self.measList[mci].data,", "))
                            #update the graph ui, if using gas< A DIRTY HACK
                            if self.uid==0 and self.MCs[mci]=="gas":
                                self.gui.bars.set_values(self.measList[mci].data)
                    if self.dir!="":
                        self.saveMeasurements()
                    #empty the measurement array, ready for the next time.
                    for mci in range(len(self.measList)):
                        self.measList[mci]=False
                #prepare to take a new measurement, send requests.
                for mc in self.MCs:
                    h=self.com.req(mc)
                self.lastMeasureDate=datetime.datetime.now()
            #load any measurements received from the board
            for mci in range(len(self.MCs)):
                tmv=self.com.get(self.MCs[mci])
                if tmv!=False and tmv!="":
                    self.measList[mci]=Measurement(tmv,self.MCs[mci],datetime.datetime.now())
            #check to see if the whole measurement array is populated
            snag=False
            for mci in self.measList:
                if mci==False:
                    snag=True
            if snag!=True:
                #if the measure array is populated, display/save all measurements.
                for mci in range(len(self.MCs)):
                    #print(mci)
                    self.gui.log("<"+self.MCs[mci]+"> "+str(self.measList[mci].MC)+" SAVING: "+self.com.scanControllers(self.measList[mci].MC).parseDataToString(self.measList[mci].data,", "))
                    #update the graph ui, if using gas< A DIRTY HACK
                    if self.uid==0 and self.MCs[mci]=="gas":
                        self.gui.bars.set_values(self.measList[mci].data)
                if self.dir!="":
                    self.saveMeasurements()
                #empty the measurement array, ready for the next time.
                for mci in range(len(self.measList)):
                    self.measList[mci]=False
        #Engage the tk.
        if self.uid!=-1:
            self.gui.master.after(self.updatems,self.normalMain)
    def saveMeasurements(self):
        #Saves everything from the self.measList array into a new file.
        dt=datetime.datetime.now()
        if not os.path.exists(self.dir+'/'+dt.date().isoformat()):
            os.makedirs(self.dir+"/"+dt.date().isoformat())
        s=dt.time().isoformat().replace(":","-")
        s=s.replace(".","_")
        file=open(self.dir+"/"+dt.date().isoformat()+"/"+s+".txt","a+")
        file.write("comment#\n")
        file.write("delineator/\n")
        file.write("#This is a data file for SOGS saved at date/time\n")
        file.write("epoch/"+dt.date().isoformat()+"/"+dt.time().isoformat()+"\n")
        file.write("kind/"+"SOGSdata"+"\n")
        for meas in self.measList:
            if meas!=False:
                file.write("m/"+meas.MC+"/"+meas.dtToD()+"/"+meas.dtToT()+"/"+self.com.scanControllers(meas.MC).parseDataToString(meas.data,"/")+"\n")
        file.close()
    def aggregate(self):
        dirlist=os.walk(self.dir)
        measurements=[[]] #A list of measurement lists!
        outmeasurements=[[]] #A list of measurement lists!
        for i in range(len(self.com.controllers)-1):
            measurements.append([])
            outmeasurements.append([])
        for (aggpath1,scrap,aggpath2) in dirlist:
            for aggpathc in aggpath2:
                if aggpathc[-3:]=="txt":
                    print("opening "+aggpath1+"/"+aggpathc)
                    try:
                        aggfile=open(aggpath1+"/"+aggpathc,"r")
                        snag=0
                        comment=""
                        delin=""
                        outkind=""
                        outdate=""
                        outtime=""
                        out=[]#an array of measurements read from file
                        tags=[]
                        while snag==0:
                            line=aggfile.readline()
                            if line[-1:]=="\n":
                                line=line[:-1] #strip off the newline character if there is one.
                            if line=="":
                                snag=1#exit file on empty line
                            else:
                                if comment=="" or delin=="":
                                    if line[:-1]=="comment":
                                        comment=line[-1:]
                                    if line[:-1]=="delineator":
                                        delin=line[-1:]
                                else:
                                    tags=chopString(line,delin,comment)
                                    if len(tags)>0:
                                        if tags[0]=="epoch":
                                            outdate=str(tags[1])#default date and time
                                            outtime=str(tags[2])
                                            if len(out)==0:#don't fill this twice if you see two epochs for some reason.
                                                for c in self.com.controllers:
                                                    #fill the measurement array with null data
                                                    out.append(Measurement(c.nullData(),c.name,outdate+"T"+outtime))
                                        if tags[0]=="kind":
                                            outkind=str(tags[1])
                                        if tags[0]=="m":
                                            #This is going to be somewhat complicated.
                                            mc=-1
                                            for c in range(len(self.com.controllers)):#Identify the controller being used
                                                if self.com.controllers[c].checkName(tags[1]):
                                                    mc=c
                                            if mc!=-1: #Make a measurement from the file's data and add it to the out array.
                                                ttags=tags[4:] #construct a temporary string containing all remaining tags
                                                tstring=""
                                                for t in range(len(ttags)):
                                                    tstring+=ttags[t]+delin
                                                tstring=tstring[:-1]
                                                out[mc]=Measurement(self.com.controllers[mc].parseStringToData(tstring,delin),self.com.controllers[mc].name,tags[2]+"T"+tags[3])
                                            else:
                                                #your stuff wasn't recognized.
                                                pass
                        aggfile.close()
                        if comment!='' and delin!='' and outkind=="SOGSdata":
                            for c in range(len(out)):
                                measurements[c].append(out[c])
                        else:
                            print("Unrecognized file: "+aggpath1+"/"+aggpathc)
                    except UnicodeDecodeError:
                        print("Unparseable character in file: "+aggpath1+"/"+aggpathc)
                else:
                    print("Skipped non-text file"+aggpath1+"/"+aggpathc)
        #looks like I'm going to have to run sorted multiple times.
        for c in range(len(self.com.controllers)):
            outmeasurements[c]=sorted(measurements[c],key=lambda Measurement:Measurement.datetime())
        if self.addAggDate==True:
            s=datetime.datetime.now().isoformat().replace(":","-")
            s=s.replace(".","_")
            outfile=open(self.aggFile+s+".csv",'w')
        else:
            outfile=open(self.aggFile+".csv",'w')
        outdel=",\t"
        outfile.write('#SOGS aggregate measurements CSV\n')
        outfile.write('#Aggregated on '+datetime.datetime.now().date().isoformat()+"_"+datetime.datetime.now().time().isoformat()+"\n")
        outline=""
        #now the aggregate file processing begins.
        for c in range(len(self.com.controllers)):
            outline+='MC'+outdel+"Date"+outdel+"Time"+outdel+self.com.controllers[c].dataID(outdel)+outdel
        outline=outline[:-len(outdel)]+"\n"
        outfile.write(outline)
        for c in range(len(outmeasurements[0])):#iterate for as many measurements as it can find.
            outline=""
            for tmc in range(len(outmeasurements)):
                meas=outmeasurements[tmc][c]
                outline+=meas.MC+outdel+meas.dtToD()+outdel+meas.dtToT()+outdel+self.com.scanControllers(meas.MC).parseDataToString(meas.data,outdel)+outdel
            outline=outline[:-len(outdel)]+"\n"
            outfile.write(outline)
        outfile.close()

def chopString(_line,delin,comment):
    #strips comments, returns a string array of delineator seperated values.
    out=[]
    snag=0
    line=_line
    if comment!="":
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
    #stores a measurement of a single type.
    def __init__(self,data=False,MC="",dt=datetime.datetime.now()):
        if str(type(MC))=="<class 'str'>":
            self.dt=dt
            self.MC=MC#the name of the measure controller
            self.data=data
        else:
            raise "You need to load a measure controller's name string rather than "+str(MC)
    def datetime(self):
        return self.dt
    def dtToT(self):#convert datetime string/object to time string
        if str(type(self.dt))=="<class 'str'>":
            return self.dt[self.dt.find("T")+1:]
        else:
            return self.dt.time().isoformat()
    def dtToD(self):#convert datetime string/object to date string
        if str(type(self.dt))=="<class 'str'>":
            return self.dt[:self.dt.find("T")]
        else:
            return self.dt.date().isoformat()

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

#The default loaded controllers. Every measure controller that isn't on this list must
#be loaded manually. If you make a custom controller, use the LairCom object's loadController(c)
#function to add it to this list. The list is used by the aggregate function, so if something
#isn't on this list it will be ignored during aggregation.
controllerList=[MCGas(),MCTHB()]
