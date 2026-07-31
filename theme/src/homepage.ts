/**
 * NordFox retro start-page logic.
 *
 * Compiled with `npx -y typescript tsc` via `theme/build.sh`.
 * Output is loaded by `homepage.html` as a sibling `homepage.js`.
 *
 * Strict TS — every DOM lookup is null-checked, every dynamic
 * value typed. Nothing here touches the network; this is a fully
 * local file://-served page.
 */

interface SearchEngine {
  readonly id: string;
  readonly name: string;
  readonly url: string;
}

const SEARCH_ENGINES: readonly SearchEngine[] = [
  { id: "ddg",       name: "DuckDuckGo",         url: "https://duckduckgo.com/?q=" },
  { id: "ddg-html",  name: "DuckDuckGo (HTML)",  url: "https://html.duckduckgo.com/html/?q=" },
  { id: "startpage", name: "Startpage",          url: "https://www.startpage.com/sp/search?query=" },
  { id: "brave",     name: "Brave",              url: "https://search.brave.com/search?q=" },
  { id: "google",    name: "Google",             url: "https://www.google.com/search?q=" },
  { id: "bing",      name: "Bing",               url: "https://www.bing.com/search?q=" },
];

const RETRO_TIPS: readonly string[] = [
  'Tabbed browsing: <kbd>&#8984;T</kbd> opens a new tab. Drag tabs to reorder.',
  'Press <kbd>&#8984;L</kbd> to jump to the address bar &mdash; the keyboard is faster than the mouse.',
  '<kbd>about:config</kbd> exposes every preference. <b>Here be dragons.</b>',
  'NordFox forces a 100&micro;s precision floor on <code>performance.now()</code> for all callers.',
  'Pocket, Normandy, and the Mozilla updater have been removed at the source level.',
  'DRM (EME), the crash reporter, and the update service are compiled out &mdash; not merely switched off by a pref.',
  'Try <kbd>&#8984;F</kbd> to find on this page &mdash; it works on the start page too.',
  'Use the Customize menu (toolbar &rarr; right-click) to switch to <i>Compact</i> density for a tighter chrome.',
];

const MONTH_NAMES: readonly string[] = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`;
}

function $(id: string): HTMLElement | null {
  return document.getElementById(id);
}

function setText(id: string, value: string): void {
  const el = $(id);
  if (el !== null) {
    el.textContent = value;
  }
}

function setHTML(id: string, value: string): void {
  const el = $(id);
  if (el !== null) {
    el.innerHTML = value;
  }
}

function startClock(): void {
  const tick = (): void => {
    const d = new Date();
    setText("clock", `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`);
  };
  tick();
  window.setInterval(tick, 1000);
}

function populateSession(): void {
  const today = new Date();
  setText("today", `${MONTH_NAMES[today.getMonth()]} ${today.getDate()}, ${today.getFullYear()}`);
  setText("ua", navigator.userAgent);
  setText("plat", navigator.platform !== "" ? navigator.platform : "(hidden)");
  setText("lang", navigator.language !== "" ? navigator.language : "(hidden)");
  setText("online", navigator.onLine ? "yes" : "no");
  setText("cookies", navigator.cookieEnabled ? "enabled" : "disabled");

  // Different browsers expose Do-Not-Track in different places.
  // The cast keeps TS happy without making the type signature lie.
  type DNTWindow = Window & { doNotTrack?: string };
  type DNTNavigator = Navigator & { doNotTrack?: string };
  const navDnt = (navigator as DNTNavigator).doNotTrack;
  const winDnt = (window as DNTWindow).doNotTrack;
  setText("dnt", navDnt ?? winDnt ?? "unset");
}

function populateEngineDropdown(): void {
  const select = $("engine");
  if (!(select instanceof HTMLSelectElement)) {
    return;
  }
  select.innerHTML = "";
  for (const engine of SEARCH_ENGINES) {
    const option = document.createElement("option");
    option.value = engine.url;
    option.textContent = engine.name;
    if (engine.id === "ddg") {
      option.selected = true;
    }
    select.appendChild(option);
  }
}

function wireSearch(): void {
  const form = $("searchform");
  if (!(form instanceof HTMLFormElement)) {
    return;
  }
  form.addEventListener("submit", (ev: SubmitEvent): void => {
    ev.preventDefault();
    const queryInput = $("q");
    const engineSelect = $("engine");
    if (!(queryInput instanceof HTMLInputElement)) return;
    if (!(engineSelect instanceof HTMLSelectElement)) return;
    const q = queryInput.value.trim();
    if (q === "") return;
    window.location.href = engineSelect.value + encodeURIComponent(q);
  });
}

function pickRandomTip(): void {
  const index = Math.floor(Math.random() * RETRO_TIPS.length);
  const tip = RETRO_TIPS[index] ?? "&mdash;";
  setHTML("tip", tip);
}

function main(): void {
  populateEngineDropdown();
  startClock();
  populateSession();
  wireSearch();
  pickRandomTip();
}

// Run after the DOM is parsed. The script is loaded at end-of-body,
// so DOMContentLoaded has likely already fired — guard either way.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", main, { once: true });
} else {
  main();
}

// Make this file a module so its top-level names don't collide with the
// other pages during compilation. The emitted `export {}` is stripped by
// theme/build.sh — the shipped JS is a classic <script>.
export {};
