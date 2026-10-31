# Public Product Requirements

This document describes this independently authored public reference package,
not a customer's confidential business requirements or approval record.

## Functional requirements

1. Install repeatably into a recipient's own tenant/workspace without embedded
   tenant IDs, credentials or shared backend.
2. Provide ten editable Power BI pages and an explicit synthetic demonstration.
3. Keep personal records self-only for Viewer consumers.
4. Use separate fixed-scope aggregates, minimum six, with suppression before
   model loading and repeated RLS protection.
5. Preserve source-specific metric units, periods, missing fields, undisclosed
   models and unattributed billing.
6. Collect current documented GitHub and Microsoft 365 metadata through an
   external pipeline rather than unsupported Graph calls from Power Query.
7. Accept approved normalized gateway, credit, audit, billing and outcome inputs.
8. Distinguish billed amounts, estimates and value scenarios.
9. Stop explicitly on schema, consent, source or deployment failures.
10. Supply English/Thai installation material, operating boundaries and
    reproducible validation/release checks.

## Acceptance checks

- All public report JSON files conform to official schemas.
- All pages/field references and model relationships are present.
- The actual semantic model serializer accepts generated metadata.
- Demo data build validates all contract tables and rejects production demo data.
- No monetary or token facts remain in suppressed aggregate records.
- Token counters retain integer precision and missing cache remains unknown.
- Actual billing net amounts are used and overlapping usage totals are not added.
- Per-tenant token mismatch and blind overwrites stop provisioning.
- Public artifacts contain no private source documents, customer records,
  credentials or protected-office containers.

Local/offline checks do not establish an arbitrary enterprise performance SLA or
prove live access to every vendor API. Tenant administrators complete source,
license, refresh and Viewer acceptance tests in their own environment.
