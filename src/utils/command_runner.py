"""تنفيذ أوامر النظام بمهلات محددة وإخفاء مخرجات العمليات التي تحمل بيانات اعتماد."""

import locale
import queue
import subprocess
import threading
import time

from src.utils.logger import setup_logger

log = setup_logger(__name__)
_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_command(
    command, timeout=60, shell=True, *, input_text=None, sensitive=False, encoding=None
):
    label = "[sensitive operation]" if sensitive else str(command)
    try:
        log.debug("Running command: %s", label)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            input=input_text,
            timeout=timeout,
            shell=shell,
            creationflags=_FLAGS,
            encoding=encoding or locale.getpreferredencoding(False),
            errors="replace",
        )
        if result.returncode:
            log.warning("Command exited %s: %s", result.returncode, label)
        # قد يعيد الأمر بيانات الاعتماد صراحة أو بعد ترميزها؛ نتجاهل المخرجات الحساسة بالكامل.
        # تتولى الجهة المستدعية عرض رسالة نجاح أو فشل آمنة.
        return (
            result.returncode == 0,
            "" if sensitive else result.stdout,
            "" if sensitive else result.stderr,
        )
    except subprocess.TimeoutExpired:
        log.error("Command timed out after %ss: %s", timeout, label)
        return False, "", f"Command timed out after {timeout} seconds."
    except Exception as exc:
        detail = type(exc).__name__ if sensitive else str(exc)
        log.error("Command failed: %s (%s)", label, detail)
        return False, "", f"Command failed: {detail}"


def run_powershell_json(script, timeout=20):
    import json

    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "$ErrorActionPreference='Stop'; [Console]::OutputEncoding="
        "[Text.UTF8Encoding]::new(); " + script,
    ]
    ok, out, err = run_command(command, timeout=timeout, shell=False, encoding="utf-8")
    if not ok:
        raise RuntimeError(err.strip() or "PowerShell query failed")
    try:
        return json.loads(out.lstrip("\ufeff").strip())
    except (ValueError, TypeError) as exc:
        raise RuntimeError("PowerShell returned invalid structured data") from exc


def run_command_streaming(command, callback, timeout=300):
    """المهلة تغطي قراءة stdout أيضًا؛ صمت العملية لا يمنع انتهاء المهلة."""
    proc = None
    lines = queue.Queue()
    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            shell=isinstance(command, str),
            creationflags=_FLAGS,
        )

        def read_lines():
            try:
                for line in proc.stdout:
                    lines.put(line.rstrip())
            finally:
                lines.put(None)

        reader = threading.Thread(target=read_lines, daemon=True)
        reader.start()
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                line = lines.get(timeout=min(remaining, 0.1))
            except queue.Empty:
                continue
            if line is None:
                break
            callback(line)
        proc.wait(timeout=max(0.001, deadline - time.monotonic()))
        return proc.returncode == 0
    except Exception as exc:
        if proc and proc.poll() is None:
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        capture_output=True,
                        creationflags=_FLAGS,
                        timeout=10,
                    )
                except (OSError, subprocess.SubprocessError):
                    pass
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=10)
        message = (
            f"Command timed out after {timeout} seconds."
            if isinstance(exc, subprocess.TimeoutExpired)
            else str(exc)
        )
        log.error("Streaming command failed: %s", message)
        callback("ERROR: " + message)
        return False
    finally:
        if proc and proc.stdout:
            proc.stdout.close()
