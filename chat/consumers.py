from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, GroupMessage, DirectMessage, Presence, User
from .settings import PRESENCE_ROOM_NAME
from .views import (enter_room, exit_room, create_direct_message,
                    create_group_message, add_user_channel,
                    remove_user_channel)
import json


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    This consumer will handle all of the communication both to and from the
    UI, allowing us to multiplex all of the chat traffic through the single
    websocket connection.
    """

    async def join_room(self, name=PRESENCE_ROOM_NAME):
        """
        Join a room, creating if necessary and broadcast needed messages 
        """
        room, occupancy, created = await enter_room(self.user, name=name)
        await self.channel_layer.group_add(
            room.name,
            self.channel_name
        )
        if created:
            await self.channel_layer.group_send(
                PRESENCE_ROOM_NAME,
                {
                    'type': 'room',
                    'action': 'open',
                    'room': room.name
                }
            )
        await self.channel_layer.group_send(
            PRESENCE_ROOM_NAME,
            {
                'type': 'presence',
                'action': 'join',
                'room': room.name,
                'occupancy': occupancy,
                'user': self.user.id,
                'username': self.user.username
            }
        )
        return room

    async def leave_room(self, name=PRESENCE_ROOM_NAME):
        """
        Leave a room, deleting if necessary and broadcast needed messages
        """
        occupancy, deleted = await exit_room(self.user, name=name)
        await self.channel_layer.group_discard(
            name,
            self.channel_name
        )
        if deleted:
            await self.channel_layer.group_send(
                PRESENCE_ROOM_NAME,
                {
                    'type': 'room',
                    'action': 'close',
                    'room': name
                }
            )
        await self.channel_layer.group_send(
            PRESENCE_ROOM_NAME,
            {
                'type': 'presence',
                'action': 'leave',
                'room': name,
                'occupancy': occupancy,
                'user': self.user.id,
                'username': self.user.username
            }
        )

    async def send_group_message(self, room_name, content):
        msg, room = await create_group_message(self.user, room_name, content)
        await self.channel_layer.group_send(
            room.name,
            {
                'type': 'chat_message',
                'msg_type': 'group',
                'content': content,
                'sender_id': self.user.id,
                'sender_usernamne': self.user.username,
                'message_id': msg.pk
            }
        )

    async def send_direct_message(self, recipient_id, content):
        msg, channel = await create_direct_message(self.user, recipient_id,
                                                   content)
        await self.channel_layer.send(
            channel.name,
            {
                'type': 'chat_message',
                'msg_type': 'direct',
                'content': content,
                'sender_id': self.user.id,
                'sender_usernamne': self.user.username,
                'message_id': msg.pk
            }
        )

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated or self.user.is_anonymous:
            await self.close()
            pass

        self.rooms = set()
        await add_user_channel(self.user, self.channel_name)
        await self.accept()
        await self.join_room()

    async def disconnect(self, close_code):
        await remove_user_channel(self.channel_name)
        for room_name in self.rooms:
            await self.leave_room(name=room_name)
        self.leave_room()
        # Leave room group

    # Receive message from WebSocket
    async def receive_json(self, content):
        '''
        Handle a websocket frame from the client
        '''
        command = content.get("command", None)
        try:
            if command == 'join':
                room_name = content["room"]
                self.rooms.add(room_name)
                await self.join_room(room_name)
            elif command == 'leave':
                room_name = content["room"]
                await self.leave_room(content["room"])
                self.rooms.remove(room_name)
            elif command == 'message':
                msg_type = content["type"]
                if msg_type == 'group':
                    room_name = content["room"]
                    await self.send_group_message(room_name, content)
                elif msg_type == 'group':
                    recipient_id = content["recipient"]
                    await self.send_direct_message(recipient_id, content)
            else:
                raise Exception('Unknown command: ' + command)
        except Exception as err:
            await self.send_json(err)

    async def chat_message(self, event):
        await self.send_json({
            'type': 'message',
            'msg_type': event["msg_type"],
            'content': event["content"],
            'sender_id': event["sender_id"],
            'sender_username': event["sender_username"],
            'message_id': event["message_id"]
        })

    async def presence(self, event):
        """
        A user joined or left a room, send the details to the UI
        """
        await self.send_json({
            'type': 'presence',
            'action': event["action"],
            'room': event["room"],
            'user_id': event["user_id"],
            'username': event["username"]
        })

    async def room(self, event):
        """
        A room was opened or closed, send the details to the UI
        """
        await self.send_json({
            'type': 'room',
            'action': event["action"],
            'room': event["room"]
        })