# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangobb_forum', '0009_auto_20160521_2055'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='topic',
            name='views',
        ),
    ]
