#!/usr/bin/env python3
"""
Omni-Ext test runner.
Discovers and runs all tests (unit, integration, E2E) with optional filtering.

Usage:
    py tests/run_all.py                          # Run all tests
    py tests/run_all.py --unit                   # Unit tests only
    py tests/run_all.py --integration            # Integration tests only
    py tests/run_all.py --e2e                    # E2E tests only
    py tests/run_all.py --bridge                 # Bridge unit tests only
    py tests/run_all.py --extension              # Extension unit tests only
    py tests/run_all.py --verbose                # Verbose output
    py tests/run_all.py --coverage               # With coverage report
"""
import sys, os, subprocess, glob, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def print_header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def run_pytest(path, label, verbose=False, coverage=False):
    """Run Python unit/integration tests with pytest."""
    args = [sys.executable, "-m", "pytest", path, "-v" if verbose else "-q", "--tb=short"]
    if coverage:
        args += ["--cov=" + os.path.join(ROOT, "bridge"), "--cov-report=term-missing"]
    print_header(f"{label} ({path})")
    start = time.time()
    result = subprocess.run(args, cwd=ROOT, capture_output=False)
    elapsed = time.time() - start
    print(f"  [{elapsed:.1f}s]")
    return result.returncode


def run_pytest_collect(path, label):
    """Just collect test count."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", path, "--collect-only", "-q"],
        cwd=ROOT, capture_output=True, text=True
    )
    count = 0
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and "selected" in line:
            try:
                count = int(line.split()[0])
            except:
                pass
    return count


def run_node_test(path, label):
    """Run a Node.js test file."""
    print_header(f"{label} ({path})")
    start = time.time()
    result = subprocess.run(["node", path], cwd=ROOT, capture_output=False)
    elapsed = time.time() - start
    print(f"  [{elapsed:.1f}s]")
    return result.returncode


def find_tests(suffix):
    """Find test files by suffix."""
    pattern = os.path.join(HERE, "**", f"*{suffix}")
    return sorted(glob.glob(pattern, recursive=True))


def main():
    args = set(sys.argv[1:])
    verbose = "--verbose" in args or "-v" in args
    coverage = "--coverage" in args or "-c" in args

    # Filter flags
    run_unit = "--unit" in args or "-u" in args
    run_integration = "--integration" in args or "-i" in args
    run_e2e = "--e2e" in args or "-e" in args
    run_bridge = "--bridge" in args or "-b" in args
    run_extension = "--extension" in args or "-x" in args

    # If no specific filter, run all
    run_all_flag = not (run_unit or run_integration or run_e2e or run_bridge or run_extension)

    exit_code = 0

    # ── Unit: Bridge (Python) ──
    if run_all_flag or run_unit or run_bridge:
        bridge_tests = find_tests("test_wl.py") + find_tests("test_summarize.py") + \
                       find_tests("test_mcpc.py") + find_tests("test_mcpm.py") + \
                       find_tests("test_sc.py")
        for test_file in bridge_tests:
            label = os.path.relpath(test_file, HERE)
            rc = run_pytest(test_file, label, verbose, coverage)
            if rc != 0:
                exit_code = 1

    # ── Unit: Extension (Node.js) ──
    if run_all_flag or run_unit or run_extension:
        ext_tests = find_tests("test_parser.js") + find_tests("test_config.js") + \
                    find_tests("test_injectImage.js")
        for test_file in ext_tests:
            label = os.path.relpath(test_file, HERE)
            rc = run_node_test(test_file, label)
            if rc != 0:
                exit_code = 1

    # ── Integration ──
    if run_all_flag or run_integration:
        int_tests_py = find_tests("test_bridge_ws.py")
        for test_file in int_tests_py:
            label = os.path.relpath(test_file, HERE)
            rc = run_pytest(test_file, label, verbose, coverage)
            if rc != 0:
                exit_code = 1

        int_tests_js = find_tests("test_agent_loop.js")
        for test_file in int_tests_js:
            label = os.path.relpath(test_file, HERE)
            rc = run_node_test(test_file, label)
            if rc != 0:
                exit_code = 1

    # ── E2E ──
    if run_all_flag or run_e2e:
        e2e_tests = find_tests("test_full_cycle.py")
        for test_file in e2e_tests:
            label = os.path.relpath(test_file, HERE)
            print_header(f"E2E ({label})")
            start = time.time()
            result = subprocess.run(
                [sys.executable, test_file],
                cwd=ROOT, capture_output=False
            )
            elapsed = time.time() - start
            print(f"  [{elapsed:.1f}s]")
            if result.returncode != 0:
                exit_code = 1

    # ── Summary ──
    if run_all_flag:
        print_header("ALL TESTS COMPLETE")
        if exit_code == 0:
            print("  ✅ All tests passed")
        else:
            print("  ❌ Some tests failed")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
