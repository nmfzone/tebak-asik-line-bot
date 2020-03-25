import django.utils.timezone
import model_utils.fields
from common.db import models as common_models
from django.db import migrations, models
from jsonfield import JSONField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', common_models.PositiveBigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID')
                 ),
                ('key', models.CharField(max_length=255, unique=True)),
                ('created_at', model_utils.fields.AutoCreatedField(
                    db_index=True,
                    default=django.utils.timezone.now,
                    editable=False
                )),
                ('updated_at', model_utils.fields.AutoLastModifiedField(
                    db_index=True,
                    default=django.utils.timezone.now,
                    editable=False
                )),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', common_models.PositiveBigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID'
                )),
                ('value', models.CharField(max_length=255)),
                ('answers', JSONField(null=True)),
                ('creator', models.ForeignKey(
                    'app.Player',
                    models.CASCADE,
                    '%(class)s_creator_is_player_related',
                    null=True
                )),
                ('for_player', models.ForeignKey(
                    'app.Player',
                    models.CASCADE,
                    '%(class)s_for_player_is_player_related',
                    null=True
                )),
                ('created_at', model_utils.fields.AutoCreatedField(
                    db_index=True,
                    default=django.utils.timezone.now,
                    editable=False
                )),
                ('updated_at', model_utils.fields.AutoLastModifiedField(
                    db_index=True,
                    default=django.utils.timezone.now,
                    editable=False
                )),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
