# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangobb_forum', '0006_auto_20160521_1511'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='aim',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='icq',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='jabber',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='location',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='msn',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='site',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='status',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='yahoo',
        ),
    ]
