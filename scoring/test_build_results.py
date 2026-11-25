import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_results as br

RULES_HEADER = ["run_id", "rule_id", "visible", "result"]
RUNS_HEADER = ["run_id", "invented_restrictions", "closed_a_choice",
               "questions_asked", "budget_stated", "notes"]
CARD_HEADER = ["case", "rule_id", "result"]


def full_rules():
    """Every expected run, every fixed rule visible and kept."""
    rows = []
    for run_id in br.expected_runs():
        for rule_id in br.CASES[run_id.split("-")[0]]:
            rows.append({"run_id": run_id, "rule_id": rule_id,
                         "visible": "yes", "result": "kept"})
    return rows


def full_runs():
    rows = []
    for run_id in br.expected_runs():
        case = run_id.split("-")[0]
        rows.append({"run_id": run_id, "invented_restrictions": "0",
                     "closed_a_choice": "0", "questions_asked": "0",
                     "budget_stated": "16000" if case == "c2" else "",
                     "notes": ""})
    return rows


def full_cards():
    return [{"case": case, "rule_id": rule_id, "result": "kept"}
            for case, rule_ids in br.CASES.items() for rule_id in rule_ids]


def write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def make_dir(rules=None, runs=None, check_rules=None, check_runs=None,
             cards=None):
    folder = Path(tempfile.mkdtemp())
    write(folder / "rules-pass-1.csv", RULES_HEADER,
          full_rules() if rules is None else rules)
    write(folder / "runs-pass-1.csv", RUNS_HEADER,
          full_runs() if runs is None else runs)
    write(folder / "rules-pass-2.csv", RULES_HEADER,
          full_rules() if check_rules is None else check_rules)
    write(folder / "runs-pass-2.csv", RUNS_HEADER,
          full_runs() if check_runs is None else check_runs)
    write(folder / "card-check.csv", CARD_HEADER,
          full_cards() if cards is None else cards)
    return folder


def change(rows, run_id, rule_id=None, **cells):
    for row in rows:
        if row["run_id"] == run_id and (
                rule_id is None or row["rule_id"] == rule_id):
            row.update(cells)
    return rows


def run_cli(folder, *flags):
    return subprocess.run(
        [sys.executable, str(HERE / "build_results.py"),
         "--dir", str(folder), *flags],
        capture_output=True, text=True)


class ExpectedRuns(unittest.TestCase):
    def test_nine_runs_all_in_the_second_account(self):
        runs = br.expected_runs()
        self.assertEqual(len(runs), 9)
        self.assertTrue(all(run.endswith("-second") for run in runs))
        self.assertEqual(runs[0], "c1-A-second")
        self.assertEqual(runs[-1], "c3-C-second")

    def test_case_3_has_four_fixed_rules_because_packs_are_the_hosts_choice(self):
        self.assertEqual(br.CASES["c3"], ["1", "3", "4", "5"])
        self.assertEqual(len(br.CASES["c1"]), 5)
        self.assertEqual(len(br.CASES["c2"]), 5)


