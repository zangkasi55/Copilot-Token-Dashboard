# Copilot Token Dashboard

A tenant-owned Power BI installation package for AI usage, token consumption,
spend, agent operations, and data-quality reporting.

**Release status: public preview.** See the release notes for the exact validation
results and required interactive Desktop/recipient-tenant smoke tests.

This is an independent open-source project. It is not an official Microsoft or
GitHub product and does not include access to Microsoft-internal telemetry.

## What you install

- A ten-page Power BI project with an editable semantic model.
- An explicitly marked synthetic demonstration dataset.
- Tenant-targeted deployment and configuration scripts.
- API collectors and a normalized CSV ingestion pipeline.
- English and Thai installation manuals and administrator documentation.

## Important boundaries

- Each organization supplies its own tenant, workspace, credentials and data.
- Power BI Desktop is free; publishing and sharing require appropriate Power BI
  or Fabric licensing and workspace permissions.
- GitHub's current APIs expose some client/model token counts, but cache details
  are not universally available. Microsoft 365 reports provide activity and
  period summaries, not general per-model token billing.
- Missing tokens, unpriced usage, attribution gaps and suppressed groups are
  not silently converted to zero.
- Organization reporting uses separate aggregate facts. Personal records remain
  self-only under the Viewer role. Workspace administrators bypass Power BI RLS
  and must be treated as trusted data custodians.
- Usage and estimated value are not employee-performance measures.

See the installation and operations documentation in `docs/`.

## Quick start

1. Download the installation ZIP from
   [Releases](https://github.com/zangkasi55/Copilot-Token-Dashboard/releases).
2. Verify the SHA-256 checksum and extract into a new folder.
3. Run `.\Install.ps1 -Action Validate -InstallDependencies`.
4. Run `.\Install.ps1 -Action Local -SourceMode Demo`, or open the included PBIT
   in Power BI Desktop and choose Demo.
5. To provision into your own tenant, follow the explicit tenant/workspace,
   credential, RLS and refresh steps in the installation guide.

The tenant command provisions definitions; it does not silently grant source
consent, issue licenses, assign RLS groups or declare production readiness.

## Manuals

- [Installation guide](docs/INSTALLATION.md)
- [คู่มือการติดตั้งภาษาไทย](docs/INSTALLATION_TH.md)
- [Administrator and operations manual](docs/ADMINISTRATION.md)
- [Data sources and API limits](docs/DATA_SOURCES.md)
- [Data contract](docs/DATA_CONTRACT.md)
- [User guide](docs/USER_GUIDE.md)
- [Public requirements](docs/REQUIREMENTS.md)
- [Release notes](docs/RELEASE_NOTES.md)

Portable PDF installation guides are in `docs/manuals/`. Rights-protected Word
outputs are not uploaded. No protected or customer-branded source documents,
actual employee records or private internal dashboard exports are distributed.

## Development checks

```powershell
python -m pip install ".[dev]"
npm ci --ignore-scripts
python -m pytest -q tests
ctd demo --output sample_data --scratch .work\demo-inputs
python tools\build_powerbi.py
python tools\validate_powerbi.py
npm run docs
python tools\publication_check.py
```

The Power BI template compiler uses the declared optional pbi-tools **core**
build utility. That utility is not bundled. The generated PBIT is inspected for
the required package parts and complete page/model counts before release.

With the official core compiler restored to the declared tool location, run
`.\tools\Build-PowerBI.ps1`. Each build uses a new ignored scratch folder,
validates the official report schemas, serializes the semantic model, compiles
the PBIT, and checks its actual report/model contents.
