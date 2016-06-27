import random
import sqlite3
import string
import time
import logging

from enum import IntEnum
from libs.fields import Field
from libs.readings import Reading

class SensorStatus(IntEnum):
    ACTIVE = 0
    INACTIVE = 1

class Sensor(object):
    """Class containing one sensor"""

    def __init__(self, sid, token, title, description, updated, status):
        self.sid = sid
        self.updated = updated
        self.token = token
        self.title = title
        self.description = description
        self.status = status

    def set_token(self, token=None):
        """Set token of sensor, or generate if new token is Null"""
        with sqlite3.connect("db.sqlite") as conn:
            if token is None:
                token = ''.join(random.choice(string.ascii_uppercase+string.digits) for _ in range(16))

            conn.execute("UPDATE sensors SET token=? WHERE sid=?",[token, self.sid])
            self.token = token
            return True

    def add_reading(self, name, value):
        """Add new reading into database"""
        # Update values in database
        with sqlite3.connect("db.sqlite") as conn:
            # Get field
            field = Field.get(sid=self.sid,name=name)
            # If field does not exist, create it
            if field is None:
                field = Field.create(sid=self.sid, name=name)
            else:
                field = field[0]

            # Refresh sensor updated timestamp
            conn.execute("UPDATE sensors SET updated=? WHERE sid=?", [int(time.time()), self.sid])

            # Refresh field updated timestamp
            conn.execute("UPDATE fields SET updated=? WHERE fid=?", [int(time.time()), field.fid])

            # Add reading to database
            conn.execute("INSERT INTO readings (sid, fid, updated, value) VALUES (?,?,?,?);",
                         [self.sid,field.fid,int(time.time()),value])

            # Update values in object
            self.value = value
            self.updated = int(time.time())
            return True

    def get_latest(self):
        """Get latest values from all fields"""
        fields = self.get_fields()
        for field in fields:
            field.readings.append(field.last_reading())
        return fields

    def get_fields(self):
        """Returns list of fields without readings"""
        with sqlite3.connect("db.sqlite") as conn:
            results = conn.execute("SELECT sid, fid, name, unit, display_name, style, updated FROM fields WHERE sid=?",[self.sid]).fetchall()
            fields = []
            for result in results:
                fields.append(Field(result[0],result[1],result[2],result[3],result[4], result[5], result[6]))
            return fields

    def get_readings(self, delta=0, group_minutes="1S"):
        """Returns list of fields with readings"""
        fields = self.get_fields()
        for field in fields:
            field.get_readings(delta, group_minutes)
        return fields

    def commit(self):
        """Send changes to database"""
        with sqlite3.connect("db.sqlite") as conn:
            conn.execute("UPDATE sensors SET updated=?, token=?, title=?, description=? WHERE sid=?",
                         [self.updated, self.token, self.title, self.description, self.sid])
            return True

    def last_update(self):
        """Returns seconds from last update"""
        return time.time()-self.updated

class Sensors(object):
    """Class containing all sensors"""

    def __init__(self):
        self.sensors = []

    def load(self):
        """Loads all sensors from database"""
        with sqlite3.connect("db.sqlite") as conn:
            results = conn.execute("SELECT sid, token, title, description, updated, status FROM sensors GROUP BY sid").fetchall()
            # Add all results to list
            for result in results:
                self.sensors.append(Sensor(result[0],result[1],result[2],result[3],result[4],result[5]))
            logging.info("Loaded {} sensors from database".format(len(results)))

    def add(self, sid=None, token="", title=None, description=None, status=None):
        """Adds new sensor to database"""
        into = []
        values = []

        logging.debug("Trying to create new sensor, title: {}".format(title))

        if sid != None and sid != "":
            into.append('sid')
            values.append(int(sid))
        if title != None:
            into.append('title')
            values.append(title)
        if description != None:
            into.append('description')
            values.append(description)
        if status != None and status != "":
            into.append('status')
            values.append(int(status))
        else:
            status = 0
        if token == "":
            token = ''.join(random.choice(string.ascii_uppercase+string.digits) for _ in range(16))
            into.append('token')
            values.append(token)
        else:
            into.append('token')
            values.append(token)

        with sqlite3.connect("db.sqlite") as conn:
            query = "INSERT INTO sensors ("+",".join(into)+") VALUES ("+",".join(["?"] * len(into))+")"
            result = conn.execute(query,values)
            sensor = Sensor(result.lastrowid,token,title,description, None, int(status))
            self.sensors.append(sensor)
            logging.info("Created new sensor, name: {} sid: {} ".format(title, result.lastrowid))
            return sensor

    def remove(self,sid):
        """Removes sensor from database and all of its fields and readings ! BE CAREFUL"""
        logging.debug("Trying to remove sensor sid: {}".format(sid))
        sensor = self.get_single(sid)
        if sensor:
            with sqlite3.connect("db.sqlite") as conn:
                conn.execute("DELETE FROM sensors WHERE sid=?",[sid])
                conn.execute("DELETE FROM fields WHERE sid=?", [sid])
                conn.execute("DELETE FROM readings WHERE sid=?", [sid])
                self.sensors.remove(sensor)
                logging.info("Removed sensor name: {} sid: ".format(sensor.title, sid))
                return True
        logging.debug("Failed to remove, sensor {} does not exist".format(sid))
        return False

    def get_single(self, sid=None, title=None):
        """Returns sensor from list by sid"""
        for index, sensor in enumerate(self.sensors):
            if sid is not None and sensor.sid == sid:
                return self.sensors[index]
            if title is not None and sensor.title == title:
                return self.sensors[index]
        return None

    def get_all(self, status=None):
        "Gets all sensors by its status"
        if status is None:
            return self.sensors
        else:
            result = []
            for sensor in self.sensors:
                if sensor.status == status:
                    result.append(sensor)
            return result

    def get_readings(self, delta=None, group_minutes=None):
        """Returns fields with readings from all sensors"""
        readings = {}
        for sensor in self.sensors:
            readings[sensor.sid] = sensor.get_readings(delta, group_minutes)
        return readings
