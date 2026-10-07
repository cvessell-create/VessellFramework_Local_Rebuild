#!/usr/bin/env Rscript

memory_scopes <- c("user", "repository")
memory_statuses <- c("pending", "approved", "corrected", "rejected")
memory_decisions <- c("created", "approved", "corrected", "rejected")

memory_now <- function() {
  format(Sys.time(), "%Y-%m-%dT%H:%M:%OS6Z", tz = "UTC")
}

memory_db_connect <- function(database) {
  if (!requireNamespace("DBI", quietly = TRUE) ||
      !requireNamespace("RSQLite", quietly = TRUE)) {
    stop("Install the R dependencies first: install.packages(c('DBI', 'RSQLite', 'jsonlite'))")
  }
  parent <- dirname(path.expand(database))
  if (!dir.exists(parent) && !dir.create(parent, recursive = TRUE)) {
    stop("Cannot create database directory: ", parent)
  }
  connection <- DBI::dbConnect(RSQLite::SQLite(), path.expand(database))
  DBI::dbExecute(connection, "PRAGMA foreign_keys = ON")
  DBI::dbExecute(
    connection,
    paste(
      "CREATE TABLE IF NOT EXISTS memories (",
      "id TEXT PRIMARY KEY,",
      "statement TEXT NOT NULL CHECK(length(trim(statement)) > 0),",
      "scope TEXT NOT NULL CHECK(scope IN ('user', 'repository')),",
      paste0(
        "citations_json TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('",
        paste(memory_statuses, collapse = "', '"), "')), "
      ),
      "created_at TEXT NOT NULL, valid_until TEXT,",
      "supersedes_id TEXT REFERENCES memories(id))"
    )
  )
  DBI::dbExecute(
    connection,
    paste(
      "CREATE TABLE IF NOT EXISTS memory_reviews (",
      "id INTEGER PRIMARY KEY AUTOINCREMENT,",
      "memory_id TEXT NOT NULL REFERENCES memories(id),",
      paste0(
        "decision TEXT NOT NULL CHECK(decision IN ('",
        paste(memory_decisions, collapse = "', '"), "')), "
      ),
      "reviewer TEXT NOT NULL, note TEXT NOT NULL, occurred_at TEXT NOT NULL)"
    )
  )
  connection
}

memory_validate <- function(memory) {
  if (!is.list(memory) ||
      !is.character(memory$statement) ||
      length(memory$statement) != 1L ||
      !nzchar(trimws(memory$statement))) {
    stop("statement must be a non-empty string.")
  }
  if (!is.character(memory$scope) ||
      length(memory$scope) != 1L ||
      !memory$scope %in% memory_scopes) {
    stop("scope must be one of: user, repository.")
  }
  if (!is.character(memory$citations) ||
      length(memory$citations) < 1L ||
      any(!nzchar(trimws(memory$citations)))) {
    stop("citations must be a non-empty array of non-empty source references.")
  }
  if (!is.null(memory$valid_until)) {
    if (!is.character(memory$valid_until) ||
        length(memory$valid_until) != 1L ||
        is.na(as.POSIXct(memory$valid_until, format = "%Y-%m-%dT%H:%M:%OSZ",
                        tz = "UTC"))) {
      stop("valid_until must be an ISO-8601 UTC timestamp ending in Z.")
    }
  }
  invisible(TRUE)
}

memory_decode_row <- function(connection, row) {
  record <- list(
    id = row$id,
    statement = row$statement,
    scope = row$scope,
    citations = jsonlite::fromJSON(row$citations_json, simplifyVector = TRUE),
    status = row$status,
    created_at = row$created_at,
    valid_until = row$valid_until,
    supersedes_id = row$supersedes_id
  )
  reviews <- DBI::dbGetQuery(
    connection,
    paste(
      "SELECT decision, reviewer, note, occurred_at FROM memory_reviews",
      "WHERE memory_id = ? ORDER BY occurred_at, id"
    ),
    params = list(row$id)
  )
  record$review_history <- lapply(seq_len(nrow(reviews)), function(index) {
    as.list(reviews[index, , drop = FALSE])
  })
  record
}

memory_add <- function(database, memory) {
  memory_validate(memory)
  identifier <- as.character(uuid::UUIDgenerate())
  now <- memory_now()
  connection <- memory_db_connect(database)
  on.exit(DBI::dbDisconnect(connection))
  DBI::dbWithTransaction(connection, {
    DBI::dbExecute(
      connection,
      paste(
        "INSERT INTO memories",
        "(id, statement, scope, citations_json, status, created_at, valid_until)",
        "VALUES (?, ?, ?, ?, 'pending', ?, ?)"
      ),
      params = list(
        identifier, trimws(memory$statement), memory$scope,
        jsonlite::toJSON(memory$citations, auto_unbox = FALSE), now,
        memory$valid_until %||% NA_character_
      )
    )
    DBI::dbExecute(
      connection,
      paste(
        "INSERT INTO memory_reviews (memory_id, decision, reviewer, note, occurred_at)",
        "VALUES (?, 'created', 'system', '', ?)"
      ),
      params = list(identifier, now)
    )
  })
  identifier
}

