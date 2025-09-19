import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class TestConsultationConsumer(AsyncWebsocketConsumer):
    """Simplified consumer for testing WebSocket signals"""

    async def connect(self):
        """Handle WebSocket connection"""
        logger.info("WebSocket connection attempted")

        # Accept the connection
        await self.accept()

        # Add to doctors group for testing
        await self.channel_layer.group_add(
            "doctors",
            self.channel_name
        )

        logger.info(f"WebSocket connected and added to doctors group: {self.channel_name}")

        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'welcome',
            'message': 'Connected to test WebSocket - waiting for consultations...'
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"WebSocket disconnected: {self.channel_name}")

        # Remove from doctors group
        await self.channel_layer.group_discard(
            "doctors",
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            logger.info(f"WebSocket message received: {data}")

            # Echo back for testing
            await self.send(text_data=json.dumps({
                'type': 'echo',
                'received': data
            }))

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")

    # Group message handlers
    async def consultation_created(self, event):
        """Send consultation_created event to WebSocket"""
        logger.info(f"Sending consultation_created to {self.channel_name}")

        await self.send(text_data=json.dumps({
            'type': 'consultation_created',
            'data': event['consultation'],
            'timestamp': event.get('timestamp')
        }))

    async def consultation_updated(self, event):
        """Send consultation_updated event to WebSocket"""
        logger.info(f"Sending consultation_updated to {self.channel_name}")

        await self.send(text_data=json.dumps({
            'type': 'consultation_updated',
            'data': event['consultation'],
            'timestamp': event.get('timestamp')
        }))

    async def consultation_status_changed(self, event):
        """Send consultation_status_changed event to WebSocket"""
        logger.info(f"Sending consultation_status_changed to {self.channel_name}")

        await self.send(text_data=json.dumps({
            'type': 'consultation_status_changed',
            'data': event['consultation'],
            'timestamp': event.get('timestamp')
        }))