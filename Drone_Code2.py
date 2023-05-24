from digi.xbee.devices import XBeeDevice
from digi.xbee.exception import *
import threading
import time
import logging as log
from haversine import *
import RPi.GPIO as GPIO
#Arduino needed imports
import serial
import datetime

# THIS IS DRONE 2 
HUBL = list() #Hub location as list
Targ_GPS = "" #targets
targ_i = 0 #target list index
home_loc = "none" #home gps location. 
DAL = "none" #drone 1 gps location
DBL = "none" #drone 3 gps location
my_loc = "42.3135 -71.0385" #my curent gps location
my_dist = 9999999.9999
Ard_trigger = 17 #Arduino trigger pin
all_devs ={
    "HUB": "none",
    "Drone 1": "none",
    "Drone 2": "none",
    "Drone 3": "none"
    }
#Yup its port USB1 for that USB 3.0 whatever dudeeee
PORT = "/dev/ttyUSB0"
ser = serial.Serial('/dev/ttyAMA0', 9600)

# PORT = "/dev/ttyS0"
BAUD_RATE = 9600

device = XBeeDevice(PORT, BAUD_RATE)

DATA_TO_SEND = "Hello Shawn Omnicron!"
PROFILE_PATH = "/home/drone/Desktop/D2_p1.xpro"

Abort_flag = False
notDone = True
has_devices = False

def main():
    log.basicConfig(filename='MeshScript.log', filemode='w')
    keys = all_devs.keys()
    print(" +--------------------------------------+")
    print(" | Mesh Communication Network in Session|")
    print(" +--------------------------------------+\n")
    
    global device
    #SETUP ARDUINO TRIGGER
    global Ard_trigger
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)   
    GPIO.setup(Ard_trigger, GPIO.OUT)

    xbee_network = device.get_network()
        
    setup_dev(device, PROFILE_PATH)
    #Look for devices on net and update dictionary   
    net_eye(keys, xbee_network)
    #add this after net_eye to avoid NI = None
    device.add_data_received_callback(my_data_received_callback)
    
    broadcast_mess(device, "Drone is on and ready to go.\n")
    
    #(+)++++Get current GPS location, this is home. We return here later.++++++
    #home_loc = get GPS location
    iterations = 0
    global Targ_GPS
    global my_dist
    while 1:
        #sleep helps smooth things out. 
        #time.sleep(0.1)
        #*******SEARCH FOR SOMEONE**********
        
        if iterations == 0:            
            net_eye(keys, xbee_network)
            if(Targ_GPS):
                #if we have something in the listt
                my_dist = calc_distance(my_loc, Targ_GPS)
                
        iterations = (iterations +1)%2
        print("Network has devices?: %s" %xbee_network.has_devices())  
        #print("Network has devices?: ", has_devices)
        if not xbee_network.has_devices():
            log.warning("No devices found. Can't fly. \n")
            # HOVER DEVICE UNTIL A **DRONE** IS IN RANGE UNLESS** targ AND Hub is in range!
            
        #*************SEARCH AND HOVER ALGO DONE *****************
        
        #(+)++++++BROADCAST MY CURRENT GPS LOCATION++++++++++
        
        #broadcast_mess(device, DATA_TO_SEND)

        
def net_eye(dev_list, net):    
    net.clear()
    #net.start_discovery_process()
    discovered = net.discover_devices(dev_list)   
    # if(len(discovered) > 0):
        # has_devices = True
    # else:
        # has_devices = False
    for a in discovered:
        temp = str(a).split(" - ")
        if all_devs.get(temp[1]) == "none":
            all_devs.update({temp[1] : temp[0]})
            print("updated dictionary: %s" %all_devs)    
    
            
def setup_dev(dev, PP):
    try:
        dev.open()
        dev.apply_profile(PP) #Configure device as Drone profile
    except TimeoutException:
        log.exception("Timeout occured, communication failed. with %s \n" % dev.get_64bit_addr())
    except InvalidOperatingModeException:
        log.exception("Operating mode of %s is not API or API-escape \n" % dev.get_64bit_addr())
    except XBeeException: 
        log.exception("Device %s may be closed or error occured when writing to it. \n" % dev.get_64bit_addr())
    except Exception as e:
        log.exception("An Exception occured for %s! \n" %dev.get_64bit_addr())
    """finally:
        if device is not None and device.is_open():
            device.close()"""

