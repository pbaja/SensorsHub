import cherrypy,  json, datetime, sqlite3, random, string
from jinja2 import Environment, FileSystemLoader

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

    @cherrypy.expose
    def index(self):
        return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors)

    @cherrypy.expose
    def logout(self):
        if self.core.accounts.logout_user():
            return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors,msg="Logged out")
        else:
            return self.env.get_template('home.html').render(sensors=self.core.sensors.sensors, msg="Failed to logout")

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
            datasets = []
            fields = sensor.get_readings(range, group_by)
            for reading in fields[0].readings:
                labels.append(datetime.datetime.fromtimestamp(reading.updated).strftime(group_labels))
            for field in fields:
                dataset = {"label": field.display_name, "data": [], "fill": False, "borderColor": "#FF9000"}
                for reading in field.readings:
                    dataset["data"].append(reading.value)
                datasets.append(dataset)

            # Create data for chart
            data = {
                "sid": sensor.sid,
                "data": {
                    "labels": labels,
                    "datasets": datasets
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

        if "action" in kwargs:
            if kwargs["action"] == "remove":
                if self.core.sensors.remove(int(kwargs["sid"])):
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Sensor removed")
                else:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                    msg="Failed to remove sensor")

            elif kwargs["action"] == "update_field":
                field = self.core.sensors.get_field(int(kwargs["fid"]))
                if field.update(kwargs["display_name"],kwargs["unit"]):
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Field updated")
                else:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Failed to update field")

            elif kwargs["action"] == "remove_field":
                if self.core.sensors.remove_field(int(kwargs["fid"])):
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Field removed")
                else:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Failed to remove field")

            elif kwargs["action"] == "regen":
                sensor = self.core.sensors.get(int(kwargs["sid"]))
                if sensor and sensor.set_token():
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Token regenerated")
                else:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Failed to regenerate token")

            elif kwargs["action"].lower() == "add":
                try:
                    if self.core.sensors.add(int(kwargs["sid"]),None, kwargs["title"], kwargs["description"]):
                        return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                            msg="Sensor added")
                    else:
                        return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                            msg="Failed to add sensor")
                except sqlite3.IntegrityError:
                    return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors,
                                                                        msg="Sensor with that ID already exist")

        return self.env.get_template('sensors.html').render(sensors=self.core.sensors.sensors)

    @cherrypy.expose
    def api(self, *args, **kwargs):
        # Check if user supplied correct amount of arguments
        if len(args) != 2:
            return json.dumps({"error": 100, "message": "Not enough arguments, i need token and sensorid"})

        # Check if sensor with that id exist
        sensor = self.core.sensors.get(int(args[1]))
        if not sensor:
            return json.dumps({"error": 101, "message": "Sensor with that id does not exist"})

        # Check if token is correct
        if sensor.token != args[0]:
            return json.dumps({"error": 102, "message": "Wrong token"})

        # Update sensor
        for field, value in kwargs.items():
            sensor.update(int(args[1]), field, float(value))
        return json.dumps({"success": 1, "message": "Sensor updated"})