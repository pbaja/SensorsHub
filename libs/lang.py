import os, json

class Lang(object):

    def __init__(self, core):
        self.core = core
        self.langs = {}

    def load(self):
        # Search for all languages in lang folder
        self.langs = {}
        for lang in os.listdir("lang"):
            if lang.endswith(".json"):
                with open("lang/"+lang, "r") as file:
                    basename = os.path.basename(lang).split(".")[-2]
                    self.langs[basename] = json.load(file)

    def get(self, key):
        lang = self.langs[self.core.config.get("language")]
        while True:
            if key in lang["strings"]:
                print("Got key: {} value: {}".format(key, lang["strings"][key]))
                return lang["strings"][key]
            if lang["fallback"] in self.langs.keys():
                lang = self.langs[lang["fallback"]]
            else:
                break
        return None