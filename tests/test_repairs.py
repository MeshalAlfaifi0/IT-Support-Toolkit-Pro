"""اختبارات الإصلاحات؛ تُحاكى تغييرات النظام ويقتصر الحذف على ملفات تجريبية."""

import io
import json
import logging
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("IT_TOOLKIT_DATA_DIR", str(Path(__file__).parent / "artifacts" / "data"))

from src.core import cybersecurity as security
from src.core import domain_info as domain
from src.core import ip_manager as ip
from src.core.health_score import calculate_health_score
from src.core.windows_repair import cleanup_directory
from src.utils import app_paths as paths
from src.utils import command_runner as runner


class CredentialTests(unittest.TestCase):
    def test_join_success_failure_timeout_and_exception_are_private(self):
        password = "Dummy'&$🔑Pässword\n42"
        username = "DUMMY\\secret-user"
        for outcome in ("success", "failure", "timeout", "exception"):
            with self.subTest(outcome=outcome):
                stream = io.StringIO()
                handler = logging.StreamHandler(stream)
                logging.getLogger().addHandler(handler)
                captured = {}

                def child(cmd, **kwargs):
                    captured.update(command=cmd, **kwargs)
                    self.assertNotIn(password, str(cmd))
                    self.assertNotIn(username, str(cmd))
                    self.assertEqual(json.loads(kwargs["input"])["password"], password)
                    self.assertFalse(kwargs["shell"])
                    if outcome == "timeout":
                        raise subprocess.TimeoutExpired(
                            cmd + [password, username], 120, output=password
                        )
                    if outcome == "exception":
                        raise OSError(password + username + kwargs["input"])
                    return subprocess.CompletedProcess(
                        cmd,
                        0 if outcome == "success" else 1,
                        password + username + kwargs["input"],
                        password,
                    )

                try:
                    with (
                        patch.object(domain, "is_admin", return_value=True),
                        patch.object(runner.subprocess, "run", side_effect=child),
                    ):
                        ok, message = domain.join_domain(
                            "dummy.local", username, password, 'OU="Dummy",DC=test'
                        )
                    self.assertEqual(ok, outcome == "success")
                    for secret in (password, username, json.dumps(password)[1:-1]):
                        self.assertNotIn(secret, message + stream.getvalue())
                    if outcome == "timeout":
                        self.assertIn("مهلة", message)
                finally:
                    logging.getLogger().removeHandler(handler)

    def test_sensitive_powershell_stdin_real_success_failure_timeout(self):
        secret = "DUMMY-SENSITIVE-42"
        script = "$payload=[Console]::In.ReadToEnd(); [Console]::Write($payload); "
        for tail, timeout, expected in [
            ("exit 0", 15, True),
            ("exit 1", 15, False),
            ("Start-Sleep 10", 0.3, False),
        ]:
            with self.subTest(tail=tail):
                ok, out, err = runner.run_command(
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script + tail],
                    shell=False,
                    input_text=secret,
                    sensitive=True,
                    timeout=timeout,
                )
                self.assertEqual(ok, expected)
                self.assertNotIn(secret, out + err)

    def test_validation_executes_nothing(self):
        with (
            patch.object(domain, "is_admin", return_value=True),
            patch.object(domain, "run_command") as command,
        ):
            for args in [("", "user", "pw"), ("test.local", "", "pw"), ("test.local", "user", "")]:
                self.assertFalse(domain.join_domain(*args)[0])
            command.assert_not_called()


