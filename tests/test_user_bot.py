import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import user_bot


class FakeClient:
    def __init__(self, fail_sends=()):
        self.sent = []
        self.read = []
        self.fail_sends = set(fail_sends)
        self.send_attempts = 0

    async def send_message(self, chat_id, text):
        self.send_attempts += 1
        if self.send_attempts in self.fail_sends:
            raise RuntimeError("send failed")
        self.sent.append((chat_id, text))

    async def read_chat_history(self, chat_id, message_id):
        self.read.append((chat_id, message_id))


def message(chat_id=1, text=None, caption=None, link=None):
    return SimpleNamespace(
        chat=SimpleNamespace(id=chat_id, title="Example"),
        id=42,
        text=text,
        caption=caption,
        link=link,
    )


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = user_bot.ChatSettings({1}, {2}, "recipient")
        self.search_phrases = ["First", "second"]
        self.client = FakeClient()

    async def handle_message(self, client, incoming):
        await user_bot.handle_message(
            client, incoming, self.settings, self.search_phrases
        )

    async def test_ignored_chat_has_no_effects_even_when_matching(self):
        await self.handle_message(self.client, message(chat_id=2, text="first"))
        self.assertEqual(self.client.sent, [])
        self.assertEqual(self.client.read, [])

    async def test_known_chat_first_case_insensitive_match_and_link(self):
        await self.handle_message(
            self.client,
            message(text="SECOND then FIRST", link="https://example.com/42"),
        )
        self.assertEqual(
            self.client.sent,
            [
                (
                    "recipient",
                    "Found 'First' in message:\nSECOND then FIRST\n\nLink: https://example.com/42",
                )
            ],
        )
        self.assertEqual(self.client.read, [(1, 42)])

    async def test_caption_is_searched(self):
        await self.handle_message(self.client, message(caption="A SECOND caption"))
        self.assertEqual(
            self.client.sent,
            [("recipient", "Found 'second' in message:\nA SECOND caption")],
        )
        self.assertEqual(self.client.read, [(1, 42)])

    async def test_unknown_chat_reports_classification_and_match(self):
        await self.handle_message(self.client, message(chat_id=3, text="first"))
        self.assertEqual(
            self.client.sent,
            [
                ("recipient", "chat not in any lists: 3,  # Example"),
                ("recipient", "Found 'First' in message:\nfirst"),
            ],
        )
        self.assertEqual(self.client.read, [(3, 42)])

    async def test_unknown_without_match_still_reports_and_marks_read(self):
        await self.handle_message(self.client, message(chat_id=3, text="other"))
        self.assertEqual(
            self.client.sent, [("recipient", "chat not in any lists: 3,  # Example")]
        )
        self.assertEqual(self.client.read, [(3, 42)])

    async def test_known_without_match_marks_read(self):
        await self.handle_message(self.client, message(text="other"))
        self.assertEqual(self.client.sent, [])
        self.assertEqual(self.client.read, [(1, 42)])

    async def test_textless_unknown_chat_is_skipped(self):
        await self.handle_message(self.client, message(chat_id=3))
        self.assertEqual(self.client.sent, [])
        self.assertEqual(self.client.read, [])

    async def test_failed_classification_notice_does_not_stop_match_or_read(self):
        self.client = FakeClient(fail_sends={1})
        await self.handle_message(self.client, message(chat_id=3, text="first"))
        self.assertEqual(
            self.client.sent, [("recipient", "Found 'First' in message:\nfirst")]
        )
        self.assertEqual(self.client.read, [(3, 42)])

    async def test_failed_match_notification_still_marks_read(self):
        self.client = FakeClient(fail_sends={1})
        await self.handle_message(self.client, message(text="first"))
        self.assertEqual(self.client.sent, [])
        self.assertEqual(self.client.send_attempts, 1)
        self.assertEqual(self.client.read, [(1, 42)])


class ChatSettingsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "chat_settings.toml"

    def test_example_settings_are_valid(self):
        settings = user_bot.load_chat_settings(
            Path(__file__).resolve().parents[1] / "chat_settings.example.toml"
        )
        self.assertTrue(settings.known_chat_ids)
        self.assertTrue(settings.ignored_chat_ids)
        self.assertTrue(settings.recipient)

    def test_invalid_or_missing_settings_fail_clearly(self):
        cases = [
            (None, "Cannot load chat settings"),
            ("known_chat_ids = [", "Cannot load chat settings"),
            ('ignored_chat_ids = []\nrecipient = "user"', "known_chat_ids"),
            (
                'known_chat_ids = [true]\nignored_chat_ids = []\nrecipient = "user"',
                "known_chat_ids",
            ),
            (
                'known_chat_ids = []\nignored_chat_ids = ["1"]\nrecipient = "user"',
                "ignored_chat_ids",
            ),
            ("known_chat_ids = []\nignored_chat_ids = []", "recipient"),
            (
                'known_chat_ids = []\nignored_chat_ids = []\nrecipient = " "',
                "recipient",
            ),
            (
                "known_chat_ids = []\nignored_chat_ids = []\nrecipient = false",
                "recipient",
            ),
        ]
        for contents, expected in cases:
            with self.subTest(contents=contents):
                if contents is not None:
                    self.path.write_text(contents)
                with self.assertRaisesRegex(ValueError, expected):
                    user_bot.load_chat_settings(self.path)

    async def test_loaded_settings_control_handler_routing(self):
        self.path.write_text("""known_chat_ids = [1] # Known source
ignored_chat_ids = [2] # Ignored source
recipient = 12345
""")
        settings = user_bot.load_chat_settings(self.path)
        client = FakeClient()
        await user_bot.handle_message(
            client, message(chat_id=2, text="first"), settings, ["first"]
        )
        await user_bot.handle_message(
            client, message(chat_id=1, text="first"), settings, ["first"]
        )
        await user_bot.handle_message(
            client, message(chat_id=3, text="first"), settings, ["first"]
        )
        self.assertEqual(
            client.sent,
            [
                (12345, "Found 'first' in message:\nfirst"),
                (12345, "chat not in any lists: 3,  # Example"),
                (12345, "Found 'first' in message:\nfirst"),
            ],
        )
        self.assertEqual(client.read, [(1, 42), (3, 42)])

    async def test_handlers_use_their_own_settings(self):
        first = user_bot.ChatSettings({1}, set(), "first recipient")
        second = user_bot.ChatSettings(set(), {1}, "second recipient")
        first_client, second_client = FakeClient(), FakeClient()
        await user_bot.handle_message(
            first_client, message(text="first"), first, ["first"]
        )
        await user_bot.handle_message(
            second_client, message(text="first"), second, ["first"]
        )
        self.assertEqual(
            first_client.sent, [("first recipient", "Found 'first' in message:\nfirst")]
        )
        self.assertEqual(first_client.read, [(1, 42)])
        self.assertEqual(second_client.sent, [])
        self.assertEqual(second_client.read, [])

    async def test_startup_registers_handler_with_loaded_settings(self):
        self.path.write_text(
            'known_chat_ids = [1]\nignored_chat_ids = [2]\nrecipient = "user"\n'
        )
        with patch("user_bot.Path", return_value=self.path), patch(
            "user_bot.config",
            side_effect=lambda key, cast: {
                "LOGIN": "test",
                "API_ID": 1,
                "API_HASH": "hash",
            }[key],
        ), patch("user_bot.Client") as client_type:
            bot = client_type.return_value
            handlers = []
            bot.on_message.return_value = (
                lambda handler: handlers.append(handler) or handler
            )
            user_bot.main()
            bot.run.assert_called_once_with()
            client = FakeClient()
            await handlers[0](client, message(chat_id=3, text="hello"))
            self.assertEqual(
                client.sent, [("user", "chat not in any lists: 3,  # Example")]
            )
            self.assertEqual(client.read, [(3, 42)])

    def test_invalid_settings_prevent_startup(self):
        with patch("user_bot.Path", return_value=self.path), patch(
            "user_bot.Client"
        ) as client_type:
            with self.assertRaisesRegex(ValueError, "Cannot load chat settings"):
                user_bot.main()
            client_type.assert_not_called()
