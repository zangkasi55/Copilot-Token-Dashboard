# Installation Guide

## 1. What this package does

Copilot Token Dashboard is a tenant-owned Power BI reference application. It
provides ten report pages for personal usage, organization aggregates, agent
operations, models, value scenarios, budgets and data quality.

It does not grant access to another organization's data. Every recipient uses
their own Microsoft tenant, Power BI workspace, source permissions and secrets.
The installation demonstration is synthetic and is marked on every page.

## 2. Prerequisites

| Component | Required for |
|---|---|
| Windows and recent Power BI Desktop | Local report authoring and validation |
| Python 3.10 or later | Collectors, normalized-data build and deployment |
| PowerShell 7 | Installation script |
| Power BI Pro, PPU or suitable Fabric capacity | Publishing and sharing, as required by Microsoft licensing |
| Workspace Contributor or higher | Provisioning semantic model and report |
| Azure CLI, or a tenant-scoped Fabric token in your process environment | Automated tenant provisioning |
| Approved source permissions | Collecting actual organizational usage and billing data |

The supplied API origins target Microsoft's global commercial cloud. Sovereign
clouds and custom GitHub hosts are not validated by this release.

Power BI Desktop and optional build utilities are not redistributed.

## 3. Download and validate

Download the versioned installation ZIP from the GitHub Releases page. Verify its
SHA-256 checksum against the release checksum file, then extract it into a new
folder, for example `C:\CopilotTokenDashboard`.

```powershell
Set-Location C:\CopilotTokenDashboard
.\Install.ps1 -Action Validate -InstallDependencies
```

This restores only the declared runtime dependencies and validates the complete
synthetic table set. No tenant resources are created in Validate mode.

Expected result: the validation reports all contract tables and no errors.

Do not disable enterprise execution policies or security controls to run the
script. Follow your organization's approved script-execution process.

## 4. Open the demonstration locally

```powershell
.\Install.ps1 -Action Local -SourceMode Demo
```

The script creates a new version-specific folder under your local application
data and opens the PBIP. An existing installation folder is not overwritten.
Use `-InstallFolder C:\CTD\Demo-1.0.0` to choose a new folder.

In Power BI Desktop:

1. Wait for the project to open.
2. Select Refresh if the data is not yet loaded.
3. Confirm the synthetic-demo banner and data-through date.
4. Visit all ten report pages.
5. Use the Agent selector or drill-through configuration for a single agent.
6. Open Modeling > View as and test the Viewer role with an example UPN.

The example people use the reserved `example.com` domain. The sample prices are
fictional; they are not vendor prices or a recommended rate card.

## 5. Publish manually into your own tenant

This path does not require an automated deployment token.

1. Sign in to Power BI Desktop with an account in the destination tenant.
2. Create or select an approved Power BI workspace.
3. Publish the opened project from Power BI Desktop.
4. Configure credentials and refresh in the Power BI Service.
5. Assign approved Entra security groups to the semantic model's Viewer role.
6. Test as real Viewer users before sharing the report or publishing an app.

A PBIT, when supplied, is opened in Desktop and instantiated there. It is not
directly imported through the Power BI Service REST API. PBIP projects are
editable source projects, not executable copies of Power BI Desktop.

## 6. Automated tenant provisioning

Use an explicitly chosen tenant and workspace:

```powershell
.\Install.ps1 -Action Tenant -SourceMode Demo `
  -TenantId '<your-tenant-guid>' `
  -WorkspaceId '<your-workspace-guid>'
```

Azure CLI authentication is performed against the specified tenant if no
`CTD_FABRIC_ACCESS_TOKEN` is present. Alternatively, acquire an approved
tenant-scoped token with `SemanticModel.ReadWrite.All` and `Report.ReadWrite.All`,
or `Item.ReadWrite.All`, and set it in the current process environment.

The script checks the token's tenant before sending any provisioning request.
The API still verifies the token's signature, audience and permissions.

The installer creates the semantic model first, then binds the report to the
created model ID. It follows Fabric long-running operations and does not
silently overwrite an existing item. Use `-Update` only after reviewing the
destination and backing up its current definitions.

The resulting state is **provisioned, configuration required**. Security-group
assignment, data-source credentials, refresh, app audiences and Viewer smoke
tests remain required. The script does not falsely declare production readiness.

## 7. Replace synthetic data with your own data

