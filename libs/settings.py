import cherrypy, time

from libs.accounts import Account
from libs.fields import Field

class WebSettings():

    def __init__(self, core, env):
        self.core = core
        self.env = env

    def render(self, template, **kwargs):
        kwargs["config"] = self.core.config
        return self.env.get_template(template).render(**kwargs)

    @cherrypy.expose
    def index(self, **kwargs):
        """Settings page"""
        account = self.core.accounts.protect()

        if "update_account" in kwargs:
            if kwargs["password"] != kwargs["password_repeat"]:
                self.render("/settings/settings.html", account=account, error="Passwords does not match")
            if kwargs["password"] != "": account.password = Account.hash_password(kwargs["password"])
            account.email = kwargs["email"]
            account.commit()
            self.core.accounts.logout_user(account)
            return self.render("/settings/settings.html", account=account, success="Account updated")

        elif "update_config" in kwargs:
            self.core.config.set("colorize_field_tile", kwargs["colorize_field_tile"] == "1", False)
            self.core.config.set("dark_theme", kwargs["dark_theme"] == "1", False)
            self.core.config.set("port", int(kwargs["port"]), False)
            self.core.config.set("host", kwargs["host"], False)
            self.core.config.set("hide_update_time", kwargs["hide_update_time"] == "1", False)
            self.core.config.save()
            return self.render("/settings/settings.html", account=account, success="Settings updated")

        return self.render("/settings/settings.html", account=account)

    @cherrypy.expose
    def sensors(self, **kwargs):
        self.core.accounts.protect()
        sensors = self.core.sensors.sensors

        if "action" in kwargs:
            if kwargs["action"] == "add":
                if self.core.sensors.add(int(kwargs["sid"]), kwargs["token"], kwargs["title"], kwargs["description"]):
                    return self.render("/settings/sensors.html", sensors=sensors , success="Sensor added")
                else:
                    return self.render("/settings/sensors.html", sensors=sensors , error="Failed to add sensor")

        return self.render("/settings/sensors.html", sensors=sensors)

    @cherrypy.expose
    def sensor(self, **kwargs):
        self.core.accounts.protect()
        sensor = self.core.sensors.get(sid=int(kwargs["sid"]))

        if "action" in kwargs:
            if kwargs["action"] == "update_sensor":
                sensor.title = kwargs["title"]
                sensor.description = kwargs["description"]
                sensor.commit()
                return self.render("/settings/sensor.html", sensor=sensor, success="Sensor updated")
            elif kwargs["action"] == "regen":
                sensor.set_token()
                sensor.commit()
                return self.render("/settings/sensor.html", sensor=sensor, success="Sensor token regenerated")
            elif kwargs["action"] == "remove":
                if self.core.sensors.remove(sensor.sid):
                    return self.render("/settings/sensors.html", sensors = self.core.sensors.sensors, success="Sensor removed")
                else:
                    return self.render("/settings/sensors.html", sensors = self.core.sensors.sensors, error="Failed to remove sensor")
            elif kwargs["action"] == "update_field":
                field = Field.get(fid=int(kwargs["fid"]))[0]
                field.display_name = kwargs["display_name"]
                field.unit = kwargs["unit"]
                field.icon = kwargs["icon"]
                field.color = kwargs["color"]
                field.commit()
                return self.render("/settings/sensor.html", sensor=sensor, success="Field updated")
            elif kwargs["action"] == "remove_field":
                if Field.remove(int(kwargs["fid"])):
                    return self.render("/settings/sensor.html", sensor=sensor, success="Field removed")
                else:
                    return self.render("/settings/sensor.html", sensor=sensor, error="Failed to remove field")


        return self.render("/settings/sensor.html", sensor=sensor)