def my_data_received_callback(xbee_message):
    #xbee_message.remote_device.read_device_info(False)
    address = str(xbee_message.remote_device.get_64bit_addr())
    data = xbee_message.data.decode("utf8")   
    data = data.split(" ")
    na = xbee_message.remote_device.get_node_id()
    #This is Done in Net_eye but, could be useful in determining explicit message etc. 
    if all_devs.get(na) == "none":
        all_devs.update({na: address})
        print(all_devs) 
    elif data[0] == "Abort!":
        global Abort_flag
        Abort_flag = True
        #Delete
        print("Aborting Mission!\n")
        abort_mess = "Drone Aborting Mission!"
        broadcast_mess(device, abort_mess)
        return
    elif ((data[0] == "HUB") and (len(HUBL) == 0)):
        data.remove("HUB") 
        HUBL = data.copy()
        #delete
        print("Drone Got Hub Location: %s" %HUBL)
    elif (data[0] == "Targ"):
        data.remove("Targ")
        global Targ_GPS
        Targ_GPS = ' '.join(data)
        #delete
        global my_dist
        my_dist = calc_distance(my_loc, Targ_GPS)
        order_message = "Order %s" %my_dist
        broadcast_mess(device, order_message)
        print("Distance to target %s" %my_dist )  
        #Testing purposes      
        #if notDone:
         #   sleep.wait(1)
          #  mess = "Done!"
           # broadcast_mess(device, mess)
            #notDone = False
    elif(data[0] == "Order"):
        if( float(data[2]) < my_dist):
            #from 1-3
            ++Or_Num
            #DELETE
            print("My order: %s" %Or_Num)
    print("recieved %s\n", data)
    
        
def calc_distance(str_loc1, str_loc2):
    num_loc1 = get_gps(str_loc1)
    num_loc2 = get_gps(str_loc2)
    m_dist = haversine(num_loc1, num_loc2, unit=Unit.METERS)
    if(m_dist <= 2):
            #Start data collection if distance is less than or equal to 2m
            print("Target in range, gathering data.... \n")
            GPIO.output(Ard_trigger, GPIO.HIGH)
            time.sleep(50)
            GPIO.output(Ard_trigger, GPIO.LOW)
            filename = "sensor_data_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt"
            f = open(filename, "w")
            while(ser.in_waiting):
                ser.readline().decode().strip()
                # write the data to the file
                f.write(data + "\n")                
                # print the data to the console
                print(data)                
                # flush the file buffer
                f.flush()
            # close the file and serial port when finished
            f.close()
            ser.close()
            print("Data collection finished See file: %s.\n", filename)
            time.sleep(5)
            complete_mission()    
            broadcast_mess(device, "Done!")
                    
    return m_dist
    
def comlete_mission():
    global targ_i
    global Targ_GPS
    targ_i += 1
    
        


def get_gps(nums):
    intnums = nums.split(" ")
    arrnums = map(float, intnums)
    return list(arrnums)

def get_remote_device(name, net):
    r_device = net.discover_device(name)
    if r_device is None:
        log.warning("Could not find the remote device, %s \n" % name)
        return r_device #none
    else:
        return r_device
    
def broadcast_mess(Mdev, message):
    try:
        Mdev.send_data_broadcast(message)
    except TimeoutException:
        log.exception("local broadcast failed due to a timeout.")
    except InvalidOperatingModeException:
        log.exception("Transmit status for local broadcast is: Failed")
    except XBeeException:
        log.exception("Error writing to Xbee interface for local broadcast")
    except Exception as e:
        log.exception("An Exception for local broadcast occured!")
    else:
        print("Success sending %s \n" % message )
    
if __name__ == '__main__':
    main()
    

