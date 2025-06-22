import logging
from typing import Union

from decouple import config
from pyrogram import Client
from pyrogram.types import Message

# Configure logger
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


API_ID: int = config("API_ID", cast=int)
API_HASH: str = config("API_HASH", cast=str)
LOGIN: str = config("LOGIN", cast=str)

SEARCH_PHRASES: list[str] = []
WHITELISTED_SOURCE_CHAT_IDS: set[int] = set()
IGNORE_CHAT_IDS: set[int] = set()
# the chat ID or username where you want to resend messages
MESSAGE_RECIPIENT_ID: Union[int, str] = "TARGET_USER_ID_OR_USERNAME"


bot = Client(name=LOGIN, api_id=API_ID, api_hash=API_HASH)


def get_chat_id(message: Message) -> Union[str, int]:
    """Extract chat ID from message, fallback to 'Unknown'."""
    return getattr(getattr(message, "chat", None), "id", "Unknown")


def make_notification_message(message: Message, phrase: str) -> str:
    """Format notification message for matched phrase."""
    message_text = message.text or message.caption or ""
    link = getattr(message, "link", None)
    link_info = f"\n\nLink: {link}" if link else ""
    return f"Found '{phrase}' in message:\n{message_text}{link_info}"


def is_message_ignored(chat_id: Union[int, str]) -> bool:
    return chat_id in IGNORE_CHAT_IDS


def is_message_whitelisted(chat_id: Union[int, str]) -> bool:
    return chat_id in WHITELISTED_SOURCE_CHAT_IDS


def get_chat_name(message: Message) -> str:
    return getattr(getattr(message, "chat", None), "title", "Unknown chat name")


@bot.on_message()  # type: ignore[misc]
async def handle_message(client: Client, message: Message):
    """
    Asynchronously handles incoming Telegram messages by performing the following actions:
    - Checks if the message's chat ID is in the ignored list and skips processing if so.
    - Ensures the message contains text or a caption; logs and returns if neither is present.
    - Logs a warning and notifies a recipient if the chat ID is not whitelisted or ignored.
    - Logs the message text in a UTF-8 safe manner.
    - Searches for predefined phrases in the message text; if found, sends a notification to a recipient.
    - Marks the message as read after processing.
    - Handles and logs exceptions that may occur during message sending, logging, or marking as read.

    Args:
        client (Client): The Telegram client instance used to interact with the API.
        message (Message): The incoming Telegram message to be processed.
    """
    chat_id = get_chat_id(message)
    if is_message_ignored(chat_id):
        logger.info(
            f"chat ID: {chat_id} | message is ignored: chat is in IGNORE_CHAT_IDS."
        )
        return

    message_text = message.text or message.caption or ""
    if not message_text:
        logger.info(f"chat ID: {chat_id} | Message has no text or caption.")
        return

    if not (is_message_whitelisted(chat_id) or is_message_ignored(chat_id)):
        chat_name = get_chat_name(message)
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

    # Mark the message as read
    try:
        await client.read_chat_history(chat_id, message.id)
    except Exception as e:
        logger.error(f"Error marking message as read: {e}")


def main() -> None:
    logger.info("User bot started. Listening for messages...")
    bot.run()


if __name__ == "__main__":
    main()
