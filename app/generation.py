import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.main import load_tree, all_nodes
from app.version_compare import compare_trees

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
STORE = BASE_DIR / "output" / "generated_cases.json"


class GenerateRequest(BaseModel):
    selection_id: int
    count: int = Field(default=4, ge=3, le=5)


def read_store():
    STORE.parent.mkdir(parents=True, exist_ok=True)
    if not STORE.exists():
        STORE.write_text("[]", encoding="utf-8")
    return json.loads(STORE.read_text(encoding="utf-8"))


def write_store(items):
    STORE.write_text(
        json.dumps(items, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def make_ideas(node, count):
    heading = node.get("heading", "Selected section")
    body = re.sub(r"\s+", " ", node.get("body", "")).strip()
    sentences = [
        s.strip() for s in re.split(r"(?<=[.!?])\s+", body)
        if len(s.strip()) > 20
    ]

    ideas = [
        {
            "title": f"Verify key requirements in {heading}",
            "objective": f"Check that the documented requirements for {heading} are represented correctly.",
            "steps": [
                "Open the relevant device or application workflow.",
                "Exercise the requirement described in the selected manual section.",
                "Compare the observed behavior with the documented requirement.",
            ],
            "expected_result": sentences[0] if sentences else
                f"The behavior matches the requirements documented in {heading}.",
        },
        {
            "title": f"Check boundary and invalid conditions for {heading}",
            "objective": "Verify safe and predictable behavior at relevant limits and invalid inputs.",
            "steps": [
                "Identify a documented limit or invalid condition.",
                "Exercise the condition in a controlled test environment.",
                "Observe the response and any warning or error indication.",
            ],
            "expected_result": "The device responds consistently with the documented limits and safety behavior.",
        },
        {
            "title": f"Verify recovery and repeatability for {heading}",
            "objective": "Check that the documented behavior remains consistent across repeated use or recovery.",
            "steps": [
                "Run the relevant operation once.",
                "Repeat it or recover from the applicable condition.",
                "Compare the outcome with the manual.",
            ],
            "expected_result": "The operation behaves consistently with the selected manual section.",
        },
        {
            "title": f"Validate manual detail for {heading}",
            "objective": "Check a specific statement in the source section against the implementation.",
            "steps": [
                "Locate the selected section in the source manual.",
                "Identify a concrete statement or parameter.",
                "Verify the corresponding behavior or configuration.",
            ],
            "expected_result": sentences[1] if len(sentences) > 1 else
                f"The implementation agrees with the source manual section: {heading}.",
        },
        {
            "title": f"Review traceability for {heading}",
            "objective": "Ensure the requirement can be traced to a test and its result.",
            "steps": [
                "Record the source section identifier.",
                "Execute the test and capture the result.",
                "Confirm the result references the same requirement.",
            ],
            "expected_result": "The test result is traceable to the selected manual section and requirement.",
        },
    ]
    return ideas[:count]


def stale_status(item):
    latest_tree = load_tree("v2")
    pinned_tree = load_tree(item["version"])
    latest_nodes = all_nodes(latest_tree)
    pinned_nodes = all_nodes(pinned_tree)
    statuses = []

    for ref in item["sources"]:
        number = ref["number"]
        pinned = pinned_nodes.get(number)
        current = latest_nodes.get(number)

        if current is None:
            statuses.append({
                "node_id": ref["node_id"],
                "status": "removed",
            })
        elif pinned is None or current.get("content_hash") != pinned.get("content_hash"):
            statuses.append({
                "node_id": ref["node_id"],
                "status": "changed",
            })
        else:
            statuses.append({
                "node_id": ref["node_id"],
                "status": "unchanged",
            })

    stale = any(s["status"] != "unchanged" for s in statuses)
    return {
        "is_stale": stale,
        "assessment": "potentially_stale" if stale else "no_detected_change",
        "node_statuses": statuses,
        "limitation": "Hash comparison detects text changes in matched section numbers; it does not prove whether a test remains semantically valid.",
    }


@router.post("/generate")
def generate_cases(request: GenerateRequest):
    import sqlite3

    with sqlite3.connect(BASE_DIR / "tri9t.db") as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, name, version, node_numbers FROM selections WHERE id = ?",
            (request.selection_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(404, "Selection not found")

    version = row["version"]
    nodes = all_nodes(load_tree(version))
    selected_numbers = json.loads(row["node_numbers"])
    sources = []

    for number in selected_numbers:
        node = nodes[number]
        sources.append({
            "node_id": f"{version}:{number}",
            "number": number,
            "heading": node.get("heading"),
            "content_hash": node.get("content_hash"),
        })

    ideas = []
    for number in selected_numbers:
        ideas.extend(make_ideas(nodes[number], request.count))

    ideas = ideas[:request.count]
    record = {
        "id": str(uuid.uuid4()),
        "selection_id": row["id"],
        "selection_name": row["name"],
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_method": "deterministic_template_fallback",
        "sources": sources,
        "cases": [
            {"case_id": str(uuid.uuid4()), **idea} for idea in ideas
        ],
    }

    store = read_store()
    store.append(record)
    write_store(store)
    return {**record, "staleness": stale_status(record)}


@router.get("/generated-cases")
def list_generated_cases(selection_id: int | None = None, node_number: str | None = None):
    items = read_store()
    results = []

    for item in items:
        if selection_id is not None and item["selection_id"] != selection_id:
            continue
        if node_number is not None and not any(
            source["number"] == node_number for source in item["sources"]
        ):
            continue
        results.append({**item, "staleness": stale_status(item)})

    return {"count": len(results), "results": results}


@router.get("/generated-cases/{case_set_id}")
def get_generated_case_set(case_set_id: str):
    for item in read_store():
        if item["id"] == case_set_id:
            return {**item, "staleness": stale_status(item)}
    raise HTTPException(404, "Generated case set not found")
