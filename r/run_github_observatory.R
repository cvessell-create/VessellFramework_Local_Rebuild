#!/usr/bin/env Rscript
arguments <- commandArgs(trailingOnly = TRUE)
if (length(arguments) > 2L) {
  stop("Usage: Rscript r/run_github_observatory.R [output-root] [max-pages]",
       call. = FALSE)
}
source("r/github_metadata.R")
source("r/metadata_learning.R")
metadata_require_json()
output_root <- if (length(arguments)) arguments[[1]] else "outputs/github-observatory"
max_pages <- if (length(arguments) >= 2L) suppressWarnings(as.numeric(arguments[[2]])) else 20L
directory <- file.path(output_root, paste0(
  format(Sys.time(), "%Y%m%dT%H%M%S", tz = "UTC"), "-", Sys.getpid()
))
if (!dir.create(directory, recursive = TRUE)) {
  stop("Cannot create a new observatory output directory: ", directory, call. = FALSE)
}
snapshot <- collect_github_metadata(max_pages = max_pages)
saveRDS(snapshot, file.path(directory, "snapshot.rds"))
metadata_write_json(snapshot, file.path(directory, "snapshot.json"))
metadata_write_json(metadata_summary(snapshot), file.path(directory, "summary.json"))
learning <- learn_metadata(snapshot)
saveRDS(learning, file.path(directory, "learning.rds"))
learning_summary <- learning
learning_summary$model <- NULL
learning_summary$partitions <- NULL
learning_summary$predictions <- NULL
metadata_write_json(learning_summary, file.path(directory, "learning.json"))
if (!is.null(learning$predictions)) {
  write.csv(learning$predictions, file.path(directory, "held_out_predictions.csv"),
            row.names = FALSE)
}
tables <- list(
  runs = metadata_run_table(snapshot),
  commits = metadata_table(snapshot$endpoints$commits$data,
                           c("sha", "committed_at", "author_login", "html_url")),
  issues = metadata_table(snapshot$endpoints$issues$data,
                          c("id", "number", "state", "created_at", "closed_at",
                            "is_pull_request", "html_url")),
  pulls = metadata_table(snapshot$endpoints$pulls$data,
                         c("id", "number", "state", "created_at", "merged_at", "html_url"))
)
for (name in names(tables)) {
  write.csv(tables[[name]], file.path(directory, paste0(name, ".csv")), row.names = FALSE)
}
suggestions <- metadata_suggestions(snapshot, learning)
preview <- list(
  state = "PREVIEW_REQUIRES_HUMAN_REVIEW", repository = github_repository,
  collected_at = snapshot$completed_at,
  collection_status = lapply(snapshot$endpoints, function(x) x$status),
  learning_status = learning$status, suggestions = suggestions,
  limits = c("Metadata is observational; it does not establish causes, quality or user motives.",
             "No code changes, report release, workflow dispatch or external execution authorized.",
             "Traffic is a rolling 14-day snapshot; do not sum overlapping unique counts.",
             "The snapshot has metadata projections only, not bodies, logs, emails or tokens.")
)
metadata_write_json(preview, file.path(directory, "suggestions.json"))
writeLines(c(
  "# GitHub observatory: human-review preview", "",
  paste("Collected:", snapshot$completed_at),
  paste("Learning status:", learning$status), "",
  "This is not a released framework report. No automated code changes are permitted.", "",
  unlist(lapply(suggestions, function(suggestion) {
    c(paste0("## ", suggestion$kind), suggestion$suggestion,
      if (!is.null(suggestion$workflow_id)) paste("Workflow ID:", suggestion$workflow_id),
      if (!is.null(suggestion$failed_runs)) {
        sprintf("Observed failures: %d/%d (%.1f%%).",
                suggestion$failed_runs, suggestion$evaluated_runs,
                100 * suggestion$failure_fraction)
      },
      if (!is.null(suggestion$count)) paste("Observed action-required runs:", suggestion$count),
      suggestion$evidence_urls, "")
  })),
  if (!is.null(learning$scores)) {
    c("## Held-out model comparison",
      unlist(lapply(names(learning$scores), function(part) {
        score <- learning$scores[[part]]
        vapply(names(score), function(model) {
          sprintf("%s / %s: Brier %.4f; log loss %.4f.",
                  part, model, score[[model]]$brier, score[[model]]$log_loss)
        }, character(1))
      })), "")
  },
  "## Limits", preview$limits
), file.path(directory, "review-preview.md"))
cat("Saved read-only metadata and human-review preview to:", directory, "\n")
cat("Learning status:", learning$status, "\n")
