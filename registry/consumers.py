# Built in imports.
import json
import asyncio
# Third Party imports.
from channels.exceptions import DenyConnection
from channels.generic.websocket import AsyncWebsocketConsumer


class RegistryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add(
            "asd",
            self.channel_name
        )

        # await self.channel_layer.group_send(
        #     "asd",
        #     {
        #         'type': 'update_load_status',
        #     }
        # )

    async def update_load_status(self, event):
        # Here helper function fetches live score from DB.
        for i in range(1, 101):
            await self.send(text_data=json.dumps({
                'loaded': i
            }))
            await asyncio.sleep(0.1)

    # TO DO: setup message receiving and disconnection

    async def generate_data(self, event):
        parameters = event['params']
        values = []
        for i in range(1, 101, 5):
            values.append((i, i ** 2))
            await self.send(text_data=json.dumps({
                'type': 'progress_update',
                'data': {
                    'progress': i
                }
            }))
            await asyncio.sleep(0.1)
        await self.send(text_data=json.dumps({
            'type': 'plot_data',
            'data': {
                'values': values
            }
        }))

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data['type'] == 'plot':
            await self.generate_data({'params': data['parameters']})

    async def websocket_disconnect(self, message):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
