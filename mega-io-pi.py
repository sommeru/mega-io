#!./bin/python

virtualmode = True

if virtualmode == False:
    from smbus2 import SMBus
    i2cbus = SMBus(1)  # Use i2c bus No.1 (for Pi Rev 2+)

import time  # for waiting in the code
import sqlite3
import csv
import sys  # for exiting the code if an error occurs
import paho.mqtt.client as mqtt
import threading

sqlconnection = sqlite3.connect(':memory:', check_same_thread=False)
sqlcursor = sqlconnection.cursor()


mqttclient = mqtt.Client("mega-io-pi")

todolist_time = dict()

#class Register:
#    def __init__(self, address):
#        self.address = address
#        self.value = 0


last_register_value = dict()
last_register_value[0x20] = dict()
last_register_value[0x20][0x14] = 0
last_register_value[0x20][0x15] = 0
last_register_value[0x21] = dict()
last_register_value[0x21][0x14] = 0
last_register_value[0x21][0x15] = 0
last_register_value[0x22] = dict()
last_register_value[0x22][0x14] = 0
last_register_value[0x22][0x15] = 0
last_register_value[0x23] = dict()
last_register_value[0x23][0x14] = 0
last_register_value[0x23][0x15] = 0



def statedb_init():
    with open('sens_act_list.csv', 'r') as f:
        reader = csv.reader(f)
        data = next(reader)
        sqlcreatequery = (", ".join(data))
        sqlcursor.execute("CREATE TABLE statedb ({0})".format(sqlcreatequery))
        query = 'insert into statedb values ({0})'
        query = query.format(','.join('?' * len(data)))
        for data in reader:
            if data[0] == "":  # Skip empty lines
                data = next(reader)
            else:
                sqlcursor.execute(query, data)
    sqlconnection.commit()


def mcp23017_init():
    mcps_output = [0x20, 0x21, 0x22, 0x23]
    mcps_input = [0x24, 0x25]
    if virtualmode == False:
        for device in mcps_output:
            i2cbus.write_byte_data(device, 0x00, 0x00)  # in register IODIRA set all pins as output (LOW)
            i2cbus.write_byte_data(device, 0x01, 0x00)  # in register IODIRB set all pins as output (LOW)
        for device in mcps_input:
            i2cbus.write_byte_data(device, 0x00, 0xFF)  # in register IODIRA set all pins as inputs (HIGH)
            i2cbus.write_byte_data(device, 0x01, 0xFF)  # in register IODIRB set all pins as inputs (HIGH)
            i2cbus.write_byte_data(device, 0x0C, 0xFF)  # enable all pullups (GPPUA) on GPIOA
            i2cbus.write_byte_data(device, 0x0D, 0xFF)  # enable all pullups (GPPUB) on GPIOB


def mcp23017_write(pinnametowriteto, pinstatetowrite):
    print(pinnametowriteto)
    try:
        sqlcursor.execute("SELECT out_i2caddr, out_gpiobank, out_pinno FROM statedb WHERE pinname = ?", (pinnametowriteto,))
        (device, gpiobank, pinno) = sqlcursor.fetchone()
        print(pinno)
    except Exception as e:
        print("sqlquery failed in module write...")
        print(e)
        return
    if gpiobank == "a":
        olat = 0x14  # GPIOA Register for configuring outputs
    elif gpiobank == "b":
        olat = 0x15  # GPIOB Register for configuring outputs
    else:
        print ("no such OLAT register =", olat)
        return
    bit = 1 << pinno
    if pinstatetowrite == 1:
        last_register_value[device][olat] |= bit
    else:
        last_register_value[device][olat] &= (0b11111111 ^ bit)

    payload  = last_register_value[device][olat]

    if virtualmode == False:
        i2cbus.write_byte_data(device, olat, payload)
        print("writing to device address", hex(device), "with olat", hex(olat), "and payload:", bin(payload))

    else:
        print("pretending write to device address", hex(device), "with olat", hex(olat), "and payload:", bin(payload))


