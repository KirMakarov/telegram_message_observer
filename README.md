# Telegram Message Observer

A Telegram userbot for monitoring messages in specified chats and notifying you when certain search phrases are found. The project is designed for flexible, private message observation and notification.

## Features

- Monitors messages in selected Telegram chats
- Notifies you when messages contain specified search phrases
- Ignores messages from specified chats
- Easily extendable: add search phrases, ignore lists, and more
- Logs processing activity without message text or captions
- MIT Licensed

## Requirements

- Python 3.14+
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
   python3.14 -m venv .venv
   source .venv/bin/activate
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

5. **Configure chats and search phrases:**

   - Copy `chat_settings.example.toml` to `chat_settings.toml`. Set the known and
     ignored chat IDs and the notification recipient. The local file is ignored
     by Git. Chat IDs are integers; the recipient is an integer ID or username.
   - Copy `search_phrases.example.txt` to `search_phrases.txt` and edit it.
     Each nonblank line is a phrase; lines beginning with `#` are comments.
     Matching ignores case and reports the first match in file order. Changes
     apply to the next processed message; an empty file disables phrase alerts.
     The file must exist and be readable when the bot starts.
     If the file cannot be read after startup, the bot logs the error and keeps
     the last successfully loaded phrases. The local file is ignored by Git.

6. **Run the bot:**
   ```sh
   python3.14 user_bot.py
   ```

## Development checks

Install the development dependencies and enable the commit hook:

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/pre-commit install
```

Run the same checks as CI from the project root:

```sh
.venv/bin/pre-commit run --all-files
.venv/bin/python -m unittest discover -s tests -v
```

Pre-commit creates separate Python 3.14 environments for its hooks on first
use, so commits do not require the project environment to be activated. The
hook runs Ruff lint and format checks on tracked Python source and tests, and
mypy on the Kurigram source. Ruff's formatter can apply changes with
`.venv/bin/ruff format .`. Mypy does not type-check Kurigram's imported library internals;
the separate Telethon version is excluded from these checks. Offline tests do
not require Telegram credentials or a network connection.

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
