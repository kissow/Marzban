const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const component = fs.readFileSync(path.join(root, 'src/components/MainUsageCard.tsx'), 'utf8');
const modal = fs.readFileSync(path.join(root, 'src/components/NodesModal.tsx'), 'utf8');
const helper = fs.readFileSync(path.join(root, 'src/utils/mainUsage.ts'), 'utf8');
const namespace = { exports: {} };
vm.runInNewContext(ts.transpileModule(helper, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, namespace);

test('coefficient validation executes actual production utility', () => {
  for (const value of ['', '0', '-1', '1.123456', '0.000001', '1001', 'NaN', 'Infinity', '1e2']) {
    assert.equal(namespace.exports.parseMainUsageRate(value), null, value);
  }
  for (const value of ['1', '0.00001', '0.29', '2.5', '1000', '1.00000']) {
    assert.equal(namespace.exports.parseMainUsageRate(value), Number(value));
  }
});

test('refetch preserves dirty draft and refreshes pristine draft', () => {
  assert.equal(namespace.exports.syncMainUsageDraft('2.5', true, 1), '2.5');
  assert.equal(namespace.exports.syncMainUsageDraft('1', false, 2), '2');
});

test('card precedes existing nodes without changing original layout or forms', () => {
  assert.ok(modal.indexOf('<MainUsageCard enabled={isEditingNodes} />') < modal.indexOf('<Accordion w="full"'));
  assert.match(modal, /maxW="800px"/);
  for (const item of ['Cert', 'NodeHealthCard', 'NodeRelayCard', 'NodeEgressCard', 'api_port', 'usage_coefficient']) assert.ok(modal.includes(item));
  assert.match(component, /columns=\{\{ base: 1, sm: 2 \}\}/);
  assert.ok(!component.includes('<form'));
  assert.ok(!component.includes('maxW="800px"'));
});

test('save is independent, authenticated through existing http service and guarded', () => {
  assert.match(component, /from "service\/http"/);
  assert.match(component, /method: "PUT", body: \{ usage_coefficient: numericRate \}/);
  assert.equal((component.match(/fetch(?:<Settings>)?\("\/node\/main\/usage"/g) || []).length, 2);
  assert.match(component, /!query\.isError && !query\.isFetching && !save\.isLoading/);
  assert.match(component, /if \(canSave\) save\.mutate\(\)/);
  assert.match(component, /onError: error => \{ generateErrorMessage/);
  for (const denied of ['/reconnect', '/core/restart', 'updateNode', 'nodeId']) assert.ok(!component.includes(denied));
});

test('original info icon supports mouse touch keyboard and retry preserves draft', () => {
  assert.match(component, /InformationCircleIcon/);
  for (const handler of ['onMouseEnter', 'onMouseLeave', 'onFocus', 'onBlur', 'onClick', 'onKeyDown']) assert.ok(component.includes(handler));
  assert.match(component, /event\.stopPropagation\(\)/);
  assert.match(component, /onClick=\{\(\) => query\.refetch\(\)\}/);
  assert.match(component, /disabled=\{!query\.data \|\| query\.isError \|\| save\.isLoading\}/);
});

test('all four locales contain every main usage label and interpolation', () => {
  const keys = [...new Set([...component.matchAll(/"(nodes\.mainUsage\.[a-zA-Z]+)"/g)].map(match => match[1]))];
  for (const locale of ['en', 'zh', 'ru', 'fa']) {
    const strings = JSON.parse(fs.readFileSync(path.join(root, `public/statics/locales/${locale}.json`), 'utf8'));
    for (const key of keys) assert.ok(typeof strings[key] === 'string' && strings[key].trim(), `${locale}: ${key}`);
    assert.match(strings['nodes.mainUsage.example'], /\{\{rate\}\}/);
  }
});

test('actual React/Chakra card renders the saved rate in all menu languages', async () => {
  const React = require('react');
  const { renderToString } = require('react-dom/server');
  const { ChakraProvider } = require('@chakra-ui/react');
  const { QueryClient, QueryClientProvider } = require('react-query');
  const { I18nextProvider } = require('react-i18next');
  const i18next = require('i18next');
  function loadTs(source, localImports = {}) {
    const box = { exports: {}, require: name => localImports[name] || require(name) };
    vm.runInNewContext(ts.transpileModule(source, { compilerOptions: {
      module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
    } }).outputText, box);
    return box.exports;
  }
  const input = loadTs(fs.readFileSync(path.join(root, 'src/components/Input.tsx'), 'utf8'));
  const theme = loadTs(fs.readFileSync(path.join(root, 'chakra.config.ts'), 'utf8')).theme;
  const card = loadTs(component, {
    'service/http': { fetch: () => { throw new Error('SSR must never contact a server'); } },
    'utils/toastHandler': { generateErrorMessage: () => {} },
    'utils/mainUsage': namespace.exports, './Input': input,
  }).MainUsageCard;
  for (const lang of ['en', 'zh', 'ru', 'fa']) {
    const strings = JSON.parse(fs.readFileSync(path.join(root, `public/statics/locales/${lang}.json`), 'utf8'));
    const i18n = i18next.createInstance();
    await i18n.init({ lng: lang, resources: { [lang]: { translation: strings } }, interpolation: { escapeValue: false } });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, cacheTime: Infinity } } });
    client.setQueryData('main-usage-settings', { usage_coefficient: 2.5 });
    const html = renderToString(React.createElement(ChakraProvider, { theme },
      React.createElement(QueryClientProvider, { client }, React.createElement(I18nextProvider, { i18n },
        React.createElement(card, { enabled: true })))));
    assert.ok(html.includes(strings['nodes.mainUsage.title']), lang);
    assert.ok(html.includes(strings['nodes.mainUsage.save']), lang);
    assert.match(html, /value="2\.5"/);
    assert.match(html, /data-testid="main-usage-card"/);
    client.clear();
  }
});
