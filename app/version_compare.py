import argparse
import json
from pathlib import Path


def flatten_sections(tree):
    """Flatten a nested section tree, keyed by section number."""
    result = {}

    def visit(sections):
        for section in sections:
            number = section["number"]
            result[number] = section
            visit(section.get("children", []))

    visit(tree.get("sections", []))
    return result


def compare_trees(old_tree, new_tree):
    old_sections = flatten_sections(old_tree)
    new_sections = flatten_sections(new_tree)
    changes = []

    for number in sorted(
        set(old_sections) | set(new_sections),
        key=lambda n: tuple(
            int(part) if part.isdigit() else part
            for part in n.split(".")
        ),
    ):
        old = old_sections.get(number)
        new = new_sections.get(number)

        if old is None:
            status = "added"
        elif new is None:
            status = "removed"
        elif old.get("content_hash") != new.get("content_hash"):
            status = "changed"
        else:
            status = "unchanged"

        item = {
            "section_number": number,
            "status": status,
            "old_heading": old.get("heading") if old else None,
            "new_heading": new.get("heading") if new else None,
        }

        if status in ("changed", "removed"):
            item["old_body"] = old.get("body", "")
        if status in ("changed", "added"):
            item["new_body"] = new.get("body", "")

        changes.append(item)

    return {
        "old_document": old_tree.get("source_file"),
        "new_document": new_tree.get("source_file"),
        "summary": {
            status: sum(1 for item in changes if item["status"] == status)
            for status in ("unchanged", "changed", "added", "removed")
        },
        "changes": changes,
    }


def main():
    parser = argparse.ArgumentParser(description="Compare two parsed manual versions")
    parser.add_argument("old_json")
    parser.add_argument("new_json")
    parser.add_argument("--out", default="output/version_diff.json")
    args = parser.parse_args()

    with open(args.old_json, encoding="utf-8") as file:
        old_tree = json.load(file)
    with open(args.new_json, encoding="utf-8") as file:
        new_tree = json.load(file)

    result = compare_trees(old_tree, new_tree)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Comparison complete:", output)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
