/**
 * sakima.co — consent-gated analytics + advertising tags.
 *
 * Mirrors lkup.info (src/lib/tags.ts + src/lib/consent.ts) but self-contained,
 * because this is a static site with no build step and no auth. Keep in sync.
 *
 *  - Tags are INJECTED, never hardcoded. Privacy Part B1 promises EEA/UK/CH
 *    visitors that no analytics/ads tag LOADS. Consent-mode-denied Google tags
 *    still send cookieless pings, so the gate must precede injection.
 *  - No auth here => no self-declared residency, so we fall back to browser
 *    timezone. Deliberately conservative: a European tz gets reduced treatment.
 *  - GPC honored as a standing opt-out, no banner. Prompting around a legal
 *    opt-out signal is itself the violation.
 *  - Accept and decline are ONE click each. Asymmetric flows are void under
 *    CCPA regs (11 CCR 7004) and banned in CO/CT.
 */
(function () {
  'use strict';

  var GTM_ID = 'GTM-NMC3WFQW';
  var GA4_ID = 'G-0RLRSJJ1LW';
  var GA4_ROLLUP_ID = 'G-Z5C47SKHDD';
  var META_PIXEL_ID = '1053752143713760';
  var KEY = 'lkup.consent.v1';

  var EUROPE_TZ = /^(Europe\/|Atlantic\/(Canary|Madeira|Azores|Faroe|Reykjavik))/;

  function looksEuropean() {
    try { return EUROPE_TZ.test(Intl.DateTimeFormat().resolvedOptions().timeZone || ''); }
    catch (e) { return false; }
  }
  function gpcOn() { return navigator.globalPrivacyControl === true; }

  function readConsent() {
    if (gpcOn()) return { analytics: false, advertising: false, decided: true, source: 'gpc' };
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return { analytics: true, advertising: true, decided: false, source: 'default' };
      var p = JSON.parse(raw);
      return { analytics: p.analytics !== false, advertising: p.advertising !== false,
               decided: !!p.decidedAt, source: p.source || 'default' };
    } catch (e) { return { analytics: true, advertising: true, decided: false, source: 'default' }; }
  }

  function writeConsent(analytics, advertising, source) {
    try {
      localStorage.setItem(KEY, JSON.stringify({ necessary: true, analytics: analytics,
        advertising: advertising, decidedAt: new Date().toISOString(), source: source }));
    } catch (e) { /* storage blocked */ }
    applyConsent(analytics, advertising, source);
  }

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }

  function applyConsent(analytics, advertising, source) {
    gtag('consent', 'update', {
      analytics_storage: analytics ? 'granted' : 'denied',
      ad_storage: advertising ? 'granted' : 'denied',
      ad_user_data: advertising ? 'granted' : 'denied',
      ad_personalization: advertising ? 'granted' : 'denied',
      personalization_storage: advertising ? 'granted' : 'denied',
      functionality_storage: 'granted', security_storage: 'granted'
    });
    window.dataLayer.push({ event: 'lkup_consent_update', consent_analytics: analytics,
      consent_advertising: advertising, consent_source: source });
    if (typeof window.fbq === 'function') window.fbq('consent', advertising ? 'grant' : 'revoke');
  }

  var loaded = false;
  function loadTags() {
    if (loaded) return;
    if (looksEuropean()) return;
    loaded = true;

    gtag('consent', 'default', {
      ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied',
      analytics_storage: 'denied', personalization_storage: 'denied',
      functionality_storage: 'granted', security_storage: 'granted', wait_for_update: 500
    });

    window.dataLayer.push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
    var gtm = document.createElement('script');
    gtm.async = true; gtm.src = 'https://www.googletagmanager.com/gtm.js?id=' + GTM_ID;
    document.head.appendChild(gtm);

    var ga = document.createElement('script');
    ga.async = true; ga.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA4_ID;
    document.head.appendChild(ga);
    gtag('js', new Date());
    gtag('config', GA4_ID);
    gtag('config', GA4_ROLLUP_ID);

    if (!window.fbq) {
      var n = window.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!window._fbq) window._fbq = n;
      n.push = n; n.loaded = true; n.version = '2.0'; n.queue = [];
      var fb = document.createElement('script');
      fb.async = true; fb.src = 'https://connect.facebook.net/en_US/fbevents.js';
      document.head.appendChild(fb);
    }
    window.fbq('consent', 'revoke');
    window.fbq('init', META_PIXEL_ID);
    window.fbq('track', 'PageView');

    var c = readConsent();
    applyConsent(c.analytics, c.advertising, c.source);
  }

  function showBanner() {
    if (document.getElementById('lkup-consent')) return;
    var bar = document.createElement('div');
    bar.id = 'lkup-consent';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Cookie notice');
    bar.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:99999;background:#fff;' +
      'border-top:1px solid #e5e7eb;padding:14px 16px;display:flex;flex-wrap:wrap;gap:10px;' +
      'align-items:center;justify-content:center;font:13px/1.5 system-ui,-apple-system,sans-serif;' +
      'box-shadow:0 -2px 12px rgba(0,0,0,.08)';
    bar.innerHTML = '<span style="flex:1;min-width:260px;max-width:640px;color:#4b5563">' +
      'We use cookies for site function, analytics and advertising, and share some data with ' +
      'partners like Google and Meta. <a href="https://lkup.info/privacy" style="color:#1e3c72;text-decoration:underline">Learn more</a></span>' +
      '<button id="lkup-essential" style="padding:8px 14px;border:1px solid #d1d5db;background:#fff;border-radius:6px;cursor:pointer;font-size:13px">Essential only</button>' +
      '<button id="lkup-accept" style="padding:8px 18px;border:0;background:#1e3c72;color:#fff;border-radius:6px;cursor:pointer;font-weight:600;font-size:13px">Accept all</button>';
    document.body.appendChild(bar);
    document.getElementById('lkup-accept').onclick = function () { writeConsent(true, true, 'accept_all'); bar.remove(); };
    document.getElementById('lkup-essential').onclick = function () { writeConsent(false, false, 'reject_all'); bar.remove(); };
  }

  function init() {
    loadTags();
    var c = readConsent();
    if (!looksEuropean() && !gpcOn() && !c.decided) showBanner();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
