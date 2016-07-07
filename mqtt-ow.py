#!/usr/bin/python


import pyownet
import time
import mosquitto

client = mosquitto.Mosquitto("ONEWIRE")

def on_connect(mosq, userdata, rc):
    print "on connect rc=",rc
    client.will_set("/ow/$online","OFF",0,True)
    client.publish("/ow/$online","ON",0,True)

vals={}


client.on_connect=on_connect
client.connect("127.0.0.1",1883,60)
client.loop_start()



ow=pyownet.protocol.proxy(host="localhost", port=4304)

while(1):
    for a in ow.dir():
        if a[:3]=="/28":
            pub=False
            sens=a+"temperature"
            #print sens
            v=str(ow.read(sens)).replace(' ','')
            if vals.has_key(a):
                if vals[a]!=v:
                    pub=True
                    #print 'new val',a,v
            else:
                pub=True
                #print 'new key',a,v
            if pub:
                vals[a]=v
                topic="/ow"+a+"temperature"
                print topic+"-"+v
                client.publish(topic,v,0,True)
    time.sleep(1)
