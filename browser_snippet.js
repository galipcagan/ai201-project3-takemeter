/*
 * Reddit comment grabber (browser-console method).
 *
 * HOW TO USE:
 *   1. Open a r/soccer comment thread in your browser (the OLD reddit UI is
 *      easiest: replace www.reddit.com with old.reddit.com in the URL).
 *   2. Scroll down and click "load more comments" a few times so the comments
 *      you want are actually on the page.
 *   3. Open DevTools (F12) -> Console tab.
 *   4. Paste this whole file, press Enter. A .json file downloads automatically.
 *   5. Move that file into data/ and run:  python fetch_reddit.py parse data/<file>.json
 *
 * Works on old.reddit.com. The new UI changes class names often; if nothing is
 * found, switch to old.reddit.com.
 */
(function () {
  const out = [];

  // old.reddit.com: each comment is a .comment with a .usertext-body
  document.querySelectorAll(".comment").forEach((el) => {
    const bodyEl = el.querySelector(".usertext-body .md");
    if (!bodyEl) return;
    const body = bodyEl.innerText.trim();
    if (!body || body === "[deleted]" || body === "[removed]") return;
    const scoreEl = el.querySelector(".score.unvoted");
    const score = scoreEl ? scoreEl.getAttribute("title") || scoreEl.innerText : "";
    out.push({
      id: el.getAttribute("data-fullname") || "",
      kind: "comment",
      title: "",
      body: body,
      score: parseInt(score, 10) || 0,
      num_comments: 0,
      permalink: "https://www.reddit.com" + (el.getAttribute("data-permalink") || ""),
    });
  });

  if (out.length === 0) {
    console.warn("No comments found. Are you on old.reddit.com on a comment thread?");
    return;
  }

  const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "reddit_comments_" + Date.now() + ".json";
  a.click();
  console.log("Grabbed " + out.length + " comments. File downloading...");
})();
