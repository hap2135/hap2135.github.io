// Renders the project grid and tag filters from data/projects.json.
// `base` lets pages in subfolders resolve paths ("" at the root, "../" one level down).

const base = document.body.dataset.base || "";

export async function loadProjects() {
  const res = await fetch(`${base}data/projects.json`);
  if (!res.ok) throw new Error(`Could not load projects.json (${res.status})`);
  return (await res.json()).projects;
}

// Titles, captions and hints are set in caps, which would turn "mA" into "MA",
// "µA" into "ΜA" and "GHz" into "GHZ". Wrapping the unit after a number lets
// the CSS leave its case alone. Longer units first, so "dBm" isn't caught as
// "dB" with an "m" left over.
export const unitSpans = text =>
  text.replace(/(\d\s*)(µA|mAh|mA|mW|dBm|dB|GHz|MHz)(?![A-Za-z])/g, '$1<span class="unit">$2</span>');

function card(p) {
  const a = document.createElement("a");
  a.className = "card";
  a.href = `${base}projects/${p.slug}.html`;
  a.dataset.tags = (p.tags || []).join("|");
  a.innerHTML = `
    <div class="card-media">
      <img src="${base}${p.hero}" alt="" loading="lazy"
           onerror="this.style.visibility='hidden'">
    </div>
    <div class="card-body">
      <h3>${unitSpans(p.title)}</h3>
      <p>${p.summary}</p>
      ${(p.tags || []).length ? `<div class="tags">${p.tags.map(t => `<span class="tag">${t}</span>`).join("")}</div>` : ""}
    </div>`;
  return a;
}

function renderFilters(projects, grid, host) {
  const found = [...new Set(projects.flatMap(p => p.tags || []))];
  host.hidden = found.length === 0;
  if (host.hidden) return;
  const tags = ["All", ...found];
  host.innerHTML = "";
  for (const tag of tags) {
    const b = document.createElement("button");
    b.className = "chip";
    b.type = "button";
    b.textContent = tag;
    b.setAttribute("aria-pressed", String(tag === "All"));
    b.addEventListener("click", () => {
      host.querySelectorAll(".chip").forEach(c => c.setAttribute("aria-pressed", "false"));
      b.setAttribute("aria-pressed", "true");
      for (const c of grid.children) {
        const match = tag === "All" || c.dataset.tags.split("|").includes(tag);
        c.hidden = !match;
      }
    });
    host.append(b);
  }
}

export async function renderGrid(gridSelector, filterSelector) {
  const grid = document.querySelector(gridSelector);
  const filters = document.querySelector(filterSelector);
  try {
    const projects = await loadProjects();
    grid.append(...projects.map(card));
    if (filters) renderFilters(projects, grid, filters);
  } catch (err) {
    grid.innerHTML = `<p class="muted">${err.message}</p>`;
  }
}
