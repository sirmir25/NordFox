/**
 * NordFox new-tab page logic.
 *
 * Compiled with `npx -y typescript tsc` via `theme/build.sh`.
 * Output is loaded by `newtab.html` as a sibling `newtab.js`.
 *
 * Deliberately lighter than homepage.ts — this page opens on every
 * Cmd+T. Nothing here touches the network; it is served from file://
 * (or from the .app Resources dir via autoconfig).
 *
 * Persistence caveat: with `privacy.file_unique_origin` (default since
 * FF 68) file:// documents get an opaque origin and localStorage may
 * THROW. Every storage access goes through safeStorage below, and the
 * page is fully functional on the static defaults when storage is
 * unavailable — edits just don't survive the tab.
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

interface DialLink {
  readonly title: string;
  readonly url: string;
}

const DEFAULT_DIALS: readonly DialLink[] = [
  { title: "Wikipedia",        url: "https://en.wikipedia.org/" },
  { title: "Hacker News",      url: "https://news.ycombinator.com/" },
  { title: "Lobsters",         url: "https://lobste.rs/" },
  { title: "Internet Archive", url: "https://archive.org/" },
  { title: "LibreWolf",        url: "https://librewolf.net/" },
  { title: "Nord theme",       url: "https://www.nordtheme.com/" },
  { title: "Downloads",        url: "about:downloads" },
  { title: "Add-ons",          url: "about:addons" },
];

const DIALS_KEY = "nordfox.newtab.dials";
const DIAL_COUNT = 8;

/**
 * Dial URLs are user-supplied (via prompt) and then written into an <a href>
 * on every page load, so anything stored once keeps running. Restrict them to
 * schemes that merely navigate — `javascript:` and `data:` would execute in
 * the context of this page instead.
 */
const ALLOWED_SCHEMES: readonly string[] = ["http:", "https:", "file:", "about:"];

const MONTH_NAMES: readonly string[] = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// ── storage ─────────────────────────────────────────────────

/** In-memory fallback used when localStorage is unavailable. */
let memoryStore: string | null = null;

function storageGet(): string | null {
  try {
    return window.localStorage.getItem(DIALS_KEY);
  } catch {
    return memoryStore;
  }
}

function storageSet(value: string): boolean {
  try {
    window.localStorage.setItem(DIALS_KEY, value);
    return true;
  } catch {
    memoryStore = value;
    return false;
  }
}

function loadDials(): DialLink[] {
  const raw = storageGet();
  if (raw !== null) {
    try {
      const parsed: unknown = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length === DIAL_COUNT) {
        const dials: DialLink[] = [];
        for (const item of parsed) {
          if (
            typeof item === "object" && item !== null &&
            typeof (item as DialLink).title === "string" &&
            typeof (item as DialLink).url === "string" &&
            isSafeUrl((item as DialLink).url)
          ) {
            dials.push({ title: (item as DialLink).title, url: (item as DialLink).url });
          }
        }
        if (dials.length === DIAL_COUNT) {
          return dials;
        }
      }
    } catch {
      // corrupt JSON — fall through to defaults
    }
  }
  return DEFAULT_DIALS.slice();
}

// ── helpers ─────────────────────────────────────────────────

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

function isSafeUrl(url: string): boolean {
  try {
    return ALLOWED_SCHEMES.indexOf(new URL(url).protocol) !== -1;
  } catch {
    return false;
  }
}

function hostOf(url: string): string {
  try {
    const u = new URL(url);
    return u.protocol === "about:" ? url : u.host;
  } catch {
    return "";
  }
}

// ── clock / date ────────────────────────────────────────────

function startClock(): void {
  const tick = (): void => {
    const d = new Date();
    setText("clock", `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`);
  };
  tick();
  window.setInterval(tick, 1000);
}

function showDate(): void {
  const today = new Date();
  setText("today", `${MONTH_NAMES[today.getMonth()]} ${today.getDate()}, ${today.getFullYear()}`);
}

// ── search ──────────────────────────────────────────────────

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

// ── quick dials ─────────────────────────────────────────────

let dials: DialLink[] = [];
let editing = false;

function renderDials(): void {
  for (let i = 0; i < DIAL_COUNT; i++) {
    const cell = $(`dial-${i}`);
    if (cell === null) continue;
    const dial = dials[i];
    if (dial === undefined) continue;
    cell.innerHTML = "";
    const a = document.createElement("a");
    a.href = dial.url;
    a.textContent = dial.title;
    const host = document.createElement("span");
    host.className = "host";
    host.textContent = hostOf(dial.url);
    a.appendChild(host);
    const index = i;
    a.addEventListener("click", (ev: MouseEvent): void => {
      if (editing) {
        ev.preventDefault();
        editDial(index);
      }
    });
    cell.appendChild(a);
  }
}

function editDial(index: number): void {
  const current = dials[index];
  if (current === undefined) return;
  const title = window.prompt("Dial title:", current.title);
  if (title === null || title.trim() === "") return;
  const url = window.prompt("Dial URL:", current.url);
  if (url === null || url.trim() === "") return;
  if (!isSafeUrl(url.trim())) {
    setText("status", "Rejected: dial URLs must be http, https, file, or about.");
    return;
  }
  dials[index] = { title: title.trim(), url: url.trim() };
  const persisted = storageSet(JSON.stringify(dials));
  renderDials();
  setText("status", persisted
    ? "Dial saved."
    : "Dial changed (storage unavailable on file:// — resets next tab).");
}

function wireEditToggle(): void {
  const toggle = $("edit-toggle");
  if (toggle === null) return;
  toggle.addEventListener("click", (ev: MouseEvent): void => {
    ev.preventDefault();
    editing = !editing;
    document.body.classList.toggle("editing", editing);
    toggle.textContent = editing ? "done editing" : "edit dials";
    setText("status", editing ? "Click a dial to edit it." : "Done.");
  });
}

// ── main ────────────────────────────────────────────────────

function main(): void {
  dials = loadDials();
  renderDials();
  populateEngineDropdown();
  wireSearch();
  wireEditToggle();
  startClock();
  showDate();
}

// Script is loaded at end-of-body; DOMContentLoaded may already be done.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", main, { once: true });
} else {
  main();
}

// Make this file a module so its top-level names don't collide with the
// other pages during compilation. The emitted `export {}` is stripped by
// theme/build.sh — the shipped JS is a classic <script>.
export {};
