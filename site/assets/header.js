(() => {
  const header = document.querySelector('.site-header');
  const nav = header?.querySelector('.site-nav');
  const drawer = header?.querySelector('.site-drawer');
  const toggle = header?.querySelector('.nav-toggle');
  const backdrop = document.querySelector('.drawer-backdrop');
  if (!nav || !drawer || !toggle || !backdrop) return;
  document.documentElement.classList.add('has-menu');
  toggle.hidden = false;
  backdrop.hidden = true;
  const mobile = window.matchMedia('(max-width: 640px)');
  function setOpen(open) {
    drawer.classList.toggle('is-open', open && mobile.matches);
    backdrop.hidden = !open || !mobile.matches;
    document.body.classList.toggle('menu-open', open && mobile.matches);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', '打开菜单');
  }
  toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
  drawer.addEventListener('click', (event) => {
    const link = event.target.closest('a');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    // Keep the overlay visible during navigation to avoid flashing the old page.
    if (link.href === window.location.href) {
      event.preventDefault();
      closeMenu();
    }
  });
  function closeMenu() {
    setOpen(false);
    toggle.focus();
  }
  backdrop.addEventListener('click', closeMenu);
  drawer.querySelector('.drawer-close').addEventListener('click', closeMenu);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      toggle.focus();
    }
  });
  mobile.addEventListener('change', () => setOpen(false));
  window.addEventListener('pageshow', () => setOpen(false));
  drawer.classList.remove('is-open');
})();