`%||%` <- function(value, fallback) {
  if (is.null(value)) fallback else value
}

memory_review <- function(database, identifier, decision, reviewer = "local-user",
                          note = "", replacement = NULL) {
  if (length(decision) != 1L || !decision %in% c("approve", "reject", "correct")) {
    stop("decision must be approve, reject, or correct.")
  }
  if (!nzchar(trimws(reviewer))) stop("reviewer must not be empty.")
  if (identical(decision, "correct")) {
    if (is.null(replacement)) stop("correct requires replacement content.")
    memory_validate(replacement)
  } else if (!is.null(replacement)) {
    stop("replacement content is only valid with decision=correct.")
  }
  connection <- memory_db_connect(database)
  on.exit(DBI::dbDisconnect(connection))
  DBI::dbWithTransaction(connection, {
    row <- DBI::dbGetQuery(
      connection, "SELECT * FROM memories WHERE id = ?", params = list(identifier)
    )
    if (nrow(row) != 1L) stop("Memory not found: ", identifier)
    status <- row$status[[1L]]
    allowed <- if (decision %in% c("reject", "correct")) {
      c("pending", "approved")
    } else {
      "pending"
    }
    if (!status %in% allowed) stop("Cannot ", decision, " a memory with status ", status, ".")
    if (identical(decision, "correct") &&
        !identical(replacement$scope, row$scope[[1L]])) {
      stop("a correction must retain the original memory scope.")
    }
    new_status <- switch(
      decision, approve = "approved", reject = "rejected", correct = "corrected"
    )
    now <- memory_now()
    DBI::dbExecute(
      connection, "UPDATE memories SET status = ? WHERE id = ?",
      params = list(new_status, identifier)
    )
    DBI::dbExecute(
      connection,
      paste(
        "INSERT INTO memory_reviews (memory_id, decision, reviewer, note, occurred_at)",
        "VALUES (?, ?, ?, ?, ?)"
      ),
      params = list(identifier, new_status, reviewer, note, now)
    )
    replacement_id <- NULL
    if (identical(decision, "correct")) {
      replacement_id <- as.character(uuid::UUIDgenerate())
      DBI::dbExecute(
        connection,
        paste(
          "INSERT INTO memories",
          "(id, statement, scope, citations_json, status, created_at, valid_until, supersedes_id)",
          "VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)"
        ),
        params = list(
          replacement_id, trimws(replacement$statement), replacement$scope,
          jsonlite::toJSON(replacement$citations, auto_unbox = FALSE), now,
          replacement$valid_until %||% NA_character_, identifier
        )
      )
      DBI::dbExecute(
        connection,
        paste(
          "INSERT INTO memory_reviews (memory_id, decision, reviewer, note, occurred_at)",
          "VALUES (?, 'created', ?, ?, ?)"
        ),
        params = list(replacement_id, reviewer, paste("Correction of", identifier), now)
      )
    }
    replacement_id
  })
}

memory_list <- function(database, status = NULL) {
  if (!is.null(status) && !status %in% memory_statuses) {
    stop("status must be one of: ", paste(memory_statuses, collapse = ", "), ".")
  }
  connection <- memory_db_connect(database)
  on.exit(DBI::dbDisconnect(connection))
  if (is.null(status)) {
    rows <- DBI::dbGetQuery(connection, "SELECT * FROM memories ORDER BY created_at, id")
  } else {
    rows <- DBI::dbGetQuery(
      connection, "SELECT * FROM memories WHERE status = ? ORDER BY created_at, id",
      params = list(status)
    )
  }
  lapply(seq_len(nrow(rows)), function(index) {
    memory_decode_row(connection, rows[index, , drop = FALSE])
  })
}

