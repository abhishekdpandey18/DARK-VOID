"""End-to-end CLI command tests using Click's CliRunner."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from click.testing import CliRunner

from darkvoid.cli import cli
from tests.helpers import generate_sample_video


class TestDarkVoidCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runner = CliRunner()
        self.env = {
            "DARKVOID_HOME": str(self.root / "config"),
            "DARKVOID_WORKSPACE": str(self.root / "workspace"),
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_version_and_help(self) -> None:
        res_ver = self.runner.invoke(cli, ["--version"], env=self.env)
        self.assertEqual(res_ver.exit_code, 0)
        self.assertIn("1.0.0", res_ver.output)

        res_help = self.runner.invoke(cli, ["--help"], env=self.env)
        self.assertEqual(res_help.exit_code, 0)
        for cmd_name in ["convert", "info", "queue", "watch", "history", "config", "doctor", "logs"]:
            self.assertIn(cmd_name, res_help.output)

    def test_doctor_and_config_commands(self) -> None:
        res_doc = self.runner.invoke(cli, ["doctor", "--json"], env=self.env)
        self.assertEqual(res_doc.exit_code, 0)
        payload = json.loads(res_doc.output)
        self.assertTrue(payload["healthy"])

        res_set = self.runner.invoke(cli, ["config", "set", "existing_output_policy", "rename"], env=self.env)
        self.assertEqual(res_set.exit_code, 0)

        res_show = self.runner.invoke(cli, ["config", "show", "--json"], env=self.env)
        self.assertEqual(res_show.exit_code, 0)
        cfg_data = json.loads(res_show.output)
        self.assertEqual(cfg_data["existing_output_policy"], "rename")

        # Attempting to alter locked codec settings must fail safely
        res_locked = self.runner.invoke(cli, ["config", "set", "video_codec", "libx264"], env=self.env)
        self.assertNotEqual(res_locked.exit_code, 0)

    def test_cli_info_convert_history_queue_and_logs(self) -> None:
        vid = generate_sample_video(self.root / "cli_sample.mp4", duration=0.3)
        out_dir = self.root / "out"

        # 1. info --json
        res_info = self.runner.invoke(cli, ["info", str(vid), "--json"], env=self.env)
        self.assertEqual(res_info.exit_code, 0)
        info_data = json.loads(res_info.output)
        self.assertEqual(info_data["filename"], "cli_sample.mp4")

        # 2. convert --dry-run
        res_dry = self.runner.invoke(
            cli,
            ["--no-banner", "convert", str(vid), "--output", str(out_dir), "--dry-run", "--json"],
            env=self.env,
        )
        self.assertEqual(res_dry.exit_code, 0)
        dry_data = json.loads(res_dry.output)
        self.assertEqual(dry_data["outcomes"][0]["status"], "DryRun")
        self.assertFalse((out_dir / "cli_sample_Resolve.mov").exists())

        # 3. convert (actual conversion)
        res_conv = self.runner.invoke(
            cli,
            ["--no-banner", "convert", str(vid), "--output", str(out_dir), "--json"],
            env=self.env,
        )
        self.assertEqual(res_conv.exit_code, 0)
        conv_data = json.loads(res_conv.output)
        self.assertEqual(conv_data["outcomes"][0]["status"], "Completed")
        self.assertTrue((out_dir / "cli_sample_Resolve.mov").exists())

        # 4. history --success --json
        res_hist = self.runner.invoke(cli, ["history", "--success", "--json"], env=self.env)
        self.assertEqual(res_hist.exit_code, 0)
        hist_data = json.loads(res_hist.output)
        self.assertEqual(len(hist_data), 1)
        self.assertEqual(hist_data[0]["output_filename"], "cli_sample_Resolve.mov")

        # 5. queue --json
        res_q = self.runner.invoke(cli, ["queue", "--json"], env=self.env)
        self.assertEqual(res_q.exit_code, 0)

        # 6. logs
        res_logs = self.runner.invoke(cli, ["logs", "--lines", "10"], env=self.env)
        self.assertEqual(res_logs.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
