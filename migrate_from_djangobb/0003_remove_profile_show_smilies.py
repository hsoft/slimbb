# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangobb_forum', '0002_auto_20160521_1149'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='show_smilies',
        ),
    ]
