from datetime import datetime, timedelta
import time
import sqlite3
import random, string

class Reading(object):

    def __init__(self, sid, fid, updated, value):
        self.sid = sid
        self.fid = fid
        self.updated = updated
        self.value = value

class Field(object):

    def __init__(self, fid, sid, name, unit, display_name=None):
        self.fid = fid
        self.sid = sid
        self.name = name
        self.unit = unit
        self.updated = None

        if display_name:
            self.display_name = display_name
        else:
            self.display_name = name

        self.readings = []

    def update(self, display_name, unit):
        with sqlite3.connect("db.sqlite") as conn:
            conn.execute("UPDATE fields SET display_name=?, unit=? WHERE fid=?",[display_name, unit, self.fid])
            self.display_name = display_name
            self.unit = unit
            return True
        return False

class Sensor(object):

    def __init__(self, sid, token, title, description, updated):
        self.sid = sid
        self.updated = updated
        self.token = token
        self.title = title
        self.description = description

    def set_token(self, token=None):
        with sqlite3.connect("db.sqlite") as conn:
            if token==None:
                token = ''.join(random.choice(string.ascii_uppercase+string.digits) for _ in range(16))

            conn.execute("UPDATE sensors SET token=? WHERE sid=?",[token, self.sid])
            self.token = token
            return True
        return False

    def update(self, sid, field_name, value):
        """Adds reading into database"""
        # Update values in database
        with sqlite3.connect("db.sqlite") as conn:
            # Get field
            field = self.get_field_by_name(field_name)
            # If field not exist, create it
            if not field:
                print("Inserting new field")
                conn.execute("INSERT INTO fields (sid, name) VALUES (?,?);", [self.sid, field_name])
                conn.commit()
                # And try again
                print("Getting field")
                field = self.get_field_by_name(field_name)

            # Refresh sensor update timestamp
            conn.execute("UPDATE sensors SET updated=? WHERE sid=?", [int(time.time()), self.sid])

            # Add reading to database
            conn.execute("INSERT INTO readings (sid, fid, updated, value) VALUES (?,?,?,?);",
                         [self.sid,field.fid,int(time.time()),value])

            # Update values in object
            self.value = value
            self.updated = int(time.time())
            field.updated = int(time.time())
            return True
        return False

    def get_latest(self):
        """Get latest values from all fields"""
        with sqlite3.connect("db.sqlite") as conn:
            results = conn.execute("SELECT m1.* FROM readings m1 "
                                   "LEFT JOIN readings m2 "
                                   "ON (m1.fid=m2.fid AND m1.updated<m2.updated) "
                                   "WHERE m2.fid IS NULL AND m1.sid=?",[self.sid]).fetchall()

            fields = []
            for result in results:
                # Get field
                field = self.get_field_by_fid(result[1])
                field.readings.append(Reading(self.sid,result[1],result[2],result[3]))
                fields.append(field)
            return fields

    def get_field_by_name(self, name):
        """Returns field by name if found in database"""
        with sqlite3.connect("db.sqlite") as conn:
            results = conn.execute("SELECT fid, sid, name, unit, display_name FROM fields WHERE sid=? AND name=?", [self.sid, name]).fetchall()
            if len(results):
                result = results[0]
                return Field(result[0],result[1],result[2],result[3],result[4])
        return None

    def get_field_by_fid(self, fid):
        """Returns field by fid if found in database"""
        with sqlite3.connect("db.sqlite") as conn:
            results = conn.execute("SELECT fid, sid, name, unit, display_name FROM fields WHERE sid=? AND fid=?",
                                   [self.sid, fid]).fetchall()
            if len(results):
                result = results[0]
                return Field(result[0], result[1], result[2], result[3],result[4])
        return None

    def get_fields(self):
        """Returns list of fields without readings"""
        with sqlite3.connect("db.sqlite") as conn:
            results = conn.execute("SELECT fid, sid, name, unit, display_name FROM fields WHERE sid=?",[self.sid]).fetchall()
            fields = []
            for result in results:
                fields.append(Field(result[0],result[1],result[2],result[3],result[4]))
            return fields

    def get_readings(self, delta=0, group_minutes=0):
        """Returns list of fields with readings"""
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

            fields = self.get_fields()

            if group_minutes != "1S":
                for field in fields:
                    results = conn.execute(
                        "SELECT updated, fid, AVG(value) FROM readings WHERE sid=? AND fid=? AND updated > ? "
                        "GROUP BY strftime(?,datetime(updated, 'unixepoch'))+strftime(?,datetime(updated, 'unixepoch'))/? "
                        "ORDER BY updated",
                        [self.sid, field.fid, updated, group_add,'%'+group_minutes[-1], group_minutes[:-1]])
                    field.readings = []
                    for result in results:
                        field.readings.append(Reading(self.sid, result[0], result[1], result[2]))
            else:
                for field in fields:
                    results = conn.execute(
                        "SELECT updated, fid, value FROM readings WHERE sid=? AND fid=? AND updated > ?;",[self.sid, field.fid, updated])
                    field.readings = []
                    for result in results:
                        field.readings.append(Reading(self.sid, result[0], result[1], result[2]))

            return fields

