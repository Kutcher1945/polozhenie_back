"""
Optimized WebSocket Consumer for Consultation Management

Features:
- Role-based group management
- Automatic authentication
- Type-safe event handling
- Built-in error handling
- Consultation-specific optimizations
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)

class OptimizedConsultationConsumer(AsyncWebsocketConsumer):
    """
    Optimized WebSocket consumer specifically for consultation management
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.user_role = None
        self.user_id = None
        self.groups = set()

    async def connect(self):
        """Handle WebSocket connection"""
        logger.info(f"Consultation WebSocket connection attempted: {self.channel_name}")

        # Accept connection immediately
        await self.accept()

        # Send connection acknowledgment
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to consultation WebSocket',
            'timestamp': timezone.now().isoformat()
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"Consultation WebSocket disconnected: {self.channel_name}, code: {close_code}")

        # Clean up all groups
        for group_name in self.groups.copy():
            await self.leave_group(group_name)

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            logger.info(f"Consultation WebSocket received: {message_type}")

            # Route messages to appropriate handlers
            if message_type == 'authenticate':
                await self.handle_authenticate(data)
            elif message_type == 'ping':
                await self.handle_ping()
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_error(f"Unknown message type: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {text_data}")
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await self.send_error("Internal server error")

    async def handle_authenticate(self, data):
        """Handle user authentication and group joining"""
        token = data.get('token')

        if not token:
            await self.send_error("Authentication token is required")
            return

        # Authenticate user
        user = await self.authenticate_user(token)

        if user and not isinstance(user, AnonymousUser):
            self.user = user
            self.user_role = getattr(user, 'role', None)
            self.user_id = user.id

            # Join role-specific groups
            await self.join_user_groups()

            # Send authentication success
            await self.send(text_data=json.dumps({
                'type': 'authenticated',
                'data': {
                    'user_id': user.id,
                    'email': user.email,
                    'role': self.user_role,
                    'groups': list(self.groups)
                },
                'timestamp': timezone.now().isoformat()
            }))

            logger.info(f"User authenticated: {user.email} (role: {self.user_role})")

        else:
            await self.send_error("Invalid authentication token")

    async def join_user_groups(self):
        """Join user to appropriate groups based on their role"""
        if not self.user or not self.user_role:
            return

        # Personal user group
        personal_group = f"user_{self.user_id}"
        await self.join_group(personal_group)

        # Role-based groups
        if self.user_role == 'doctor':
            await self.join_group("doctors")
            await self.join_group("consultations_staff")
            logger.info(f"Doctor {self.user.email} joined doctors group")

        elif self.user_role == 'patient':
            await self.join_group("patients")
            await self.join_group("consultations_users")
            logger.info(f"Patient {self.user.email} joined patients group")

        elif self.user_role == 'admin':
            await self.join_group("admins")
            await self.join_group("doctors")  # Admins can see doctor notifications
            await self.join_group("consultations_staff")
            logger.info(f"Admin {self.user.email} joined admin groups")

    async def join_group(self, group_name):
        """Join a channel group and track it"""
        await self.channel_layer.group_add(group_name, self.channel_name)
        self.groups.add(group_name)
        logger.debug(f"Joined group: {group_name}")

    async def leave_group(self, group_name):
        """Leave a channel group and stop tracking it"""
        await self.channel_layer.group_discard(group_name, self.channel_name)
        self.groups.discard(group_name)
        logger.debug(f"Left group: {group_name}")

    async def handle_ping(self):
        """Handle ping for keepalive"""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        }))

    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'data': {'message': message},
            'timestamp': timezone.now().isoformat()
        }))

    @database_sync_to_async
    def authenticate_user(self, token):
        """Authenticate user by token"""
        try:
            token_obj = Token.objects.select_related('user').get(key=token)
            user = token_obj.user

            if user.is_active:
                return user
            else:
                logger.warning(f"Inactive user attempted to connect: {user.email}")
                return AnonymousUser()

        except Token.DoesNotExist:
            logger.warning(f"Invalid token: {token[:10]}...")
            return AnonymousUser()
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return AnonymousUser()

    # ==========================================
    # Group Event Handlers (called by signals)
    # ==========================================

    async def consultation_created(self, event):
        """Handle consultation created event"""
        logger.info(f"Sending consultation_created to {self.channel_name}")

        consultation_data = event.get('consultation', {})

        # Add additional metadata for the frontend
        enhanced_data = {
            **consultation_data,
            'event_type': 'consultation_created',
            'recipient_role': self.user_role,
            'requires_action': self.user_role == 'doctor' and consultation_data.get('status') == 'pending'
        }

        await self.send(text_data=json.dumps({
            'type': 'consultation_created',
            'data': enhanced_data,
            'timestamp': event.get('timestamp', timezone.now().isoformat())
        }))

    async def consultation_updated(self, event):
        """Handle consultation updated event"""
        logger.info(f"Sending consultation_updated to {self.channel_name}")

        await self.send(text_data=json.dumps({
            'type': 'consultation_updated',
            'data': event.get('consultation', {}),
            'timestamp': event.get('timestamp', timezone.now().isoformat())
        }))

    async def consultation_status_changed(self, event):
        """Handle consultation status change event"""
        logger.info(f"Sending consultation_status_changed to {self.channel_name}")

        consultation_data = event.get('consultation', {})

        # Add role-specific metadata
        enhanced_data = {
            **consultation_data,
            'recipient_role': self.user_role,
            'is_relevant': self._is_consultation_relevant(consultation_data)
        }

        await self.send(text_data=json.dumps({
            'type': 'consultation_status_changed',
            'data': enhanced_data,
            'timestamp': event.get('timestamp', timezone.now().isoformat())
        }))

    async def doctor_availability_changed(self, event):
        """Handle doctor availability change event"""
        logger.info(f"Sending doctor_availability_changed to {self.channel_name}")

        await self.send(text_data=json.dumps({
            'type': 'doctor_availability_changed',
            'data': event.get('data', {}),
            'timestamp': event.get('timestamp', timezone.now().isoformat())
        }))

    def _is_consultation_relevant(self, consultation_data):
        """Check if consultation is relevant to the current user"""
        if not self.user_id:
            return False

        # Doctors see all consultations
        if self.user_role == 'doctor':
            return True

        # Patients only see their own consultations
        if self.user_role == 'patient':
            return consultation_data.get('patient_id') == self.user_id

        # Admins see all
        if self.user_role == 'admin':
            return True

        return False