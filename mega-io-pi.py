#!./bin/python

virtualmode = False

if virtualmode == False:
    from smbus2 import SMBus
    i2cbus = SMBus(1)  # Use i2c bus No.1 (for Pi Rev 2+)

import time
import sqlite3
import csv
import sys  # for exiting the code if an error occurs
import paho.mqtt.client as mqtt
import Adafruit_ADS1x15
import threading
import traceback

ANALOGWOBBLEBANDWITH = 400

lock = threading.Lock()
lock2 = threading.Lock()

sqlconnection = sqlite3.connect(':memory:', check_same_thread=False)
sqlcursor = sqlconnection.cursor()

mqttclient = mqtt.Client("mega-io-pi")
ADS = dict()
ADS[0x48] = Adafruit_ADS1x15.ADS1115(address=0x48)
ADS[0x49] = Adafruit_ADS1x15.ADS1115(address=0x49)
ADS["gain"] = 1

todolist_time = dict()
todolist_value = dict()
adscalibration = dict()

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
            if len(data) < 1:  # Skip empty lines
                data = next(reader)
            else:
                print(data)
                sqlcursor.execute(query, data)
    sqlconnection.commit()

def mcp23017_init():
    mcps_output = [0x20, 0x21, 0x22, 0x23]
    mcps_input = [0x24, 0x25, 0x26]
    if virtualmode == False:
        for device in mcps_output:
            try:
                i2cbus.write_byte_data(device, 0x00, 0x00)  # in register IODIRA set all pins as output (LOW)
                i2cbus.write_byte_data(device, 0x01, 0x00)  # in register IODIRB set all pins as output (LOW)
            except KeyboardInterrupt:
                raise
            except:
                print ("---------------> bus initialization failed at output MCP, device :",hex(device))
        for device in mcps_input:
            try:
                i2cbus.write_byte_data(device, 0x00, 0xFF)  # in register IODIRA set all pins as inputs (HIGH)
                i2cbus.write_byte_data(device, 0x01, 0xFF)  # in register IODIRB set all pins as inputs (HIGH)
                i2cbus.write_byte_data(device, 0x0C, 0xFF)  # enable all pullups (GPPUA) on GPIOA
                i2cbus.write_byte_data(device, 0x0D, 0xFF)  # enable all pullups (GPPUB) on GPIOB
            except KeyboardInterrupt:
                raise
            except:
                print ("---------------> bus initialization failed at input MCP, device :",hex(device))

def mcp23017_write(pinnametowriteto, pinstatetowrite):
    result = None
    try:
        lock.acquire(True)
        try:
            sqlcursor.execute("SELECT out_i2caddr, out_gpiobank, out_pinno FROM statedb WHERE pinname = ?", (pinnametowriteto,))
            result = sqlcursor.fetchone()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print("sqlquery failed in module write...")
            print(e)
            return
    finally:
        lock.release()

    if (result == None):
        print ("pinname", pinnametowriteto, "not known...")
        return
    (device, gpiobank, pinno) = result

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
        print("writing to device address", hex(device), "gpiobank", gpiobank, "and payload:", bin(payload))

    else:
        print("pretending write to device address", hex(device), "with olat", hex(olat), "and payload:", bin(payload))

