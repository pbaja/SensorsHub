#!/usr/bin/python3.4
import cherrypy, os, json
from jinja2 import Environment, FileSystemLoader

class WebRoot(object):

    def __init__(self):
        # Load templates
        self.env = Environment(loader=FileSystemLoader('templates'))

        self.value = 0.0

    @cherrypy.expose
    def index(self):
        return self.env.get_template('home.html').render(value=self.value)

    @cherrypy.expose
    def api(self, *args, **kwargs):
        print(args)
        print(kwargs)

        if args[0] == "0" and kwargs["token"] == "123":
            # All okay, get data
            self.value = float(kwargs["value"])
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