class SecurityTests(unittest.TestCase):
    def test_bitlocker_distinguishes_encryption_and_protection(self):
        for volume, protection, percent, expected in [
            (1, 1, 100, True),
            (1, 0, 100, False),
            (0, 0, 0, False),
            (2, 1, 60, False),
            (1, 2, 100, None),
            (99, 1, 100, None),
        ]:
            with (
                self.subTest(volume=volume, protection=protection),
                patch.object(
                    security,
                    "run_powershell_json",
                    return_value=dict(
                        VolumeStatus=volume,
                        ProtectionStatus=protection,
                        EncryptionPercentage=percent,
                    ),
                ),
            ):
                result = security.get_bitlocker_status()
                self.assertIs(result["enabled"], expected)
                self.assertEqual(result["encryption_percentage"], percent)
        with patch.object(security, "run_powershell_json", side_effect=RuntimeError("Unavailable")):
            self.assertIsNone(security.get_bitlocker_status()["enabled"])
        with patch.object(
            security,
            "run_powershell_json",
            return_value={
                "VolumeStatus": "Conversion Status: Fully Decrypted",
                "ProtectionStatus": "Protection Off",
            },
        ):
            self.assertIsNone(security.get_bitlocker_status()["enabled"])

    def test_firewall_profiles_and_unknown(self):
        for values, expected in [
            ((1, 1, 1), True),
            ((1, 1, 0), False),
            ((0, 1, 1), False),
            ((1, 2, 1), None),
        ]:
            data = [
                dict(Name=name, Enabled=value)
                for name, value in zip(("Domain", "Private", "Public"), values)
            ]
            with (
                self.subTest(values=values),
                patch.object(security, "run_powershell_json", return_value=data),
            ):
                result = security.get_windows_firewall_status()
                self.assertIs(security.firewall_assessment(result), expected)
        with patch.object(
            security, "run_powershell_json", side_effect=RuntimeError("Access denied")
        ):
            self.assertIsNone(security.firewall_assessment(security.get_windows_firewall_status()))
        with patch.object(
            security, "run_powershell_json", return_value=[{"Name": "Domain", "Enabled": 1}]
        ):
            self.assertIsNone(security.firewall_assessment(security.get_windows_firewall_status()))

    def test_update_presence_is_not_recency(self):
        cases = [
            ({"Count": 3, "Date": "2026-09-20"}, True, True),
            ({"Count": 3, "Date": "2020-01-01"}, True, False),
            ({"Count": 0, "Date": None}, False, False),
            ({"Count": 1, "Date": None}, True, None),
            ({"Count": 1, "Date": "2027-01-01"}, True, None),
        ]
        for data, present, recent in cases:
            with (
                self.subTest(data=data),
                patch.object(security, "run_powershell_json", return_value=data),
            ):
                result = security.get_windows_update_status(today=date(2026, 9, 30))
                self.assertIs(result["has_updates"], present)
                self.assertIs(result["recent"], recent)
        with patch.object(security, "run_powershell_json", side_effect=RuntimeError()):
            self.assertIsNone(security.get_windows_update_status()["ok"])

    def test_missing_registry_is_unknown_instead_of_pass(self):
        with patch.object(security.winreg, "OpenKey", side_effect=FileNotFoundError()):
            self.assertIsNone(security.get_rdp_status()["enabled"])
            self.assertIsNone(security.get_tls_status()["ok"])
            self.assertIsNone(security.get_uac_status()["enabled"])

    def test_structured_parser_rejects_empty_and_malformed_results(self):
        for value in ("", "garbage", "<xml>bad</xml>"):
            with patch.object(runner, "run_command", return_value=(True, value, "")):
                with self.assertRaises(RuntimeError):
                    runner.run_powershell_json("query")

    def test_unavailable_health_components_receive_no_credit(self):
        result = calculate_health_score(
            0,
            10,
            16,
            80,
            False,
            "Unknown",
            False,
            False,
            True,
            unavailable={"disk", "antivirus", "windows_update", "drivers"},
        )
        self.assertEqual(result["coverage"], 45)
        self.assertEqual(result["label"], "Incomplete")
        self.assertEqual(result["score"], 45)
        for component in result["unavailable"]:
            self.assertEqual(result["breakdown"][component], 0)