class Counting(unittest.TestCase):
    def test_kept_is_counted_against_visible_rules_and_against_final_rules(self):
        rules = full_rules()
        change(rules, "c2-A-second", "1", visible="no", result="changed")
        change(rules, "c2-A-second", "4", visible="no", result="missing")
        change(rules, "c2-A-second", "5", visible="no", result="missing")
        results = br.build(make_dir(rules=rules))
        run = results["runs"]["c2-A-second"]
        self.assertEqual((run["kept_visible"], run["visible_total"]), (2, 2))
        self.assertEqual((run["kept_final"], run["final_total"]), (2, 5))

    def test_a_rule_kept_without_being_visible_counts_only_in_the_final_count(self):
        rules = full_rules()
        change(rules, "c1-A-second", "4", visible="no", result="kept")
        run = br.build(make_dir(rules=rules))["runs"]["c1-A-second"]
        self.assertEqual((run["kept_visible"], run["visible_total"]), (4, 4))
        self.assertEqual((run["kept_final"], run["final_total"]), (5, 5))

    def test_totals_are_given_by_handoff_and_for_all_9_runs(self):
        rules = full_rules()
        change(rules, "c1-A-second", "5", result="missing")
        runs = full_runs()
        change(runs, "c3-A-second", invented_restrictions="2",
               closed_a_choice="1", questions_asked="1")
        results = br.build(make_dir(rules=rules, runs=runs))
        a = results["by_handoff"]["A"]
        self.assertEqual(a["runs"], 3)
        self.assertEqual((a["kept_final"], a["final_total"]), (13, 14))
        self.assertEqual(a["invented_restrictions"], 2)
        self.assertEqual(a["closed_a_choice"], 1)
        self.assertEqual(a["questions_asked"], 1)
        c = results["by_handoff"]["C"]
        self.assertEqual((c["kept_final"], c["final_total"]), (14, 14))
        everything = results["all"]
        self.assertEqual(everything["runs"], 9)
        self.assertEqual(
            (everything["kept_final"], everything["final_total"]), (41, 42))
        self.assertEqual(everything["invented_restrictions"], 2)

    def test_budget_stated_is_reported_for_case_2(self):
        runs = full_runs()
        change(runs, "c2-B-second", budget_stated="both")
        results = br.build(make_dir(runs=runs))
        self.assertEqual(results["runs"]["c2-B-second"]["budget_stated"], "both")
        self.assertEqual(results["runs"]["c1-B-second"]["budget_stated"], "")


class Missing(unittest.TestCase):
    def test_a_blank_result_makes_the_run_missing(self):
        rules = full_rules()
        change(rules, "c3-B-second", "4", result="")
        results = br.build(make_dir(rules=rules))
        self.assertEqual(results["missing"], ["c3-B-second"])
        self.assertNotIn("c3-B-second", results["runs"])

    def test_a_case_2_run_with_no_budget_line_is_missing(self):
        runs = full_runs()
        change(runs, "c2-C-second", budget_stated="")
        self.assertEqual(br.build(make_dir(runs=runs))["missing"],
                         ["c2-C-second"])

    def test_blank_sheets_report_every_run_missing(self):
        rules = change(full_rules(), None)
        for row in rules:
            row.update(visible="", result="")
        runs = full_runs()
        for row in runs:
            row.update(invented_restrictions="", closed_a_choice="",
                       questions_asked="", budget_stated="")
        folder = make_dir(rules=rules, runs=runs)
        self.assertEqual(len(br.build(folder)["missing"]), 9)
        done = run_cli(folder, "--check")
        self.assertEqual(done.stdout.splitlines()[0], "0 runs, 9 missing")
        self.assertEqual(done.returncode, 1)


class Validation(unittest.TestCase):
    def test_an_unknown_result_word_is_refused_and_the_row_is_named(self):
        rules = full_rules()
        change(rules, "c1-B-second", "2", result="lost")
        done = run_cli(make_dir(rules=rules), "--check")
        self.assertEqual(done.returncode, 2)
        self.assertIn("rules-pass-1.csv", done.stderr)
        self.assertIn("c1-B-second", done.stderr)
        self.assertIn("lost", done.stderr)

    def test_more_closed_choices_than_invented_restrictions_is_refused(self):
        runs = full_runs()
        change(runs, "c1-A-second", invented_restrictions="1",
               closed_a_choice="2")
        done = run_cli(make_dir(runs=runs), "--check")
        self.assertEqual(done.returncode, 2)
        self.assertIn("c1-A-second", done.stderr)

    def test_more_than_three_questions_is_refused(self):
        runs = full_runs()
        change(runs, "c1-A-second", questions_asked="4")
        done = run_cli(make_dir(runs=runs), "--check")
        self.assertEqual(done.returncode, 2)
        self.assertIn("questions_asked", done.stderr)

    def test_a_run_id_outside_the_plan_is_refused(self):
        runs = full_runs()
        runs.append(dict(runs[0], run_id="c4-A-second"))
        done = run_cli(make_dir(runs=runs), "--check")
        self.assertEqual(done.returncode, 2)
        self.assertIn("c4-A-second", done.stderr)


