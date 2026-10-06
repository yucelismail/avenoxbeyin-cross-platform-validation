"""Machine-readable unittest results: assertion failures differ from setup errors."""
import json
from pathlib import Path
import unittest

suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern='contract_test.py')
result = unittest.TestResult()
suite.run(result)
print(json.dumps({'tests': result.testsRun,
                  'failures': [t.id().split('.')[-1] for t, _ in result.failures],
                  'errors': [t.id().split('.')[-1] for t, _ in result.errors],
                  'details': [detail for _, detail in result.failures + result.errors]}))
raise SystemExit(2 if result.errors else 1 if result.failures else 0)
