const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, Header,
  Footer, PageNumber, HeadingLevel, WidthType, BorderStyle, ShadingType,
  LevelFormat, AlignmentType,
} = require("docx");

const root = path.resolve(__dirname, "..");
const destination = path.join(root, "docs", "manuals");
fs.mkdirSync(destination, { recursive: true });

const border = { style: BorderStyle.SINGLE, size: 4, color: "DCE4EC" };
const borders = { top: border, bottom: border, left: border, right: border };
const escape = value => value.replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
}[char]));
const clean = value => value.replace(/\*\*/g, "").replace(/`/g, "")
  .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 ($2)");

function blocks(markdown) {
  const lines = markdown.split(/\r?\n/);
  const result = [];
  let index = 0;
  let list = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index++; continue; }
    if (line.startsWith("```")) {
      const code = [];
      index++;
      while (index < lines.length && !lines[index].startsWith("```")) code.push(lines[index++]);
      result.push({ kind: "code", lines: code });
      index++;
    } else if (line.startsWith("|")) {
      const rows = [];
      while (index < lines.length && lines[index].startsWith("|")) {
        const value = lines[index++];
        if (/^\|[\s:|-]+\|$/.test(value)) continue;
        rows.push(value.split("|").slice(1, -1).map(cell => clean(cell.trim())));
      }
      result.push({ kind: "table", rows });
    } else if (/^#{1,3} /.test(line)) {
      const level = line.match(/^#+/)[0].length;
      result.push({ kind: "heading", level, text: clean(line.replace(/^#+ /, "")) });
      index++;
    } else if (/^[-*] /.test(line)) {
      result.push({ kind: "bullet", text: clean(line.slice(2)) });
      index++;
    } else if (/^\d+\. /.test(line)) {
      if (result[result.length - 1]?.kind !== "number") list++;
      result.push({ kind: "number", list, number: Number(line.match(/^\d+/)[0]),
        text: clean(line.replace(/^\d+\. /, "")) });
      index++;
    } else {
      const paragraph = [line];
      index++;
      while (index < lines.length && lines[index].trim() && !/^(#|\||```|[-*] |\d+\. )/.test(lines[index])) {
        paragraph.push(lines[index++]);
      }
      result.push({ kind: "paragraph", text: clean(paragraph.join(" ")) });
    }
  }
  return result;
}

function table(rows, font) {
  const count = Math.max(...rows.map(row => row.length));
  const widths = Array.from({ length: count }, (_, index) =>
    Math.floor(9360 / count) + (index === count - 1 ? 9360 % count : 0));
  return new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((row, index) => new TableRow({
      tableHeader: index === 0,
      children: widths.map((width, column) => new TableCell({
        width: { size: width, type: WidthType.DXA }, borders,
        margins: { top: 90, bottom: 90, left: 110, right: 110 },
        shading: { fill: index === 0 ? "E7F0FA" : "FFFFFF", type: ShadingType.CLEAR },
        children: [new Paragraph({ children: [new TextRun({
          text: row[column] || "", font, size: 19, bold: index === 0,
        })] })],
      })),
    })),
  });
}

function document(content, font) {
  const children = [];
  for (const block of content) {
    if (block.kind === "table") children.push(table(block.rows, font));
    else if (block.kind === "code") {
      for (const line of block.lines) children.push(new Paragraph({
        spacing: { before: 0, after: 30 },
        children: [new TextRun({ text: line || " ", font: "Consolas", size: 18 })],
      }));
    } else {
      const properties = {
        spacing: { before: 50, after: 110 },
        children: [new TextRun({ text: block.text, font })],
      };
      if (block.kind === "heading") properties.heading = [
        HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3,
      ][block.level - 1];
      if (block.kind === "bullet" || block.kind === "number") properties.numbering = {
        reference: block.kind === "bullet" ? "bullets" : "numbers-" + block.list, level: 0,
      };
      children.push(new Paragraph(properties));
    }
  }
  return new Document({
    title: "Copilot Token Dashboard Installation Guide",
    creator: "Copilot Token Dashboard contributors",
    description: "Public tenant-owned installation instructions; no customer data or credentials.",
    styles: {
      default: { document: { run: { font, size: 22 } } },
      paragraphStyles: [1, 2, 3].map(level => ({
        id: "Heading" + level, name: "Heading " + level, basedOn: "Normal",
        next: "Normal", quickFormat: true,
        run: { font, size: level === 1 ? 32 : level === 2 ? 27 : 24, bold: true, color: "17324D" },
        paragraph: { spacing: { before: 220, after: 140 }, outlineLevel: level - 1 },
      })),
    },
    numbering: { config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022",
        alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 420, hanging: 210 } } } }] },
      ...[...new Set(content.filter(block => block.kind === "number").map(block => block.list))].map(list => ({
        reference: "numbers-" + list,
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 420, hanging: 210 } } } }],
      })),
    ] },
    sections: [{
      properties: { page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1440, bottom: 1080, left: 1440 },
      } },
      headers: { default: new Header({ children: [
        new Paragraph({ children: [new TextRun({ text: "Copilot Token Dashboard | Public Installation Guide", font, size: 17, color: "52677A" })] }),
      ] }) },
      footers: { default: new Footer({ children: [
        new Paragraph({ alignment: AlignmentType.RIGHT, children: [
          new TextRun({ text: "1.0.0 | ", font, size: 17 }),
          new TextRun({ children: [PageNumber.CURRENT], font, size: 17 }),
        ] }),
      ] }) },
      children,
    }],
  });
}

