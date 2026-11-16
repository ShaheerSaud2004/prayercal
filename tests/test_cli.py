import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from prayercal.cli import main

NYC = ["--lat", "40.7128", "--lon", "-74.0060", "--tz", "America/New_York"]


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = main(list(args))
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def test_methods(self):
        code, out, _ = run("methods")
        self.assertEqual(code, 0)
        self.assertIn("ISNA", out)
        self.assertIn("90 min", out)

    def test_times_table(self):
        code, out, _ = run("times", *NYC, "--method", "ISNA", "--start", "2026-11-16", "--days", "2", "--24h")
        self.assertEqual(code, 0)
        self.assertIn("2026-11-16", out)
        self.assertIn("05:25", out)
        self.assertIn("Jumada al-Thani", out)

    def test_ics_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "p.ics")
            code, _, err = run("ics", *NYC, "--start", "2026-11-16", "--days", "3", "-o", path)
            self.assertEqual(code, 0)
            self.assertIn("wrote 3 days", err)
            with open(path, encoding="utf-8", newline="") as fh:
                self.assertEqual(fh.read().count("BEGIN:VEVENT"), 15)

    def test_custom_prayers(self):
        code, out, _ = run("ics", *NYC, "--start", "2026-11-16", "--days", "1", "--prayers", "fajr,sunrise")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("BEGIN:VEVENT"), 2)
        self.assertIn("SUMMARY:Sunrise", out)

    def test_bad_timezone(self):
        code, _, err = run("times", "--lat", "0", "--lon", "0", "--tz", "Mars/Olympus")
        self.assertEqual(code, 2)
        self.assertIn("unknown timezone", err)

    def test_bad_method(self):
        code, _, err = run("times", *NYC, "--method", "nope")
        self.assertEqual(code, 2)
        self.assertIn("unknown method", err)

    def test_bad_adjust(self):
        code, _, err = run("times", *NYC, "--adjust", "tahajjud=2")
        self.assertEqual(code, 2)

    def test_bad_latitude(self):
        code, _, err = run("times", "--lat", "91", "--lon", "0", "--tz", "UTC")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
