(() => {
  const measurementId = document.currentScript?.dataset.measurementId;
  const { protocol, hostname } = window.location;
  const local = hostname === 'localhost' || hostname.endsWith('.localhost')
    || /^127\./.test(hostname) || hostname === '[::1]' || hostname === '::1';
  if (!/^G-[A-Z0-9]+$/.test(measurementId || '') || local
      || !['https:', 'http:'].includes(protocol) || window.gtag) return;

  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { window.dataLayer.push(arguments); };
  window.gtag('js', new Date());
  // The config command sends the initial page_view. Do not send it again.
  window.gtag('config', measurementId, {
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
  });
  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
  document.head.append(script);
})();
