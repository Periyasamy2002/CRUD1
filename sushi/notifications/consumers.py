from channels.generic.websocket import AsyncJsonWebsocketConsumer

class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close()
            return
        self.group_name = f"notifications_user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # handler for server-sent events: server uses type "notify"
    async def notify(self, event):
        payload = event.get("payload", {})
        await self.send_json(payload)