class NetworkTests(unittest.TestCase):
    def test_ipv4_and_subnet_validation(self):
        good = [
            ("192.168.1.20", "255.255.255.0", "192.168.1.1", "8.8.8.8", "1.1.1.1"),
            ("10.0.0.5", "255.255.255.0", "", "", ""),
            ("10.0.0.0", "255.255.255.254", "10.0.0.1", "", ""),
        ]
        bad = [
            ("192.168.1.20", "255.0.255.0", "192.168.1.1", "", ""),
            ("192.168.1.20", "255.255.255.0", "192.168.2.1", "", ""),
            ("192.168.1.0", "255.255.255.0", "192.168.1.1", "", ""),
            ("192.168.1.255", "255.255.255.0", "192.168.1.1", "", ""),
            ("192.168.1.20", "255.255.255.0", "192.168.1.20", "", ""),
            ("224.1.2.3", "255.255.255.0", "", "", ""),
            ("127.0.0.1", "255.255.255.0", "", "", ""),
            ("10.0.0.1", "0.0.0.255", "", "", ""),
            ("10.0.0.1", "0.0.0.0", "", "", ""),
            ("10.0.0.1", "255.255.255.0", "", "", "1.1.1.1"),
            ("10.0.0.1", "255.255.255.0", "", "8.8.8.8", "8.8.8.8"),
            ("10.0.0.1", "255.255.255.0", "", "0.0.0.0", ""),
            ("::1", "255.255.255.0", "", "", ""),
            ("010.0.0.1", "255.255.255.0", "", "", ""),
        ]
        for args in good:
            with self.subTest(args=args):
                self.assertTrue(ip.validate_static_params(*args)[0])
        for args in bad:
            with self.subTest(args=args):
                self.assertFalse(ip.validate_static_params(*args)[0])

    def test_invalid_settings_run_no_system_command(self):
        with (
            patch.object(ip, "is_admin", return_value=True),
            patch.object(ip, "run_command") as command,
        ):
            self.assertFalse(ip.set_static_ip("Dummy", "10.0.0.1", "255.0.255.0", "", "", "")[0])
            command.assert_not_called()

    def test_arguments_do_not_invoke_shell_and_dns_failure_is_reported(self):
        with (
            patch.object(ip, "is_admin", return_value=True),
            patch.object(
                ip,
                "run_command",
                side_effect=[(True, "", ""), (True, "", ""), (False, "", "DNS error")],
            ) as command,
        ):
            result = ip.set_static_ip(
                "Dummy & unsafe", "10.0.0.5", "255.255.255.0", "10.0.0.1", "8.8.8.8", "1.1.1.1"
            )
            self.assertFalse(result[0])
            for call in command.call_args_list:
                self.assertIsInstance(call.args[0], list)
                self.assertFalse(call.kwargs["shell"])
                self.assertIn("name=Dummy & unsafe", call.args[0])

    def test_primary_dns_failure_does_not_add_secondary(self):
        with (
            patch.object(ip, "is_admin", return_value=True),
            patch.object(
                ip, "run_command", side_effect=[(True, "", ""), (False, "", "DNS failed")]
            ) as command,
        ):
            result = ip.set_static_ip(
                "Dummy", "10.0.0.5", "255.255.255.0", "10.0.0.1", "8.8.8.8", "1.1.1.1"
            )
            self.assertFalse(result[0])
            self.assertEqual(command.call_count, 2)

    def test_ip_failure_does_not_modify_dns(self):
        with (
            patch.object(ip, "is_admin", return_value=True),
            patch.object(ip, "run_command", return_value=(False, "", "Failure")) as command,
        ):
            self.assertFalse(
                ip.set_static_ip("Dummy", "10.0.0.5", "255.255.255.0", "10.0.0.1", "8.8.8.8")[0]
            )
            self.assertEqual(command.call_count, 1)


