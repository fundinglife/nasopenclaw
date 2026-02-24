"""Master test runner for nasOpenClaw test suite.

Usage:
    python tests/run_all.py                    # run all tests
    python tests/run_all.py test_configs       # run one module
"""
import os
import sys
import unittest


def main():
    test_dir = os.path.dirname(os.path.abspath(__file__))

    if len(sys.argv) > 1:
        pattern = f"{sys.argv[1]}.py"
    else:
        pattern = "test_*.py"

    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern=pattern, top_level_dir=os.path.dirname(test_dir))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(f"\n{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures:  {len(result.failures)}")
    print(f"Errors:    {len(result.errors)}")
    print(f"Skipped:   {len(result.skipped)}")
    print(f"{'='*60}")

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
