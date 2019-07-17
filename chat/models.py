from django.db import models
from django.contrib.auth import get_user_model

from .settings import PRESENCE_ROOM_NAME

User = get_user_model()


class Channel(models.Model):
    '''One to one model with users for storing their channel names'''

    name = models.CharField(max_length=255, primary_key=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE)


class Room(models.Model):
    '''Chat room model'''

    name = models.CharField(max_length=255, unique=True)

    occupants = models.ManyToManyField(
        User,
        through='Presence',
        through_fields=('room', 'user')
    )

    def __str__(self):
        return '%s (%d)' % (self.name, len(self.occupants))


class Presence(models.Model):
    '''User presence model'''

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    room = models.ForeignKey(Room, on_delete=models.CASCADE)


class AbstractMessage(models.Model):
    '''Abstract model for a message'''

    sender = models.ForeignKey(User, related_name='+', null=True,
                               on_delete=models.SET_NULL)

    content = models.TextField()

    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.sender.username

    class Meta:
        abstract = True


class GroupMessage(AbstractMessage):
    '''Message model for room messages'''

    room = models.ForeignKey(Room, related_name='+', null=True,
                             on_delete=models.CASCADE)


class DirectMessage(AbstractMessage):
    '''Message model for direct messages'''

    recipient = models.ForeignKey(User, related_name='+', null=True,
                                  on_delete=models.CASCADE)

    seen_at = models.DateTimeField()

    seen = models.BooleanField()
