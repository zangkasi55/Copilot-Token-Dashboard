# Data Sources and Capability Matrix

## Implemented paths

| Source | Implemented path | Available metrics | Important limits |
|---|---|---|---|
| GitHub Copilot daily usage | collect-github | Client/model prompt and output token sums where exposed, successful requests, sessions and activity | Not every feature exposes tokens; cache details are not guaranteed |
| GitHub enterprise billing | collect-github with include-billing | Billed netAmount, premium-request or GitHub AI-credit quantities, user/model | Covers users in the selected daily report; use full exports for reconciliation |
| Microsoft 365 Copilot v2 | collect-m365 | App last-activity observations and period prompt/active-day summaries | Not daily request counts or per-model token/spend data; names may be concealed |
| Entra directory | collect-directory | Minimal user/license/directory metadata | Requires a reviewed HR/scope/access mapping; no automatic organizational entitlement grants |
| Owned gateway telemetry | import-source gateway | Reported input/output/cache metadata and known amount | Caller identity must come from authenticated, trusted telemetry; missing cache is unknown |
| Copilot credit exports | import-source credits | Agent/resource credit quantities; optional explicitly estimated unit cost | No automatic per-user split, session or outcome inference |
| Purview audit exports | import-source audit | Minimized interaction metadata and prompt counts when provided | Audit counts are not Microsoft's official Copilot usage measure; no message content retained |
| FOCUS cost exports | import-source focus | Billed amount and currency for explicitly selected AI service | Requires explicit AI service filter; no automatic attribution to user or model |
| ITSM/work outcomes | Reviewed Outcomes.csv | Handling mode, elapsed resolution time, effort and optional CSAT | Bring your own system export; no ticket text or automatic causal claims |

API live access must be smoke-tested in the destination tenant. Automated tests
use synthetic/mock responses, not another organization's credentials.

## GitHub collection

Current documented API version: `2026-03-10`.

Daily reports:

- `GET /enterprises/{enterprise}/copilot/metrics/reports/users-1-day?day=YYYY-MM-DD`
- `GET /orgs/{organization}/copilot/metrics/reports/users-1-day?day=YYYY-MM-DD`

The endpoint returns presigned download links to report data. The enterprise
policy must allow Copilot usage metrics. Required enterprise scopes/permissions
depend on token type: documented Copilot metrics read entitlement, or appropriate
classic/OAuth enterprise/billing scopes.

The parser uses client/model leaves where available and does not add overlapping
CLI totals again. Parent residual counters are retained under undisclosed model.
Session counts remain client-level when model-level sessions are not exposed.

Enterprise billed usage:

- `GET /enterprises/{enterprise}/settings/billing/premium_request/usage`
- `GET /enterprises/{enterprise}/settings/billing/ai_credit/usage`

Per-user/day requests carry year, month, day and user. Billed netAmount is used,
including refunds, rather than replacing it with a guessed unit price.
GitHub AI credits and Copilot Studio credits are separate units.

Use an explicit login-to-UPN map. The tool never guesses enterprise usernames
into real employee email addresses.

## Microsoft 365 and Entra permissions

The client-credentials collector uses an app registered in your own tenant:

- `Reports.Read.All` for Microsoft 365 Copilot reports.
- `User.Read.All` for the minimal directory export.
- Additional permissions must be approved before extending the collector.

Endpoint:

`GET /v1.0/copilot/reports/getMicrosoft365CopilotUsageUserDetail(period='D28',version='v2')`

Supported selected windows: D7, D28, D90 and D180. V2 adds period prompts,
active-usage days and app/agent last-activity dates. These windows are stored as
period summaries. A last-activity observation is not a complete reconstruction
of all daily activity.

Concealed identifiers are detected and are not guessed or joined to people.
Changing the tenant's concealed-name setting requires its own privacy approval;
the package does not disable it.

## Metadata imports

```powershell
ctd import-source --kind gateway --input runtime\gateway.jsonl `
  --scope '<approved-scope-key>' --output runtime\incoming\gateway.jsonl

ctd import-source --kind credits --input runtime\credits.jsonl `
  --scope '<approved-scope-key>' --output runtime\incoming\credits.jsonl

ctd import-source --kind audit --input runtime\audit.jsonl `
  --scope '<approved-scope-key>' --output runtime\incoming\audit.jsonl

ctd import-source --kind focus --input runtime\focus.csv `
  --scope '<approved-scope-key>' --service-filter 'Azure OpenAI' `
  --output runtime\incoming\costs.jsonl
```

Gateway metadata fields include timestamp, request_id, upn, model, prompt_tokens,
completion_tokens, optional cached_tokens/cache_write_tokens, amount/currency,
surface and agent. Do not log full LLM response bodies just to recover cache
counts; emit only the approved usage metadata upstream.

Credit exports require resourceId, usageDate and consumed, with optional
environmentId. A unit price is used only when explicitly supplied and the
result is labelled estimated.

FOCUS imports require ChargePeriodStart, BilledCost, BillingCurrency, ResourceId
and an explicit service selection. Unattributed billing dimensions stay visible.

## Public reference documentation

- [GitHub usage metrics API](https://docs.github.com/en/rest/copilot/copilot-usage-metrics)
- [GitHub example schema](https://docs.github.com/en/copilot/reference/copilot-usage-metrics/example-schema)
- [GitHub billing usage](https://docs.github.com/en/enterprise-cloud@latest/rest/billing/usage)
- [Microsoft 365 usage detail](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/api/admin-settings/reports/copilotreportroot-getmicrosoft365copilotusageuserdetail)
- [Power Query and Microsoft Graph](https://learn.microsoft.com/en-us/power-query/connecting-to-graph)
- [Fabric semantic-model creation](https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/create-semantic-model)
- [Fabric report creation](https://learn.microsoft.com/en-us/rest/api/fabric/report/items/create-report)
- [Power BI project overview](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)

