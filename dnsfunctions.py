import dns
import dns.update
import dns.query
import dns.rdatatype
import dns.reversename
import sys
dns_name = "computer"
ttl = "30000"


def edit_dns(ip: str):
    dns_file_text = "domain computer\nnameserver {0}".format(ip)
    file = open("/etc/resolv.conf", "w")
    file.write(dns_file_text)
    file.close()


def dns_update_ip(host_name: str, host_ip: str, server_ip: str):
    update_message = dns.update.Update(dns_name)
    update_message.add(host_name, ttl, 'A', host_ip)
    test = dns.query.tcp(update_message, server_ip)

def dns_delete_host(host_name: str, server_ip):
    try:
        update_message = dns.update.Update(dns_name)
        update_message.delete(host_name)
        dns.query.tcp(update_message, server_ip)
    except Exception as n:
        print(n)

