# Illustrated Sample Dashboard

Explore the report concepts before installing the Power BI project.

**All screenshots below are browser-rendered illustrations using the shipped
synthetic CSVs, not verified Power BI Desktop screenshots.** The companion's
layout/styling is intentionally simplified. It does not run DAX, enforce RLS,
connect to a tenant or prove a successful Power BI deployment.

## Open the sample

- [Open the live synthetic sample](https://zangkasi55.github.io/Copilot-Token-Dashboard/).
  This hosts only the standalone synthetic HTML, not a Power BI workspace or
  any customer data.
- Download [sample-dashboard.html](assets/sample-dashboard.html) using GitHub's
  download/raw-file control, then open the saved file in Edge or Chrome.
- The sample is a single self-contained HTML file. No sign-in, API calls,
  external scripts or customer data are required.
- Select a page, period and example scope. My AI Usage remains fixed to
  `user01@example.com`; it is not your signed-in account.
- Try the Value and Budget hourly-rate slider and the light/dark theme button.
- For the actual Power BI package, use the
  [installation guide](INSTALLATION.md) or [คู่มือภาษาไทย](INSTALLATION_TH.md).

The public screenshots are 1600 pixels wide. Click an image to open its
full-resolution PNG. The English and Thai PDF manuals embed all ten figures.

## Reproducible example settings

| Setting | Value |
|---|---|
| Source | Shipped synthetic sample CSVs |
| Anchor date | 2026-05-28 |
| Period | Last 28 days |
| Default scope | Example engineering team |
| Personal viewer | user01@example.com |
| Outcomes example scope | Example operations team |
| Scenario hourly rate | USD 20 |
| Privacy minimum | Six people |

The [provenance manifest](assets/sample-provenance.json) records SHA-256 hashes
of every source CSV. It contains no private tenant information.

## 1. Overview

![Browser-rendered synthetic Overview illustration, not a verified Power BI screenshot.](images/01-overview.png)

Engineering scope: **USD 468.48 known spend**, **12 active people**,
**1 active agent** and **644,590 reported tokens**. Check scope and data date
before comparing cards. Completed-week trends do not include the latest partial
week. Unavailable usage prices are not shown as free metered consumption.

## 2. My AI Usage

![Browser-rendered synthetic My AI Usage illustration for user01@example.com, not a verified Power BI screenshot.](images/02-personal.png)

The fictional viewer has **USD 34.00 seven-day spend**, **USD 39.04
28-day spend** and **USD 39.04 month-to-date spend**. Masked account IDs and
unavailable model fields stay explicit. Production personal access must be
tested with real Viewer users in Power BI.

## 3. Organization Usage

![Browser-rendered synthetic Organization Usage illustration, not a verified Power BI screenshot.](images/03-organization.png)

The engineering example contains **12 people**. The four-person example team
does not appear as a published scope. The completed-week bands describe recorded
activity, not performance. Fixed scopes and already-suppressed data are a
different security surface from personal raw rows.

## 4. Adoption and Momentum

![Browser-rendered synthetic Adoption and Momentum illustration, not a verified Power BI screenshot.](images/04-momentum.png)

Compare distinct observed users and requests per active user-week across two
six-week windows. Stable activity and a latest-week spend spike can coexist;
neither measure is an individual productivity rating.

## 5. Agents

![Browser-rendered synthetic Agents illustration, not a verified Power BI screenshot.](images/05-agents.png)

The example build helper reports **384 runs**. The spend-spike inputs are
**USD 408.00 last seven days** versus **USD 20.16 prior weekly average**.
Review context and measurement coverage; notifications require separate
approved automation.

## 6. Agent Detail

![Browser-rendered synthetic Agent Detail illustration, not a verified Power BI screenshot.](images/06-agent-detail.png)

Select the build helper to review its profile, approximate **USD 1.22 cost per
run**, reported tokens and fictional minutes-saved assumption. Missing data in
another scope is not silently replaced with numbers.

## 7. Agent Outcomes

![Browser-rendered synthetic Agent Outcomes illustration for the operations team, not a verified Power BI screenshot.](images/07-outcomes.png)

Switch to **Example operations team**. The sample has **56 resolved work
items**: 20 human-only, 18 agent-assisted and 18 agent-resolved. Resolution time
and human effort are separate measures. No causal inference is claimed.

## 8. Value and Budget

![Browser-rendered synthetic Value and Budget illustration, not a verified Power BI screenshot.](images/08-value.png)

The build-helper example uses **48 estimated saved hours** and **USD 20/hour**
to show **USD 960.00 scenario value**. The slider changes the assumption, not
the observed cost. Budget is prorated through May 28.

## 9. Models and Efficiency

![Browser-rendered synthetic Models and Efficiency illustration, not a verified Power BI screenshot.](images/09-models.png)

Cached input is a subset of input. Preserve undisclosed models, unpriced data
and any privacy-hidden breakdown difference. Synthetic token coverage is not
representative of every live vendor API.

## 10. Data Quality and Guide

![Browser-rendered synthetic Data Quality and Guide illustration, not a verified Power BI screenshot.](images/10-guide.png)

The sample reports **8 known**, **0 partial** and **4 unavailable**
source-field capabilities. Complete validation, Desktop rendering, tenant
configuration, credentials, Viewer RLS and refresh checks before sharing.

## Rebuild the illustrations

```powershell
$env:PYTHONPATH = 'src'
python tools\build_sample_dashboard.py
npm run docs
npm run test:manuals
```

The dashboard generator fails if it receives non-demo settings or non-synthetic
identities. The screenshots were captured in Microsoft Edge at 1600 × 1050
CSS pixels with full-page capture; longer pages preserve their full height.
Default screenshots use light theme, the settings above and the build-helper
agent. None was copied from a private or company-branded dashboard.
