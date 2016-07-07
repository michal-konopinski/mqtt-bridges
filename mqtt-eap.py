#!/usr/bin/python
# -*- coding: utf-8 -*-.




import serial
import sys
import time
import collections
import copy
import array
import json
import re
import datetime
import BaseHTTPServer
import mosquitto
from datetime import datetime

vals={}


METER_NUMBER = '323.0014755'

client = mosquitto.Mosquitto("EAP")


def calcBcc(data):
    bcc = 0
    init = True
    for b in data:
	if init:
	    if(b == '\01' or b == '\x02'):
		init = False
		continue
	bcc = bcc ^ ord(b)
	if b == '\x03':
	    return chr(bcc)
    raise "Wrong data format"

def addBcc(data):
    return data + calcBcc(data)


def pub(type,value):
    topic="/meter/"+type
    print type,value
    v=str(float(value))
    public=False
    if vals.has_key(topic):
        if vals[topic]!=v:
            public=True
    else:
        public=True
    if public:
        vals[topic]=v
        print topic,v
        client.publish(topic,v,0,True)



ser = serial.Serial('/dev/ttyS2',
	baudrate=4800,        # baud rate
	bytesize=7,           # number of data bits
	parity=serial.PARITY_EVEN,        # enable parity checking
	stopbits=1,           # number of stop bits
	timeout=1,           # set a timeout value, None for waiting forever
	xonxoff=0,             # enable software flow control
	rtscts=0,              # enable RTS/CTS flow control
	dsrdtr=0
	)

ser.isOpen()


def eap_func():
    print "start eap"
    t=time.time()
    # close existing sessions
    ser.write("\r")
    time.sleep(1)
    for n in range(10):
	ser.write("/A%s\r\n"%METER_NUMBER)
	rec = ser.read(200)
	if len(rec) > 5:
	    break
        #print len(rec)

    ser.write("/?!\r\n")
    if len(ser.read(200)) == 0:
	print "Brak odpowiedzi z licznika", METER_NUMBER
    else:
        ser.write("\x06001\r\n")
	ser.read(200)
	ser.write(addBcc("\x01P2\x02(0000)\x03"))
	ser.read(200)
	#ser.write(addBcc("\x01R1\x02T()\x03"))
	#ser.read(200)

	for ttt in range(10):
	    ser.write(addBcc("\x01R1\x02P()\x03"))
	    d=ser.read(200)
	    dd=re.search('\\((.+)\\:(.+)\\;(.+)\\;(.+)\\;(.+)\\)',d)
	    c=dd.group(1)
	    if c=='N':
		pub("P",dd.group(5))
		break
	    else:
		print "sleepP",c
		time.sleep(2)

	for ttt in range(10):
	    ser.write(addBcc("\x01R1\x02Q()\x03"))
	    d=ser.read(200)
	    dd=re.search('\\((.+)\\:(.+)\\;(.+)\\;(.+)\\;(.+)\\)',d)
	    c=dd.group(1)
	    if c=='N':
		pub("Q",dd.group(5))
		break
	    else:
		print "sleepQ",c
		time.sleep(2)

	for ttt in range(10):
	    ser.write(addBcc("\x01R1\x02S()\x03"))
	    d=ser.read(200)
	    dd=re.search('\\((.+)\\:(.+)\\;(.+)\\;(.+)\\;(.+)\\)',d)
	    c=dd.group(1)
	    if c=='N':
		pub("S",dd.group(5))
		break
	    else:
		print "sleepS",c
		time.sleep(2)
	
	ser.write(addBcc("\x01R1\x02EPP0()\x03"))
	d=ser.read(200)
	dd=re.search('\\((.+)\\)',d)
	pub("EPP",dd.group(1))

	ser.write(addBcc("\x01R1\x02F()\x03"))
	d=ser.read(200)
	dd=re.search('\\((.+)\\)',d)
	pub("F",dd.group(1))

	ser.write(addBcc("\x01R1\x02U()\x03"))
	d=ser.read(200)
	dd=re.search('\\((.+);(.+);(.+);(.+);(.+);(.+);(.+)\\)',d)
	pub("U1",dd.group(1))
	pub("U2",dd.group(2))
	pub("U3",dd.group(3))
	pub("U1F",dd.group(4))
	pub("U2F",dd.group(5))
	pub("U3F",dd.group(6))
	pub("UF",dd.group(7))

	ser.write(addBcc("\x01R1\x02I()\x03"))
	d=ser.read(200)
	dd=re.search('\\((.+)\\;(.+)\\;(.+)\\)',d)
	pub("I1",dd.group(1))
	pub("I2",dd.group(2))
	pub("I3",dd.group(3))
    print "eap_completed in %f sec"%(time.time()-t)


def on_connect(client,userdata,rc):
    print "on connect rc=",rc
    client.will_set("/meter/$online","OFF",0,True)
    client.publish("/meter/$online","ON",0,True)



client.on_connect=on_connect
client.connect("127.0.0.1",1883,60)
client.loop_start()

while(1):
    eap_func()




