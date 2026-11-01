# SCBX Power BI Theme Variant

Branch: **scbx**. Base: **Copilot Token Dashboard 1.0.1 public preview**.

## Native local installation check

The repaired **PBIP project** was installed locally in Power BI Desktop
2.160.407.0 using synthetic data. All ten actual report pages rendered without
visual errors after a native data refresh, save and reopen. The Overview showed
468.48 spend, 12 active people and one agent; the fictional personal view showed
34.00 seven-day spend and 39.04 twenty-eight-day spend. Reconciliation was 0.0000.

This check exposed and fixed missing PBIR version metadata, the reserved
`Measures` table name, reserved DAX variable names `start` and `scope`, an
unquoted `Models` table reference and an invalid stacked-column visual type.
The installed sample uses `_Measures`, safe variable names and the native
`columnChart` type. Optional sources remain empty; this is not live usage.

The repaired PBIP source is included in this branch. See the
[actual ten-page Power BI screenshot gallery](SAMPLE_DASHBOARD.md), with Thai
captions, and the [capture provenance](images/native/provenance.json).
These are native Desktop report-canvas crops, not browser illustrations; they
exclude the signed-in account and application chrome.

The check is **local synthetic PBIP verification**, not a claim that the
previously published PBIT was successfully loaded. Cloud publishing, source
credentials and real-user RLS remain separate recipient-tenant checks.

This branch applies the supplied **SCBX Bright** Power BI theme. It is a visual
variant, not an endorsement by SCBX and not a deployment into an SCBX tenant.

## What changed

- Preserved every setting in the supplied theme JSON, including its twelve-color
  data palette, typography, table styles and page styling.
- Registered the theme in PBIR and embedded it in the compiled PBIT.
- Applied purple headers, white header text, a gold divider, violet labels,
  pale page backgrounds, white cards and eight-pixel card borders.
- Adapted the supplied mockups' visual hierarchy to the existing report canvas.
  This is not a pixel-for-pixel recreation of the original PDF.
- Gave local installations a separate `CopilotTokenDashboard\SCBX\1.0.1` folder.
- Tenant API item display names are **SCBX Copilot Token Dashboard**, avoiding
  accidental naming collisions with the neutral variant.

| Theme role | Color |
|---|---|
| Primary/header | #8F47BF |
| Gold accent | #FCAF17 |
| Titles and callouts | #4B2885 |
| Page background | #F7F3FC |
| Card background | #FFFFFF |
| Card border | #E7DCF3 |
| Body text | #151A1F |

Canonical source: [SCBX_Theme.json](../powerbi/SCBX_Theme.json). The generated
report also contains a matching copy under its registered resources.

## What stays unchanged

The model/data contract, 101 measures, ten report pages, collectors, missing-data
rules and six-person privacy minimum are retained from the tested core package.
The ten decorative gold lines increase the visual-container count from 146 to
156; they are not new metrics.

All shipped data remains fictional. No actual SCBX employees, budgets, rate
cards, tenant IDs, credentials or source-system exports are included. The
original mockup PDF and protected company documents are not redistributed.

The neutral browser companion remains a separate generic illustration. It
does not run Power BI, DAX or RLS. The primary gallery and the English/Thai
manuals now use genuine SCBX Power BI Desktop captures of fictional data.

## Install the SCBX variant

Use the repaired branch source, either the
[SCBX source ZIP](https://github.com/zangkasi55/Copilot-Token-Dashboard/archive/refs/heads/scbx.zip)
or a branch clone:

```powershell
git clone --branch scbx --single-branch https://github.com/zangkasi55/Copilot-Token-Dashboard.git
Set-Location Copilot-Token-Dashboard
.\Install.ps1 -Action Validate -InstallDependencies
.\Install.ps1 -Action Local -SourceMode Demo
```

The editable entry point remains `powerbi\Copilot Token Dashboard.pbip`.
The earlier release's compiled template is named
`Copilot-Token-Dashboard-SCBX-1.0.1.pbit`. That legacy PBIT failed native loading
and is not the verified path shown by these screenshots. The historical release
assets remain unchanged; prefer the repaired PBIP source.

Source modes, tenant permissions, Viewer RLS, refresh and acceptance steps are
described in the [English](INSTALLATION.md) and [Thai](INSTALLATION_TH.md)
installation guides. Both guides include the actual ten-page native sample
walkthrough and explicitly separate local PBIP success from live tenant checks.

## Validation

The supplied theme passed Microsoft's official **reportThemeSchema-2.159**
before integration. The branch validator checks that the registered copy
matches the source and validates every report definition.

```powershell
python -m pytest -q tests
python tools\validate_powerbi.py
.\tools\Build-PowerBI.ps1
```

Builds verify the actual compiled custom-theme binding and resource bytes.
The compiler carries RegisteredResources type 1 and custom-theme item type 201,
as verified against the installed product's resource enum metadata.

Desktop rendering and real tenant credentials/refresh/RLS must still be tested
in the recipient environment. A theme schema pass is not production sign-off.

## สรุปภาษาไทย

สาขา **scbx** ใช้ธีม **SCBX Bright** ตามไฟล์ที่ให้มา
ธีมถูกลงทะเบียนใน PBIR และฝังใน PBIT ไม่ได้เพียงวาง JSON ไว้ข้างรายงาน
สีหัวรายงานเป็นม่วง เส้นเน้นเป็นทอง และการ์ด/พื้นหลังใช้ค่าจากธีม

ข้อมูลทั้งหมดยังเป็นข้อมูลสมมติ และเกณฑ์ความเป็นส่วนตัวยังคงหกคน
ไม่ได้อัปโหลด PDF ต้นฉบับหรือข้อมูล tenant จริง
ภาพครบสิบหน้าใน [แกลเลอรี](SAMPLE_DASHBOARD.md) และคู่มือรุ่นที่ปรับปรุงแล้ว
จับจาก Power BI Desktop จริงด้วยข้อมูลสมมติ ตัดบัญชีผู้ใช้และแถบโปรแกรมออก
PBIP ที่แก้แล้วเปิด Refresh บันทึก และเปิดซ้ำได้บนเครื่องทดสอบ
PBIT ของ release เดิมยังไม่ผ่านการเปิดจริง ให้ติดตั้งจาก source ของสาขา scbx
ต้องทดสอบ source, refresh และ RLS ใน tenant ปลายทางก่อนใช้ production
