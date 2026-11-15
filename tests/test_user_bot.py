import tempfile
import unittest
from contextlib import chdir
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
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        path = Path(self.directory.name) / "phrases.txt"
        path.write_text("First\nsecond\n", encoding="utf-8")
        self.search_phrases = user_bot.SearchPhrases(path)
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
        phrase_path = Path(self.directory.name) / "phrases.txt"
        phrase_path.write_text("first\n", encoding="utf-8")
        phrases = user_bot.SearchPhrases(phrase_path)
        await user_bot.handle_message(
            client, message(chat_id=2, text="first"), settings, phrases
        )
        await user_bot.handle_message(
            client, message(chat_id=1, text="first"), settings, phrases
        )
        await user_bot.handle_message(
            client, message(chat_id=3, text="first"), settings, phrases
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
        phrase_path = Path(self.directory.name) / "phrases.txt"
        phrase_path.write_text("first\n", encoding="utf-8")
        phrases = user_bot.SearchPhrases(phrase_path)
        await user_bot.handle_message(
            first_client, message(text="first"), first, phrases
        )
        await user_bot.handle_message(
            second_client, message(text="first"), second, phrases
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
        phrase_path = Path(self.directory.name) / "search_phrases.txt"
        phrase_path.write_text("hello\n", encoding="utf-8")
        with chdir(self.directory.name), patch(
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
            try:
                user_bot.main()
            except ValueError as exc:
                self.fail(f"Valid configuration must allow startup: {exc}")
            bot.run.assert_called_once_with()
            client = FakeClient()
            await handlers[0](client, message(chat_id=3, text="hello"))
            phrase_path.write_text("updated\n", encoding="utf-8")
            await handlers[0](client, message(text="updated"))
            self.assertEqual(
                client.sent,
                [
                    ("user", "chat not in any lists: 3,  # Example"),
                    ("user", "Found 'hello' in message:\nhello"),
                    ("user", "Found 'updated' in message:\nupdated"),
                ],
            )
            self.assertEqual(client.read, [(3, 42), (1, 42)])

    def test_invalid_settings_prevent_startup(self):
        with patch("user_bot.Path", return_value=self.path), patch(
            "user_bot.Client"
        ) as client_type:
            with self.assertRaisesRegex(ValueError, "Cannot load chat settings"):
                user_bot.main()
            client_type.assert_not_called()


class SearchPhraseReloadTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "phrases.txt"
        self.path.write_text("alpha\n", encoding="utf-8")
        self.phrases = user_bot.SearchPhrases(self.path)
        self.settings = user_bot.ChatSettings({1}, set(), "recipient")
        self.client = FakeClient()

    async def process(self, text):
        await user_bot.handle_message(
            self.client, message(text=text), self.settings, self.phrases
        )

    async def test_comments_blanks_and_substring_matching(self):
        self.path.write_text("# comment\n  # indented\n\n  alpha  \n", encoding="utf-8")
        await self.process("# comment and # indented")
        await self.process("xxALPHAyy")
        self.assertEqual(
            self.client.sent,
            [("recipient", "Found 'alpha' in message:\nxxALPHAyy")],
        )
        self.assertEqual(self.client.read, [(1, 42)] * 2)

    async def test_empty_file_is_valid_at_startup(self):
        self.path.write_text("", encoding="utf-8")
        self.phrases = user_bot.SearchPhrases(self.path)
        await self.process("alpha")
        self.assertEqual(self.client.sent, [])
        self.assertEqual(self.client.read, [(1, 42)])

    async def test_add_edit_remove_reorder_and_disable(self):
        await self.process("ALPHA beta")
        self.path.write_text("# comment\n  beta  \nalpha\n\n", encoding="utf-8")
        await self.process("ALPHA beta")
        self.path.write_text("gamma\n", encoding="utf-8")
        await self.process("ALPHA gamma")
        self.path.write_text("  # disabled\n\n", encoding="utf-8")
        await self.process("gamma")
        self.path.write_text("delta\n", encoding="utf-8")
        await self.process("DELTA")
        self.path.write_text("", encoding="utf-8")
        await self.process("DELTA")
        self.assertEqual(
            self.client.sent,
            [
                ("recipient", "Found 'alpha' in message:\nALPHA beta"),
                ("recipient", "Found 'beta' in message:\nALPHA beta"),
                ("recipient", "Found 'gamma' in message:\nALPHA gamma"),
                ("recipient", "Found 'delta' in message:\nDELTA"),
            ],
        )
        self.assertEqual(self.client.read, [(1, 42)] * 6)

    async def test_read_error_keeps_last_successful_list_and_recovers(self):
        self.path.write_text("beta\n", encoding="utf-8")
        await self.process("beta")
        self.path.unlink()
        with self.assertLogs("user_bot", level="ERROR") as captured:
            await self.process("beta")
        self.assertIn("Cannot read search phrases", captured.output[0])
        self.assertIn("keeping previous search phrases", captured.output[0])
        self.path.write_bytes(b"\xff")
        with self.assertLogs("user_bot", level="ERROR"):
            await self.process("beta")
        self.path.write_text("gamma\n", encoding="utf-8")
        await self.process("gamma")
        self.assertEqual(
            self.client.sent,
            [
                ("recipient", "Found 'beta' in message:\nbeta"),
                ("recipient", "Found 'beta' in message:\nbeta"),
                ("recipient", "Found 'beta' in message:\nbeta"),
                ("recipient", "Found 'gamma' in message:\ngamma"),
            ],
        )
        self.assertEqual(self.client.read, [(1, 42)] * 4)

    def test_unreadable_phrase_file_prevents_startup(self):
        settings_path = Path(self.directory.name) / "chat_settings.toml"
        settings_path.write_text(
            'known_chat_ids = []\nignored_chat_ids = []\nrecipient = "user"\n',
            encoding="utf-8",
        )
        phrase_path = settings_path.with_name("search_phrases.txt")
        for case in ("missing", "invalid UTF-8", "directory"):
            with self.subTest(case=case):
                if case == "invalid UTF-8":
                    phrase_path.write_bytes(b"\xff")
                elif case == "directory":
                    phrase_path.unlink()
                    phrase_path.mkdir()
                with chdir(self.directory.name), patch(
                    "user_bot.Client"
                ) as client_type, patch(
                    "user_bot.config",
                    side_effect=lambda key, cast: {
                        "LOGIN": "test",
                        "API_ID": 1,
                        "API_HASH": "hash",
                    }[key],
                ):
                    with self.assertRaisesRegex(
                        ValueError, "Cannot read search phrases"
                    ):
                        user_bot.main()
                    client_type.assert_not_called()
