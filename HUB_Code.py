from digi.xbee.devices import *
from digi.xbee.exception import *
from digi.xbee.models.status import *
import time
import logging as log
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import * 
from haversine import *

max_dist = 300 #Max distance in meters for the mesh sensor network
# UMB: 42.313432 -71.038445
#JKF Library: 42.3095337619 -71.0337848649 too far
#Drone: "42.3135 -71.0385" 


Targs_list = list()
Targ_num = 0
AbortFlag = False
#has_devices = False

#(-) WE CAN'T DO HUB GPS WE CAN'T GET IT! USE TRANSMISSON STRENGTH OR Maybe we have it entered in GUI?
HUBL = "none"
#drone 1 gps location
DAL = "none"
#drone 2 gps location
DBL = "none"
DCL = "none" #drone 3 GPS location
# This dictionary is for explicit addressing messages
all_devs ={
    "HUB": "none",
    "Drone 1": "none",
    "Drone 2": "none",
    "Drone 3": "none"
    }

PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600
device = XBeeDevice(PORT, BAUD_RATE)
PROFILE_PATH = "/home/drone/Documents/Drone_Hub/Hub_p1.xpro"


def main():
    print(" +--------------------------------------+")
    print(" | Mesh Communication Network in Session|")
    print(" +--------------------------------------+\n")
    print("Initializing... Please Wait...\n")
    
    global Targ_num
    global device
    Targ_num = 0
    log.basicConfig(filename='HUB.log', filemode='w')
    keys = all_devs.keys()   

    
    xbee_network = device.get_network()
    
    setup_dev(device, PROFILE_PATH)    
    #Look for devices in the network
    net_eye(keys, xbee_network)
    #Put this after to avoid null AT:NI
    device.add_data_received_callback(my_data_received_callback) 
    xbee_network.start_discovery_process() 
    print("opening Gui...\n")
    lock = threading.Lock()
    tgui = threading.Thread(target=go_gui, args=(lock,))
    tgui.start()
    print("Gui Opened! \n")
    
    #(+)++++Get current GPS location, this is home. We return here later.++++++
    
    iterations = 0    
    while 1:          
        net_eye(keys, xbee_network)
        print("Network has devices?: %s" %xbee_network.has_devices())
        if not xbee_network.has_devices():
            log.warning("No devices found. Can't fly. \n")
        
            #(+) Output warning in app
            
        #*************SEARCH ALGO DONE *****************
        
        #(+)++++++BROADCAST MY CURRENT GPS LOCATION++++++++++
        
        #broadcast_mess(device, "HUB " + HUBL)
        
        
        #Begin mission when we have some targets        
        print("Number targ: ", Targ_num)        
        print("Abort flag: ", AbortFlag)
        print("Iterations: ", iterations)
        
        
        if AbortFlag == True:
            Targ_num = 0
            iterations = 0
            print("Abort flag done")
            abort_mess = "Abort!"
            broadcast_mess(device, abort_mess)            
        elif (Targ_num > 0) and (iterations == 0):
            for x in Targs_list:
                print("Target: ", x)
                cal_dist = calc_distance(HUBL, x)
                print("Distance to target: ", cal_dist)
                if(cal_dist > 300):
                    print("The target: %s is outside the range of xbee mesh netwrok." %x)
                    completed_mission()   
                    Targs_list.remove(x)         
            if(Targ_num != 0):
                targ_Message = "Targ " + Targs_list[Targ_num - 1 ]
                print("Broadcasting targ")
                broadcast_mess(device, targ_Message)
            
        iterations = (iterations + 1)%2
        broadcast_mess(device, "Hello Drone.\n")
        

def set_abort():
    global AbortFlag
    AbortFlag = True

def net_eye(dev_list, net):
    net.clear()
    #net.start_discovery_process()
    discovered = net.discover_devices(dev_list)
    print(net.get_number_devices())
    for a in discovered:
        temp = str(a).split(" - ")        
        if all_devs.get(temp[1]) == "none":
            all_devs.update({temp[1] : temp[0]})
            print("updated dictionary: %s" %all_devs)      
    return
            
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
    print("Data received: %s from %s:  \n" %(data, na) )
    if data[0] == "Done!":
        makeProgress(0, 100)
    

def decode_gps(nums):
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
        
def completed_mission():
    global Targ_num
    Targ_num -= 1
    
def calc_distance(str_loc1, str_loc2):
    num_loc1 = decode_gps(str_loc1)
    num_loc2 = decode_gps(str_loc2)
    km_dist = haversine(num_loc1, num_loc2, unit=Unit.METERS)
    return km_dist
    
    
    
    
