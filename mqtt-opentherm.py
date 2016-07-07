#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib2
import time
import sys
import re
import serial
import mosquitto
from threading import Lock


lock=Lock()


client = mosquitto.Mosquitto("OTG")


#insert into czujniki(typ,adres,opis,miano) values(4,80,'Supply inlet temperature:','C');
#insert into czujniki(typ,adres,opis,miano) values(4,82,'Exhaust inlet temperature:','C');

mt=['READ-DATA','WRITE-DATA','INVALID-DATA','RESERVED','READ-ACK','WRITE-ACK','DATA-INVALID','UNKNOWN-DATAID']

mids={2: 'Master configuration:',
70: 'Status V/H:',
71: 'Control setpoint V/H:',
72: 'Fault flags/code V/H:',
74: 'Configuration/memberid V/H:',
77: 'Relative ventilation:',
80: 'Supply inlet temperature:',
82: 'Exhaust inlet temperature:',
89: 'TSP setting V/H:',
126: 'Master product version:',
127: 'Slave product version:'}

setts={
0:  'Przepływ objętościowy powietrza przy wentylacji zredukowanej (m3/h):',
1:  '1-zawsze 0?:',
2:  'Przepływ objętościowy powietrza przy wentylacji normalnej (m3/h):',
3:  '3-zawsze 0?:',
4:  'Przepływ objętościowy powietrza przy wentylacji zwiększonej (m3/h):',
5:  '5-zawsze 0?:',
6:  'Wartość wymagana temperatury zewnętrznej do zamknięcia obejścia (°C)(*0.5):',
7:  'Wartość wymagana temperatury powietrza wywiewnego do otwarcia obejścia (°C)(*0.5):',
11: 'Stałe zachwianie równowagi ciśnienia w celu wyrównania nieszczelności budynku (m3/h)(-100):',
17: 'Aktywacja lub dezaktywacja układu chroniącego przed oblodzeniem:',
18: 'Tryb obejścia:',
19: 'Histereza obejścia (°K):',
20: 'Sposób eksploatacji Vitovent:',
23: 'Wskaźnik wymiany filtra na wyświetlaczu:',
24: 'Dodatkowa płytka instalacyjna:',
48: '48-zawsze 44? :',
49: '49-zawsze 1? :',
52: 'Przepływ objętościowy powietrza, wartość rzeczywista (m3/h):',
53: '53-zawsze 0?:',
54: '54-zawsze 0?:',
55: 'Temperatura powietrza zewnętrznego (°C)(-100):',
56: 'Temperatura powietrza wywiewnego, wartość rzeczywista (°C)(-100):',
60: 'Przepływ objętościowy powietrza nawiewnego, wartość rzeczywista (m3/h):',
61: '61-zawsze 0?:',
62: 'Przepływ objętościowy powietrza wywiewnego, wartość rzeczywista (m3/h):',
63: '63-zawsze 0?:',
64: 'Zewnętrzna strata ciśnienia po stronie nawiewnej, wartość rzeczywista (Pa):',
65: '65-zawsze 0?:',
66: 'Zewnętrzna strata ciśnienia po stronie wywiewnej, wartość rzeczywista (Pa):',
67: '67-zawsze 0?:',
68: 'Status układu chroniącego przed oblodzeniem (0 Nieaktywny,1 Zachwianie równowagi ciśnienia,5 Wentylator powietrza nawiewnego wył.):',

#12: 'Typ urządzenia:',
#14: 'Ustawienie obejścia:',
}

