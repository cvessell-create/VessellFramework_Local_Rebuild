#!/usr/bin/env Rscript

source("r/memory_store.R")

temporary_directory <- tempfile("vessell-memory-r-")
dir.create(temporary_directory)
database <- file.path(temporary_directory, "memories.sqlite3")
memory <- list(
  statement = "Python 3.12 is supported by this repository.",
  scope = "repository",
  citations = c("pyproject.toml:10", "CONTRIBUTING.md:15")
)

identifier <- memory_add(database, memory)
stopifnot(length(memory_list(database)) == 1L)
stopifnot(memory_list(database)[[1L]]$status == "pending")
stopifnot(length(memory_retrieve(database, "Python compatibility", "repository")) == 0L)

invisible(memory_review(
  database, identifier, "approve", reviewer = "test reviewer", note = "Verified"
))
found <- memory_retrieve(database, "Python 3.12", "repository")
stopifnot(length(found) == 1L)
stopifnot(found[[1L]]$id == identifier)
stopifnot(identical(unlist(found[[1L]]$citations), memory$citations))
stopifnot(found[[1L]]$review_history[[2L]]$reviewer == "test reviewer")
stopifnot(length(memory_retrieve(database, "Python", "user")) == 0L)

replacement <- list(
  statement = "Python 3.12 is supported and Python 3.13 is tested.",
  scope = "repository",
  citations = list(".github/workflows/ci.yml:12-17")
)
replacement_id <- memory_review(
  database, identifier, "correct", replacement = replacement, reviewer = "test reviewer"
)
stopifnot(memory_list(database, "corrected")[[1L]]$id == identifier)
stopifnot(length(memory_retrieve(database, "Python", "repository")) == 0L)
stopifnot(memory_list(database, "pending")[[1L]]$id == replacement_id)
invisible(memory_review(database, replacement_id, "approve"))
corrected <- memory_retrieve(database, "Python 3.13", "repository")[[1L]]
stopifnot(corrected$id == replacement_id)
stopifnot(identical(unlist(corrected$citations), ".github/workflows/ci.yml:12-17"))

rejected_id <- memory_add(database, list(
  statement = "A rejected memory is not retrievable.",
  scope = "repository",
  citations = "test fixture"
))
invisible(memory_review(database, rejected_id, "reject"))
stopifnot(memory_list(database, "rejected")[[1L]]$id == rejected_id)
stopifnot(length(memory_retrieve(database, "rejected memory", "repository")) == 0L)

expired_id <- memory_add(database, list(
  statement = "An expired memory is not retrievable.",
  scope = "repository",
  citations = "test fixture",
  valid_until = "2000-01-01T00:00:00Z"
))
invisible(memory_review(database, expired_id, "approve"))
stopifnot(length(memory_retrieve(database, "expired memory", "repository")) == 0L)

stopifnot(inherits(try(memory_review(database, identifier, "approve"), silent = TRUE), "try-error"))
stopifnot(inherits(try(
  memory_review(database, identifier, "correct", replacement = list(
    statement = "scope change attempt",
    scope = "user",
    citations = "test fixture"
  )), silent = TRUE
), "try-error"))

python_database <- file.path(temporary_directory, "python.sqlite3")
r_database <- file.path(temporary_directory, "converted.sqlite3")
python_connection <- memory_db_connect(python_database)
invisible(DBI::dbExecute(
  python_connection,
  paste(
    "INSERT INTO memories",
    "(id, statement, scope, citations_json, status, created_at, valid_until, supersedes_id)",
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
  ),
  params = list(
    "python-record-1", "Memory created in the Python-compatible schema.", "repository",
    jsonlite::toJSON(c("README.md:1", "r/README.md:1")), "approved",
    "2026-10-07T00:00:00.000000+00:00", NA_character_, NA_character_
  )
))
invisible(DBI::dbExecute(
  python_connection,
  paste(
    "INSERT INTO memory_reviews (memory_id, decision, reviewer, note, occurred_at)",
    "VALUES (?, ?, ?, ?, ?)"
  ),
  params = list(
    "python-record-1", "approved", "migration-test", "retained", "2026-10-07T00:00:00+00:00"
  ))
)
DBI::dbDisconnect(python_connection)
converter_output <- system2(
  "Rscript",
  c(
    "r/convert_python_memory_db.R",
    shQuote(python_database),
    shQuote(r_database)
  ),
  stdout = TRUE,
  stderr = TRUE
)
converter_status <- attr(converter_output, "status")
if (is.null(converter_status)) converter_status <- 0L
stopifnot(converter_status == 0L)
converted <- memory_retrieve(r_database, "Python schema", "repository")
stopifnot(length(converted) == 1L)
stopifnot(converted[[1L]]$id == "python-record-1")
stopifnot(identical(
  unlist(converted[[1L]]$citations),
  c("README.md:1", "r/README.md:1")
))
stopifnot(converted[[1L]]$review_history[[1L]]$reviewer == "migration-test")
existing_destination_output <- suppressWarnings(system2(
  "Rscript",
  c("r/convert_python_memory_db.R", shQuote(python_database), shQuote(r_database)),
  stdout = TRUE,
  stderr = TRUE
))
existing_destination_status <- attr(existing_destination_output, "status")
if (is.null(existing_destination_status)) existing_destination_status <- 0L
stopifnot(existing_destination_status != 0L)
source_connection <- DBI::dbConnect(RSQLite::SQLite(), python_database)
stopifnot(DBI::dbGetQuery(source_connection, "SELECT COUNT(*) AS n FROM memories")$n[[1L]] == 1L)
DBI::dbDisconnect(source_connection)

unlink(temporary_directory, recursive = TRUE)
cat("R memory-store tests passed.\n")
