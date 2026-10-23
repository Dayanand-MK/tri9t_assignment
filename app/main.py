import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.version_compare import compare_trees, flatten_sections

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = BASE_DIR / "tri9t.db"

VERSION_FILES = {
    "v1": OUTPUT_DIR / "v1_tree.json",
    "v2": OUTPUT_DIR / "v2_tree.json",
}

app = FastAPI(
    title="Tri9T Manual Intelligence API",
    description="Versioned document parsing, search, comparison and selections.",
    version="1.0.0",
)


def load_tree(version: str):
    if version not in VERSION_FILES:
        raise HTTPException(404, f"Unknown version '{version}'. Use v1 or v2.")

    path = VERSION_FILES[version]
    if not path.exists():
        raise HTTPException(404, f"Parsed tree not found: {path.name}")

    with path.open(encoding="utf-8-sig") as file:
        return json.load(file)


def all_nodes(tree):
    result = {}

    def visit(sections):
        for section in sections:
            result[section["number"]] = section
            visit(section.get("children", []))

    visit(tree.get("sections", []))
    return result


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS selections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                version TEXT NOT NULL,
                node_numbers TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


init_db()


class SelectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    version: str = Field(pattern="^v[12]$")
    node_numbers: list[str] = Field(min_length=1)


@app.get("/")
def root():
    return {
        "name": "Tri9T Manual Intelligence API",
        "docs": "/docs",
        "versions": ["/versions", "/versions/v1/sections", "/versions/v2/sections"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/versions")
def versions():
    result = []
    for version, path in VERSION_FILES.items():
        if path.exists():
            tree = load_tree(version)
            result.append({
                "version": version,
                "source_file": tree.get("source_file"),
                "page_count": tree.get("page_count"),
                "section_count": len(all_nodes(tree)),
            })
    return {"versions": result, "latest": result[-1]["version"] if result else None}


@app.get("/versions/{version}/sections")
def list_sections(version: str):
    tree = load_tree(version)
    return {
        "version": version,
        "sections": [
            {
                "number": section["number"],
                "heading": section["heading"],
                "level": section.get("level"),
                "parent_number": section.get("parent_number"),
                "page_start": section.get("page_start"),
            }
            for section in tree.get("sections", [])
        ],
    }


@app.get("/versions/{version}/nodes/{number:path}")
def get_node(version: str, number: str):
    tree = load_tree(version)
    node = all_nodes(tree).get(number)

    if node is None:
        raise HTTPException(404, f"Section {number} not found in {version}")

    return {
        "version": version,
        "node_id": f"{version}:{number}",
        **node,
    }


@app.get("/versions/{version}/search")
def search_nodes(
    version: str,
    q: str = Query(min_length=1),
):
    tree = load_tree(version)
    query = q.casefold()
    matches = []

    for number, node in all_nodes(tree).items():
        heading = node.get("heading", "")
        body = node.get("body", "")
        if query in heading.casefold() or query in body.casefold():
            matches.append({
                "node_id": f"{version}:{number}",
                "number": number,
                "heading": heading,
                "match_in_heading": query in heading.casefold(),
                "body_excerpt": body[:300],
                "content_hash": node.get("content_hash"),
            })

    return {"version": version, "query": q, "count": len(matches), "results": matches}


@app.get("/compare")
def compare_versions(
    old: str = "v1",
    new: str = "v2",
    status: Optional[str] = None,
):
    result = compare_trees(load_tree(old), load_tree(new))

    if status:
        allowed = {"unchanged", "changed", "added", "removed"}
        if status not in allowed:
            raise HTTPException(400, f"status must be one of {sorted(allowed)}")
        result["changes"] = [
            item for item in result["changes"] if item["status"] == status
        ]

    result["filtered_count"] = len(result["changes"])
    return result


@app.post("/selections", status_code=201)
def create_selection(request: SelectionRequest):
    tree = load_tree(request.version)
    nodes = all_nodes(tree)

    missing = sorted(set(request.node_numbers) - set(nodes))
    if missing:
        raise HTTPException(
            400,
            {"message": "Some section numbers do not exist in this version",
             "missing": missing},
        )

    # Reject duplicate names rather than silently overwriting a saved selection.
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO selections (name, version, node_numbers) VALUES (?, ?, ?)",
                (
                    request.name.strip(),
                    request.version,
                    json.dumps(list(dict.fromkeys(request.node_numbers))),
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                409,
                "A selection with this name already exists. Use a different name.",
            )

        selection_id = cursor.lastrowid

    return get_selection(selection_id)


@app.get("/selections")
def list_selections():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, name, version, node_numbers, created_at "
            "FROM selections ORDER BY id"
        ).fetchall()

    return {
        "selections": [
            {
                "id": row["id"],
                "name": row["name"],
                "version": row["version"],
                "node_numbers": json.loads(row["node_numbers"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


@app.get("/selections/{selection_id}")
def get_selection(selection_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, name, version, node_numbers, created_at "
            "FROM selections WHERE id = ?",
            (selection_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(404, "Selection not found")

    numbers = json.loads(row["node_numbers"])
    tree = load_tree(row["version"])
    nodes = all_nodes(tree)

    return {
        "id": row["id"],
        "name": row["name"],
        "version": row["version"],
        "created_at": row["created_at"],
        "nodes": [
            {
                "node_id": f"{row['version']}:{number}",
                "number": number,
                "heading": nodes[number].get("heading"),
                "body": nodes[number].get("body", ""),
                "content_hash": nodes[number].get("content_hash"),
            }
            for number in numbers
        ],
    }

from app.generation import router as generation_router
app.include_router(generation_router, prefix="/qa", tags=["QA Generation"])

from app.generation import router as generation_router
app.include_router(generation_router, prefix="/qa", tags=["QA Generation"])
