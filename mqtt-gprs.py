#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib2
import time
import sys
import re
import serial
import mosquitto

def on_connect(cl,userdata,flags):
   cl.will_set('/gprs/c','0')
   cl.publish('/gprs/c','1')


client = mosquitto.Mosquitto("GPRS")


client.on_connect=on_connect

client.connect("127.0.0.1",1883,60)

ser = serial.Serial('/dev/serial/by-id/usb-HUAWEI_MOBILE_HUAWEI_MOBILE_0123456789ABCDEF-if01-port0',baudrate=115200,bytesize=8,parity=serial.PARITY_NONE,stopbits=1,timeout=5,xonxoff=0,rtscts=0,dsrdtr=0)

while(ser.isOpen()):
    client.loop(0.1)
    line=ser.readline().strip()
    print line
    sl=line.split(':',2)
    if(len(sl)==2):
        typ=sl[0][1:]
        val=sl[1].strip().split(',',7)
        print typ,len(val),val
        if (typ=='RSSI') & (len(val)==1):
            topic="/gprs/"+typ
            client.publish(topic,val[0])
            print topic,val[0]
        elif (typ=='DSFLOWRPT') & (len(val)==7):
            topic="/gprs/DSFLOWRPT.UPLOAD"
            v=int(val[1],16)
            client.publish(topic,v)
            print topic,v
            topic="/gprs/DSFLOWRPT.DOWNLOAD"
            v=int(val[2],16)
            client.publish(topic,v)
            print topic,v
        elif (typ=='MODE') & (len(val)>1):
            topic="/gprs/MODE.A"
            v=int(val[0],10)
            client.publish(topic,v)
            print topic,v
            topic="/gprs/MODE.B"
            v=int(val[1],10)
            client.publish(topic,v)
            print topic,v
        elif (typ=='HCSQ') & (len(val)>0):
            topic="/gprs/HCSQ.SYSMODE"
            v=0
            if   val[0]=='"GSM"':    v=1
            elif val[0]=='"WCDMA"':  v=2
            elif val[0]=='"LTE"':    v=3
            client.publish(topic,v)
            print topic,v
        else:
            print typ,val
