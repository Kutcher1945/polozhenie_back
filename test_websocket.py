#!/usr/bin/env python3
"""
Simple test script to verify WebSocket implementation
"""
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """Test WebSocket connection to the Django server"""

    # Replace with actual token from your database
    test_token = "your_test_token_here"

    # WebSocket URL
    ws_url = "ws://localhost:8000/ws/consultations/"

    try:
        logger.info(f"Connecting to WebSocket: {ws_url}")

        async with websockets.connect(ws_url) as websocket:
            logger.info("✅ WebSocket connection established")

            # Send authentication message
            auth_message = {
                "type": "authenticate",
                "token": test_token,
                "user_id": 1,
                "user_role": "doctor"
            }

            await websocket.send(json.dumps(auth_message))
            logger.info("📤 Authentication message sent")

            # Listen for messages for 30 seconds
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(message)
                    logger.info(f"📥 Received: {data}")

            except asyncio.TimeoutError:
                logger.info("⏰ No messages received within 30 seconds")

    except websockets.exceptions.ConnectionRefused:
        logger.error("❌ Connection refused - Make sure Django server is running")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {str(e)}")

if __name__ == "__main__":
    print("🧪 WebSocket Test Script")
    print("Make sure your Django server is running on port 8000")
    print("You may need to update the test_token variable with a real token")
    print("-" * 50)

    asyncio.run(test_websocket_connection())