function html(content, language) {
  const output = content.map(block => {
    if (block.kind === "heading") return `<h${block.level}>${escape(block.text)}</h${block.level}>`;
    if (block.kind === "table") return "<table>" + block.rows.map((row, index) =>
      "<tr>" + row.map(cell => `<${index === 0 ? "th" : "td"}>${escape(cell)}</${index === 0 ? "th" : "td"}>`).join("") + "</tr>").join("") + "</table>";
    if (block.kind === "code") return "<pre><code>" + escape(block.lines.join("\n")) + "</code></pre>";
    if (block.kind === "bullet") return "<p class=\"list\">&#8226; " + escape(block.text) + "</p>";
    if (block.kind === "number") return "<p class=\"list\">" + block.number + ". " + escape(block.text) + "</p>";
    return "<p>" + escape(block.text) + "</p>";
  }).join("\n");
  return `<!doctype html><html lang="${language}"><head><meta charset="utf-8">
<title>Copilot Token Dashboard Installation Guide</title><style>
@page{size:Letter;margin:18mm 20mm}body{font-family:Tahoma,Arial,sans-serif;font-size:10.5pt;line-height:1.5;color:#17324d}
h1{font-size:21pt}h2{font-size:15pt;margin-top:18pt}h3{font-size:12pt}h1,h2,h3{break-after:avoid}
table{width:100%;border-collapse:collapse;font-size:9pt;margin:12pt 0}td,th{border:1px solid #dce4ec;padding:6pt;text-align:left}
th{background:#e7f0fa}tr{break-inside:avoid}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f9;padding:10pt;font-size:8.5pt}
p{margin:6pt 0}.list{padding-left:12pt}code{font-family:Consolas,monospace}
</style></head><body>${output}</body></html>`;
}

async function main() {
  const contract = JSON.parse(fs.readFileSync(path.join(root, "sample_data", "data-contract.json"), "utf8"));
  const sections = ["# Data Contract", "", "Generated from the shared schema. CSV column order is part of the contract.", ""];
  for (const [name, columns] of Object.entries(contract.tables)) {
    sections.push("## " + name, "", "| Column | Type |", "|---|---|");
    for (const [column, type] of Object.entries(columns)) sections.push(`| ${column} | ${type} |`);
    sections.push("");
  }
  fs.writeFileSync(path.join(root, "docs", "DATA_CONTRACT.md"), sections.join("\n"), "utf8");
  for (const [file, suffix, font, language] of [
    ["INSTALLATION.md", "EN", "Arial", "en"], ["INSTALLATION_TH.md", "TH", "Tahoma", "th"],
  ]) {
    const content = blocks(fs.readFileSync(path.join(root, "docs", file), "utf8"));
    const base = path.join(destination, `Copilot Token Dashboard - Installation ${suffix}`);
    fs.writeFileSync(base + ".docx", await Packer.toBuffer(document(content, font)));
    fs.writeFileSync(base + ".html", html(content, language), "utf8");
    console.log("Built public manual: " + suffix);
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
