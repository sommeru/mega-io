#!./bin/python

virtualmode = False

if virtualmode == False:
    from smbus2 import SMBus

    i2cbus = SMBus(1)  # Use i2c bus No.1 (for Pi Rev 2+)
import time  # for waiting in the code
import sqlite3
import csv
import sys  # for exiting the code if an error occurs
import paho.mqtt.client as mqtt

sqlconnection = sqlite3.connect(':memory:')
sqlcursor = sqlconnection.cursor()

IODIRA = 0x00  # Pin direction register for GPIOA (LOW= output, HIGH=input)
IODIRB = 0x01  # Pin direction register for GPIOB
OLATA = 0x14  # GPIOA Register for configuring outputs
OLATB = 0x15  # GPIOB Register for configuring outputs
GPIOA = 0x12  # Register for inputs
GPIOB = 0x13
GPPUA = 0x0C  # HIGH = PULLUP enabled
GPPUB = 0x0D  # LOW PULLUP disabled
PinDict = {"7": 0x80, "6": 0x40, "5": 0x20, "4": 0x10, "3": 0x08, "2": 0x04, "1": 0x02, "0": 0x01, "all": 0xff,
           "off": 0x00}

mqttclient = mqtt.Client(client_id="mega-io-pi", clean_session=True, userdata=None, transport="tcp")


#class Register:
#    def __init__(self, address):
#        self.address = address
#        self.value = 0


last_register_value = dict()
last_register_value[32] = dict()
last_register_value[32][0x14] = 0
last_register_value[32][0x15] = 0



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
    sqlcursor.execute("SELECT out_i2caddr, out_gpiobank, out_pinno FROM statedb WHERE pinname = ?", (pinnametowriteto,))
    (device, gpiobank, pinno) = sqlcursor.fetchone()
    if gpiobank == "a":
        olat = 0x14  # GPIOA Register for configuring outputs
    elif gpiobank == "b":
        olat = 0x15  # GPIOB Register for configuring outputs

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

    time.sleep(.200)

    if virtualmode == False:
        i2cbus.write_byte_data(device, olat, 0x00)
        print("writing to device adress", hex(device), "with olat", hex(olat), "and payload:", bin(payload))
    else:
        print("pretending write to device adress", hex(device), "with olat", hex(olat), "and payload:", bin(0))


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
                        sqlcursor.execute(
                            "SELECT pinstate, pinname FROM statedb WHERE in_i2caddr = ? AND  in_gpiobank = ? AND in_pinno = ?",
                            (i2caddr[0], gpiobank[0], bytepos))
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
    mqttclient.connect_async(mqtt_credentials_server, port=mqtt_credentials_port, keepalive=60, bind_address="")
    mqttclient.loop_start()
    # time.sleep(10)


statedb_init()
mcp23017_init()
mqtt_connect()

mcp23017_read()
mcp23017_write("1_ShopF_Spot", 1)

# the main loop

# while True
time.sleep(.5)
mcp23017_read()
#    time.sleep(1.000)