def mcp23017_read( ):
    try:
        lock.acquire(True)
        i2caddrs = list(sqlcursor.execute("SELECT DISTINCT in_i2caddr FROM statedb"))
        gpiobanks = list(sqlcursor.execute("SELECT DISTINCT in_gpiobank FROM statedb"))
    finally:
        lock.release()

    for i2caddr in i2caddrs:
        if ((int(i2caddr[0]) > 0) & (int(i2caddr[0]) < 40)):  # Then it's presumably a MCP
            for gpiobank in gpiobanks:
                if len(gpiobank[0]) > 0:
                    if virtualmode == False:
                        if gpiobank[0] == "a":
                            try:
                                read = i2cbus.read_byte_data(i2caddr[0], 0x12)  # Read register GPIOA (0x12)
                            except KeyboardInterrupt:
                                raise
                            except Exception as e:
                                print("Error in reading MCP")
                                print(e)
                                read=254
                        elif gpiobank[0] == "b":
                            try:
                                read = i2cbus.read_byte_data(i2caddr[0], 0x13)  # Read register GPIOB (0x13)
                            except KeyboardInterrupt:
                                raise
                            except:
                                print("Error in reading MCP")
                                read=254

                    else:
                        read = 254
                    for bytepos in range(0, 8):
                        try:
                            lock.acquire(True)
                            sqlcursor.execute( "SELECT pinstate, pinname FROM statedb WHERE in_i2caddr = ? AND  in_gpiobank = ? AND in_pinno = ?", (i2caddr[0], gpiobank[0], bytepos))
                        finally:
                            lock.release()
                        try:
                            lock.acquire(True)
                            oldpin = sqlcursor.fetchone()
                            newpinvalue = 1 - (read & 1)
                            if oldpin[0] != (1 - (read & 1)):
                                # print("Old pin value of {0} is {1}, new is {2}. Updating statedb...".format(oldpin[1], oldpin[0], newpinvalue))
                                sqlcursor.execute("UPDATE statedb SET pinstate = ? WHERE in_i2caddr = ? AND in_gpiobank=? AND in_pinno=?", (newpinvalue, i2caddr[0], gpiobank[0], bytepos))
                                processchangedpin(oldpin[1], newpinvalue)

                        except TypeError:
                            pass
                        lock.release()
                        read = read >> 1

    sqlconnection.commit()

def processchangedpin(pinname, pinvalue):
    print("new value:", pinname, ":", pinvalue)
    mqtttopic = "kirchenfelder75/mega-io/state/" + pinname
    if (pinvalue == 0):
        mqttmessage = "OFF"
    elif (pinvalue == 1):
        mqttmessage = "ON"
    else:
        mqttmessage = str(pinvalue)

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

    except KeyboardInterrupt:
        raise
    except:
        print("error opening mqtt_credentials.csv. Aborting...")
        sys.exit()

    mqttclient.username_pw_set(mqtt_credentials_user, password=mqtt_credentials_password)
    mqttclient.on_message=mqtt_message_received
    mqttclient.on_subscribe=mqttsubscribed
    mqttclient.on_connect=mqttconnected
    mqttclient.connect(mqtt_credentials_server, port=mqtt_credentials_port, keepalive=60, bind_address="")

    #mqttclient.loop_start()
    mqttclient.subscribe("kirchenfelder75/mega-io/command/#")
    mqttclient.publish("kirchenfelder75/mega-io/debug","hello from mega-io-pi")

def mqtt_message_received(client, userdata, message):
    with lock2:
        try:
            mqtttopic=str(message.payload.decode("utf-8"))
            print("message received " ,mqtttopic, "/ message topic =",message.topic, "/ message qos =", message.qos, "/ message retain flag =", message.retain)
            channel = message.topic.split("command/")[1]

            # check if we want to run analog calibration for channel
            if (mqtttopic == "calibration"):
                analogin_calibration(channel)
                return
            elif (mqtttopic == "ON"):
                try:
                    lock.acquire(True)
                    sqlcursor.execute("SELECT latchingtime, pinstate, in_i2caddr FROM statedb WHERE pinname = ?", (channel,))
                    sqlresult = sqlcursor.fetchone()
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print("sqlquery failed in module mqttmesg recieved...")
                    print(e)
                    latchingtime = 200 #to avoid blocking of switches
                finally:
                    lock.release()
                latchingtime = sqlresult[0]
                pinstate = int(sqlresult[1])
                isanalogchannel = (int(sqlresult[2]) >= 72)
                if (isanalogchannel):
                    pinstate = ads1115_convert(channel, pinstate)

                if ((pinstate == 0) or (pinstate == -1)):
                    mcp23017_write(channel, 1)
                    todolist_time[channel] = [int(round(time.time() * 1000)), latchingtime, 0]
                else:
                    print("no turning ON as pinstate is already", pinstate)

            elif ((mqtttopic == "OFF") or (mqtttopic == "0")):
                try:
                    lock.acquire(True)
                    r = sqlcursor.execute("SELECT latchingtime, pinstate, in_i2caddr FROM statedb WHERE pinname = ?", (channel,))
                    sqlresult = sqlcursor.fetchone()
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print("sqlquery failed in module mqttmesg recieved...")
                    print(e)
                    latchingtime = 200 #to avoid blocking of switches
                finally:
                    lock.release()
                latchingtime = sqlresult[0]
                pinstate = int(sqlresult[1])
                isanalogchannel = (int(sqlresult[2]) >= 72)
                if (isanalogchannel):
                    pinstate = ads1115_convert(channel, pinstate)

                if ((pinstate > 0) or (pinstate == -1)):
                    mcp23017_write(channel, 1)
                    todolist_time[channel] = [int(round(time.time() * 1000)), latchingtime, 0]
                else:
                    print("no turning OFF as pinstate is already", pinstate)

            else:
                try:
                    setvalue = int(mqtttopic)
                except KeyboardInterrupt:
                    raise
                except:
                    print ("Don't know how to handle topic",mqtttopic,"giving up...")
                    return
                if ((setvalue > 0) and (setvalue <= 100)):
                    mcp23017_write(channel, 1)
                    todolist_value[channel] = setvalue
                else:
                    print ("Only numbers between 0 and 100 are supported.", setvalue, "seemes to be outside...") 
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print("error in mqtt_message_received: %s" % str(e))
            print("full traceback follows:")
            print(traceback.format_exc())
            raise

