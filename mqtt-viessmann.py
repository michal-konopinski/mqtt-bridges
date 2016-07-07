#!/usr/bin/python
# -*- coding: utf-8 -*-

import serial
import binascii
import mosquitto
from threading import Lock

client = mosquitto.Mosquitto("VCONTROL")
lock=Lock()

def on_connect(mosq, userdata, rc):
    print "on connect rc=",rc
    client.subscribe("/vcontrol/set/TrybPracy",2)
    client.will_set("/vcontrol/$online","OFF",0,True)
    client.publish("/vcontrol/$online","ON",0,True)


ser=serial.Serial('/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A70379CZ-if00-port0',baudrate=4800,bytesize=8,parity=serial.PARITY_EVEN,stopbits=2,timeout=10,xonxoff=0,rtscts=0,dsrdtr=0)
#ser.open()
ser.flushInput()
ser.read()

def waitForTransmission():
    n=ser.read()
    #print len(n)
    if(len(n)==1):
	#print n
	c=ord(n[0])
	if(c==5):
	    ser.write('\x01')
	    return 1
	return 0

def getShort(addr):
    str='\xF7'+chr(addr//256)+chr(addr%256)+chr(2)
    ser.write(str)
    s=ser.read(2)
    return ord(s[0])+ord(s[1])*256

def getSShort(addr):
    ret=getShort(addr)
    if(ret>32767):
        ret=ret-65536
    return ret

def setByte(addr,val):
    str='\xF4'+chr(addr//256)+chr(addr%256)+chr(1)+chr(val%256)
    ser.write(str)
    s=ser.read(1)
    return ord(s[0])

def getByte(addr):
    str='\xF7'+chr(addr//256)+chr(addr%256)+chr(1)
    ser.write(str)
    s=ser.read(1)
    return ord(s[0])

def getInt(addr):
    str='\xF7'+chr(addr//256)+chr(addr%256)+chr(4)
    ser.write(str)
    s=ser.read(4)
    return ord(s[0])+ord(s[1])*256+ord(s[2])*256*256+ord(s[3])*256*256*256


def on_message(mosq, userdata, msg):
    print msg.topic, msg.payload
    if(msg.topic=="/vcontrol/set/TrybPracy"):
        rc=0
        lock.acquire()
        try:
	    rc=setByte(0xB000,int(msg.payload))
        finally:
            lock.release()
	print "rc=",rc

client.on_connect=on_connect
client.on_message=on_message
client.connect("127.0.0.1",1883,60)
client.loop_start()


datapoints=[
(0x0101,getSShort,10.0,'Temperatura zewnętrzna            ','TempZewnetrzna'),
(0x0116,getShort,10.0,'Temperatura wewnętrzna            ','TempWewnetrzna'),
(0x010A,getShort,10.0,'Temperatura zasilania instalacji  ','TempZasilania'),
(0x010B,getShort,10.0,'Temperatura bufora                ','TempBufora'),
(0x010D,getShort,10.0,'Temperatura ciepłej wody          ','TempWody'),
(0x0103,getSShort,10.0,'Temperatura solanki na wejściu    ','TempSolankiWe'),
(0x0105,getShort,10.0,'Temperatura wody na zasilaniu     ','TempWodyZasilanie'),
(0x0106,getShort,10.0,'Temperatura wody na powrocie      ','TempWodyPowrot'),
(0xB000,getByte,1,    'Tryb pracy                        ','TrybPracy'),
(0x2000,getShort,10.0,'Oczekiwana temperatura pokojowa   ','OTempPokojowa'),
(0x2001,getShort,10.0,'Oczekiwana temperatura zredukowana','OTempZredukowana'),
(0x2022,getShort,10.0,'Oczekiwana temperatura party      ','OTempParty'),
(0x0400,getByte,1,    'Stan sprężarki                    ','Sprezarka'),
(0x0402,getByte,1,    'Stan źródła pierwotnego           ','ZrodloPierwotne'),
(0x0404,getByte,1,    'Stan źródła wtórnego              ','ZrodloWtorne'),
(0x040D,getByte,1,    'Stan obiegu A1                    ','ObiegA1'),
(0x0414,getByte,1,    'Stan zaworu 3-dr                  ','Zawor3Dr'),
]
#(0x2006,getShort,10.0,'Poziom krzywej grzewczej          ',''),
#(0x2007,getShort,10.0,'Nachylenie krzywej grzewczej      ',''),


vals={}

while(1):
    lock.acquire()
    rc=0
    try:
        rc=waitForTransmission()
    finally:
        lock.release()
        if(rc>0):
            for x in datapoints:
                topic='/vcontrol/'+x[4]
                lock.acquire()
                value=''
                try:
                    value=str(x[1](x[0])/x[2])
                finally:
                    lock.release()
                if len(value)>0:
                    pub=False
                    if vals.has_key(topic):
                        if vals[topic]!=value:
                            pub=True
                    else:
                        pub=True
                    if pub:
                        vals[topic]=value
                        print topic,value
                        client.publish(topic,value,0,True)