class Check(unittest.TestCase):
    def test_complete_sheets_print_9_runs_0_missing(self):
        done = run_cli(make_dir(), "--check")
        self.assertEqual(done.stdout.splitlines()[0], "9 runs, 0 missing")
        self.assertEqual(done.stdout.splitlines()[1],
                         "second pass: 9 runs, 0 missing")
        self.assertEqual(done.returncode, 0)

    def test_every_score_where_the_two_passes_differ_is_listed(self):
        check_rules = full_rules()
        change(check_rules, "c2-B-second", "1", result="changed")
        check_runs = full_runs()
        change(check_runs, "c3-A-second", invented_restrictions="1")
        done = run_cli(make_dir(check_rules=check_rules,
                                check_runs=check_runs), "--check")
        self.assertIn("2 scores differ", done.stdout)
        self.assertIn("c2-B-second rule 1 result: pass 1=kept, pass 2=changed",
                      done.stdout)
        self.assertIn(
            "c3-A-second invented_restrictions: pass 1=0, pass 2=1",
            done.stdout)

    def test_a_difference_is_saved_with_both_passes_named(self):
        check_rules = full_rules()
        change(check_rules, "c2-B-second", "1", result="changed")
        results = br.build(make_dir(check_rules=check_rules))
        self.assertEqual(results["differences"],
                         [{"run_id": "c2-B-second", "field": "rule 1 result",
                           "pass_1": "kept", "pass_2": "changed"}])

    def test_notes_are_never_compared(self):
        check_runs = full_runs()
        change(check_runs, "c1-A-second", notes="reads fine to me")
        done = run_cli(make_dir(check_runs=check_runs), "--check")
        self.assertIn("0 scores differ", done.stdout)

    def test_check_writes_no_results_file(self):
        folder = make_dir()
        run_cli(folder, "--check")
        self.assertFalse((folder / "results.json").exists())

    def test_without_check_the_results_file_is_written(self):
        folder = make_dir()
        done = run_cli(folder)
        self.assertEqual(done.returncode, 0)
        saved = json.loads((folder / "results.json").read_text("utf-8"))
        self.assertEqual(len(saved["runs"]), 9)
        self.assertEqual(saved["missing"], [])


class CardLosses(unittest.TestCase):
    def test_a_rule_missing_from_the_card_is_lost_at_the_card(self):
        cards = full_cards()
        for row in cards:
            if row["case"] == "c2" and row["rule_id"] == "1":
                row["result"] = "changed"
        rules = full_rules()
        change(rules, "c2-C-second", "1", visible="no")
        change(rules, "c2-C-second", "1", result="changed")
        check_rules = [dict(row) for row in rules]
        run = br.build(make_dir(rules=rules, check_rules=check_rules,
                                cards=cards))["runs"]["c2-C-second"]
        self.assertEqual(run["losses"], [{"rule_id": "1", "lost_at": "card"}])

    def test_a_loss_is_unchecked_until_the_card_check_is_filled_in(self):
        cards = full_cards()
        for row in cards:
            row["result"] = ""
        rules = full_rules()
        change(rules, "c2-C-second", "1", result="changed")
        run = br.build(make_dir(rules=rules, cards=cards))["runs"]["c2-C-second"]
        self.assertEqual(run["losses"],
                         [{"rule_id": "1", "lost_at": "unchecked"}])

    def test_a_card_run_that_shows_a_rule_the_card_dropped_is_refused(self):
        cards = full_cards()
        for row in cards:
            if row["case"] == "c2" and row["rule_id"] == "1":
                row["result"] = "missing"
        done = run_cli(make_dir(cards=cards), "--check")
        self.assertEqual(done.returncode, 2)
        self.assertIn("c2-C-second rule 1", done.stderr)
        self.assertIn("card-check.csv", done.stderr)

    def test_a_rule_on_the_card_but_not_in_the_rules_is_lost_in_the_run(self):
        rules = full_rules()
        change(rules, "c2-C-second", "1", result="changed")
        run = br.build(make_dir(rules=rules))["runs"]["c2-C-second"]
        self.assertEqual(run["losses"], [{"rule_id": "1", "lost_at": "run"}])

    def test_handoffs_without_a_card_list_no_card_losses(self):
        rules = full_rules()
        change(rules, "c1-A-second", "4", visible="no", result="missing")
        run = br.build(make_dir(rules=rules))["runs"]["c1-A-second"]
        self.assertEqual(run["losses"], [])


