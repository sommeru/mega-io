#!./bin/python

virtualmode = True

if virtualmode == False:
    from smbus2 import SMBus
    i2cbus = SMBus(1) # Use i2c bus No.1 (for Pi Rev 2+)
import time
import sqlite3
import csv

sqlconnection = sqlite3.connect(':memory:')
sqlcursor = sqlconnection.cursor()

IODIRA = 0x00 # Pin direction register for GPIOA (LOW= output, HIGH=input)
IODIRB = 0x01 # Pin direction register for GPIOB
OLATA  = 0x14 # GPIOA Register for configuring outputs
OLATB  = 0x15 # GPIOB Register for configuring outputs
GPIOA  = 0x12 # Register for inputs
GPIOB  = 0x13
GPPUA  = 0x0C    # HIGH = PULLUP enabled
GPPUB  = 0x0D    # LOW PULLUP disabled
PinDict= {"7": 0x80, "6":0x40, "5":0x20, "4":0x10,"3":0x08, "2":0x04, "1":0x02, "0":0x01, "all":0xff, "off":0x00}

def statedb_init():
    sqlcursor.execute('''CREATE TABLE statedb (pinname text, out_i2caddr int, out_gpiobank text, out_pinno int, in_i2caddr int, in_gpiobank text, in_pinno int, latchingtime int, pinstate int)''')

    with open ('sens_act_list.csv', 'r') as f:
        reader = csv.reader(f)
        data = next(reader)
        query = 'insert into statedb values ({0})'
        query = query.format(','.join('?' * len(data)))
        for data in reader:
            if data[0]=="": # Skip empty lines
                data = next(reader)
            else:
                sqlcursor.execute(query, data)
    sqlconnection.commit()


def mcp23017_init():
    if virtualmode == False:
        DEVICE = 0x20
        i2cbus.write_byte_data(DEVICE,0x00,0x00) # in register IODIRA set all pins as output (LOW)
        i2cbus.write_byte_data(DEVICE,0x01,0x00) # in register IODIRB set all pins as output (LOW)
        DEVICE= 0x24
        i2cbus.write_byte_data(DEVICE,0x00,0xFF) # in register IODIRA set all pins as inputs (HIGH)
        i2cbus.write_byte_data(DEVICE,0x01,0xFF) # in register IODIRB set all pins as inputs (HIGH)
        i2cbus.write_byte_data(DEVICE,0x0C,0xFF) # enable all pullups (GPPUA) on GPIOA
        i2cbus.write_byte_data(DEVICE,0x0D,0xFF) # enable all pullups (GPPUB) on GPIOB


def mcp23017_write(pinnametowriteto, pinstatetowrite):
    if virtualmode == False:
        i2cbus.write_byte_data(DEVICE,OLATA,0x01)
        time.sleep(.200)
        i2cbus.write_byte_data(DEVICE,OLATA,0x00)
    else:
        sqlcursor.execute("SELECT * FROM statedb WHERE pinname = ?",(pinnametowriteto,))
        writechannel=sqlcursor.fetchone()
        device = (writechannel[1])
        if writechannel[2] == "a":
            olat = 0x14 # GPIOA Register for configuring outputs
        elif writechannel[2] == "b":
            olat = 0x15 # GPIOB Register for configuring outputs

        if pinstatetowrite == 0:
            payload = 0
        elif pinstatetowrite == 1:
            if writechannel[3] == 0:
                payload = 0
            else:
                payload = 1
            for x in range (0,writechannel[3]):
                payload = payload << 1
            print("pretending write to device adress", hex(device), "with olat", hex(olat), "and payload:", bin(payload))
            time.sleep(.200)
            print("pretending write to device adress", hex(device), "with olat", hex(olat), "and payload:", bin(0))

def mcp23017_read():

    i2caddrs= list(sqlcursor.execute("SELECT DISTINCT in_i2caddr FROM statedb"))
    gpiobanks = list(sqlcursor.execute("SELECT DISTINCT in_gpiobank FROM statedb"))

    for i2caddr in i2caddrs:
        if ((int(i2caddr[0]) > 0) & (int(i2caddr[0])< 40)): #Then it's presumably a MCP
            for gpiobank in gpiobanks:
                if len(gpiobank[0]) > 0:
                    if virtualmode == False:
                        if gpiobank[0] == "a":
                            read = i2cbus.read_byte_data(i2caddr[0], 0x12) #Read register GPIOA (0x12)
                        elif gpiobank[0] == "b":
                            read = i2cbus.read_byte_data(i2caddr[0], 0x13) #Read register GPIOB (0x13)
                    else:
                        read= 254
                    for x in range(0, 8):
                        sqlcursor.execute("UPDATE statedb SET pinstate = ? WHERE in_i2caddr = ? AND in_gpiobank=? AND in_pinno=?", (1-(read & 1),i2caddr[0],gpiobank[0], x))
                        read = read >> 1

    sqlconnection.commit()


statedb_init()
mcp23017_init()

time.sleep(.500)
mcp23017_read()
mcp23017_write("1_Bed_SpotBig",1)