def mqttsubscribed(client, userdata, mid, granted_qos):
    print ("successfully subscribed to MQTT topic with qos levels:", granted_qos)

def checktolist_value():
    poplist = set()
    for todolistitem in todolist_value:
        try:
            lock.acquire(True)
            sqlcursor.execute("SELECT pinstate FROM statedb WHERE pinname = ?", (todolistitem,))
            actualvalue = int(sqlcursor.fetchone()[0])
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print("sqlquery failed in module checktolistvalue...")
            print(e)
        finally:
            lock.release()
        actualvalue = ads1115_convert(todolistitem, actualvalue)
        if (abs(actualvalue - todolist_value[todolistitem]) < 5):
            mcp23017_write(todolistitem,0)
            poplist.add(todolistitem)
    for popitem in poplist:
        todolist_value.pop(popitem)

def checktodolist_time():
    poplist = set()
    for todolistitem in todolist_time:
        if (int(round(time.time() * 1000)) - (todolist_time[todolistitem][0]) > (todolist_time[todolistitem][1]) ):

            try:
                lock.acquire(True)
                sqlcursor.execute("SELECT latchingtime FROM statedb WHERE pinname = ?", (todolistitem,))
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print("sqlquery failed in module checktodolist...")
                print(e)
                return
            finally:
                lock.release()
            mcp23017_write(todolistitem, todolist_time[todolistitem][2])
            poplist.add(todolistitem)
    for popitem in poplist:
        todolist_time.pop(popitem)

def ads1115_read():
    try:
        try:
            lock.acquire(True)
            i2caddrs = list(sqlcursor.execute("SELECT DISTINCT in_i2caddr FROM statedb WHERE in_i2caddr >= 72")) # >=72 usually means an ADS1XXX
        finally:
            lock.release()
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print("sqlquery failed in module adsread_i2caddrs...")
        print(e)
        return
    for i2caddr in i2caddrs:
        try:
            try:
                lock.acquire(True)
                pins = list(sqlcursor.execute("SELECT DISTINCT in_pinno FROM statedb WHERE in_i2caddr = ?",(i2caddr[0],)))
            finally:
                lock.release()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print("sqlquery failed in module adsread_pins...")
            print(e)
            return
        for pin in pins:
            if virtualmode == False:
                try:
                    read = ADS[i2caddr[0]].read_adc(pin[0], gain=ADS["gain"])
                except KeyboardInterrupt:
                    raise
                except:
                    read = 0
                    print ("Error reading ADS", i2caddr[0])
            else:
                read = 0
            try:
                lock.acquire(True)
                sqlcursor.execute("SELECT pinstate, pinname FROM statedb WHERE in_i2caddr = ? AND in_pinno = ?",(i2caddr[0],pin[0]))
                oldvalue = sqlcursor.fetchone()
            except KeyboardInterrupt:
                raise
            except:
                oldvalue[0] = 0
            finally:
                lock.release()
            if (abs(int(oldvalue[0])-int(read))>ANALOGWOBBLEBANDWITH):
                try:
                    lock.acquire(True)
                    sqlcursor.execute("UPDATE statedb SET pinstate = ? WHERE in_i2caddr = ? AND in_pinno=?",(read, i2caddr[0], pin[0]))
                    sqlconnection.commit()
                finally:
                    lock.release()
                convertedvalue = ads1115_convert(oldvalue[1],read)
                processchangedpin(oldvalue[1], convertedvalue)

