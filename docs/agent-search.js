"use strict";

function searchIndex(index, query, limit = 10) {
  query = query.trim();
  const terms = query.toLowerCase().match(/[\p{L}\p{N}]+/gu) || [];
  if (!terms.length || Array.from(query).length > 200 || !Number.isInteger(limit) || limit < 1 || limit > 10) {
    throw new Error("Use 1-200 characters containing letters or digits and a limit of 1-10.");
  }
  const hits = [];
  for (const row of index.documents) {
    row.text.split(/\r?\n/).forEach((line, number) => {
      const tokens = line.toLowerCase().match(/[\p{L}\p{N}]+/gu) || [];
      if (terms.every(term => tokens.includes(term))) {
        hits.push({
          path: row.path, title: row.title, line: number + 1,
          snippet: Array.from(line).slice(0, 1000).join(""), source_sha256: row.sha256
        });
      }
    });
  }
  return {
    results: hits.slice(0, limit), total_matches: hits.length,
    result_count: Math.min(hits.length, limit), limit_hit: hits.length > limit,
    status: hits.length ? "MATCHES IN SCOPE" : "NOT FOUND IN SCOPE"
  };
}

if (typeof module !== "undefined") module.exports = { searchIndex };

if (typeof document !== "undefined") {
  const status = document.getElementById("status");
  const results = document.getElementById("results");
  const button = document.getElementById("search-button");
  fetch("agent-reference-index.json")
    .then(response => {
      if (!response.ok) throw new Error(`Index request failed: HTTP ${response.status}`);
      return response.json();
    })
    .then(index => {
      if (index.contract_version !== "1.0" || !Array.isArray(index.documents) ||
          index.documents.length !== 12 || index.documents.some(row =>
            typeof row.path !== "string" || typeof row.title !== "string" ||
            typeof row.text !== "string" || !/^[a-f0-9]{64}$/.test(row.sha256))) {
        throw new Error("Invalid public reference index.");
      }
      status.textContent = `Ready: ${index.documents.length} public document snapshots. No live sources checked.`;
      button.disabled = false;
      document.getElementById("search-form").addEventListener("submit", event => {
        event.preventDefault();
        results.replaceChildren();
        try {
          const found = searchIndex(index, document.getElementById("query").value);
          status.textContent = `${found.status}: ${found.result_count} of ${found.total_matches} matching lines; limit hit: ${found.limit_hit}. Corpus: 12 public documents.`;
          for (const hit of found.results) {
            const item = document.createElement("li");
            const link = document.createElement("a");
            link.href = `https://github.com/cvessell-create/VessellFramework_Local_Rebuild/blob/master/${hit.path}#L${hit.line}`;
            link.textContent = `${hit.title} (${hit.path}:${hit.line})`;
            const snippet = document.createElement("pre");
            snippet.textContent = hit.snippet;
            const hash = document.createElement("small");
            hash.textContent = `REPOSITORY REFERENCE ONLY | Source SHA-256: ${hit.source_sha256}`;
            item.append(link, snippet, hash);
            results.append(item);
          }
        } catch (error) {
          status.textContent = `Search failed: ${error.message}`;
        }
      });
    })
    .catch(error => {
      status.textContent = `Reference search unavailable: ${error.message}`;
      button.disabled = true;
    });
}
