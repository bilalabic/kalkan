"""Offline evaluation against labelled test cases in data/."""
import json
import pathlib


def load_cases(path: str = "data") -> list[dict]:
    cases = []
    for f in pathlib.Path(path).glob("*.json"):
        cases.append(json.loads(f.read_text(encoding="utf-8")))
    return cases


if __name__ == "__main__":
    cases = load_cases()
    print(f"{len(cases)} test case(s) found.")
