"""Great Expectations gate: validate raw Bigtable product rows before BigQuery load.

This is the "front door" guard for Option B of the pipeline:

    scrapers -> Bigtable (raw) -> [THIS GATE] -> bq load -> raw products -> dbt

It is imported and called by ``scrapers/bigtable_to_bigquery.py`` right before the
``load_table_from_file`` call. It can also be run standalone for ad-hoc checks.

Critical expectations BLOCK the load (return ok=False). Soft expectations only
warn (collected in ``result.warnings``) so a single weird row never halts the
whole batch.

GE 1.x API. Everything in Bigtable arrives as a string, so most checks are
regex / null / set membership. Numeric range checks run on a derived numeric
column parsed from ``current_price``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd
import great_expectations as gx

# --- domain config -----------------------------------------------------------

KNOWN_STORES = ["ebay", "jumia", "sport-direct"]
PRICE_MIN = 0.0          # exclusive lower bound
PRICE_MAX = 100_000.0    # MAD; kills the ~1.8M parse-error outlier
NAME_MAX_LEN = 300
SINGLE_NUMBER_RE = r"^\d+(\.\d+)?$"   # rejects jumia range strings "189.00 - 299.00"
URL_RE = r"^https?://"

_PRICE_EXTRACT_RE = re.compile(r"\d+(?:\.\d+)?")


@dataclass
class GateResult:
    ok: bool
    n_rows: int
    failures: list[str] = field(default_factory=list)   # critical -> blocks load
    warnings: list[str] = field(default_factory=list)   # soft -> logged only

    def summary(self) -> str:
        lines = [f"GE gate: {self.n_rows} rows, ok={self.ok}"]
        for f in self.failures:
            lines.append(f"  BLOCK  {f}")
        for w in self.warnings:
            lines.append(f"  warn   {w}")
        return "\n".join(lines)


def _to_frame(products: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(products)
    # guarantee the columns the suite references exist, even if a batch lacks them
    for col in ["name", "current_price", "store", "source", "product_url",
                "scraped_at", "stars", "discount", "image_url", "category"]:
        if col not in df.columns:
            df[col] = None
    # store can be empty -> fall back to source (mirrors bigtable_to_bigquery)
    df["store"] = df["store"].where(df["store"].astype(str).str.len() > 0, df["source"])

    def _price_num(v):
        if v is None:
            return None
        m = _PRICE_EXTRACT_RE.search(str(v))
        return float(m.group()) if m else None

    df["_price_num"] = df["current_price"].map(_price_num)
    return df


def _crit(suite, expectation):
    suite.add_expectation(expectation)


def validate_products(products: list[dict], *, strict: bool = True) -> GateResult:
    """Validate a list of raw Bigtable product dicts.

    Args:
        products: rows as read from Bigtable (string values).
        strict: if True, soft/warn expectations are still evaluated but never
            flip ``ok``. Critical expectations always gate ``ok``.

    Returns:
        GateResult with ok flag, failure list (blocking), warning list.
    """
    if not products:
        return GateResult(ok=True, n_rows=0)

    df = _to_frame(products)
    context = gx.get_context(mode="ephemeral")
    asset = context.data_sources.add_pandas("dq").add_dataframe_asset("products")
    batch_def = asset.add_batch_definition_whole_dataframe("batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    E = gx.expectations

    # --- critical suite: any failure blocks the BQ load ----------------------
    critical = gx.ExpectationSuite(name="pre_bq_products_critical")
    _crit(critical, E.ExpectColumnValuesToNotBeNull(column="name"))
    _crit(critical, E.ExpectColumnValueLengthsToBeBetween(
        column="name", min_value=1, max_value=NAME_MAX_LEN))
    _crit(critical, E.ExpectColumnValuesToNotBeNull(column="current_price"))
    _crit(critical, E.ExpectColumnValuesToMatchRegex(
        column="current_price", regex=SINGLE_NUMBER_RE))
    _crit(critical, E.ExpectColumnValuesToBeBetween(
        column="_price_num", min_value=PRICE_MIN, max_value=PRICE_MAX,
        strict_min=True))
    _crit(critical, E.ExpectColumnValuesToBeInSet(
        column="store", value_set=KNOWN_STORES))
    _crit(critical, E.ExpectColumnValuesToNotBeNull(column="scraped_at"))

    crit_res = batch.validate(critical)

    # --- soft suite: warnings only ------------------------------------------
    soft = gx.ExpectationSuite(name="pre_bq_products_soft")
    soft.add_expectation(E.ExpectColumnValuesToNotBeNull(column="category"))
    soft.add_expectation(E.ExpectColumnValuesToMatchRegex(
        column="product_url", regex=URL_RE, mostly=0.95))
    soft.add_expectation(E.ExpectColumnValuesToMatchRegex(
        column="discount", regex=r"^\d+%$", mostly=0.90))
    soft.add_expectation(E.ExpectColumnValuesToMatchRegex(
        column="image_url", regex=URL_RE, mostly=0.90))
    soft_res = batch.validate(soft)

    failures = [
        r["expectation_config"]["type"]
        for r in crit_res["results"] if not r["success"]
    ]
    warnings = [
        r["expectation_config"]["type"]
        for r in soft_res["results"] if not r["success"]
    ]

    return GateResult(
        ok=len(failures) == 0,
        n_rows=len(df),
        failures=failures,
        warnings=warnings,
    )


if __name__ == "__main__":
    # smoke test with synthetic good + junk rows
    sample = [
        {"name": "Whey Protein 1kg", "current_price": "299.00", "store": "ebay",
         "source": "ebay", "product_url": "https://ebay.com/x", "scraped_at": "2026-06-01T10:00:00Z",
         "category": "protein", "discount": "10%", "image_url": "https://img/x.jpg"},
        {"name": "", "current_price": "", "store": "unknown",            # junk
         "source": "unknown", "product_url": "n/a", "scraped_at": ""},
        {"name": "Range Item", "current_price": "189.00  - 299.00", "store": "jumia",  # range string
         "source": "jumia", "product_url": "https://jumia/y", "scraped_at": "2026-06-01T10:00:00Z"},
    ]
    res = validate_products(sample)
    print(res.summary())
    raise SystemExit(0 if res.ok else 1)
