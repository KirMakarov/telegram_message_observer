import logging

from decouple import config
from pyrogram import Client
from pyrogram.types import Message

# Configure logger
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


api_id: int = config("API_ID")  # type: ignore
api_hash: str = config("API_HASH")  # type: ignore
name: str = config("LOGIN")  # type: ignore


bot = Client(name=name, api_id=api_id, api_hash=api_hash)

SEARCH_PHRASES = [
    "example phrase 1",
]

MESSAGE_RECIPIENT_ID = "TARGET_USER_ID_OR_USERNAME"  # Replace with the chat ID where you want to resend messages


def get_chat_id(message: Message) -> str:
    if message.chat is not None:
        return str(message.chat.id)
    return "Unknown"


@bot.on_message()
async def handle_message(client: Client, message: Message):
    message_text = message.text or message.caption
    if not message_text:
        chat_id = get_chat_id(message)
        logger.info(f"chat ID: {chat_id} | Message has no text or caption.")
        return

    message_text_lower = message_text.lower() if message_text else ""
    phrase_found = False
    for phrase in SEARCH_PHRASES:
        if phrase.lower() in message_text_lower:
            logger.info(f"Found search phrase '{phrase}' in message.")
            phrase_found = True
            break

    if phrase_found:
        try:
            await client.send_message(
                chat_id=MESSAGE_RECIPIENT_ID,
                text=message_text,
            )
        except Exception as e:
            logger.error(f"Error resending message: {e}")
    else:
        logger.info("No search phrases found in the message text. Message not resent.")


if __name__ == "__main__":
    logger.info("User bot started. Listening for messages...")
    bot.run()
