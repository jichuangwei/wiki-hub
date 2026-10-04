const filtersRow = document.querySelector('.filters-row');
const siteHeader = document.querySelector('.site-header');
const filterSentinel = document.createElement('div');
filterSentinel.setAttribute('aria-hidden', 'true');
filtersRow.before(filterSentinel);
function updateStickyFilters() {
  const headerHeight = siteHeader.getBoundingClientRect().height;
  document.documentElement.style.setProperty('--site-header-height', `${headerHeight}px`);
  filtersRow.classList.toggle('is-stuck', filterSentinel.getBoundingClientRect().top < headerHeight);
}
let stickyFrame = 0;
window.addEventListener('scroll', () => {
  if (stickyFrame) return;
  stickyFrame = requestAnimationFrame(() => {
    stickyFrame = 0;
    updateStickyFilters();
  });
}, { passive: true });
window.addEventListener('resize', updateStickyFilters);
if ('ResizeObserver' in window) new ResizeObserver(updateStickyFilters).observe(siteHeader);
updateStickyFilters();
function scrollToNewsStart() {
  const content = document.querySelector('.weekly-reports');
  const top = window.scrollY + content.getBoundingClientRect().top
    - siteHeader.getBoundingClientRect().height - filtersRow.getBoundingClientRect().height;
  window.scrollTo({ top: Math.max(0, top), behavior: 'instant' });
}

const weekPicker = document.querySelector(".week-picker");
const weekTrigger = document.querySelector("#week-trigger");
const weekCurrent = document.querySelector("#week-current");
const weekMenu = document.querySelector("#week-menu");
const weekOptions = Array.from(document.querySelectorAll(".week-option"));
const pathWeek = window.location.pathname.match(/\/news\/(\d{4}-week-\d{1,2})\/?$/)?.[1];
const activeOption = weekOptions.find((option) => option.dataset.weekPath === pathWeek) || weekOptions[0];
const activeWeek = activeOption.dataset.week;
const activeWeekLabel = activeOption.querySelector('span').textContent;
weekCurrent.textContent = activeWeekLabel;
weekTrigger.title = activeWeekLabel;
weekOptions.forEach((option) => option.setAttribute("aria-selected", String(option === activeOption)));
const tabs = Array.from(document.querySelectorAll(".category-tab"));
const reports = Array.from(document.querySelectorAll(".weekly-report"));
const emptyState = document.querySelector("#empty-state");

let activeCategory = "all";
const categoryPicker = document.querySelector('.category-picker');
const categoryTrigger = document.querySelector('.category-trigger');
const categoryCurrent = document.querySelector('#category-current');
document.documentElement.classList.add('has-filters');
categoryTrigger.hidden = false;
function setCategoryOpen(open) {
  categoryPicker.classList.toggle('is-open', open);
  categoryTrigger.setAttribute('aria-expanded', String(open));
}
categoryTrigger.addEventListener('click', () => {
  setWeekMenuOpen(false);
  setCategoryOpen(categoryTrigger.getAttribute('aria-expanded') !== 'true');
});
categoryTrigger.addEventListener('keydown', (event) => {
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    setCategoryOpen(true);
    tabs.find(tab => tab.classList.contains('is-active'))?.focus();
  }
});

function updateCategories() {
  const weekCards = Array.from(reports.find((report) => report.dataset.week === activeWeek).querySelectorAll('[data-kind="news"]'));
  for (const tab of tabs) {
    const count = tab.dataset.filter === "all"
      ? weekCards.length
      : weekCards.filter((card) => card.dataset.category === tab.dataset.filter).length;
    tab.hidden = count === 0;
    tab.querySelector("span").textContent = count;
  }
  if (activeCategory !== "all" && !weekCards.some((card) => card.dataset.category === activeCategory)) {
    activeCategory = "all";
  }
  for (const tab of tabs) {
    const selected = tab.dataset.filter === activeCategory;
    tab.classList.toggle("is-active", selected);
    tab.setAttribute("aria-pressed", String(selected));
  }
  const selected = tabs.find(tab => tab.dataset.filter === activeCategory);
  categoryCurrent.textContent = activeCategory === 'all' ? '全部分类' : selected.firstChild.textContent.trim();
  categoryTrigger.title = categoryCurrent.textContent;
}

function filterNews() {
  let visible = 0;
  for (const report of reports) {
    report.hidden = report.dataset.week !== activeWeek;
    for (const row of report.querySelectorAll("[data-category]")) {
      row.hidden = activeCategory !== "all" && row.dataset.category !== activeCategory;
      if (!report.hidden && !row.hidden && row.dataset.kind === "news") visible += 1;
    }
  }
  emptyState.hidden = visible !== 0;
}

function setWeekMenuOpen(open) {
  if (open) setCategoryOpen(false);
  weekMenu.hidden = !open;
  weekTrigger.setAttribute("aria-expanded", String(open));
}

weekTrigger.addEventListener("click", () => setWeekMenuOpen(weekMenu.hidden));
weekTrigger.addEventListener("keydown", (event) => {
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    setWeekMenuOpen(true);
    (event.key === "ArrowDown" ? weekOptions[0] : weekOptions.at(-1)).focus();
  }
});
weekOptions.forEach((option, index) => {
  option.addEventListener('click', (event) => {
    if (option !== activeOption || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    setWeekMenuOpen(false);
    weekTrigger.focus({ preventScroll: true });
    scrollToNewsStart();
  });
  option.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      weekOptions[(index + (event.key === "ArrowDown" ? 1 : -1) + weekOptions.length) % weekOptions.length].focus();
    }
  });
});
document.addEventListener("click", (event) => {
  if (!weekPicker.contains(event.target)) setWeekMenuOpen(false);
  if (!categoryPicker.contains(event.target)) setCategoryOpen(false);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !weekMenu.hidden) {
    setWeekMenuOpen(false);
    weekTrigger.focus();
  }
  if (event.key === 'Escape' && categoryTrigger.getAttribute('aria-expanded') === 'true') {
    setCategoryOpen(false);
    categoryTrigger.focus();
  }
});
for (const tab of tabs) {
  tab.addEventListener('keydown', (event) => {
    if (!window.matchMedia('(max-width: 640px)').matches) return;
    const visibleTabs = tabs.filter(item => !item.hidden);
    const index = visibleTabs.indexOf(tab);
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      visibleTabs[(index + (event.key === 'ArrowDown' ? 1 : -1) + visibleTabs.length) % visibleTabs.length].focus();
    }
  });
  tab.addEventListener("click", () => {
    activeCategory = tab.dataset.filter;
    updateCategories();
    filterNews();
    setCategoryOpen(false);
    scrollToNewsStart();
    if (window.matchMedia('(max-width: 640px)').matches) categoryTrigger.focus({ preventScroll: true });
  });
}
window.matchMedia('(max-width: 640px)').addEventListener('change', () => {
  setCategoryOpen(false);
  setWeekMenuOpen(false);
});
for (const link of document.querySelectorAll(".weekly-report a")) {
  link.target = "_blank";
  link.rel = "noopener noreferrer";
}

updateCategories();
filterNews();
