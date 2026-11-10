"""No real brand names anywhere, and model output is scrubbed before it is stored or scored."""

import subprocess
import sys

import check_brands
from conftest import ROOT

TERM = "Zorblax Industries"  # made-up name, hashed here so the test needs no real brand
HASHES = {"term_hashes": {check_brands.digest(TERM.lower())}, "spelling_hashes": {check_brands.digest(TERM)}}


def test_scrub_is_deterministic_keeps_word_count_and_is_idempotent():
    text = f"Ask {TERM} about pallets. {TERM} said yes."
    out, n = check_brands.scrub(text, **HASHES)
    assert n == 2 and TERM not in out and len(out.split()) == len(text.split())
    assert check_brands.scrub(text, **HASHES)[0] == out and check_brands.scrub(out, **HASHES) == (out, 0)


def test_no_file_is_excluded_from_the_brand_check():
    assert check_brands.SKIP == set()


def test_whole_repository_is_brand_clean():
    r = subprocess.run([sys.executable, "scripts/check_brands.py"], cwd=ROOT, capture_output=True, text=True,
                       check=False)
    assert r.returncode == 0, r.stdout
