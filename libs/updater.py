import json, logging, zipfile, os, shutil, psutil, sys, stat
import urllib.request
import distutils.dir_util

class Updater(object):

    VERSION_URL = "https://raw.githubusercontent.com/SkewPL/SensorsHub/master/version.json"

    def __init__(self, core):
        self.core = core
        self.version = {}
        self.update_available = False

    def __chmod_x(self, f):
        try:
            st = os.stat(f)
            os.chmod(f, st.st_mode | stat.S_IEXEC)
        except:
            pass

    def check_updates(self):
        """Check if new version is available"""
        try:
            self.version = json.loads(urllib.request.urlopen(self.VERSION_URL).read().decode("UTF-8"))
            if self.version["latest"] > self.core.VERSION:
                self.update_available = True
                logging.info("")
                logging.info("New update available! Current version: {} Latest: {}".format(self.core.VERSION, self.version["latest"]))
                logging.info("To start automatic update, run this script with --update option")
                logging.info("")
                return True
            return False
        except urllib.error.HTTPError:
            logging.warning("Failed to check for updates")
            return False

    def update(self):
        """Downloads zip and uzip it with replacing files"""
        if self.version["latest"] > self.core.VERSION:
            try:
                url = self.version["url"]
                filename = url.split("/")[-1]

                logging.info("Downloading zip...")
                if not os.path.exists("update"):
                    os.mkdir("update")
                urllib.request.urlretrieve(url, "update/"+filename)

                logging.info("Extracting...")
                zip = zipfile.ZipFile("update/"+filename)
                zip.extractall("update")

                logging.info("Replacing files...")
                directory = next(os.walk('update'))[1][0]
                distutils.dir_util.copy_tree("update/"+directory, ".")

                logging.info("Removing update dir...")
                shutil.rmtree("update")

                logging.info("Configuring permissions...")
                self.__chmod_x("run.py")
                self.__chmod_x("run.sh")

                logging.info("Closing connections and restartnig script.")
                try:
                    p = psutil.Process(os.getpid())
                    for handler in p.open_files() + p.connections():
                        os.close(handler.fd)
                except Exception as e:
                    logging.error(e)

                python = sys.executable
                os.execl(python, python, *sys.argv)
                sys.exit(0)

            except Exception as e:
                logging.error("Failed to update. Exception: {}".format(e))
        else:
            logging.warning("Current version is latest, not updating")