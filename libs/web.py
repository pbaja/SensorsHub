import cherrypy,  json, datetime, sqlite3, time
from jinja2 import Environment, FileSystemLoader

from libs.fields import Field
from libs.graphs import Graph

class WebRoot(object):

    def __init__(self, core):
        # Load templates
        self.env = Environment(loader=FileSystemLoader('templates'))

        def to_json(value): return json.dumps(value)
        self.env.filters["to_json"] = to_json

        def format_datetime(value, format="%d.%m.%Y %H:%M"):
            if value == None:
                return "Never"
            else:
                try:
                    return datetime.datetime.fromtimestamp(value).strftime(format)
                except TypeError:
                    return value.strftime(format)
        self.env.filters["strftime"] = format_datetime

        # Save core object
        self.core = core

    def bench(self, started):
        """Internal function used to test page generation time"""
        return "<!-- Page generated in {}ms -->".format(round(time.time() - started, 4))

    @cherrypy.expose
    def index(self):
        start = time.time()
        return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors)+self.bench(start)

    @cherrypy.expose
    def logout(self):
        start = time.time()
        if self.core.accounts.logout_user():
            return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors,msg="Logged out")+self.bench(start)
        else:
            return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors, msg="Failed to logout")+self.bench(start)

    @cherrypy.expose
    def single(self, *args, **kwargs):
        start = time.time()
        if len(args) != 1: raise cherrypy.HTTPRedirect("/index")

        # Get settings from kwargs
        settings = {"group": "15M", "range": "24"}
        for arg, value in kwargs.items():
            arg = arg.split("_")
            settings.update({arg[0]: value})

        range = 60 * 60 * 24
        if settings["range"]:
            range = 60 * 60 * int(settings["range"])
        else:
            settings["range"] = "24"

        # Get fields ids from sensor
        fids = []
        sensor = self.core.sensors.get(int(args[0]))
        for field in sensor.get_fields():
            fids.append(field.fid)

        # Generate data
        data = Graph.generate(fids,settings["group"],range)

        return self.env.get_template('single.html').render(sensor=sensor, settings=settings, data=json.dumps(data))+self.bench(start)

    @cherrypy.expose
    def sensors(self, *args, **kwargs):
        start = time.time()
        self.core.accounts.protect()

        if "action" in kwargs:
            if kwargs["action"] == "remove":
                if self.core.sensors.remove(int(kwargs["sid"])):
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Sensor removed")+self.bench(start)
                else:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                    msg="Failed to remove sensor")+self.bench(start)

            elif kwargs["action"] == "update_field":
                field = Field.get(fid=int(kwargs["fid"]))[0]
                field.display_name = kwargs["display_name"]
                field.unit = kwargs["unit"]
                field.icon = kwargs["icon"]
                field.color = kwargs["color"]
                field.commit()
                return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Field updated")+self.bench(start)

            elif kwargs["action"] == "remove_field":
                if Field.remove(int(kwargs["fid"])):
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Field removed")+self.bench(start)
                else:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Failed to remove field")+self.bench(start)

            elif kwargs["action"] == "regen":
                sensor = self.core.sensors.get(int(kwargs["sid"]))
                if sensor and sensor.set_token():
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Token regenerated")+self.bench(start)
                else:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Failed to regenerate token")+self.bench(start)

            elif kwargs["action"].lower() == "add":
                try:
                    if self.core.sensors.add(int(kwargs["sid"]),None, kwargs["title"], kwargs["description"]):
                        return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                            msg="Sensor added")+self.bench(start)
                    else:
                        return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                            msg="Failed to add sensor")+self.bench(start)
                except sqlite3.IntegrityError:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Sensor with that ID already exist")+self.bench(start)

        return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors)+self.bench(start)

    @cherrypy.expose
    def graph(self, *args):
        # Check if user supplied correct amount of arguments
        if len(args) >= 1:
            return json.dumps({"error": 100, "message": "Not enough arguments, i need at least one field id"})

        fields = []
        for fid in args:
            fields.append(Field.get(fid=int(fid)))


    @cherrypy.expose
    def api(self, *raw_args, **kwargs):

        # Get arguments
        args = {}
        for arg in raw_args:
            arg = arg.split(",")
            args[arg[0]] = arg[1]

        if not "action" in args:
            return json.dumps({"code": 100, "message": "action argument is needed"})

        # Add new readings
        if args["action"] == "append":
            # Check if there are needed values
            if not "sensorid" in args:
                return json.dumps({"code": 100, "message": "sensorid argument is needed"})

            # Check if there is sensor with that id
            sensor = self.core.sensors.get(int(args["sensorid"]))
            if sensor is None:
                return json.dumps({"code": 101, "message": "Sensor with that id does not exist"})

            # Check if token exist and is correct
            if not "token" in args or sensor.token != args["token"]:
                return json.dumps({"code": 102, "message": "Wrong token"})

            # Update sensor
            try:
                for field, value in kwargs.items():
                    sensor.add_reading(field,float(value))
            except ValueError:
                return json.dumps({"code": 103, "message": "Parsing url error, make sure that all fields are floats"})
            return json.dumps({"code": 1, "message": "Sensor updated"})

        # Get chart data for fields
        elif args["action"] == "chart":
            # Get all field ids
            if not "fields" in kwargs:
                return json.dumps({"code": 100, "message": "fields argument is needed"})

            fids = []
            for fid in kwargs["fields"].split(","):
                fids.append(int(fid))

            # Get settings from kwargs
            settings = {"group": "15M", "range": "24"}
            if "group" in kwargs:
                settings["group"] = kwargs["group"]
            if "range" in kwargs:
                settings["range"] = kwargs["range"]

            range = 60 * 60 * 24
            if settings["range"]:
                range = 60 * 60 * int(settings["range"])
            else:
                settings["range"] = "24"

            # Generate data
            data = Graph.generate(fids, settings["group"], range, sensor_label = True, sensors=self.core.sensors)
            return json.dumps(data)
