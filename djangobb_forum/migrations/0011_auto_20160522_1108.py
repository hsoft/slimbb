# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangobb_forum', '0010_remove_topic_views'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='attachment',
            table='slimbb_attachment',
        ),
        migrations.AlterModelTable(
            name='ban',
            table='slimbb_ban',
        ),
        migrations.AlterModelTable(
            name='category',
            table='slimbb_category',
        ),
        migrations.AlterModelTable(
            name='forum',
            table='slimbb_forum',
        ),
        migrations.AlterModelTable(
            name='post',
            table='slimbb_post',
        ),
        migrations.AlterModelTable(
            name='posttracking',
            table='slimbb_posttracking',
        ),
        migrations.AlterModelTable(
            name='profile',
            table='slimbb_profile',
        ),
        migrations.AlterModelTable(
            name='report',
            table='slimbb_report',
        ),
        migrations.AlterModelTable(
            name='topic',
            table='slimbb_topic',
        ),
    ]
