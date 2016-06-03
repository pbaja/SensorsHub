#!/usr/bin/python3.4
import cherrypy, os, json, sqlite3, time, datetime
from jinja2 import Environment, FileSystemLoader


class WebRoot(object):

    def __init__(self):
        # Load templates
        self.env = Environment(loader=FileSystemLoader('templates'))
        def to_json(value): return json.dumps(value)
        self.env.filters["to_json"] = to_json

        # Create place for current values
        self.sensors = {}

        # Create databse
        with sqlite3.connect("db.sqlite") as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS sensors(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date INTEGER,
                sensorid INTEGER,
                value FLOAT
            )""")

    @cherrypy.expose
    def index(self):
        with sqlite3.connect("db.sqlite") as conn:
            result = conn.execute("SELECT * FROM sensors WHERE date > ?",[time.time()-86400]).fetchall()
            values = {}

            # Create all sensors
            for sensor in result:
                if not sensor[2] in values:
                    current = 0.0
                    lastupd = "Never"
                    if sensor[2] in self.sensors:
                        current = self.sensors[sensor[2]]["current"]
                        lastupd = self.sensors[sensor[2]]["lastupd"]
                    values[sensor[2]] = {"id": sensor[2],"labels": [], "values": [], "current": current, "lastupd": lastupd}

            # Add all values to sensors
            for sensor in result:
                date = datetime.datetime.fromtimestamp(sensor[1])
                print(date)
                values[sensor[2]]["labels"].append("{}:{}".format(date.hour,date.minute))
                values[sensor[2]]["values"].append(sensor[3])

            return self.env.get_template('home.html').render(sensors=list(values.values()))

    @cherrypy.expose
    def api(self, *args, **kwargs):
        if args[0] == "0" and kwargs["token"] == "123":
            # All okay, get data
            self.sensors[0] = {"current": float(kwargs["value"]), "lastupd": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}
            with sqlite3.connect("db.sqlite") as conn:
                conn.execute("INSERT INTO sensors (date, sensorid, value) VALUES (?,?,?)",[time.time(),0,kwargs["value"]])
                return json.dumps({"success": "Value saved"})
        else:
            return json.dumps({"error": "Wrong token"})

if __name__ == "__main__":
    cherrypy.config.update({
        "server.socket_port": 5000,
        "server.socket_host": "0.0.0.0"
    })
    cherrypy.tree.mount(WebRoot(), "/", {
        "/static": {
            "tools.staticdir.root": os.getcwd(),
            "tools.staticdir.on": True,
            "tools.staticdir.dir": "static"
        }
    })
    cherrypy.engine.signals.subscribe()
    cherrypy.engine.start()

    try:
        while True: pass
    except:
        cherrypy.engine.exit()