setts={
0:  'Przepływ objętościowy powietrza przy wentylacji zredukowanej (m3/h):',
1:  '1-zawsze 0?:',
2:  'Przepływ objętościowy powietrza przy wentylacji normalnej (m3/h):',
3:  '3-zawsze 0?:',
4:  'Przepływ objętościowy powietrza przy wentylacji zwiększonej (m3/h):',
5:  '5-zawsze 0?:',
6:  'Wartość wymagana temperatury zewnętrznej do zamknięcia obejścia (°C)(*0.5):',
7:  'Wartość wymagana temperatury powietrza wywiewnego do otwarcia obejścia (°C)(*0.5):',
11: 'Stałe zachwianie równowagi ciśnienia w celu wyrównania nieszczelności budynku (m3/h)(-100):',
17: 'Aktywacja lub dezaktywacja układu chroniącego przed oblodzeniem:',
18: 'Tryb obejścia:',
19: 'Histereza obejścia (°K):',
20: 'Sposób eksploatacji Vitovent:',
23: 'Wskaźnik wymiany filtra na wyświetlaczu:',
24: 'Dodatkowa płytka instalacyjna:',
48: '48-zawsze 44? :',
49: '49-zawsze 1? :',
52: 'Przepływ objętościowy powietrza, wartość rzeczywista (m3/h):',
53: '53-zawsze 0?:',
54: '54-zawsze 0?:',
55: 'Temperatura powietrza zewnętrznego (°C)(-100):',
56: 'Temperatura powietrza wywiewnego, wartość rzeczywista (°C)(-100):',
60: 'Przepływ objętościowy powietrza nawiewnego, wartość rzeczywista (m3/h):',
61: '61-zawsze 0?:',
62: 'Przepływ objętościowy powietrza wywiewnego, wartość rzeczywista (m3/h):',
63: '63-zawsze 0?:',
64: 'Zewnętrzna strata ciśnienia po stronie nawiewnej, wartość rzeczywista (Pa):',
65: '65-zawsze 0?:',
66: 'Zewnętrzna strata ciśnienia po stronie wywiewnej, wartość rzeczywista (Pa):',
67: '67-zawsze 0?:',
68: 'Status układu chroniącego przed oblodzeniem (0 Nieaktywny,1 Zachwianie równowagi ciśnienia,5 Wentylator powietrza nawiewnego wył.):',

#12: 'Typ urządzenia:',
#14: 'Ustawienie obejścia:',
}


def printMsgId(msgId):
    if msgId in mids.keys():
        return mids[msgId]
    else:
        return str(msgId)


def printSetts(a,b):
    if a in setts.keys():
        return setts[a]+str(b)
    else:
        return str(a)+':'+str(b)

def printVal(dataId,dataVal):
    i1=int(dataVal[0:2],16)
    i2=int(dataVal[2:4],16)
    if dataId in (80,82):
        if i1<128:
            return str(i1+i2/256.0)
        else:
            return str(i1-256+i2/256.0)
    else:
        return str(i1)+' '+str(i2)


r=re.compile('[TB][0-9A-F]{8}')

vals={}


def pub(type,value):
    topic="/ot/"+str(type)
    v=str(value)
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

serPort='/dev/ttyS1'
#serPort='/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'

ser2 = serial.Serial(serPort,baudrate=9600,bytesize=8,parity=serial.PARITY_NONE,stopbits=1,timeout=0.5,xonxoff=0,rtscts=0,dsrdtr=0)


def on_message(mosq, userdata, msg):
    print msg.topic,msg.payload
    cmd=''
    if msg.topic=='/ot/set/71':
        if msg.payload=="4":
            #ser2.write("VS=-\r\n")
            cmd="VS=-\r\n"
        else:
            #ser2.write("VS="+msg.payload+"\r\n")
            cmd="VS="+msg.payload+"\r\n"
        print(cmd)
        lock.acquire()
        try:
            ser2.write(cmd)
        finally:
            lock.release()


def on_connect(mosq, userdata, rc):
    print "Connected rc=",rc
    client.subscribe("/ot/set/71",2)
    client.will_set("/ot/$online","OFF",0,True)
    client.publish("/ot/$online","ON",0,True)

client.on_message=on_message
client.on_connect=on_connect

client.connect("127.0.0.1",1883,60)
client.loop_start()

cnt=0


while True:
    d=''
    lock.acquire()
    try:
        d=ser2.read(100)
    finally:
        lock.release()
    for a in r.findall(d):
        dev=a[0:1]
        msgType=int(a[1:2],16)&7
        msgId=int(a[3:5],16)
        msgData=a[5:9]
        msgDataS=int(a[5:7],16)
        msgDataV=int(a[7:9],16)
        if dev=='B':
            cnt=cnt+1
            if cnt>100:
                cnt=0
                last_values={}
            if( msgId==80 or msgId==82 ):     #inlet,outlet temp:
                i1=msgDataS
                i2=msgDataV
                temp=0.0
                if i1<128:
                    temp=i1+i2/256.0
                else:
                    temp=i1-256+i2/256.0
                print a,round(temp,2)
                pub(msgId,round(temp,2))
            elif msgId==71 or msgId==77:
                print a,mt[msgType],printMsgId(msgId),printVal(msgId,msgData)
                pub(msgId,msgDataV)
            elif msgId==89:
                print a,mt[msgType],printMsgId(msgId),printSetts(msgDataS,msgDataV)
            else:
                print a,mt[msgType],printMsgId(msgId),printVal(msgId,msgData)
        else:
            print a
