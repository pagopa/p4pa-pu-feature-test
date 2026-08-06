#!/usr/bin/env python3
"""Build a Markdown summary from behave JUnit XML.

Meant to be uploaded to the Azure DevOps run summary via
``##vso[task.uploadsummary]``, to give a more readable view than the raw
Tests tab (totals + the list of failed scenarios). Reads the JUnit files
that behave already produces; it does not run anything.
"""
import argparse
import glob
import os
import xml.etree.ElementTree as ET


def feature_label(suite_name):
    # behave names suites "features.<file>.<Feature name>"; keep just the feature name.
    parts = suite_name.split(".", 2)
    return parts[-1] if len(parts) == 3 else suite_name


def collect(junit_dir):
    total = passed = failed = skipped = 0
    failures = []
    for path in sorted(glob.glob(os.path.join(junit_dir, "*.xml"))):
        root = ET.parse(path).getroot()
        for suite in root.iter("testsuite"):
            for case in suite.findall("testcase"):
                total += 1
                status = case.get("status")
                is_failure = case.find("failure") is not None or case.find("error") is not None
                if case.find("skipped") is not None or status in ("skipped", "untested"):
                    skipped += 1
                elif is_failure or status in ("failed", "error"):
                    failed += 1
                    failures.append((feature_label(suite.get("name", "")), case.get("name", "")))
                else:
                    passed += 1
    return total, passed, failed, skipped, failures


def render(tag, total, passed, failed, skipped, failures):
    heading = f"## Feature test summary — {tag}" if tag else "## Feature test summary"
    lines = [
        heading, "",
        "| Total | ✅ Passed | ❌ Failed | ⏭️ Skipped |",
        "|---|---|---|---|",
        f"| {total} | {passed} | {failed} | {skipped} |",
    ]
    if failures:
        lines += ["", "### ❌ Failed scenarios"]
        lines += [f"- **{feature}** → {scenario}" for feature, scenario in failures]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Markdown summary from behave JUnit XML.")
    parser.add_argument("--junit-dir", default="tests/reports/behave")
    parser.add_argument("--tag", default="")
    parser.add_argument("--out", default="summary.md")
    args = parser.parse_args()

    data = collect(args.junit_dir)
    with open(args.out, "w", encoding="utf-8") as out:
        out.write(render(args.tag, *data))
    print(f"Wrote {args.out}: total={data[0]} passed={data[1]} failed={data[2]} skipped={data[3]}")


if __name__ == "__main__":
    main()