class Sensors(object):

    def __init__(self):
        self.sensors = []

    def load(self):
        """Loads all sensors from database"""
        with sqlite3.connect("db.sqlite") as conn:
            results = conn.execute("SELECT sid, token, title, description, updated FROM sensors GROUP BY sid").fetchall()
            # Add all results to list
            for result in results:
                self.sensors.append(Sensor(result[0],result[1],result[2],result[3],result[4]))

    def add(self, sid, token=None, title=None, description=None):
        """Adds new sensor to database"""
        if token == None: token = ''.join(random.choice(string.ascii_uppercase+string.digits) for _ in range(16))
        if title == None: description = "Default title"
        if description == None: description = "Default description"

        with sqlite3.connect("db.sqlite") as conn:
            conn.execute("INSERT INTO sensors (sid, token, title, description) VALUES (?,?,?,?)",[sid,token,title, description])
            sensor = Sensor(sid,token,title,description, None)
            self.sensors.append(sensor)
            return True
        return None

    def remove_field(self, fid):
        """Removes field from database and all of its readings ! BE CAREFUL"""
        field = self.get_field(fid)
        if field:
            with sqlite3.connect("db.sqlite") as conn:
                conn.execute("DELETE FROM fields WHERE fid=?", [fid])
                conn.execute("DELETE FROM readings WHERE fid=?", [fid])
                return True
        return False

    def remove(self,sid):
        """Removes sensor from database and all of its fields and readings ! BE CAREFUL"""
        sensor = self.get(sid)
        if sensor:
            with sqlite3.connect("db.sqlite") as conn:
                conn.execute("DELETE FROM sensors WHERE sid=?",[sid])
                conn.execute("DELETE FROM fields WHERE sid=?", [sid])
                conn.execute("DELETE FROM readings WHERE sid=?", [sid])
                self.sensors.remove(sensor)
                return True
        return False

    def get(self, sid):
        """Returns sensor from list by id"""
        for index, sensor in enumerate(self.sensors):
            if sensor.sid == sid:
                return self.sensors[index]
        return None

    def get_latest(self):
        """Returns list with latest readings from all sensors"""
        latest = {}
        for sensor in self.sensors:
            latest[sensor.sid] = sensor.get_latest()

    def get_readings(self, delta=None, group_minutes=None):
        """Returns fields with readings from all sensors"""
        readings = {}
        for sensor in self.sensors:
            readings[sensor.sid] = sensor.get_readings(delta, group_minutes)
        return readings

    def get_field(self, fid):
        for sensor in self.sensors:
            for field in sensor.get_fields():
                if field.fid == fid:
                    return field
        return None

    def update(self, sid, field_name, value):
        """Adds reading into database"""
        sensor = self.get(sid)
        if sensor:
            sensor.update(field_name, value)
            return True
        return False