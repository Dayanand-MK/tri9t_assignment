# Tri9T AI — CT-200 Document Intelligence

Deadline-focused implementation for the Tri9T AI internship assignment.

## Current scope
- CT-200-specific native PDF text extraction with PyMuPDF.
- Numbered section hierarchy, paragraphs, list-item detection, page provenance, SHA-256 content hashes, and parser warnings.
- Explicit tests for repeated headings, a missing intermediate heading, and version-specific changed thresholds.

## Known limitations (do not hide these)
- OCR fallback is not implemented; supplied PDFs have extractable text.
- Table cell grids are not yet reconstructed reliably; table content is preserved as extracted text.
- Parser is specific to this CT-200 manual and should not be described as a generic PDF parser.

## Setup
Python 3.10+ recommended.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
pytest -q
```

PDFs are in `data/ct200_manual.pdf` and `data/ct200_manual_v2.pdf`.
