#!/usr/bin/env Rscript

convert_python_memory_db <- function(arguments = commandArgs(trailingOnly = TRUE)) {
  if (length(arguments) != 2L) {
    stop(
      "Usage: Rscript r/convert_python_memory_db.R SOURCE_PYTHON_DB DESTINATION_R_DB",
      call. = FALSE
    )
  }
  source_path <- normalizePath(arguments[[1L]], mustWork = TRUE)
  destination_path <- normalizePath(arguments[[2L]], mustWork = FALSE)
  if (identical(source_path, destination_path)) {
    stop("Source and destination databases must be different files.", call. = FALSE)
  }
  if (file.exists(destination_path)) {
    stop("Destination already exists; choose a new path to avoid overwriting data.",
         call. = FALSE)
  }
  if (!requireNamespace("DBI", quietly = TRUE) ||
      !requireNamespace("RSQLite", quietly = TRUE) ||
      !requireNamespace("jsonlite", quietly = TRUE) ||
      !requireNamespace("uuid", quietly = TRUE)) {
    stop("Install R dependencies: install.packages(c('DBI', 'RSQLite', 'jsonlite', 'uuid'))",
         call. = FALSE)
  }
  script_path <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[[1L]])
  source(file.path(dirname(normalizePath(script_path)), "memory_store.R"), local = TRUE)

  source_connection <- DBI::dbConnect(RSQLite::SQLite(), source_path)
  on.exit(DBI::dbDisconnect(source_connection), add = TRUE)
  tables <- DBI::dbListTables(source_connection)
  required <- c("memories", "memory_reviews")
  if (!all(required %in% tables)) {
    stop("Source database is missing the Python reviewed-memory tables.", call. = FALSE)
  }
  memories <- DBI::dbGetQuery(
    source_connection, "SELECT * FROM memories ORDER BY created_at, id"
  )
  reviews <- DBI::dbGetQuery(source_connection, "SELECT * FROM memory_reviews ORDER BY id")
  for (index in seq_len(nrow(memories))) {
    citations <- jsonlite::fromJSON(memories$citations_json[[index]], simplifyVector = TRUE)
    expiry <- memories$valid_until[[index]]
    memory_validate(list(
      statement = memories$statement[[index]],
      scope = memories$scope[[index]],
      citations = citations,
      valid_until = if (is.na(expiry)) NULL else expiry
    ))
  }
  remaining <- seq_len(nrow(memories))
  insertion_order <- integer()
  inserted_ids <- character()
  while (length(remaining)) {
    ready <- remaining[vapply(remaining, function(index) {
      parent_id <- memories$supersedes_id[[index]]
      is.na(parent_id) || !nzchar(parent_id) || parent_id %in% inserted_ids
    }, logical(1))]
    if (!length(ready)) {
      stop("Source memories contain a missing or cyclic correction link.", call. = FALSE)
    }
    insertion_order <- c(insertion_order, ready)
    inserted_ids <- c(inserted_ids, memories$id[ready])
    remaining <- setdiff(remaining, ready)
  }

  destination_connection <- memory_db_connect(destination_path)
  on.exit(DBI::dbDisconnect(destination_connection), add = TRUE)
  DBI::dbWithTransaction(destination_connection, {
    for (index in insertion_order) {
      row <- memories[index, , drop = FALSE]
      DBI::dbExecute(
        destination_connection,
        paste(
          "INSERT INTO memories",
          "(id, statement, scope, citations_json, status, created_at, valid_until, supersedes_id)",
          "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        params = unname(as.list(row[1L, c(
          "id", "statement", "scope", "citations_json", "status", "created_at",
          "valid_until", "supersedes_id"
        )]))
      )
    }
    if (nrow(reviews)) {
      for (index in seq_len(nrow(reviews))) {
        row <- reviews[index, , drop = FALSE]
        DBI::dbExecute(
          destination_connection,
          paste(
            "INSERT INTO memory_reviews (id, memory_id, decision, reviewer, note, occurred_at)",
            "VALUES (?, ?, ?, ?, ?, ?)"
          ),
          params = unname(as.list(row[1L, c(
            "id", "memory_id", "decision", "reviewer", "note", "occurred_at"
          )]))
        )
      }
    }
  })
  cat(jsonlite::toJSON(
    list(
      source = source_path,
      destination = destination_path,
      memories_converted = nrow(memories),
      review_events_converted = nrow(reviews)
    ),
    auto_unbox = TRUE, pretty = TRUE
  ), "\n")
}

tryCatch(
  convert_python_memory_db(),
  error = function(error) {
    cat("CONVERSION FAILED: ", conditionMessage(error), "\n", file = stderr())
    quit(status = 1L)
  }
)
