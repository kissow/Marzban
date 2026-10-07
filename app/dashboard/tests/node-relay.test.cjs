const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const component = fs.readFileSync(path.join(root, 'src/components/NodeRelayCard.tsx'), 'utf8');
const modal = fs.readFileSync(path.join(root, 'src/components/NodesModal.tsx'), 'utf8');

test('relay preview describes a path, never creates or renames a subscription entry', () => {
  assert.ok(!component.includes('(Relay)'));
  assert.match(component, /main\.example\.com/);
  const share = fs.readFileSync(path.join(root, '../subscription/share.py'), 'utf8');
  assert.match(share, /for host in subscription_hosts\(tag\):/);
  assert.ok(!share.includes('*subscription_hosts(tag)'));
});

test('relay uses existing Node modal/theme without replacing certificates or controls', () => {
  assert.match(modal, /maxW="800px"/);
  for (const name of ['NodeRelayCard', 'NodeEgressCard', 'NodeHealthCard', 'Cert']) assert.ok(modal.includes(name));
  for (const field of ['api_port', 'usage_coefficient', 'port', 'address', 'name']) assert.ok(modal.includes(field));
  assert.match(component, /columns=\{\{ base: 1, md: 2 \}\}/);
  assert.ok(!component.includes('<form'));
  assert.ok(!component.includes('window.location'));
});

test('relay strings are present in all four existing locales', () => {
  const keys = [...new Set([...component.matchAll(/"(nodes\.relay\.[a-zA-Z]+)"/g)].map(match => match[1]))];
  for (const locale of ['en', 'zh', 'ru', 'fa']) {
    const strings = JSON.parse(fs.readFileSync(path.join(root, `public/statics/locales/${locale}.json`), 'utf8'));
    for (const key of [...keys, ...['inactive', 'pending', 'running', 'error'].map(status => `nodes.relay.status.${status}`)]) {
      assert.equal(typeof strings[key], 'string', `${locale}: ${key}`);
      assert.ok(strings[key].trim());
    }
  }
});

test('relay persists only its own API and does not submit the original Node form', () => {
  assert.match(component, /method: "PUT"/);
  assert.match(component, /\/node\/\$\{nodeId\}\/relay/);
  assert.match(component, /\/nodes\/relay\/options/);
  assert.match(component, /source: form\.source/);
  assert.match(component, /source_node_id: form\.source === "node" \? Number\(form\.sourceId\) : null/);
  assert.match(component, /type="button" size="sm" colorScheme="primary"/);
  assert.ok(!component.includes('/reconnect'));
  assert.ok(!component.includes('privateKey'));
});

test('automatic allocation does not display an unsaved manual port as assigned', () => {
  assert.match(component, /form\.allocation === "auto" \? automaticPort : form\.port/);
  assert.match(component, /listen_port: form\.allocation === "manual" \? Number\(form\.port\) : null/);
  assert.match(component, /if \(dirty \|\| !query\.data\) return/);
  assert.match(component, /!options\.isError/);
});

test('relay settings use a separate responsive Chakra modal and original info icon', () => {
  assert.ok(!component.includes('Collapse'));
  assert.match(component, /size="xs" variant="outline" colorScheme="primary" onClick=\{openManager\}/);
  assert.match(component, /<Modal isOpen=\{modal.isOpen\}/);
  assert.match(component, /scrollBehavior="inside"/);
  assert.match(component, /calc\(100vw - 24px\)/);
  assert.match(component, /InformationCircleIcon/);
  for (const handler of ['onMouseEnter', 'onMouseLeave', 'onFocus', 'onBlur', 'onClick', 'onKeyDown']) assert.ok(component.includes(handler));
  assert.match(component, /aria-expanded=\{visible\}/);
  assert.match(component, /event\.stopPropagation\(\)/);
  assert.match(component, /closeOnEsc=\{!save.isLoading\}/);
  assert.match(component, /closeOnOverlayClick=\{!save.isLoading\}/);
});

test('source selection excludes self and offline Nodes and invalidates old automatic-port preview', () => {
  assert.match(component, /item\.id !== nodeId/);
  assert.match(component, /disabled=\{!item.connected\}/);
  assert.match(component, /sourceValid/);
  assert.match(component, /query\.data\?\.source === form\.source/);
  assert.match(component, /source_node_id \|\| ""\) === form\.sourceId/);
  assert.match(component, /save\.reset\(\); modal.onOpen\(\); query.refetch\(\)/);
  assert.match(component, /if \(!save.isLoading\)/);
});
