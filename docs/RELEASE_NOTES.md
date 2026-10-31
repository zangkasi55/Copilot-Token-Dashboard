# Release 1.0.0

Initial independently authored public preview release.

- Ten Power BI pages, editable model and explicit synthetic data.
- Separate self-only personal facts and privacy-filtered organization aggregates.
- Billing-only personal contributions also respect the cohort minimum;
  privacy-restricted people are excluded from organization aggregate facts.
- Current GitHub client/model token metrics, net billed amounts and distinct
  premium-request/AI-credit units.
- Microsoft 365 v2 period/activity collection and minimal Entra export.
- Metadata imports for owned gateway, credit, audit and FOCUS exports.
- Explicit unknown cache/price/attribution states.
- Uncached-input derivation requires reported cache-read and cache-write coverage.
- Tenant-scoped Fabric provisioning with safe model/report binding and operation
  polling; manual RLS/credential/refresh steps remain explicit.
- English and Thai installation manuals plus administrator, capability,
  data-contract and user documentation.

Public manuals are distributed in Markdown and PDF. Rights-protected Word
outputs from a managed authoring environment are not published or unprotected.

## Validation boundaries

Automated API tests use synthetic/mock responses. They do not establish live
permissions or vendor payload availability inside a recipient's tenant.
Recipients must complete source, license, refresh and Viewer smoke tests.

Interactive Power BI Desktop loading did not complete in the managed authoring
session, including for an isolated one-table control project. The semantic model
serializer, official JSON schemas, compiled PBIT package parts/counts, offline
tests, installer preflight and public-content checks passed. Interactive Desktop
and recipient-tenant validation are not claimed as passed; do not use the preview
in production until those checks pass in your own environment.

This release does not provide automatic tenant-wide credential grants, paid
licenses, invoice posting, employee ranking, or automatic Teams/email alerts.
Sovereign-cloud endpoints and custom GitHub hosts are not validated.
