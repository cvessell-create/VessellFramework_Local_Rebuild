r_system_readout_path <- function() {
  configured <- Sys.getenv("VESSELL_R_SYSTEM_READOUT_PATH", "")
  if (nzchar(configured)) return(path.expand(configured))
  file.path(path.expand("~"), ".vessell", "r-system-readout.md")
}

r_system_readout_update <- function(operation, status = "invoked") {
  descriptions <- c(
    setup = "Checks installed R package metadata and installs missing declared packages.",
    memory_db_access = "Opens the local SQLite memory store and ensures its schema exists.",
    memory_add = "Adds a cited memory as pending and records its creation review event.",
    memory_review = "Reviews a memory and may create a linked pending correction.",
    memory_list = "Lists memory records and their review history, optionally by status.",
    memory_retrieve = "Searches approved, unexpired memories in one declared scope.",
    statistics_smoke_checks = "Runs statistical assertions on generated synthetic data only.",
    github_observatory = "Collects projected repository, workflow, issue, pull-request, and traffic metadata.",
    prompt_audit = "Reads selected aggregate summaries from the local SQL prompt catalog.",
    memory_database_conversion = "Copies memory records and review history to a new SQLite database."
  )
  if (length(operation) != 1L || is.na(operation) || !operation %in% names(descriptions)) {
    warning("R system readout skipped for an unknown operation.", call. = FALSE)
    return(invisible(FALSE))
  }
  if (length(status) != 1L || is.na(status) ||
      !status %in% c("invoked", "completed", "failed")) {
    warning("R system readout skipped for an invalid status.", call. = FALSE)
    return(invisible(FALSE))
  }

  path <- r_system_readout_path()
  parent <- dirname(path)
  if (!dir.exists(parent) && !dir.create(parent, recursive = TRUE, showWarnings = FALSE)) {
    warning("Cannot create the private R readout directory: ", parent, call. = FALSE)
    return(invisible(FALSE))
  }
  updated <- format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  lines <- c(
    "# R system usage readout",
    "",
    paste0("- Updated (UTC): `", updated, "`"),
    paste0("- Latest operation: `", operation, "`"),
    paste0("- Operation status: `", status, "`"),
    paste0("- R runtime: `", getRversion(), "`"),
    paste0("- Operation: ", descriptions[[operation]]),
    "",
    "## Collection and review boundaries",
    "",
    "- This file records only the latest operation, its status, timestamp, and R runtime.",
    "- It never copies memory statements, citations, reviewer notes, query text, prompt content,",
    "  repository payloads, credentials, statistical observations, or analysis results.",
    "- The operation-specific data categories and limitations are documented in",
    "  `docs/r-system-readout.md`.",
    "- This readout is local operational metadata, not evidence, a review decision, or authorization."
  )
  temporary <- tempfile(".r-system-readout-", tmpdir = parent)
  on.exit(unlink(temporary), add = TRUE)
  tryCatch({
    writeLines(lines, temporary, useBytes = TRUE)
    Sys.chmod(temporary, mode = "0600")
    if (!file.rename(temporary, path)) {
      stop("Could not atomically update the readout.")
    }
    invisible(TRUE)
  }, error = function(error) {
    warning("Could not update the R system readout: ", conditionMessage(error), call. = FALSE)
    invisible(FALSE)
  })
}
