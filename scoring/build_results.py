"""Turn the scoring sheets into results.json.

Every run is scored twice from the saved text. Melissa's sheets are the
ones the page reports. The check sheets are an automated second pass, and
this script lists every score where the 2 differ.

    python3 scoring/build_results.py --check   # count runs, list differences
    python3 scoring/build_results.py           # same, and write results.json
"""

import argparse
import csv
import json
import sys
from pathlib import Path

# The fixed rules in each case, by rule number. Case 3 leaves the packs to
# whoever hosts, so rule 2 is an open choice there and not a fixed rule.
CASES = {
    "c1": ["1", "2", "3", "4", "5"],
    "c2": ["1", "2", "3", "4", "5"],
    "c3": ["1", "3", "4", "5"],
}
HANDOFFS = ["A", "B", "C"]
RESULTS = {"kept", "changed", "missing"}
VISIBLE = {"yes", "no"}
BUDGETS = {"16000", "20000", "both", "neither"}
MAX_QUESTIONS = 3
COUNT_FIELDS = ["invented_restrictions", "closed_a_choice", "questions_asked"]


class SheetError(Exception):
    """A cell holds a value the sheet does not allow."""


def expected_runs():
    """9 runs in the second account, then 3 card runs in the creator's."""
    second = [f"{case}-{handoff}-second" for case in CASES for handoff in HANDOFFS]
    same = [f"{case}-C-same" for case in CASES]
    return second + same


