import dayjs from "dayjs";
import { t as translate, TFunction } from "i18next";

export const relativeExpiryDate = (
  expiryDate: number | null | undefined,
  t: TFunction = translate,
  now: number = Date.now()
) => {
  let dateInfo = { status: "", time: "" };
  if (expiryDate && Number.isFinite(expiryDate)) {
    const difference = expiryDate * 1000 - now;
    dateInfo.status = difference > 0 ? "expires" : "expired";
    const durationSlots: string[] = [];
    const duration = dayjs.duration(Math.abs(difference));
    const addUnit = (unit: string, count: number) => {
      if (count) durationSlots.push(t(`time.${unit}`, { count }));
    };
    addUnit("year", duration.years());
    addUnit("month", duration.months());
    addUnit("day", duration.days());
    if (durationSlots.length === 0) {
      addUnit("hour", duration.hours());
      addUnit("minute", duration.minutes());
    }
    dateInfo.time = durationSlots.length
      ? durationSlots.join(t("time.separator"))
      : t("time.lessThanMinute");
  }
  return dateInfo;
};

// The API returns UTC timestamps, sometimes without an explicit timezone.
export const parseLastOnline = (lastOnline?: string | null): number | null => {
  if (!lastOnline) return null;
  const timestamp = Date.parse(
    /(?:Z|[+-]\d{2}:?\d{2})$/i.test(lastOnline) ? lastOnline : `${lastOnline}Z`
  );
  return Number.isFinite(timestamp) ? Math.floor(timestamp / 1000) : null;
};

export const relativeOnlineDate = (
  lastOnline: string | null | undefined,
  t: TFunction = translate,
  now: number = Date.now()
): string => {
  const timestamp = parseLastOnline(lastOnline);
  if (timestamp === null) return t("onlineStatus.neverConnected");
  if (now / 1000 - timestamp <= 60) return t("onlineStatus.online");
  return t("onlineStatus.ago", { time: relativeExpiryDate(timestamp, t, now).time });
};
