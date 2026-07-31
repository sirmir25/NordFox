// ============================================================
// RerFire user.js – Security & Privacy Hardening
// Based on arkenfox/user.js (github.com/arkenfox/user.js)
// Target: Firefox ESR 128 / LibreWolf 128
// ============================================================
// Overrides in this file survive browser updates.
// Place in: <profile>/user.js
// Every pref here is verified to exist in the ESR 128 source
// (StaticPrefList.yaml / all.js / firefox.js or read at runtime).
// ============================================================

// ── STARTUP ─────────────────────────────────────────────────
// NordFox retro start page is installed by install.sh into
// <profile>/chrome/homepage.html. The placeholder below is substituted
// at install time with the real file:// URL.
user_pref("browser.startup.page", 1);                       // show homepage on start
user_pref("browser.startup.homepage", "__NORDFOX_HOMEPAGE_URL__");
user_pref("browser.startup.homepage_override.mstone", "ignore"); // no "what's new" page after updates

// New tab: enabled and pointed at the NordFox retro homepage too,
// so Cmd+T behaves the same as opening the home page. The standard
// Firefox new-tab tiles are off (sponsored stuff disabled below).
user_pref("browser.newtabpage.enabled", true);
// PRELOAD the next new tab in the background so Cmd+T appears
// instantly with no white flash. The autoconfig override points
// the preloaded tab at the retro homepage.
user_pref("browser.newtab.preload", true);
// Default document background — match the NordFox homepage body
// (#ECEFF4, Nord "snow storm"), not the inner card (#FAF7EE). This
// is the colour the user actually sees while the page paints, so
// matching it eliminates the visible flash.
user_pref("browser.display.background_color", "#ECEFF4");
user_pref("browser.display.foreground_color", "#2E3440");

// ── ANTI-FLICKER / NO-ANIMATION CHROME ─────────────────────
// ui.prefersReducedMotion=1 is the modern switch that kills every
// chrome animation (tab open/close, fullscreen, toolbar transitions).
// The old per-animation prefs (browser.tabs.animate,
// toolkit.cosmeticAnimations.enabled, …) were removed from Firefox
// years before ESR 128 and are gone from this file.
user_pref("ui.prefersReducedMotion", 1);                    // global "reduce motion"
// Fullscreen: no fade transition, no "press Esc to exit" hint.
// Format is "<fade-in ms> <fade-out ms>".
user_pref("full-screen-api.transition-duration.enter", "0 0");
user_pref("full-screen-api.transition-duration.leave", "0 0");
user_pref("full-screen-api.warning.timeout", 0);
// Don't shrink tabs when the bar is full — keeps the +/X positions stable.
user_pref("browser.tabs.tabClipWidth", 0);
user_pref("browser.tabs.tabMinWidth", 100);
// CRITICAL: take the tab strip OUT of the macOS title bar. With
// tabs-in-titlebar on, every change to the tab strip (opening a
// tab, hovering, fadein) can shift the title-bar layout, which
// physically moves the native macOS traffic-light buttons.
// With this off, the traffic lights live in their own immovable
// system title bar above the tab strip.
user_pref("browser.tabs.inTitlebar", 0);
user_pref("browser.tabs.drawInTitlebar", false);
// (browser.uidensity is set in the UI section below.)
user_pref("browser.newtabpage.activity-stream.showSponsored", false);
user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);
user_pref("browser.newtabpage.activity-stream.feeds.section.topstories", false);
user_pref("browser.newtabpage.activity-stream.feeds.topsites", false);
user_pref("browser.newtabpage.activity-stream.feeds.section.highlights", false);
user_pref("browser.newtabpage.activity-stream.section.highlights.includePocket", false);
user_pref("browser.newtabpage.activity-stream.showWeather", false);
user_pref("browser.newtabpage.activity-stream.feeds.weatherfeed", false);

// ── GEOLOCATION ─────────────────────────────────────────────
user_pref("geo.enabled", false);
user_pref("geo.provider.use_corelocation", false);          // macOS Core Location
user_pref("geo.provider.network.url", "");

// ── LANGUAGE / LOCALE FINGERPRINTING ────────────────────────
// (locale spoofing itself is handled by resistFingerprinting)
user_pref("intl.accept_languages", "en-US, en");

