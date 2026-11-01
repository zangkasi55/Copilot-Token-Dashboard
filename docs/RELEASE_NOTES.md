# SCBX Theme Variant - 1.0.1 Public Preview

Branch/release: `scbx` / `scbx-v1.0.1`.

## SCBX branch update - native sample captures, 2026-11-01

- Published genuine report-canvas screenshots of all ten pages from Power BI
  Desktop 2.160.407.0, with synthetic data and no account chrome.
- Added Thai captions and replaced browser illustrations in both installation
  manuals with the native captures, including the portable PDFs.
- Included the PBIP repairs verified by native refresh, save and reopen:
  required PBIR version metadata, `_Measures`, safe DAX variable names,
  quoted `'Models'` references and the supported `columnChart` visual type.
- Recorded image hashes, actual sample values, dimensions and filters in
  [native provenance](images/native/provenance.json).
- Kept the neutral browser companion and `main` unchanged.

This is a repaired **branch source/documentation snapshot**, not a replacement
binary release. The earlier `scbx-v1.0.1` PBIT failed native loading; the
screenshots do not certify that old artifact or any live tenant integration.
Use the repaired branch PBIP as described in [SCBX setup](SCBX.md).

## Original SCBX theme release

- Applied the supplied SCBX Bright palette, typography and table/page styles.
- Added SCBX purple headers, white header text and ten gold header dividers.
- Registered the theme in PBIR and embedded it in the compiled PBIT.
- Preserved the core model, data contract, ten pages and six-person privacy rule.
- Used separate local-installation folders and SCBX tenant item display names.
- The original PDF/private source documents and real tenant data are not included.

See [SCBX.md](SCBX.md) for current setup and validation. The original release
used neutral browser illustrations; the updated branch gallery above now shows
actual SCBX Power BI rendering.

## Core Release 1.0.1 - Thai installation guide and code recheck

Public preview, updated 2026-11-01.

## Installation and documentation

- Expanded the Thai installation guide with executable checksum checks, direct
  PBIT and scripted PBIP paths, source/identity preparation, exact SharePoint
  configuration, refresh prerequisites and a production acceptance checklist.
- Retained all ten synthetic illustrations in the English and Thai PDFs.
- Added a validation report documenting executed tests and unverified live paths.
- The local installer and tenant deployer share source-parameter validation.
  Local CSV folders are saved as absolute paths; invalid SharePoint folders fail
  before copying a project or starting deployment.

## Code corrections and regression coverage

- Reject missing/duplicate Settings, ambiguous demo flags and incorrect CSV row
  widths.
- Validate modeled fact references and all numeric suppression fields, including
  weekly engagement bands.
- Reject unsuppressed small or invalid active cohorts.
- Include all thirteen completed weeks in Calendar for early-year builds.
- Preserve GitHub model-selection-mode record identities instead of colliding
  auto-selected and user-selected model entries.
- Reject truthy non-Boolean activity flags and cache-write counts above input.
- Fail explicitly when Fabric's item-listing response is malformed; valid empty
  listings and null end-of-pagination markers remain supported.

## Included capabilities

Ten Power BI pages, an editable 22-table/101-measure semantic model, compiled PBIT,
synthetic data, API collectors, metadata imports, privacy-filtered aggregates,
tenant deployment, English/Thai manuals and the offline synthetic sample.

## Validation boundaries

See [VALIDATION.md](VALIDATION.md) for the actual executed checks.
Local results: 102 Python tests and four Node tests passed, 162 Power BI
schema files validated, the PBIT compiled and its model metadata matched source,
and the installer preflight/local mocked-launch checks passed.
Automated API tests use synthetic/mock responses. They do not establish live
permissions, source availability, credentials, refresh or actual recipient RLS.
Local installer integration tests intercept the Desktop launch; they prove
copy/configuration/error handling, not successful Power BI rendering.

Interactive Desktop loading in the original managed authoring session did not
complete even for a one-table control project. This release does not claim that
Desktop rendering passed. Recipients must complete Desktop and own-tenant
acceptance checks before using the preview in production.

The illustrations are synthetic browser renderings, not verified Power BI
screenshots. Protected source documents, rights-protected Word outputs,
credentials and private dashboard data are not published.

## Previous releases

`v1.0.0` introduced the public preview. `v1.0.0-manuals.1` added the illustrated
manuals, ten-page gallery and self-contained sample without changing its runtime.
Those releases remain available; install 1.0.1 into a new version folder.
