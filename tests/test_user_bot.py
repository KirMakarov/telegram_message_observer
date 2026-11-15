import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

with patch.dict(os.environ, {"API_ID": "12345", "API_HASH": "test", "LOGIN": "test"}):
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
        self.settings = patch.multiple(
            user_bot,
            SEARCH_PHRASES=["First", "second"],
            WHITELISTED_SOURCE_CHAT_IDS={1},
            IGNORE_CHAT_IDS={2},
            MESSAGE_RECIPIENT_ID="recipient",
        )
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.client = FakeClient()

    async def test_ignored_chat_has_no_effects_even_when_matching(self):
        await user_bot.handle_message(self.client, message(chat_id=2, text="first"))
        self.assertEqual(self.client.sent, [])
        self.assertEqual(self.client.read, [])

    async def test_known_chat_first_case_insensitive_match_and_link(self):
        await user_bot.handle_message(
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
        await user_bot.handle_message(self.client, message(caption="A SECOND caption"))
        self.assertEqual(
            self.client.sent,
            [("recipient", "Found 'second' in message:\nA SECOND caption")],
        )
        self.assertEqual(self.client.read, [(1, 42)])

    async def test_unknown_chat_reports_classification_and_match(self):
        await user_bot.handle_message(self.client, message(chat_id=3, text="first"))
        self.assertEqual(
            self.client.sent,
            [
                ("recipient", "chat not in any lists: 3,  # Example"),
                ("recipient", "Found 'First' in message:\nfirst"),
            ],
        )
        self.assertEqual(self.client.read, [(3, 42)])

    async def test_unknown_without_match_still_reports_and_marks_read(self):
        await user_bot.handle_message(self.client, message(chat_id=3, text="other"))
        self.assertEqual(
            self.client.sent, [("recipient", "chat not in any lists: 3,  # Example")]
        )
        self.assertEqual(self.client.read, [(3, 42)])

    async def test_known_without_match_marks_read(self):
        await user_bot.handle_message(self.client, message(text="other"))
        self.assertEqual(self.client.sent, [])
        self.assertEqual(self.client.read, [(1, 42)])

    async def test_textless_unknown_chat_is_skipped(self):
        await user_bot.handle_message(self.client, message(chat_id=3))
        self.assertEqual(self.client.sent, [])
        self.assertEqual(self.client.read, [])

    async def test_failed_classification_notice_does_not_stop_match_or_read(self):
        self.client = FakeClient(fail_sends={1})
        await user_bot.handle_message(self.client, message(chat_id=3, text="first"))
        self.assertEqual(
            self.client.sent, [("recipient", "Found 'First' in message:\nfirst")]
        )
        self.assertEqual(self.client.read, [(3, 42)])

    async def test_failed_match_notification_still_marks_read(self):
        self.client = FakeClient(fail_sends={1})
        await user_bot.handle_message(self.client, message(text="first"))
        self.assertEqual(self.client.sent, [])
        self.assertEqual(self.client.send_attempts, 1)
        self.assertEqual(self.client.read, [(1, 42)])
