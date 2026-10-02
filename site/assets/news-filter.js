const weekPicker = document.querySelector(".week-picker");
const weekTrigger = document.querySelector("#week-trigger");
const weekCurrent = document.querySelector("#week-current");
const weekMenu = document.querySelector("#week-menu");
const weekOptions = Array.from(document.querySelectorAll(".week-option"));
let activeWeek = weekOptions[0].dataset.week;
const tabs = Array.from(document.querySelectorAll(".category-tab"));
const reports = Array.from(document.querySelectorAll(".weekly-report"));
const emptyState = document.querySelector("#empty-state");

let activeCategory = "all";

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
  option.addEventListener("click", () => {
    activeWeek = option.dataset.week;
    activeCategory = "all";
    weekCurrent.textContent = option.textContent;
    weekOptions.forEach((item) => item.setAttribute("aria-selected", String(item === option)));
    setWeekMenuOpen(false);
    weekTrigger.focus();
    updateCategories();
    filterNews();
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
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !weekMenu.hidden) {
    setWeekMenuOpen(false);
    weekTrigger.focus();
  }
});
for (const tab of tabs) {
  tab.addEventListener("click", () => {
    activeCategory = tab.dataset.filter;
    updateCategories();
    filterNews();
  });
}
for (const link of document.querySelectorAll(".weekly-report a")) {
  link.target = "_blank";
  link.rel = "noopener noreferrer";
}

updateCategories();
filterNews();
