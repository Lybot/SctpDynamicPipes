import time as t
import subprocess as sp
import re
from inputserver import *
from dnsfunctions import *


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
    address = re.findall(r"\d+\.\d+\.\d+\.", address)[0]
    exec_com("route add -net {0}.0/24 eth0".format(address))


def get_veth_ip(virtual: bool):
    if virtual:
        cmd_result = exec_com("ifconfig eth0:0")[0]
    else:
        cmd_result = exec_com("ifconfig eth0")[0]
    ip = re.findall(r'(\d+\.\d+\.\d+\.\d+)', cmd_result)[0]
    return ip


def exec_com(command_string):
    p = sp.Popen(command_string, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    out, err = str(p.stdout.read()), str(p.stderr.read())
    return out, err


if sys.argv[1] is None:
    print("add host name")
    sys.exit(0)
host_name = sys.argv[1]
exec_com("dhclient -v eth0")
leases_fname = "/var/lib/dhcp/dhclient.leases"
dhcp_ip_address = get_dhcp_ip(leases_fname)  # читаем IP адрес DHCP сервера, записываем в переменную dhcp_ip_addr
edit_dns(dhcp_ip_address)
log_str = "[ + ] DHCP's IP is " + dhcp_ip_address
print(log_str)
current_ip = get_veth_ip(False)  # в данной переменной хранится текущий ip-адрес порта, к которому закреплен dhcp
dns_delete_host(host_name, dhcp_ip_address)
dns_update_ip(host_name, current_ip, dhcp_ip_address)
log_str = "[ + ] Ethernet interface was set. Eth0 has IP " + current_ip
print(log_str)
if sys.argv[2] == "server":
    server = InputServer(current_ip, 22, 5000, "keker.computer", socket.IPPROTO_TCP, True)
    log_str = "[ + ] sctp-server запущен"
else:
    server = InputServer(current_ip, 5001, 5000, "keker.computer", socket.IPPROTO_TCP, False)
    log_str = "[ + ] sctp-client запущен"
print(log_str)
# Основной цикл
while True:
    try:
        t.sleep(1)
        command = "ping " + str(dhcp_ip_address) + " -c 2"  # выполняем ping DHCP сервера
        ping_out = exec_com(command)[0]
        # извлекаем из вывода количество принятых от сервера ICMP пакетов
        pk_received = int(re.findall(r'(\d) received', ping_out)[-1])
        if pk_received < 1:  # если не принято ни одного пакет
            print("[ !!! ] DHCPserver is LOST")
            exec_com("dhclient -v eth0:0")  # перезапускаем DHCP клиент
            # exec_com("killall -9 dhclient")
            dhcp_ip_address = get_dhcp_ip(leases_fname)
            edit_dns(dhcp_ip_address)
            # получаем новый адрес сервера
            #edit_dhcp_conf(dhcp_ip_address)
            #exec_com("dhclient -v eth0:0")
            new_ip = get_veth_ip(True)
            dns_delete_host(host_name, dhcp_ip_address)
            dns_update_ip(host_name, new_ip, dhcp_ip_address)
            try:
                server.add_address(new_ip)
            except Exception as n:
                print(n)
                pass
            exec_com("ifconfig eth0:0 down")
            t.sleep(5)
            exec_com("dhclient -v eth0")
            add_route(current_ip)
            # server.reconnect()
            log_str = "[ + ] DHClient RESTARTED. Eth0: {0} / DHCP - {1}".format(new_ip, dhcp_ip_address)
            print(log_str)
            current_ip = new_ip
        t.sleep(0.5)
    except Exception as n:
        print(n)
        # в случае ошибки ждем 5 с, повторяем цикл сначала
        exec_com("ifconfig eth0:0 down")
        exec_com("dhclient -v eth0")
        t.sleep(1)