class CleanupTests(unittest.TestCase):
    def test_partial_cleanup_counts_only_successful_files_and_preserves_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "bundle"
            data = root / "appdata"
            locked = root / "locked"
            for directory in (bundle, data, root / "normal"):
                directory.mkdir()
            (bundle / "dll").write_bytes(b"A" * 7)
            (data / "db").write_bytes(b"B" * 8)
            (root / "normal" / "a").write_bytes(b"C" * 11)
            (root / "b").write_bytes(b"D" * 13)
            locked.write_bytes(b"E" * 17)
            real_unlink = Path.unlink

            def unlink(path, *args, **kwargs):
                if path == locked:
                    raise PermissionError("Fixture in use")
                return real_unlink(path, *args, **kwargs)

            # cwd is protected by default; tests isolate it to a separate sibling.
            with (
                patch.object(Path, "cwd", return_value=root.parent / "separate-cwd"),
                patch.object(Path, "unlink", unlink),
                patch.object(sys, "_MEIPASS", str(bundle), create=True),
            ):
                stats = cleanup_directory(root, [data])
            self.assertEqual(stats["deleted"], 2)
            self.assertEqual(stats["bytes"], 24)
            self.assertEqual(stats["folders"], 1)
            self.assertEqual(stats["errors"], 1)
            self.assertTrue((bundle / "dll").exists())
            self.assertTrue((data / "db").exists())
            self.assertTrue(locked.exists())

    @unittest.skipUnless(sys.platform == "win32", "Windows sharing lock test")
    def test_real_locked_fixture_is_preserved(self):
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            locked = root / "locked.fixture"
            ordinary = root / "ordinary.fixture"
            locked.write_bytes(b"LOCKED")
            ordinary.write_bytes(b"DUMMY12")
            handle = kernel.CreateFileW(str(locked), 0x80000000, 0, None, 3, 0x80, None)
            self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
            try:
                with patch.object(Path, "cwd", return_value=root / "unrelated"):
                    stats = cleanup_directory(root)
                self.assertEqual(stats["deleted"], 1)
                self.assertEqual(stats["bytes"], 7)
                self.assertEqual(stats["errors"], 1)
                self.assertTrue(locked.exists())
            finally:
                kernel.CloseHandle(handle)

    def test_runtime_as_target_is_never_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "dll").write_text("fixture")
            with patch.object(sys, "_MEIPASS", str(folder), create=True):
                stats = cleanup_directory(folder)
            self.assertEqual(stats["deleted"], 0)
            self.assertTrue((folder / "dll").exists())


