source("r/github_metadata.R")
source("r/metadata_learning.R")
metadata_require_json()

expect_error <- function(expression, pattern) {
  error <- tryCatch({ force(expression); NULL }, error = identity)
  stopifnot(inherits(error, "error"), grepl(pattern, conditionMessage(error)))
}

requested <- character()
mock <- function(endpoint) {
  requested <<- c(requested, endpoint)
  if (grepl("/traffic/", endpoint, fixed = TRUE)) {
    return(list(code = 403L, error = "Traffic permission unavailable"))
  }
  if (grepl("/actions/runs", endpoint, fixed = TRUE)) {
    page <- if (grepl("page=2$", endpoint)) 2L else 1L
    return(list(code = 200L, next_page = page == 1L, data = list(
      workflow_runs = list(list(id = page, workflow_id = 3, name = "test",
                                head_sha = paste0("sha", page), run_attempt = 1,
                                created_at = "2026-01-01T00:00:00Z",
                                updated_at = "2026-01-01T00:01:00Z")),
      total_count = 2
    )))
  }
  if (grepl("/languages$", endpoint)) {
    return(list(code = 200L, data = list(R = 25, Python = 75)))
  }
  if (!grepl("\\?", endpoint) && endsWith(endpoint, github_repository)) {
    return(list(code = 200L, data = list(full_name = github_repository,
                                        default_branch = "master", secret = "omit")))
  }
  list(code = 200L, data = list())
}
warnings <- character()
snapshot <- withCallingHandlers(
  collect_github_metadata(max_pages = 2L, request = mock),
  warning = function(w) {
    warnings <<- c(warnings, conditionMessage(w))
    invokeRestart("muffleWarning")
  }
)
stopifnot(length(warnings) == 2L, snapshot$endpoints$views$status == "UNAVAILABLE",
          snapshot$endpoints$runs$status == "COMPLETE",
          length(snapshot$endpoints$runs$data) == 2L,
          length(snapshot$endpoints$runs$pages) == 2L,
          is.null(snapshot$endpoints$repository$data$secret),
          all(grepl("^repos/", requested)))
truncated <- withCallingHandlers(
  collect_github_metadata(max_pages = 1L, request = mock),
  warning = function(w) invokeRestart("muffleWarning")
)
stopifnot(truncated$endpoints$runs$status == "TRUNCATED",
          learn_metadata(truncated)$status == "INCOMPLETE_COLLECTION")
expect_error(collect_github_metadata(repository = "../repo"), "owner/repository")
expect_error(collect_github_metadata(max_pages = 0L), "max_pages")
expect_error(collect_github_metadata(request = function(url) {
  list(code = 429L, error = "Rate limit")
}), "HTTP 429")
expect_error(collect_github_metadata(request = function(url) {
  list(code = 200L, data = list())
}), "workflow_runs")

private <- list(id = 1, number = 2, body = "private", title = "private",
                user = list(email = "private"), pull_request = list(url = "x"))
projected <- metadata_project("issues", list(private))[[1]]
stopifnot(isTRUE(projected$is_pull_request), is.null(projected$body),
          is.null(projected$title), is.null(projected$user))

set.seed(1)
x <- matrix(rnorm(40), nrow = 10)
y <- rep(c(0, 1), 5)
weights <- network_initialize(c(4, 3, 2, 1))
shapes <- lapply(weights, dim)
parameters <- unlist(weights)
objective <- network_objective(parameters, shapes, x, y)
epsilon <- 1e-6
numerical <- vapply(seq_along(parameters), function(i) {
  upper <- lower <- parameters
  upper[[i]] <- upper[[i]] + epsilon
  lower[[i]] <- lower[[i]] - epsilon
  (network_objective(upper, shapes, x, y)$loss -
     network_objective(lower, shapes, x, y)$loss) / (2 * epsilon)
}, numeric(1))
stopifnot(max(abs(numerical - objective$gradient)) < 1e-6)
stopifnot(abs(probability_metrics(c(0, 1, 1, 0), c(0.1, 0.9, 0.8, 0.3))$brier -
                0.0375) < 1e-12)

