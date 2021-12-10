import unittest

class TestHelpers(unittest.TestCase):
    def test_session_id(self):
        from session import session_id

        _id = session_id()
        self.assertIsInstance(_id, str)
        self.assertNotEqual(len(_id), 0)

    def test_any_line_mathces(self):
        from wrapper import any_line_matches

        lines = ["hello", "world\n"]
        self.assertFalse(any_line_matches("hell0", lines))
        self.assertTrue(any_line_matches("world", lines))

    def test_search_first_matching_line(self):
        from wrapper import search_first_matching_line

        lines = ["The ribs and terrors in the whale",
            "Arched over me a dismal gloom"]
        select = search_first_matching_line(r"(\w*oom)$", lines, group=1)
        self.assertEqual(select, "gloom")

"""
# TODO test Wrapper with mock Session
# Session proves difficult to test
class TestSessionWrapper(unittest.TestCase):
    def test_session_wrapper(self):
        import session
        import wrapper

        class TestArgs():
            drive = "/dev/sr0"
            http_endpoint = "http://localhost:8000/update"
            http_auth = None
            # unused
            log_dir = None
            new_dir = ""
            failed_dir = ""
            done_dir = ""
            venv_dir = ""

        s = session.UnattendedSession(TestArgs())
        wrapper.parse("Reading TOC   0 %", s)
        self.assertEqual(s._stage, session.READING_TOC)

        wrapper.parse("MusicBrainz disc id XzPS7vW.HPHsYemQh0HBUGr8vuU-", s)
        self.assertEqual(s.mb_disc_id, "XzPS7vW.HPHsYemQh0HBUGr8vuU-")

        wrapper.parse("MusicBrainz lookup URL https://example.test/ ", s)
        self.assertEqual(s.mb_lookup_url, "https://example.test/")

        wrapper.parse("Matching releases:", s)
        self.assertEqual(s._stage, session.RIPPING)

        wrapper.parse("Verifying track 24 of 64", s)
        self.assertEqual(s.user_progress, "Ripped 24 of 64 tracks.")

        wrapper.parse_all(0, s)
        self.assertEqual(s._failed, "Unknown track count")

        s.post()
"""

if __name__ == '__main__':
    unittest.main()
