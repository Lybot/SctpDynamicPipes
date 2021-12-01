import dns
import dns.update
import dns.query
import dns.rdatatype
import dns.reversename
dns_name = "computer" # Система настроена на работу в домене computer
ttl = "30000" # Время жизни записи в секундах


def edit_dns(ip: str):
    """
    Изменяет файл /etc/resolv.conf для актуальности адреса dns-сервера (он тоже меняет ip)
    :param ip: новый ip адрес dns-сервера
    :return:
    """
    dns_file_text = "domain computer\nnameserver {0}".format(ip)
    file = open("/etc/resolv.conf", "w")
    file.write(dns_file_text)
    file.close()


def dns_update_ip(host_name: str, host_ip: str, server_ip: str):
    """
    Функция динамического изменения адресов DNS-сервера. Добавляет новый ip-адрес к выбранному хосту.
    :param host_name: хост, которому присваивается адрес
    :param host_ip: новый ip-адрес
    :param server_ip: ip-адрес dns-сервера
    :return:
    """
    update_message = dns.update.Update(dns_name)
    update_message.add(host_name, ttl, 'A', host_ip)
    dns.query.tcp(update_message, server_ip)


def dns_delete_host(host_name: str, server_ip, host_ip=""):
    """
    Функция удаления определенного/всех ip-адресов хоста
    :param host_name: хост, у которого удаляются адреса
    :param server_ip: ip-адрес dns-сервера
    :param host_ip: ip-адрес, который нужно удалить. Пустая строка, если нужно удалить все
    :return:
    """
    try:
        update_message = dns.update.Update(dns_name)
        if host_ip == "":
            update_message.delete(host_name)
        else:
            update_message.delete(host_name, 'A', host_ip)
        dns.query.tcp(update_message, server_ip)
    except Exception as n:
        print(n)

