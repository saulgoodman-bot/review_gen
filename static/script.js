// ---------- image dropzones ----------
document.querySelectorAll(".dropzone").forEach((zone) => {
  const input = zone.querySelector("input[type=file]");
  const preview = zone.querySelector(".dropzone__preview");

  zone.addEventListener("click", () => input.click());

  input.addEventListener("change", () => {
    const file = input.files[0];
    if (!file) return;
    preview.src = URL.createObjectURL(file);
    zone.classList.add("has-image");
  });

  ["dragover", "dragenter"].forEach((evt) =>
    zone.addEventListener(evt, (e) => {
      e.preventDefault();
      zone.classList.add("is-dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    zone.addEventListener(evt, (e) => {
      e.preventDefault();
      zone.classList.remove("is-dragover");
    })
  );
  zone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (!file) return;
    input.files = e.dataTransfer.files;
    preview.src = URL.createObjectURL(file);
    zone.classList.add("has-image");
  });
});

// ---------- char counter ----------
const reviewText = document.getElementById("review_text");
const charCount = document.getElementById("char-count");
reviewText.addEventListener("input", () => {
  charCount.textContent = reviewText.value.length;
});

// ---------- half-star picker ----------
const picker = document.getElementById("star-picker");
const fill = document.getElementById("star-fill");
const ratingInput = document.getElementById("rating");
const ratingReadout = document.getElementById("rating-readout");

function setRating(value) {
  value = Math.max(0, Math.min(5, Math.round(value * 2) / 2));
  ratingInput.value = value;
  ratingReadout.textContent = value;
  fill.style.width = (value / 5) * 100 + "%";
}

function ratingFromEvent(e) {
  const rect = picker.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const raw = (x / rect.width) * 5;
  return Math.max(0, Math.min(5, Math.round(raw * 2) / 2));
}

picker.addEventListener("mousemove", (e) => setRating(ratingFromEvent(e)));
picker.addEventListener("mouseleave", () => setRating(parseFloat(ratingInput.value) || 0));
picker.addEventListener("click", (e) => {
  const value = ratingFromEvent(e);
  setRating(value);
  ratingInput.dataset.locked = value;
});
picker.addEventListener("mouseleave", () => {
  const locked = ratingInput.dataset.locked || 0;
  setRating(parseFloat(locked));
});
setRating(0);

// ---------- submit ----------
const form = document.getElementById("review-form");
const btn = document.getElementById("generate-btn");
const errorBox = document.getElementById("form-error");
const loading = document.getElementById("loading");
const resultsEmpty = document.getElementById("results-empty");
const resultsGrid = document.getElementById("results-grid");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.hidden = true;

  const rating = parseFloat(ratingInput.value || "0");
  if (rating <= 0) {
    errorBox.textContent = "Pick a star rating before generating.";
    errorBox.hidden = false;
    return;
  }

  const formData = new FormData(form);
  btn.disabled = true;
  btn.textContent = "Generating…";
  resultsEmpty.hidden = true;
  resultsGrid.hidden = true;
  loading.hidden = false;

  try {
    const res = await fetch("/generate", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Generation failed.");

    document.getElementById("cover-preview").src = data.cover;
    document.getElementById("cover-download").href = data.cover;
    document.getElementById("review-preview").src = data.review;
    document.getElementById("review-download").href = data.review;

    loading.hidden = true;
    resultsGrid.hidden = false;
  } catch (err) {
    loading.hidden = true;
    resultsEmpty.hidden = false;
    errorBox.textContent = err.message;
    errorBox.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Instagram posts";
  }
});
