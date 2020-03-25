from common.db import models as common_models
from common.models import IndexedTimeStampedModel
from django.db import models
from jsonfield import JSONField


class Player(IndexedTimeStampedModel):
    id = common_models.PositiveBigAutoField(
        auto_created=True,
        primary_key=True,
        serialize=False,
        verbose_name='ID'
    )
    key = models.CharField(
        max_length=255,
        unique=True
    )

    def __str__(self):
        return self.key


class Question(IndexedTimeStampedModel):
    id = common_models.PositiveBigAutoField(
        auto_created=True,
        primary_key=True,
        serialize=False,
        verbose_name='ID'
    )
    value = models.CharField(
        max_length=255,
    )
    answers = JSONField(null=True)
    creator = models.ForeignKey(
        Player,
        models.CASCADE,
        '%(class)s_creator_is_player_related',
        null=True
    )
    for_player = models.ForeignKey(
        Player,
        models.CASCADE,
        '%(class)s_for_player_is_player_related',
        null=True
    )

    def __str__(self):
        return '(%s) -> %s' % (self.id, self.value)
