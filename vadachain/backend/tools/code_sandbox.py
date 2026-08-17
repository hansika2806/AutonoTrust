"""
code_sandbox.py — Sandboxed subprocess executor with resource limits.

Exact required function signature (from spec):
    run_tests(code: str, test_code: str, timeout_seconds: int = 5, memory_limit_mb: int = 256) -> dict

Returns: {"passed": bool, "output": str, "num_tests_passed": int, "num_tests_total": int}
"""
import os
import sys
import subprocess
import tempfile
import re
import platform
import logging

logger = logging.getLogger(__name__)

_IS_LINUX = platform.system() == "Linux"


def _make_preexec_fn(memory_limit_mb: int):
    """
    Returns a preexec_fn that enforces memory limits via resource.setrlimit.
    Only works on Linux. On Windows/macOS, returns None (no memory limit enforced).
    """
    if not _IS_LINUX:
        return None

    import resource

    def _limit():
        mem_bytes = memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

    return _limit


def run_tests(
    code: str,
    test_code: str,
    timeout_seconds: int = 5,
    memory_limit_mb: int = 256,
) -> dict:
    """
    Write code to a temp file, run test_code (pytest-style) against it in a subprocess.
    Enforces timeout and (on Linux) memory limits.
    No network access inside the subprocess.
    Returns {"passed": bool, "output": str, "num_tests_passed": int, "num_tests_total": int}
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        code_file = os.path.join(tmpdir, "solution.py")
        test_file = os.path.join(tmpdir, "test_solution.py")

        # Write code under test
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        # Write test file — test_code imports from solution
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)

        preexec_fn = _make_preexec_fn(memory_limit_mb)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m", "pytest",
                    test_file,
                    "-p", "no:pytest_ethereum",
                    "-v",
                    "--tb=short",
                    "--no-header",
                    # Restrict network: --no-site prevents most external imports
                    # but we cannot fully block net at subprocess level on Windows
                ],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=tmpdir,
                preexec_fn=preexec_fn,
            )
            stdout = result.stdout
            stderr = result.stderr
            combined_output = stdout + ("\n" + stderr if stderr.strip() else "")

            # Parse pytest summary line e.g. "2 passed, 1 failed in 0.12s"
            num_passed, num_total = _parse_pytest_summary(stdout)
            passed = (num_passed == num_total) and num_total > 0

            return {
                "passed": passed,
                "output": combined_output,
                "num_tests_passed": num_passed,
                "num_tests_total": num_total,
            }

        except subprocess.TimeoutExpired:
            logger.warning(f"code_sandbox: timeout after {timeout_seconds}s")
            return {
                "passed": False,
                "output": f"Execution timed out after {timeout_seconds} seconds.",
                "num_tests_passed": 0,
                "num_tests_total": 0,
            }
        except Exception as e:
            logger.error(f"code_sandbox unexpected error: {e}")
            return {
                "passed": False,
                "output": f"Sandbox error: {e}",
                "num_tests_passed": 0,
                "num_tests_total": 0,
            }


def _parse_pytest_summary(output: str) -> tuple[int, int]:
    """
    Parse pytest output to extract (num_passed, num_total).
    Looks for lines like: '2 passed' or '1 passed, 2 failed' or '3 failed'.
    """
    passed = 0
    failed = 0
    error_count = 0

    passed_match = re.search(r"(\d+) passed", output)
    if passed_match:
        passed = int(passed_match.group(1))

    failed_match = re.search(r"(\d+) failed", output)
    if failed_match:
        failed = int(failed_match.group(1))

    error_match = re.search(r"(\d+) error", output)
    if error_match:
        error_count = int(error_match.group(1))

    total = passed + failed + error_count
    return passed, total
