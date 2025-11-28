# Run All Checks

Run type checking, linting, and tests.

## Usage
```
/project:check
```

## Instructions

Run all quality checks in sequence:

1. **Type Check (mypy)**
```bash
cd /Users/fender/Desktop/liftlogic && mypy liftlogic --ignore-missing-imports
```

2. **Lint (ruff)**
```bash
cd /Users/fender/Desktop/liftlogic && ruff check .
```

3. **Tests (pytest)**
```bash
cd /Users/fender/Desktop/liftlogic && pytest -v --tb=short
```

Report results for each check. If any check fails, provide specific guidance on how to fix the issues.

Summary format:
- ✅ Type Check: PASSED / ❌ FAILED (N errors)
- ✅ Lint: PASSED / ❌ FAILED (N issues)
- ✅ Tests: PASSED / ❌ FAILED (N/M passed)
