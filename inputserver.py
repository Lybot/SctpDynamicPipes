import random
import socket

from middlesocket import *


class InputServer:

    # def add_address(self, address: str):
    #     """
    #     Функция добавления в ассоциации sctp-сокетов нового адреса (полученного с DHCP) (НЕ РАБОТАЕТ ! (пока что))
    #     :param address: добавляемый адрес
    #     :return: nothing
    #     """
    #     if self.is_server:
    #         # self.sctp_server.bindx([(address, self.output_port)])
    #         for connected_socket in self.sockets:
    #             connected_socket.bindx([("192.168.1.1", self.output_port)])
    #     else:
    #         for connected_socket in self.sockets:
    #             connected_socket.bindx([(address, self.output_port)])

    def receive_from_output(self, sctp_conn: sctp.sctpsocket):
        """
        Функция для обработки подключений к серверу. Создается промежуточный сокет (нужного типа TCP или UDP), который
        непосредственно подключается к необходимому порту.
        :param sctp_conn: подключенное соединение (типа sctp)
        :return: nothing
        """
        middle_socket = InputMiddleSocket(self.socket_style, "127.0.0.1", self.input_server_port, sctp_conn.sctp_send)
        while True:
            try:
                data = sctp_conn.sctp_recv(16500)
                # if data[2] == b"":
                #     middle_socket.sock.close()
                #     return
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
        sctp_middle_socket = OutputMiddleSocket(self.socket_style, self.output_server_address,
                                                self.output_server_port, socket_conn.send, self.current_bindx)
        while True:
            try:
                data = socket_conn.recv(16500)
                # if data == b"":
                #     sctp_middle_socket.sock.close()
                #     return
                sctp_middle_socket.send_packet(data)
            except KeyboardInterrupt:
                sys.exit(1)

    def update(self, current_bindx):
        """
        Функция обновления списка используемых адресов. Для серверов так же обновляется bind
        :param current_bindx: текущий список используемых адресов для sctp-сокетов
        :return:
        """
        # Проверка на то, является ли объект серверным
        if self.is_server:
            for bind in current_bindx:
                if not self.current_bindx.__contains__(bind):
                    # Объявляем саб интерфейс, чтобы нормально работала привязка (bindx)
                    exec_com("ifconfig eth0:1 {0}/24".format(bind))
                    self.sctp_server.bindx([(bind, self.output_server_port)])
            exec_com("ifconfig eth0:1 down")
            for bind in self.current_bindx:
                if not current_bindx.__contains__(bind):
                    # Удаляем старые привязки
                    self.sctp_server.bindx([(bind, self.output_server_port)], sctp.BINDX_REMOVE)
        self.current_bindx = current_bindx.copy()

    def __init__(self, input_client_port: int, input_server_port: int, output_server_port: int,
                 output_server_address: str, socket_style: any, is_server: bool):
        """
        Инициализация объекта на каждый объявляенный сервер из конфига. Если в конфиге данный хост указан, как server,
        то is_server = True, если клиент то - False. На каждый описанный в конфиге сервис должен быть создан объект
        данного класса!
        :param input_client_port: Порт для коннекта на клиентах
        :param input_server_port: Порт сервиса сервера (SSH, FTP, HTTP и т.д)
        :param output_server_port: Порт для SCTP - сервера (любой доступный)
        :param output_server_address: IP-Адрес для общения с клиентами
        :param socket_style: Тип сокета - socket.IPPROTO_TCP или socket.IPPROTO_UDP
        :param is_server: Сервер - True, Клиент - False
        """
        self.current_bindx = [socket.gethostbyname(output_server_address)]
        self.random = random.Random()
        self.is_server = is_server
        self.input_server_port = input_server_port
        self.input_client_port = input_client_port
        self.output_server_port = output_server_port
        self.socket_style = socket_style
        self.output_server_address = output_server_address
        if self.is_server:
            if socket_style == socket.IPPROTO_TCP:
                type_socket = sctp.TCP_STYLE
            else:
                type_socket = sctp.UDP_STYLE
            self.sctp_server = sctp.sctpsocket(socket.AF_INET, type_socket, None)
            # Параметр, позволяющий использовать порт несколько раз
            self.sctp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            for bind in self.current_bindx:
                self.sctp_server.bindx([(bind, self.output_server_port)])
            # Постановка сокета в состояние ожидания соединения (5 - очередь обслуживания)
            self.sctp_server.listen(5)
            thread = Thread(target=self.listen_output_connection)
            thread.start()
        else:
            # Для клиентов открывается внутренний сокет с нужным портом
            if socket_style == socket.IPPROTO_TCP:
                self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket_style)
                self.socket_client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket_client.bind(("127.0.0.1", self.input_client_port))
                self.socket_client.listen(5)
                thread = Thread(target=self.listen_input_connection_tcp)
                thread.start()
            else:
                self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket_style)
                self.socket_client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket_client.bind(("127.0.0.1", self.input_client_port))
                thread = Thread(target=self.listen_input_connection_udp)
                thread.start()

    def listen_output_connection(self):
        """
        Функция прослушивания серверного сокета. Каждый сокет обрабатывается в отдельном потоке.
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

    def listen_input_connection_tcp(self):
        """
        Функция прослушивания клиентского tcp сокета. Каждый сокет обрабатывается в отдельном потоке.
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

    def listen_input_connection_udp(self):
        """
        Функция прослушивания клиентского udp сокета.
        :return:
        """
        while True:
            try:
                data = self.socket_client.recvfrom(16500)  # client - установленное соединение.
                # 2-ой аргумент - адрес (не нужен здесь)
            except KeyboardInterrupt:
                sys.exit(1)
            except socket.error:  # данных нет
                pass  # если ошибка - пропускаем
            else:
                proc = Thread(target=self.receive_from_input, args=(data,))  # иначе обрабатываем клиента
                proc.start()
