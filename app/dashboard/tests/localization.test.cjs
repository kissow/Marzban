const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");
const i18next = require("i18next");
const dayjs = require("dayjs");
dayjs.extend(require("dayjs/plugin/duration"));

const dashboard = path.resolve(__dirname, "..");
const languages = ["en", "zh", "fa", "ru"];
const resources = Object.fromEntries(languages.map(language => [language, {
  translation: JSON.parse(fs.readFileSync(path.join(dashboard, "public/statics/locales", `${language}.json`), "utf8")),
}]));
const instance = i18next.createInstance();
instance.init({ resources, lng: "en", fallbackLng: false, initImmediate: false, interpolation: { escapeValue: false } });
const compiled = ts.transpileModule(fs.readFileSync(path.join(dashboard, "src/utils/dateFormatter.ts"), "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true },
}).outputText;
const moduleObject = { exports: {} };
vm.runInNewContext(compiled, { exports: moduleObject.exports, require, module: moduleObject, Date, Number });
const { relativeExpiryDate, relativeOnlineDate, parseLastOnline } = moduleObject.exports;
const now = Date.UTC(2026, 9, 5, 12, 0);
const second = 1000, minute = 60 * second, hour = 60 * minute, day = 24 * hour;
const samples = {
  en: ["6 days ago", "7 hours, 36 mins ago", "Not connected yet", "Online", "24 days"],
  zh: ["6 天前", "7 小时、36 分钟前", "尚未连接", "在线", "24 天"],
  fa: ["6 روز پیش", "7 ساعت، 36 دقیقه پیش", "هنوز متصل نشده", "آنلاین", "24 روز"],
  ru: ["6 дней назад", "7 часов, 36 минут назад", "Ещё не подключался", "В сети", "24 дня"],
};
const flatten = (object, prefix = "") => Object.fromEntries(Object.entries(object).flatMap(([key, value]) =>
  typeof value === "object" ? Object.entries(flatten(value, `${prefix}${key}.`)) : [[prefix + key, value]]));
const canonical = key => key.replace(/_(zero|one|two|few|many|other)$/, "");
const normalizedKeys = object => [...new Set(Object.keys(flatten(object)).map(canonical))].sort();
const placeholders = value => [...value.matchAll(/{{\s*([^}]+?)\s*}}/g)].map(match => match[1]).sort();

