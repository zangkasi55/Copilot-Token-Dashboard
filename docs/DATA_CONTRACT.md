# Data Contract

Generated from the shared schema. CSV column order is part of the contract.

## Settings

| Column | Type |
|---|---|
| IsDemo | bool |
| AnchorDate | date |
| MinimumGroupSize | int |
| BaseCurrency | text |
| SchemaVersion | text |

## People

| Column | Type |
|---|---|
| PersonKey | text |
| UPN | text |
| DisplayName | text |
| ScopeKey | text |
| Company | text |
| BusinessUnit | text |
| Department | text |
| Team | text |
| JobFamily | text |
| EmployeeType | text |
| IsService | bool |
| IsPrivacyRestricted | bool |
| HasLicense | bool |

## ScopeAccess

| Column | Type |
|---|---|
| ViewerUPN | text |
| ScopeKey | text |

## Scopes

| Column | Type |
|---|---|
| ScopeKey | text |
| Name | text |
| ParentScopeKey | text |
| Company | text |
| BusinessUnit | text |
| Department | text |
| Team | text |
| ScopeLevel | text |
| MemberCount | int |

## Accounts

| Column | Type |
|---|---|
| AccountKey | text |
| PersonKey | text |
| UPN | text |
| Platform | text |
| AccountType | text |
| MaskedId | text |
| DataThroughDate | date |

## Surfaces

| Column | Type |
|---|---|
| SurfaceKey | text |
| Name | text |
| Platform | text |
| SurfaceType | text |
| WorkCategory | text |
| BillingKind | text |

## Models

| Column | Type |
|---|---|
| ModelKey | text |
| Name | text |
| Provider | text |
| Tier | text |
| InputRate | number |
| CacheReadRate | number |
| CacheWriteRate | number |
| OutputRate | number |
| IsPriced | bool |

## Agents

| Column | Type |
|---|---|
| AgentKey | text |
| Name | text |
| Type | text |
| ScopeKey | text |
| Platform | text |
| OwnerContact | text |
| Status | text |
| Risk | text |
| PublishedDate | date |
| MinutesSavedPerRun | number |
| IsRegistered | bool |

## UsageDaily

| Column | Type |
|---|---|
| RowKey | text |
| Date | date |
| PersonKey | text |
| AccountKey | text |
| SurfaceKey | text |
| ModelKey | text |
| AgentKey | text |
| ScopeKey | text |
| InputTokens | int |
| CachedInputTokens | int |
| CacheWriteTokens | int |
| OutputTokens | int |
| Requests | number |
| Sessions | int |
| AgentRuns | int |
| PremiumRequests | number |
| CopilotCredits | number |
| GitHubAiCredits | number |
| Amount | number |
| Currency | text |
| CostBasis | text |
| Source | text |
| BillingKind | text |
| ActivityObserved | bool |
| IsAttributed | bool |
| RequestUnit | text |

## ScopeDaily

| Column | Type |
|---|---|
| Date | date |
| ScopeKey | text |
| SurfaceKey | text |
| ModelKey | text |
| AgentKey | text |
| Amount | number |
| InputTokens | int |
| CachedInputTokens | int |
| CacheWriteTokens | int |
| OutputTokens | int |
| Requests | number |
| AgentRuns | int |
| UserDays | int |
| ActiveUsers | int |
| PrivacySuppressed | bool |
| UnpricedRows | int |

## ScopeWeekly

| Column | Type |
|---|---|
| WeekStart | date |
| ScopeKey | text |
| SurfaceKey | text |
| Amount | number |
| InputTokens | int |
| OutputTokens | int |
| Requests | number |
| AgentRuns | int |
| ActiveUsers | int |
| UserDays | int |
| High | int |
| Moderate | int |
| Low | int |
| None | int |
| NoRecorded | int |
| PrivacySuppressed | bool |

## ScopePeriod

| Column | Type |
|---|---|
| PeriodLabel | text |
| ScopeKey | text |
| Amount | number |
| InputTokens | int |
| CachedInputTokens | int |
| OutputTokens | int |
| Requests | number |
| AgentRuns | int |
| ActiveUsers | int |
| UserDays | int |
| MemberCount | int |
| PrivacySuppressed | bool |
| UnpricedRows | int |
| UnattributedAmount | number |

## AgentPeriod

| Column | Type |
|---|---|
| PeriodLabel | text |
| ScopeKey | text |
| AgentKey | text |
| Amount | number |
| AgentRuns | int |
| ActiveUsers | int |
| InputTokens | int |
| CachedInputTokens | int |
| OutputTokens | int |
| Last7Amount | number |
| Prior4WeekAverage | number |
| SpikeFlag | bool |
| Idle30Days | bool |
| NewThisMonth | bool |
| UsersLast6Weeks | int |
| UsersPrior6Weeks | int |
| IntensityLast6Weeks | number |
| IntensityPrior6Weeks | number |
| UserGrowth | number |
| IntensityGrowth | number |
| TrendClass | text |
| PrivacySuppressed | bool |

## Outcomes

| Column | Type |
|---|---|
| RecordKey | text |
| ResolvedDate | date |
| ScopeKey | text |
| AgentKey | text |
| Category | text |
| Priority | text |
| HandlingMode | text |
| ResolutionHours | number |
| HumanEffortMinutes | number |
| CSAT | number |

## Budgets

| Column | Type |
|---|---|
| MonthStart | date |
| ScopeKey | text |
| Platform | text |
| BudgetAmount | number |
| Currency | text |

## Coverage

| Column | Type |
|---|---|
| Source | text |
| Metric | text |
| Granularity | text |
| Status | text |
| AsOfDate | date |
| LoadedAtUTC | text |
| RowCount | int |
| Detail | text |

## PeriodSummary

| Column | Type |
|---|---|
| PersonKey | text |
| Source | text |
| StartDate | date |
| EndDate | date |
| Metric | text |
| Value | number |
| Unit | text |
| IsConcealed | bool |

## Calendar

| Column | Type |
|---|---|
| Date | date |
| Year | int |
| MonthNumber | int |
| Month | text |
| YearMonth | text |
| MonthStart | date |
| WeekStart | date |
| WeekLabel | text |
| DayName | text |

## Periods

| Column | Type |
|---|---|
| Label | text |
| Mode | text |
| Days | int |
| SortOrder | int |

## Currencies

| Column | Type |
|---|---|
| Code | text |
| Multiplier | number |
| Symbol | text |

## HourlyRate

| Column | Type |
|---|---|
| Rate | number |
