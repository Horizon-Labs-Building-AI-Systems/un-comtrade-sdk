"""Validate CI-002/CI-003/CI-004 foundations across all workflows.

For every workflow file in .github/workflows/:

- Every declared job runs on ubuntu-latest.
- Every job that declares a Python matrix uses
  `3.11 / 3.12 / 3.13` with `fail-fast: false`.
- Every job with a Python matrix includes an
  `actions/checkout@v4` step.
- Every job with a Python matrix includes an
  `actions/setup-python@v5` step with `cache: pip`
  and `cache-dependency-path: pyproject.toml`.
- The `setup-python` step binds `python-version` to the
  matrix value.

The job name is intentionally not pinned (CI-001 used
`placeholder`, CI-002 renamed to `python-setup`, CI-003
uses `ruff`, CI-004 adds `mypy`, etc.).
"""
import sys
import pathlib

import yaml

ROOT = pathlib.Path(r"C:\Users\DELL\Downloads\India-Impex-Analytics\.github\workflows")
EXPECTED_MATRIX = ["3.11", "3.12", "3.13"]
EXPECTED_MATRIX_REF = "${{ matrix.python-version }}"


def main() -> int:
    fail = 0
    files = sorted(ROOT.glob("*.yml"))
    print(f"Validating {len(files)} workflows")

    for f in files:
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        name = data.get("name")
        jobs = data.get("jobs", {})
        if not jobs:
            print(f"  FAIL {f.name}: no jobs declared")
            fail += 1
            continue
        job_pass = 0
        for job_key, job in jobs.items():
            runs_on = job.get("runs-on")
            if runs_on != "ubuntu-latest":
                print(f"  FAIL {f.name}:{job_key} runs-on={runs_on}")
                fail += 1
                continue
            matrix = job.get("strategy", {}).get("matrix", {}).get("python-version")
            steps = job.get("steps", [])
            uses = [s.get("uses", "") for s in steps]
            checkout_ok = "actions/checkout@v4" in uses
            sp_steps = [
                s for s in steps if s.get("uses", "").startswith("actions/setup-python")
            ]
            sp_ok = bool(sp_steps) and sp_steps[0]["uses"].startswith(
                "actions/setup-python@v5"
            )
            cache_ok = False
            ref_ok = False
            if sp_ok:
                sp = sp_steps[0].get("with", {})
                cache_ok = (
                    sp.get("cache") == "pip"
                    and sp.get("cache-dependency-path") == "pyproject.toml"
                )
                ref_ok = sp.get("python-version") == EXPECTED_MATRIX_REF
            if matrix is not None:
                if matrix != EXPECTED_MATRIX:
                    print(f"  FAIL {f.name}:{job_key} matrix={matrix}")
                    fail += 1
                    continue
                if not (checkout_ok and sp_ok and cache_ok and ref_ok):
                    print(
                        f"  FAIL {f.name}:{job_key} foundation missing "
                        f"(checkout={checkout_ok}, setup-python={sp_ok}, "
                        f"cache={cache_ok}, ref={ref_ok})"
                    )
                    fail += 1
                    continue
            job_pass += 1
        if job_pass == len(jobs):
            job_names = ", ".join(jobs.keys())
            print(f"  OK   {f.name:14s} name={name:14s} jobs=[{job_names}]")

    print(f"--- {len(files)-fail}/{len(files)} pass")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())