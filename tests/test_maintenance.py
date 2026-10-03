"""اختبارات محاكاة للطباعة والشبكة؛ لا تُلغى مهام طباعة ولا تتغير إعدادات فعلية."""

import unittest
from unittest.mock import patch

import win32print

from src.core import network_tools, printer_tools


class PrinterTests(unittest.TestCase):
    def test_status_flags_are_independent_and_combined(self):
        self.assertEqual(printer_tools._decode_printer_status(0), "Ready")
        for flag, label in [
            (win32print.PRINTER_STATUS_PAPER_OUT, "Paper Out"),
            (win32print.PRINTER_STATUS_OFFLINE, "Offline"),
            (win32print.PRINTER_STATUS_PRINTING, "Printing"),
        ]:
            self.assertEqual(printer_tools._decode_printer_status(flag), label)
        result = printer_tools._decode_printer_status(
            win32print.PRINTER_STATUS_PAPER_OUT | win32print.PRINTER_STATUS_OFFLINE
        )
        self.assertIn("Paper Out", result)
        self.assertIn("Offline", result)
        self.assertNotIn("Manual Feed", result)

    def test_printer_handle_is_closed_when_enumeration_fails(self):
        with (
            patch.object(win32print, "OpenPrinter", return_value=123),
            patch.object(win32print, "EnumJobs", side_effect=OSError("dummy failure")),
            patch.object(win32print, "ClosePrinter") as close,
        ):
            self.assertEqual(printer_tools.get_printer_jobs("DUMMY"), [])
            close.assert_called_once_with(123)

    def test_job_count_is_not_limited_to_first_100_jobs(self):
        with (
            patch.object(win32print, "OpenPrinter", return_value=123),
            patch.object(win32print, "GetPrinter", return_value={"cJobs": 250}),
            patch.object(win32print, "ClosePrinter") as close,
        ):
            self.assertEqual(printer_tools._get_job_count("DUMMY"), 250)
            close.assert_called_once_with(123)

    def test_partial_queue_failure_is_not_full_success(self):
        with (
            patch.object(win32print, "OpenPrinter", return_value=123),
            patch.object(win32print, "GetPrinter", return_value={"cJobs": 150}),
            patch.object(
                win32print, "EnumJobs", return_value=[{"JobId": 1}, {"JobId": 2}]
            ) as enumerate_jobs,
            patch.object(win32print, "SetJob", side_effect=[None, OSError("dummy locked")]),
            patch.object(win32print, "ClosePrinter") as close,
        ):
            ok, message = printer_tools.clear_print_queue("DUMMY")
            self.assertFalse(ok)
            self.assertIn("Cancelled 1", message)
            self.assertIn("Failed to cancel 1", message)
            enumerate_jobs.assert_called_once_with(123, 0, 150, 1)
            close.assert_called_once_with(123)

    def test_handle_is_closed_when_queue_query_fails(self):
        with (
            patch.object(win32print, "OpenPrinter", return_value=123),
            patch.object(win32print, "GetPrinter", side_effect=OSError("dummy query")),
            patch.object(win32print, "ClosePrinter") as close,
        ):
            self.assertFalse(printer_tools.clear_print_queue("DUMMY")[0])
            close.assert_called_once_with(123)


class NetworkDiagnosticsTests(unittest.TestCase):
    def test_config_uses_one_adapter_and_preserves_all_dns(self):
        adapters = [
            {"name": "NoGateway", "ip": "192.0.2.2", "gateway": "غير متاح"},
            {
                "name": "DUMMY",
                "ip": "198.51.100.2",
                "mac": "AA-BB-CC-DD-EE-FF",
                "gateway": "198.51.100.1",
                "dns": ["192.0.2.53", "198.51.100.53"],
            },
        ]
        with patch("src.core.network_info.get_all_adapters", return_value=adapters):
            data = network_tools.get_ip_config()
        self.assertEqual(data["adapter_name"], "DUMMY")
        self.assertEqual(data["dns_servers"], ["192.0.2.53", "198.51.100.53"])

    def test_ping_passes_separate_arguments_without_shell(self):
        with patch(
            "src.core.network_tools.run_command", return_value=(True, "localized dummy output", "")
        ) as command:
            data = network_tools.ping_host("example.test", count=2)
        self.assertTrue(data["reachable"])
        self.assertFalse(command.call_args.kwargs["shell"])
        self.assertEqual(
            command.call_args.args[0], ["ping", "-n", "2", "-w", "2000", "example.test"]
        )

    def test_invalid_host_and_count_do_not_execute_commands(self):
        for host, count in [
            ("example.test & whoami", 4),
            ("-t", 4),
            ("example.test", 0),
            ("example.test", 50),
            ("example.test", True),
        ]:
            with (
                self.subTest(host=host, count=count),
                patch("src.core.network_tools.run_command") as command,
            ):
                self.assertFalse(network_tools.ping_host(host, count)["reachable"])
                command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
