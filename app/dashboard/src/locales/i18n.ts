import { joinPaths } from "@remix-run/router";

import fa from "date-fns/locale/fa-IR";
import ru from "date-fns/locale/ru";
import zh from "date-fns/locale/zh-CN";
import dayjs from "dayjs";
import "dayjs/locale/fa";
import "dayjs/locale/ru";
import "dayjs/locale/zh-cn";
import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import HttpApi from "i18next-http-backend";
import { registerLocale } from "react-datepicker";
import { initReactI18next } from "react-i18next";

declare module "i18next" {
    interface CustomTypeOptions {
        returnNull: false;
    }
}

const updateDateLocale = (lng: string) => {
    const language = lng.toLowerCase().split("-")[0];
    dayjs.locale(language === "zh" ? "zh-cn" : language);
    document.documentElement.lang = lng;
};

i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .use(HttpApi)
    .init(
        {
            debug: import.meta.env.NODE_ENV === "development",
            returnNull: false,
            fallbackLng: "en",
            interpolation: {
                escapeValue: false,
            },
            react: {
                useSuspense: false,
            },
            load: "languageOnly",
            detection: {
                caches: ["localStorage", "sessionStorage", "cookie"],
            },
            backend: {
                loadPath: joinPaths([
                    import.meta.env.BASE_URL,
                    `statics/locales/{{lng}}.json`,
                ]),
            },
        },
        function (err, t) {
            updateDateLocale(i18n.resolvedLanguage || i18n.language || "en");
        }
    );

i18n.on("languageChanged", (lng) => {
    updateDateLocale(lng);
});

// DataPicker
registerLocale("zh-cn", zh);
registerLocale("zh", zh);
registerLocale("ru", ru);
registerLocale("fa", fa);

export default i18n;
