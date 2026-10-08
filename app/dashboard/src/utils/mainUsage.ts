// Same bounds as MainUsageSettings. Do not turn an empty draft into zero.
export function parseMainUsageRate(value: string): number | null {
  if (!/^\d+(\.\d{1,5})?$/.test(value)) return null;
  const rate = Number(value);
  return Number.isFinite(rate) && rate > 0 && rate <= 1000 ? rate : null;
}

export function syncMainUsageDraft(draft: string, dirty: boolean, saved: number): string {
  return dirty ? draft : String(saved);
}
