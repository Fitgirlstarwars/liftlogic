# Add Feature Workflow

Guided workflow for adding a new feature to LiftLogic.

## Usage
```
/project:add-feature <domain> <feature_name>
```

## Arguments
- `domain`: Target domain (extraction, search, knowledge, diagnosis, orchestration)
- `feature_name`: Name of the feature to add

## Instructions

Follow this checklist to add a feature:

### 1. Check Contracts
First, read the contracts file to understand existing interfaces:
```
Read: liftlogic/domains/$1/contracts.py
```

### 2. Check Models
Review existing data types:
```
Read: liftlogic/domains/$1/models.py
```

### 3. Plan Changes
Based on the feature "$2", determine:
- Do we need new Pydantic models?
- Do we need new Protocol methods?
- Which implementation file needs changes?

### 4. Implementation Order
1. Add types to `models.py` (if needed)
2. Add protocol method to `contracts.py` (if needed)
3. Implement in appropriate `.py` file
4. Update `__init__.py` exports
5. Add API route (if user-facing)
6. Add CLI command (if applicable)
7. Write tests

### 5. Verify
After implementation, run:
```bash
cd /Users/fender/Desktop/liftlogic && mypy liftlogic/domains/$1 && pytest liftlogic/domains/$1 -v
```

Present a summary of all changes made.
