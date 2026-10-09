github_repository <- "cvessell-create/VessellFramework_Local_Rebuild"

metadata_require_json <- function() {
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    stop("Missing jsonlite; run Rscript r/setup.R.", call. = FALSE)
  }
}

metadata_utc <- function() {
  format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
}

metadata_time <- function(x) {
  as.POSIXct(x, format = "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
}

metadata_get <- function(endpoint) {
  metadata_require_json()
  if (!nzchar(Sys.which("gh"))) {
    stop("GitHub CLI is required; run gh auth login.", call. = FALSE)
  }
  response <- tempfile()
  errors <- tempfile()
  on.exit(unlink(c(response, errors)), add = TRUE)
  exit_code <- system2(
    "gh", c("api", "--hostname", "github.com", "--method", "GET", "--include",
            shQuote(endpoint)),
    stdout = response, stderr = errors
  )
  lines <- readLines(response, warn = FALSE)
  separator <- which(lines == "")
  if (!length(separator)) {
    stop("No HTTP headers in GitHub response: ",
         paste(readLines(errors, warn = FALSE), collapse = "\n"), call. = FALSE)
  }
  headers <- lines[seq_len(separator[[1]] - 1L)]
  code <- as.integer(strsplit(headers[[1]], " +")[[1]][[2]])
  if (exit_code != 0L || code != 200L) {
    return(list(code = code, error = paste(readLines(errors, warn = FALSE),
                                         collapse = "\n")))
  }
  body <- paste(lines[-seq_len(separator[[1]])], collapse = "\n")
  list(
    code = code,
    data = jsonlite::fromJSON(body, simplifyVector = FALSE),
    next_page = any(grepl('^link:.*rel="next"', headers, ignore.case = TRUE)),
    rate_remaining = sub("^[^:]+: *", "", headers[
      grepl("^x-ratelimit-remaining:", headers, ignore.case = TRUE)
    ])
  )
}

metadata_pick <- function(record, fields) {
  result <- setNames(vector("list", length(fields)), fields)
  for (field in fields) result[field] <- list(record[[field]])
  result
}

metadata_project <- function(name, records) {
  fields <- switch(
    name,
    repository = c("id", "full_name", "private", "default_branch", "created_at",
                   "pushed_at", "stargazers_count", "forks_count", "open_issues_count"),
    runs = c("id", "workflow_id", "name", "head_sha", "head_branch", "event",
             "status", "conclusion", "created_at", "updated_at", "run_started_at",
             "run_attempt", "html_url"),
    issues = c("id", "number", "state", "created_at", "closed_at", "updated_at",
               "comments", "html_url"),
    pulls = c("id", "number", "state", "created_at", "closed_at", "merged_at",
              "updated_at", "draft", "html_url"),
    branches = c("name", "protected"),
    contributors = c("login", "contributions", "type", "html_url"),
    releases = c("id", "tag_name", "created_at", "published_at", "draft",
                 "prerelease", "html_url"),
    NULL
  )
  if (name == "repository") return(metadata_pick(records, fields))
  if (name == "languages" || name %in% c("views", "clones")) return(records)
  lapply(records, function(record) {
    if (name == "commits") {
      return(list(sha = record$sha, html_url = record$html_url,
                  author_login = record$author$login,
                  committed_at = record$commit$committer$date))
    }
    result <- metadata_pick(record, fields)
    if (name == "issues") result$is_pull_request <- !is.null(record$pull_request)
    result
  })
}

collect_github_metadata <- function(repository = github_repository, max_pages = 20L,
                                    request = metadata_get) {
  if (length(repository) != 1L || is.na(repository) ||
      !grepl("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", repository) ||
      any(strsplit(repository, "/", fixed = TRUE)[[1]] %in% c(".", ".."))) {
    stop("Expected a GitHub owner/repository name.", call. = FALSE)
  }
  if (length(max_pages) != 1L || !is.finite(max_pages) ||
      max_pages < 1L || max_pages != as.integer(max_pages) || max_pages > 100L) {
    stop("max_pages must be an integer from 1 to 100.", call. = FALSE)
  }
  prefix <- paste0("repos/", repository)
  routes <- c(repository = "", languages = "/languages", commits = "/commits",
              issues = "/issues?state=all", pulls = "/pulls?state=all",
              runs = "/actions/runs", contributors = "/contributors",
              branches = "/branches", releases = "/releases",
              views = "/traffic/views", clones = "/traffic/clones")
  lists <- c("commits", "issues", "pulls", "runs", "contributors", "branches",
             "releases")
  snapshot <- list(schema_version = 1L, repository = repository,
                   started_at = metadata_utc(), endpoints = list())
  for (name in names(routes)) {
    endpoint <- paste0(prefix, routes[[name]])
    records <- list()
    pages <- list()
    next_page <- FALSE
    status <- "COMPLETE"
    error <- NULL
    for (page in seq_len(if (name %in% lists) max_pages else 1L)) {
      url <- endpoint
      if (name %in% lists) {
        url <- paste0(url, if (grepl("?", url, fixed = TRUE)) "&" else "?",
                      "per_page=100&page=", page)
      }
      result <- request(url)
      pages[[page]] <- list(endpoint = url, collected_at = metadata_utc(),
                            http_status = result$code,
                            rate_remaining = result$rate_remaining)
      if (result$code != 200L) {
        optional <- name %in% c("views", "clones") &&
          result$code %in% c(403L, 404L)
        if (!optional) {
          stop("GitHub collection failed: ", url, " (HTTP ", result$code,
               "): ", result$error, call. = FALSE)
        }
        status <- "UNAVAILABLE"
        error <- result$error
        warning(name, " unavailable (HTTP ", result$code, "): ", error,
                call. = FALSE)
        break
      }
      data <- result$data
      if (name == "runs") {
        if (!is.list(data$workflow_runs)) {
          stop("GitHub workflow_runs response is not a list.", call. = FALSE)
        }
        data <- data$workflow_runs
      }
      projected <- metadata_project(name, data)
      if (name %in% lists) records <- c(records, projected) else records <- projected
      next_page <- isTRUE(result$next_page)
      if (!(name %in% lists) || !next_page) break
    }
    if (next_page && status == "COMPLETE") status <- "TRUNCATED"
    snapshot$endpoints[[name]] <- list(status = status, error = error,
                                      pages = pages, data = records)
  }
  if (!identical(tolower(snapshot$endpoints$repository$data$full_name),
                 tolower(repository))) {
    stop("Canonical repository identity differs from requested scope.", call. = FALSE)
  }
  snapshot$completed_at <- metadata_utc()
  snapshot
}

metadata_table <- function(records, fields) {
  columns <- lapply(fields, function(field) {
    vapply(records, function(record) {
      value <- record[[field]]
      if (is.null(value)) NA_character_ else as.character(value)
    }, character(1))
  })
  names(columns) <- fields
  as.data.frame(columns, stringsAsFactors = FALSE)
}

metadata_write_json <- function(value, path) {
  metadata_require_json()
  jsonlite::write_json(value, path, pretty = TRUE, auto_unbox = TRUE,
                      na = "null", null = "null", digits = 16)
}

metadata_summary <- function(snapshot) {
  runs <- metadata_table(snapshot$endpoints$runs$data,
                         c("created_at", "conclusion"))
  dates <- as.Date(metadata_time(runs$created_at))
  weeks <- as.character(dates - (as.integer(format(dates, "%u")) - 1L))
  weekly <- lapply(sort(unique(weeks)), function(week) {
    selected <- !is.na(weeks) & weeks == week
    evaluated <- runs$conclusion[selected] %in% c("success", "failure", "timed_out")
    failed <- runs$conclusion[selected] %in% c("failure", "timed_out")
    list(week_start_utc = week, runs = sum(selected),
         evaluated = sum(evaluated), failures = sum(failed),
         failure_fraction = if (sum(evaluated)) sum(failed) / sum(evaluated) else NA_real_)
  })
  commits <- snapshot$endpoints$commits$data
  commit_dates <- as.Date(metadata_time(vapply(
    commits, function(x) x$committed_at, character(1)
  )))
  commit_weeks <- as.character(commit_dates - (as.integer(format(commit_dates, "%u")) - 1L))
  language_bytes <- unlist(snapshot$endpoints$languages$data)
  language_share <- if (length(language_bytes) && sum(language_bytes) > 0) {
    as.list(language_bytes / sum(language_bytes))
  } else list()
  issues <- Filter(function(x) !isTRUE(x$is_pull_request), snapshot$endpoints$issues$data)
  merged <- Filter(function(x) !is.null(x$merged_at), snapshot$endpoints$pulls$data)
  merge_hours <- vapply(merged, function(x) {
    as.numeric(difftime(metadata_time(x$merged_at), metadata_time(x$created_at),
                       units = "hours"))
  }, numeric(1))
  list(
    repository = snapshot$repository, observed_at = snapshot$completed_at,
    scope = "Default-branch commits; returned workflow runs; current metadata, not immutable event history.",
    language_byte_fraction = language_share,
    weekly_commits = as.list(table(commit_weeks)), weekly_ci = weekly,
    issues_excluding_pull_requests = length(issues),
    open_issues = sum(vapply(issues, function(x) identical(x$state, "open"), logical(1))),
    merged_pull_requests = length(merged),
    median_merge_hours = if (length(merge_hours)) median(merge_hours) else NA_real_,
    traffic = lapply(snapshot$endpoints[c("views", "clones")], function(x) {
      list(status = x$status, count = x$data$count, uniques = x$data$uniques)
    }),
    endpoint_status = lapply(snapshot$endpoints, function(x) x$status)
  )
}
