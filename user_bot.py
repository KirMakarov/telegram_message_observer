from decouple import config
from pyrogram import Client
from pyrogram.types import Message


api_id: int = config("API_ID")  # type: ignore
api_hash: str = config("API_HASH")  # type: ignore
name: str = config("LOGIN")  # type: ignore


bot = Client(name=name, api_id=api_id, api_hash=api_hash)

MESSAGE_RECIPIENT_ID = "TARGET_USER_ID_OR_USERNAME"  # Replace with the chat ID where you want to resend messages


@bot.on_message()
async def handle_message(client: Client, message: Message):
    message_text = message.text or message.caption
    if message_text:
        try:
            await client.send_message(
                chat_id=MESSAGE_RECIPIENT_ID,
                text=message_text,
            )
        except Exception as e:
            print(f"Error resending message: {e}")


if __name__ == "__main__":
    print("User bot started. Listening for messages...")
    bot.run()