#***********************************************************************************************************
def go_gui(l):
    try:                
            #********************************************************
        #Button Pressed, lets get going
        def btnClickFunction():
                l.acquire()
                print('clicked Done')
                global HUBL
                global Targ_num
                HUBL = getHubLoc()
                selection = getRadioButtonValue()
                if selection == "":
                        log.warning("No radio selected.")
                elif selection == "one_targ":
                        print("Selected 1 targ")
                        #global Targ_num
                        Targ_num = 1
                        Targs_list.clear()
                        Targs_list.append(getTargetOne()) #string
                elif selection == "two_targs":
                        #global Targ_num
                        Targ_num = 2
                        Targs_list.clear()
                        Targs_list.append(getTargetTwo() )
                        Targs_list.append(getTargetOne() )                        
                elif selection == "thr_targs":
                        #global Targ_num
                        Targ_num = 3
                        Targs_list.clear()
                        Targs_list.append(getTargetThree() ) 
                        Targs_list.append(getTargetTwo() )
                        Targs_list.append(getTargetOne() )
                        
                l.release()
        
        #Abort flight mission        
        def Abort_btn():
                print('clicked Abort')                
                global AbortFlag
                AbortFlag = True

        #We can increase the progress bar to keep track of mission
        def makeProgress(val = 1, percent = 0):
                if percent != 0:
                    progessBarOne['value'] = percent
                else:
                    progessBarOne['value']=progessBarOne['value'] + val
                    root.update_idletasks()               
                
                
                
        # this is a function to get the selected radio button value
        def getRadioButtonValue():
                buttonSelected = Targ_Number.get()
                return buttonSelected
        
        
        # this is a function to get the user input from the text input box
        def getHubLoc():
                userInput = HUB_LOC.get()
                return userInput
        
        
        # this is a function to get the user input from the text input box
        def getTargetOne():
                userInput = targ_input_one.get()                
                return userInput
        
        
        # this is a function to get the user input from the text input box
        def getTargetTwo():
                userInput = targ_input_two.get()
                return userInput
        
        
        # this is a function to get the user input from the text input box
        def getTargetThree():
                userInput = targ_input_three.get()
                return userInput
                
        #**************************************************************************
        
        #Create Main Window
        root = Tk()
        root.geometry('790x490')
        root.configure(background='#30B700')
        root.title('Welcome to the Drone HUB')
        
        #Hub GPS Coordinates input
        Label(root, text='Please Input HUBs GPS coordinates (Longitude, Latitude)', bg='#82A3FF', font=('arial', 12, 'normal')).place(x=24, y=20)
        HUB_LOC=Entry(root)
        HUB_LOC.place(x=24, y=50)
        
        #Target inputs
        Label(root, text='Please Enter Target GPS Coordinates Below (Longitude, Latitude)', bg='#82A3FF', font=('arial', 12, 'normal')).place(x=24, y=90)
        targ_input_one=Entry(root)
        targ_input_one.place(x=24, y=120)
        targ_input_two=Entry(root)
        targ_input_two.place(x=24, y=160)        
        targ_input_three=Entry(root)
        targ_input_three.place(x=24, y=200)
                
        
        #Radio Buttons to know how many targets
        Targ_Number = tk.StringVar()
        frame=Frame(root, width=0, height=0, bg='#F7F749')
        frame.place(x=644, y=40)
        ARBEES=[
        ('1 Target', 'one_targ'), 
        ('2 Targets', 'two_targs'), 
        ('3 Targets', 'thr_targs'), 
        ]
        for text, mode in ARBEES:
            Targ_Sel=Radiobutton(frame, text=text, variable=Targ_Number, value=mode, bg='#F7F749', font=('arial', 12, 'normal')).pack(side='top', anchor = 'w')
            
        #Done Button to begin            
        Button(root, text='Done', bg='#08FF08', font=('arial', 12, 'normal'), command=btnClickFunction).place(x=44, y=250)
        
        #put a cute little picture ;) 
        Parrot_Fire= Canvas(root, height=400, width=400)
        picture_file = PhotoImage(file = '/home/drone/Documents/Drone_Hub/2AEIROS.gif')
        Parrot_Fire.create_image(400, 0, anchor=NE, image=picture_file)
        Parrot_Fire.place(x=234, y=160)
        
        # This is the section of code which creates a color style to be used with the progress bar
        progessBarOne_style = ttk.Style()
        progessBarOne_style.theme_use('clam')
        progessBarOne_style.configure('progessBarOne.Horizontal.TProgressbar', foreground='#00FFFF', background='#00FFFF')
        
        
        # This is the section of code which creates a progress bar
        progessBarOne=ttk.Progressbar(root, style='progessBarOne.Horizontal.TProgressbar', orient='horizontal', length=170, mode='determinate', maximum=100, value=1)
        progessBarOne.place(x=44, y=292)
        
        # Abort Button, cancel flight mission
        Button(root, text='Abort!', bg='#FF3030', font=('arial', 12, 'normal'), command=Abort_btn).place(x=44, y=330)
        
        root.mainloop()        
               
        
    except Exception as e:
        log.exception("\n******GUI****\nA GUI exception occured: \n")
        
#*************************************************************************************
    
if __name__ == '__main__':
    main()
    