// ── TELEMETRY ───────────────────────────────────────────────
user_pref("toolkit.telemetry.unified", false);
user_pref("toolkit.telemetry.enabled", false);
user_pref("toolkit.telemetry.server", "data:,");
user_pref("toolkit.telemetry.server_owner", "");
user_pref("toolkit.telemetry.archive.enabled", false);
user_pref("toolkit.telemetry.newProfilePing.enabled", false);
user_pref("toolkit.telemetry.shutdownPingSender.enabled", false);
user_pref("toolkit.telemetry.updatePing.enabled", false);
user_pref("toolkit.telemetry.bhrPing.enabled", false);
user_pref("toolkit.telemetry.firstShutdownPing.enabled", false);
user_pref("toolkit.telemetry.cachedClientID", "");
user_pref("toolkit.telemetry.previousBuildID", "");
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("toolkit.coverage.opt-out", true);                // hidden
user_pref("toolkit.coverage.endpoint.base", "");
user_pref("browser.newtabpage.activity-stream.feeds.telemetry", false);
user_pref("browser.newtabpage.activity-stream.telemetry", false);
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("datareporting.policy.firstRunURL", "");
// PPA "privacy-preserving" ad attribution shipped in ESR 128. The FPP
// override above excludes it from fingerprinting protection
// (-PrivateAttributionAPI), so it must be switched off here explicitly.
user_pref("dom.private-attribution.submission.enabled", false);
// CFR: "recommended extension/feature" doorhangers driven by the remote
// messaging system (ASRouter).
user_pref("browser.newtabpage.activity-stream.asrouter.userprefs.cfr.addons", false);
user_pref("browser.newtabpage.activity-stream.asrouter.userprefs.cfr.features", false);

// ── CRASH REPORTER ──────────────────────────────────────────
user_pref("breakpad.reportURL", "");
user_pref("browser.tabs.crashReporting.sendReport", false);
user_pref("browser.crashReports.unsubmittedCheck.enabled", false);
user_pref("browser.crashReports.unsubmittedCheck.autoSubmit2", false);

// ── NORMANDY / SHIELD STUDIES ────────────────────────────────
user_pref("app.normandy.enabled", false);
user_pref("app.normandy.api_url", "");
user_pref("app.shield.optoutstudies.enabled", false);

// ── CAPTIVE PORTAL ──────────────────────────────────────────
user_pref("captivedetect.canonicalURL", "");
user_pref("network.captive-portal-service.enabled", false);
user_pref("network.connectivity-service.enabled", false);

// ── SAFE BROWSING (local checks only, no remote lookups) ─────
user_pref("browser.safebrowsing.malware.enabled", true);    // keep local
user_pref("browser.safebrowsing.phishing.enabled", true);   // keep local
user_pref("browser.safebrowsing.downloads.enabled", false);
user_pref("browser.safebrowsing.downloads.remote.enabled", false);
user_pref("browser.safebrowsing.downloads.remote.url", "");
user_pref("browser.safebrowsing.downloads.remote.block_potentially_unwanted", false);
user_pref("browser.safebrowsing.downloads.remote.block_uncommon", false);
user_pref("browser.safebrowsing.allowOverride", false);

// ── NETWORK ─────────────────────────────────────────────────
user_pref("network.prefetch-next", false);                  // no link prefetch
user_pref("network.dns.disablePrefetch", true);
user_pref("network.dns.disablePrefetchFromHTTPS", true);
user_pref("network.predictor.enabled", false);
user_pref("network.predictor.enable-prefetch", false);
user_pref("network.http.speculative-parallel-limit", 0);
// speculative-parallel-limit=0 caps the sockets, but these two stop the
// attempts entirely: typing in the urlbar / hovering a bookmark otherwise
// opens TCP connections to sites you never actually visit.
user_pref("browser.urlbar.speculativeConnect.enabled", false);
user_pref("browser.places.speculativeConnect.enabled", false);
user_pref("browser.send_pings", false);
// Cross-origin subresources must not pop HTTP-auth dialogs (phishing
// vector); top-level and same-origin auth still work. 1 = same-origin only.
user_pref("network.auth.subresource-http-auth-allow", 1);
// Referer: send full referer same-origin, origin-only cross-origin.
// (sendRefererHeader=1 was removed here — it also suppressed the
// referer on direct navigations and broke logins/checkouts.)
user_pref("network.http.referer.spoofSource", false);
user_pref("network.http.referer.XOriginPolicy", 2);        // strict-origin
user_pref("network.http.referer.XOriginTrimmingPolicy", 2);// origin only

// ── DNS-OVER-HTTPS + ECH ─────────────────────────────────────
// mode 3 = TRR only, NO fallback to system DNS. mode 2 silently
// leaked queries to the system resolver whenever Quad9 hiccuped.
// If Quad9 is down, DNS stops working — switch network.trr.uri or
// temporarily set mode back to 2 in about:config.
user_pref("network.trr.mode", 3);
user_pref("network.trr.uri", "https://dns.quad9.net/dns-query");
user_pref("network.trr.bootstrapAddress", "9.9.9.9");
// Encrypted Client Hello — hide the SNI hostname from the wire.
// Only effective with DoH enabled (it is, above).
user_pref("network.dns.echconfig.enabled", true);
user_pref("network.dns.http3_echconfig.enabled", true);

