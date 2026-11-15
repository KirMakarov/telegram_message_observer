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

## Cutover and rollback

Complete this procedure before resuming long-running use. The operator performs
the Telegram checks; the offline suite does not replace them.

1. Keep the previous working directory, its environment, private settings and
   session files available. Record its launch command and revision locally.
   Before replacing any existing configuration in the new checkout, keep a
   private backup outside Git. Verify the new revision's CI result and complete
   the development checks above on Python 3.14.
2. Transfer the **currently active** configuration from the previous run, rather
   than the illustrative examples. For a legacy run, move
   `WHITELISTED_SOURCE_CHAT_IDS` to `known_chat_ids`, `IGNORE_CHAT_IDS` to
   `ignored_chat_ids`, and `MESSAGE_RECIPIENT_ID` to `recipient` in
   `chat_settings.toml`. Copy `SEARCH_PHRASES` to `search_phrases.txt`, one phrase
   per line in its original order. If the previous run already uses local files,
   copy those files instead. Preserve `.env` credentials locally. Compare the
   transferred values privately with the active settings; do not paste them
   into a commit, issue, or review.
3. From the new checkout, verify the private files are ignored and validate
   configuration without connecting to Telegram:

   ```sh
   git check-ignore .env chat_settings.toml search_phrases.txt
   git ls-files -- .env chat_settings.toml search_phrases.txt
   .venv/bin/python -c 'from pathlib import Path; from user_bot import load_chat_settings, SearchPhrases; load_chat_settings(Path("chat_settings.toml")); SearchPhrases(Path("search_phrases.txt"))'
   ```

   The first command must list all three paths; the second must print nothing.
   The validation command must exit successfully. Keep a private copy of these
   validated settings before making temporary smoke-test changes.
4. Stop the previous bot before starting the new one. Keep its session files
   intact; never copy an active session database or run both copies against the
   same session. Set up the new checkout's session locally, then launch
   `.venv/bin/python user_bot.py` from its root. Confirm startup without errors
   and delivery to the intended recipient using controlled chats and phrases.
5. Send fresh controlled messages from another account. Use three distinct
   chats classified as shown, and inspect the recipient and read state after
   each message. Avoid other clients marking the test messages read.

   | Controlled input | Expected notifications | Read action |
   | --- | --- | --- |
   | Ignored chat, matching text | None | None |
   | Known chat, text matching two phrases with mixed case | One phrase alert for the first phrase in file order | Marked read |
   | Known chat, matching media caption | One phrase alert containing the caption | Marked read |
   | Known chat, nonmatching text | None | Marked read |
   | Unknown chat, matching text | Classification notice and one phrase alert | Marked read |
   | Unknown chat, nonmatching text | Classification notice only | Marked read |
   | Unknown chat, media without text or caption | None | None |

   Edit the phrase file while the bot runs and confirm the next controlled
   message uses the new phrase. Empty the file and confirm phrase alerts stop;
   unknown-chat notices and read marking must continue. Inspect activity logs
   for message bodies and captions, and confirm no diagnostic export is created
   or appended. Record only pass/fail results locally, without private content.
6. Restore the validated production files, restart to load the production chat
   settings, and confirm the intended recipient before accepting the new run.
   Keep the previous copy until the operator explicitly accepts the results.

If startup or any smoke check fails, stop the new bot, restore its private
configuration backups, and restart the previous working copy with its original
launch command, environment, settings and session. Confirm its operation before
investigating the new copy offline. Rollback does not undo notifications already
sent or messages already marked read. Do not delete prior exports or sessions.

## Roadmap

- [x] Configure known and ignored chats
- [x] Add mark message as read
- [ ] Switch on another lib - Telethon
- [ ] Add using uv package manager
- [ ] Add silent time for sending messages
- [ ] checking the last sent messages, don't send repeating from different channel
- [ ] Add rate limit for sending messages
- [ ] Add exclude phrases for each search phrase
- [ ] Add search in history during offline time
- [ ] Add ability to add/remove search phrases via user chat
- [x] Move search phrases from code to a reloadable local file
- [ ] Add ability to add/remove users who can use the bot via user chat
- [ ] Add user subscription by search phrases
- [ ] Add semantic search

## License

MIT License. See [LICENSE](LICENSE) for details.
