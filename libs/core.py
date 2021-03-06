import os, sys
import sqlite3
import cherrypy
import json
import datetime
import logging

from jinja2 import Environment, FileSystemLoader
from libs.accounts import Accounts
from libs.sensors import Sensors
from libs.config import Config
from libs.lang import Lang
from libs.web import WebRoot
from libs.settings import WebSettings
from libs.updater import Updater
from libs.statistics import Statistics

class Core(object):

    VERSION = 0.06

    def __init__(self):
        # Configure logger
        logFormatter = logging.Formatter(fmt="[%(asctime)-15s][%(levelname)s] %(message)s", datefmt='%d.%m.%Y %H:%M:%S')
        log = logging.getLogger()
        log.setLevel(logging.DEBUG)

        fileName = "logs/"+"sensorshub_{}_".format(datetime.datetime.now().strftime("%d-%m-%Y"))+"{}.log"
        fileNum = 0

        if not os.path.isdir("logs"):
            os.mkdir("logs")

        while os.path.isfile(fileName.format(fileNum)):
            fileNum += 1

        fileHandler = logging.FileHandler(fileName.format(fileNum))
        fileHandler.setFormatter(logFormatter)
        log.addHandler(fileHandler)

        consoleHandler = logging.StreamHandler(sys.stdout)
        consoleHandler.setFormatter(logFormatter)
        log.addHandler(consoleHandler)

        logging.info("Starting SensorsHub version {}".format(self.VERSION))

        # Create databse and tables
        with sqlite3.connect("db.sqlite") as conn:

            #
            # SENSORS
            # Table for sensors, each sensor has one row.
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sensors("
                "sid INTEGER PRIMARY KEY AUTOINCREMENT, " # Sensor ID, must be unique
                "token TEXT, " # Generated string for authentication
                "title TEXT, " # Title of the sensor, f.eg. Outside
                "description TEXT, " # Description of the sensor, f.eg. ESP8266 temperature sensor
                "updated INTEGER, " # Timestamp updated when new reading is received
                "status INTEGER DEFAULT 0" # Current status (enabled, disabled)
                ")")

            # FIELDS
            conn.execute(
                "CREATE TABLE IF NOT EXISTS fields("
                "fid INTEGER PRIMARY KEY AUTOINCREMENT, " # Field ID, must be unique
                "sid INTEGER, " # Sensor ID to which this field belong
                "parent INTEGER" # Parent fid, default None
                "type INTEGER" # Field type
                "updated INTEGER, " # Updated time in timestamp format
                "value FLOAT, " # Current field value
                "name TEXT, " # Name of the field, f.eg. temperature
                "display_name TEXT, " # Human friendly name of the field, f.eg. Temperature
                "color TEXT, " # Color (HEX) of the field without hashtag, f.eg. FF00AA
                "icon TEXT" # Font awesome icon f.eg. fa-sun-o
                "unit TEXT)") # Unit of the field, f.eg. &deg;C

            #
            # READINGS
            # Table for readings, each reding must specify field and sensor
            #
            # sid - Sensor ID to which this reading belong
            # fid - Field ID to which this reading belong
            # updated - When reading has been created in timestamp format
            # value - New value of the field
            conn.execute(
                """CREATE TABLE IF NOT EXISTS readings(sid INTEGER, fid INTEGER, updated INT, value FLOAT)""")

            #
            # ACCOUNTS
            # Table for accounts
            #
            # uid - User ID, must be unique
            # session - Generated string for sessions
            # user - Unique user login
            # password - Hashed password using hashlib
            # lastlogin - Timestamp updated when user logged in
            # email - User email
            conn.execute(
                """CREATE TABLE IF NOT EXISTS accounts(uid INTEGER PRIMARY KEY, session TEXT, user TEXT UNIQUE , password TEXT, lastlogin INTEGER, email TEXT)""")

        # Load config
        self.config = Config()
        self.config.load()

        # Load lang
        self.lang = Lang(self)
        self.lang.load()

        # Load updater
        self.updater = Updater(self)
        if self.updater.check_updates():
            if "update" in self.config.args:
                logging.info("Starting auto update")
                self.updater.update()
        else:
            logging.info("No updates available")

        # Create and read sensors from database
        self.sensors = Sensors()
        self.sensors.load()

        # Create and load accounts
        self.accounts = Accounts(self)

        # Load statistics
        self.statistics = Statistics(self)

        # Configure web template engine
        env = Environment(loader=FileSystemLoader('templates'))
        env.filters["to_json"] = lambda value: json.dumps(value)

        def format_datetime(value, format="%d.%m.%Y %H:%M"):
            if value == None:
                return "Never"
            else:
                try:
                    return datetime.datetime.fromtimestamp(value).strftime(format)
                except TypeError:
                    return value.strftime(format)
        env.filters["strftime"] = format_datetime

        # Configure web server
        cherrypy_config = {
            "server.socket_port": self.config.get("port"),
            "server.socket_host": self.config.get("host"),
            "checker.check_skipped_app_config": False,
            "log.screen": False,
            "log.access_file": '',
            "log.error_file": ''
        }
        cherrypy.config.update(cherrypy_config)
        cherrypy.tree.mount(WebRoot(self,env),"/", {
            "/static": {
                "tools.staticdir.root": os.getcwd(),
                "tools.staticdir.on": True,
                "tools.staticdir.dir": "static"
            }
        })
        cherrypy.tree.mount(WebSettings(self, env), "/settings", {

        })

        # Disable cherrypy loggers
        logging.info("Starting up web server at {}:{}".format(cherrypy_config["server.socket_host"], cherrypy_config["server.socket_port"]))

        logging.getLogger("cherrypy").propagate = False
        #logging.getLogger("cherrypy.error").propagate = False
        logging.getLogger("cherrypy.access").propagate = False

        cherrypy.engine.signals.subscribe()
        cherrypy.engine.start()

        logging.info("Done loading")
        Statistics.snooper(1)
        cherrypy.engine.block()

    def get_client_ip(self):
        headers = cherrypy.request.headers
        if "X-Forwarded-For" in headers and headers["X-Forwarded-For"] != "127.0.0.1":
            return headers["X-Forwarded-For"]
        if "X-Forwarded" in headers and headers["X-Forwarded"] != "127.0.0.1":
            return headers["X-Forwarded"]
        if "Remote-Addr" in headers and headers["Remote-Addr"] != "127.0.0.1":
            return headers["Remote-Addr"]
        return "0.0.0.0"