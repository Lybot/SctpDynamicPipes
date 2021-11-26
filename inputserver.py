import random
import socket

import sctp

from middlesocket import *


# list_ip = ["192.168.1.10"]
class InputServer:

    def get_random_port(self):
        return self.random.randint(1000, 5000)

    def reconnect(self):
        if self.is_server:
            for sock in self.sockets:
                sock.close()
        else:
            self.socket_client.setblocking(True)
            for connected_socket in self.sockets:
                connected_socket.reconnect()
            self.socket_client.setblocking(False)

    def add_address(self, address: str):
        """
        Функция добавления в ассоциации sctp-сокетов нового адреса (полученного с DHCP)
        :param address: добавляемый адрес
        :return: nothing
        """
        if self.is_server:
            # self.sctp_server.bindx([(address, self.output_port)])
            for connected_socket in self.sockets:
                connected_socket
                connected_socket.bindx((address, self.output_port))
        else:
            for connected_socket in self.sockets:
                connected_socket.bindx([(address, self.output_port)])

    def receive_from_output(self, sctp_conn: sctp.sctpsocket):
        """
        Функция для обработки подключений к серверу. Создается промежуточный сокет (нужного типа TCP или UDP), который
        непосредственно подключается к необходимому порту.
        :param sctp_conn: подключенное соединение (типа sctp)
        :return: nothing
        """
        # port = self.get_random_port()
        # sctp_conn.bindx([("192.168.1.1", self.output_port)], sctp.BINDX_ADD)
        # sctp_conn.bindx([(self.input_address, self.output_port)], sctp.BINDX_REMOVE)
        # sctp_conn.sock().bind()
        middle_socket = InputMiddleSocket(self.socket_style, "127.0.0.1", self.input_port, sctp_conn.sctp_send)
        self.sockets.append(sctp_conn)
        while True:
            try:
                data = sctp_conn.sctp_recv(16500)
                if data[2] == b"":
                    middle_socket.sock.close()
                    return
                middle_socket.send_packet(data[2])
            except KeyboardInterrupt:
                sys.exit(1)

    def receive_from_input(self, socket_conn: socket.socket):
        """
        Функция для обработки внутренних соединений. Создается sctp сокет, который подключается к необходимому хосту
        (где уже работает sctp_server).
        :param socket_conn: подключенное соединение (типа TCP или UDP)
        :return: nothing
        """
        sctp_middle_socket = OutputMiddleSocket(self.socket_style, self.input_address, self.output_address,
                                                self.output_port, socket_conn.send)
        self.sockets.append(sctp_middle_socket)
        while True:
            try:
                data = socket_conn.recv(16500)
                if data == b"":
                    sctp_middle_socket.sock.close()
                    return
                sctp_middle_socket.send_packet(data)
            except KeyboardInterrupt:
                sys.exit(1)

    def __init__(self, input_address: str, input_port: int, output_port: int, output_address: str, socket_style: any,
                 is_server: bool):
        self.random = random.Random()
        self.sockets = []
        self.is_server = is_server
        self.input_address = input_address
        self.input_port = input_port
        self.output_port = output_port
        self.socket_style = socket_style
        self.output_address = output_address
        if self.is_server:
            if socket_style == socket.IPPROTO_TCP:
                type_socket = sctp.TCP_STYLE
            else:
                type_socket = sctp.UDP_STYLE
            self.sctp_server = sctp.sctpsocket(socket.AF_INET, type_socket, None)
            # Параметр, позволяющий использовать порт несколько раз
            self.sctp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sctp_server.bindx([("0.0.0.0", self.output_port)])
            # Постановка сокета в состояние ожидания соединения (5 - очередь обслуживания)
            self.sctp_server.listen(5)
            thread = Thread(target=self.listen_output_connection)
            thread.start()
        else:
            self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket_style)
            self.socket_client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket_client.bind(("127.0.0.1", self.input_port))
            self.socket_client.listen(5)
            thread = Thread(target=self.listen_input_connection)
            thread.start()

    def listen_output_connection(self):
        """
        Функция прослушивания серверного сокета
        :return:
        """
        while True:
            try:
                client, _ = self.sctp_server.accept()  # client - установленное соединение.
                # 2-ой аргумент - адрес (не нужен здесь)
            except KeyboardInterrupt:
                sys.exit(1)
            except socket.error:  # данных нет
                pass  # если ошибка - пропускаем
            else:
                proc = Thread(target=self.receive_from_output, args=(client,))  # иначе обрабатываем клиента
                proc.start()

    def listen_input_connection(self):
        """
        Функция прослушивания серверного сокета
        :return:
        """
        while True:
            try:
                client, _ = self.socket_client.accept()  # client - установленное соединение.
                # 2-ой аргумент - адрес (не нужен здесь)
            except KeyboardInterrupt:
                sys.exit(1)
            except socket.error:  # данных нет
                pass  # если ошибка - пропускаем
            else:
                proc = Thread(target=self.receive_from_input, args=(client,))  # иначе обрабатываем клиента
                proc.start()
