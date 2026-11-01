from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import shutil
import stat
import uuid
from pathlib import Path

from copilot_token_dashboard import __version__
from copilot_token_dashboard.schema import TABLES

PRODUCT = "Copilot Token Dashboard"
SCHEMAS = "https://developer.microsoft.com/json-schemas/fabric/"
REPORT_SCHEMA = SCHEMAS + "item/report/definition/report/3.0.0/schema.json"
PAGE_SCHEMA = SCHEMAS + "item/report/definition/page/2.0.0/schema.json"
VISUAL_SCHEMA = SCHEMAS + "item/report/definition/visualContainer/2.4.0/schema.json"
THEME_FILE = Path(__file__).resolve().parents[1] / "powerbi" / "SCBX_Theme.json"
THEME = json.loads(THEME_FILE.read_text(encoding="utf-8"))
PALETTE = {
    "primary": THEME["tableAccent"],
    "gold": THEME["dataColors"][1],
    "title": THEME["textClasses"]["title"]["color"],
    "page": THEME["minimum"],
    "surface": THEME["background"],
    "text": THEME["foreground"],
    "border": THEME["visualStyles"]["*"]["*"]["border"][0]["color"]["solid"]["color"],
}


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ident(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def literal(value: str | bool | int) -> dict:
    if isinstance(value, str):
        value = "'" + value.replace("'", "''") + "'"
    elif isinstance(value, bool):
        value = "true" if value else "false"
    else:
        value = str(value)
    return {"expr": {"Literal": {"Value": value}}}


def field(table: str, property_name: str, measure: bool = False) -> dict:
    return {
        "Measure" if measure else "Column": {
            "Expression": {"SourceRef": {"Entity": table}},
            "Property": property_name,
        }
    }


def m_parameter(name: str, value: str, allowed: list[str] | None = None, required: bool = False) -> dict:
    metadata = 'IsParameterQuery=true, Type="Text", IsParameterQueryRequired=' + ("true" if required else "false")
    if allowed:
        metadata += ", List={" + ",".join('"' + item + '"' for item in allowed) + "}"
    return {"name": name, "kind": "m", "expression": '"' + value.replace('"', '""') + '" meta [' + metadata + "]"}


READ_TABLE = r'''(fileName as text, embeddedCsv as text, columnTypes as list) as table =>
let
    BinarySource =
        if SourceMode = "Demo" then Binary.FromText(embeddedCsv, BinaryEncoding.Base64)
        else if SourceMode = "CSV" then
            if Text.Trim(DataFolder) = "" then error "DataFolder is required for CSV mode."
            else File.Contents(DataFolder & "\" & fileName)
        else if SourceMode = "SharePoint" then
            let
                Checked = if Text.Trim(SharePointSite) = "" or Text.Trim(SharePointFolder) = ""
                    then error "SharePointSite and SharePointFolder are required." else SharePointSite,
                Files = SharePoint.Files(Checked, [ApiVersion = 15]),
                Matches = Table.SelectRows(Files, each [Name] = fileName and [Folder Path] = SharePointFolder),
                Selected = if Table.RowCount(Matches) <> 1
                    then error "Expected exactly one matching SharePoint CSV file." else Matches{0}[Content]
            in Selected
        else error "SourceMode must be Demo, CSV, or SharePoint.",
    Csv = Csv.Document(BinarySource, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Csv, [PromoteAllScalars=true]),
    Expected = List.Transform(columnTypes, each _{0}),
    CheckedHeaders = if Table.ColumnNames(Headers) <> Expected
        then error "CSV columns do not match the published data contract." else Headers,
    Nulls = Table.ReplaceValue(CheckedHeaders, "", null, Replacer.ReplaceValue, Expected),
    Typed = Table.TransformColumnTypes(Nulls, columnTypes, "en-US")
in
    Typed'''


def measures() -> list[dict]:
    expressions: dict[str, tuple[str, str, str]] = {
        "Anchor Date": ("MAX(Settings[AnchorDate])", "yyyy-MM-dd", "Context"),
        "Data Banner": ('IF(SELECTEDVALUE(Settings[IsDemo],FALSE()), "SYNTHETIC DEMO - NOT LIVE DATA", "CUSTOMER DATA - REVIEW COVERAGE")', "", "Context"),
        "Viewer UPN": (
            'VAR u=USERPRINCIPALNAME() VAR known=COUNTROWS(FILTER(ALL(People),LOWER(People[UPN])=LOWER(u))) '
            'RETURN IF(known>0 || NOT SELECTEDVALUE(Settings[IsDemo],FALSE()),u,"user01@example.com")', "", "Context"),
        "Viewer Greeting": ('"Private usage for " & [Viewer UPN]', "", "Context"),
        "Selected Period": ('SELECTEDVALUE(Periods[Label], "Last 28 days")', "", "Context"),
        "Selected Scope": (
            'COALESCE(SELECTEDVALUE(Scopes[ScopeKey]), '
            'LOOKUPVALUE(People[ScopeKey], People[UPN], [Viewer UPN]))', "", "Context"),
        "Period Start": (
            'VAR a=[Anchor Date] VAR mode=SELECTEDVALUE(Periods[Mode],"Rolling") '
            'VAR days=SELECTEDVALUE(Periods[Days],28) RETURN SWITCH(mode,'
            '"MTD",DATE(YEAR(a),MONTH(a),1),"YTD",DATE(YEAR(a),1,1),a-days+1)',
            "yyyy-MM-dd", "Context"),
        "Privacy Minimum": ("MAX(6,MAX(Settings[MinimumGroupSize]))", "0", "Context"),
        "Currency Multiplier": ("SELECTEDVALUE(Currencies[Multiplier],1)", "0.0000", "Context"),
        "Currency Code": ('SELECTEDVALUE(Currencies[Code],MAX(Settings[BaseCurrency]))', "", "Context"),
        "Data Date Label": ('"Data through " & FORMAT([Anchor Date],"yyyy-MM-dd")', "", "Context"),
        "Scope Name": ('LOOKUPVALUE(Scopes[Name],Scopes[ScopeKey],[Selected Scope])', "", "Context"),
        "Personal Privacy Note": ('"Personal records are self-only under Viewer RLS. Workspace administrators are trusted custodians."', "", "Guidance"),
        "Data Quality Note": ('"Missing metrics are not zero. Costs are reported/estimated subtotals; inspect coverage and unpriced records."', "", "Guidance"),
        "Usage Note": ('"Activity and spend do not measure employee performance. Sources and measurement units differ."', "", "Guidance"),
        "Momentum Note": ('"Last six completed weeks versus the preceding six. Intensity is reported requests per active user-week."', "", "Guidance"),
        "Value Note": ('"Scenario estimates use owner assumptions and a blended hourly rate. They are not causal productivity evidence."', "", "Guidance"),
        "Source Note": ('"Microsoft 365 period summaries are not daily request counts. GitHub cache details are not universally exposed."', "", "Guidance"),
        "Production Note": ('"Set customer sources, validate data, assign Viewer RLS and credentials, then complete tenant smoke tests."', "", "Guidance"),
        "Hourly Rate": ("SELECTEDVALUE(HourlyRate[Rate],20)", "0.00", "Value"),
    }
    personal = {
        "Known Spend": ("Amount", "#,0.00"),
        "Input Tokens": ("InputTokens", "#,0"),
        "Cached Input Tokens": ("CachedInputTokens", "#,0"),
        "Cache Write Tokens": ("CacheWriteTokens", "#,0"),
        "Output Tokens": ("OutputTokens", "#,0"),
        "Requests": ("Requests", "#,0"),
        "Sessions": ("Sessions", "#,0"),
        "Agent Runs": ("AgentRuns", "#,0"),
        "Premium Requests": ("PremiumRequests", "#,0.00"),
        "Copilot Credits": ("CopilotCredits", "#,0.00"),
        "GitHub AI Credits": ("GitHubAiCredits", "#,0.00"),
    }
    for name, (column, formatting) in personal.items():
        expression = (
            f'VAR u=[Viewer UPN] VAR startDate=[Period Start] VAR finish=[Anchor Date] '
            f'RETURN CALCULATE(SUM(UsageDaily[{column}]),KEEPFILTERS(People[UPN]=u),'
            'KEEPFILTERS(DATESBETWEEN(Calendar[Date],startDate,finish)))'
        )
        if column == "Amount":
            expression += "*[Currency Multiplier]"
        expressions["My " + name] = (expression, formatting, "Personal")
    for name, length in (("7 Days", 7), ("28 Days", 28), ("MTD", 0)):
        start = f"[Anchor Date]-{length - 1}" if length else "DATE(YEAR([Anchor Date]),MONTH([Anchor Date]),1)"
        expressions["My Spend " + name] = (
            f'VAR u=[Viewer UPN] RETURN CALCULATE(SUM(UsageDaily[Amount]),KEEPFILTERS(People[UPN]=u),'
            f'DATESBETWEEN(Calendar[Date],{start},[Anchor Date]))*[Currency Multiplier]',
            "#,0.00", "Personal")
    expressions.update({
        "My Reported Tokens": ("[My Input Tokens]+[My Output Tokens]", "#,0", "Personal"),
        "My Active Days": (
            'VAR u=[Viewer UPN] RETURN CALCULATE(DISTINCTCOUNT(UsageDaily[Date]),'
            'KEEPFILTERS(People[UPN]=u),UsageDaily[ActivityObserved]=TRUE(),'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date]))', "#,0", "Personal"),
        "My Cache Coverage Gaps": (
            'VAR u=[Viewer UPN] RETURN CALCULATE(COUNTROWS(UsageDaily),KEEPFILTERS(People[UPN]=u),'
            'NOT ISBLANK(UsageDaily[InputTokens]),ISBLANK(UsageDaily[CachedInputTokens]),'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date]))', "#,0", "Personal"),
        "My Cache Write Coverage Gaps": (
            'VAR u=[Viewer UPN] RETURN CALCULATE(COUNTROWS(UsageDaily),KEEPFILTERS(People[UPN]=u),'
            'NOT ISBLANK(UsageDaily[InputTokens]),ISBLANK(UsageDaily[CacheWriteTokens]),'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date]))', "#,0", "Personal"),
        "My Cache Hit Ratio": (
            'IF([My Cache Coverage Gaps]=0,DIVIDE([My Cached Input Tokens],[My Input Tokens]))', "0.0%", "Personal"),
        "My Uncached Input Tokens": (
            'IF([My Cache Coverage Gaps]=0 && [My Cache Write Coverage Gaps]=0,'
            '[My Input Tokens]-[My Cached Input Tokens]-[My Cache Write Tokens])',
            "#,0", "Personal"),
        "My Token Requests": (
            'VAR u=[Viewer UPN] RETURN CALCULATE(SUM(UsageDaily[Requests]),KEEPFILTERS(People[UPN]=u),'
            'NOT ISBLANK(UsageDaily[InputTokens]),'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date]))', "#,0", "Personal"),
        "My Tokens per Request": ("DIVIDE([My Reported Tokens],[My Token Requests])", "#,0", "Personal"),
        "My Unpriced Records": (
            'VAR u=[Viewer UPN] RETURN CALCULATE(COUNTROWS(UsageDaily),KEEPFILTERS(People[UPN]=u),'
            'NOT ISBLANK(UsageDaily[InputTokens]),ISBLANK(UsageDaily[Amount]),'
            'UsageDaily[CostBasis]<>"billed separately",'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date]))', "#,0", "Personal"),
        "My Cost Label": (
            'IF(SELECTEDVALUE(UsageDaily[BillingKind])="licence-included","Not usage billed",'
            'IF(ISBLANK([My Known Spend]),"Not reported",FORMAT([My Known Spend],"0.00")))', "", "Personal"),
        "My Model Reconciliation": (
            "[My Known Spend]-SUMX(VALUES('Models'[ModelKey]),[My Known Spend])", "0.0000", "Quality"),
    })
    scope_fields = {
        "Known Spend": ("Amount", "#,0.00"),
        "Input Tokens": ("InputTokens", "#,0"), "Cached Input Tokens": ("CachedInputTokens", "#,0"),
        "Output Tokens": ("OutputTokens", "#,0"), "Requests": ("Requests", "#,0"),
        "Agent Runs": ("AgentRuns", "#,0"), "Active Users": ("ActiveUsers", "#,0"),
        "User Days": ("UserDays", "#,0"), "Member Count": ("MemberCount", "#,0"),
        "Unpriced Records": ("UnpricedRows", "#,0"),
    }
    for name, (column, formatting) in scope_fields.items():
        expression = (
            f'VAR scopeKey=[Selected Scope] VAR period=[Selected Period] RETURN '
            f'CALCULATE(SUM(ScopePeriod[{column}]),KEEPFILTERS(Scopes[ScopeKey]=scopeKey),'
            'KEEPFILTERS(ScopePeriod[PeriodLabel]=period),ScopePeriod[PrivacySuppressed]=FALSE())'
        )
        if column == "Amount":
            expression += "*[Currency Multiplier]"
        expressions["Scope " + name] = (expression, formatting, "Organization")
    expressions.update({
        "Scope Reported Tokens": ("[Scope Input Tokens]+[Scope Output Tokens]", "#,0", "Organization"),
        "Scope Adoption": ("DIVIDE([Scope Active Users],[Scope Member Count])", "0.0%", "Organization"),
        "Scope MTD Spend": (
            'VAR scopeKey=[Selected Scope] RETURN CALCULATE(SUM(ScopePeriod[Amount]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),ScopePeriod[PeriodLabel]="Month to date",'
            'ScopePeriod[PrivacySuppressed]=FALSE())*[Currency Multiplier]', '"USD "#,0.00', "Organization"),
        "Scope Breakdown Spend": (
            'VAR scopeKey=[Selected Scope] RETURN CALCULATE(SUM(ScopeDaily[Amount]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),ScopeDaily[PrivacySuppressed]=FALSE(),'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date]))*[Currency Multiplier]',
            '"USD "#,0.00', "Organization"),
        "Scope Breakdown Tokens": (
            'VAR scopeKey=[Selected Scope] RETURN CALCULATE(SUM(ScopeDaily[InputTokens])+SUM(ScopeDaily[OutputTokens]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),ScopeDaily[PrivacySuppressed]=FALSE(),'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date]))', "#,0", "Organization"),
        "Scope Weekly Spend": (
            'VAR scopeKey=[Selected Scope] RETURN CALCULATE(SUM(ScopeWeekly[Amount]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),ScopeWeekly[SurfaceKey]="all",'
            'ScopeWeekly[PrivacySuppressed]=FALSE())*[Currency Multiplier]', '"USD "#,0.00', "Organization"),
        "Scope Weekly Active Users": (
            'VAR scopeKey=[Selected Scope] RETURN CALCULATE(SUM(ScopeWeekly[ActiveUsers]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),ScopeWeekly[SurfaceKey]="all",'
            'ScopeWeekly[PrivacySuppressed]=FALSE())', "#,0", "Organization"),
        "Hidden Breakdown Difference": ("[Scope Known Spend]-[Scope Breakdown Spend]", '"USD "#,0.00', "Quality"),
    })
    for band in ("High", "Moderate", "Low", "None", "NoRecorded"):
        expressions["Weekly " + band] = (
            f'VAR scopeKey=[Selected Scope] RETURN CALCULATE(SUM(ScopeWeekly[{band}]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),ScopeWeekly[SurfaceKey]="all",'
            'ScopeWeekly[PrivacySuppressed]=FALSE())', "#,0", "Organization")
    for name, column, formatting in (
        ("Spend", "Amount", '"USD "#,0.00'), ("Runs", "AgentRuns", "#,0"),
        ("Users", "ActiveUsers", "#,0"), ("Input Tokens", "InputTokens", "#,0"),
        ("Output Tokens", "OutputTokens", "#,0"), ("Cached Input", "CachedInputTokens", "#,0"),
    ):
        expression = (
            f'VAR scopeKey=[Selected Scope] VAR period=[Selected Period] RETURN CALCULATE(SUM(AgentPeriod[{column}]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),KEEPFILTERS(AgentPeriod[PeriodLabel]=period),'
            'AgentPeriod[PrivacySuppressed]=FALSE())'
        )
        if column == "Amount":
            expression += "*[Currency Multiplier]"
        expressions["Agent " + name] = (expression, formatting, "Agents")
    expressions.update({
        "Active Agents": (
            'VAR scopeKey=[Selected Scope] VAR period=[Selected Period] RETURN CALCULATE(DISTINCTCOUNT(AgentPeriod[AgentKey]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),AgentPeriod[PeriodLabel]=period,AgentPeriod[AgentRuns]>0,'
            'AgentPeriod[PrivacySuppressed]=FALSE())', "#,0", "Agents"),
        "Agent Cost per Run": ("DIVIDE([Agent Spend],[Agent Runs])", '"USD "#,0.00', "Agents"),
        "Agent Tokens per Run": ("DIVIDE([Agent Input Tokens]+[Agent Output Tokens],[Agent Runs])", "#,0", "Agents"),
        "Agent Cache Ratio": ("DIVIDE([Agent Cached Input],[Agent Input Tokens])", "0.0%", "Agents"),
        "Agent Name": ('SELECTEDVALUE(Agents[Name],"Select one agent on this page")', "", "Agents"),
        "Agent User Growth": (
            'VAR scopeKey=[Selected Scope] VAR period=[Selected Period] RETURN CALCULATE(AVERAGE(AgentPeriod[UserGrowth]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),AgentPeriod[PeriodLabel]=period)', "0.0%", "Agents"),
        "Agent Intensity Growth": (
            'VAR scopeKey=[Selected Scope] VAR period=[Selected Period] RETURN CALCULATE(AVERAGE(AgentPeriod[IntensityGrowth]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),AgentPeriod[PeriodLabel]=period)', "0.0%", "Agents"),
        "Agent Trend": (
            'VAR scopeKey=[Selected Scope] VAR period=[Selected Period] RETURN CALCULATE(SELECTEDVALUE(AgentPeriod[TrendClass]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),AgentPeriod[PeriodLabel]=period)', "", "Agents"),
        "Spend Spike Agents": (
            'VAR scopeKey=[Selected Scope] VAR period=[Selected Period] RETURN CALCULATE(DISTINCTCOUNT(AgentPeriod[AgentKey]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),AgentPeriod[PeriodLabel]=period,'
            'AgentPeriod[SpikeFlag]=TRUE())', "#,0", "Agents"),
        "Resolved Work Items": (
            'VAR scopeKey=[Selected Scope] RETURN CALCULATE(COUNTROWS(Outcomes),KEEPFILTERS(Scopes[ScopeKey]=scopeKey),'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date]))', "#,0", "Outcomes"),
        "AI Involved Share": (
            'VAR scopeKey=[Selected Scope] VAR involved=CALCULATE(COUNTROWS(Outcomes),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),Outcomes[HandlingMode]<>"Human only",'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date])) '
            'RETURN DIVIDE(involved,[Resolved Work Items])', "0.0%", "Outcomes"),
        "Agent Resolved Share": (
            'VAR scopeKey=[Selected Scope] VAR resolved=CALCULATE(COUNTROWS(Outcomes),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),Outcomes[HandlingMode]="Agent-resolved",'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date])) '
            'RETURN DIVIDE(resolved,[Resolved Work Items])', "0.0%", "Outcomes"),
        "Resolution Hours": (
            'VAR scopeKey=[Selected Scope] RETURN CALCULATE(AVERAGE(Outcomes[ResolutionHours]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date]))', "0.00", "Outcomes"),
        "Human Resolution Hours": (
            'CALCULATE([Resolution Hours],Outcomes[HandlingMode]="Human only")', "0.00", "Outcomes"),
        "Agent Resolution Hours": (
            'CALCULATE([Resolution Hours],Outcomes[HandlingMode]<>"Human only")', "0.00", "Outcomes"),
        "Measured Effort Saved Hours": (
            'VAR scopeKey=[Selected Scope] VAR baseline=CALCULATE(AVERAGE(Outcomes[HumanEffortMinutes]),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),Outcomes[HandlingMode]="Human only",REMOVEFILTERS(Agents),'
            'DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date])) '
            'RETURN IF(NOT ISBLANK(baseline),CALCULATE(SUMX(Outcomes,'
            'IF(Outcomes[HandlingMode]<>"Human only" && NOT ISBLANK(Outcomes[HumanEffortMinutes]),'
            'MAX(0,baseline-Outcomes[HumanEffortMinutes])/60)),'
            'KEEPFILTERS(Scopes[ScopeKey]=scopeKey),DATESBETWEEN(Calendar[Date],[Period Start],[Anchor Date])))',
            "0.0", "Outcomes"),
        "Estimated Hours Saved": (
            'SUMX(VALUES(Agents[AgentKey]),DIVIDE([Agent Runs]*CALCULATE(MAX(Agents[MinutesSavedPerRun])),60))', "0.0", "Value"),
        "Estimated Value": ("[Estimated Hours Saved]*[Hourly Rate]*[Currency Multiplier]", '"USD "#,0.00', "Value"),
        "Net Scenario Value": ("[Estimated Value]-[Agent Spend]", '"USD "#,0.00', "Value"),
        "Scenario Value Cost Ratio": ("DIVIDE([Estimated Value],[Agent Spend])", "0.0", "Value"),
        "Month Budget": (
            'VAR scopeKey=[Selected Scope] VAR month=DATE(YEAR([Anchor Date]),MONTH([Anchor Date]),1) '
            'RETURN CALCULATE(SUM(Budgets[BudgetAmount]),KEEPFILTERS(Scopes[ScopeKey]=scopeKey),'
            'Budgets[MonthStart]=month)*[Currency Multiplier]', '"USD "#,0.00', "Budget"),
        "Prorated Budget": ("[Month Budget]*DIVIDE(DAY([Anchor Date]),DAY(EOMONTH([Anchor Date],0)))", '"USD "#,0.00', "Budget"),
        "Budget Used Ratio": ("DIVIDE([Scope MTD Spend],[Prorated Budget])", "0.0%", "Budget"),
        "Budget Variance": ("[Scope MTD Spend]-[Prorated Budget]", '"USD "#,0.00', "Budget"),
        "Coverage Fields Reported": ('CALCULATE(COUNTROWS(Coverage),Coverage[Status]="Reported")', "#,0", "Quality"),
        "Coverage Fields Missing": ('CALCULATE(COUNTROWS(Coverage),Coverage[Status]="Not reported")', "#,0", "Quality"),
        "Coverage Fields Partial": ('CALCULATE(COUNTROWS(Coverage),Coverage[Status]="Partial")', "#,0", "Quality"),
    })
    output = []
    for name, (expression, formatting, folder) in expressions.items():
        item = {"name": name, "expression": expression, "displayFolder": folder}
        if formatting:
            item["formatString"] = formatting.replace('"USD "', "")
        output.append(item)
    return output


