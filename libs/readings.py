
class Reading(object):

    def __init__(self, sid, fid, updated, value):
        """Contains one reading, you should get reading from database everytime you need a reading.
        Do not store it anywhere in RAM! There are too many readings, save memory!"""
        self.sid = sid
        self.fid = fid
        self.updated = updated
        self.value = value