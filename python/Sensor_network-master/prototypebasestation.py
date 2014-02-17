"""
Remote Sensing Base communication protocol.

Dependencies:
    apscheduler - http://pythonhosted.org/APScheduler/
    xbee python library - https://code.google.com/p/python-xbee/

"""

from xbee import ZigBee
from apscheduler.scheduler import Scheduler
import serial

# Implementation of logging library required
#import logging
#import datetime
import time
from time import gmtime, strftime

# Used to store received messages
import queue

# Serial Port Information
PORT = 'COM5'
BAUD_RATE = 9600

# XBee Address Information
BROADCAST = b'\x00\x00\x00\x00\x00\x00\xFF\xFF'
# This is the 'I don't know' 16 bit address
UNKNOWN = b'\xFF\xFE'

# Store all network keys in list, retreive using index
# network_long = ['\x00\x00\x00\x00\x00\x00\xff\xff']  # etc
# network_short = ['\x00\x00']  # etc

'''Function Definitions'''


def message_received(data):
        """
        Call back Function. When a message is received over the network this
        function will get the data and put it in the Queue
        """
        # Stores the data in the Queue
        #  print(strftime("%Y-%m-%d %H:%M:%S", gmtime()))
        packets.put(data, block=False)
        print('Received Packet at: ' + strftime("%Y-%m-%d %H:%M:%S", gmtime()))


def sendPacket(address_long, address_short, payload):
        """
        Sends a Packet of data to an XBee.

        Inputs:     wddress_long - 64bit destination XBee Address
                    address_short - 16bit destination XBee Address
                    payload - Information to be sent to payload
        """
        print(len(address_long))
        print(len(address_short))
        xbee.send('tx',
                  dest_addr_long=address_long,
                  dest_addr=address_short,
                  data=payload
                  )


def sendQueryPacket():
        """
        Sends a test packet to all XBees on network
        """
        print('Sending Test Packet')
        sendPacket(BROADCAST, UNKNOWN, b'q')


def handlePacket(data):
        """
        Handles a received packet. First determines the packet type and then
        performs
        analysis
        """
        # Determine if received packet is a tx_status packet
        if data['id'] == 'tx_status':
            if ord(data['deliver_status']) != 0:
                print('Transmit error = ')
                print(data['deliver_status'].encode('hex'))

        # Determine if received packet is a data packet
        elif data['id'] == 'rx':
            print(data['rf_data'])
            # len(rxList)  # Do things
            # Detemine if received packet is an undetermined XBee frame
        else:
            print('Unimplemented XBee frame type' + data['id'])


def printpacket(packet):
    '''  This is a random function
    '''
    print(packet)


# Queue in which to store packets when received
packets = queue.Queue()

# Open XBee Serial Port
ser = serial.Serial(PORT, BAUD_RATE)

#------------------Scheduled Tasks -----
sendsched = Scheduler()
sendsched.start()

# Create XBee library API object, which spawns a new thread
xbee = ZigBee(ser, callback=message_received, escaped=True)

# Can schedule tasks such as sending test packet
sendsched.add_interval_job(sendQueryPacket, seconds=15)


# Main thread handles received packets
while True:
        try:
            time.sleep(0.1)
            # Received packets are put into queue by message_received
            if packets.qsize() > 0:
                # Retrieve Packet
                newPacket = packets.get_nowait()
                # Dismantle Packet
                handlePacket(newPacket)
        except KeyboardInterrupt:
            break

# halt() must be called before closing the serial port in order to ensure
#  proper thread shutdown
xbee.halt()
ser.close()
