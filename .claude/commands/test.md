# Run Tests

Run the test suite for LiftLogic.

## Usage
```
/project:test [domain]
```

## Arguments
- `domain` (optional): Specific domain to test (extraction, search, knowledge, diagnosis, orchestration)

## Instructions

Run the appropriate pytest command:

If no argument provided:
```bash
cd /Users/fender/Desktop/liftlogic && pytest -v --tb=short
```

If domain specified:
```bash
cd /Users/fender/Desktop/liftlogic && pytest liftlogic/domains/$ARGUMENTS -v --tb=short
```

Report the results clearly, highlighting any failures.