def read_rows(path):
    """Rows as plain text cells. Sheets get filled in by hand, so a byte order
    mark is skipped and a note with an unquoted comma is put back together."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            overflow = row.pop(None, None)
            if overflow:
                last = reader.fieldnames[-1]
                row[last] = ",".join([row[last] or "", *overflow])
            rows.append({key: (value or "").strip()
                         for key, value in row.items()})
        return rows


def load_rules(path):
    """{run_id: {rule_id: {"visible": ..., "result": ...}}}"""
    name = Path(path).name
    known = set(expected_runs())
    sheet = {}
    for row in read_rows(path):
        run_id, rule_id = row["run_id"], row["rule_id"]
        row["visible"] = row["visible"].lower()
        row["result"] = row["result"].lower()
        if run_id not in known:
            raise SheetError(f"{name}: {run_id} is not a run in this test")
        if rule_id not in CASES[run_id.split("-")[0]]:
            raise SheetError(f"{name}: {run_id} has no fixed rule {rule_id}")
        if row["visible"] and row["visible"] not in VISIBLE:
            raise SheetError(
                f"{name}: {run_id} rule {rule_id} visible is "
                f"'{row['visible']}', expected yes or no")
        if row["result"] and row["result"] not in RESULTS:
            raise SheetError(
                f"{name}: {run_id} rule {rule_id} result is "
                f"'{row['result']}', expected kept, changed or missing")
        sheet.setdefault(run_id, {})[rule_id] = {
            "visible": row["visible"], "result": row["result"]}
    return sheet


def load_runs(path):
    """{run_id: {field: value}}"""
    name = Path(path).name
    known = set(expected_runs())
    sheet = {}
    for row in read_rows(path):
        run_id = row["run_id"]
        row["budget_stated"] = row["budget_stated"].lower()
        if run_id not in known:
            raise SheetError(f"{name}: {run_id} is not a run in this test")
        for field in COUNT_FIELDS:
            if row[field] and not row[field].isdigit():
                raise SheetError(
                    f"{name}: {run_id} {field} is '{row[field]}', "
                    "expected a whole number")
        if row["questions_asked"] and int(row["questions_asked"]) > MAX_QUESTIONS:
            raise SheetError(
                f"{name}: {run_id} questions_asked is {row['questions_asked']}, "
                f"and a run stops after {MAX_QUESTIONS}")
        if (row["invented_restrictions"] and row["closed_a_choice"]
                and int(row["closed_a_choice"]) > int(row["invented_restrictions"])):
            raise SheetError(
                f"{name}: {run_id} closes more choices than it has "
                "invented restrictions")
        if row["budget_stated"] and row["budget_stated"] not in BUDGETS:
            raise SheetError(
                f"{name}: {run_id} budget_stated is '{row['budget_stated']}', "
                "expected 16000, 20000, both or neither")
        sheet[run_id] = row
    return sheet


def load_cards(path):
    """{case: {rule_id: result}}. An absent sheet means no card was checked yet."""
    if not Path(path).exists():
        return {}
    cards = {}
    for row in read_rows(path):
        row["result"] = row["result"].lower()
        if row["result"] and row["result"] not in RESULTS:
            raise SheetError(
                f"{Path(path).name}: {row['case']} rule {row['rule_id']} result "
                f"is '{row['result']}', expected kept, changed or missing")
        cards.setdefault(row["case"], {})[row["rule_id"]] = row["result"]
    return cards


def is_complete(run_id, rules, runs):
    """Every fixed rule is scored and every count is filled in."""
    case = run_id.split("-")[0]
    rule_rows = rules.get(run_id, {})
    for rule_id in CASES[case]:
        cells = rule_rows.get(rule_id)
        if not cells or not cells["visible"] or not cells["result"]:
            return False
    run_row = runs.get(run_id)
    if not run_row or any(not run_row[field] for field in COUNT_FIELDS):
        return False
    if case == "c2" and not run_row["budget_stated"]:
        return False
    return True


def score_run(run_id, rules, runs, cards):
    case, handoff, account = run_id.split("-")
    rule_rows = rules[run_id]
    run_row = runs[run_id]
    visible = [r for r in CASES[case] if rule_rows[r]["visible"] == "yes"]
    kept = [r for r in CASES[case] if rule_rows[r]["result"] == "kept"]
    losses = []
    if handoff == "C":
        card = cards.get(case, {})
        for rule_id in CASES[case]:
            if rule_rows[rule_id]["result"] != "kept":
                lost_at = {"kept": "run", "changed": "card",
                           "missing": "card"}.get(card.get(rule_id), "unchecked")
                losses.append({"rule_id": rule_id, "lost_at": lost_at})
    return {
        "case": case,
        "handoff": handoff,
        "account": account,
        "kept_visible": len([r for r in kept if r in visible]),
        "visible_total": len(visible),
        "kept_final": len(kept),
        "final_total": len(CASES[case]),
        "invented_restrictions": int(run_row["invented_restrictions"]),
        "closed_a_choice": int(run_row["closed_a_choice"]),
        "questions_asked": int(run_row["questions_asked"]),
        "budget_stated": run_row["budget_stated"] if case == "c2" else "",
        "rules": {r: dict(rule_rows[r]) for r in CASES[case]},
        "losses": losses,
    }


def total(scored):
    sums = {"runs": len(scored)}
    for field in ["kept_visible", "visible_total", "kept_final", "final_total",
                  *COUNT_FIELDS]:
        sums[field] = sum(run[field] for run in scored)
    return sums


def differences(rules, runs, check_rules, check_runs):
    """Every score where the two passes differ, for runs both have finished."""
    found = []
    for run_id in expected_runs():
        if not (is_complete(run_id, rules, runs)
                and is_complete(run_id, check_rules, check_runs)):
            continue
        for rule_id in CASES[run_id.split("-")[0]]:
            for field in ["visible", "result"]:
                mine = rules[run_id][rule_id][field]
                theirs = check_rules[run_id][rule_id][field]
                if mine != theirs:
                    found.append({"run_id": run_id,
                                  "field": f"rule {rule_id} {field}",
                                  "melissa": mine, "check": theirs})
        for field in [*COUNT_FIELDS, "budget_stated"]:
            mine, theirs = runs[run_id][field], check_runs[run_id][field]
            if mine != theirs:
                found.append({"run_id": run_id, "field": field,
                              "melissa": mine, "check": theirs})
    return found


def check_card_runs(name, rules, cards):
    """A card run can only show a rule the card carries."""
    for run_id, rule_rows in rules.items():
        case, handoff, _ = run_id.split("-")
        if handoff != "C":
            continue
        for rule_id, cells in rule_rows.items():
            on_card = cards.get(case, {}).get(rule_id)
            if not on_card or not cells["visible"]:
                continue
            expected = "yes" if on_card == "kept" else "no"
            if cells["visible"] != expected:
                raise SheetError(
                    f"{name}: {run_id} rule {rule_id} visible is "
                    f"{cells['visible']}, but card-check.csv marks that rule "
                    f"as {on_card} on the card")


def build(folder):
    folder = Path(folder)
    rules = load_rules(folder / "rules-melissa.csv")
    runs = load_runs(folder / "runs-melissa.csv")
    check_rules = load_rules(folder / "rules-check.csv")
    check_runs = load_runs(folder / "runs-check.csv")
    cards = load_cards(folder / "card-check.csv")
    check_card_runs("rules-melissa.csv", rules, cards)
    check_card_runs("rules-check.csv", check_rules, cards)

    scored, missing = {}, []
    for run_id in expected_runs():
        if is_complete(run_id, rules, runs):
            scored[run_id] = score_run(run_id, rules, runs, cards)
        else:
            missing.append(run_id)

    second = [run for run in scored.values() if run["account"] == "second"]
    return {
        "runs": scored,
        "missing": missing,
        "by_handoff": {handoff: total([run for run in second
                                       if run["handoff"] == handoff])
                       for handoff in HANDOFFS},
        "same_account": total([run for run in scored.values()
                               if run["account"] == "same"]),
        "second_pass_missing": [
            run_id for run_id in expected_runs()
            if not is_complete(run_id, check_rules, check_runs)],
        "differences": differences(rules, runs, check_rules, check_runs),
        "cards": cards,
    }


def report(results):
    expected = len(expected_runs())
    check_missing = len(results["second_pass_missing"])
    lines = [
        f"{len(results['runs'])} runs, {len(results['missing'])} missing",
        f"second pass: {expected - check_missing} runs, {check_missing} missing",
        f"{len(results['differences'])} scores differ",
    ]
    for item in results["differences"]:
        lines.append(f"{item['run_id']} {item['field']}: "
                     f"melissa={item['melissa']} check={item['check']}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", default=Path(__file__).resolve().parent,
                        help="folder that holds the scoring sheets")
    parser.add_argument("--check", action="store_true",
                        help="report only, and write no file")
    args = parser.parse_args(argv)

    try:
        results = build(args.dir)
    except SheetError as problem:
        print(problem, file=sys.stderr)
        return 2

    print(report(results))
    if not args.check:
        out = Path(args.dir) / "results.json"
        out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 1 if results["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