// Exercise the existing production schema, not a duplicated validation implementation.
const hostSource = fs.readFileSync(path.join(dashboard, "src/components/HostsDialog.tsx"), "utf8");
const hostAST = ts.createSourceFile("HostsDialog.tsx", hostSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const hostDeclaration = hostAST.statements.find(statement => ts.isVariableStatement(statement) &&
  statement.declarationList.declarations.some(declaration => declaration.name.getText(hostAST) === "hostsSchema"));
assert.ok(hostDeclaration, "Production hostsSchema exists");
const compileHostSchema = translate => vm.runInNewContext(
  ts.transpileModule(hostDeclaration.getText(hostAST), { compilerOptions: { target: ts.ScriptTarget.ES2020 } }).outputText + "\nhostsSchema;",
  { z: require("zod").z, translate }
);
const sampleHost = { remark: "Node 01", address: "node.example.com", port: "8443", path: null, sni: null,
  host: null, fragment_setting: null, noise_setting: null, security: "inbound_default", alpn: "", fingerprint: "" };

for (const language of languages) {
  const t = instance.getFixedT(language);
  const [daysAgo, hoursAgo, never, online, days] = samples[language];
  test(`${language}: existing host form required errors are localized`, () => {
    const schema = compileHostSchema(t);
    assert.equal(schema.parse({ INBOUND: [sampleHost] }).INBOUND[0].port, 8443);
    const parsed = schema.safeParse({ INBOUND: [{ ...sampleHost, remark: "", address: "" }] });
    assert.equal(parsed.success, false);
    assert.deepEqual(parsed.error.issues.map(issue => issue.message), [t("hostsDialog.remarkRequired"), t("hostsDialog.addressRequired")]);
  });
  test(`${language}: locale coverage, nonempty values, and interpolation parity`, () => {
    const entries = flatten(resources[language].translation);
    const english = flatten(resources.en.translation);
    assert.deepEqual(normalizedKeys(resources[language].translation), normalizedKeys(resources.en.translation));
    for (const [key, value] of Object.entries(entries)) {
      assert.equal(typeof value, "string", key);
      assert.ok(value.trim() || key === "time.separator", key);
      const baselineKey = Object.keys(english).find(candidate => canonical(candidate) === canonical(key));
      assert.deepEqual(placeholders(value), placeholders(english[baselineKey]), key);
    }
  });
  test(`${language}: screenshot last-online cases`, () => {
    assert.equal(relativeOnlineDate(new Date(now - 6 * day).toISOString(), t, now), daysAgo);
    assert.equal(relativeOnlineDate(new Date(now - 7 * hour - 36 * minute).toISOString(), t, now), hoursAgo);
    assert.equal(relativeOnlineDate(null, t, now), never);
    assert.equal(relativeOnlineDate("invalid", t, now), never);
  });
  test(`${language}: zero and sixty-second online boundaries`, () => {
    for (const age of [0, second, 60 * second]) {
      assert.equal(relativeOnlineDate(new Date(now - age).toISOString(), t, now), online);
    }
    assert.notEqual(relativeOnlineDate(new Date(now - 61 * second).toISOString(), t, now), online);
  });
  test(`${language}: future, past, unlimited and invalid expiry`, () => {
    const future = relativeExpiryDate((now + 24 * day) / second, t, now);
    assert.equal(future.status, "expires");
    assert.equal(future.time, days);
    assert.equal(relativeExpiryDate((now - 24 * day) / second, t, now).status, "expired");
    for (const value of [null, undefined, 0, NaN, Infinity]) {
      assert.equal(relativeExpiryDate(value, t, now).time, "");
    }
    assert.equal(relativeExpiryDate((now + 30 * second) / second, t, now).time, t("time.lessThanMinute"));
    assert.equal(relativeExpiryDate(now / second, t, now).time, t("time.lessThanMinute"));
  });
  test(`${language}: date units and plural forms resolve without fallback`, () => {
    for (const unit of ["year", "month", "day", "hour", "minute"]) {
      for (const count of [1, 2, 5, 11, 21, 24]) {
        const value = t(`time.${unit}`, { count });
        assert.ok(!value.includes("time.") && !value.includes("{{") && value.includes(String(count)), value);
      }
    }
    assert.ok(relativeExpiryDate((now + 400 * day) / second, t, now).time.includes(t("time.year", { count: 1 })));
    assert.ok(relativeExpiryDate((now + 55 * day) / second, t, now).time.includes(t("time.month", { count: 1 })));
  });
}

test("UTC timestamps with and without timezone have the same meaning", () => {
  assert.equal(parseLastOnline("2026-10-05T12:00:00"), now / second);
  assert.equal(parseLastOnline("2026-10-05T12:00:00Z"), now / second);
  assert.equal(parseLastOnline("2026-10-05T20:00:00+08:00"), now / second);
  assert.equal(parseLastOnline("2026-10-05T20:00:00+0800"), now / second);
  assert.equal(parseLastOnline("not a date"), null);
});

test("Russian plural forms distinguish 1, 2, 5, 21 and 24 days", () => {
  const t = instance.getFixedT("ru");
  for (const [count, expected] of [[1, "1 день"], [2, "2 дня"], [5, "5 дней"], [21, "21 день"], [24, "24 дня"]]) {
    assert.equal(t("time.day", { count }), expected);
  }
});

test("Every literal translation key in production TypeScript exists in all menu languages", () => {
  const visitDirectory = directory => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const filename = path.join(directory, entry.name);
      if (entry.isDirectory()) { visitDirectory(filename); continue; }
      if (!/\.tsx?$/.test(filename)) continue;
      const source = ts.createSourceFile(filename, fs.readFileSync(filename, "utf8"), ts.ScriptTarget.Latest, true);
      const visit = node => {
        if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === "t" && node.arguments[0] && ts.isStringLiteral(node.arguments[0])) {
          const key = node.arguments[0].text;
          for (const language of languages) assert.ok(instance.exists(key, { lng: language }), `${language}: ${key} (${entry.name})`);
        }
        ts.forEachChild(node, visit);
      };
      visit(source);
    }
  };
  visitDirectory(path.join(dashboard, "src"));
});

