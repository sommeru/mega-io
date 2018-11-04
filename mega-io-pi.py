#!./bin/python

virtualmode = True

if virtualmode == False:
    from smbus2 import SMBus
    i2cbus = SMBus(1) # Use i2c bus No.1 (for Pi Rev 2+)
import time


print ('Hello world!')


IODIRA = 0x00 # Pin direction register for GPIOA (LOW= output, HIGH=input)
IODIRB = 0x01 # Pin direction register for GPIOB
OLATA  = 0x14 # GPIOA Register for configuring outputs
OLATB  = 0x15 # GPIOB Register for configuring outputs
GPIOA  = 0x12 # Register for inputs
GPIOB  = 0x13
GPPUA  = 0x0C    # HIGH = PULLUP enabled
GPPUB  = 0x0D    # LOW PULLUP disabled
PinDict= {"7": 0x80, "6":0x40, "5":0x20, "4":0x10,"3":0x08, "2":0x04, "1":0x02, "0":0x01, "all":0xff, "off":0x00}

outputstates = []

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


def mcp23017_write():
    if virtualmode == False:
        DEVICE = 0x20
        i2cbus.write_byte_data(DEVICE,OLATA,0x01)
        time.sleep(.200)
        i2cbus.write_byte_data(DEVICE,OLATA,0x00)

def mcp23017_read():
    DEVICE = 0x24
    if virtualmode == False:
        read = i2cbus.read_byte_data(DEVICE,0x12) #Read register GPIOA (0x12)
    else:
        read= 254

    print (bin(read))
    for x in range(0, 8):
        outputstates.append(read & 1)
        read = read >> 1

    print (outputstates)


    mcp23017_init()

mcp23017_write()
time.sleep(.500)
mcp23017_read()

