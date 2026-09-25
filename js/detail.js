// Fills a project detail page from data/projects.json, keyed by <body data-slug>.

import { loadProjects, unitSpans } from "./projects.js";
import { mountViewer } from "./viewer.js";

const base = document.body.dataset.base || "";
const slug = document.body.dataset.slug;

function fill(sel, html) {
  const el = document.querySelector(sel);
  if (el) el.innerHTML = html;
}

const project = (await loadProjects()).find(p => p.slug === slug);

if (!project) {
  fill("#detail", `<p class="muted">No project named "${slug}" in projects.json.</p>`);
} else {
  document.title = `${project.title} — EE Portfolio`;
  fill("#title", unitSpans(project.title));
  fill("#summary", project.summary);

  fill("#meta", [
    ["Role", project.role],
    ["Tools", project.tools.join(", ")],
  ].map(([dt, dd]) => `<div><dt>${dt}</dt><dd>${dd}</dd></div>`).join(""));

  // A simulation-only project has a spec table where a board would have its
  // model. Each section hides when its project has nothing to put in it, so
  // every detail page can carry the same markup.
  const specs = project.specs;
  const specsSection = document.querySelector("#specs")?.closest("section");
  if (specsSection) specsSection.hidden = !specs;
  if (specs) {
    fill("#specs-caption", unitSpans(specs.caption || ""));
    // Headers default to the markup's Parameter / Target / Result; a project
    // can relabel them, e.g. to put its frequency band on the result column.
    if (specs.columns) fill("#specs-head", specs.columns.map(c =>
      `<th scope="col">${unitSpans(c)}</th>`).join(""));
    fill("#specs", specs.rows.map(r =>
      `<tr><th scope="row">${r.label}</th><td>${r.target}</td><td>${r.result}</td></tr>`).join(""));
    fill("#specs-note", specs.note || "");
  }

  fill("#highlights", project.highlights.map(h => `<li>${h}</li>`).join(""));
  // An empty body leaves the list standing on its own, not a stray paragraph.
  fill("#body", project.body ? `<p>${project.body}</p>` : "");

  const gallery = document.querySelector("#gallery");
  const section = gallery.closest("section");
  const shots = project.gallery || [];
  section.hidden = shots.length === 0;
  // A shot marked `wide` in projects.json spans the grid instead of taking a
  // cell — the class is inert on the live site, which has its own gallery.
  gallery.innerHTML = shots.map(g => `
    <figure class="${g.wide ? "wide" : ""}">
      <img src="${base}${g.src}" alt="${g.caption}" loading="lazy"
           onerror="this.closest('figure').hidden = true; hideEmptyGallery()">
      <figcaption>${unitSpans(g.caption)}</figcaption>
    </figure>`).join("");

  // Placeholder projects have no photos yet — drop the heading rather than
  // leaving an empty section behind.
  window.hideEmptyGallery = () => {
    section.hidden = [...gallery.querySelectorAll("figure")].every(f => f.hidden);
  };

  const viewerSection = document.querySelector("#viewer").closest("section");
  viewerSection.hidden = !project.model;
  if (project.model) mountViewer("#viewer", `${base}${project.model}`, { flip: project.modelFlip });
}
