const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { createHash } = require("node:crypto");
const vm = require("node:vm");
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

test("all ten native figures are embedded into both installation manual variants", () => {
  for (const language of ["EN", "TH"]) {
    const filename = language === "EN" ? "INSTALLATION.md" : "INSTALLATION_TH.md";
    const content = fs.readFileSync(path.join(__dirname, "..", "docs", filename), "utf8");
    const parsed = blocks(content);
    const figures = parsed.filter(block => block.kind === "image");
    assert.equal(figures.length, 10);
    for (const figure of figures) {
      assert.match(figure.target, /^images\/native\/\d{2}-[a-z-]+\.png$/);
      assert.match(figure.text, /Power BI Desktop/);
    }
    const rendered = html(parsed, language === "EN" ? "en" : "th");
    assert.equal((rendered.match(/<figure>/g) || []).length, 10);
    assert.equal((rendered.match(/src="data:image\/png;base64,/g) || []).length, 10);
  }
});

test("native screenshot provenance matches every report page and original PNG", () => {
  const root = path.join(__dirname, "..");
  const provenance = JSON.parse(fs.readFileSync(
    path.join(root, "docs", "images", "native", "provenance.json"), "utf8").replace(/^\uFEFF/, ""));
  const report = JSON.parse(fs.readFileSync(path.join(root, "powerbi", "build-manifest.json"), "utf8"));
  assert.equal(provenance.kind, "native-power-bi-desktop");
  assert.equal(provenance.synthetic_data, true);
  assert.equal(provenance.account_chrome_included, false);
  assert.equal(provenance.browser_reconstruction, false);
  assert.equal(provenance.live_sources_verified, false);
  assert.equal(provenance.data_through, "2026-05-28");
  assert.match(provenance.application_version, /^2\.\d+\.\d+\.\d+$/);
  assert.equal(provenance.page_count, 10);
  assert.equal(provenance.pages.length, 10);
  assert.deepEqual(provenance.pages.map(page => [page.page, page.title]),
    report.pages.map(page => [page.name, page.title]));
  assert.equal(new Set(provenance.pages.map(page => page.image)).size, 10);
  for (const page of provenance.pages) {
    assert.match(page.image, /^\d{2}-[a-z-]+\.png$/);
    const image = pngImage("images/native/" + page.image);
    assert.equal(image.width, page.width);
    assert.equal(image.height, page.height);
    assert.ok(image.width >= 1000 && image.height >= 1000);
    assert.equal(createHash("sha256").update(image.data).digest("hex"), page.sha256);
    assert.equal(page.visual_errors, 0);
    assert.equal(page.period, "Last 28 days");
    assert.ok(page.sample_values.includes("Data Banner SYNTHETIC DEMO - NOT LIVE DATA."));
  }
  const values = name => provenance.pages.find(page => page.page === name).sample_values;
  assert.ok(values("overview").includes("Scope Known Spend 468.48."));
  assert.ok(values("personal").includes("My Spend 7 Days 34.00."));
  assert.ok(values("personal").includes("My Spend 28 Days 39.04."));
  assert.ok(values("outcomes").includes("Resolved Work Items 56."));
  assert.ok(values("value").includes("Estimated Value 960.00."));
  assert.ok(values("guide").includes("My Model Reconciliation 0.0000."));
  assert.ok(values("guide").includes("Coverage Fields Partial (Blank)."));
});

test("the primary SCBX gallery and readme use actual native captures", () => {
  const root = path.join(__dirname, "..");
  const gallery = fs.readFileSync(path.join(root, "docs", "SAMPLE_DASHBOARD.md"), "utf8");
  const parsed = blocks(gallery);
  const figures = parsed.filter(block => block.kind === "image");
  assert.equal(figures.length, 10);
  for (const figure of figures) {
    assert.match(figure.target, /^images\/native\//);
    assert.match(figure.text, /Power BI Desktop/);
    assert.match(parsed[parsed.indexOf(figure) + 1].text, /\p{Script=Thai}/u);
  }
  const readme = fs.readFileSync(path.join(root, "README.md"), "utf8");
  assert.match(readme, /\]\(docs\/images\/native\/01-overview\.png\)/);
});

test("manual printing uses light colors and restores the screen theme afterwards", () => {
  const result = html(blocks("# Native screenshot manual"), "th");
  const script = [...result.matchAll(/<script>([\s\S]*?)<\/script>/g)]
    .find(match => match[1].includes("beforeprint"))[1];
  const listeners = new Map();
  let theme = "dark";
  vm.runInNewContext(script, {
    document: {
      documentElement: {
        getAttribute: name => { assert.equal(name, "data-theme"); return theme; },
        setAttribute: (name, value) => { assert.equal(name, "data-theme"); theme = value; },
      },
    },
    window: { addEventListener: (name, callback) => listeners.set(name, callback) },
  });
  assert.equal(theme, "dark");
  listeners.get("beforeprint")();
  assert.equal(theme, "light");
  listeners.get("afterprint")();
  assert.equal(theme, "dark");
  assert.match(result, /html\[lang="th"\] body\{font-family:"Segoe UI",Tahoma,/);
});
