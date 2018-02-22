import time
import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:6000")

for i in range(100):
    now = time.time()
    socket.send_string("hello {:d}".format(i))
    socket.recv()
    print(time.time() - now)
    time.sleep(1)

