const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const vm = require("node:vm");

const dashboard = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(dashboard, "index.html"), "utf8");
const source = fs.readFileSync(path.join(dashboard, "src/components/HostsDialog.tsx"), "utf8");
const ast = ts.createSourceFile("HostsDialog.tsx", source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

for (const tag of ["html", "body"]) {
  test(`${tag} protects React root and body-mounted Chakra portals from browser translation`, () => {
    const opening = html.match(new RegExp(`<${tag}\\b[^>]*>`))[0];
    assert.match(opening, /translate="no"/);
    assert.match(opening, /class="notranslate"/);
  });
}
test("Google translation opt-out is present before the application module", () => {
  assert.match(html, /<meta name="google" content="notranslate"\s*\/>/);
  assert.ok(html.indexOf('content="notranslate"') < html.indexOf('type="module"'));
});

// Inspect and render production JSX, rather than a duplicate of the status expressions.
for (const key of ["loading", "noInbound"]) {
  test(`hostsDialog.${key} is owned by a removable element, not a conditional bare text node`, () => {
    let call;
    const visit = node => {
      if (ts.isCallExpression(node) && node.expression.getText(ast) === "t" &&
          node.arguments[0]?.getText(ast) === `"hostsDialog.${key}"`) call = node;
      ts.forEachChild(node, visit);
    };
    visit(ast);
    assert.ok(call);
    assert.ok(ts.isJsxExpression(call.parent));
    const element = call.parent.parent;
    assert.ok(ts.isJsxElement(element), "Conditional status must have an element wrapper");
    assert.equal(element.openingElement.tagName.getText(ast), "Text");
    assert.match(element.openingElement.getText(ast), /as="span"/);
    const compiled = ts.transpileModule(`const result = (${element.getText(ast)});`, {
      compilerOptions: { jsx: ts.JsxEmit.React, target: ts.ScriptTarget.ES2020 },
    }).outputText;
    const Text = ({ as, children }) => React.createElement(as, null, children);
    for (const label of ["Loading…", "正在加载…", "Нет входящих", "در حال بارگذاری"]) {
      const result = vm.runInNewContext(compiled + "\nresult;", { React, Text, t: () => label });
      assert.equal(renderToStaticMarkup(result), `<span>${label}</span>`);
    }
  });
}
test("Translation protection does not disable native i18next or monkey-patch DOM methods", () => {
  const entry = fs.readFileSync(path.join(dashboard, "src/index.tsx"), "utf8");
  const i18n = fs.readFileSync(path.join(dashboard, "src/locales/i18n.ts"), "utf8");
  assert.match(entry, /import "locales\/i18n"/);
  assert.match(i18n, /languageChanged/);
  for (const content of [entry, source, html]) {
    assert.doesNotMatch(content, /Node\.prototype\.(removeChild|insertBefore)\s*=/);
  }
});
