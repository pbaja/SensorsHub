import datetime, collections
from libs.fields import Field

class Graph(object):
    """Class containing userful functions for charts"""

    @staticmethod
    def generate(field_ids,
                 group_by="15M",
                 date_from=None,
                 date_to=None,
                 sensor_label=False,
                 sensors=None,
                 return_fields=False,
                 prefix="",
                 datasetConfig={},
                 generateAverage=False):
        """Generate chart data based on arguments"""

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
            field.get_readings(group_by, date_from, date_to)
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
            if sensor_label: label = sensors.get_single(sid=field.sid).title + " " + label

            dataset = {"label": prefix+label, "data": [],  "borderColor": field.color}
            dataset.update(datasetConfig)
            for values in y.values():
                # Get value for exact field
                for value in values:
                    if value.fid == field.fid:
                        dataset["data"].append(value.value)
                        break
                else:
                    dataset["data"].append(None)

            datasets.append(dataset)

        # Generate average
        if generateAverage:
            avg_dataset = {"label": "average", "data": [], "borderColor": "#777"}
            avg_dataset.update(datasetConfig)
            for i in range(len(labels)):
                sum = 0
                tot = 0
                non = False
                for dataset in datasets:
                    if dataset["data"][i] == None:
                        non = True
                        break
                    sum += dataset["data"][i]
                    tot += 1

                if non: avg_dataset["data"].append(None)
                else: avg_dataset["data"].append(sum / tot)

            datasets.append(avg_dataset)

        # Create data for chart
        data = {
            "labels": labels,
            "datasets": datasets
        }
        if return_fields: return (fields, data)
        else: return data