memory_retrieve <- function(database, query, scope, limit = 10L) {
  if (length(scope) != 1L || !scope %in% memory_scopes) {
    stop("scope must be one of: user, repository.")
  }
  if (length(limit) != 1L || is.na(limit) || limit < 1L) {
    stop("limit must be at least 1.")
  }
  terms <- unique(tolower(unlist(strsplit(query, "[^[:alnum:]_-]+"))))
  terms <- terms[nzchar(terms)]
  if (!length(terms)) stop("query must contain at least one searchable term.")
  connection <- memory_db_connect(database)
  on.exit(DBI::dbDisconnect(connection))
  rows <- DBI::dbGetQuery(
    connection,
    paste(
      "SELECT * FROM memories WHERE status = 'approved' AND scope = ?",
      "AND (valid_until IS NULL OR valid_until > ?)",
      "ORDER BY created_at DESC, id"
    ),
    params = list(scope, memory_now())
  )
  results <- list()
  for (index in seq_len(nrow(rows))) {
    statement_terms <- unique(tolower(unlist(strsplit(
      rows$statement[[index]], "[^[:alnum:]_-]+"
    ))))
    matched <- intersect(terms, statement_terms[nzchar(statement_terms)])
    if (length(matched)) {
      record <- memory_decode_row(connection, rows[index, , drop = FALSE])
      record$relevance <- length(matched) / length(terms)
      record$matched_terms <- matched
      results[[length(results) + 1L]] <- record
    }
  }
  if (!length(results)) return(results)
  ordering <- order(
    -vapply(results, `[[`, numeric(1), "relevance"),
    vapply(results, `[[`, character(1), "created_at"),
    vapply(results, `[[`, character(1), "id")
  )
  results[head(ordering, as.integer(limit))]
}

memory_cli <- function(arguments = commandArgs(trailingOnly = TRUE)) {
  if (!requireNamespace("jsonlite", quietly = TRUE) ||
      !requireNamespace("uuid", quietly = TRUE)) {
    stop("Install R dependencies: install.packages(c('DBI', 'RSQLite', 'jsonlite', 'uuid'))")
  }
  default_database <- file.path(path.expand("~"), ".vessell", "memories.sqlite3")
  if (length(arguments) && identical(arguments[[1L]], "--database")) {
    if (length(arguments) < 3L) stop("--database requires a path before the command.")
    database <- arguments[[2L]]
    arguments <- arguments[-c(1L, 2L)]
  } else {
    database <- default_database
  }
  if (!length(arguments)) stop("Use add, review, list, or retrieve. See r/README.md.")
  command <- arguments[[1L]]
  arguments <- arguments[-1L]
  if (identical(command, "add")) {
    if (length(arguments) != 1L) stop("Usage: add memory.json")
    memory <- jsonlite::fromJSON(arguments[[1L]], simplifyVector = FALSE)
    id <- memory_add(database, memory)
    cat(jsonlite::toJSON(list(id = id, status = "pending"), auto_unbox = TRUE), "\n")
  } else if (identical(command, "review")) {
    if (length(arguments) < 2L) stop("Usage: review ID approve|reject|correct [options]")
    id <- arguments[[1L]]
    decision <- arguments[[2L]]
    options <- arguments[-c(1L, 2L)]
    option_value <- function(name, fallback = NULL) {
      position <- match(name, options)
      if (is.na(position) || position == length(options)) fallback else options[[position + 1L]]
    }
    replacement_path <- option_value("--replacement")
    replacement <- if (!is.null(replacement_path)) {
      jsonlite::fromJSON(replacement_path, simplifyVector = FALSE)
    } else {
      NULL
    }
    if (identical(decision, "correct") && is.null(replacement)) {
      stop("--replacement is required when decision is correct.")
    }
    replacement_id <- memory_review(
      database, id, decision,
      reviewer = option_value("--reviewer", "local-user"),
      note = option_value("--note", ""), replacement = replacement
    )
    status <- switch(decision, approve = "approved", reject = "rejected", correct = "corrected")
    result <- list(id = id, status = status)
    if (!is.null(replacement_id)) result$replacement_id <- replacement_id
    cat(jsonlite::toJSON(result, auto_unbox = TRUE), "\n")
  } else if (identical(command, "list")) {
    status <- if (length(arguments) >= 2L &&
                  identical(arguments[[1L]], "--status")) arguments[[2L]] else NULL
    cat(jsonlite::toJSON(memory_list(database, status), auto_unbox = TRUE, pretty = TRUE), "\n")
  } else if (identical(command, "retrieve")) {
    if (length(arguments) < 4L || !identical(arguments[[2L]], "--scope")) {
      stop('Usage: retrieve "query" --scope user|repository [--limit N]')
    }
    limit <- 10L
    if (length(arguments) >= 6L && identical(arguments[[5L]], "--limit")) {
      limit <- as.integer(arguments[[6L]])
    }
    cat(jsonlite::toJSON(
      memory_retrieve(database, arguments[[1L]], arguments[[3L]], limit),
      auto_unbox = TRUE, pretty = TRUE
    ), "\n")
  } else {
    stop("Unknown command: ", command)
  }
  invisible(0L)
}

if (sys.nframe() == 0L) {
  tryCatch(
    memory_cli(),
    error = function(error) {
      cat("MEMORY STORE FAILED: ", conditionMessage(error), "\n", file = stderr())
      quit(status = 1L)
    }
  )
}