// ── HTTPS ────────────────────────────────────────────────────
user_pref("dom.security.https_only_mode", true);
user_pref("dom.security.https_only_mode_send_http_background_request", false);
// Block passive mixed content too (images/media loaded over HTTP on an
// HTTPS page). Breakage is ~nil with HTTPS-Only mode already on.
user_pref("security.mixed_content.block_display_content", true);

// ── WEBRTC ──────────────────────────────────────────────────
user_pref("media.peerconnection.enabled", false);           // disable WebRTC
user_pref("media.peerconnection.ice.default_address_only", true);
user_pref("media.peerconnection.ice.no_host", true);
user_pref("media.peerconnection.ice.proxy_only_if_behind_proxy", true);

// ── COOKIES & STORAGE ────────────────────────────────────────
user_pref("network.cookie.cookieBehavior", 5);             // reject cross-site
user_pref("browser.contentblocking.category", "strict");
user_pref("privacy.partition.network_state.ocsp_cache", true);
user_pref("network.cookie.thirdparty.sessionOnly", true);
user_pref("network.cookie.thirdparty.nonsecureSessionOnly", true);

// ── TRACKING PROTECTION ─────────────────────────────────────
user_pref("privacy.trackingprotection.enabled", true);
// Global Privacy Control replaces the deprecated DNT header —
// DNT only added fingerprint entropy and no site honored it.
user_pref("privacy.globalprivacycontrol.enabled", true);

// ── FINGERPRINTING PROTECTION ────────────────────────────────
user_pref("privacy.resistFingerprinting", true);
user_pref("privacy.resistFingerprinting.block_mozAddonManager", true);
user_pref("privacy.fingerprintingProtection", true);
user_pref("privacy.fingerprintingProtection.overrides", "+AllTargets,-PrivateAttributionAPI");

// Canvas fingerprint
user_pref("privacy.resistFingerprinting.randomDataOnCanvasExtract", true);

// Screen/window size spoofing
user_pref("privacy.window.maxInnerWidth", 1600);
user_pref("privacy.window.maxInnerHeight", 900);
// Letterboxing: pad the viewport to a stepped, standardized size so the
// real content dimensions never leak. Without this, the maxInner* spoof
// above is incomplete under resistFingerprinting — JS can still read the
// true inner size. Margins are drawn in the default document background
// (#ECEFF4) set in the STARTUP section, so the padding is unobtrusive.
user_pref("privacy.resistFingerprinting.letterboxing", true);
// Block scripts from moving/resizing the chrome window — another vector
// for re-deriving the real screen geometry that RFP tries to hide.
user_pref("dom.disable_window_move_resize", true);

// ── TIMING PRECISION (defeat timing attacks) ─────────────────
user_pref("javascript.options.shared_memory", false);      // SharedArrayBuffer
user_pref("privacy.reduceTimerPrecision", true);
user_pref("privacy.resistFingerprinting.reduceTimerPrecision.microseconds", 1000);

// ── WEBGL ────────────────────────────────────────────────────
user_pref("webgl.disabled", true);
user_pref("webgl.enable-webgl2", false);
// WebGPU: off by default in ESR 128 (nightly-only), but pin it — it is a
// large GPU attack/fingerprint surface and default flips ride in silently.
user_pref("dom.webgpu.enabled", false);

// ── MEDIA / DRM / AUTOPLAY ───────────────────────────────────
user_pref("media.eme.enabled", false);                     // no DRM
user_pref("media.gmp-widevinecdm.enabled", false);
user_pref("media.autoplay.default", 5);                    // block audio+video autoplay

// ── WORKERS & SERVICE WORKERS ────────────────────────────────
user_pref("dom.serviceWorkers.enabled", false);

// ── NOTIFICATIONS ────────────────────────────────────────────
user_pref("dom.webnotifications.enabled", false);
user_pref("dom.push.enabled", false);
user_pref("dom.push.connection.enabled", false);
user_pref("dom.push.serverURL", "");

// ── MISCELLANEOUS DOM ────────────────────────────────────────
user_pref("dom.battery.enabled", false);
user_pref("dom.gamepad.enabled", false);
user_pref("dom.vr.enabled", false);
user_pref("dom.event.clipboardevents.enabled", false);     // no clipboard snooping
user_pref("dom.allow_scripts_to_close_windows", false);
user_pref("dom.disable_beforeunload", true);
user_pref("dom.disable_open_during_load", true);
user_pref("beacon.enabled", false);                        // no sendBeacon analytics
user_pref("dom.webmidi.enabled", false);                   // no MIDI device enumeration

