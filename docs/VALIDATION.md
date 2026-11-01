# SCBX Branch Validation - 1.0.1

## Native Desktop installation verification

On 2026-11-01 the repaired local PBIP loaded in Power BI Desktop 2.160.407.0.
A native refresh loaded 2,160 synthetic usage rows. The saved project reopened
with its local data cache, and all ten actual Desktop report pages had zero
visual errors. Verified values include 468.48 engineering spend, 34.00/39.04
personal spend and 0.0000 model reconciliation.

Native DAX probes reproduced errors for the reserved variable names `start`
and `scope` and verified their corrected forms. Native loading also required
the PBIR version file, `_Measures` instead of `Measures`, a quoted `Models`
reference and the built-in `columnChart` type.

The updated source passed 111 Python tests and 172 schema checks. This is
**local synthetic PBIP verification only**: the previous compiled PBIT load
issue is not claimed fixed, and no live source access, cloud workspace
deployment or actual recipient-user RLS was performed.

## Genuine native screenshot verification

All ten pages were captured again from the installed synthetic project on
2026-11-01. Each native report canvas was visually inspected before publication.
Recovery notices, selected-visual handles, the signed-in account, ribbon and
desktop were excluded. The original pixels were cropped, not reconstructed.

The [native provenance manifest](images/native/provenance.json) records page
titles, filters, pixel sizes, actual accessible sample values, zero visual errors
and SHA-256 hashes of every PNG. Native values include 56 operations work items,
960.00 scenario value and 0.0000 personal model reconciliation. The guide's
Partial card actually displays `(Blank)`; it has not been edited to show zero.

The [primary gallery](SAMPLE_DASHBOARD.md) and both installation manuals use the
ten genuine captures, with Thai captions available. The Node regression checks
verify image hashes/dimensions, native figure references in both languages and
the gallery, and recorded sample figures. They check the frozen artifacts, not
a new automated Desktop or tenant run in CI. PNG privacy review was visual;
the public-content scanner does not perform OCR.

### Final branch/publication checks

| Check | Verified result |
|---|---|
| Python regressions | 111 tests passing on Python 3.14 |
| Node manual/image regressions | 7 tests passing; native image hashes, both language variants and print-theme restoration |
| Official Power BI schemas | 172 schema-bearing files, Microsoft theme schema 2.159, zero errors |
| Genuine Desktop images | Ten report-canvas captures, all visually inspected; zero native visual errors |
| PDF screenshot integrity | Ten original native images in each PDF; embedded RGB pixels exactly match the original PNGs |
| English PDF | 16 pages; cover, portrait example and guide page visually inspected |
| Thai PDF | 20 pages; Thai rendering, native figures and cover/portrait/final-page layout visually inspected |
| Related local links | 94 links verified across eight updated documentation files |
| Public-content safety | 287 public source/documentation files inspected, zero errors; screenshots separately reviewed visually |

PDFs print with light pages while the HTML manual retains and restores its
screen theme. This publication updates the SCBX branch source, PNGs and manuals;
it does not replace the old binary release or certify its compiled PBIT.

## Archived SCBX theme/package checks before native repairs

The original **scbx-v1.0.1** variant passed **108 Python tests**, four Node manual tests,
**172 PBIR/schema checks** and Microsoft theme schema **2.159**.
The exact supplied theme settings are preserved and registered in PBIR.
The compiled PBIT contains the matching theme resource and binding, ten pages,
**156 visuals**, 22 tables and 101 measures.

The ten additional visuals are decorative gold header lines. Core measures,
security rules and synthetic CSV values are unchanged. Git normalized CSV line
endings in 21 embedded import payloads; this does not change their parsed values.

The installer preflight passed with a separate SCBX local folder and SCBX tenant
item display names. `main` remains separate. Original mockups/private source data
are not part of the branch.

Those package/schema checks did not prove native rendering, and the legacy PBIT
subsequently failed native loading. The repaired branch PBIP now has the local
synthetic Desktop evidence above. Real tenant acceptance remains unverified.
The neutral browser companion is a separate illustration. See [SCBX.md](SCBX.md).

## Original core code and installation recheck - 1.0.1

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

The CSV table count and model table count differ intentionally: 21 CSV
tables feed the model, plus the measure table makes 22 semantic-model tables.
The repaired native branch names that table `_Measures`.

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
| Actual Power BI Desktop rendering/refresh | Failed in the original core recheck; subsequently passed for the repaired SCBX synthetic PBIP as documented above |
| Legacy compiled PBIT native loading | Failed; the old binary is not certified by the new PBIP screenshots |
| Real Graph/GitHub source access and permissions | Not executed against a recipient tenant; collector tests use mock responses |
| Actual Fabric resource creation | Not performed in a recipient tenant; deployment tests verify request/response and error handling |
| Power BI Service credentials, gateway and scheduled refresh | Recipient setup and smoke test required |
| Actual Viewer RLS and app audiences | Must be tested with real authorized/unauthorized users in the recipient tenant |
| Enterprise performance or legal compliance | Not certified by unit tests, schema validation or the illustrations |

The native screenshots show the actual repaired PBIP rendering and DAX sample
values. The separate HTML companion does not run DAX or enforce authorization.
Neither the native sample nor the companion replaces live source, cloud
publication or recipient-user RLS acceptance tests.

Use the [Thai installation checklist](INSTALLATION_TH.md) or
[English installation guide](INSTALLATION.md) before production use.
