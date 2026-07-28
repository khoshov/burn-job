"""End-to-end integration test for CLI subcommands."""

import unittest
import subprocess
import sys

class TestCLIIntegration(unittest.TestCase):

    def test_cli_help(self):
        res = subprocess.run([sys.executable, "-m", "burn_job.cli", "--help"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("scan", res.stdout)
        self.assertIn("ingest", res.stdout)
        self.assertIn("run-cycle", res.stdout)

    def test_cli_version(self):
        res = subprocess.run([sys.executable, "-m", "burn_job.cli", "version"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("0.1.0", res.stdout)

    def test_cli_scan(self):
        res = subprocess.run([sys.executable, "-m", "burn_job.cli", "scan", "--help"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("--src", res.stdout)

if __name__ == "__main__":
    unittest.main()
