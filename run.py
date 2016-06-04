#!/usr/bin/python3.4
import cherrypy, os, json, sqlite3, time, datetime
from jinja2 import Environment, FileSystemLoader

from sensors import Sensor, Sensors

class Core(object):
    def __init__(self):
        # Create databse
        with sqlite3.connect("db.sqlite") as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS sensors(sid INTEGER PRIMARY KEY, token TEXT, title TEXT, description TEXT, updated INTEGER)""")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS readings(sid, updated INT, value FLOAT, battery FLOAT)""")

        # Create and read sensors from database
        self.sensors = Sensors()
        self.sensors.load()

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
        sensors = self.core.sensors.sensors
        data = []

        # Generate chart data
        for sensor in sensors:
            # Read all values
            labels = []
            values = []
            voltages = []
            readings = sensor.get_readings(60*60*24)
            for reading in readings:
                labels.append(datetime.datetime.fromtimestamp(reading.updated).strftime("%H:%M"))
                values.append(reading.value)
                voltages.append(reading.battery)

            # Create data for chart
            data.append({
                "sid": sensor.sid,
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

        return self.env.get_template('home.html').render(sensors=sensors, data=json.dumps(data))

    @cherrypy.expose
    def sensors(self, *args, **kwargs):
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
        print(args)

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