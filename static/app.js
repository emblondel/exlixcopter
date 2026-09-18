const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanels = document.querySelectorAll(".tab-panel");

function activateTab(tabName) {
  tabButtons.forEach((b) => b.classList.toggle("active", b.dataset.tab === tabName));
  tabPanels.forEach((p) => p.classList.toggle("active", p.id === `tab-${tabName}`));
  if (tabName === "review") showSessionSetup();
  if (tabName === "deck") loadDeck();
}

tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => activateTab(btn.dataset.tab));
});

// ---------- Search & add ----------
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const searchStatus = document.getElementById("search-status");
const suggestionsEl = document.getElementById("suggestions");
const resultsEl = document.getElementById("results");

searchForm.addEventListener("submit", (e) => {
  e.preventDefault();
  runSearch(searchInput.value.trim());
});

async function runSearch(word) {
  if (!word) return;
  searchInput.value = word;
  searchStatus.textContent = "Recherche en cours…";
  searchStatus.classList.remove("error");
  suggestionsEl.innerHTML = "";
  resultsEl.innerHTML = "";

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(word)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erreur de recherche");

    if (data.meanings.length === 0) {
      searchStatus.textContent = `Aucun résultat exact pour « ${word} ». Suggestions :`;
      data.suggestions.forEach((s) => {
        const b = document.createElement("button");
        b.textContent = s;
        b.addEventListener("click", () => runSearch(s));
        suggestionsEl.appendChild(b);
      });
      return;
    }

    searchStatus.textContent = `${data.meanings.length} vidéo(s) trouvée(s) pour « ${data.word} ». Choisissez le bon signe pour chaque sens.`;

    data.meanings.forEach((meaning) => {
      meaning.video_urls.forEach((videoUrl, idx) => {
        resultsEl.appendChild(buildMeaningCard(meaning, videoUrl, idx, data.saved[videoUrl]));
      });
    });
  } catch (err) {
    searchStatus.textContent = err.message;
    searchStatus.classList.add("error");
  }
}

