# Cookbook — `metadata/` Category

Recipes that exercise the **`client.metadata` service** —
the reference catalogue for countries, partners,
classifications, HS codes, trade flows, transport modes,
quantity units, frequencies, and data items (M01–M18
in `007_SDK_SPECIFICATION.md` §3.4).

## Purpose

A consumer should be able to read this category and
understand:

- How to fetch any reference catalogue.
- How the cache works (and how to refresh it).
- How to look up a single entity by code.
- How to search the HS nomenclature.
- How to combine metadata across categories.

## SDK services exercised

| Service / symbol                          | Used in planned recipes |
| ----------------------------------------- | ------------------------ |
| `client.metadata.get_countries()`         | ✓                        |
| `client.metadata.get_country()`           | ✓                        |
| `client.metadata.get_partners()`          | ✓                        |
| `client.metadata.get_partner()`           | ✓                        |
| `client.metadata.get_classifications()`   | ✓                        |
| `client.metadata.get_classification()`    | ✓                        |
| `client.metadata.get_hs_codes()`          | ✓                        |
| `client.metadata.get_hs_code()`           | ✓                        |
| `client.metadata.search_hs()`             | ✓                        |
| `client.metadata.get_trade_flows()`       | ✓                        |
| `client.metadata.get_transport_modes()`   | ✓                        |
| `client.metadata.get_quantity_units()`    | ✓                        |
| `client.metadata.get_frequencies()`       | ✓                        |
| `client.metadata.get_data_items()`        | ✓                        |
| `client.metadata.get_metadata()`          | ✓                        |

## API key policy

| `requires_api_key` | Default for this category |
| ------------------ | ------------------------- |
| `no`               | ✓ (per `recipes/README.md` §8.2) |

A recipe in this category that needs a key MUST declare
`requires_api_key: yes` in its frontmatter and explain
the reason in the recipe's long-form description.

## Estimated runtime band

| `estimated_runtime` | Typical recipes in this category |
| ------------------- | --------------------------------- |
| `<1s`               | catalogue fetch with warm cache   |
| `<10s`              | catalogue fetch with cold cache   |

A cold cache adds one or two seconds per catalogue
fetch; recipes that fetch multiple catalogues in
sequence fall in the `<10s` band.

## Planned recipe roster

| Recipe ID     | Title                                                                  | Difficulty      | Runtime | API key | Status   | Source file                  |
| ------------- | ---------------------------------------------------------------------- | --------------- | ------- | ------- | -------- | ---------------------------- |
| `RECIPE-001`  | List reporter countries with ISO-2 / ISO-3 codes                       | beginner        | `<1s`   | no      | DRAFT    | `01_list_countries.py`       |
| `RECIPE-002`  | List partner countries with ISO-2 / ISO-3 codes                        | beginner        | `<1s`   | no      | DRAFT    | `02_list_partners.py`        |
| `RECIPE-003`  | List HS commodity codes for an edition (chapter → heading → subheading)| beginner        | `<10s`  | no      | DRAFT    | `03_list_hs_codes.py`        |
| `RECIPE-004`  | Search HS commodity codes by keyword                                   | beginner        | `<1s`   | no      | DRAFT    | `04_search_hs.py`            |
| `RECIPE-005`  | Refresh the metadata cache                                             | beginner        | `<1s`   | no      | DRAFT    | `05_refresh_metadata.py`     |
| `RECIPE-006`  | Look up a single country by reporter code                              | beginner        | `<1s`   | no      | PROPOSED | —                            |
| `RECIPE-007`  | List trade flows (export / import / re-export / ...)                   | beginner        | `<1s`   | no      | PROPOSED | —                            |
| `RECIPE-008`  | List transport modes, quantity units, frequencies                      | beginner        | `<1s`   | no      | PROPOSED | —                            |
| `RECIPE-009`  | Walk the HS chapter / heading / subheading tree                        | intermediate    | `<10s`  | no      | PROPOSED | —                            |
| `RECIPE-010`  | Build a country → ISO-3 lookup table for downstream use                | intermediate    | `<1s`   | no      | PROPOSED | —                            |

**CB-002 (DRAFT).** Recipes `RECIPE-001` through `RECIPE-005` are the
first batch of beginner metadata recipes. They are
**DRAFT**: the code compiles, the test suite
(`tests/test_recipes_metadata.py`, 12 tests) is green,
and the on-screen output has been smoke-checked against
the recorded fixtures. The recipes are not yet
**STABLE** because they have not been exercised against
the live upstream API in CI.

**Note on file naming.** CB-001 §3.1 specified the
naming convention `RECIPE_NNN_<slug>.py`. CB-002
**deviates** from that convention and uses the shorter
`NN_<slug>.py` form (zero-padded two-digit index,
no `RECIPE_` prefix). The recipe IDs in the frontmatter
still use the canonical `RECIPE-NNN` form. See the
closing notes in the CB-002 delivery report for the
rationale and the proposed amendment to CB-001.

## Per-recipe cross-references

A `metadata/` recipe that needs to explain a behaviour
links to the relevant `docs/` page. The pages most often
referenced from this category are:

- `docs/007_SDK_SPECIFICATION.md` §3.4 (M01–M18)
- `docs/008_METADATA_LAYER_SPEC.md`
- `docs/010_INFRASTRUCTURE_SPEC.md` §3 (configuration;
  cache directory)
- `docs/003_ARCHITECTURE.md` §5.3 (L3 metadata layer)

## Category-specific notes

- **Cache is a first-class concern.** Recipes that
  demonstrate the cache (`RECIPE-009` etc.) MUST print
  the cache state (warm / cold, size) at the start of
  the run. The cache directory is `UN_COMTRADE_CACHE_DIR`
  (default `~/.cache/un_comtrade`).
- **Search is fuzzy.** `client.metadata.search_hs()`
  performs a tokenised search; the recipe that
  demonstrates it (`RECIPE-005`) prints a side-by-side
  comparison of the search results and the exact
  matches.
- **No side effects.** Recipes in this category are
  read-only. They MUST NOT write to the trade data
  store. The only write a metadata recipe performs is
  the cache fill.

## How to add a recipe to this category

1. Choose the next free `RECIPE-NNN` ID from the
   roster above. If the recipe is not on the roster,
   add it to the roster first.
2. Copy `recipes/_TEMPLATE.py` to
   `recipes/metadata/RECIPE_NNN_<slug>.py`.
3. Implement the body per `recipes/_TEMPLATE.md`.
4. Update this README's roster table with the new
   recipe's status (`PROPOSED` → `DRAFT` → `STABLE`).
5. Submit a pull request.

A recipe that does not match the catalogue surface is
not a `metadata/` recipe and belongs in another
category (most likely `end_to_end/`).
