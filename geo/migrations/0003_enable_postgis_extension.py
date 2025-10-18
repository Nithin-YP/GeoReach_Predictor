from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("geo", "0002_remove_demographicprofile_geo_demogra_state_i_c97c76_idx_and_more"),
    ]

    operations = [
        CreateExtension("postgis"),
    ]