class HandEditedSheets(unittest.TestCase):
    def test_a_note_with_an_unquoted_comma_does_not_break_the_sheet(self):
        folder = make_dir()
        path = folder / "runs-pass-1.csv"
        text = path.read_text("utf-8").replace(
            "c1-A-second,0,0,0,,",
            "c1-A-second,0,0,0,,banned mods, banned custom content")
        path.write_text(text, "utf-8")
        self.assertIn("c1-A-second", br.build(folder)["runs"])

    def test_a_sheet_saved_with_a_byte_order_mark_is_read(self):
        folder = make_dir()
        for name in ["rules-pass-1.csv", "runs-pass-1.csv"]:
            path = folder / name
            path.write_text("\ufeff" + path.read_text("utf-8"), "utf-8")
        self.assertEqual(br.build(folder)["missing"], [])

    def test_capital_letters_in_a_cell_are_accepted(self):
        rules = full_rules()
        change(rules, "c1-B-second", "2", visible="Yes", result="Kept")
        run = br.build(make_dir(rules=rules))["runs"]["c1-B-second"]
        self.assertEqual(run["kept_final"], 5)


def blank_first_pass():
    rules = full_rules()
    for row in rules:
        row.update(result="")
    runs = full_runs()
    for row in runs:
        row.update(invented_restrictions="", closed_a_choice="",
                   questions_asked="", budget_stated="")
    return rules, runs


class SecondPass(unittest.TestCase):
    def test_the_second_pass_is_scored_on_its_own_while_the_first_is_blank(self):
        rules, runs = blank_first_pass()
        check_rules = full_rules()
        change(check_rules, "c2-B-second", "1", result="changed")
        check_runs = full_runs()
        change(check_runs, "c2-B-second", invented_restrictions="2")
        results = br.build(make_dir(rules=rules, runs=runs,
                                    check_rules=check_rules,
                                    check_runs=check_runs))
        self.assertEqual(results["runs"], {})
        second = results["second_pass"]
        self.assertEqual(len(second["runs"]), 9)
        self.assertEqual(second["runs"]["c2-B-second"]["kept_final"], 4)
        self.assertEqual(second["by_handoff"]["B"]["kept_final"], 13)
        self.assertEqual(second["by_handoff"]["B"]["invented_restrictions"], 2)

    def test_the_second_pass_has_totals_by_handoff_and_for_all_9_runs(self):
        second = br.build(make_dir())["second_pass"]
        self.assertEqual(second["by_handoff"]["C"]["runs"], 3)
        self.assertEqual(second["all"]["runs"], 9)

    def test_an_unfinished_second_pass_run_stays_out_of_its_totals(self):
        check_rules = full_rules()
        change(check_rules, "c1-A-second", "2", result="")
        results = br.build(make_dir(check_rules=check_rules))
        self.assertNotIn("c1-A-second", results["second_pass"]["runs"])
        self.assertEqual(results["second_pass"]["by_handoff"]["A"]["runs"], 2)
        self.assertEqual(results["second_pass_missing"], ["c1-A-second"])


if __name__ == "__main__":
    unittest.main()
