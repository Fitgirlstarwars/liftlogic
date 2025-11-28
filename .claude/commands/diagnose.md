# Diagnose Fault Code

Run fault code diagnosis from the CLI.

## Usage
```
/project:diagnose <fault_code> [manufacturer]
```

## Arguments
- `fault_code` (required): The fault code to diagnose (e.g., F505, E-42)
- `manufacturer` (optional): Manufacturer name (KONE, Otis, Schindler, etc.)

## Instructions

Run the diagnosis command:

```bash
cd /Users/fender/Desktop/liftlogic && liftlogic diagnose $1 --manufacturer "$2" --detailed
```

If manufacturer not provided, omit the --manufacturer flag.

Present the diagnosis results in a clear, formatted way showing:
- Severity level
- Possible causes
- Recommended remedies
- Safety warnings (if any)
