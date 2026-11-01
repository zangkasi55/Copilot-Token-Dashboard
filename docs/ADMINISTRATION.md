# Administrator and Operations Manual

## Security boundary

Personal UsageDaily and Accounts rows are restricted through the dynamic Viewer
role to the actual signed-in UPN. Organization pages read separate aggregate
tables without person identifiers. The pipeline publishes only eligible fixed
scopes, erases numeric facts on suppressed rows, and the Viewer role rejects
those rows again.

The cohort check also applies to billing-only personal contributions; a record
without an activity signal cannot turn a one-person billed amount into an
unsuppressed organization fact. Privacy-restricted people are excluded from
organization aggregate facts.

The default minimum is six. Changing group structure or policy requires a new
validated data generation and a data-protection review. This is not differential
privacy and does not eliminate all inference risks across overlapping scopes.

Workspace Admin, Member and Contributor permissions bypass RLS. Those accounts
are trusted data custodians, not normal consumers. App audience visibility and
hidden columns are usability features, not security controls.

## Source credentials

- Configure source apps inside the customer tenant.
- Use the least privilege required by the selected API.
- Store secrets in a secret manager or process environment.
- Never put access tokens, client secrets, private keys or actual employee
  exports into Git or the distribution ZIP.
- Presigned download links are sensitive and temporary. The downloader sends
  no API Authorization header to their host and does not log the link query.
- Fabric tokens are tenant-checked before provisioning.

## Daily refresh sequence

1. Collect each authorized source into an ignored runtime directory.
2. Normalize metadata and review source/identity coverage.
3. Build a new versioned gold-table folder.
4. Run production validation and reconcile monetary totals.
5. Upload the entire completed generation to the approved cloud data folder.
6. Refresh the semantic model only after upload completes.
7. Validate data-through dates, personal identity checks and scope availability.

Do not refresh while CSV files are being updated. Use scheduler dependencies or
a controlled complete-generation switch rather than concurrent writes.

For CSV sources in Power BI Service, configure an approved gateway. SharePoint
uses tenant-owned organizational OAuth credentials. Refresh permissions and
source permissions are separate from report-view permissions.

## Data quality

Version 1.0.1 checks the full CSV row width, singleton Settings and explicit
demo/suppression flags. Every modeled fact reference must resolve to its
dimension/calendar entry; an unsuppressed active cohort must meet the privacy
minimum. Do not bypass validation by marking an unsafe cohort as reportable.

Review Coverage.csv and the Data Quality page. Missing token fields mean
unavailable information, not zero consumption. Cache ratios are blank when the
cache coverage is incomplete. Actual billing amounts and estimated token prices
must remain distinguishable.

The model preserves undisclosed/unattributed dimensions. Known-spend subtotals
may not equal an invoice. Privacy-hidden breakdowns may not sum to an eligible
scope total; the difference is displayed instead of being silently discarded.

GitHub per-user billing collection covers users present in the requested daily
usage report. Reconcile against a complete billing export to include billing-only
or departed users.

## Privacy tests

- Test two actual UPNs under Viewer. Each sees only their own personal rows.
- Test an account with no mapping: it must not receive another person's data.
- Confirm unapproved scope IDs cannot be viewed.
- Confirm four-person sample scope rows are absent from published Scopes.csv.
- Confirm suppressed rows have null sensitive numbers, not just hidden visuals.
- Confirm no synthetic example.com identities exist in production.
- Review metadata contact fields; use shared team contacts rather than
  individual/private contact details.

## Upgrades and rollback

The 1.0.1 installer validates source settings before copying or provisioning and
resolves local CSV folders to absolute paths. Malformed Fabric item-listing
responses fail rather than being treated as an empty workspace.

Use a new version-specific local installation folder. Back up your current
report/model definitions and runtime configuration before tenant updates.
The tenant installer requires an explicit Update flag to replace an existing
item's definition.

For GitHub data that reports the same model under different selection modes,
reload affected authorized source reports and rebuild a complete generation.
Do not blindly merge old/new normalized exports. Records without a reported
selection mode retain their previous deterministic identifiers.

Keep your own credentials, RLS group assignments and source configuration outside
the release. A software update does not automatically complete those settings.
Rollback restores your approved prior definitions and data generation; do not
delete a workspace or user data to roll back a report.

## Alerts

The agent watch list exposes spend-spike flags. External Teams/email delivery is
not enabled automatically by this package. Use your approved scheduler or Fabric
Activator/automation to evaluate the validated outputs and notify appropriate
owners. Keep webhook URLs and credentials out of source control.

## Support evidence

Collect software version, sanitized HTTP status/request ID, source name,
schema error location, dataset refresh result and the failed installation stage.
Do not attach raw prompts, full presigned URLs, tokens, employee exports or
unreviewed screenshots to public GitHub issues.
