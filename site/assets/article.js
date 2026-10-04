const directory = document.querySelector('.article-toc');
if (directory) {
  const links = Array.from(directory.querySelectorAll('a'));
  const headings = links.map(link => document.getElementById(link.hash.slice(1))).filter(Boolean);
  let queued = false;
  function updateActiveSection() {
    queued = false;
    const offset = document.querySelector('.site-header').getBoundingClientRect().height + 32;
    let active = headings[0];
    for (const heading of headings) {
      if (heading.getBoundingClientRect().top <= offset) active = heading;
      else break;
    }
    for (const link of links) {
      if (link.hash === '#' + active?.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  }
  window.addEventListener('scroll', () => {
    if (!queued) { queued = true; requestAnimationFrame(updateActiveSection); }
  }, { passive: true });
  updateActiveSection();
}
for (const pre of document.querySelectorAll('.note-body pre')) {
  const code = pre.querySelector('code');
  if (!code) continue;
  const tools = document.createElement('div');
  tools.className = 'code-tools';
  const language = document.createElement('span');
  language.textContent = Array.from(code.classList).find(name => name.startsWith('language-'))?.slice(9) || '代码';
  const copy = document.createElement('button');
  copy.type = 'button';
  copy.className = 'code-copy';
  copy.textContent = '复制';
  copy.setAttribute('aria-label', '复制代码');
  const status = document.createElement('span');
  status.setAttribute('role', 'status');
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(code.textContent);
      status.textContent = '已复制';
    } catch {
      status.textContent = '复制失败，请手动选择代码';
    }
  });
  tools.append(language, status, copy);
  pre.prepend(tools);
}
