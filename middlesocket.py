import socket
from threading import Thread
import sctp
import sys
import subprocess as sp


def exec_com(command_string):
    """
    Функция выполнения команд в bash
    :param command_string: команда
    :return: turple[str,str]. [0] - вывод результата команды (если есть). [1] - вывод ошибки (если есть)
    """
    p = sp.Popen(command_string, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    out, err = str(p.stdout.read()), str(p.stderr.read())
    return out, err


class InputMiddleSocket:
    """
    Промежуточный сокет для серверного sctp-сокета. Создает соединение с внутренним сервисом по определенному порту.
    """
    def __init__(self, type_sock: int, address: str, port: int, send_func):
        """
        Инициализация внутренного серверного сокета
        :param type_sock: Тип сокета сервиса (socket.IPPROTO_TCP или socket.IPPROTO_UDP)
        :param address: Адрес для подключения сокета (обычно 127.0.0.1)
        :param port: Порт для подключения сокета
        :param send_func: Функция для переброса пакетов на другой сокет. В данном системе сюда передается функция
        передачи sctp сокета.
        """
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
        """
        Функция приема пакетов на внутреннем сервером сокете. Каждый пакет перебрасывается на sctp-сокет.
        :return:
        """
        while True:
            try:
                data = self.sock.recv(16500)
                # if data == b"":  # При закрытии сокета обычно посылаются пустые байты,
                #     # в таком случае мы тоже закрываем сокет и закрываем поток (return)
                #     self.sock.close()
                #     return
                if data:  # если есть что передать
                    self.send_func(data)
            except KeyboardInterrupt:
                sys.exit(1)


class OutputMiddleSocket:
    """
    Промежуточный сокет для клиентского sctp-сокета. Создает соединение с другим хостом по SCTP
    """
    def __init__(self, type_sock: int, output_address: str, output_port: int, send_func, current_bindx):
        """
        Инициализация клиентского sctp-сокета
        :param type_sock: Тип сокета (socket.IPPROTO_TCP или socket.IPPROTO_UDP)
        :param output_address: ip-адрес для коннекта
        :param output_port: порт для коннекта
        :param send_func: функция отправки пакетов на внутренний сокет
        :param current_bindx: текущий список используемых ip-адресов для соединения
        """
        self.send_func = send_func
        self.output_address = output_address
        self.output_port = output_port
        self.type_sock = type_sock
        if self.type_sock == socket.IPPROTO_TCP:
            type_input_socket = sctp.TCP_STYLE
        else:
            type_input_socket = sctp.UDP_STYLE
        self.sock = sctp.sctpsocket(socket.AF_INET, type_input_socket, None)
        i = 1
        # Для коннекта со всеми ip-адресами надо создать саб интерфейсы с ними
        for bind in current_bindx:
            exec_com("ifconfig eth0:{0} {1}/24".format(i, bind))
            i += 1
        test = socket.gethostbyname(self.output_address)
        self.sock.connectx([(test, self.output_port)])
        # Затем удаляем саб интерфейсы
        for j in range(1, i):
            exec_com("ifconfig eth0:{0} down".format(j))
        self.read_process = Thread(target=self.receive_packets)
        self.working = True
        self.read_process.start()

    def send_packet(self, packet: bytes):
        self.sock.send(packet)

    def receive_packets(self):
        while True & self.working:
            try:
                data = self.sock.recv(16500)
                # if data == b"":
                #     self.sock.close()
                #     return
                if data:
                    self.send_func(data)
            except KeyboardInterrupt:
                sys.exit(1)
