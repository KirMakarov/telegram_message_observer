import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from decouple import config
from pyrogram import Client
from pyrogram.types import Message


@dataclass(frozen=True)
class ChatSettings:
    known_chat_ids: set[int]
    ignored_chat_ids: set[int]
    recipient: Union[int, str]


def get_chat_id(message: Message) -> Union[str, int]:
    """Extract chat ID from message, fallback to 'Unknown'."""
    return getattr(getattr(message, "chat", None), "id", "Unknown")


def make_notification_message(message: Message, phrase: str) -> str:
    """Format notification message for matched phrase."""
    message_text = message.text or message.caption or ""
    link = getattr(message, "link", None)
    link_info = f"\n\nLink: {link}" if link else ""
    return f"Found '{phrase}' in message:\n{message_text}{link_info}"


def get_chat_name(message: Message) -> str:
    return getattr(getattr(message, "chat", None), "title", "Unknown chat name")


async def handle_message(
    client: Client, message: Message, settings: ChatSettings, search_phrases: list[str]
):
    """
    Asynchronously handles incoming Telegram messages by performing the following actions:
    - Checks if the message's chat ID is in the ignored list and skips processing if so.
    - Ensures the message contains text or a caption; logs and returns if neither is present.
    - Logs a warning and notifies a recipient if the chat ID is not known or ignored.
    - Logs the message text in a UTF-8 safe manner.
    - Searches for predefined phrases in the message text; if found, sends a notification to a recipient.
    - Marks the message as read after processing.
    - Handles and logs exceptions that may occur during message sending, logging, or marking as read.

    Args:
        client (Client): The Telegram client instance used to interact with the API.
        message (Message): The incoming Telegram message to be processed.
    """
    logger = logging.getLogger(__name__)
    chat_id = get_chat_id(message)
    if chat_id in settings.ignored_chat_ids:
        logger.info(
            f"chat ID: {chat_id} | message is ignored: chat is in IGNORED_CHAT_IDS."
        )
        return

    message_text = message.text or message.caption or ""
    if not message_text:
        logger.info(f"chat ID: {chat_id} | Message has no text or caption.")
        return

    if chat_id not in settings.known_chat_ids:
        chat_name = get_chat_name(message)
        logger.warning(
            f"chat ID: {chat_id}, name: {chat_name} is not in KNOWN_CHAT_IDS or IGNORED_CHAT_IDS."
        )
        try:
            await client.send_message(
                chat_id=settings.recipient,
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
    for phrase in search_phrases:
        if phrase.lower() in message_text_lower:
            logger.info(f"Found search phrase '{phrase}' in message.")
            matched_phrase = phrase
            break

    if matched_phrase:
        try:
            await client.send_message(
                chat_id=settings.recipient,
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


def load_chat_settings(path: Path) -> ChatSettings:
    """Read and validate the local chat settings before starting the bot."""
    try:
        with path.open("rb") as settings_file:
            settings = tomllib.load(settings_file)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"Cannot load chat settings from {path}: {exc}") from exc

    for name in ("known_chat_ids", "ignored_chat_ids"):
        value = settings.get(name)
        if not isinstance(value, list) or any(type(item) is not int for item in value):
            raise ValueError(f"{path}: {name} must be a list of integer chat IDs")

    recipient = settings.get("recipient")
    if not (type(recipient) is int or isinstance(recipient, str) and recipient.strip()):
        raise ValueError(
            f"{path}: recipient must be an integer ID or nonempty username"
        )

    return ChatSettings(
        set(settings["known_chat_ids"]), set(settings["ignored_chat_ids"]), recipient
    )


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
    )
    settings = load_chat_settings(Path("chat_settings.toml"))
    search_phrases: list[str] = []
    bot = Client(
        name=config("LOGIN", cast=str),
        api_id=config("API_ID", cast=int),
        api_hash=config("API_HASH", cast=str),
    )

    @bot.on_message()
    async def on_message(client: Client, message: Message) -> None:
        await handle_message(client, message, settings, search_phrases)

    logging.getLogger(__name__).info("User bot started. Listening for messages...")
    bot.run()


if __name__ == "__main__":
    main()
