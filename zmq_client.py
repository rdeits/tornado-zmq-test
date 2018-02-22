import time
import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

for i in range(100):
    socket.send_string("hello {:d}".format(i))
    socket.recv()
    time.sleep(1)

