import asyncio
import logging
import requests

logger = logging.getLogger(__name__)


def get_mistral_api_key():
    """Get Mistral API key from Django settings"""
    try:
        from django.conf import settings
        api_key = getattr(settings, 'MISTRAL_API_KEY', None)
        if api_key:
            logger.info("✅ Mistral API key loaded from Django settings")
        else:
            logger.warning("⚠️ MISTRAL_API_KEY not found in Django settings")
        return api_key
    except Exception as e:
        logger.error(f"❌ Error loading Mistral API key: {e}")
        return None


async def get_conversational_ai_response(user_message: str):
    """Get conversational AI response for any user message"""
    # Get API key from Django settings
    MISTRAL_API_KEY = get_mistral_api_key()

    if not MISTRAL_API_KEY:
        logger.warning("⚠️ MISTRAL_API_KEY not available, AI response disabled")
        return None

    system_prompt = """
    You are a friendly and helpful medical assistant for ZhanCare, a telemedicine platform in Kazakhstan.

    Your role:
    - Answer medical and health questions in a clear, simple way
    - Be warm, conversational and empathetic
    - Always respond in Russian language
    - Keep responses short and concise (2-3 sentences)
    - Provide general health information only, no specific diagnoses
    - For serious symptoms, suggest consulting a doctor
    - For greetings, respond warmly

    Guidelines:
    - Be natural and friendly
    - Use simple language
    - No emojis unless greeting
    - No HTML formatting
    - Keep it brief and helpful
    """

    try:
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "open-mistral-nemo",
            "temperature": 0.7,
            "top_p": 1,
            "max_tokens": 300,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
        }

        # Send request
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers)
        )

        response.raise_for_status()
        ai_reply = response.json()["choices"][0]["message"]["content"].strip()

        return ai_reply

    except Exception as e:
        logger.error(f"❌ Conversational AI error: {e}")
        return None
