import time

class Statistics(object):

    def __init__(self, core):
        self.core = core
        self.online_users = {}

    def online(self):
        self.online_users[self.core.get_client_ip()] = time.time()

    def currently_online(self):
        counter = 0
        for key, value in list(self.online_users.items()):
            if time.time() - value > 30:
                del self.online_users[key]
            else:
                counter += 1
        return counter