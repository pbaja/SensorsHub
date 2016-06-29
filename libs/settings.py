import cherrypy, os, sqlite3, markdown2

from libs.accounts import Account
from libs.fields import Field
from libs.sensors import SensorStatus

class WebSettings():
    """Class responsible for rendering content for settings web page"""

    def __init__(self, core, env):
        self.core = core
        self.env = env

    def render(self, template, **kwargs):
        """Gets template and kwargs passed as args, and returns rendered template"""
        kwargs["config"] = self.core.config
        kwargs["lang"] = self.core.lang

        if self.core.updater.update_available and template != "/settings/login.html":
            kwargs["info"] = self.core.lang.get("settings_update_available")

        if self.core.config.get("demo_mode"):
            kwargs["warning"] = self.core.lang.get("settings_demo_mode_enabled")

        return self.env.get_template(template).render(**kwargs)

    @cherrypy.expose
    def index(self, **kwargs):
        """Settings web page, available at /settings"""
        account = self.core.accounts.verify_user()

        if self.core.config.get("demo_mode") and not account:
            return self.render("/settings/settings.html")
        elif not account:
            raise cherrypy.HTTPRedirect("/settings/login")

        if "update_account" in kwargs:
            if kwargs["password"] != kwargs["password_repeat"]:
                self.render("/settings/settings.html", account=account, error=self.core.lang.get("error_passwords_not_match"))
            if kwargs["password"] != "": account.password = Account.hash_password(kwargs["password"])
            account.email = kwargs["email"]
            account.commit()
            self.core.accounts.logout_user(account)
            return self.render("/settings/settings.html", account=account, success=self.core.lang.get("success_account_updated"))

        if "reload_lang" in kwargs:
            self.core.lang.load()
            return self.render("/settings/settings.html", account=account, success=self.core.lang.get("success_lang_files_reloaded"))

        elif "update_config" in kwargs:
            self.core.config.set("colorize_field_tile", kwargs["colorize_field_tile"] == "1", False)
            self.core.config.set("dark_theme", kwargs["dark_theme"] == "1", False)
            self.core.config.set("port", int(kwargs["port"]), False)
            self.core.config.set("host", kwargs["host"], False)
            self.core.config.set("page_title", kwargs["page_title"], False)
            self.core.config.set("show_update_time", kwargs["show_update_time"] == "1", True)
            self.core.config.set("about_page", kwargs["about_page"], False)
            self.core.config.set("language", kwargs["language"], False)
            self.core.config.set("chart_point_radius", int(kwargs["chart_point_radius"]), False)
            self.core.config.set("chart_generate_average", kwargs["chart_generate_average"] == "1", False)
            self.core.config.set("chart_fill", kwargs["chart_fill"] == "1", False)
            self.core.config.set("demo_mode", kwargs["demo_mode"] == "1", False)
            self.core.config.save()
            return self.render("/settings/settings.html", account=account, success=self.core.lang.get("success_settings_updated"))

        return self.render("/settings/settings.html", account=account)

    @cherrypy.expose
    def login(self, **kwargs):
        """Login web page, available at /settings/login"""
        if "user" in kwargs and "pass" in kwargs:
            if self.core.accounts.login_user(kwargs["user"], kwargs["pass"]):
                raise cherrypy.HTTPRedirect("/settings")
            else:
                return self.render("/settings/login.html", error=self.core.lang.get("error_wrong_username_or_password"))

        return self.render("/settings/login.html")

    @cherrypy.expose
    def logout(self):
        """Logout web page, available at /settings/logout"""
        if self.core.accounts.logout_user():
            return self.render("home.html", success=self.core.lang.get("success_logged_out"))
        else:
            return self.render("home.html", error=self.core.lang.get("error_logout_failed"))

    @cherrypy.expose
    def tools(self, **kwargs):
        """Tools web page, available at /settings/tools"""
        if not self.core.config.get("demo_mode"):
            self.core.accounts.protect()

        if "action" in kwargs:
            if kwargs["action"] == "autoupdate":
                self.core.updater.update()
                return ""

        with sqlite3.connect("db.sqlite") as conn:
            database = {
                "filesize": round(os.path.getsize("db.sqlite")/1024/1024,2),
                "readings":  conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
            }

            autoupdate = {
                "version": self.core.VERSION,
                "latest": self.core.updater.version["latest"],
            }

            statistics = {
                "online": self.core.statistics.currently_online()
            }

            return self.render("/settings/tools.html", database=database, autoupdate=autoupdate, statistics=statistics)

    @cherrypy.expose
    def log(self, **kwargs):
        """Log web page, available at /settings/log"""
        self.core.accounts.protect()

        # Load all files from dir and sort them by modification date
        all_files = os.listdir("logs")
        all_files.sort(key=lambda k: -os.path.getmtime("logs/"+k))

        # Get basename of files
        files = []
        for file in all_files:
            if file.endswith(".log"):
                files.append(os.path.basename(file).split(".")[-2])

        log_file = files[0]
        if "file" in kwargs:
            log_file = kwargs["file"]

        with open("logs/{}.log".format(log_file),"r") as file:
            log = file.read()
            formatted_log = ""
            for line in log.split("\n"):
                formatted_log += "<div class='"
                if "[INFO]" in line: formatted_log += "info"
                if "[DEBUG]" in line: formatted_log += "debug"
                if "[WARNING]" in line: formatted_log += "warn"
                if "[ERROR]" in line: formatted_log += "error"
                formatted_log += "'>"
                formatted_log += line
                formatted_log += "</div>"

        return self.render('/settings/log.html', files=files, log_file=log_file, log=formatted_log)

    @cherrypy.expose
    def sensors(self, **kwargs):
        """Sensors web page, available at /settings/sensors"""
        active_sensors = self.core.sensors.get_all(status=SensorStatus.ACTIVE)
        inactive_sensors = self.core.sensors.get_all(status=SensorStatus.INACTIVE)

        account = self.core.accounts.verify_user()
        if self.core.config.get("demo_mode") and not account:
            return self.render("/settings/sensors.html", active_sensors=active_sensors,inactive_sensors=inactive_sensors)
        elif not account:
            raise cherrypy.HTTPRedirect("/settings/login")

        if "action" in kwargs:
            if kwargs["action"] == "add":
                if self.core.sensors.add(title=kwargs["title"], description=kwargs["description"]):
                    active_sensors = self.core.sensors.get_all(SensorStatus.ACTIVE)
                    return self.render("/settings/sensors.html",
                                       active_sensors=active_sensors,
                                       inactive_sensors=inactive_sensors ,
                                       success=self.core.lang.get("success_sensor_added"))
                else:
                    return self.render("/settings/sensors.html",
                                       active_sensors=active_sensors,
                                       inactive_sensors=inactive_sensors ,
                                       error=self.core.lang.get("error_sensor_add_failed"))

        return self.render("/settings/sensors.html", active_sensors=active_sensors,inactive_sensors=inactive_sensors)

    @cherrypy.expose
    def sensor(self, **kwargs):
        """Single sensor web page, available at /settings/sensor/SENSORID"""
        sensor = self.core.sensors.get_single(sid=int(kwargs["sid"]))

        account = self.core.accounts.verify_user()
        if self.core.config.get("demo_mode") and not account:
            return self.render("/settings/sensor.html", sensor=sensor, account=account)
        elif not account:
            raise cherrypy.HTTPRedirect("/settings/login")

        if "action" in kwargs:
            if kwargs["action"] == "update_sensor":
                sensor.title = kwargs["title"]
                sensor.description = kwargs["description"]
                sensor.commit()
                return self.render("/settings/sensor.html", sensor=sensor, account=account, success=self.core.lang.get("success_sensor_updated"))
            elif kwargs["action"] == "regen":
                sensor.set_token()
                sensor.commit()
                return self.render("/settings/sensor.html", sensor=sensor, account=account, success=self.core.lang.get("success_sensor_token_regenerated"))
            elif kwargs["action"] == "remove":
                if self.core.sensors.remove(sensor.sid):
                    return self.render("/settings/sensors.html", sensors = self.core.sensors.sensors, account=account, success=self.core.lang.get("success_sensor_removed"))
                else:
                    return self.render("/settings/sensors.html", sensors = self.core.sensors.sensors, account=account, error=self.core.lang.get("error_sensor_remove_failed"))
            elif kwargs["action"] == "enable":
                sensor.status = SensorStatus.ACTIVE
                sensor.commit()
                return self.render("/settings/sensor.html", sensor=sensor, account=account, success=self.core.lang.get("success_sensor_enabled"))
            elif kwargs["action"] == "disable":
                sensor.status = SensorStatus.INACTIVE
                sensor.commit()
                return self.render("/settings/sensor.html", sensor=sensor, account=account, success=self.core.lang.get("success_sensor_disabled"))
            elif kwargs["action"] == "update_field":
                field = Field.get(fid=int(kwargs["fid"]))[0]
                field.display_name = kwargs["display_name"]
                field.unit = kwargs["unit"]
                field.icon = kwargs["icon"]
                field.color = kwargs["color"]
                field.commit()
                return self.render("/settings/sensor.html", sensor=sensor, account=account, success=self.core.lang.get("success_field_updated"))
            elif kwargs["action"] == "remove_field":
                if Field.remove(int(kwargs["fid"])):
                    return self.render("/settings/sensor.html", sensor=sensor, account=account, success=self.core.lang.get("success_field_removed"))
                else:
                    return self.render("/settings/sensor.html", sensor=sensor, account=account, error=self.core.lang.get("error_field_remove_failed"))


        return self.render("/settings/sensor.html", sensor=sensor, account=account)