test("Same i18next instance switches existing duration labels immediately", async () => {
  for (const language of ["zh", "en", "fa", "ru", "zh"]) {
    await instance.changeLanguage(language);
    assert.equal(relativeExpiryDate((now + 24 * day) / second, instance.t.bind(instance), now).time, samples[language][4]);
  }
});

test("Status filters keep API values, not translated labels, on both layouts", () => {
  const source = fs.readFileSync(path.join(dashboard, "src/components/UsersTable.tsx"), "utf8");
  for (const status of ["active", "on_hold", "disabled", "limited", "expired"]) {
    assert.equal(source.split(`<option value="${status}">{t("status.${status}")}</option>`).length - 1, 2);
  }
  assert.ok(!source.includes("Sort by expire"));
});

test("Chinese regional menu choice resolves the same Chinese translations", async () => {
  await instance.changeLanguage("zh-cn");
  assert.equal(relativeOnlineDate(null, instance.t.bind(instance), now), "尚未连接");
  assert.equal(relativeExpiryDate((now + 24 * day) / second, instance.t.bind(instance), now).time, "24 天");
});

test("Host validation translates at validation time after a language change", async () => {
  const schema = compileHostSchema(instance.t.bind(instance));
  for (const language of ["zh", "ru", "fa", "en"]) {
    await instance.changeLanguage(language);
    assert.equal(schema.safeParse({ INBOUND: [{ ...sampleHost, remark: "" }] }).error.issues[0].message,
      instance.t("hostsDialog.remarkRequired"));
  }
});

test("Original host modal keeps desktop width and constrains narrow screens", () => {
  assert.ok(hostSource.includes('w="440px" maxW="calc(100vw - 24px)"'));
  assert.ok(hostSource.includes('<ModalBody w="full" minW={0}'));
  assert.ok(!hostSource.includes('<ModalBody w="440px"'));
  assert.ok(!hostSource.includes('overflowX="hidden"'));
  for (const viewport of [320, 360, 375, 390, 768, 1280]) {
    const constrainedWidth = Math.min(440, viewport - 24);
    assert.ok(constrainedWidth + 24 <= viewport);
    if (viewport >= 464) assert.equal(constrainedWidth, 440);
  }
});

test("Every host help popover is constrained; long text and host actions can wrap", () => {
  const popovers = [...hostSource.matchAll(/<PopoverContent\b[^>]*>/g)].map(match => match[0]);
  assert.equal(popovers.length, 9);
  for (const popover of popovers) {
    assert.ok(popover.includes('maxW="calc(100vw - 24px)"'));
    assert.ok(popover.includes('overflowY="auto"'));
    assert.ok(popover.includes('overflowWrap="anywhere"'));
  }
  assert.ok(hostSource.includes('flexWrap: "wrap"'));
});

test("Datepickers use the resolved menu language rather than raw browser region", () => {
  for (const file of ["UserDialog", "UsageFilter"]) {
    const source = fs.readFileSync(path.join(dashboard, `src/components/${file}.tsx`), "utf8");
    assert.ok(source.includes('locale={(i18n.resolvedLanguage || i18n.language).toLowerCase()}'));
  }
});
