import sqlite3
import time
import enum
import random

from libs.readings import Reading

class FieldType(enum.IntEnum):
    FLOAT = 0 # Default
    INTEGER = 1
    BOOL = 2 # Switches, ON/OFF
    PERCENT = 3 # Just float, but treated as percentage

class Field(object):
    """Class containing one field"""

    def __init__(self, sid, fid, name, unit, display_name, icon, color, updated, parent, fieldtype):
        """Creates new field from arguments"""
        self.sid = sid
        self.fid = fid
        self.name = name
        self.unit = unit
        self.icon = icon
        self.color = color
        self.updated = updated
        self.parent = parent
        self.fieldtype = fieldtype

        if display_name: self.display_name = display_name
        else: self.display_name = name

        self.readings = []

    @staticmethod
    def remove(fid):
        """Removes field from database and all of its readings ! BE CAREFUL"""
        field = Field.get(fid=fid)
        if field:
            with sqlite3.connect("db.sqlite") as conn:
                conn.execute("DELETE FROM fields WHERE fid=?", [fid])
                conn.execute("DELETE FROM readings WHERE fid=?", [fid])
                return True
        return False

    @staticmethod
    def get(sid=None, fid=None, name=None):
        """Return array with new field/s from database based on fid, sid and/or name"""
        where = []
        values = []
        if fid is not None:
            where.append("fid=?")
            values.append(fid)
        if sid is not None:
            where.append("sid=?")
            values.append(sid)
        if name is not None:
            where.append("name=?")
            values.append(name)

        with sqlite3.connect("db.sqlite") as conn:
            results = conn.execute("SELECT sid, fid, name, unit, display_name, icon, color, updated, parent, type FROM fields WHERE " + " AND ".join(where),values).fetchall()
            if len(results) > 0:
                fields = []
                for result in results:
                    fields.append(Field(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7], result[8], result[9]))
                return fields
            else:
                return None

    @classmethod
    def create(cls, sid, name, unit=None, display_name=None, icon=None, color=None, parent=None, fieldtype=FieldType.FLOAT):
        """Create new field in database and return it"""
        into = ["sid", "name"]
        values = [sid, name]

        if unit is not None:
            into.append("unit")
            values.append(unit)
        if display_name is not None:
            into.append("display_name")
            values.append(display_name)
        if parent is not None:
            into.append("parent")
            values.append(parent)
        if icon is not None:
            into.append("icon")
            values.append(icon)
        if icon is not None:
            into.append("color")
            values.append(color)
        if type is not None:
            into.append("type")
            values.append(type)

        with sqlite3.connect("db.sqlite") as conn:
            result = conn.execute("INSERT INTO fields ("+",".join(into)+") VALUES ("+",".join(["?"] * len(into))+")", values)
            return cls(sid, result.lastrowid, name, unit, display_name, icon, color, time.time(), parent, fieldtype)

    def get_readings(self, group_minutes="1S", date_from=None, date_to=None):
        """Returns array with readings associated with this field (also stores them in field.readings)"""
        with sqlite3.connect("db.sqlite") as conn:
            # Create updated value from delta
            if date_to is None:
                date_to = time.time()
            if date_from is None:
                date_from = date_to - 24*60*60

            # Split group_minutes to strftime format
            group_add = "%Y"
            if group_minutes[-1] != "m":
                group_add += "%m"
                if group_minutes[-1] != "d":
                    group_add += "%d"
                    if group_minutes[-1] != "H":
                        group_add += "%H0"

            # If group_minutes not equals '1S', average results by group_minutes
            if group_minutes != "1S":
                results = conn.execute(
                    "SELECT fid, updated, AVG(value) FROM readings WHERE sid=? AND fid=? AND updated > ? AND updated < ? "
                    "GROUP BY strftime(?,datetime(updated, 'unixepoch'))+strftime(?,datetime(updated, 'unixepoch'))/? "
                    "ORDER BY updated",
                    [self.sid, self.fid, date_from, date_to, group_add, '%' + group_minutes[-1], group_minutes[:-1]]).fetchall()
            # Otherwise, get all readings withouth averaging
            else:
                results = conn.execute(
                    "SELECT fid, updated, value FROM readings WHERE sid=? AND fid=? AND updated > ? AND updated < ?;",
                    [self.sid, self.fid, date_from, date_to]).fetchall()

            # Create readings from results
            readings = []
            for result in results:
                readings.append(Reading(self.sid, result[0], result[1], round(result[2],2)))
            self.readings = readings
            return readings

    def commit(self):
        """Send changes to database"""
        with sqlite3.connect("db.sqlite") as conn:
            conn.execute("UPDATE fields SET name=?, unit=?, updated=?,  display_name=?, color=?, icon=?, parent=?, type=? WHERE fid=?",
                         [self.name, self.unit, self.updated, self.display_name, self.color, self.icon, self.parent, self.fieldtype, self.fid])
            return True

    def last_update(self):
        """Returns seconds from last update"""
        if self.updated is not None: return time.time() - self.updated
        else: return 0

    def last_reading(self):
        """Returns last reading"""
        with sqlite3.connect("db.sqlite") as conn:
            results = conn.execute("SELECT updated, value FROM readings WHERE fid=? ORDER BY updated DESC LIMIT 1",[self.fid]).fetchall()
        if len(results) > 0:
            result = results[0]
            return Reading(self.sid, self.fid, result[0], result[1])