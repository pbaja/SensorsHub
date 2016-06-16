import cherrypy,  json, datetime, sqlite3, time
from jinja2 import Environment, FileSystemLoader

from libs.fields import Field
from libs.graphs import Graph
from libs.accounts import Account

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
        """Home page"""
        start = time.time()
        return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors, config=self.core.config)+self.bench(start)

    @cherrypy.expose
    def logout(self):
        """Loggnig out, unfortunately browser will immidiately log in you back automatically."""
        start = time.time()
        if self.core.accounts.logout_user():
            return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors,msg="Logged out", config=self.core.config)+self.bench(start)
        else:
            return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors, msg="Failed to logout", config=self.core.config)+self.bench(start)

    @cherrypy.expose
    def single(self, *args, **kwargs):
        """This page is displaying fields and graphs from all fields for given sensor"""
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

        return self.env.get_template('single.html').render(sensor=sensor, settings=settings, data=json.dumps(data), config=self.core.config)+self.bench(start)

    @cherrypy.expose
    def sensors(self, *args, **kwargs):
        """This page allows you to configure and create sensors"""
        start = time.time()
        self.core.accounts.protect()

        if "action" in kwargs:
            if kwargs["action"] == "remove":
                if self.core.sensors.remove(int(kwargs["sid"])):
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        success="Sensor removed", config=self.core.config)+self.bench(start)
                else:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                    error="Failed to remove sensor", config=self.core.config)+self.bench(start)

            elif kwargs["action"] == "update_field":
                field = Field.get(fid=int(kwargs["fid"]))[0]
                field.display_name = kwargs["display_name"]
                field.unit = kwargs["unit"]
                field.icon = kwargs["icon"]
                field.color = kwargs["color"]
                field.commit()
                return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        success="Field updated", config=self.core.config)+self.bench(start)

            elif kwargs["action"] == "remove_field":
                if Field.remove(int(kwargs["fid"])):
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        success="Field removed", config=self.core.config)+self.bench(start)
                else:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        error="Failed to remove field", config=self.core.config)+self.bench(start)

            elif kwargs["action"] == "regen":
                sensor = self.core.sensors.get(int(kwargs["sid"]))
                if sensor and sensor.set_token():
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        success="Token regenerated", config=self.core.config)+self.bench(start)
                else:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        error="Failed to regenerate token", config=self.core.config)+self.bench(start)

            elif kwargs["action"] == "add":
                try:
                    if self.core.sensors.add(int(kwargs["sid"]),kwargs["token"], kwargs["title"], kwargs["description"]):
                        return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                            success="Sensor added", config=self.core.config)+self.bench(start)
                    else:
                        return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                            error="Failed to add sensor", config=self.core.config)+self.bench(start)
                except sqlite3.IntegrityError:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        error="Sensor with that ID already exist", config=self.core.config)+self.bench(start)

        return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors, config=self.core.config)+self.bench(start)

    @cherrypy.expose
    def settings(self, *args, **kwargs):
        """Settings page"""
        start = time.time()
        account = self.core.accounts.protect()

        if "update_account" in kwargs:
            if kwargs["password"] != kwargs["password_repeat"]:
                return self.env.get_template('settings.html').render(error="Passwords does not match",
                                                                     account=account, config=self.core.config) + self.bench(start)
            if kwargs["password"] != "": account.password = Account.hash_password(kwargs["password"])
            account.email = kwargs["email"]
            account.commit()
            self.core.accounts.logout_user(account)
            return self.env.get_template('settings.html').render(success="Account updated",account=account) + self.bench(start)

        elif "update_config" in kwargs:
            self.core.config.set("colorize_field_tile", kwargs["colorize_field_tile"] == "1",False)
            self.core.config.set("dark_theme", kwargs["dark_theme"] == "1",False)
            self.core.config.set("port", int(kwargs["port"]),False)
            self.core.config.set("host", kwargs["host"],False)
            self.core.config.save()
            return self.env.get_template('settings.html').render(success="Settings updated", account=account,
                                                                 config=self.core.config) + self.bench(start)

        return self.env.get_template('settings.html').render(account=account, config=self.core.config)+self.bench(start)

    @cherrypy.expose
    def log(self):
        return self.env.get_template('log.html').render(config=self.core.config)

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
            sensor = self.core.sensors.get(int(args["sensorid"]))
            if sensor is None:
                return json.dumps({"code": 111, "message": "Sensor with that id does not exist"})

            # Check if token exist and is correct
            if not "token" in args or sensor.token != args["token"]:
                return json.dumps({"code": 112, "message": "Wrong token"})

            # Update sensor
            try:
                for field, value in kwargs.items():
                    sensor.add_reading(field,float(value))
            except ValueError:
                return json.dumps({"code": 113, "message": "Parsing url error, make sure that all fields are floats"})
            return json.dumps({"code": 10, "message": "Sensor updated"})

        # Get chart data for fields
        elif args["action"] == "chart":
            # Get all field ids
            if not "fields" in kwargs:
                return json.dumps({"code": 120, "message": "fields argument is needed"})

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
