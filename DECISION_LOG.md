# Implementation Decision Log
## Tri9T AI Engineering Internship Assignment

### Decision 1: Python and FastAPI

**Choice:** Python with FastAPI.

**Reason:** FastAPI supports quick development of REST endpoints and provides interactive Swagger documentation, making the backend easy to test without a frontend.

### Decision 2: PyMuPDF for PDF Extraction

**Choice:** PyMuPDF.

**Reason:** It extracts text directly from the supplied PDF files and avoids requiring an external document-processing service.

**Trade-off:** Complex layouts, tables, and irregular heading structures require additional parsing logic and may not be represented perfectly.

### Decision 3: Nested JSON for Document Trees

**Choice:** Represent sections as nested JSON objects.

**Reason:** Nested nodes naturally represent parent-child relationships and make it straightforward to return a section together with its descendants.

**Trade-off:** More sophisticated document structures may require explicit node tables or a richer document schema.

### Decision 4: Section Identifiers and Content Hashes

**Choice:** Use section identifiers and content hashes for version comparison.

**Reason:** Identifiers provide a practical way to align corresponding sections, while hashes help detect content changes.

**Trade-off:** This is not full semantic matching. Renumbered or relocated content may require additional matching logic.

### Decision 5: SQLite for Named Selections

**Choice:** Store named selections in SQLite.

**Reason:** SQLite is available locally and does not require a separate database server.

**Trade-off:** A production application may require migrations, stronger transactional guarantees, and a more comprehensive relational data model.

### Decision 6: JSON Storage for Generated Cases

**Choice:** Store generated QA case sets in a JSON file.

**Reason:** JSON is simple to inspect and suitable for a small local prototype.

**Trade-off:** Concurrent writes, data integrity, and querying become harder as usage increases. A database-backed implementation would be more suitable for production.

### Decision 7: Deterministic QA Generation

**Choice:** Use deterministic templates for the current implementation.

**Reason:** This allows the prototype to produce test-case ideas without API credentials or dependence on an external LLM service.

**Trade-off:** Template output is less flexible than genuine LLM-generated test cases. The current implementation should not be described as a live LLM integration.

### Decision 8: Hash-Based Staleness Checks

**Choice:** Compare pinned source hashes against the latest available section content.

**Reason:** This provides a straightforward way to flag generated cases whose source content may have changed.

**Trade-off:** A changed hash does not necessarily mean a test case is invalid, and unchanged hashes do not prove that a test case remains adequate.

### Decision 9: Automated Tests with Pytest

**Choice:** Use Pytest for automated testing.

**Reason:** It provides a simple way to run repeatable checks during development.

**Trade-off:** The current four passing tests are not comprehensive coverage of all API endpoints and error cases. Additional integration tests are needed.

### Decision 10: Document Limitations Explicitly

**Choice:** Document parser, matching, generation, and staleness limitations.

**Reason:** Clear limitations make the implementation easier to evaluate and establish a realistic basis for future improvements.