make_runs <- function(n) {
  lapply(seq_len(n), function(i) {
    start <- as.POSIXct("2026-01-01", tz = "UTC") + i * 3600
    list(id = i, workflow_id = 7, name = "synthetic", head_sha = paste0("sha", i),
         head_branch = "master", event = if (i %% 2) "push" else "pull_request",
         status = "completed", conclusion = if (i %% 2) "success" else "failure",
         created_at = format(start, "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
         updated_at = format(start + 60, "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
         run_attempt = 1, html_url = paste0("https://github.com/example/runs/", i))
  })
}
snapshot$endpoints$runs$data <- make_runs(400L)
split <- metadata_split(metadata_run_table(snapshot))
stopifnot(split$status == "READY",
          max(split$partitions$train$observed) < min(split$partitions$validation$created),
          max(split$partitions$validation$observed) < min(split$partitions$test$created))
learning <- learn_metadata(snapshot)
stopifnot(length(learning$model$network$architecture) == 4L,
          learning$status == "EXPERIMENTAL_BASELINE_WIN",
          learning$scores$test$neural$brier < 0.05,
          all(is.finite(learning$predictions$experimental_failure_probability)),
          length(intersect(learning$partition_ids$train, learning$partition_ids$test)) == 0L)
repeat_learning <- learn_metadata(snapshot)
stopifnot(identical(learning$scores, repeat_learning$scores))

leaky <- metadata_run_table(snapshot)
leaky$head_sha[[1]] <- leaky$head_sha[[400]]
leaky$observed[[2]] <- leaky$created[[300]]
purged <- metadata_split(leaky)
stopifnot(!leaky$id[[1]] %in% purged$partitions$train$id,
          !leaky$id[[2]] %in% purged$partitions$train$id)
features <- metadata_features(leaky[1:3, ], "7", "master")
changed <- leaky[1:3, ]
changed$conclusion <- "failure"
changed$observed <- changed$observed + 1000
stopifnot(identical(features, metadata_features(changed, "7", "master")))
unknown <- leaky[1:3, ]
unknown$workflow_id <- "new"
stopifnot(all(metadata_features(unknown, "7", "master")[, "unknown_workflow"] == 1))

snapshot$endpoints$runs$data <- make_runs(199L)
stopifnot(learn_metadata(snapshot)$status == "INSUFFICIENT_DATA")
snapshot$endpoints$runs$data <- make_runs(400L)
for (i in seq_along(snapshot$endpoints$runs$data)) {
  snapshot$endpoints$runs$data[[i]]$conclusion <- "success"
}
stopifnot(learn_metadata(snapshot)$status == "INSUFFICIENT_DATA")
snapshot$endpoints$runs$data <- list()
stopifnot(learn_metadata(snapshot)$status == "INSUFFICIENT_DATA",
          length(metadata_suggestions(snapshot, list(status = "INSUFFICIENT_DATA"))) == 1L)
snapshot$endpoints$runs$data <- make_runs(400L)
snapshot$endpoints$runs$data[[1]]$conclusion <- "action_required"
suggestions <- metadata_suggestions(snapshot, learning)
stopifnot(any(vapply(suggestions, function(x) x$kind == "REVIEW_ACTION_REQUIRED",
                     logical(1))))
summary <- metadata_summary(snapshot)
stopifnot(summary$language_byte_fraction$R == 0.25,
          summary$issues_excluding_pull_requests == 0L,
          summary$traffic$views$status == "UNAVAILABLE")

directory <- tempfile()
dir.create(directory)
path <- file.path(directory, "summary.json")
metadata_write_json(list(probability = 1 / 3, missing = NA_real_), path)
restored <- jsonlite::fromJSON(path)
stopifnot(abs(restored$probability - 1 / 3) < 1e-14, is.null(restored$missing))
unlink(path)
unlink(directory)
cat("GitHub observatory checks passed: collection, privacy, gradients, chronology, gates, persistence.\n")