def analogin_calibration(pinname):
    oldcsvcontent = list()
    with open("calibration.csv", newline='') as oldcsvfile:
        calibreader = csv.reader(oldcsvfile)
        try:
            for row in calibreader:
                if (row[0] != pinname):
                    oldcsvcontent.append(row)
        except csv.Error as e:
            sys.exit('file {}, line {}: {}'.format(filename, reader.line_num, e))

    with open('calibration.csv', 'w', newline='') as csvfile:
        calibwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        calibwriter.writerows(oldcsvcontent)

    print("starting calibration of channel:",pinname)
    maximum = -100000
    minimum = 100000
    mean = list()
    try:
        lock.acquire(True)
        sqlcursor.execute("SELECT in_i2caddr, in_pinno FROM statedb WHERE pinname = ?",(pinname,))
        targetchannel = sqlcursor.fetchone()
    finally:
        lock.release()
    mcp23017_write(pinname,1)
    time.sleep(2)
    starttime = int(round(time.time() * 1000))
    while int(round(time.time() * 1000)) - starttime < 30000:
        read = ADS[targetchannel[0]].read_adc(targetchannel[1], gain=ADS["gain"])
        if (read > maximum):
            maximum = read
        if (read < minimum):
            minimum = read

    mcp23017_write(pinname,0)
    time.sleep(1)
    print("Minimum for channel", pinname, "was", minimum)
    print("Maximum for channel", pinname, "was", maximum)

    mcp23017_write(pinname,1)
    time.sleep(.2)
    mcp23017_write(pinname,0)
    print("Detecting zero value")
    time.sleep(2)
    starttime = int(round(time.time() * 1000))
    while int(round(time.time() * 1000)) - starttime < 10000:
        mean.append(ADS[targetchannel[0]].read_adc(targetchannel[1], gain=ADS["gain"]))
        time.sleep(.01)

    print ("Mean zero value :", sum(mean)/len(mean))
    print ("Min zero value :", min(mean))
    print ("Max zero value :", max(mean))
    with open('calibration.csv', 'a', newline='') as csvfile:
        calibwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        calibwriter.writerow([pinname, min(mean), sum(mean)/len(mean), max(mean), minimum, maximum])

def ads1115_init():
    adscsvcontent = list()
    with open("calibration.csv", newline='') as calibcsvfile:
        calibreader = csv.reader(calibcsvfile)
        header = next(calibreader, None)
        try:
            for row in calibreader:
                zerocutoff = int(row[3]) + (int(row[4]) - int(row[3])) / 2
                oneperc =     int(row[4]) + ((int(row[5]) - int(row[4])) / 20)
                hundredperc = int(row[5]) - ((int(row[5]) - int(row[4])) / 20)
                adscalibration[row[0]] = dict(zerocutoff=zerocutoff, oneperc=oneperc, hundredperc=hundredperc)
        except csv.Error as e:
            sys.exit('file {}, line {}: {}'.format(filename, reader.line_num, e))

def ads1115_convert(pinname, rawvalue):
    if (rawvalue < adscalibration[pinname]["zerocutoff"]):
        returnvalue = 0
    else:
        returnvalue = int((rawvalue-adscalibration[pinname]["oneperc"]) / (adscalibration[pinname]["hundredperc"] - adscalibration[pinname]["oneperc"])*100 )
        if returnvalue < 1:
            returnvalue = 1
        elif returnvalue > 100:
            returnvalue = 100
    return(returnvalue)



statedb_init()
mcp23017_init()
ads1115_init()
mqtt_connect()

starttime = time.time()
# the main loop
while True:
    mqttclient.loop(0.001)
    checktodolist_time()
    checktolist_value()
    mcp23017_read()
    ads1115_read()
