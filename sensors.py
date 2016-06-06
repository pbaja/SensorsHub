from datetime import datetime, timedelta
import time
import sqlite3
import random, string

class Reading(object):

    def __init__(self, sid, updated, value, battery):
        self.sid = sid
        self.updated = updated
        self.value = value
        self.battery = battery

class Sensor(object):

    def __init__(self, sid, token, title, description, value=None, battery=None):
        self.sid = sid
        self.updated = datetime.now()
        self.token = token
        self.title = title
        self.description = description
        self.value = value
        self.battery = battery

    def update(self, value, battery):
        # Update values in database
        with sqlite3.connect("db.sqlite") as conn:
            conn.execute("UPDATE sensors SET updated=? WHERE sid=?", [int(time.time()), self.sid])
            conn.execute("INSERT INTO readings (sid, updated, value, battery) VALUES (?,?,?,?);",
                         [self.sid,int(time.time()),value,battery])

        # Update values in object
        self.value = value
        self.battery = battery
        self.updated = datetime.now()

    def get_readings(self, delta=0, group_minutes=0):
        with sqlite3.connect("db.sqlite") as conn:
            if delta != 0: updated = time.time()-delta
            else: updated = 0

            group_add = "%Y"
            if group_minutes[-1] != "m":
                group_add += "%m"
                if group_minutes[-1] != "d":
                    group_add += "%d"
                    if group_minutes[-1] != "H":
                        group_add += "%H0"

            if group_minutes != 0:
                results = conn.execute(
                    "SELECT updated, AVG(value), AVG(battery) FROM readings WHERE sid=? AND updated > ? "
                    "GROUP BY strftime(?,datetime(updated, 'unixepoch'))+strftime(?,datetime(updated, 'unixepoch'))/? "
                    "ORDER BY updated;",
                    [self.sid, updated, group_add,'%'+group_minutes[-1], group_minutes[:-1]])
            else:
                results = conn.execute("SELECT updated, value, battery FROM readings WHERE sid=? AND updated > ?;",[self.sid, updated])

            readings = []
            for result in results.fetchall():
                readings.append(Reading(self.sid, result[0],result[1],result[2]))
            return readings

class Sensors(object):

    def __init__(self):
        self.sensors = []

    def load(self):
        """Load all sensors from database"""
        with sqlite3.connect("db.sqlite") as conn:
            results = conn.execute("SELECT sid, token, title, description FROM sensors GROUP BY sid").fetchall()
            for result in results: self.sensors.append(Sensor(result[0],result[1],result[2],result[3]))

    def add(self, sid, title=None, description=None, token=None):
        """Add sensor to database"""
        if token == None: token = ''.join(random.choice(string.ascii_uppercase+string.digits) for _ in range(16))
        if title == None: description = "Default title"
        if description == None: description = "Default description"

        with sqlite3.connect("db.sqlite") as conn:
            conn.execute("INSERT INTO sensors (sid, token, title, description, updated) VALUES (?,?,?,?,?)",
                                   [sid,token,title, description,int(time.time())]).fetchall()
            self.sensors.append(Sensor(sid,token,title,description))

    def remove(self,sid):
        sensor = self.get(sid)
        if sensor:
            with sqlite3.connect("db.sqlite") as conn:
                conn.execute("DELETE FROM sensors WHERE sid=?",[sid])
                conn.execute("DELETE FROM readings WHERE sid=?", [sid])
                self.sensors.remove(sensor)
                return True
        return False

    def get(self, sid):
        for index, sensor in enumerate(self.sensors):
            if sensor.sid == sid:
                return self.sensors[index]
        return None

    def get_readings(self, delta=None):
        readings = {}
        for sensor in self.sensors:
            readings[sensor.sid] = sensor.get_readings(delta)
        return readings

    def update(self, sid, value, battery):
        sensor = self.get(sid)
        if sensor:
            sensor.update(value,battery)
            return True
        return False