#!./bin/python

virtualmode = True

if virtualmode == False:
    from smbus2 import SMBus
    i2cbus = SMBus(1) # Use i2c bus No.1 (for Pi Rev 2+)
import time
import sqlite3
sqlconnection = sqlite3.connect(':memory:')
sqlcursor = sqlconnection.cursor()
sqlcursor.execute('''CREATE TABLE statedb ( pinname text, out_i2caddr int, out_gpiobank text, out_pinno int, in_i2caddr int, in_gpiobank text, in_pinno int, latchingtime int, pinstate int)''')

sqlcursor.execute("insert into statedb values ('1_ShopF_Spot', 0x20, 'a', 0, 0x24, 'a', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_EntranceF_Spot', 0x20, 'a', 1, 0x24, 'a', 1, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_EntranceR_Spot', 0x20, 'a', 2, 0x24, 'a', 2, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_EntranceR_Walllamp', 0x20, 'a', 3, 0x24, 'a', 3, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Work_SpotSmall', 0x20, 'a', 4, 0x24, 'a', 4, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Work_SpotBig', 0x20, 'a', 5, 0x24, 'a', 5, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Bed_SpotSmall', 0x20, 'a', 6, -1, '', 0, -1, -1)")
sqlcursor.execute("insert into statedb values ('1_Bed_SpotBig', 0x20, 'a', 7, -1, '', 1, -1, -1)")
sqlcursor.execute("insert into statedb values ('1_BathBig_SpotMirror', 0x20, 'b', 0, 0x24, 'a', 6, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_BathBig_SpotRear', 0x20, 'b', 1, 0x24, 'a', 7, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Stairway_Spot', 0x20, 'b', 2, 0x24, 'b', 1, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Stairway_Walllamp', 0x20, 'b', 3, 0x24, 'b', 2, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Stairway_Pendant', 0x20, 'b', 4, 0x24, 'b', 3, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_Walllamp', 0x20, 'b', 5, 0x24, 'b', 4, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_SpotMain', 0x20, 'b', 6, -1, '', 2, -1, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_SpotWintergarden', 0x21, 'a', 0, -1, '', 3, -1, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_SpotTv', 0x21, 'a', 1, -1, '', 4, -1, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_SpotKitchen', 0x21, 'a', 2, -1, '', 5, -1, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_Socket', 0x21, 'a', 3, 0x24, 'b', 5, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Kitchen_Spot', 0x21, 'a', 4, 0x24, 'b', 6, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Kitchen_LightCupboard', 0x21, 'a', 5, 0x24, 'b', 7, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Kitchen_Pendant', 0x21, 'a', 6, 0x24, 'b', 8, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Outdoor_LightPatio', 0x21, 'a', 7, 0x24, 'a', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Outdoor_LightFront', 0x21, 'b', 1, 0x24, 'a', 1, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Outdoor_LightEntrance', 0x21, 'b', 0, 0x24, 'a', 2, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Outdoor_LightSide', 0x21, 'b', 2, 0x24, 'a', 3, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Outdoor_SocketPatio', 0x21, 'b', 3, 0x24, 'a', 4, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Garage_Light', 0x21, 'b', 4, 0x24, 'a', 5, 200, -1)")

sqlcursor.execute("insert into statedb values ('1_Bed_ShutterUp', 0x22, 'a', 0, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Bed_ShutterDown', 0x22, 'a', 1, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_BathBig_ShutterUp', 0x22, 'a', 2, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_BathBig_ShutterDown', 0x22, 'a', 3, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Work_ShutterUp', 0x22, 'a', 4, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('1_Work_ShutterDown', 0x22, 'a', 5, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Stairway_ShutterUp', 0x22, 'a', 6, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Stairway_ShutterDown', 0x22, 'a', 7, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_ShutterWintergardenLUp', 0x22, 'b', 0, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_ShutterWintergardenLDown', 0x22, 'b', 1, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_ShutterWintergardenMUp', 0x22, 'b', 2, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_ShutterWintergardenMDown', 0x22, 'b', 3, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_ShutterWintergardenRUp', 0x22, 'b', 4, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_ShutterWintergardenRDown', 0x22, 'b', 5, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_ShutterTvUp', 0x23, 'b', 0, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Living_ShutterTvDown', 0x23, 'b', 1, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Kitchen_ShutterUp', 0x23, 'b', 2, 0, '', 0, 200, -1)")
sqlcursor.execute("insert into statedb values ('2_Kitchen_ShutterDown', 0x23, 'b', 3, 0, '', 0, 200, -1)")

sqlcursor.execute("insert into statedb values ('1_EntranceF_DooropenerEntrance', 0x23, 'a', 0, 0, '', 0, 3000, -1)")
sqlcursor.execute("insert into statedb values ('1_Misc_DooropenerDriveway', 0x23, 'a', 1, 0, '', 0, 250, -1)")

IODIRA = 0x00 # Pin direction register for GPIOA (LOW= output, HIGH=input)
IODIRB = 0x01 # Pin direction register for GPIOB
OLATA  = 0x14 # GPIOA Register for configuring outputs
OLATB  = 0x15 # GPIOB Register for configuring outputs
GPIOA  = 0x12 # Register for inputs
GPIOB  = 0x13
GPPUA  = 0x0C    # HIGH = PULLUP enabled
GPPUB  = 0x0D    # LOW PULLUP disabled
PinDict= {"7": 0x80, "6":0x40, "5":0x20, "4":0x10,"3":0x08, "2":0x04, "1":0x02, "0":0x01, "all":0xff, "off":0x00}

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
        sqlcursor.execute("UPDATE statedb SET pinstate = ? WHERE in_i2caddr = 0x24 AND in_gpiobank='a' AND in_pinno=?", (1-(read & 1), x))
        read = read >> 1


    sqlconnection.commit()

    t = (0,)
    sqlcursor.execute("SELECT * FROM statedb WHERE in_i2caddr = 0x24 AND in_gpiobank='a' AND in_pinno=?", t)
    print(sqlcursor.fetchone())
    t = (1,)
    sqlcursor.execute("SELECT * FROM statedb WHERE in_i2caddr = 0x24 AND in_gpiobank='a' AND in_pinno=?", t)
    print(sqlcursor.fetchone())


mcp23017_init()

mcp23017_write()
time.sleep(.500)
mcp23017_read()


