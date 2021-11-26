import socket
from threading import Thread
import sctp
import sys


class InputMiddleSocket:

    def __init__(self, type_sock: int, address: str, port: int, send_func):
        self.send_func = send_func
        self.address = address
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, type_sock)
        self.sock.connect((address, port))
        self.read_process = Thread(target=self.receive_packets)
        self.read_process.start()

    def send_packet(self, packet: bytes):
        self.sock.send(packet)

    def receive_packets(self):
        while True:
            try:
                data = self.sock.recv(16500)
                if data == b"":
                    self.sock.close()
                    return
                if data:
                    self.send_func(data)
            except KeyboardInterrupt:
                sys.exit(1)


class OutputMiddleSocket:
    def __init__(self, type_sock: int, my_address: str, output_address: str, output_port: int, send_func):
        self.send_func = send_func
        self.output_address = output_address
        self.output_port = output_port
        self.type_sock = type_sock
        if self.type_sock == socket.IPPROTO_TCP:
            type_input_socket = sctp.TCP_STYLE
        else:
            type_input_socket = sctp.UDP_STYLE
        self.sock = sctp.sctpsocket(socket.AF_INET, type_input_socket, None)
        # self.add_address(my_address, output_port)
        self.sock.connectx([(socket.gethostbyname(self.output_address), self.output_port)])
        self.read_process = Thread(target=self.receive_packets)
        self.working = True
        self.read_process.start()

    def bindx(self, address):
        self.sock.bindx(address)

    def reconnect(self):
        self.working = False
        self.sock.sock().close()
        if self.type_sock == socket.IPPROTO_TCP:
            type_input_socket = sctp.TCP_STYLE
        else:
            type_input_socket = sctp.UDP_STYLE
        self.sock = sctp.sctpsocket(socket.AF_INET, type_input_socket, None)
        # self.add_address(my_address, output_port)
        self.sock.connectx([(socket.gethostbyname(self.output_address), self.output_port)])
        self.read_process = Thread(target=self.receive_packets)
        self.read_process.start()

    def bind(self, address):
        self.sock.bind(address)

    def add_address(self, address, port):
        self.sock.bindx([(address, port)])

    def send_packet(self, packet: bytes):
        self.sock.send(packet)

    def receive_packets(self):
        while True & self.working:
            try:
                data = self.sock.recv(16500)
                if data == b"":
                    self.sock.close()
                    return
                if data:
                    self.send_func(data)
            except KeyboardInterrupt:
                sys.exit(1)