// ── SENSORS / MOTION ─────────────────────────────────────────
user_pref("device.sensors.ambientLight.enabled", false);
user_pref("device.sensors.enabled", false);
user_pref("device.sensors.motion.enabled", false);
user_pref("device.sensors.orientation.enabled", false);
user_pref("device.sensors.proximity.enabled", false);

// ── POCKET / SPONSORED ──────────────────────────────────────
user_pref("extensions.pocket.enabled", false);
user_pref("extensions.pocket.api", "");
user_pref("extensions.pocket.site", "");
user_pref("extensions.pocket.oAuthConsumerKey", "");
user_pref("browser.topsites.useRemoteSetting", false);

// ── SEARCH / URL BAR ─────────────────────────────────────────
// Don't stream keystrokes to the search engine as you type,
// and kill Firefox Suggest / trending noise.
user_pref("browser.search.suggest.enabled", false);
user_pref("browser.urlbar.suggest.searches", false);
user_pref("browser.urlbar.suggest.quicksuggest.nonsponsored", false);
user_pref("browser.urlbar.suggest.quicksuggest.sponsored", false);
user_pref("browser.urlbar.trending.featureGate", false);
// Show punycode for IDN domains — defeats homoglyph phishing
// (аpple.com with a Cyrillic "а" renders as xn--pple-43d.com).
user_pref("network.IDN_show_punycode", true);

// ── HISTORY & SESSION ────────────────────────────────────────
user_pref("places.history.enabled", true);                 // keep local history
user_pref("browser.formfill.enable", false);               // no form history
user_pref("browser.sessionstore.max_tabs_undo", 10);
user_pref("browser.sessionstore.privacy_level", 2);        // never store extra session data
user_pref("signon.rememberSignons", false);                // no password saving
user_pref("signon.autofillForms", false);

// ── CERTIFICATES / OCSP / CRLITE ─────────────────────────────
user_pref("security.OCSP.require", true);
user_pref("security.OCSP.enabled", 1);
user_pref("security.cert_pinning.enforcement_level", 2);   // strict
// CRLite: local revocation checks via downloaded filters —
// faster and more private than OCSP, covers OCSP blind spots.
// mode 2 = enforce CRLite results.
user_pref("security.remote_settings.crlite_filters.enabled", true);
user_pref("security.pki.crlite_mode", 2);

// ── TLS / SSL ────────────────────────────────────────────────
user_pref("security.tls.version.min", 3);                  // TLS 1.2 minimum
user_pref("security.tls.version.max", 4);                  // TLS 1.3 max
user_pref("security.ssl.require_safe_negotiation", true);
user_pref("security.ssl.treat_unsafe_negotiation_as_broken", true);
user_pref("security.tls.enable_0rtt_data", false);        // disable 0-RTT (replay attacks)

// ── ATTACK SURFACE ───────────────────────────────────────────
// PDF.js: no JavaScript inside PDFs (interactive forms still render).
user_pref("pdfjs.enableScripting", false);
// Accessibility engine: classic process-injection surface on macOS;
// disable unless a screen reader is actually needed.
user_pref("accessibility.force_disabled", 1);
// asm.js fast path: historic exploit vector; wasm and the normal JIT
// stay enabled, so web breakage is near zero.
user_pref("javascript.options.asmjs", false);
// SVG glyphs inside OpenType fonts (arkenfox 2620) — obscure rendering
// path; only exotic color fonts regress.
user_pref("gfx.font_rendering.opentype_svg.enabled", false);
// UITour lets mozilla.org pages drive the browser chrome remotely.
user_pref("browser.uitour.enabled", false);
user_pref("browser.uitour.url", "");

// ── EXTENSIONS / RECOMMENDATIONS ─────────────────────────────
user_pref("extensions.getAddons.showPane", false);         // no AMO "Recommended" pane
user_pref("extensions.htmlaboutaddons.recommendations.enabled", false);
user_pref("browser.discovery.enabled", false);             // no personalized extension recs
user_pref("extensions.screenshots.disabled", true);        // built-in Screenshots off

// ── CONTAINERS ───────────────────────────────────────────────
// Multi-account containers: isolate cookies per container tab.
user_pref("privacy.userContext.enabled", true);
user_pref("privacy.userContext.ui.enabled", true);

// ── UI / CLASSIC LOOK HELPERS ────────────────────────────────
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true); // enable userChrome.css
user_pref("browser.compactmode.show", true);
user_pref("browser.uidensity", 1);                        // compact
user_pref("browser.toolbars.bookmarks.visibility", "always");
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.pagethumbnails.capturing_disabled", true); // no page screenshots on disk
