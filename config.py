from json import *


class Config:

    def __init__(self, path):
        try:
            file = open(path, 'r')
            self.config_json = load(file)
            file.close()
            self.success = True
            self.error = ""
        except Exception as n:
            self.success = False
            self.error = n
        self.servers = self.config_json['servers']
        self.dhcp_count_jumps = self.config_json['dhcp_count_jumps']
