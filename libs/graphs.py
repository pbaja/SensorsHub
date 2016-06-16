import datetime, collections
from libs.fields import Field

class Graph(object):

    @staticmethod
    def generate(field_ids, group_by="15M", range=60*60*24, sensor_label=False, sensors=None):

        # Group by
        group_labels = "%H:%M"
        group_seconds = float(group_by[:-1])
        group_unit = group_by[-1]
        if group_unit == "M": group_seconds *= 60
        elif group_unit == "H": group_seconds *= 60*60
        elif group_unit == "d": group_seconds *= 60*60*24
        elif group_unit == "m": group_seconds *= 60*60*24*31

        if group_seconds >= 525600: group_labels = "%Y"
        elif group_seconds >= 1440: group_labels = "%d.%m"

        # Get fields
        fields = []
        for fid in field_ids:
            field = Field.get(fid=fid)[0]
            field.get_readings(range, group_by)
            fields.append(field)

        # Generate labels
        y = {}
        for field in fields:
            # Create key for every field
            for reading in field.readings:
                # Round to nearest
                key = round(reading.updated / group_seconds) * group_seconds
                # Append time
                if not key in y:
                    y[key] = []
                # Append reading
                y[key].append(reading)

        # Sort dictionary
        y = collections.OrderedDict(sorted(y.items(), key=lambda f: f[0]))

        # Extract labels
        labels = [datetime.datetime.fromtimestamp(t).strftime(group_labels) for t in list(y.keys())]

        # Generate datasets
        datasets = []
        for field in fields:
            label = field.display_name
            if sensor_label: label = sensors.get(sid=field.sid).title + " " + label

            dataset = {"label": label, "data": [], "fill": False, "borderColor": field.color}
            for values in y.values():
                # Get value for exact field
                for value in values:
                    if value.fid == field.fid:
                        dataset["data"].append(value.value)
                        break
                else:
                    dataset["data"].append(None)

            datasets.append(dataset)

        '''
        # Generate labels
        readings = fields[0].readings
        labels = []
        ttime *= 60
        for reading in readings:
            # Round to nearest
            upd = round(reading.updated / ttime) * ttime
            # Append label
            labels.append(datetime.datetime.fromtimestamp(upd).strftime(group_labels))

        # Generate datasets
        datasets = []
        for field in fields:
            label = field.display_name
            #TODO Do it better :P
            if sensor_label: label = sensors.get(sid=field.sid).title + " " + label

            dataset = {"label": label, "data": [], "fill": False, "borderColor": field.color}
            for reading in field.readings:
                dataset["data"].append(reading.value)
            datasets.append(dataset)

        '''

        # Create data for chart
        return {
                "labels": labels,
                "datasets": datasets
         }