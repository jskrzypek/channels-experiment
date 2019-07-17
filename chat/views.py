from django.shortcuts import render, get_object_or_404
from django.utils.safestring import mark_safe
from channels.db import database_sync_to_async
from .models import Channel, Room, GroupMessage, DirectMessage, Presence, User
from .settings import PRESENCE_ROOM_NAME
import json


def index(request):
    return render(request, 'chat/index.html', {})


def room(request, room_name):
    return render(request, 'chat/room.html', {
        'room_name_json': mark_safe(json.dumps(room_name))
    })


@database_sync_to_async
def add_user_channel(user, channel_name):
    '''
    Get the current user and add the supplied channel
    '''
    channel = Channel(name=channel_name, user=user.id)
    User.objects.get(pk=user.id).channel.add(channel)


@database_sync_to_async
def remove_user_channel(channel):
    '''
    Get the current user and remove the supplied channel
    '''

    Channel.objects.filter(name=channel).delete()


@database_sync_to_async
def enter_room(user, name=PRESENCE_ROOM_NAME):
    '''
    Find and enter a room, creating it if it does not exist.
    '''

    room, created = Room.objects.get_or_create(name=name)
    room.occupants.add(user)
    occupancy = room.occupants.count()

    return room, occupancy, created


@database_sync_to_async
def exit_room(user, room, strict=False):
    '''
    Exit a room, deleting the room if the last one to leave.
    '''

    room.occupants.remove(user)
    deleted = False
    occupancy = room.occupants.count()
    if occupancy == 0:
        Room.objects.filter(pk=room.id).delete()
        deleted = True

    return occupancy, deleted


@database_sync_to_async
def create_direct_message(user, recipient_id, content):
    '''
    Create a direct message
    '''
    recipient = get_object_or_404(User, pk=recipient_id)
    msg = DirectMessage.objects.create(sender=user, recipient=recipient,
                                       content=content)
    return msg, recipient.channel


@database_sync_to_async
def create_group_message(sender, room_name, content):
    '''
    Create a group message in a room
    '''
    room = get_object_or_404(Room, name=room_name)
    msg = GroupMessage.objects.create(sender=sender, room=room,
                                      content=content)
    return msg, room
