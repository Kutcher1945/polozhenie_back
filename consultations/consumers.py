import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)

class ConsultationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle WebSocket connection"""
        logger.info("WebSocket connection attempted")

        # Accept the connection first
        await self.accept()

        # Add to general consultations group
        await self.channel_layer.group_add(
            "consultations",
            self.channel_name
        )

        logger.info(f"WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"WebSocket disconnected: {self.channel_name}, code: {close_code}")

        # Remove from all groups
        await self.channel_layer.group_discard(
            "consultations",
            self.channel_name
        )

        # Remove from doctors group if user was a doctor
        await self.channel_layer.group_discard(
            "doctors",
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            logger.info(f"WebSocket message received: {data}")

            if data.get('type') == 'authenticate':
                await self.handle_authentication(data)
            else:
                logger.warning(f"Unknown message type: {data.get('type')}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")

    async def handle_authentication(self, data):
        """Handle user authentication"""
        token = data.get('token')
        user_id = data.get('user_id')
        user_role = data.get('user_role')

        if token:
            # Authenticate user with token
            user = await self.authenticate_user(token)
            self.scope['user'] = user

            if user and not isinstance(user, AnonymousUser):
                logger.info(f"User authenticated: {user.email} (role: {user.role})")

                # Join role-specific groups
                if user.role == 'doctor':
                    await self.channel_layer.group_add(
                        "doctors",
                        self.channel_name
                    )
                    logger.info(f"Doctor {user.email} added to doctors group")

                # Send authentication success
                await self.send(text_data=json.dumps({
                    'type': 'authentication_success',
                    'message': 'Successfully authenticated',
                    'user_role': user.role
                }))
            else:
                logger.warning(f"Authentication failed for token: {token[:10]}...")
                await self.send(text_data=json.dumps({
                    'type': 'authentication_error',
                    'message': 'Invalid token'
                }))
        else:
            logger.warning("No token provided for authentication")

    @database_sync_to_async
    def authenticate_user(self, token):
        """Authenticate user by token"""
        try:
            token_obj = Token.objects.get(key=token)
            return token_obj.user
        except Token.DoesNotExist:
            logger.warning(f"Token not found: {token[:10]}...")
            return AnonymousUser()
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return AnonymousUser()

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