from __future__ import absolute_import, division, print_function

import os

import tornado.web
import tornado.ioloop
import tornado.websocket

import zmq
from zmq.eventloop import ioloop
from zmq.eventloop.zmqstream import ZMQStream

# Install ZMQ ioloop instead of a tornado ioloop
# http://zeromq.github.com/pyzmq/eventloop.html
ioloop.install()

connections = set()


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        connections.add(self)
        print("opened:", self)

    def on_message(self, message):
        print("got message:", message)

    def on_close(self):
        connections.remove(self)
        print("closed:", self)


def setup_zmq():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    stream = ZMQStream(socket)

    def publish_to_websockets(msg):
        print("msg:", msg)
        for websocket in connections:
            websocket.write_message(msg[0])
        socket.send(b"ok")

    stream.on_recv(publish_to_websockets)
    return stream

def make_app():
    return tornado.web.Application([
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": os.path.dirname(__file__), "default_filename": "test.html"}),
        (r"/", WebSocketHandler)
    ])

if __name__ == '__main__':
    stream = setup_zmq()
    app = make_app()
    app.listen(8888)

    import webbrowser
    webbrowser.open("http://localhost:8888/static/")

    tornado.ioloop.IOLoop.current().start()
