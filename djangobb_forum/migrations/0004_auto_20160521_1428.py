# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangobb_forum', '0003_remove_profile_show_smilies'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='poll',
            name='topic',
        ),
        migrations.RemoveField(
            model_name='poll',
            name='users',
        ),
        migrations.RemoveField(
            model_name='pollchoice',
            name='poll',
        ),
        migrations.DeleteModel(
            name='Poll',
        ),
        migrations.DeleteModel(
            name='PollChoice',
        ),
    ]
