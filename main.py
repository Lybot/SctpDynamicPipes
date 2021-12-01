import time as t
import re
from inputserver import *
from dnsfunctions import *
from config import *


def get_dhcp_ip(f_name):
    f = open(f_name, 'r')
    leases = str(f.read())
    try:
        ip = re.findall(r'dhcp-server-identifier (.*);', leases)[-1]
    except:
        ip = "192.168.0.1"
    f.close()
    return ip


def add_route(address: str):
    address = re.findall(r"(\d+\.\d+\.\d+)\.", address)[0]
    exec_com("route add -net {0}.0/24 eth0".format(address))


def get_veth_ip(virtual: bool):
    if virtual:
        cmd_result = exec_com("ifconfig eth0:0")[0]
    else:
        cmd_result = exec_com("ifconfig eth0")[0]
    ip = re.findall(r'(\d+\.\d+\.\d+\.\d+)', cmd_result)[0]
    return ip


def clear_eth():
    for i in range(0, 5):
        exec_com("ifconfig eth0:{0} down".format(i))


if sys.argv[1] is None:
    print("add host name")
    sys.exit(0)
config = Config("config.json")
clear_eth()
if config.success:
    print("Config загружен")
else:
    print("Ошибка {0}".format(config.error))
    sys.exit(0)
dhcp_mass_ip = []
host_name = sys.argv[1]
exec_com("killall -9 dhclient")
exec_com("dhclient -v eth0")
leases_fname = "/var/lib/dhcp/dhclient.leases"
dhcp_ip_address = get_dhcp_ip(leases_fname)  # читаем IP адрес DHCP сервера, записываем в переменную dhcp_ip_addr
edit_dns(dhcp_ip_address)
log_str = "[ + ] DHCP's IP is " + dhcp_ip_address
print(log_str)
current_ip = get_veth_ip(False)  # в данной переменной хранится текущий ip-адрес порта, к которому закреплен dhcp
dns_delete_host(host_name, dhcp_ip_address)
dns_update_ip(host_name, current_ip, dhcp_ip_address)
dhcp_mass_ip.insert(0, current_ip)
log_str = "[ + ] Ethernet interface was set. Eth0 has IP " + current_ip
print(log_str)
servers = []
for server_json in config.servers:
    if server_json['dns_name'] == host_name:  # если данный хост сервер сервиса
        if server_json['type_socket'] == "tcp":
            socket_json_type = socket.IPPROTO_TCP
        else:
            socket_json_type = socket.IPPROTO_UDP
        server = InputServer(server_json['input_client_port'], server_json['input_server_port'],
                             server_json['output_server_port'], server_json['dns_name'], socket_json_type, True)
        servers.append(server)
        print("Добавлен SCTP-сервер для сервиса на порту {0}".format(server_json['input_server_port']))
    else:  # если данный хост будет клиентом
        if server_json['type_socket'] == "tcp":
            socket_json_type = socket.IPPROTO_TCP
        else:
            socket_json_type = socket.IPPROTO_UDP
        server = InputServer(server_json['input_client_port'], server_json['input_server_port'],
                             server_json['output_server_port'], server_json['dns_name'], socket_json_type, False)
        servers.append(server)
        print("Добавлен SCTP-клиент для подключения к {0}:{1} на порту {2}".format(server_json['dns_name'],
                                                                                   server_json['input_server_port'],
                                                                                   server_json['input_client_port']))
while True:  # Основной цикл
    try:
        t.sleep(1)
        command = "ping " + str(dhcp_ip_address) + " -c 2"  # выполняем ping DHCP сервера
        ping_out = exec_com(command)[0]
        # извлекаем из вывода количество принятых от сервера ICMP пакетов
        pk_received = int(re.findall(r'(\d) received', ping_out)[-1])
        if pk_received < 1:  # если не принято ни одного пакет
            print("[ !!! ] DHCPserver is LOST")
            if dhcp_mass_ip.__len__() > (config.dhcp_count_jumps-1):
                exec_com("dhclient -v eth0:0")
                exec_com("ifconfig eth0 {0}/24".format(dhcp_mass_ip[config.dhcp_count_jumps-2]))
                dhcp_ip_address = get_dhcp_ip(leases_fname)
                new_ip = get_veth_ip(True)
                edit_dns(dhcp_ip_address)
                dhcp_mass_ip.insert(0, new_ip)
                # dns_delete_host(host_name, dhcp_ip_address, dhcp_mass_ip[config.dhcp_count_jumps])
                dns_delete_host(host_name, dhcp_ip_address)
                dns_update_ip(host_name, new_ip, dhcp_ip_address)
                dhcp_mass_ip.__delitem__(config.dhcp_count_jumps-1)
                for server in servers:
                    server.update(dhcp_mass_ip)
            else:
                exec_com("dhclient -v eth0:0")
                dhcp_ip_address = get_dhcp_ip(leases_fname)
                new_ip = get_veth_ip(True)
                edit_dns(dhcp_ip_address)
                dns_delete_host(host_name, dhcp_ip_address)
                dns_update_ip(host_name, new_ip, dhcp_ip_address)
                dhcp_mass_ip.insert(0, new_ip)
                for server in servers:
                    server.update(dhcp_mass_ip)
            exec_com("killall -9 dhclient")
            log_str = "[ + ] DHClient RESTARTED. Eth0: {0} / DHCP - {1}".format(new_ip, dhcp_ip_address)
            print(log_str)
    except Exception as n:
        print(n)
        # в случае ошибки ждем 5 с, повторяем цикл сначала
        exec_com("ifconfig eth0:0 down")
        exec_com("dhclient -v eth0")
        t.sleep(1)
