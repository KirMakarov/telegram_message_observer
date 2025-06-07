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

WHITELISTED_SOURCE_CHAT_IDS = []

IGNORE_CHAT_IDS = []

MESSAGE_RECIPIENT_ID = "TARGET_USER_ID_OR_USERNAME"  # Replace with the chat ID where you want to resend messages


def get_chat_id(message: Message) -> str:
    if message.chat is not None:
        return str(message.chat.id)
    return "Unknown"


def make_notification_message(message: Message, phrase: str) -> str:
    message_text = message.text or message.caption
    return f"""
search phrase << {phrase} >> found in message:
{message_text}

link: {message.link}"""


@bot.on_message()
async def handle_message(client: Client, message: Message):
    chat_id = get_chat_id(message)
    if chat_id in IGNORE_CHAT_IDS:
        logger.info(
            f"chat ID: {chat_id} | message is ignored: chat is in IGNORE_CHAT_IDS."
        )
        return

    message_text = message.text or message.caption or ""
    if not message_text:
        logger.info(f"chat ID: {chat_id} | Message has no text or caption.")
        return

    if chat_id not in WHITELISTED_SOURCE_CHAT_IDS and chat_id not in IGNORE_CHAT_IDS:
        chat_name = message.chat.title if message.chat else "Unknown chat name"
        logger.warning(
            f"chat ID: {chat_id}, name: {chat_name} is not in WHITELISTED_SOURCE_CHAT_IDS or IGNORE_CHAT_IDS."
        )
        try:
            await client.send_message(
                chat_id=MESSAGE_RECIPIENT_ID,
                text=f"chat not in any lists: {chat_id},  # {chat_name}",
            )
        except Exception as e:
            logger.error(f"Error resending message: {e}")

    try:
        utf8_safe_text = message_text.encode("utf-8", errors="replace").decode(
            "utf-8", errors="replace"
        )
        logger.info(f"chat ID: {chat_id} | text message: {utf8_safe_text[:50]}...")
    except Exception as e:
        logger.error(f"Error printing message: {e}")

    message_text_lower = message_text.lower() if message_text else ""
    matched_phrase = None
    for phrase in SEARCH_PHRASES:
        if phrase.lower() in message_text_lower:
            logger.info(f"Found search phrase '{phrase}' in message.")
            matched_phrase = phrase
            break

    if matched_phrase:
        try:
            await client.send_message(
                chat_id=MESSAGE_RECIPIENT_ID,
                text=make_notification_message(message, matched_phrase),
            )
        except Exception as e:
            logger.error(f"Error resending message: {e}")
    else:
        logger.info("No search phrases found in the message text. Message not resent.")


if __name__ == "__main__":
    logger.info("User bot started. Listening for messages...")
    bot.run()
