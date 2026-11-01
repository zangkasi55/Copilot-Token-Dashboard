# Code and Installation Recheck - 1.0.1

Recheck date: **2026-11-01**. Release channel: **public preview**.

## Executed local checks

| Check | Result and scope |
|---|---|
| Python regression suite | 102 tests passing on Python 3.14; no live tenant credentials used |
| Node manual-renderer suite | 4 tests passing, including all ten embedded figures per language |
| Power BI JSON schemas | 162 schema-bearing files validated with zero errors |
| Semantic model serializer | Generated model accepted and serialized to TMDL |
| Actual compiled PBIT | 10 pages, 146 visuals, 22 tables and 101 measures verified inside the package |
| Template/source equivalence | All compiled table columns/types and 101 measure expressions match the source metadata |
| Python distribution | 1.0.1 wheel built from the declared package metadata |
| Installer Validate | Passed for all 21 CSV contract tables and source configuration; created no tenant resources |
| Local CSV installation | Executed copy/absolute-path/model-configuration flow with synthetic data; Desktop launch intercepted |
| Invalid SharePoint configuration | Rejected before a local installation directory or report launch was created |
| Existing installation | Rejected without overwriting its sentinel file |
| Thai checksum instructions | Extracted command executed: matching SHA-256 passed, mismatching SHA-256 failed |
| Synthetic data rebuild | 2,160 usage rows, three eligible scopes, anchor 2026-05-28; contract validation passed |
| Editor diagnostics | No reported errors in the package, tooling and tests |
| Thai illustrated PDF | 19 pages with all ten embedded screenshots; cover and final page visually inspected |
| English illustrated PDF | 16 pages with all ten embedded screenshots; content/version checks passed |

The Power BI row count and model table count differ intentionally: 21 CSV
tables feed the model, plus its Measures table makes 22 semantic-model tables.

## Failures reproduced before fixing

The original 57 Python and four Node tests passed. New negative-control tests
exposed previously untested cases; **23 new regressions failed before the
corresponding fixes**.

- Missing/duplicate Settings and ambiguous demo flags were accepted.
- Incorrect CSV row widths and unknown modeled fact references were accepted.
- Small unsuppressed cohorts and retained weekly suppression counts were not
  rejected.
- Early-January builds did not include all completed-week dates in Calendar.
- Auto-selected and user-selected instances of the same GitHub model reused an
  event identifier.
- Non-Boolean activity flags and excessive cache-write counts were accepted.
- A malformed Fabric item listing was treated as empty or raised an incidental
  attribute/type error.

These cases now have regression coverage and explicit errors. Existing GitHub
model entries without selection mode retain their identifiers.

## Reproducible commands

Run from the extracted project or repository using the intended Python
environment and PowerShell 7:

```powershell
python -m pip install ".[dev]"
python -m pytest -q tests
npm ci --ignore-scripts
npm run test:manuals
.\Install.ps1 -Action Validate
python tools\validate_powerbi.py
python -m pip wheel . --no-deps --wheel-dir .work\wheel
```

With the declared official pbi-tools core compiler restored:

```powershell
.\tools\Build-PowerBI.ps1
```

The GitHub validation workflow runs the package checks on Python **3.10, 3.12
and 3.14**. Refer to [GitHub Actions](https://github.com/zangkasi55/Copilot-Token-Dashboard/actions)
for the executed status of each published commit; local checks alone do not
prove every matrix environment.

## Deliberately unverified live paths

| Check | Status |
|---|---|
| Actual Power BI Desktop rendering/refresh | Not passed in this recheck. The previous managed Desktop session stalled even on a control project |
| Real Graph/GitHub source access and permissions | Not executed against a recipient tenant; collector tests use mock responses |
| Actual Fabric resource creation | Not performed in a recipient tenant; deployment tests verify request/response and error handling |
| Power BI Service credentials, gateway and scheduled refresh | Recipient setup and smoke test required |
| Actual Viewer RLS and app audiences | Must be tested with real authorized/unauthorized users in the recipient tenant |
| Enterprise performance or legal compliance | Not certified by unit tests, schema validation or the illustrations |

The sample screenshots and HTML demonstrate synthetic report concepts. They do
not run DAX or enforce authorization and are not substituted for a Desktop or
tenant acceptance test.

Use the [Thai installation checklist](INSTALLATION_TH.md) or
[English installation guide](INSTALLATION.md) before production use.
