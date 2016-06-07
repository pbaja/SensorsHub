import sqlite3
import time

from libs.readings import Reading


class Field(object):
    """Class containing one field"""

    def __init__(self, sid, fid, name, unit, display_name, style):
        """Creates new field from arguments"""
        self.sid = sid
        self.fid = fid
        self.name = name
        self.unit = unit
        self.updated = None
        self.value = None
        self.readings = []

        if display_name:
            self.display_name = display_name
        else:
            self.display_name = name

        self.icon = None
        self.color = None
        if style:
            style = style.split("#")
            if len(style) > 0:
                self.icon = style[0]
            if len(style) > 1:
                self.color = "#"+style[1]

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
            query = "SELECT sid, fid, name, unit, display_name, style FROM fields WHERE " + " AND ".join(where)
            print(query)
            results = conn.execute(query,values).fetchall()
            if len(results) > 0:
                fields = []
                for result in results:
                    fields.append(Field(result[0], result[1], result[2], result[3], result[4], result[5]))
                return fields
            else:
                return None

    @staticmethod
    def create(sid, name):
        """Create new field in database and return it"""
        with sqlite3.connect("db.sqlite") as conn:
            result = conn.execute("INSERT INTO fields (sid, name) VALUES (?,?);", [sid, name])
            return Field(sid, result.lastrowid, name, None, name, None)

    def get_readings(self, delta=0, group_minutes="1S"):
        """Returns array with readings associated with this field (also stores them in field.readings)"""
        with sqlite3.connect("db.sqlite") as conn:
            # Create updated value from delta
            if delta != 0:
                updated = time.time() - delta
            else:
                updated = 0

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
                    "SELECT updated, fid, AVG(value) FROM readings WHERE sid=? AND fid=? AND updated > ? "
                    "GROUP BY strftime(?,datetime(updated, 'unixepoch'))+strftime(?,datetime(updated, 'unixepoch'))/? "
                    "ORDER BY updated",
                    [self.sid, self.fid, updated, group_add, '%' + group_minutes[-1], group_minutes[:-1]])
            # Otherwise, get all readings withouth averaging
            else:
                results = conn.execute(
                    "SELECT updated, fid, value FROM readings WHERE sid=? AND fid=? AND updated > ?;",
                    [self.sid, self.fid, updated])

            # Create readings from results
            readings = []
            for result in results:
                readings.append(Reading(self.sid, result[0], result[1], result[2]))
            self.readings = readings
            return readings

    def commit(self):
        """Send changes to database"""
        with sqlite3.connect("db.sqlite") as conn:
            conn.execute("UPDATE fields SET name=?, unit=?, updated=?, value=?, display_name=?, style=? WHERE fid=?",
                         [self.name, self.unit, self.updated, self.value, self.display_name, "{}{}".format(self.icon, self.color), self.fid])
            return True
