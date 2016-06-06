#!/usr/bin/python3.4
import cherrypy, os, json, sqlite3, time, datetime
from jinja2 import Environment, FileSystemLoader

from sensors import Sensors
from accounts import Accounts

class Core(object):
    def __init__(self):
        # Create databse and tables
        with sqlite3.connect("db.sqlite") as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS sensors(sid INTEGER PRIMARY KEY, token TEXT, title TEXT, description TEXT, updated INTEGER)""")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS readings(sid, updated INT, value FLOAT, battery FLOAT)""")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS accounts(uid INTEGER PRIMARY KEY, session TEXT, user TEXT, password TEXT, lastlogin INTEGER, email TEXT)""")

        # Create and read sensors from database
        self.sensors = Sensors()
        self.sensors.load()

        # Create and load accounts
        self.accounts = Accounts()

        # Create website
        cherrypy.config.update({
            "server.socket_port": 5000,
            "server.socket_host": "0.0.0.0"
        })
        cherrypy.quickstart(WebRoot(self), "/", {
            "/static": {
                "tools.staticdir.root": os.getcwd(),
                "tools.staticdir.on": True,
                "tools.staticdir.dir": "static"
            }
        })

class WebRoot(object):

    def __init__(self, core):
        # Load templates
        self.env = Environment(loader=FileSystemLoader('templates'))

        def to_json(value): return json.dumps(value)
        self.env.filters["to_json"] = to_json

        def format_datetime(value, format="%d.%m.%Y %H:%M"): return datetime.datetime.fromtimestamp(value).strftime(format)
        self.env.filters["strftime"] = format_datetime

        # Save core object
        self.core = core

    @cherrypy.expose
    def index(self):
        return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors)

    @cherrypy.expose
    def single(self, *args, **kwargs):
        if len(args) != 1: raise cherrypy.HTTPRedirect("/index")

        sensor = self.core.sensors.get(int(args[0]))
        settings = {}

        # Get settings from kwargs
        settings = {"group": None, "range": None}
        for arg, value in kwargs.items():
            arg = arg.split("_")
            settings.update({arg[0]: value})

        if sensor:
            # Group by
            group_by = "15M"
            group_labels = "%H:%M"
            if settings["group"]:
                group_by = settings["group"]
                time = (2208989361.0 + datetime.datetime.strptime(group_by[:-1], "%" + group_by[-1]).timestamp()) / 60.0
                if time >= 525600: group_labels = "%Y"
                elif time >= 1440: group_labels = "%d.%m"
            else:
                settings["group"] = "15M"

            # In range
            range = 60 * 60 * 24
            if settings["range"]:
                range = 60 * 60 * int(settings["range"])
            else:
                settings["range"] = "24"

            # Read all readings
            labels = []
            values = []
            voltages = []
            average = 0.0
            readings = sensor.get_readings(range, group_by)
            for reading in readings:
                labels.append(datetime.datetime.fromtimestamp(reading.updated).strftime(group_labels))
                values.append(round(reading.value, 2))
                voltages.append(round(reading.battery, 2))
                average += reading.value

            average /= len(readings) if len(readings) > 0 else 1

            # Create data for chart
            data = {
                "sid": sensor.sid,
                "average": round(average, 2),
                "data": {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Temperature",
                            "data": values,
                            "fill": False,
                            "borderColor": "#FF9000",
                        },
                        {
                            "label": "Battery",
                            "data": voltages,
                            "fill": False,
                            "borderColor": "#0079C4",
                        }
                    ]
                }
            };

            return self.env.get_template('single.html').render(sensor=sensor, data=json.dumps(data), settings=settings)

    @cherrypy.expose
    def singlesss(self, *args, **kwargs):
        sensors = self.core.sensors.sensors[:]
        data = []
        settings = {}

        # Get settings from kwargs
        for sensor in sensors:
            settings[sensor.sid] = {"group": None, "range": None}
        for arg, value in kwargs.items():
            arg = arg.split("_")
            settings[int(arg[1])].update({arg[0]: value})

        # Generate chart data
        for sensor in sensors:
            # Add current settings from kwargs
            group_by = "15M"
            group_labels = "%H:%M"
            if settings[sensor.sid]["group"]:
                group_by = settings[sensor.sid]["group"]
                time = (2208989361.0 + datetime.datetime.strptime(group_by[:-1],"%"+group_by[-1]).timestamp())/60.0

                print(time)

                if time >= 525600:
                    group_labels = "%Y"
                elif time >= 1440:
                    group_labels = "%d.%m"
            else:
                settings[sensor.sid]["group"] = "15M"

            range = 60*60*24
            if settings[sensor.sid]["range"]:
                range = 60*60*int(settings[sensor.sid]["range"])
            else:
                settings[sensor.sid]["range"] = "24"

            # Read all values
            labels = []
            values = []
            voltages = []
            average = 0.0
            readings = sensor.get_readings(range,group_by)
            for reading in readings:
                labels.append(datetime.datetime.fromtimestamp(reading.updated).strftime(group_labels))
                values.append(round(reading.value,2))
                voltages.append(round(reading.battery,2))
                average += reading.value

            average /= len(readings) if len(readings) > 0 else 1

            # Create data for chart
            data.append({
                "sid": sensor.sid,
                "average": round(average,2),
                "data": {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Temperature",
                            "data": values,
                            "fill": False,
                            "borderColor": "#FF9000",
                        },
                        {
                            "label": "Battery",
                            "data": voltages,
                            "fill": False,
                            "borderColor": "#0079C4",
                        }
                    ]
                }
            });

        return self.env.get_template('single.html').render(sensors=sensors, data=json.dumps(data), settings=settings)

    @cherrypy.expose
    def sensors(self, *args, **kwargs):
        self.core.accounts.protect()

        if "add" in kwargs:
            try:
                if kwargs["token"] != "":
                    token = kwargs["token"]
                else:
                    token = None

                self.core.sensors.add(int(kwargs["sid"]),kwargs["title"],kwargs["description"],token)
                return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,msg="Sensor added")
            except sqlite3.IntegrityError:
                return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                    msg="Sensor with that ID already exist")
        if "remove" in kwargs:
            if self.core.sensors.remove(int(kwargs["sid"])):
                return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,msg="Sensor removed")
            else:
                return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,msg="Failed to remove sensor")

        return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors)

    @cherrypy.expose
    def api(self, *args, **kwargs):
        sensor = self.core.sensors.get(int(args[0]))
        if sensor:
            if sensor.token == kwargs["token"]:
                sensor.update(float(kwargs["value"]),float(kwargs["battery"]))
                return json.dumps({"success": 1, "message": "Sensor updated"})
            else:
                return json.dumps({"error": 101, "message": "Wrong token"})
        else:
            return json.dumps({"error": 100, "message": "Sensor with that id does not exist"})

if __name__ == "__main__":
    Core()