function buildMeaningCard(meaning, videoUrl, idx, savedCardId) {
  const card = document.createElement("div");
  card.className = "meaning-card";
  if (savedCardId) card.classList.add("already-saved");

  const pos = document.createElement("div");
  pos.className = "pos";
  pos.textContent = meaning.part_of_speech || "";
  if (savedCardId) {
    const badge = document.createElement("span");
    badge.className = "saved-badge";
    badge.textContent = "✔ Déjà enregistrée";
    pos.appendChild(badge);
  }
  card.appendChild(pos);

  const video = document.createElement("video");
  video.src = videoUrl;
  video.controls = true;
  video.preload = "metadata";
  card.appendChild(video);

  const def = document.createElement("div");
  def.className = "def";
  def.textContent = meaning.definition;
  card.appendChild(def);

  const source = document.createElement("div");
  source.className = "source";
  source.textContent = meaning.video_urls.length > 1 ? `Variante ${idx + 1}/${meaning.video_urls.length}` : "";
  card.appendChild(source);

  if (savedCardId) {
    const goToDeckBtn = document.createElement("button");
    goToDeckBtn.className = "save-btn secondary";
    goToDeckBtn.textContent = "Voir dans Mes cartes";
    goToDeckBtn.addEventListener("click", () => activateTab("deck"));
    card.appendChild(goToDeckBtn);
    return card;
  }

  const saveBtn = document.createElement("button");
  saveBtn.className = "save-btn";
  saveBtn.textContent = "✔ C'est le bon signe — enregistrer";
  saveBtn.addEventListener("click", async () => {
    saveBtn.disabled = true;
    saveBtn.textContent = "Enregistrement…";
    try {
      const res = await fetch("/api/cards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          word: meaning.word,
          part_of_speech: meaning.part_of_speech,
          definition: meaning.definition,
          source_url: meaning.source_url,
          video_url: videoUrl,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur");
      saveBtn.textContent = "✔ Enregistré dans les cartes";
      card.classList.add("already-saved");
    } catch (err) {
      saveBtn.disabled = false;
      saveBtn.textContent = "Erreur — réessayer";
      console.error(err);
    }
  });
  card.appendChild(saveBtn);

  return card;
}

// ---------- Review ----------
const reviewSetup = document.getElementById("review-setup");
const startSessionBtn = document.getElementById("start-session-btn");
const sessionSizeSelect = document.getElementById("session-size");

const reviewEmpty = document.getElementById("review-empty");
const backToSetupBtn = document.getElementById("back-to-setup-btn");

const reviewSessionComplete = document.getElementById("review-session-complete");
const sessionCompleteText = document.getElementById("session-complete-text");
const newSessionBtn = document.getElementById("new-session-btn");

const reviewCard = document.getElementById("review-card");
const reviewVideo = document.getElementById("review-video");
const reviewVideoPlaceholder = document.getElementById("review-video-placeholder");
const reviewWord = document.getElementById("review-word");
const reviewDef = document.getElementById("review-definition");
const reviewPos = document.getElementById("review-pos");
const reviewProficiency = document.getElementById("review-proficiency");
const sessionProgress = document.getElementById("session-progress");
const revealBtn = document.getElementById("reveal-btn");
const gradeButtons = document.getElementById("grade-buttons");
const nextDueInfo = document.getElementById("next-due-info");

let currentCard = null;
let session = { mode: "recognize", target: null, reviewed: 0 };

function showPanel(panel) {
  [reviewSetup, reviewEmpty, reviewSessionComplete, reviewCard].forEach((p) => (p.hidden = p !== panel));
}

function showSessionSetup() {
  showPanel(reviewSetup);
}

backToSetupBtn.addEventListener("click", showSessionSetup);
newSessionBtn.addEventListener("click", showSessionSetup);

startSessionBtn.addEventListener("click", () => {
  const mode = document.querySelector('input[name="mode"]:checked').value;
  const sizeValue = sessionSizeSelect.value;
  session = { mode, target: sizeValue === "all" ? null : parseInt(sizeValue, 10), reviewed: 0 };
  loadNextReview();
});

async function loadNextReview() {
  if (session.target !== null && session.reviewed >= session.target) {
    showPanel(reviewSessionComplete);
    sessionCompleteText.textContent = `Session terminée — ${session.reviewed} carte(s) revue(s) 🎉`;
    return;
  }

  reviewWord.hidden = true;
  reviewDef.hidden = true;
  reviewVideo.hidden = true;
  reviewVideo.removeAttribute("src");
  reviewVideoPlaceholder.hidden = true;
  gradeButtons.hidden = true;
  revealBtn.hidden = false;

  const res = await fetch("/api/review/next");
  const data = await res.json();

  if (!data.card) {
    if (session.reviewed > 0) {
      showPanel(reviewSessionComplete);
      sessionCompleteText.textContent = `Session terminée — ${session.reviewed} carte(s) revue(s), plus aucune carte due 🎉`;
      return;
    }
    showPanel(reviewEmpty);
    nextDueInfo.textContent = data.next_due_at
      ? `Prochaine carte due le ${new Date(data.next_due_at).toLocaleString("fr-FR")}.`
      : "Ajoutez des mots dans l'onglet « Ajouter un mot » pour commencer.";
    return;
  }

  currentCard = data.card;
  showPanel(reviewCard);
  reviewWord.textContent = data.card.word;
  reviewDef.textContent = data.card.definition;
  reviewPos.textContent = data.card.part_of_speech || "";
  reviewProficiency.textContent = proficiencyLabel(data.card.proficiency);
  reviewProficiency.className = `badge proficiency ${data.card.proficiency}`;
  sessionProgress.textContent = session.target !== null ? `${session.reviewed + 1} / ${session.target}` : `${session.reviewed + 1}`;
  revealBtn.textContent = session.mode === "produce" ? "Afficher la vidéo" : "Afficher la réponse";
  reviewCard.classList.toggle("mode-produce", session.mode === "produce");

  if (session.mode === "produce") {
    // Prompt = word + definition (disambiguates homonyms); answer = the sign video.
    // The video's src is only set on reveal, so it can't silently autoplay under the placeholder.
    reviewWord.hidden = false;
    reviewDef.hidden = false;
    reviewVideoPlaceholder.hidden = false;
  } else {
    // Prompt = video only; answer = word + definition.
    reviewVideo.src = data.card.video_src;
    reviewVideo.hidden = false;
  }
}

function proficiencyLabel(p) {
  return { new: "Nouveau", learning: "En cours", weak: "Fragile", strong: "Acquis" }[p] || p;
}

revealBtn.addEventListener("click", () => {
  reviewWord.hidden = false;
  reviewDef.hidden = false;
  reviewVideoPlaceholder.hidden = true;
  if (!reviewVideo.getAttribute("src") && currentCard) {
    reviewVideo.src = currentCard.video_src;
  }
  reviewVideo.hidden = false;
  gradeButtons.hidden = false;
  revealBtn.hidden = true;
});

let submittingGrade = false;

gradeButtons.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-grade]");
  if (!btn || !currentCard || submittingGrade) return;
  submittingGrade = true;
  gradeButtons.classList.add("disabled");
  try {
    await fetch(`/api/review/${currentCard.id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ grade: btn.dataset.grade }),
    });
    session.reviewed += 1;
    await loadNextReview();
  } finally {
    submittingGrade = false;
    gradeButtons.classList.remove("disabled");
  }
});

// ---------- Deck ----------
const deckList = document.getElementById("deck-list");
const deckStats = document.getElementById("deck-stats");

const PROFICIENCY_ORDER = ["new", "learning", "weak", "strong"];

async function loadDeck() {
  deckList.innerHTML = "Chargement…";
  deckStats.innerHTML = "";
  const res = await fetch("/api/cards");
  const cards = await res.json();
  deckList.innerHTML = "";

  renderDeckStats(cards);

  if (cards.length === 0) {
    deckList.innerHTML = "<p class='muted'>Aucune carte pour le moment.</p>";
    return;
  }
  cards.forEach((card) => deckList.appendChild(buildDeckCard(card)));
}

function renderDeckStats(cards) {
  const counts = { new: 0, learning: 0, weak: 0, strong: 0 };
  cards.forEach((card) => {
    if (counts[card.proficiency] !== undefined) counts[card.proficiency] += 1;
  });

  deckStats.innerHTML = "";

  const total = document.createElement("div");
  total.className = "stat-pill stat-total";
  total.innerHTML = `<span class="stat-count">${cards.length}</span><span class="stat-label">carte(s) au total</span>`;
  deckStats.appendChild(total);

  PROFICIENCY_ORDER.forEach((p) => {
    const pill = document.createElement("div");
    pill.className = `stat-pill proficiency ${p}`;
    pill.innerHTML = `<span class="stat-count">${counts[p]}</span><span class="stat-label">${proficiencyLabel(p)}</span>`;
    deckStats.appendChild(pill);
  });
}

function buildDeckCard(card) {
  const el = document.createElement("div");
  el.className = "deck-card";

  const video = document.createElement("video");
  video.src = card.video_src;
  video.controls = true;
  video.preload = "metadata";
  el.appendChild(video);

  const header = document.createElement("div");
  header.className = "deck-card-header";
  const h3 = document.createElement("h3");
  h3.textContent = card.word;
  const badge = document.createElement("span");
  badge.className = `badge proficiency ${card.proficiency}`;
  badge.textContent = proficiencyLabel(card.proficiency);
  header.appendChild(h3);
  header.appendChild(badge);
  el.appendChild(header);

  const def = document.createElement("div");
  def.className = "def";
  def.textContent = card.definition;
  el.appendChild(def);

  const metaRow = document.createElement("div");
  metaRow.className = "meta-row";
  const due = new Date(card.due_at);
  metaRow.innerHTML = `<span>Due : ${due.toLocaleDateString("fr-FR")}</span>`;
  const delBtn = document.createElement("button");
  delBtn.className = "delete-btn";
  delBtn.textContent = "Supprimer";
  delBtn.addEventListener("click", async () => {
    if (!confirm(`Supprimer la carte « ${card.word} » ?`)) return;
    await fetch(`/api/cards/${card.id}`, { method: "DELETE" });
    loadDeck();
  });
  metaRow.appendChild(delBtn);
  el.appendChild(metaRow);

  return el;
}