def model_definition(data: Path) -> dict:
    m_types = {"text": "type text", "date": "type date", "bool": "type logical",
               "int": "Int64.Type", "number": "type number"}
    bim_types = {"text": "string", "date": "dateTime", "bool": "boolean",
                 "int": "int64", "number": "double"}
    tables = []
    for name, columns in TABLES.items():
        path = data / f"{name}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Power BI build requires {name}.csv")
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        types = "{" + ",".join('{"' + column + '",' + m_types[kind] + "}" for column, kind in columns.items()) + "}"
        expression = f'ReadTable("{name}.csv","{encoded}",{types})'
        table_columns = []
        for column, kind in columns.items():
            item = {"name": column, "dataType": bim_types[kind], "sourceColumn": column, "summarizeBy": "none"}
            if kind == "date":
                item["formatString"] = "yyyy-MM-dd"
            elif kind == "int":
                item["formatString"] = "#,0"
            elif kind == "number":
                item["formatString"] = "0.00"
            if column.endswith("Key") or column in {"UPN", "ViewerUPN"}:
                item["isHidden"] = True
            if name == "Calendar" and column == "Month":
                item["sortByColumn"] = "MonthNumber"
            if name == "Periods" and column == "Label":
                item["sortByColumn"] = "SortOrder"
            table_columns.append(item)
        tables.append({
            "name": name, "columns": table_columns,
            "partitions": [{"name": name, "mode": "import", "source": {"type": "m", "expression": expression}}],
            "annotations": [{"name": "PBI_ResultType", "value": "Table"}],
            "isHidden": name in {"Settings", "ScopeAccess", "UsageDaily", "ScopeDaily", "ScopeWeekly", "ScopePeriod", "AgentPeriod"},
        })
    tables.append({
        "name": "_Measures", "columns": [{"name": "Value", "sourceColumn": "Value", "dataType": "int64", "isHidden": True}],
        "partitions": [{"name": "_Measures", "mode": "import", "source": {"type": "m", "expression": "#table(type table [Value=Int64.Type],{{0}})"}}],
        "measures": measures(),
    })
    expressions = [
        m_parameter("SourceMode", "Demo", ["Demo", "CSV", "SharePoint"], required=True),
        m_parameter("DataFolder", ""), m_parameter("SharePointSite", ""), m_parameter("SharePointFolder", ""),
        {"name": "ReadTable", "kind": "m", "expression": READ_TABLE},
    ]
    relationships = []

    def relation(source: str, column: str, target: str, key_column: str) -> None:
        relationships.append({
            "name": str(uuid.uuid5(uuid.NAMESPACE_URL, "|".join((PRODUCT, source, column, target, key_column)))),
            "fromTable": source, "fromColumn": column, "toTable": target, "toColumn": key_column,
            "crossFilteringBehavior": "oneDirection",
        })

    for source, column in (("UsageDaily", "Date"), ("ScopeDaily", "Date"),
                           ("ScopeWeekly", "WeekStart"), ("Outcomes", "ResolvedDate")):
        relation(source, column, "Calendar", "Date")
    relation("UsageDaily", "PersonKey", "People", "PersonKey")
    relation("UsageDaily", "AccountKey", "Accounts", "AccountKey")
    relation("PeriodSummary", "PersonKey", "People", "PersonKey")
    for source in ("UsageDaily", "ScopeDaily"):
        relation(source, "ModelKey", "Models", "ModelKey")
        relation(source, "SurfaceKey", "Surfaces", "SurfaceKey")
    for source in ("ScopeDaily", "ScopeWeekly", "ScopePeriod", "AgentPeriod", "Outcomes", "Budgets"):
        relation(source, "ScopeKey", "Scopes", "ScopeKey")
    relation("AgentPeriod", "AgentKey", "Agents", "AgentKey")
    relation("Outcomes", "AgentKey", "Agents", "AgentKey")
    permissions = [
        {"name": "People", "filterExpression": "LOWER([UPN])=LOWER(USERPRINCIPALNAME())"},
        {"name": "Accounts", "filterExpression": "LOWER([UPN])=LOWER(USERPRINCIPALNAME())"},
        {"name": "ScopeAccess", "filterExpression": "LOWER([ViewerUPN])=LOWER(USERPRINCIPALNAME())"},
        {"name": "Scopes", "filterExpression":
            '[MemberCount]>=6 && [ScopeKey] IN CALCULATETABLE(VALUES(ScopeAccess[ScopeKey]),'
            'LOWER(ScopeAccess[ViewerUPN])=LOWER(USERPRINCIPALNAME()))'},
    ]
    permissions.extend({"name": name, "filterExpression": "[PrivacySuppressed]=FALSE()"}
                       for name in ("ScopeDaily", "ScopeWeekly", "ScopePeriod", "AgentPeriod"))
    return {
        "name": PRODUCT, "compatibilityLevel": 1550,
        "model": {
            "culture": "en-US", "sourceQueryCulture": "en-US",
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "tables": tables, "relationships": relationships, "expressions": expressions,
            "roles": [{"name": "Viewer", "modelPermission": "read", "tablePermissions": permissions}],
            "annotations": [{"name": "PBI_ProTooling", "value": '["DevMode"]'}],
        },
    }


