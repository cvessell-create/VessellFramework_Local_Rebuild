#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
database <- if (length(args) >= 1) args[[1]] else "data/sql_reference.sqlite"

if (!file.exists(database)) {
  stop(sprintf("Prompt audit catalog not found: %s", database), call. = FALSE)
}
if (!requireNamespace("DBI", quietly = TRUE) ||
    !requireNamespace("RSQLite", quietly = TRUE)) {
  stop("Install the R packages DBI and RSQLite to read the audit catalog.",
       call. = FALSE)
}

connection <- DBI::dbConnect(
  RSQLite::SQLite(),
  dbname = normalizePath(database),
  flags = RSQLite::SQLITE_RO
)
on.exit(DBI::dbDisconnect(connection), add = TRUE)

tables <- DBI::dbListTables(connection)
required <- c("metadata", "prompt_audit_cases", "prompt_guidance")
if (!all(required %in% tables)) {
  stop("Database lacks prompt-audit catalog tables.", call. = FALSE)
}

case_count <- DBI::dbGetQuery(
  connection,
  "SELECT COUNT(*) AS n FROM prompt_audit_cases"
)$n[[1]]
outcomes <- DBI::dbGetQuery(
  connection,
  paste(
    "SELECT outcome_status, COUNT(*) AS cases",
    "FROM prompt_audit_cases",
    "GROUP BY outcome_status ORDER BY outcome_status"
  )
)
guidance <- DBI::dbGetQuery(
  connection,
  paste(
    "SELECT dialect_id, COUNT(*) AS templates",
    "FROM prompt_guidance GROUP BY dialect_id ORDER BY dialect_id"
  )
)

cat("Selected audit summaries:", case_count, "\n")
cat("Visible outcome classes:\n")
print(outcomes, row.names = FALSE)
cat("Prompt templates by dialect:\n")
print(guidance, row.names = FALSE)
cat("Private chain-of-thought: NOT_ACCESSIBLE; no mental-state inference made.\n")
cat(
  "Scope: selected analyst summaries only; not a full account export, internal model trace,",
  "representative frequency sample, or causal evaluation.\n"
)
