# Cookbook — `storage/` Category

Recipes that exercise the **`client.storage` registry**
and the five storage backends (T01–T05 in
`012_STORAGE_SPECIFICATION.md`):

- T01 LOCAL_FILES — local filesystem.
- T02 JSON — JSON files.
- T03 CSV — CSV files.
- T04 PARQUET — Parquet files.
- T05 DUCKDB — embedded analytical database.

The storage layer is **read-only** from the Cookbook's
perspective: a `storage/` recipe consumes a dataset
that has been produced by a previous `trade/`,
`etl/`, or `end_to_end/` recipe, and renders it
through a backend.

## Purpose

A consumer should be able to read this category and
understand:

- How to open a `CanonicalDataset` from a Parquet /
  CSV / JSON / DuckDB / local-files path.
- How to read the dataset's metadata sidecar.
- How to round-trip a dataset through a backend
  (write → read → assert equality).
- How to partition a dataset (by reporter, by year,
  by HS chapter).
- How to update an existing dataset (append, replace,
  upsert).
- How to query a DuckDB dataset with SQL.

## SDK services exercised

| Service / symbol                                | Used in planned recipes |
| ----------------------------------------------- | ------------------------ |
| `client.storage.open()`                         | ✓                        |
| `client.storage.LocalFilesStorage`              | ✓                        |
| `client.storage.JSONStorage`                    | ✓                        |
| `client.storage.CSVStorage`                     | ✓                        |
| `client.storage.ParquetStorage`                 | ✓                        |
| `client.storage.DuckDBStorage`                  | ✓                        |
| `client.storage.PartitionStrategy`              | ✓                        |
| `client.storage.DatasetUpdater`                 | ✓                        |
| `client.storage.UpdateMode`                     | ✓                        |
| `client.storage.DuplicatePolicy`                | ✓                        |
| `client.storage.verify_schema_compatibility()`  | ✓                        |

## API key policy

| `requires_api_key` | Default for this category |
| ------------------ | ------------------------- |
| `no`               | ✓ (per `recipes/README.md` §8.2) |

The "storage" category is **read-only by design**: a
pure storage recipe consumes a dataset that has
already been produced by a previous `trade/`,
`etl/`, or `end_to_end/` recipe, and renders it
through a backend. Pure storage recipes do not call
the network and so declare `requires_api_key: no`.

A storage recipe that *also* produces the input
dataset inline (i.e. its `main()` calls
`client.trade`) declares `requires_api_key: yes`
and explains the reason in its frontmatter.
The current batch ships 4 such recipes
(`RECIPE-031` through `RECIPE-034`); they exist so
a one-liner user invocation works without a separate
fetch recipe. A consumer who wants the pure-storage
contract can use the recipes' `*_demo(...)` seams
directly, passing in a pre-built `TradeResponse` or
`CanonicalDataset`.

## Estimated runtime band

| `estimated_runtime` | Typical recipes in this category                  |
| ------------------- | ------------------------------------------------- |
| `<1s`               | in-memory round-trip of a small dataset           |
| `<10s`              | read or write a 100k-record dataset               |
| `<1min`             | read or write a multi-million-record dataset      |
| `1-10min`           | rebuild a partitioned dataset from scratch        |

The dominant cost is deserialisation (read) or
serialisation (write). Parquet and DuckDB are the
fastest; CSV and JSON are the slowest.

## Shipped recipe roster (CB-005 batch 1)

| Recipe ID    | File                                | Title                                                                 | Difficulty      | Runtime   | API key |
| ------------ | ----------------------------------- | --------------------------------------------------------------------- | --------------- | --------- | ------- |
| `RECIPE-031` | `01_etl_pipeline.py`                | Run a 3-stage ETL pipeline (extract → transform → load)               | intermediate    | `<1min`   | yes     |
| `RECIPE-032` | `02_export_csv.py`                  | Export a `TradeResponse` to CSV                                       | beginner        | `<1min`   | yes     |
| `RECIPE-033` | `03_export_parquet.py`              | Export a `TradeResponse` to Parquet (partitioned, with codec)         | intermediate    | `<1min`   | yes     |
| `RECIPE-034` | `04_export_duckdb.py`               | Export a `TradeResponse` to a DuckDB database (replace / append)      | intermediate    | `<1min`   | yes     |
| `RECIPE-035` | `05_reload_storage.py`              | Reload a stored dataset back into a `CanonicalDataset`                | beginner        | `<30s`    | no      |
| `RECIPE-036` | `06_analytics_on_stored.py`         | Run analytics on a stored dataset (round-trip)                        | intermediate    | `<30s`    | no      |

**Coverage of the four Cookbook pillars:**

- **Authentication** — recipes 031-034 declare `requires_api_key: yes`
  because their `main()` fetches via `client.trade`. Recipes 035-036
  are key-free (`no`) because their `main()` either reads from an
  existing dataset (035) or runs analytics locally (036).
