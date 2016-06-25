import json, os, getopt, sys, logging, shutil

class Config(object):

    def __init__(self):
        self.config = {}
        self.config_default = {}
        self.args = {}

        # Load config from command line
        opts, args = getopt.getopt(sys.argv[1:], '', ["port=", "host=", "dark_theme"])
        for arg, value in opts:
            logging.info("Config key {} changed to {} by commandline, ignoring config file value".format(arg, value))
            if arg == "--port":
                self.args[arg[2:]] = int(value)
            elif arg in ("--dark_theme", "--colorize_field_tile"):
                self.args[arg[2:]] = True
            else:
                self.args[arg] = value

    def load(self):
        """Loads data from config file, or creates it if it does not exist."""
        # Read default config file
        with open("config_default.json","r") as file:
            self.config_default = json.load(file)

        # If config file does not exist, copy default values
        if not os.path.isfile("config.json"):
            shutil.copy("config_default.json","config.json")
            logging.info("Created new config file config.json")

        # Otherwise, read config from file
        else:
            with open("config.json", "r") as file:
                self.config = json.load(file)
                logging.info("Loaded config from config.json")

    def save(self):
        """Saves data back to file"""
        with open("config.json", "w") as file:
            json.dump(self.config, file)
            logging.info("Saved config to config.json")
            return True

    def get(self, key):
        if key in self.args:
            return self.args[key]
        if key in self.config:
            return self.config[key]
        if key in self.config_default:
            self.config[key] = self.config_default[key]
            self.save()
            return self.config[key]
        return None

    def set(self, key, value, save=True):
        self.config[key] = value
        if save: self.save()