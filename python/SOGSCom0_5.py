#Written for python 3
#This library is designed to allow for simple user access to the Lair
#prototype board.
#0_1 First version
#0_1b New handshake listener system
#0_2 display version
#0_3 Accessable version
#0_4 Modified for multiple measurements per file
#0_5 Changed name to SOGSCom, added multiple sensor control

import tkinter as tk
import os
import serial
from psigraph import barGraph
import datetime
import time
import math




class Board:
    def __init__(self,nameID):
        #boards are referred to by name.
        self.instruments=[]
        self.slots=[False,False,False,False]
        #self.controller=Controller()
        self.nameID=nameID
    def loadInstrument(self,instrument,nameID,slot=-1):
        try:
            self.setSlot(slot,instrument)
        except:
            print("The slot "+slot+" requested by "+instrument.nameID+" is already in use by instrument "+slots[slot].nameID)
            raise Exception
        self.instruments.append(instrument)
    def clearInstruments(self):
        pass
    def removeInstrument(self,nameID):
        pass
    def setSlot(self,slot,instrument):
        if slots[slot]!=False:
            raise slots[slot]
        slots[slot]=instrument
        instrument.slot=slot
    def powerAux1(self,on=True):
        pass
    def powerAux2(self,on=True):
        pass
    def powerRadio(self,on=True):
        pass
    def powerComputer(self,on=True):
        pass
    def powerSD(self,on=True):
        pass
    def useSD(self,on=True):
        pass
    def useEEPROM(self,on=True):
        pass
    def getMeasurements(self,instrumentName,startTime,stopTime=datetime.datetime.now()):
        pass
    def clockSet(self,time):
        pass
    def clockGet(self):
        pass
    def clockWake(self):
        pass
    def enableShutdown(self,on=True):
        pass
    def measure(self,nameID):
        #takes a single measurement with the named instrument.
        pass
    def get(self,nameID):
        #when measurements are finished, they are placed in the measurements list.
        #calling this function with an instrument name will scan that list
        #and return the oldest measurement.
        pass
    def tick(self):
        pass

class Conduit:
    #conduits are transparent; their functions are only called by board and
    #hub objects. The user can just ignore them, beyond selecting the correct
    #one for their purposes.
    def __init__(self,conduitID=""):
        self.bufferPacketIn=[]
        self.bufferPacketOut=[]
        self.state=0 #By default the state variable is: 0 for no connection,
                #                       1 for connection established,
                #                       2 for handshake received.
        self.conduitID=conduitID #this string might contain radio ID or COM port number.
    def packetTransmit(self,packet):
        #call to transmit a string packet.
        pass
    def packetRetrieve(self,instrument=False):
        #Retrieves the oldest packet in bufferPacketIn. If an instrument is specified,
        #the oldest packet belonging to that instrument will be retrieved instead.
        pass
    def tick(self):
        #called every frame to handle incoming data, appends new data from the
        #board onto the bufferPacket array. This buffer contains strings.
        #Packet interpretation is left to the hub object. This function should also
        #handle connection and disconnection.
        pass

class ConduitRPiSerialArduino(Conduit):
    #If this program is running on a Raspberry Pi that has a direct
    #connection to the arduino serial lines, this conduit can be used.
    pass
class ConduitRPiDirect(Conduit):
    #If this program is running on an RPi connected to the board and this device
    #needs to control things directly without an arduino, use this conduit.
    pass
class ConduitBluetooth(Conduit):
    #If the program is running on a hub and you want to connect to a board
    #via bluetooth, use this conduit.
    pass
class ConduitXBeeNetwork(Conduit):
    #If this program is running on a hub connected to an XBee as the base station
    #for a swarm of sensors, use this conduit.
    pass
class ConduitUSBSerial(Conduit):
    #If this program is running on any PC or RPi that is connected to the board
    #via a USB/UART adapter on an arduino, use this conduit.
    pass

class Instrument:
    def __init__(self,nameID):
        #instruments are referred to by name, and slot.
        pass
class InstrumentPea(Instrument):
    def __init__(self,nameID):
        pass
class InstrumentAlphasense(Instrument):
    def __init__(self,nameID):
        pass
class InstrumentKLASP(Instrument):
    def __init__(self,nameID):
        pass
class InstrumentHTP(Instrument):
    def __init__(self,nameID):
        pass
class InstrumentBatterySolar(Instrument):
    def __init__(self,nameID):
        pass

class Measurement:
    def __init__(self,instrument):
        #instrument should be a new Instrument object. It only represents the
        #class of object.
        self.instrument=instrument
        self.sensorTime=datetime()
        self.localTime=datetime()

class Hub:
    #This is the main object around which all others are based. The hub
    #represents the controlling computer. Board can be added to it through
    #conduits, and instruments are then added onto the boards.
    def __init__(self):
        self.boards=[]
    def boardCreate(self,boardID,conduit):
        board=board(boardID)
        board.conduit=conduit
        self.boards.append(board)
    def loadInstrument(self,boardID,instrument):
        board=scanList(self.boards,boardID)
        board.loadInstrument(instrument)
    def loadInstruments(self,boardID,instruments):
        #make sure instruments is an array.
        board=scanList(self.boards,boardID)
        board.instruments=instruments
    def boardStart(self,nameID,interval,startTime,stopTime):
        pass
    def boardStop(self,nameID):
        pass
    def measure(self,boardID,instrumentID):
        #requests the board take a single measurement from the specified instrument.
        pass
    def get(self,boardID,instrumentID,erase=False):
        #downloads all measurements from a specific instrument from the board.
        #returns a measurement array.
        pass
    def getAll(self,boardID,erase=False):
        #downloads all measurements from all instruments from the board.
        #returns a measurement array.
        pass
    def tick(self):
        pass

def scanListForIndex(l,nameID):
    #returns the first member of a list that has the nameID specified.
    c=0
    for cl in l:
        if nameID==cl.nameID:
            break
        c++
    return c

def scanList(l,nameID):
    #returns the first member of a list that has the nameID specified.
    for cl in l:
        if nameID==cl.nameID:
            break
    return cl























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





