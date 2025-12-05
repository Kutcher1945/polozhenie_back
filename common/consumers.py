import json
import logging
import jwt
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework.authtoken.models import Token
from .models import User

logger = logging.getLogger(__name__)

class SocketIOConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that handles Socket.IO-like events from frontend
    """

    async def connect(self):
        """Handle WebSocket connection"""
        logger.info("Socket.IO WebSocket connection attempted")

        # Extract token from query parameters
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        token = None

        if query_string:
            # Parse query parameters
            from urllib.parse import parse_qs
            params = parse_qs(query_string)
            token = params.get('token', [None])[0]

        logger.info(f"WebSocket connection with token: {token[:10] + '...' if token else 'None'}")

        # Try to authenticate if token is provided
        if token:
            user = await self.authenticate_user(token)
            if user and not isinstance(user, AnonymousUser):
                self.scope['user'] = user
                self.user_id = user.id
                logger.info(f"WebSocket authentication successful for user: {user.email}")
            else:
                logger.warning("WebSocket authentication failed")
                await self.close(code=4001, reason="Authentication failed")
                return
        else:
            logger.warning("No token provided for WebSocket connection")
            await self.close(code=4000, reason="Token required")
            return

        # Accept the connection
        await self.accept()

        # Add to general group
        await self.channel_layer.group_add(
            "socketio_clients",
            self.channel_name
        )

        # Add user to personal room if authenticated
        if hasattr(self, 'user_id'):
            await self.channel_layer.group_add(
                f"user_{self.user_id}",
                self.channel_name
            )

        # Add doctors to the doctors group for consultation notifications
        if hasattr(self.scope.get('user'), 'role') and self.scope['user'].role == 'doctor':
            await self.channel_layer.group_add(
                "doctors",
                self.channel_name
            )
            logger.info(f"Doctor {self.scope['user'].email} added to doctors group")

        logger.info(f"Socket.IO client connected: {self.channel_name}")

        # Send connection acknowledgment (Socket.IO style)
        await self.send(text_data=json.dumps({
            'type': 'connect',
            'data': {'message': 'Connected to WebSocket'}
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"Socket.IO client disconnected: {self.channel_name}, code: {close_code}")

        # Remove from groups
        await self.channel_layer.group_discard(
            "socketio_clients",
            self.channel_name
        )

        if hasattr(self, 'user_id'):
            await self.channel_layer.group_discard(
                f"user_{self.user_id}",
                self.channel_name
            )

        # Remove from doctors group if applicable
        if hasattr(self, 'scope') and self.scope.get('user'):
            user = self.scope['user']
            if getattr(user, 'role', None) == 'doctor':
                await self.channel_layer.group_discard(
                    "doctors",
                    self.channel_name
                )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages (Socket.IO events)"""
        try:
            data = json.loads(text_data)
            event_type = data.get('type')
            event_data = data.get('data', {})

            logger.info(f"Socket.IO event received: {event_type} with data: {event_data}")

            # Handle different Socket.IO-like events
            if event_type == 'authenticate':
                await self.handle_authenticate(event_data)
            elif event_type == 'join_room':
                await self.handle_join_room(event_data)
            elif event_type == 'leave_room':
                await self.handle_leave_room(event_data)
            elif event_type == 'send_message':
                await self.handle_send_message(event_data)
            elif event_type == 'ping':
                await self.handle_ping()
            else:
                logger.warning(f"Unknown Socket.IO event type: {event_type}")
                await self.send_error(f"Unknown event type: {event_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing Socket.IO message: {str(e)}")
            await self.send_error("Internal server error")

    async def handle_authenticate(self, data):
        """Handle user authentication"""
        token = data.get('token')

        if not token:
            await self.send_error("Token is required for authentication")
            return

        user = await self.authenticate_user(token)

        if user and not isinstance(user, AnonymousUser):
            self.scope['user'] = user
            self.user_id = user.id

            # Add user to personal room
            await self.channel_layer.group_add(
                f"user_{user.id}",
                self.channel_name
            )

            # Add doctors to the doctors group for consultation notifications
            if getattr(user, 'role', None) == 'doctor':
                await self.channel_layer.group_add(
                    "doctors",
                    self.channel_name
                )
                logger.info(f"Doctor {user.email} added to doctors group")

            logger.info(f"Socket.IO user authenticated: {user.email}")

            # Send authentication success
            await self.send(text_data=json.dumps({
                'type': 'authenticated',
                'data': {
                    'user_id': user.id,
                    'email': user.email,
                    'role': getattr(user, 'role', 'user')
                }
            }))
        else:
            await self.send_error("Invalid authentication token")

    async def handle_join_room(self, data):
        """Handle joining a room/channel"""
        room_name = data.get('room')

        if not room_name:
            await self.send_error("Room name is required")
            return

        # Add to room group
        await self.channel_layer.group_add(
            f"room_{room_name}",
            self.channel_name
        )

        logger.info(f"Socket.IO client joined room: {room_name}")

        await self.send(text_data=json.dumps({
            'type': 'joined_room',
            'data': {'room': room_name}
        }))

    async def handle_leave_room(self, data):
        """Handle leaving a room/channel"""
        room_name = data.get('room')

        if not room_name:
            await self.send_error("Room name is required")
            return

        # Remove from room group
        await self.channel_layer.group_discard(
            f"room_{room_name}",
            self.channel_name
        )

        logger.info(f"Socket.IO client left room: {room_name}")

        await self.send(text_data=json.dumps({
            'type': 'left_room',
            'data': {'room': room_name}
        }))

    async def handle_send_message(self, data):
        """Handle sending message to a room"""
        room_name = data.get('room')
        message = data.get('message')

        if not room_name or not message:
            await self.send_error("Room and message are required")
            return

        # Send message to room group
        await self.channel_layer.group_send(
            f"room_{room_name}",
            {
                'type': 'room_message',
                'message': message,
                'sender': getattr(self.scope.get('user'), 'email', 'Anonymous'),
                'room': room_name
            }
        )

    async def handle_ping(self):
        """Handle ping for keepalive"""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'data': {'timestamp': json.dumps({})}  # You can add timestamp here
        }))

    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'data': {'message': message}
        }))

    @database_sync_to_async
    def authenticate_user(self, token):
        """Authenticate user by token - prioritizes Token over JWT"""
        try:
            # First, always try Token authentication (our primary method)
            logger.info("Attempting Token authentication")
            token_obj = Token.objects.get(key=token)
            logger.info(f"Token authentication successful for user: {token_obj.user.email}")
            return token_obj.user
        except Token.DoesNotExist:
            logger.info("Token not found, trying JWT authentication")
            # Only try JWT if Token fails and token looks like JWT
            if '.' in token and len(token.split('.')) == 3:
                logger.info("Attempting JWT authentication as fallback")
                return self.authenticate_jwt(token)
            else:
                logger.warning(f"Invalid token format: {token[:10]}... (length: {len(token)})")
                return AnonymousUser()
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return AnonymousUser()

    def authenticate_jwt(self, token):
        """Authenticate JWT token"""
        try:
            # Get the JWT secret from settings
            secret_key = getattr(settings, 'SECRET_KEY', 'your-secret-key')

            # Decode the JWT token
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])

            # Get user from payload
            user_id = payload.get('user_id')
            if not user_id:
                logger.warning("JWT token missing user_id")
                return AnonymousUser()

            # Get user from database
            user = User.objects.get(id=user_id, is_active=True)
            logger.info(f"JWT authentication successful for user: {user.email}")
            return user

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return AnonymousUser()
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return AnonymousUser()
        except User.DoesNotExist:
            logger.warning(f"User not found for JWT token user_id: {user_id}")
            return AnonymousUser()
        except Exception as e:
            logger.error(f"JWT authentication error: {str(e)}")
            return AnonymousUser()

    # Group message handlers (these handle messages sent from Django views/signals)
    async def room_message(self, event):
        """Send room message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'data': {
                'room': event['room'],
                'message': event['message'],
                'sender': event['sender']
            }
        }))

    async def notification(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))

    async def broadcast(self, event):
        """Send broadcast message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'broadcast',
            'data': event['data']
        }))

    async def doctor_availability_changed(self, event):
        """Send doctor availability change notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'doctor_availability_changed',
            'data': {
                'doctor_id': event['doctor_id'],
                'availability_status': event['availability_status'],
                'availability_note': event.get('availability_note', ''),
                'old_status': event.get('old_status'),
                'doctor_info': event.get('doctor_info', {}),
                'timestamp': timezone.now().isoformat()
            }
        }))

    async def consultation_created(self, event):
        """Send consultation created notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'consultation_created',
            'data': {
                'consultation': event['consultation'],
                'timestamp': event['timestamp']
            }
        }))

    async def consultation_updated(self, event):
        """Send consultation updated notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'consultation_updated',
            'data': {
                'consultation': event['consultation'],
                'timestamp': event['timestamp']
            }
        }))

    async def consultation_status_changed(self, event):
        """Send consultation status change notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'consultation_status_changed',
            'data': {
                'consultation': event['consultation'],
                'timestamp': event['timestamp']
            }
        }))