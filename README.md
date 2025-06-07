# Telegram Message Observer

A Telegram userbot for monitoring messages in specified chats and notifying you when certain search phrases are found. The project is designed for flexible, private message observation and notification.

## Features

- Monitors messages in selected Telegram chats
- Notifies you when messages contain specified search phrases
- Ignores messages from specified chats
- Easily extendable: add search phrases, ignore lists, and more
- Logs all activity for transparency and debugging
- MIT Licensed

## Requirements

- Python 3.13+
- Telegram API credentials (API_ID, API_HASH, LOGIN)
- See `requirements.txt` for Python dependencies

## Quick Start

1. **Clone the repository:**

   ```sh
   git clone git@github.com:KirMakarov/telegram_message_observer.git
   cd telegram_message_observer
   ```

2. **Create and activate a virtual environment (recommended):**

   ```sh
   python3.13 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

4. **Run the bot:**
   ```sh
   python3.13 user_bot.py
   ```

## License

MIT License. See [LICENSE](LICENSE) for details.