class Page:
    def __init__(self, report: Path, name: str, title: str, height: int = 1000) -> None:
        self.folder = report / "definition" / "pages" / name
        self.name, self.title, self.height, self.visuals = name, title, height, []
        save_json(self.folder / "page.json", {
            "$schema": PAGE_SCHEMA, "name": name, "displayName": title,
            "displayOption": "FitToWidth" if height > 1000 else "FitToPage",
            "width": 1600, "height": height,
            "objects": {
                "background": [{"properties": {
                    "color": {"solid": {"color": literal(PALETTE["page"])}},
                    "transparency": literal(0),
                }}],
            },
        })

    def visual(
        self, kind: str, title: str, roles: dict[str, list[tuple[str, str, bool]]],
        x: int, y: int, width: int, height: int, header: bool = False,
    ) -> None:
        name = ident(self.name, title, str(len(self.visuals)))
        query_state = {}
        for role, selections in roles.items():
            query_state[role] = {"projections": [{
                "field": field(table, prop, is_measure), "queryRef": table + "." + prop,
                "nativeQueryRef": prop,
            } for table, prop, is_measure in selections]}
        visual = {
            "visualType": kind, "query": {"queryState": query_state},
            "visualContainerObjects": {
                "title": [{"properties": {
                    "show": literal(True),
                    "text": literal("SCBX - " + title if header and title == self.title else title),
                    "fontColor": {"solid": {"color": literal(PALETTE["surface"] if header else PALETTE["title"])}},
                    "fontFamily": literal("Segoe UI Semibold"),
                    "fontSize": literal(20 if header and title == self.title else 12),
                }}],
                "background": [{"properties": {"show": literal(True),
                    "color": {"solid": {"color": literal(PALETTE["primary"] if header else PALETTE["surface"])}},
                    "transparency": literal(0)}}],
                "border": [{"properties": {"show": literal(not header),
                    "color": {"solid": {"color": literal(PALETTE["border"])}}, "radius": literal(8)}}],
                "general": [{"properties": {"altText": literal(title + ". Read metric coverage before interpretation.")}}],
            },
        }
        if kind == "slicer":
            visual["objects"] = {"selection": [{"properties": {"singleSelect": literal(True)}}]}
        elif kind == "card":
            visual["objects"] = {
                "labels": [{"properties": {
                    "color": {"solid": {"color": literal(PALETTE["surface"] if header else PALETTE["title"])}},
                    "fontFamily": literal("Segoe UI" if header else "Segoe UI Semibold"),
                    "fontSize": literal(12 if header else 24),
                }}],
                "categoryLabels": [{"properties": {"show": literal(False)}}],
            }
        definition = {
            "$schema": VISUAL_SCHEMA, "name": name,
            "position": {"x": x, "y": y, "width": width, "height": height,
                         "z": len(self.visuals), "tabOrder": len(self.visuals)},
            "visual": visual,
        }
        save_json(self.folder / "visuals" / name / "visual.json", definition)
        self.visuals.append({"id": name, "type": kind, "title": title, "roles": roles,
                             "position": definition["position"]})

    def card(self, title: str, measure: str, x: int, y: int, width: int = 248,
             height: int = 112, header: bool = False) -> None:
        self.visual("card", title, {"Values": [("_Measures", measure, True)]},
                    x, y, width, height, header)

    def common(self, personal: bool = False) -> None:
        self.card(self.title, "Data Banner", 0, 0, 1160, 80, header=True)
        self.card("Data freshness", "Data Date Label", 1160, 0, 440, 80, header=True)
        self.visual("slicer", "Period", {"Values": [("Periods", "Label", False)]}, 16, 90, 300, 72)
        if not personal:
            self.visual("slicer", "Reporting scope", {"Values": [("Scopes", "Name", False)]}, 330, 90, 650, 72)
        self.visual("slicer", "Currency", {"Values": [("Currencies", "Code", False)]}, 1284, 90, 300, 72)

    def cards(self, values: list[tuple[str, str]], y: int = 176) -> None:
        for index, (title, measure) in enumerate(values):
            self.card(title, measure, 16 + (index % 6) * 264, y + (index // 6) * 126)

    def table(self, title: str, selections: list[tuple[str, str, bool]], y: int, height: int = 280) -> None:
        self.visual("tableEx", title, {"Values": selections}, 16, y, 1568, height)

    def accent_line(self) -> None:
        name = ident(self.name, "SCBX gold header accent")
        definition = {
            "$schema": VISUAL_SCHEMA, "name": name,
            "position": {"x": 0, "y": 80, "width": 1600, "height": 4,
                         "z": len(self.visuals), "tabOrder": len(self.visuals)},
            "visual": {
                "visualType": "shape",
                "objects": {
                    "shape": [{"properties": {"tileShape": literal("rectangle")}}],
                    "fill": [{"properties": {"show": literal(True),
                        "fillColor": {"solid": {"color": literal(PALETTE["gold"])}},
                        "transparency": literal(0)}, "selector": {"id": "default"}}],
                    "outline": [{"properties": {"show": literal(False)}, "selector": {"id": "default"}}],
                },
                "visualContainerObjects": {
                    "title": [{"properties": {"show": literal(False)}}],
                    "background": [{"properties": {"show": literal(False)}}],
                    "border": [{"properties": {"show": literal(False)}}],
                    "general": [{"properties": {"altText": literal("SCBX gold header accent; decorative")}}],
                },
            },
        }
        save_json(self.folder / "visuals" / name / "visual.json", definition)
        self.visuals.append({"id": name, "type": "shape", "title": "SCBX gold header accent",
                             "roles": {}, "position": definition["position"]})

    def remove_obsolete_visuals(self) -> None:
        expected = {visual["id"] for visual in self.visuals}
        for directory in (self.folder / "visuals").iterdir():
            if not directory.is_dir() or directory.name in expected:
                continue
            paths = list(directory.iterdir())
            if paths and (len(paths) != 1 or paths[0].name != "visual.json"):
                raise ValueError("An obsolete generated visual contains custom files; preserve them before rebuilding")
            if paths:
                paths[0].unlink()
            if getattr(directory.stat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_READONLY", 0):
                directory.chmod(stat.S_IREAD | stat.S_IWRITE)
            directory.rmdir()


def generate_report(folder: Path) -> list[dict]:
    pages = []
    save_json(folder / "definition" / "version.json", {
        "$schema": SCHEMAS + "item/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })

    def page(name: str, title: str, height: int = 1000, personal: bool = False) -> Page:
        result = Page(folder, name, title, height)
        result.common(personal)
        pages.append(result)
        return result

    p = page("overview", "Overview")
    p.cards([("Known usage spend", "Scope Known Spend"), ("Spend MTD", "Scope MTD Spend"),
             ("Prorated budget used", "Budget Used Ratio"), ("Active people", "Scope Active Users"),
             ("Active agents", "Active Agents"), ("Reported tokens", "Scope Reported Tokens")])
    p.visual("lineChart", "Weekly known spend: 13 completed weeks",
             {"Category": [("Calendar", "WeekStart", False)], "Y": [("_Measures", "Scope Weekly Spend", True)]},
             16, 306, 768, 270)
    p.visual("donutChart", "Visible spend by surface",
             {"Category": [("Surfaces", "Name", False)], "Y": [("_Measures", "Scope Breakdown Spend", True)]},
             800, 306, 784, 270)
    p.table("Agent portfolio", [("Agents", "Name", False), ("_Measures", "Agent Spend", True),
            ("_Measures", "Agent Runs", True), ("_Measures", "Agent Cost per Run", True)], 590, 270)
    p.card("Purpose", "Usage Note", 16, 876, 1568, 102)

    p = page("personal", "My AI Usage", 1850, True)
    p.cards([("My spend 7 days", "My Spend 7 Days"), ("My spend 28 days", "My Spend 28 Days"),
             ("My spend MTD", "My Spend MTD"), ("My reported tokens", "My Reported Tokens"),
             ("My observed active days", "My Active Days"), ("Unpriced token records", "My Unpriced Records")])
    p.table("My accounts", [("Accounts", "Platform", False), ("Accounts", "AccountType", False),
            ("Accounts", "MaskedId", False), ("Accounts", "DataThroughDate", False)], 306, 210)
    p.visual("lineChart", "My known spend over time",
             {"Category": [("Calendar", "Date", False)], "Y": [("_Measures", "My Known Spend", True)]},
             16, 530, 1568, 270)
    p.table("My surfaces and agents", [("Surfaces", "Name", False), ("_Measures", "My Cost Label", True),
            ("_Measures", "My Requests", True), ("_Measures", "My Agent Runs", True),
            ("_Measures", "My Reported Tokens", True)], 814, 270)
    p.table("My model usage", [("Models", "Name", False), ("Models", "Provider", False),
            ("Models", "Tier", False), ("_Measures", "My Reported Tokens", True),
            ("_Measures", "My Cached Input Tokens", True), ("_Measures", "My Known Spend", True)], 1098, 270)
    p.table("Source period summaries: not daily counts", [("PeriodSummary", "Source", False),
            ("PeriodSummary", "StartDate", False), ("PeriodSummary", "EndDate", False),
            ("PeriodSummary", "Metric", False), ("PeriodSummary", "Value", False)], 1382, 270)
    p.card("Privacy", "Personal Privacy Note", 16, 1666, 1568, 150)

    p = page("organization", "Organization Usage")
    p.cards([("Reporting members", "Scope Member Count"), ("Active people", "Scope Active Users"),
             ("Recorded adoption", "Scope Adoption"), ("Active user-days", "Scope User Days"),
             ("Known spend", "Scope Known Spend"), ("Privacy minimum", "Privacy Minimum")])
    p.visual("lineChart", "Weekly active people: completed weeks",
             {"Category": [("Calendar", "WeekStart", False)], "Y": [("_Measures", "Scope Weekly Active Users", True)]},
             16, 306, 1568, 250)
    p.visual("columnChart", "Recorded weekly engagement bands",
             {"Category": [("Calendar", "WeekStart", False)], "Y": [
                 ("_Measures", "Weekly High", True), ("_Measures", "Weekly Moderate", True),
                 ("_Measures", "Weekly Low", True), ("_Measures", "Weekly None", True),
                 ("_Measures", "Weekly NoRecorded", True)]}, 16, 570, 1568, 260)
    p.card("Interpretation", "Usage Note", 16, 846, 1568, 130)

    p = page("momentum", "Adoption and Momentum")
    p.card("Method", "Momentum Note", 16, 176, 1568, 100)
    p.visual("scatterChart", "Agent adoption versus intensity",
             {"Category": [("Agents", "Name", False)], "X": [("_Measures", "Agent User Growth", True)],
              "Y": [("_Measures", "Agent Intensity Growth", True)], "Size": [("_Measures", "Agent Spend", True)]},
             16, 292, 768, 350)
    p.visual("tableEx", "Trend classification", {"Values": [
        ("Agents", "Name", False), ("_Measures", "Agent User Growth", True),
        ("_Measures", "Agent Intensity Growth", True), ("_Measures", "Agent Trend", True)]},
        800, 292, 784, 350)
    p.card("Data caution", "Data Quality Note", 16, 660, 1568, 180)

    p = page("agents", "Agents")
    p.cards([("Active agents", "Active Agents"), ("Known agent spend", "Agent Spend"),
             ("Reported runs", "Agent Runs"), ("Known cost per run", "Agent Cost per Run"),
             ("Eligible agent users", "Agent Users"), ("Spend-spike agents", "Spend Spike Agents")])
    p.table("Agent portfolio: use the selector on Agent Detail",
            [("Agents", "Name", False), ("Agents", "Type", False), ("Agents", "Status", False),
             ("_Measures", "Agent Spend", True), ("_Measures", "Agent Runs", True),
             ("_Measures", "Agent Cost per Run", True), ("_Measures", "Agent Users", True)], 306, 350)
    p.table("Registered agent metadata", [("Agents", "Name", False), ("Agents", "Platform", False),
            ("Agents", "Status", False), ("Agents", "Risk", False), ("Agents", "OwnerContact", False)], 674, 280)

    p = page("agent_detail", "Agent Detail")
    p.visual("slicer", "Agent", {"Values": [("Agents", "Name", False)]}, 990, 90, 280, 72)
    p.cards([("Selected agent", "Agent Name"), ("Known spend", "Agent Spend"),
             ("Reported runs", "Agent Runs"), ("Cost per run", "Agent Cost per Run"),
             ("Reported tokens per run", "Agent Tokens per Run"), ("Estimated hours", "Estimated Hours Saved")])
    p.table("Agent profile", [("Agents", "Name", False), ("Agents", "Type", False),
            ("Agents", "Platform", False), ("Agents", "OwnerContact", False),
            ("Agents", "Status", False), ("Agents", "Risk", False)], 306, 250)
    p.table("Agent reported period metrics", [("Agents", "Name", False), ("_Measures", "Agent Spend", True),
            ("_Measures", "Agent Runs", True), ("_Measures", "Agent Users", True),
            ("_Measures", "Agent Input Tokens", True), ("_Measures", "Agent Output Tokens", True)], 572, 250)
    p.card("Caution", "Value Note", 16, 840, 1568, 130)

    p = page("outcomes", "Agent Outcomes")
    p.cards([("Resolved work items", "Resolved Work Items"), ("AI-involved share", "AI Involved Share"),
             ("Agent-resolved share", "Agent Resolved Share"), ("Human resolution hours", "Human Resolution Hours"),
             ("Agent resolution hours", "Agent Resolution Hours"), ("Measured effort saved", "Measured Effort Saved Hours")])
    p.visual("clusteredColumnChart", "Resolution hours by handling mode",
             {"Category": [("Outcomes", "HandlingMode", False)], "Y": [("_Measures", "Resolution Hours", True)]},
             16, 306, 768, 280)
    p.visual("columnChart", "Resolved work by category",
             {"Category": [("Outcomes", "Category", False)], "Series": [("Outcomes", "HandlingMode", False)],
              "Y": [("_Measures", "Resolved Work Items", True)]}, 800, 306, 784, 280)
    p.table("Outcome categories", [("Outcomes", "Category", False), ("Outcomes", "Priority", False),
            ("Outcomes", "HandlingMode", False), ("_Measures", "Resolved Work Items", True),
            ("_Measures", "Resolution Hours", True)], 602, 250)
    p.card("Interpretation", "Value Note", 16, 868, 1568, 110)

    p = page("value", "Value and Budget")
    p.visual("slicer", "Scenario hourly rate", {"Values": [("HourlyRate", "Rate", False)]}, 990, 90, 280, 72)
    p.cards([("Estimated hours saved", "Estimated Hours Saved"), ("Scenario value", "Estimated Value"),
             ("Known agent cost", "Agent Spend"), ("Net scenario value", "Net Scenario Value"),
             ("Value / cost ratio", "Scenario Value Cost Ratio"), ("Budget variance MTD", "Budget Variance")])
    p.table("Value assumptions by agent", [("Agents", "Name", False), ("Agents", "MinutesSavedPerRun", False),
            ("_Measures", "Agent Runs", True), ("_Measures", "Estimated Hours Saved", True),
            ("_Measures", "Estimated Value", True), ("_Measures", "Agent Spend", True)], 306, 310)
    p.cards([("Month budget", "Month Budget"), ("Prorated budget", "Prorated Budget"),
             ("Known spend MTD", "Scope MTD Spend"), ("Prorated budget used", "Budget Used Ratio")], 632)
    p.card("Scenario limits", "Value Note", 16, 774, 1568, 200)

    p = page("models", "Models and Efficiency")
    p.cards([("Known spend", "Scope Known Spend"), ("Reported input", "Scope Input Tokens"),
             ("Reported output", "Scope Output Tokens"), ("Reported tokens", "Scope Reported Tokens"),
             ("Unpriced records", "Scope Unpriced Records"), ("Hidden breakdown difference", "Hidden Breakdown Difference")])
    p.visual("donutChart", "Visible spend by provider",
             {"Category": [("Models", "Provider", False)], "Y": [("_Measures", "Scope Breakdown Spend", True)]},
             16, 306, 768, 270)
    p.visual("donutChart", "Visible spend by tier",
             {"Category": [("Models", "Tier", False)], "Y": [("_Measures", "Scope Breakdown Spend", True)]},
             800, 306, 784, 270)
    p.table("Visible model breakdown", [("Models", "Name", False), ("Models", "Provider", False),
            ("Models", "Tier", False), ("_Measures", "Scope Breakdown Tokens", True),
            ("_Measures", "Scope Breakdown Spend", True)], 592, 270)
    p.card("Coverage", "Source Note", 16, 878, 1568, 100)

    p = page("guide", "Data Quality and Guide", 1320)
    p.cards([("Fields reported", "Coverage Fields Reported"), ("Fields partial", "Coverage Fields Partial"),
             ("Fields not reported", "Coverage Fields Missing"), ("Privacy minimum", "Privacy Minimum"),
             ("My model reconciliation", "My Model Reconciliation"), ("Scope unpriced rows", "Scope Unpriced Records")])
    p.table("Source capability and freshness", [("Coverage", "Source", False), ("Coverage", "Metric", False),
            ("Coverage", "Granularity", False), ("Coverage", "Status", False),
            ("Coverage", "AsOfDate", False), ("Coverage", "Detail", False)], 306, 360)
    for index, (title, metric) in enumerate((
        ("Interpretation", "Usage Note"), ("Missing data", "Data Quality Note"),
        ("Privacy", "Personal Privacy Note"), ("Production setup", "Production Note"),
    )):
        p.card(title, metric, 16, 682 + index * 150, 1568, 138)
    order = [item.name for item in pages]
    for item in pages:
        item.accent_line()
        item.remove_obsolete_visuals()
    resources = folder / "StaticResources" / "RegisteredResources"
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(THEME_FILE, resources / THEME_FILE.name)
    save_json(folder / "definition" / "pages" / "pages.json", {
        "$schema": SCHEMAS + "item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": order, "activePageName": order[0],
    })
    save_json(folder / "definition" / "report.json", {
        "$schema": REPORT_SCHEMA,
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU10", "type": "SharedResources",
                "reportVersionAtImport": {"visual": "2.4.0", "page": "2.0.0", "report": "3.0.0"},
            },
            "customTheme": {
                "name": THEME_FILE.stem, "type": "RegisteredResources",
                "reportVersionAtImport": {"visual": "2.4.0", "page": "2.0.0", "report": "3.0.0"},
            },
        },
        "resourcePackages": [{
            "name": "RegisteredResources", "type": "RegisteredResources",
            "items": [{"name": THEME_FILE.stem, "path": THEME_FILE.name, "type": "CustomTheme"}],
        }],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized"},
    })
    return [{"name": item.name, "title": item.title, "visualCount": len(item.visuals),
             "visuals": item.visuals} for item in pages]


def build(data: Path, output: Path) -> dict:
    semantic = output / (PRODUCT + ".SemanticModel")
    report = output / (PRODUCT + ".Report")
    save_json(semantic / "definition.pbism", {
        "$schema": SCHEMAS + "item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0", "settings": {"qnaEnabled": False},
    })
    model = model_definition(data)
    save_json(semantic / "model.bim", model)
    save_json(report / "definition.pbir", {
        "$schema": SCHEMAS + "item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": "../" + semantic.name}},
    })
    save_json(output / (PRODUCT + ".pbip"), {
        "$schema": SCHEMAS + "pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": report.name}}],
        "settings": {"enableAutoRecovery": True},
    })
    pages = generate_report(report)
    manifest = {
        "product": PRODUCT, "version": __version__, "pageCount": len(pages),
        "visualCount": sum(page["visualCount"] for page in pages),
        "tableCount": len(model["model"]["tables"]),
        "measureCount": len(model["model"]["tables"][-1]["measures"]),
        "roles": ["Viewer"], "defaultMode": "Demo", "pages": pages,
        "variant": "SCBX", "theme": THEME["name"], "themeFile": THEME_FILE.name,
    }
    save_json(output / "build-manifest.json", manifest)
    return {key: value for key, value in manifest.items() if key != "pages"}


if __name__ == "__main__":
    arguments = argparse.ArgumentParser()
    arguments.add_argument("--data", type=Path, default=Path("sample_data"))
    arguments.add_argument("--output", type=Path, default=Path("powerbi"))
    options = arguments.parse_args()
    print(json.dumps(build(options.data, options.output), indent=2))
