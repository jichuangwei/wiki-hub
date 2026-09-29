const tabs = Array.from(document.querySelectorAll(".category-tab"));
const cards = Array.from(document.querySelectorAll(".news-card"));
const search = document.querySelector("#news-search");
const emptyState = document.querySelector("#empty-state");

let activeCategory = "all";

function filterNews() {
  const query = search.value.trim().toLocaleLowerCase();
  let visible = 0;

  for (const card of cards) {
    const categoryMatches = activeCategory === "all" || card.dataset.category === activeCategory;
    const textMatches = !query || card.dataset.search.includes(query);
    card.hidden = !(categoryMatches && textMatches);
    if (!card.hidden) visible += 1;
  }

  emptyState.hidden = visible !== 0;
}

for (const tab of tabs) {
  tab.addEventListener("click", () => {
    activeCategory = tab.dataset.filter;
    for (const item of tabs) {
      const selected = item === tab;
      item.classList.toggle("is-active", selected);
      item.setAttribute("aria-pressed", String(selected));
    }
    filterNews();
  });
}

search.addEventListener("input", filterNews);

for (const image of document.querySelectorAll(".card-art img")) {
  image.addEventListener("error", () => {
    image.replaceWith(Object.assign(document.createElement("span"), {
      className: "card-art-mark",
      textContent: "AI / DEV",
    }));
  }, { once: true });
}
