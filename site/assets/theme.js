(() => {
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  const key = 'wiki-hub-theme';
  let preference;
  try { preference = localStorage.getItem(key); } catch {}
  if (!['light', 'dark'].includes(preference)) preference = null;
  let button;

  function apply(theme) {
    root.dataset.theme = theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = theme === 'dark' ? '#111827' : '#f6f8fc';
    if (button) {
      const label = theme === 'dark' ? '切换浅色模式' : '切换深色模式';
      button.setAttribute('aria-label', label);
      button.title = label;
    }
  }
  const currentSystemTheme = () => system.matches ? 'dark' : 'light';
  apply(preference || currentSystemTheme());
  system.addEventListener('change', () => {
    if (!preference) apply(currentSystemTheme());
  });
  window.addEventListener('storage', (event) => {
    if (event.key !== key && event.key !== null) return;
    preference = ['light', 'dark'].includes(event.newValue) ? event.newValue : null;
    apply(preference || currentSystemTheme());
  });
  document.addEventListener('DOMContentLoaded', () => {
    button = document.querySelector('.theme-toggle');
    if (!button) return;
    apply(root.dataset.theme);
    button.hidden = false;
    button.addEventListener('click', () => {
      preference = root.dataset.theme === 'dark' ? 'light' : 'dark';
      apply(preference);
      try { localStorage.setItem(key, preference); } catch {}
    });
  });
})();
