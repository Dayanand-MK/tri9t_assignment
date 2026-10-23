# Approach Document
## Tri9T AI Engineering Internship Assignment

### 1. Objective

The objective of this project is to build a backend API that processes different versions of a fictional CardioTrack CT-200 Home Blood Pressure Monitor manual. The API represents document content in a hierarchy, compares versions, supports named selections, generates QA test-case ideas, and identifies potentially outdated generated cases.

### 2. Technology Stack

- Python
- FastAPI for REST API endpoints
- PyMuPDF for PDF text extraction
- Pydantic for request and response validation where implemented
- SQLite for named selection storage
- JSON files for parsed document trees, comparison results, and generated QA cases
- Pytest for automated tests

### 3. PDF Parsing and Hierarchy

The parser extracts text from the supplied PDF manuals and identifies section headings using their numbering and text patterns. The extracted content is organized into nested JSON nodes representing the document hierarchy.

The parser retains section identifiers, headings, content, and content hashes. Parent-child relationships are represented through nested nodes.

The parser also reports certain extraction problems. For example, the supplied manuals contain a subsection whose immediate parent heading is missing, and some text before the first recognized section is not assigned to a section.

PDF tables and other complex layouts may not be preserved perfectly by plain text extraction.

### 4. Content Hashing

Content hashes are used to identify changes in parsed section content. A hash can help distinguish unchanged text from modified text without comparing every character manually.

Hash-based comparison depends on the consistency of the extracted content. Changes in PDF formatting or extraction order can affect hashes even when the underlying meaning remains similar.

### 5. Version Comparison

The project compares the supplied V1 and V2 document trees. It classifies sections as unchanged, changed, added, or removed based on the identifiers and content comparison implemented in the application.

The current comparison result reports:
- Unchanged sections: 23
- Changed sections: 4
- Added sections: 1
- Removed sections: 0

These counts describe the current parsed outputs and may change if the parser or comparison logic is modified.

The current implementation does not provide full semantic matching of nodes whose identifiers or positions change.

### 6. API Design

The FastAPI application provides endpoints for:
- Checking API health
- Listing available document versions
- Browsing top-level sections
- Retrieving a section and its nested content
- Searching document headings and text
- Comparing two document versions
- Creating and retrieving named selections
- Generating QA test-case ideas from selections
- Retrieving generated cases and checking their potential staleness

Interactive API documentation is available through the FastAPI Swagger UI at `/docs` while the server is running locally.

### 7. Selection and Storage Design

Named selections are stored in SQLite. A selection records the selected section identifiers and the document version associated with them.

Generated QA cases are stored in a JSON file. Each generated case set includes source references and content hashes so that the system can check whether the referenced content may have changed.

This approach keeps the prototype simple to run without requiring an external database service.

### 8. QA Test-Case Generation

The current implementation generates QA test-case ideas using deterministic templates. It does not call a live large language model.

The generator supports a requested count between three and five ideas and associates generated output with the source selection and document content.

A future version could integrate an LLM provider, validate its structured responses, retry malformed responses, and record model and prompt metadata.

### 9. Staleness and Impact Detection

The current implementation compares the source hashes recorded with generated cases against the corresponding content in the latest document version.

When source content has changed or a referenced section can no longer be found, the generated cases can be marked as potentially stale.

This is a conservative content-change check, not proof that a test case is incorrect. It also does not fully understand semantic changes or automatically determine which individual test steps require revision.

### 10. Testing

The current automated test suite contains four tests, and the latest recorded run completed successfully with all four passing.

Further tests should cover API status codes, missing resources, duplicate selection names, invalid generation counts, generated-case persistence, and stale-content detection.

### 11. Known Limitations and Future Improvements

- Improve heading recognition and parent assignment for irregular documents.
- Preserve tables, lists, figures, and page references more accurately.
- Add stronger semantic matching across versions.
- Add API-level and generation-level automated tests.
- Integrate a real LLM with structured output validation and retries.
- Improve staleness detection to identify specific affected test cases.
- Consider a more structured persistence layer if the application grows.

### 12. Conclusion

This project provides a local backend prototype for parsing, browsing, comparing, and using versioned medical-device manual content. The implementation prioritizes traceability through section identifiers, content hashes, pinned selections, and source-linked QA output while documenting areas that require further development.
