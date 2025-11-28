# Extract PDF

Extract structured data from an elevator technical manual PDF.

## Usage
```
/project:extract <pdf_path> [--evaluate]
```

## Arguments
- `pdf_path` (required): Path to the PDF file
- `--evaluate` (optional): Run quality evaluation on extraction

## Instructions

Run the extraction command:

```bash
cd /Users/fender/Desktop/liftlogic && liftlogic extract "$1" --output extracted.json $2
```

After extraction, summarize:
- Number of components found
- Number of connections found
- Number of fault codes found
- Quality score (if --evaluate used)

If errors occur, provide troubleshooting suggestions.
