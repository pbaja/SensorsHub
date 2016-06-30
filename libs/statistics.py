import time, urllib.request

class Statistics(object):

    def __init__(self, core):
        self.core = core
        self.online_users = {}

    @staticmethod
    def snooper(status):
        """
            Send anonymous data to statistics server.

            status:
            0 - Sensorshub installed
            1 - Sensorshub runned at least once
            2 - User visited settings at least once
        """
        try:
            with open("machineid.txt") as m:
                urllib.request.urlopen("http://skew.tk/sensorshub?status={}&machineid={}".format(status,m.read())).read()
        except:
            pass

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