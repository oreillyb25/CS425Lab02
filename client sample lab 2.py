#python 3 code
import socket
from time import *
from pynput import keyboard
"""pynput: On Mac OSX, one of the following must be true:
* The process must run as root. OR
* Your application must be white listed under Enable access for assistive devices. Note that this might require that you package your application, since otherwise the entire Python installation must be white listed."""
import sys
import threading
import enum

socketLock = threading.Lock()

# You should fill this in with your states
class States(enum.Enum):
    #put ur states here
    LISTEN = enum.auto()
    WANDER = enum.auto()
    FIND_THE_DOOR = enum.auto()
    FOLLOWR = enum.auto()
    FOLLOWL = enum.auto()
    BACKR = enum.auto()
    BACKL = enum.auto()


# Not a thread because this is the main thread which can be important for GUI access
class StateMachine():

    def __init__(self):
        # CONFIGURATION PARAMETERS
        self.IP_ADDRESS = "192.168.1.106" 	# SET THIS TO THE RASPBERRY PI's IP ADDRESS
        self.CONTROLLER_PORT = 5001
        self.TIMEOUT = 10					# If its unable to connect after 10 seconds, give up.  Want this to be a while so robot can init.
        self.STATE = States.LISTEN
        self.RUNNING = True
        self.DIST = False
        self.THRESH = 2600
        
        # connect to the motorcontroller
        try:
            with socketLock:
                self.sock = socket.create_connection( (self.IP_ADDRESS, self.CONTROLLER_PORT), self.TIMEOUT)
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print("Connected to RP")
        except Exception as e:
            print("ERROR with socket connection", e)
            sys.exit(0)
    
        # Collect events until released
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()

    def main(self):
        # connect to the robot
        """ The i command will initialize the robot.  It enters the create into FULL mode which means it can drive off tables and over steps: be careful!"""
        with socketLock:
            self.sock.sendall("i /dev/ttyUSB0".encode())
            print("Sent command")
            result = self.sock.recv(128)
            print(result)
            if result.decode() != "i /dev/ttyUSB0":
                self.RUNNING = False
        
        self.sensors = Sensing(self.sock)
        # Start getting data
        self.sensors.start()

        # BEGINNING OF THE CONTROL LOOP
        while(self.RUNNING):
            sleep(0.1)
            print(self.STATE)
            if self.STATE == States.LISTEN:
                self.STATE = States.WANDER
                continue
            if self.STATE == States.WANDER:
                with socketLock:
                    self.sock.sendall("a drive_straight(25)".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a drive_straight(25)":
                        self.RUNNING = False

                if (int(self.sensors.cliffFL) > -1 and int(self.sensors.cliffFR) > -1 and
                self.sensors.cliffBL > -1 and self.sensors.cliffBR > -1):
                    if (self.sensors.cliffFR < self.THRESH):
                        self.STATE = States.FOLLOWR
                    elif(self.sensors.cliffFL < self.THRESH):
                        self.STATE = States.FOLLOWL
                    elif(self.sensors.cliffBR < self.THRESH):
                        self.STATE = States.BACKR
                    elif(self.sensors.cliffBL < self.THRESH):
                        self.STATE = States.BACKL
                    else:
                        self.STATE = States.LISTEN

                continue
            if self.STATE == States.FOLLOWR:
                with socketLock:
                    self.sock.sendall("a drive_direct(25,150)".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a drive_direct(25,150)":
                        self.RUNNING = False
                    self.sock.sendall("a set_song(0, [(80,32)])".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a set_song(0, [(80,32)])":
                        self.RUNNING = False
                    self.sock.sendall("a play_song(0)".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a play_song(0)":
                        self.RUNNING = False
                    sleep(.25)
                self.STATE = States.LISTEN
                continue
            if self.STATE == States.FOLLOWL:
                with socketLock:
                    self.sock.sendall("a drive_direct(150,25)".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a drive_direct(150,25)":
                        self.RUNNING = False
                    self.sock.sendall("a set_song(0, [(62,32)])".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a set_song(0, [(62,32)])":
                        self.RUNNING = False
                    self.sock.sendall("a play_song(0)".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a play_song(0)":
                        self.RUNNING = False
                    sleep(.25)

                self.STATE = States.LISTEN
                continue
            if self.STATE == States.BACKL:
                with socketLock:
                    self.sock.sendall("a spin_left(100)".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a spin_left(100)":
                        self.RUNNING = False
                    self.sock.sendall("a set_song(0, [(62,32)])".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a set_song(0, [(62,32)])":
                        self.RUNNING = False
                    self.sock.sendall("a play_song(0)".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a play_song(0)":
                        self.RUNNING = False
                    sleep(1)
                    self.STATE = States.LISTEN
            if self.STATE == States.BACKR:
                with socketLock:
                    self.sock.sendall("a spin_right(100)".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a spin_right(100)":
                        self.RUNNING = False
                    self.sock.sendall("a set_song(0, [(80,32)])".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a set_song(0, [(80,32)])":
                        self.RUNNING = False
                    self.sock.sendall("a play_song(0)".encode())
                    result = self.sock.recv(128)
                    if result.decode() != "a play_song(0)":
                        self.RUNNING = False
                    sleep(1)
                    self.STATE = States.LISTEN


            

        # END OF CONTROL LOOP
        
        # First stop any other threads talking to the robot
        self.sensors.RUNNING = False
        self.sensors.join()
        
        # Need to disconnect
        """ The c command stops the robot and disconnects.  The stop command will also reset the Create's mode to a battery safe PASSIVE.  It is very important to use this command!"""
        with socketLock:
            self.sock.sendall("c".encode())
            print(self.sock.recv(128))

        with socketLock:
            self.sock.close()
        # If the user didn't request to halt, we should stop listening anyways
        self.listener.stop()

    def on_press(self, key):
        # WARNING: DO NOT attempt to use the socket directly from here
        try:
            print('alphanumeric key {0} pressed'.format(key.char))
            if key.char == 'd':
                self.DIST = True
        except AttributeError:
            print('special key {0} pressed'.format(key))

    def on_release(self, key):
        # WARNING: DO NOT attempt to use the socket directly from here
        print('{0} released'.format(key))
        if key == keyboard.Key.esc or key == keyboard.Key.ctrl:
            # Stop listener
            self.RUNNING = False
            return False

# END OF STATEMACHINE


class Sensing(threading.Thread):
    cliffFL = -1
    cliffFR = -1
    cliffBL = -1
    cliffBR = -1

    def __init__(self, socket):
        threading.Thread.__init__(self)   # MUST call this to make sure we setup the thread correctly
        self.sock = socket
        self.RUNNING = True

    
    def run(self):
        while self.RUNNING:
            sleep(0.2)
            # This is where I would get a sensor update
            # Store it in this class
            # You can change the polling frequency to optimize performance, don't forget to use socketLock
            # must be MUST BE LISTEN TO ME in the format as seen!
            with socketLock:
                self.sock.sendall("a battery_charge".encode())
                print("Battery charge: ", self.sock.recv(128).decode())
            with socketLock:
                self.sock.sendall("a cliff_front_left_signal".encode())
                self.cliffFL = int(self.sock.recv(128).decode())
                print("Cliff Front Left Signal: ", self.cliffFL)
            with socketLock:
                self.sock.sendall("a cliff_front_right_signal".encode())
                self.cliffFR = int(self.sock.recv(128).decode())
                print("Cliff Front Right Signal: ", self.cliffFR)
            with socketLock:
                self.sock.sendall("a cliff_left_signal".encode())
                self.cliffBL = int(self.sock.recv(128).decode())
                print("Cliff Left Signal: ", self.cliffBL)
            with socketLock:
                self.sock.sendall("a cliff_right_signal".encode())
                self.cliffBR = int(self.sock.recv(128).decode())
                print("Cliff Right Signal: ", self.cliffBR)
# END OF SENSING


if __name__ == "__main__":
    sm = StateMachine()
    sm.main()


