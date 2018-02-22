from __future__ import absolute_import, division, print_function

import os
import multiprocessing

import tornado.web
import tornado.ioloop
import tornado.websocket

import zmq
from zmq.eventloop import ioloop
from zmq.eventloop.zmqstream import ZMQStream

# Install ZMQ ioloop instead of a tornado ioloop
# http://zeromq.github.com/pyzmq/eventloop.html
ioloop.install()


DEFAULT_FILESERVER_PORT = 7000
MAX_ATTEMPTS = 1000
DEFAULT_ZMQ_METHOD = "tcp"
DEFAULT_ZMQ_PORT = 6000


def find_available_port(func, default_port, max_attempts=MAX_ATTEMPTS):
    for i in range(max_attempts):
        port = default_port + i
        try:
            return func(port), port
        except OSError as e:
            print("Port: {:d} in use, trying another...".format(port))
            pass
    else:
        raise(Exception("Could not find an available port in the range: [{:d}, {:d})".format(default_port, max_attempts + default_port)))


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, websocket_pool=None, **kwargs):
        super(WebSocketHandler, self).__init__(*args, **kwargs)
        self.websocket_pool = websocket_pool

    def open(self):
        self.websocket_pool.add(self)
        print("opened:", self)

    def on_message(self, message):
        print("got message:", message)

    def on_close(self):
        self.websocket_pool.remove(self)
        print("closed:", self)


class ZMQWebsocketBridge(object):
    context = zmq.Context()

    def __init__(self, zmq_url=None, host="127.0.0.1", port=None):
        self.host = host
        self.websocket_pool = set()
        self.app = self.make_app()

        if zmq_url is None:
            def f(port):
                return self.setup_zmq("{:s}://{:s}:{:d}".format(DEFAULT_ZMQ_METHOD, self.host, port))
            (self.zmq_socket, self.zmq_stream, self.zmq_url), _ = find_available_port(f, DEFAULT_ZMQ_PORT)
        else:
            self.zmq_socket, self.zmq_stream, self.zmq_url = self.setup_zmq(zmq_url)
        print("ZMQ socket listening at {url}".format(url=self.zmq_url))

        if port is None:
            _, self.fileserver_port = find_available_port(self.app.listen, DEFAULT_FILESERVER_PORT)
        else:
            self.app.listen(port)
            self.fileserver_port = port
        self.web_url = "http://{host}:{port}/static/".format(host=self.host, port=self.fileserver_port)
        print("Serving files at {url}".format(url=self.web_url))

    def make_app(self):
        return tornado.web.Application([
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": os.path.dirname(__file__), "default_filename": "test.html"}),
            (r"/", WebSocketHandler, {"websocket_pool": self.websocket_pool})
        ])

    def send_to_websockets(self, msg):
        print("msg:", msg)
        for websocket in self.websocket_pool:
            websocket.write_message(msg[0])
        self.zmq_socket.send(b"ok")

    def setup_zmq(self, url):
        zmq_socket = self.context.socket(zmq.REP)
        zmq_socket.bind(url)
        zmq_stream = ZMQStream(zmq_socket)
        zmq_stream.on_recv(self.send_to_websockets)
        return zmq_socket, zmq_stream, url

    def run(self):
        tornado.ioloop.IOLoop.current().start()


def _run_server(queue, **kwargs):
    bridge = ZMQWebsocketBridge(**kwargs)
    queue.put((bridge.zmq_url, bridge.web_url))
    bridge.run()

def create_server(*args, **kwargs):
    queue = multiprocessing.Queue()
    proc = multiprocessing.Process(target=_run_server, args=(queue,), kwargs=kwargs)
    proc.daemon = True
    proc.start()
    return proc, queue.get()


if __name__ == '__main__':
    proc, (zmq_url, web_url) = create_server()
    print(proc, zmq_url, web_url)
    # bridge = ZMQWebsocketBridge()

    import webbrowser
    webbrowser.open(web_url)

    tornado.ioloop.IOLoop.current().start()
