#!/usr/bin/python3

#based on https://github.com/mkorz/IntegraPy

from socket import *
from struct import *
from array import array
import time
import sys
import config
import mosquitto
import binascii
from threading import Lock


lock=Lock()
connected=0
outputs=array('b')
for i in range(0,128):
    outputs.append(-1)


def on_connect(mosq, userdata, rc):
    print ("on connect rc=%d"%(rc))
    client.subscribe("/satel/ctrl/#",2)
    client.will_set("/satel/$online","OFF",0,True)
    client.publish("/satel/$online","ON",0,True)


def on_disconnect(mosq, userdata, rc):
    print ("on disconnect rc=%d"%(rc))

client = mosquitto.Mosquitto("SATEL")



## Extra debugging
DEBUG = 0

# Delay between consecutive commands 
DELAY = 0.002

# Maximum number of retries when talking to Integra
MAX_ATTEMPTS = 3

# device types as defined by satel manual
PARTITION = "00"
ZONE = "01"
OUTPUT = "04"

def ihex(byte):
    return str(hex(byte)[2:])


''' Function to calculate a checksum as per Satel manual
beware - it might have a bug!
'''

def checksum(command):
    crc = 0x147A;
    for b in command:
        # rotate (crc 1 bit left)
        crc = ((crc << 1) & 0xFFFF) | (crc & 0x8000) >> 15
        crc = crc ^ 0xFFFF
        crc = (crc + (crc >> 8) + b) & 0xFFFF
    return crc;


''' All logic is hidden here - this function will send the requests and extract the result
hence the poor man debugging inside
'''


def sendcommand(command,sock):
    data = bytearray.fromhex(command)
    c = checksum(bytearray.fromhex(command))
    data.append(c >> 8)
    data.append(c & 0xFF)
    data.replace(b'\xFE', b'\xFE\xF0')

    data = bytearray.fromhex("FEFE") + data + bytearray.fromhex("FE0D")

    if DEBUG:
        print("-- Sending data --", file=sys.stderr)
        for c in data: print(">>> %s" % hex(c), file=sys.stderr)
        print("-- ------------- --", file=sys.stderr)
        print("Sent %d bytes" % len(data), file=sys.stderr)

    #print(0)
    failcount=0
    while True:
        if not sock.send(data): raise Exception("Error Sending message.")
        resp = sock.recv(100)
        if DEBUG:
            print("-- Receving data --", file=sys.stderr)
            for c in resp: print("<<<0x%X ('%c')" % (c, c), file=sys.stderr)
            print("-- ------------- --", file=sys.stderr)
        # integra will respond "Busy!" if it gets next message too early
        if (len(resp)==0 )| (resp[0:8] == b'\x10\x42\x75\x73\x79\x21\x0D\x0A'):
            failcount=failcount+1
            if failcount>MAX_ATTEMPTS:
                break 
        else:
            break

    if len(resp)==0:
        return ""
    #print(1)
    # check message
        
    if (resp[0:2] != b'\xFE\xFE'):
        for c in resp:
            print("0x%X" % c)
        raise Exception("Wrong header - got %X%X" % (resp[0], resp[1]))
    if (resp[-2:] != b'\xFE\x0D'):
        raise Exception("Wrong footer - got %X%X" % (resp[-2], resp[-1]))

    output = resp[2:-2].replace(b'\xFE\xF0', b'\xFE')
    if output[0:1] == b'\xEF':
        if not output[1:1] in b'\xFF\x00':
            raise Exception("Integra reported an error code %X" % output[1])
    elif output[0] != bytearray.fromhex(command[0:2])[0]:
        raise Exception(
            "Response to a wrong command - got %X expected %X" % (output[0], bytearray.fromhex(command[0:2])[0]))
    #print(2)
    c = checksum(bytearray(output[0:-2]))
    if (256 * output[-2:-1][0] + output[-1:][0]) != c:
        raise Exception("Wrong checksum - got %d expected %d" % ((256 * output[-2:-1][0] + output[-1:][0]), c))
    # return only data
    #print(4)
    return output[1:-2]


''' I only bothered with few of them, feel free to add all newer models
'''


def hardwareModel(code):
    if code == 0:
        return "24"
    if code == 1:
        return "32"
    if code == 2:
        return "64"
    if code == 3:
        return "128"
    if code == 4:
        return "128-WRL SIM300"
    if code == 132:
        return "128-WRL LEON"
    if code == 66:
        return "64 PLUS"
    if code == 67:
        return "128 PLUS"
    return "UNKNOWN"


''' Gets the firmware version as reported by panel, language and whether settings has been copied to flash
again - I only check if language is English or other
'''


def iVersion(soc):
    resp = sendcommand("7E",soc)
    model = "INTEGRA " + hardwareModel(resp[0])
    version = format("%c.%c%c %c%c%c%c-%c%c-%c%c" % tuple([chr(x) for x in resp[1:12]]))
    if resp[12] == 1:
        language = "English"
    else:
        language = "Other"

    if resp[13] == 255:
        settings = "stored"
    else:
        settings = "NOT STORED"
    print(model, version, "LANG: " + language, "SETTINGS " + settings + " in flash")


