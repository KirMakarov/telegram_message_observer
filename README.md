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

4. **Set up environment variables:**
   Create a `.env` file in the project root with the following content:

   ```env
   API_ID=your_telegram_api_id
   API_HASH=your_telegram_api_hash
   LOGIN=your_session_name
   ```

5. **Configure search and ignore lists:**

   - Edit `user_bot.py` to set `SOURCE_CHAT_IDS`, `IGNORE_CHAT_IDS`, and `SEARCH_PHRASES` as needed.

6. **Run the bot:**
   ```sh
   python3.13 user_bot.py
   ```

## Roadmap

- [x] Add white and black lists of chats
- [x] Add mark message as read
- [ ] Switch on another lib - Telethon
- [ ] Add using uv package manager
- [ ] Add silent time for sending messages
- [ ] checking the last sent messages, don't send repeating from different channel
- [ ] Add rate limit for sending messages
- [ ] Add exclude phrases for each search phrase
- [ ] Add search in history during offline time
- [ ] Add ability to add/remove search phrases via user chat
- [ ] Move storong search phrases from code
- [ ] Add ability to add/remove users who can use the bot via user chat
- [ ] Add user subscription by search phrases
- [ ] Add semantic search

## License

MIT License. See [LICENSE](LICENSE) for details.