- **Filtering** — each export recipe takes `--reporter`,
  `--period`, and `--flow` so the user can target a specific
  reporter + year + flow without rewriting the recipe.
- **Output formats** — the three backend writers (CSV, Parquet,
  DuckDB) cover the three documented persistence formats. Recipe
  035 round-trips through all three; recipe 036 reads the DuckDB
  file directly via `duckdb.connect(read_only=True)`.
- **Error handling** — every recipe's `main()` catches the full
  `ComtradeError` hierarchy and maps to a documented exit code
  (CB-001 §6.4 contract: 3 validation, 4 auth, 5 rate-limit,
  6 network, 7 server, 8 API/business-rule).

## Planned recipe roster

The following recipes are planned for future batches
(RECIPE-070..083) and have not yet been shipped. They cover
specialised scenarios (per-format openers, partitioning strategies,
update modes, dedup, schema verification, sidecar reading).

| Recipe ID     | Title                                                                    | Difficulty      | Runtime   | API key |
| ------------- | ------------------------------------------------------------------------ | --------------- | --------- | ------- |
| `RECIPE-070`  | Open a `CanonicalDataset` from a Parquet file                            | beginner        | `<1s`     | no      |
| `RECIPE-071`  | Open a `CanonicalDataset` from a CSV file                                | beginner        | `<1s`     | no      |
| `RECIPE-072`  | Open a `CanonicalDataset` from a JSON file                               | beginner        | `<1s`     | no      |
| `RECIPE-073`  | Open a `CanonicalDataset` from a DuckDB file                             | beginner        | `<1s`     | no      |
| `RECIPE-074`  | Round-trip a dataset through Parquet (write → read → assert)              | intermediate    | `<10s`    | no      |
| `RECIPE-075`  | Round-trip a dataset through DuckDB (write → read → assert)               | intermediate    | `<10s`    | no      |
| `RECIPE-076`  | Partition a dataset by reporter and write to Parquet                     | intermediate    | `<1min`   | no      |
| `RECIPE-077`  | Partition a dataset by year and write to DuckDB                          | intermediate    | `<1min`   | no      |
| `RECIPE-078`  | Append records to an existing dataset (`UpdateMode.append`)              | intermediate    | `<10s`    | no      |
| `RECIPE-079`  | Replace records in an existing dataset (`UpdateMode.replace`)            | intermediate    | `<10s`    | no      |
| `RECIPE-080`  | Deduplicate a dataset (`DuplicatePolicy`)                                | intermediate    | `<10s`    | no      |
| `RECIPE-081`  | Query a DuckDB dataset with SQL                                          | intermediate    | `<1s`     | no      |
| `RECIPE-082`  | Verify schema compatibility before update                                | intermediate    | `<1s`     | no      |
| `RECIPE-083`  | Read the metadata sidecar of a stored dataset                            | beginner        | `<1s`     | no      |

## Per-recipe cross-references

A `storage/` recipe that needs to explain a behaviour
links to:

- `docs/007_SDK_SPECIFICATION.md` §3.4 (storage
  surface)
- `docs/012_STORAGE_SPECIFICATION.md`
- `docs/024_STORAGE_REVIEW_REPORT.md` (the design
  history of the storage layer)
- `docs/006_DATA_MODEL.md` (the schema that the
  storage layer preserves)

## Category-specific notes

- **Backends are interchangeable.** A consumer who
  learns the Parquet backend should be able to switch
  to DuckDB by changing the URI. Recipes that
  demonstrate a backend use a single, canonical
  example (a 100-row `CanonicalDataset`).
- **Metadata sidecar is mandatory.** Every storage
  write produces a `<file>.meta.json` sidecar. A
  `storage/` recipe that produces a sidecar is a
  complete recipe; a `storage/` recipe that omits
  the sidecar is rejected.
- **Decimal preservation is non-negotiable.** Parquet
  and DuckDB writes preserve `Decimal` precision
  (ADR-0027). A recipe that round-trips a `Decimal`
  field through CSV (which converts to `float` by
  default) is rejected. Recipes that need to write
  Decimal through CSV MUST use the
  `un_comtrade.storage.csv` writer (not
  `pandas.to_csv`).
- **Partitioning is logical, not physical.** A
  recipe that physically partitions a directory tree
  is rejected; the SDK uses logical partitioning
  (one file per partition key).

## How to add a recipe to this category

1. Choose the next free `RECIPE-NNN` ID from the
   roster above.
2. Copy `recipes/_TEMPLATE.py` to
   `recipes/storage/RECIPE_NNN_<slug>.py`.
3. Implement the body per `recipes/_TEMPLATE.md`. The
   body MUST:
   - Set `requires_api_key: no` in the frontmatter.
   - Operate on a `CanonicalDataset` (loaded from a
     file or built in-memory).
   - Use a documented SDK storage backend, not a
     third-party writer.
4. Update this README's roster table.
5. Submit a pull request.

A recipe that fetches trade data and then writes it
to a storage backend belongs in `end_to_end/`, not
here.
