const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { blocks, html, pngImage } = require("../tools/build_manuals.cjs");

test("Markdown images remain images rather than flattened links", () => {
  const parsed = blocks("Before\n![Synthetic overview](images/01-overview.png)\nAfter");
  assert.deepEqual(parsed.map(block => block.kind), ["paragraph", "image", "paragraph"]);
  assert.equal(parsed[1].text, "Synthetic overview");
  assert.equal(parsed[1].target, "images/01-overview.png");
});

test("illustrated HTML embeds the PNG and readable provenance caption", () => {
  const result = html(blocks("![Synthetic browser-rendered overview, not Power BI](images/01-overview.png)"), "en");
  assert.match(result, /<figure><img src="data:image\/png;base64,/);
  assert.match(result, /<figcaption>Synthetic browser-rendered overview, not Power BI<\/figcaption>/);
  assert.match(result, /--cp-accent: #b11f4b;/);
  assert.match(result, /--cp-accent: #fd8ea1;/);
  assert.doesNotMatch(result, /src="images\//);
});

test("image loading does not allow paths outside documentation", () => {
  assert.throws(() => pngImage("../README.md"), /local PNGs/);
  assert.throws(() => pngImage("https://example.com/image.png"));
  assert.throws(() => pngImage("images/missing-image.png"));
});

test("all ten figures are embedded into both installation manual variants", () => {
  for (const language of ["EN", "TH"]) {
    const filename = language === "EN" ? "INSTALLATION.md" : "INSTALLATION_TH.md";
    const content = fs.readFileSync(path.join(__dirname, "..", "docs", filename), "utf8");
    const rendered = html(blocks(content), language === "EN" ? "en" : "th");
    assert.equal((rendered.match(/<figure>/g) || []).length, 10);
    assert.equal((rendered.match(/src="data:image\/png;base64,/g) || []).length, 10);
  }
});
