import datetime
from libs.fields import Field

class Graph(object):

    @staticmethod
    def generate(field_ids, group_by="15M", range=60 * 60 * 24):

        # Group by
        group_labels = "%H:%M"
        ttime = (2208989361.0 + datetime.datetime.strptime(group_by[:-1], "%" + group_by[-1]).timestamp()) / 60.0
        if ttime >= 525600:
            group_labels = "%Y"
        elif ttime >= 1440:
            group_labels = "%d.%m"

        # Get fields
        fields = []
        for fid in field_ids:
            field = Field.get(fid=fid)[0]
            field.get_readings(range, group_by)
            fields.append(field)

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
            dataset = {"label": field.display_name, "data": [], "fill": False, "borderColor": field.color}
            for reading in field.readings:
                dataset["data"].append(reading.value)
            datasets.append(dataset)

        # Create data for chart
        return {
                "labels": labels,
                "datasets": datasets
         }