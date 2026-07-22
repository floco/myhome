// packages/editor/src/main.ts
import "./lib/ingressFetchShim";
import "./lib/theme.css";
import { initTheme } from "./lib/theme";
import { register, init, waitLocale } from "svelte-i18n";
import { getStoredLocale } from "./lib/locale";
import { mount } from "svelte";
import App from "./App.svelte";

initTheme();

register("en", () => import("./lib/locales/en.json"));
register("fr", () => import("./lib/locales/fr.json"));
await init({ fallbackLocale: "en", initialLocale: getStoredLocale() });
await waitLocale();

const target = document.getElementById("app");
if (!target) throw new Error("Missing #app element");

const app = mount(App, { target });

export default app;
