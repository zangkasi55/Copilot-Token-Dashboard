# คู่มือการติดตั้ง Copilot Token Dashboard

## 1. ภาพรวม

ชุดนี้เป็นรายงาน Power BI แบบโอเพนซอร์สสำหรับติดตั้งใน tenant ขององค์กรคุณเอง
มี 10 หน้า ครอบคลุมการใช้งานส่วนตัว ข้อมูลรวมขององค์กร agent โมเดล
งบประมาณ สมมติฐานด้านคุณค่า และคุณภาพข้อมูล

ชุดนี้ไม่ได้ให้สิทธิ์อ่านข้อมูลขององค์กรอื่น และไม่ได้เชื่อมต่อข้อมูลภายในของ Microsoft
ผู้ติดตั้งต้องใช้ tenant, workspace, สิทธิ์, ข้อมูล และ secret ของตนเอง
ข้อมูลที่ให้มาสาธิตเป็นข้อมูลสมมติและมีป้ายกำกับทุกหน้า

ดูภาพประกอบครบทั้ง 10 หน้าในหัวข้อ 11 หรือ
[แกลเลอรีแดชบอร์ดตัวอย่าง](SAMPLE_DASHBOARD.md)
เปิด [ตัวอย่างข้อมูลสมมติบนเว็บ](https://zangkasi55.github.io/Copilot-Token-Dashboard/)
หรือ
ดาวน์โหลด [แดชบอร์ด HTML แบบออฟไลน์](assets/sample-dashboard.html)
แล้วเปิดใน Edge หรือ Chrome ได้โดยไม่ต้องมี tenant หรือเข้าสู่ระบบ

## 2. สิ่งที่ต้องเตรียม

| รายการ | ใช้สำหรับ |
|---|---|
| Windows และ Power BI Desktop รุ่นปัจจุบัน | เปิดและตรวจรายงานบนเครื่อง |
| Python 3.10 ขึ้นไป | ตัวเก็บข้อมูล การสร้างข้อมูลรายงาน และ deployment |
| PowerShell 7 | สคริปต์ติดตั้ง |
| Power BI Pro, PPU หรือ Fabric capacity ที่เหมาะสม | เผยแพร่และแชร์ตามเงื่อนไข license |
| สิทธิ์ Contributor ขึ้นไปใน workspace | สร้าง semantic model และรายงาน |
| Azure CLI หรือ Fabric access token ของ tenant เป้าหมาย | deployment แบบอัตโนมัติ |
| การอนุมัติสิทธิ์จากเจ้าของข้อมูล | เก็บข้อมูลจริงผ่าน API |

API ในรุ่นนี้ใช้ global commercial cloud ยังไม่ได้ยืนยัน sovereign cloud
หรือ GitHub host ที่กำหนดเอง ชุดนี้ไม่ได้แจกโปรแกรม Power BI Desktop

## 3. ดาวน์โหลดและตรวจชุด

ดาวน์โหลด ZIP ของรุ่นที่ต้องการจาก GitHub Releases
ตรวจ SHA-256 เทียบกับไฟล์ checksum แล้วแตกไฟล์ลงโฟลเดอร์ใหม่ เช่น
`C:\CopilotTokenDashboard`

```powershell
Set-Location C:\CopilotTokenDashboard
.\Install.ps1 -Action Validate -InstallDependencies
```

คำสั่งนี้ติดตั้งเฉพาะ dependency ที่ประกาศไว้ และตรวจข้อมูลสมมติทุกตาราง
ยังไม่สร้าง resource ใน tenant

อย่าปิด execution policy หรือมาตรการรักษาความปลอดภัยขององค์กร
ให้ใช้กระบวนการรันสคริปต์ที่องค์กรอนุมัติ

## 4. เปิดข้อมูลสาธิตบนเครื่อง

```powershell
.\Install.ps1 -Action Local -SourceMode Demo
```

สคริปต์สร้างโฟลเดอร์เฉพาะรุ่นใน local application data แล้วเปิด PBIP
ไม่เขียนทับโฟลเดอร์ติดตั้งเดิม หากมีโฟลเดอร์แล้วให้กำหนด `-InstallFolder`
เป็นโฟลเดอร์ใหม่

ใน Power BI Desktop:

1. รอให้โปรเจกต์เปิดเสร็จ แล้วกด Refresh ถ้ายังไม่มีข้อมูล
2. ตรวจป้ายข้อมูลสมมติและวันที่ Data through
3. เปิดตรวจรายงานครบทั้ง 10 หน้า
4. เลือก agent ด้วยตัวเลือกในหน้า Agent Detail
5. ใช้ Modeling > View as ทดสอบ role Viewer กับ UPN ตัวอย่าง

บุคคลตัวอย่างใช้โดเมน `example.com` และราคาตัวอย่างเป็นราคาสมมติ
ไม่ใช่ราคาผู้ให้บริการหรือ rate card ที่แนะนำ

## 5. Publish แบบทำด้วยตนเอง

วิธีนี้ไม่ต้องใช้ token สำหรับ deployment อัตโนมัติ:

1. ลงชื่อเข้าใช้ Power BI Desktop ด้วยบัญชีของ tenant ปลายทาง
2. สร้างหรือเลือก workspace ที่องค์กรอนุมัติ
3. Publish จาก Power BI Desktop
4. ตั้ง credentials และ Refresh ใน Power BI Service
5. เพิ่มกลุ่ม Entra ที่อนุมัติให้เป็นสมาชิก role Viewer ของ semantic model
6. ทดสอบด้วยผู้ใช้ Viewer จริงก่อนแชร์หรือสร้าง Power BI App

PBIT ต้องเปิดใน Desktop ก่อน แล้วสร้างรายงานจาก template
ไม่ใช่ไฟล์ที่ import ตรงเข้า Power BI Service REST API
PBIP เป็น source project สำหรับแก้ไขรายงานและโมเดล ไม่ใช่โปรแกรม Power BI

## 6. สร้างรายงานใน tenant แบบอัตโนมัติ

ต้องระบุ tenant และ workspace อย่างชัดเจน:

```powershell
.\Install.ps1 -Action Tenant -SourceMode Demo `
  -TenantId '<your-tenant-guid>' `
  -WorkspaceId '<your-workspace-guid>'
```

หากไม่มี `CTD_FABRIC_ACCESS_TOKEN` สคริปต์จะลงชื่อเข้าใช้ Azure CLI
ใน tenant ที่ระบุ หรือคุณอาจตั้ง token ที่องค์กรอนุมัติใน environment ของ process
สิทธิ์ที่ API ต้องการคือ SemanticModel.ReadWrite.All และ Report.ReadWrite.All
หรือ Item.ReadWrite.All

สคริปต์ตรวจว่า token เป็นของ tenant เป้าหมายก่อนส่งคำขอ
API ของ Microsoft ยังเป็นผู้ตรวจ signature, audience และสิทธิ์จริง

ระบบสร้าง semantic model ก่อน แล้วผูกรายงานด้วย model ID ที่สร้าง
รอผล long-running operation และไม่เขียนทับ item เดิมโดยเงียบ
ใช้ `-Update` หลังตรวจปลายทางและสำรอง definition แล้วเท่านั้น

สถานะที่ได้คือ **สร้าง resource แล้ว แต่ยังต้องตั้งค่าความปลอดภัยและ refresh**
ยังต้องกำหนดกลุ่ม RLS, credentials, gateway ถ้าจำเป็น, app audiences
และทดสอบ Viewer ก่อนถือว่าพร้อมใช้งานจริง

## 7. ใช้ข้อมูลของคุณเอง

อย่าใส่ข้อมูลจริงหรือ secret ลงในข้อมูลสาธิตแล้ว commit ขึ้น GitHub
ให้ทำงานในโฟลเดอร์ runtime ที่ถูกตัดออกจาก source control

```powershell
python -m pip install .
ctd collect-github --settings config\settings.json `
  --day 2026-05-28 --output runtime\incoming\github.jsonl
ctd collect-m365 --settings config\settings.json `
  --output runtime\incoming\m365.jsonl
```

คัดลอก settings.example.json เป็น settings.json ซึ่งถูก ignore ไว้
ใส่เฉพาะ tenant, app และรายละเอียด source ส่วนค่าจริงของ secret
อยู่ใน environment หรือ secret manager ที่องค์กรอนุมัติ

เตรียม People.csv, Scopes.csv และ ScopeAccess.csv ตาม data contract
รวม metadata ที่ผ่านการตรวจเป็น usage.jsonl
อาจเพิ่ม Models, Surfaces, Agents, Budgets และ Outcomes
รวมทั้ง period-summaries.jsonl จากรายงาน Microsoft 365

ห้ามกระจายยอดรวมของช่วงเวลาให้เป็นยอดรายวัน
และห้ามเดา cached tokens จากยอด input tokens

```powershell
ctd build-data --input runtime\incoming --output runtime\gold-2026-05-28
ctd validate-data --input runtime\gold-2026-05-28 --production
```

ข้อมูลจริงถูกสร้างโดยปิด demo mode
scope ที่ไม่ถึงเกณฑ์ถูกตัดออก และตัวเลขของแถวที่ถูก suppress ถูกล้างก่อนเข้าโมเดล
รายการที่ยังไม่มีราคาและรายการที่ยังระบุเจ้าของไม่ได้ยังคงถูกแจ้งอย่างชัดเจน

## 8. แหล่งข้อมูลใน Power BI

### CSV บนเครื่อง

```powershell
.\Install.ps1 -Action Local -SourceMode CSV `
  -DataFolder C:\CTD\runtime\gold-2026-05-28 `
  -InstallFolder C:\CTD\Customer-1.0.0
```

Power BI Service อ่านโฟลเดอร์บนเครื่องไม่ได้ถ้าไม่มี on-premises data gateway
snapshot ที่ Publish แล้วดูได้ แต่ไม่ใช่ pipeline สดที่ refresh ได้เอง

### SharePoint ใน tenant ของคุณ

อัปโหลด CSV ครบทั้งรุ่นข้อมูลที่ตรวจแล้วไปยังโฟลเดอร์ที่อนุมัติ
กำหนด URL ของ site และ folder ให้ตรง รวม slash ท้าย folder
และใช้ organizational OAuth credentials

```powershell
.\Install.ps1 -Action Tenant -SourceMode SharePoint `
  -TenantId '<your-tenant-guid>' -WorkspaceId '<your-workspace-guid>' `
  -DataFolder C:\CTD\runtime\gold-2026-05-28 `
  -SharePointSite 'https://<your-tenant>.sharepoint.com/sites/AIReporting' `
  -SharePointFolder 'https://<your-tenant>.sharepoint.com/sites/AIReporting/Shared Documents/Gold/'
```

DataFolder เป็นสำเนาบนเครื่องที่ตรวจแล้วสำหรับ preflight
หลัง deployment โมเดลอ่าน SharePoint ไม่ได้อ่านสำเนานั้น
ต้องพบชื่อไฟล์และ folder ตรงกันเพียงไฟล์เดียว ไม่เช่นนั้นเกิด error
credentials ไม่ได้รวมอยู่ในโมเดล

## 9. ความปลอดภัยก่อน go-live

- ใช้ role Viewer; การซ่อนหน้าใน App ไม่ใช่การป้องกันข้อมูล
- ผู้ใช้ทั่วไปควรมี Viewer หรือ app access ไม่ใช่ Member หรือ Contributor
- ไม่ให้ Build หรือ export กว้างโดยไม่มีการทบทวนข้อมูล
- ติด sensitivity label ของ tenant คุณเอง
- ทดสอบว่าผู้ใช้ A ไม่เห็น personal rows ของผู้ใช้ B
- ตรวจ scope เล็กกว่าเกณฑ์หกคนและตัวเลขแถวที่ถูก suppress
- ตั้ง refresh หลังอัปโหลดข้อมูลครบทั้ง generation แล้วเท่านั้น
- ตรวจสิทธิ์ API และ credentials ใน tenant ปลายทางจริง
- ตรวจว่าไม่มีบุคคลสมมติคงอยู่ในข้อมูล production
- ทบทวนสิทธิ์และ coverage ตามรอบ

ผู้ดูแล workspace bypass RLS ตามการทำงานของ Power BI
จึงต้องเป็นผู้ดูแลข้อมูลที่เชื่อถือได้ ชุดนี้ไม่ใช่การรับรอง PDPA หรือ GDPR
และไม่ใช่เครื่องมือวัดผลการทำงานของพนักงาน

## 10. การแก้ปัญหา

| อาการ | สิ่งที่ควรตรวจ |
|---|---|
| Dependency ไม่ครบ | ติดตั้งเฉพาะ package ที่ประกาศไว้ |
| CSV header หรือ type ไม่ตรง | ตรวจชื่อ ลำดับ และชนิดตาม contract |
| Token หรือ cache ไม่มีข้อมูล | ตรวจ coverage ไม่แทนด้วยศูนย์ |
| ยอดค่าใช้จ่ายไม่ตรง | ตรวจ billed/estimated, unattributed และ privacy suppression |
| Personal view ว่าง | ตรวจ UPN mapping และสมาชิก role Viewer |
| Organization scope ว่าง | ตรวจสิทธิ์ scope และเกณฑ์หกคน |
| HTTP 403 | ขอ consent หรือ role ที่ถูกต้อง ไม่ bypass |
| Item เดิมมีอยู่แล้ว | ตรวจปลายทางก่อนใช้ Update |
| Refresh ล้มเหลว | ตรวจ credentials, gateway และ folder permission |
| Operation timeout | ตรวจ workspace ก่อนสร้าง item ซ้ำ |

## 11. คู่มือภาพประกอบแดชบอร์ดตัวอย่าง

ภาพต่อไปนี้จับจากแดชบอร์ดสาธิตบนเบราว์เซอร์ โดยใช้ CSV ข้อมูลสมมติที่มากับชุด
**ไม่ใช่ภาพ Power BI Desktop ที่ยืนยันการทำงานแล้ว**
รูปแบบและสีของตัวอย่างต่างจาก Power BI และไม่ได้รัน DAX เรียก API
ตรวจการเข้าสู่ระบบ หรือบังคับ RLS ต้องทดสอบโปรเจกต์ Power BI จริงใน tenant
ของคุณก่อนยอมรับว่าใช้งาน production ได้

ภาพ 1–6 และ 8–10 ใช้ **Last 28 days** และ **Example engineering team**
ภาพ 7 ใช้ **Example operations team**
หน้าส่วนตัวใช้บุคคลสมมติ **user01@example.com**
วันที่ข้อมูลตัวอย่างคือ **2026-05-28**
คลิกภาพบน GitHub เพื่อดู PNG ต้นฉบับความกว้าง 1600 พิกเซล
PDF ฝังภาพไว้ในไฟล์และขยายดูรายละเอียดแบบออฟไลน์ได้

### ภาพที่ 1. Overview: ตรวจขอบเขตและวันที่ข้อมูล

![ภาพที่ 1 Overview จากเบราว์เซอร์และข้อมูลสมมติ ไม่ใช่ภาพ Power BI ที่ยืนยันการทำงานแล้ว](images/01-overview.png)

1. ตรวจป้าย SYNTHETIC DEMO และวันที่ Data through ก่อนอ่านค่า
2. ตัวอย่างทีม engineering มียอดที่ทราบใน 28 วัน **USD 468.48**
   ผู้ใช้ที่มีข้อมูล **12 คน** agent ที่มีการใช้งาน **1 ตัว**
   และ token ที่รายงาน **644,590**
3. กราฟรายสัปดาห์แสดงสัปดาห์ที่จบแล้ว ไม่ย้อนนำยอดล่าสุดไปใส่ในสัปดาห์เก่า
   ราคาการใช้งาน Word ที่ไม่มีรายงานไม่ถูกแทนด้วยศูนย์

### ภาพที่ 2. My AI Usage: ตรวจหน้าส่วนตัวสมมติ

![ภาพที่ 2 การใช้งานส่วนตัวสมมติของ user01@example.com ไม่ใช่ภาพ Power BI ที่ยืนยันการทำงานแล้ว](images/02-personal.png)

บุคคลตัวอย่างมียอด **USD 34.00 ในเจ็ดวัน**
**USD 39.04 ใน 28 วัน** และ **USD 39.04 ตั้งแต่ต้นเดือน**
ตารางแสดงบัญชีที่ปิดบังบางส่วน token ของโมเดล และข้อมูลที่ไม่มีรายงานอย่างชัดเจน

ใน Power BI จริงต้องทดสอบ role Viewer ด้วย UPN จริงอย่างน้อยสองบัญชี
อย่าใช้บุคคลคงที่ใน HTML นี้เป็นหลักฐานว่า RLS ของ tenant ทำงานแล้ว

### ภาพที่ 3. Organization Usage: เข้าใจความเป็นส่วนตัว

![ภาพที่ 3 ข้อมูลรวมขององค์กรจากเบราว์เซอร์และข้อมูลสมมติ ไม่ใช่ภาพ Power BI ที่ยืนยันการทำงานแล้ว](images/03-organization.png)

ทีม engineering มี **12 คน**
ทีมตัวอย่างขนาดสี่คนไม่อยู่ในรายการ scope ที่เผยแพร่ เพราะเกณฑ์ขั้นต่ำคือหกคน
High engagement หมายถึงมีข้อมูลกิจกรรมอย่างน้อยสี่วันในสัปดาห์ที่จบแล้ว
ไม่ใช่คะแนนผลงาน HTML ไม่มีระบบกำหนดสิทธิ์จริง
การป้องกัน production มาจาก pipeline ที่ตรวจแล้วและ role Viewer ของ Power BI

### ภาพที่ 4. Adoption and Momentum: อ่านอัตราเติบโตให้ถูก

![ภาพที่ 4 การยอมรับและความเข้มข้นของการใช้งานสมมติ ไม่ใช่ภาพ Power BI ที่ยืนยันการทำงานแล้ว](images/04-momentum.png)

เปรียบเทียบหกสัปดาห์ล่าสุดที่จบแล้วกับหกสัปดาห์ก่อนหน้า
จำนวนผู้ใช้และ requests ต่อ active user-week เป็นคนละตัววัด
ตัวอย่าง build helper อยู่กลุ่ม **Stable** แม้ค่าใช้จ่ายล่าสุดพุ่งสูง
เพราะยอดพุ่งอยู่นอกช่วงเปรียบเทียบสัปดาห์ที่จบแล้ว

### ภาพที่ 5. Agents: ตรวจสัญญาณค่าใช้จ่าย

![ภาพที่ 5 รายการ agent และสัญญาณค่าใช้จ่ายจากข้อมูลสมมติ ไม่ใช่ภาพ Power BI ที่ยืนยันการทำงานแล้ว](images/05-agents.png)

build helper ตัวอย่างมี **384 runs** ในช่วงที่เลือก
ยอดเจ็ดวันล่าสุดคือ **USD 408.00** เทียบค่าเฉลี่ยรายสัปดาห์ของสี่สัปดาห์ก่อนหน้า
**USD 20.16** ตรวจ workload และ coverage แทนการใช้สัญญาณนี้ตัดสินผลงานบุคคล
การส่งแจ้งเตือนต้องมี automation ที่องค์กรอนุมัติต่างหาก

### ภาพที่ 6. Agent Detail: เลือก agent ตัวอย่าง

![ภาพที่ 6 รายละเอียด agent จากเบราว์เซอร์และข้อมูลสมมติ ไม่ใช่ภาพ Power BI ที่ยืนยันการทำงานแล้ว](images/06-agent-detail.png)

เปิด Agent Detail แล้วใช้ตัวเลือก agent
ต้นทุนที่ทราบต่อ run ของ build helper ประมาณ **USD 1.22**
ค่าประหยัดเวลาเจ็ดนาทีครึ่งต่อ run เป็นสมมติฐานของเจ้าของในข้อมูลสาธิต
ไม่ใช่ผลประโยชน์ที่วัดได้จริง

หาก agent ไม่มีข้อมูลใน scope ปัจจุบัน ให้เลือก scope ที่มีสิทธิ์และมีข้อมูล
อย่าสร้างตัวเลขทดแทนข้อมูลที่ขาด

### ภาพที่ 7. Agent Outcomes: ใช้ตัวอย่างทีม operations

![ภาพที่ 7 ผลลัพธ์งานสมมติของทีม operations ไม่ใช่ภาพ Power BI ที่ยืนยันการทำงานแล้ว](images/07-outcomes.png)

เลือก **Example operations team** ตัวอย่างมีงานที่ปิดแล้ว **56 รายการ**
แบ่งเป็นคนทำเอง 20 รายการ agent ช่วย 18 รายการ และ agent ปิดเอง 18 รายการ
ชั่วโมงตั้งแต่เปิดจนปิดกับเวลาที่คนลงมือทำเป็นคนละปริมาณ
การเปรียบเทียบนี้ไม่พิสูจน์เหตุและผล และไม่แทนการตรวจข้อมูล ITSM จริงของคุณ

### ภาพที่ 8. Value and Budget: ทดลองสมมติฐาน

![ภาพที่ 8 สมมติฐานคุณค่าและงบประมาณจากข้อมูลสมมติ ไม่ใช่ภาพ Power BI ที่ยืนยันการทำงานแล้ว](images/08-value.png)

ที่ **USD 20 ต่อชั่วโมง** build helper มีเวลาประหยัดโดยประมาณ **48 ชั่วโมง**
และคุณค่าแบบ scenario **USD 960.00**
เปลี่ยน slider เป็น USD 40 แล้วค่าเพิ่มเป็น USD 1,920.00
แต่ค่าใช้จ่ายที่วัดไม่เปลี่ยน และไม่ได้พิสูจน์ productivity
งบประมาณถูกเฉลี่ยตามวันที่ anchor ที่แสดง

### ภาพที่ 9. Models and Efficiency: ตรวจยอดที่ทราบ

![ภาพที่ 9 โมเดลและ token จากเบราว์เซอร์และข้อมูลสมมติ ไม่ใช่ภาพ Power BI ที่ยืนยันการทำงานแล้ว](images/09-models.png)

Input รวม cached-input อยู่แล้ว **อย่าบวก cached tokens ซ้ำ**
ตรวจยอดรวมโมเดลและ surface เทียบยอด scope รวมทั้งส่วนต่างที่ซ่อนเพื่อความเป็นส่วนตัว
cache ในข้อมูลสมมติไม่ได้รับประกันว่า API ของ Microsoft 365 หรือ GitHub
ให้ข้อมูลเหมือนกันใน production

### ภาพที่ 10. Data Quality and Guide: ทำ checklist ให้ครบ

![ภาพที่ 10 coverage และขั้นตอนติดตั้งจากข้อมูลสมมติ ไม่ใช่ภาพ Power BI ที่ยืนยันการทำงานแล้ว](images/10-guide.png)

ตารางตัวอย่างมี source-field ที่รายงานได้ **8 รายการ**
บางส่วน **0 รายการ** และไม่มีรายงาน **4 รายการ**
นี่เป็นข้อมูลสาธิต ไม่ใช่ผลทดสอบการเชื่อมต่อสด
ทำ Validate ตรวจ Desktop ตั้ง tenant และ source ทดสอบ Viewer
และยืนยัน refresh ก่อนแชร์

ดูวิธีทดลอง HTML แบบออฟไลน์และภาพต้นฉบับครบทุกหน้าได้ใน
[แกลเลอรีแดชบอร์ดตัวอย่าง](SAMPLE_DASHBOARD.md)
