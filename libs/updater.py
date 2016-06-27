import json, logging, zipfile
import urllib.request

class Updater(object):

    VERSION_URL = "https://raw.githubusercontent.com/SkewPL/SensorsHub/master/version.json"

    def __init__(self, core):
        self.core = core

    def check_updates(self):
        """Check if new version is available"""
        try:
            self.version = json.loads(urllib.request.urlopen(self.VERSION_URL).read().decode("UTF-8"))
            return self.version["latest"] > self.core.VERSION
        except urllib.error.HTTPError:
            logging.warning("Failed to check for updates")
            return False

    def update(self):
        """Downloads zip and uzip it with replacing files"""
        if self.version["latest"] > self.core.VERSION:
            try:
                url = self.version["url"]
                filename = url.split("/")[-1]
                urllib.urlretrieve(url, filename)

                zip = zipfile.ZipFile(filename)
                #zip.extractall()
                
            except Exception as e:
                logging.error("Failed to update. Exception: {}".format(e))
        else:
            logging.warning("Current version is latest, not updating")