''' Gets the Integra time. Unfortunately, it is being sent in a rather weird format, hence the mess below
'''


def iTime():
    r = sendcommand("1A")
    itime = ihex(r[0]) + ihex(r[1]) + "-" + ihex(r[2]) + "-" + ihex(r[3]) + " " + ihex(r[4]) + ":" + ihex(
        r[5]) + ":" + ihex(r[6])
    return itime


''' Gets name of the zone and output. Could be easily extended to get name of users, expanders and so on
'''


def iName(number, devicetype):
    number = str(hex(number))[2:]
    if len(number) == 1:
        number = "0" + number
    r = sendcommand("EE" + devicetype + str(number))
    return r[3:].decode(config.encoding)


''' Checks violated zones. This make separate calls to get name of the violated zones. In a real life software,
this should be cached and synchronised when data are change (i.e. rarely, as zones, outputs et ceterea usually 
keep their names for a long time). In this demo, the more enabled outputs you have, the longer this script  will
take to execute
'''


def iViolation():
    r = sendcommand("00")
    v = ""
    for i in range(0, 15):
        for b in range(0, 7):
            if 2 ** b & (r[i]):
                v += str(8 * i + b + 1) + " " + iName(8 * i + b + 1, ZONE) + ":*\n"
    print(v)


''' Checks enabled outputs. See the comment for iViolation
'''


def iOutputs():
    r = sendcommand("17")
    o = ""
    for i in range(0, 15):
        for b in range(0, 7):
            if 2 ** b & r[i]:
                o += str(8 * i + b + 1) + " " + iName(8 * i + b + 1, OUTPUT) + ": ON\n"
    print(o)


''' Returns arm status for the partition (true: armed, false: disarmed)
'''


def iArmStatus(partition):
    r = sendcommand("0A")
    if 2 ** (partition % 8) & r[partition >> 3]:
        return True
    else:
        return False


''' Returns a string that can be sent to enable/disable a given output
'''


def outputAsString (output):
    string = ""
    byte = output // 8 + 1
    while byte > 1:
        string += "00"
        byte -= 1
    out = 1 << (output % 8 )
    result = str(hex(out)[2:])
    if len(result) == 1:
        result = "0" + result
    string += result
    while len(string) < 32:
        string += "0"
    return string

def outputsAsString (outputs):
    string = bytearray(16)
    for i in range(0,16):
        string[i]=0;
    for b in outputs:
        by=b//8
        bi=b%8
        va=1<<bi
        string[by]|=va
    return binascii.hexlify(string).decode("ascii")

''' Switches the state of a given output
'''


def iSwitchOutput(code, output):
    while len(code) < 16:
        code += "F"
    output = outputAsString(output)
    cmd = "91" + code + output
    r = sendcommand(cmd)







sock = socket(AF_INET, SOCK_STREAM)
sock.connect((config.host, config.port))

usercode=config.usercode
while len(usercode)<16:
    usercode+="F"


def on_message(mosq, userdata, msg):
    print("topic=%s  payload=%s"%(msg.topic, msg.payload))
    idx=int(msg.topic[msg.topic.rfind("/")+1:])-1
    val=msg.payload
    print("idx=%d to state %s"%(idx,val))
    cmd=""
    if (val==b'ON')|(val==b'UP'):
        cmd="88"+usercode+outputAsString(idx)
    else:
       if val==b'OFF':
           cmd="89"+usercode+outputAsString(idx)
       else:
           if val==b'DOWN':
               cmd="88"+usercode+outputAsString(idx+1)
           else:
               if val==b'STOP':
                   cmd="89"+usercode+outputsAsString((idx,idx+1))
               else:
                   return
    print("cmd=%s"%(cmd))
    lock.acquire()
    try:
        sendcommand(cmd,sock)
    finally:
        lock.release()

iVersion(sock)

client.on_connect=on_connect
client.on_disconnect=on_disconnect
client.on_message=on_message
client.connect("127.0.0.1",1883,60)
client.loop_start()







while True:
    lock.acquire()
    try:
        r=sendcommand("7F",sock)
    finally:
        lock.release()
    if r[2]&128==128:
        print("reading outputs")
        lock.acquire()
        try:
            r=sendcommand("17",sock)
        finally:
            lock.release()
        for i in range(0,128):
            by=i//8
            bi=i%8
            v=1<<bi
            o=(r[by]&v)>>bi
            if outputs[i]!=o:
                print ("changed index %03d %d->%d"%(i+1,outputs[i],o))
                outputs[i]=o
                topic="/satel/out/%d"%(i+1)
                if o==0:
                    value="OFF"
                else:
                    value="ON"
                client.publish(topic,value,0,True)


