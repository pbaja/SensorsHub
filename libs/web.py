import cherrypy,  json, datetime, time, logging

from libs.sensors import SensorStatus
from libs.graphs import Graph
from libs.fields import Field

class WebRoot(object):

    def __init__(self, core, env):
        self.core = core
        self.env = env

    def bench(self, started):
        """Internal function used to test page generation time"""
        return "<!-- Page generated in {}ms -->".format(round(time.time() - started, 4))

    @cherrypy.expose
    def index(self):
        """Home page"""
        start = time.time()
        return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors, config=self.core.config)+self.bench(start)

    @cherrypy.expose
    def single(self, *args, **kwargs):
        """This page is displaying fields and graphs from all fields for given sensor"""
        start = time.time()
        if len(args) != 1: raise cherrypy.HTTPRedirect("/index")

        # Get settings from kwargs
        now = datetime.datetime.now()
        settings = {"group": "15M", "range": "24", "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M")}
        for arg, value in kwargs.items():
            settings.update({arg: value})

        # Get fields ids from sensor
        fids = []
        sensor = self.core.sensors.get_single(int(args[0]))
        for field in sensor.get_fields():
            fids.append(field.fid)

        # Prepare date
        date_to = time.mktime(datetime.datetime.strptime(settings["date"]+" "+settings["time"],"%Y-%m-%d %H:%M").timetuple())
        date_from = None
        if settings["range"]: date_from = date_to - (60 * 60 * int(settings["range"]))
        else: settings["range"] = "24"

        # Generate data
        fields, data = Graph.generate(fids, settings["group"], date_from=date_from, date_to=date_to, return_fields=True)

        for field in fields:
            field.min = min(field.readings, key=lambda f: f.value).value
            field.max = max(field.readings, key=lambda f: f.value).value

        return self.env.get_template('single.html').render(sensor=sensor, fields=fields, settings=settings, data=json.dumps(data), config=self.core.config)+self.bench(start)

    @cherrypy.expose
    def about(self):
        return self.env.get_template('about.html').render(config=self.core.config)

    @cherrypy.expose
    def api(self, *raw_args, **kwargs):
        """API"""

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
                return json.dumps({"code": 110, "message": "sensorid argument is needed"})

            # Check if there is sensor with that id
            sensor = self.core.sensors.get_single(int(args["sensorid"]))
            if sensor is None:
                return json.dumps({"code": 111, "message": "Sensor with that id does not exist"})

            # Check if token exist and is correct
            if not "token" in args or sensor.token != args["token"]:
                return json.dumps({"code": 112, "message": "Wrong token"})

            # Check if sensor is active
            if sensor.status != SensorStatus.ACTIVE:
                return json.dumps({"code": 114, "message": "Sensor is inactive, data not appended"})

            # Update sensor
            try:
                logging.debug("Appended new data to sensor sid: {} title: {}".format(sensor.sid, sensor.title))
                for field, value in kwargs.items():
                    sensor.add_reading(field,float(value))
            except ValueError:
                return json.dumps({"code": 113, "message": "Parsing url error, make sure that all fields are floats"})
            return json.dumps({"code": 10, "message": "Sensor updated"})

        # Register sensor
        elif args["action"] == "register":
            # Get sensor data
            if not "title" in args:
                return json.dumps({"code": 120, "message": "Sensor title is needed"})
            if not "description" in args:
                return json.dumps({"code": 121, "message": "Sensor description is needed"})

            # Check if sensor with given title exist (To avoid registering one sensor multiple times)
            if self.core.sensors.get_single(title=args["title"]) is not None:
                return json.dumps({"code": 122, "message": "Sensor with that title already exist!"})

            # Get fields data
            fields = {}
            for field, value in kwargs.items():
                name, key = field.split(",")
                if not name in fields:
                    fields[name] = {}
                fields[name][key] = value

            sensor = self.core.sensors.add(title=args["title"],description=args["description"], status=SensorStatus.INACTIVE)
            for name, field in fields.items():
                Field.create(sensor.sid, name, **field)

            return json.dumps({"code": 20, "message": "Sensor registered. Now wait for user to enable it.", "sensorid": sensor.sid, "token": sensor.token})

        # Get chart data for fields
        elif args["action"] == "chart":
            # Get all field ids
            if not "fields" in kwargs:
                return json.dumps({"code": 120, "message": "fields argument is needed"})

            fids = []
            for fid in kwargs["fields"].split(","):
                fids.append(int(fid))

            # Get settings from kwargs
            now = datetime.datetime.now()
            settings = {"group": "15M", "range": "24", "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M")}
            if "group" in kwargs:
                settings["group"] = kwargs["group"]
            if "range" in kwargs:
                settings["range"] = kwargs["range"]

            # Prepare date
            date_to = time.mktime(
                datetime.datetime.strptime(settings["date"] + " " + settings["time"], "%Y-%m-%d %H:%M").timetuple())
            date_from = None
            if settings["range"]:
                date_from = date_to - (60 * 60 * int(settings["range"]))
            else:
                settings["range"] = "24"

            # Generate data
            data = Graph.generate(fids, settings["group"], date_from=date_from, date_to=date_to, sensor_label = True, sensors=self.core.sensors)
            return json.dumps(data)
