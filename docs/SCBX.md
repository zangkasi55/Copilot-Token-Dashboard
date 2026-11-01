# SCBX Power BI Theme Variant

Branch: **scbx**. Base: **Copilot Token Dashboard 1.0.1 public preview**.

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

The neutral browser companion and its screenshot gallery remain generic
illustrations. They are **not SCBX Power BI screenshots**. This branch applies
the supplied palette to the actual Power BI definitions/template only.

## Install the SCBX variant

Use the [SCBX preview release](https://github.com/zangkasi55/Copilot-Token-Dashboard/releases/tag/scbx-v1.0.1)
or clone the branch:

```powershell
git clone --branch scbx --single-branch https://github.com/zangkasi55/Copilot-Token-Dashboard.git
Set-Location Copilot-Token-Dashboard
.\Install.ps1 -Action Validate -InstallDependencies
.\Install.ps1 -Action Local -SourceMode Demo
```

The editable entry point remains `powerbi\Copilot Token Dashboard.pbip`.
The compiled SCBX template is named
`Copilot-Token-Dashboard-SCBX-1.0.1.pbit`.

Source modes, tenant permissions, Viewer RLS, refresh and acceptance steps are
described in the [English](INSTALLATION.md) and [Thai](INSTALLATION_TH.md)
installation guides. Those guides' existing figures demonstrate the neutral
synthetic companion, not a claimed rendering of the SCBX template.

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
ภาพประกอบในคู่มือเดิมเป็นตัวอย่างเบราว์เซอร์กลาง ไม่ใช่ภาพ Power BI รุ่น SCBX
ต้องทดสอบ Desktop และ tenant ปลายทางจริงก่อนใช้ production