def mcp23017_read():
    i2caddrs = list(sqlcursor.execute("SELECT DISTINCT in_i2caddr FROM statedb"))
    gpiobanks = list(sqlcursor.execute("SELECT DISTINCT in_gpiobank FROM statedb"))

    for i2caddr in i2caddrs:
        if ((int(i2caddr[0]) > 0) & (int(i2caddr[0]) < 40)):  # Then it's presumably a MCP
            for gpiobank in gpiobanks:
                if len(gpiobank[0]) > 0:
                    if virtualmode == False:
                        if gpiobank[0] == "a":
                            read = i2cbus.read_byte_data(i2caddr[0], 0x12)  # Read register GPIOA (0x12)
                        elif gpiobank[0] == "b":
                            read = i2cbus.read_byte_data(i2caddr[0], 0x13)  # Read register GPIOB (0x13)
                    else:
                        read = 254
                    for bytepos in range(0, 8):
                        sqlcursor.execute( "SELECT pinstate, pinname FROM statedb WHERE in_i2caddr = ? AND  in_gpiobank = ? AND in_pinno = ?", (i2caddr[0], gpiobank[0], bytepos))
                        try:
                            oldpin = sqlcursor.fetchone()
                            newpinvalue = 1 - (read & 1)
                            if oldpin[0] != (1 - (read & 1)):
                                # print("Old pin value of {0} is {1}, new is {2}. Updating statedb...".format(oldpin[1], oldpin[0], newpinvalue))
                                sqlcursor.execute(
                                    "UPDATE statedb SET pinstate = ? WHERE in_i2caddr = ? AND in_gpiobank=? AND in_pinno=?",
                                    (newpinvalue, i2caddr[0], gpiobank[0], bytepos))
                                processchangedpin(oldpin[1], newpinvalue)

                        except TypeError:
                            pass
                        read = read >> 1

    sqlconnection.commit()


def processchangedpin(pinname, pinvalue):
    print("new value:", pinname, ":", pinvalue)
    mqtttopic = "kirchenfelder75/mega-io/state/" + pinname
    if (pinvalue == 0):
        mqttmessage = "OFF"
    elif (pinvalue == 1):
        mqttmessage = "ON"

    mqttclient.publish(mqtttopic, mqttmessage)

def mqttconnected(client, userdata, flags, rc):
    if rc==0:
        print("successfully connected to MQTT broker. Returned code =",rc)
    else:
        print("Bad connection to MQTT broker. Returned code =",rc)
        mqtterrorcode = {
            1: "Connection refused – incorrect protocol version",
            2: "Connection refused – invalid client identifier",
            3: "Connection refused – server unavailable",
            4: "Connection refused – bad username or password",
            5: "Connection refused – not authorised"
        }
        print (mqtterrorcode.get(rc, "Error code unknown..."))

def mqtt_connect():
    try:
        with open('mqtt_credentials.csv', 'r') as f:
            reader = csv.reader(f)
            data = next(reader)  # Skip header line
            data = next(reader)
            mqtt_credentials_server = data[0]
            mqtt_credentials_user = data[1]
            mqtt_credentials_password = data[2]
            mqtt_credentials_port = int(data[3])
            mqtt_credentials_sslport = int(data[4])
            mqtt_credentials_websocketport = int(data[5])
        print("successfully imported MQTT credentials...")

    except:
        print("error opening mqtt_credentials.csv. Aborting...")
        sys.exit()

    mqttclient.username_pw_set(mqtt_credentials_user, password=mqtt_credentials_password)
    mqttclient.on_message=mqtt_message_recieved
    mqttclient.on_subscribe=mqttsubscribed
    mqttclient.on_connect=mqttconnected
    mqttclient.connect(mqtt_credentials_server, port=mqtt_credentials_port, keepalive=60, bind_address="")

    mqttclient.loop_start()
    mqttclient.subscribe("kirchenfelder75/mega-io/command/#")
    mqttclient.publish("kirchenfelder75/mega-io/debug","hello from mega-io-pi")


def mqtt_message_recieved(client, userdata, message):
    mqtttopic=str(message.payload.decode("utf-8"))
    print("message received " ,mqtttopic, "/ message topic =",message.topic, "/ message qos =", message.qos, "/ message retain flag =", message.retain)
    channel = message.topic.split("command/")[1]
    mcp23017_write(channel, 1)
    try:
        sqlcursor.execute("SELECT latchingtime FROM statedb WHERE pinname = ?", (channel,))
    except Exception as e:
        print("sqlquery failed in module mqttmesg recieved...")
        print(e)
        return
    latchingtime = sqlcursor.fetchone()[0]
    todolist_time[channel] = [int(round(time.time() * 1000)), latchingtime, 0]


def mqttsubscribed(client, userdata, mid, granted_qos):
    print ("successfully subscribed to MQTT topic with qos levels:", granted_qos)


def checktodolist_time():
    poplist = set()
    for todolistitem in todolist_time:
        print(todolistitem)
        if (int(round(time.time() * 1000)) - (todolist_time[todolistitem][0]) > (todolist_time[todolistitem][1]) ):

            try:
                sqlcursor.execute("SELECT latchingtime FROM statedb WHERE pinname = ?", (todolistitem,))
            except Exception as e:
                print("sqlquery failed in module checktodolist...")
                print(e)
                return
            mcp23017_write(todolistitem, todolist_time[todolistitem][2])
            poplist.add(todolistitem)
    for popitem in poplist:
        todolist_time.pop(popitem)

statedb_init()
mcp23017_init()
mqtt_connect()

# the main loop
while True:
    checktodolist_time()
    mcp23017_read()
    time.sleep(1)