Never edit the shipped demonstration to contain real secrets or employee data
and then commit it. Work in an ignored runtime folder.

```powershell
python -m pip install .
ctd collect-github --settings config\settings.json `
  --day 2026-05-28 --output runtime\incoming\github.jsonl
ctd collect-m365 --settings config\settings.json `
  --output runtime\incoming\m365.jsonl
```

Copy `config\settings.example.json` to the ignored `config\settings.json` and
provide your tenant/app/source settings. Secrets are read from environment
variables or from an approved secret manager that populates those variables.

Prepare the input folder:

- `People.csv`, `Scopes.csv`, `ScopeAccess.csv`: required, reviewed organization
  and access mappings.
- `usage.jsonl`: normalized metadata records, combining the approved sources.
- `Models.csv`, `Surfaces.csv`, `Agents.csv`, `Budgets.csv`, `Outcomes.csv`: optional
  registry and outcome inputs using the exact public contract.
- `period-summaries.jsonl`: optional Microsoft 365 period summaries.

Use the data contract and source-capability guide. Do not spread period totals
into daily rows or infer cached tokens from input totals.

```powershell
ctd build-data --input runtime\incoming --output runtime\gold-2026-05-28
ctd validate-data --input runtime\gold-2026-05-28 --production
```

The build sets demonstration mode to false for customer data, removes
ineligible organization scopes, erases suppressed numeric facts and preserves
unpriced/unattributed records.

## 8. Customer data-source modes

### CSV

```powershell
.\Install.ps1 -Action Local -SourceMode CSV `
  -DataFolder C:\CTD\runtime\gold-2026-05-28 `
  -InstallFolder C:\CTD\Customer-1.0.0
```

The Power BI Service cannot read your local folder without a configured
on-premises data gateway. A Desktop-published snapshot can be viewed without
scheduled refresh, but it is not a live pipeline.

### SharePoint

Upload a complete, validated generation of the contract CSV files to an
approved folder in your own tenant. Use the exact folder URL, including its
trailing slash, and configure organizational OAuth credentials:

```powershell
.\Install.ps1 -Action Tenant -SourceMode SharePoint `
  -TenantId '<your-tenant-guid>' -WorkspaceId '<your-workspace-guid>' `
  -DataFolder C:\CTD\runtime\gold-2026-05-28 `
  -SharePointSite 'https://<your-tenant>.sharepoint.com/sites/AIReporting' `
  -SharePointFolder 'https://<your-tenant>.sharepoint.com/sites/AIReporting/Shared Documents/Gold/'
```

The local validated folder is required as a preflight mirror. The model reads
the SharePoint files after deployment, not that local mirror.

A file must match its expected name and exact folder once; missing or duplicate
matches fail explicitly. Credentials are not shipped in the model.

## 9. Security and go-live checks

- Use the Viewer RLS role; app page visibility is not a security boundary.
- Give consumers Viewer/app access, not Workspace Member or Contributor.
- Do not grant broad Build/export permissions without a data-protection review.
- Assign your own sensitivity label in the destination tenant.
- Verify personal user A cannot see user B's personal rows.
- Verify a small scope is absent and suppressed aggregate rows contain no
  numeric facts, even through dataset access.
- Configure refresh only after a complete data generation is uploaded.
- Test all source credentials and permissions in the destination tenant.
- Confirm no demo identities remain in customer data.
- Review access and source coverage periodically.

This is not a legal-compliance certification or an employee-performance tool.

## 10. Troubleshooting

| Symptom | Action |
|---|---|
| Python dependency error | Install the declared runtime package; do not install arbitrary packages |
| CSV header/type error | Compare exact column order/types with the contract |
| Missing tokens or cached tokens | Inspect source coverage; do not substitute zero |
| Unexpected spend totals | Compare billed/estimated basis, unattributed rows and privacy-hidden breakdowns |
| No personal rows | Confirm the actual UPN mapping and Viewer role membership |
| Blank organization scope | Confirm approved scope access and the six-person minimum |
| HTTP 403 | Obtain required consent/role/policy; do not bypass the restriction |
| Existing item conflict | Inspect the destination; use Update only deliberately |
| Refresh failure | Configure credentials, gateway and source-folder permissions |
| Long-running operation timeout | Inspect the workspace and operation before retrying creation |

The accompanying administrator and source-capability manuals provide detailed
operating boundaries.