class PersistenceTests(unittest.TestCase):
    def test_settings_write_failure_is_not_reported_as_success(self):
        from src.database.init_db import save_setting

        with patch("src.database.connection.execute_write", return_value=-1):
            with self.assertRaises(RuntimeError):
                save_setting("dummy", "value")

    def test_health_scan_and_recommendations_are_atomic(self):
        from src.core.health_checker import _save_scan
        from src.database import connection
        from src.database.init_db import initialize_database

        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(connection, "DB_PATH", str(Path(temp) / "dummy.db")),
            patch.object(connection, "prepare_data"),
        ):
            initialize_database()
            data = {
                "device_name": "QA-DUMMY",
                "username": "tester",
                "health_score": {"score": 42},
                "recommendations": [{"category": "Dummy", "recommendation": "Dummy note"}],
            }
            with self.assertRaises(KeyError):
                _save_scan(data)
            conn = connection.get_connection()
            try:
                for table in ("devices", "health_checks", "recommendations"):
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0], 0)
            finally:
                conn.close()
            data["recommendations"][0]["priority"] = "Medium"
            first = _save_scan(data)
            second = _save_scan(data)
            self.assertGreater(second, first)
            conn = connection.get_connection()
            try:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0], 1)
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) FROM health_checks").fetchone()[0], 2
                )
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0], 2
                )
                self.assertEqual(
                    json.loads(
                        conn.execute(
                            "SELECT scan_data FROM health_checks WHERE id=?", (second,)
                        ).fetchone()[0]
                    ),
                    data,
                )
                self.assertEqual(conn.execute("PRAGMA quick_check").fetchone()[0], "ok")
            finally:
                conn.close()

    def test_wal_migration_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            old = base / "old"
            new = base / "new"
            (old / "database").mkdir(parents=True)
            source = sqlite3.connect(old / "database/app.db")
            source.execute("PRAGMA journal_mode=WAL")
            source.execute("CREATE TABLE settings (value TEXT)")
            source.execute("INSERT INTO settings VALUES ('legacy-WAL')")
            source.commit()
            with (
                patch.multiple(
                    paths,
                    DATA_DIR=new,
                    DATABASE_DIR=new / "database",
                    LOG_DIR=new / "logs",
                    EXPORTS_DIR=new / "exports",
                    DB_FILE=new / "database/app.db",
                    _prepared=False,
                ),
                patch.object(paths, "legacy_roots", return_value=[old]),
            ):
                paths.prepare_data()
                with closing(sqlite3.connect(paths.DB_FILE)) as migrated:
                    self.assertEqual(
                        migrated.execute("SELECT value FROM settings").fetchone()[0], "legacy-WAL"
                    )
                    migrated.execute("UPDATE settings SET value='saved-setting'")
                    migrated.commit()
                paths._prepared = False
                paths.prepare_data()
                with closing(sqlite3.connect(paths.DB_FILE)) as migrated:
                    self.assertEqual(
                        migrated.execute("SELECT value FROM settings").fetchone()[0],
                        "saved-setting",
                    )
                self.assertEqual(
                    source.execute("SELECT value FROM settings").fetchone()[0], "legacy-WAL"
                )
            source.close()

    def test_setting_survives_two_independent_processes(self):
        with tempfile.TemporaryDirectory() as temp:
            env = os.environ.copy()
            env["IT_TOOLKIT_DATA_DIR"] = temp
            env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
            scripts = [
                "from src.utils import app_paths; app_paths.legacy_roots=lambda: []; from src.database.init_db import initialize_database,save_setting; initialize_database(); save_setting('repair-persistence','dummy-42')",
                "from src.utils import app_paths; app_paths.legacy_roots=lambda: []; from src.database.init_db import initialize_database,get_setting; initialize_database(); assert get_setting('repair-persistence')=='dummy-42' ",
            ]
            for script in scripts:
                result = subprocess.run(
                    [sys.executable, "-c", script], env=env, capture_output=True, text=True
                )
                self.assertEqual(result.returncode, 0, result.stderr)


class TimeoutTests(unittest.TestCase):
    def test_frozen_restart_reextracts_resources_without_duplicate_exe_argument(self):
        from src.utils.restart import restart_request

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", "dummy.exe"),
            patch.object(sys, "argv", ["dummy.exe", "--dummy"]),
        ):
            command, environment = restart_request()
            self.assertEqual(command, ["dummy.exe", "--dummy"])
            self.assertEqual(environment["PYINSTALLER_RESET_ENVIRONMENT"], "1")

    def test_silent_streaming_process_has_a_real_deadline(self):
        lines = []
        started = time.monotonic()
        ok = runner.run_command_streaming(
            [sys.executable, "-c", "import time; time.sleep(10)"], lines.append, timeout=0.3
        )
        self.assertFalse(ok)
        self.assertLess(time.monotonic() - started, 5)
        self.assertTrue(any("timed out" in line for line in lines))

    def test_streamed_success_and_failure(self):
        for code in (0, 1):
            lines = []
            self.assertEqual(
                runner.run_command_streaming(
                    [sys.executable, "-c", f"print('dummy-output'); raise SystemExit({code})"],
                    lines.append,
                    timeout=10,
                ),
                code == 0,
            )
            self.assertIn("dummy-output", lines)


if __name__ == "__main__":
    unittest.main(verbosity=2)
