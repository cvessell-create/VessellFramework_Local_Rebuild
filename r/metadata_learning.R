network_initialize <- function(widths, seed = 42L) {
  set.seed(seed)
  lapply(seq_len(length(widths) - 1L), function(i) {
    matrix(rnorm((widths[[i]] + 1L) * widths[[i + 1L]],
                 sd = sqrt(1 / widths[[i]])),
           nrow = widths[[i]] + 1L, ncol = widths[[i + 1L]])
  })
}

network_unpack <- function(parameters, shapes) {
  offset <- 0L
  lapply(shapes, function(shape) {
    count <- prod(shape)
    result <- matrix(parameters[offset + seq_len(count)], nrow = shape[[1]])
    offset <<- offset + count
    result
  })
}

network_forward <- function(weights, x) {
  activations <- list(x)
  for (i in seq_along(weights)) {
    z <- cbind(1, activations[[i]]) %*% weights[[i]]
    activations[[i + 1L]] <- if (i == length(weights)) plogis(z) else tanh(z)
  }
  activations
}

network_objective <- function(parameters, shapes, x, y, lambda = 0.01) {
  weights <- network_unpack(parameters, shapes)
  activations <- network_forward(weights, x)
  p <- activations[[length(activations)]]
  z <- cbind(1, activations[[length(weights)]]) %*% weights[[length(weights)]]
  loss <- mean(pmax(z, 0) - y * z + log1p(exp(-abs(z))))
  penalty <- sum(vapply(weights, function(w) sum(w[-1, , drop = FALSE]^2),
                        numeric(1)))
  gradient <- vector("list", length(weights))
  delta <- (p - y) / nrow(x)
  for (i in rev(seq_along(weights))) {
    regularization <- weights[[i]]
    regularization[1, ] <- 0
    gradient[[i]] <- crossprod(cbind(1, activations[[i]]), delta) +
      2 * lambda * regularization
    if (i > 1L) {
      delta <- (delta %*% t(weights[[i]][-1, , drop = FALSE])) *
        (1 - activations[[i]]^2)
    }
  }
  list(loss = loss + lambda * penalty, gradient = unlist(gradient))
}

network_fit <- function(x, y, hidden = c(8L, 4L), lambda = 0.01) {
  weights <- network_initialize(c(ncol(x), hidden, 1L))
  shapes <- lapply(weights, dim)
  objective <- function(parameters) {
    network_objective(parameters, shapes, x, y, lambda)
  }
  fit <- optim(unlist(weights), function(p) objective(p)$loss,
               function(p) objective(p)$gradient, method = "BFGS",
               control = list(maxit = 500L, reltol = 1e-8))
  if (fit$convergence != 0L || !is.finite(fit$value)) {
    stop("Neural optimizer did not converge; no learning preview produced.",
         call. = FALSE)
  }
  list(weights = network_unpack(fit$par, shapes), objective = fit$value,
       architecture = c(ncol(x), hidden, 1L), lambda = lambda, seed = 42L)
}

network_predict <- function(model, x) {
  activations <- network_forward(model$weights, x)
  as.numeric(activations[[length(activations)]])
}

probability_metrics <- function(y, p) {
  p <- pmin(pmax(p, 1e-12), 1 - 1e-12)
  list(brier = mean((p - y)^2),
       log_loss = -mean(y * log(p) + (1 - y) * log1p(-p)))
}

metadata_run_table <- function(snapshot) {
  runs <- metadata_table(
    snapshot$endpoints$runs$data,
    c("id", "workflow_id", "name", "head_sha", "head_branch", "event",
      "status", "conclusion", "created_at", "updated_at", "run_attempt", "html_url")
  )
  if (anyDuplicated(runs$id)) stop("Duplicate workflow run IDs.", call. = FALSE)
  runs$created <- metadata_time(runs$created_at)
  runs$observed <- metadata_time(runs$updated_at)
  runs
}

metadata_split <- function(runs) {
  usable <- runs$status == "completed" &
    runs$conclusion %in% c("success", "failure", "timed_out") &
    runs$run_attempt == "1"
  usable[is.na(usable)] <- FALSE
  data <- runs[usable, , drop = FALSE]
  if (anyNA(data$created) || anyNA(data$observed) ||
      anyNA(data$head_sha) || any(!nzchar(data$head_sha)) ||
      any(data$observed < data$created)) {
    stop("Invalid modeling timestamps or missing commit SHA.", call. = FALSE)
  }
  data <- data[order(data$created, data$id), , drop = FALSE]
  if (nrow(data) < 200L) return(list(status = "INSUFFICIENT_DATA", n = nrow(data)))
  validation_start <- data$created[[floor(nrow(data) * 0.6) + 1L]]
  test_start <- data$created[[floor(nrow(data) * 0.8) + 1L]]
  train <- data[data$created < validation_start & data$observed < validation_start, ]
  validation <- data[data$created >= validation_start & data$created < test_start &
                       data$observed < test_start, ]
  test <- data[data$created >= test_start, ]
  validation <- validation[!validation$head_sha %in% test$head_sha, ]
  train <- train[!train$head_sha %in% c(validation$head_sha, test$head_sha), ]
  partitions <- list(train = train, validation = validation, test = test)
  counts <- lapply(partitions, function(part) {
    list(success = sum(part$conclusion == "success"),
         failure = sum(part$conclusion != "success"))
  })
  adequate <- nrow(train) >= 100L && all(unlist(counts$train) >= 20L) &&
    nrow(validation) >= 30L && all(unlist(counts$validation) >= 5L) &&
    nrow(test) >= 30L && all(unlist(counts$test) >= 5L)
  list(status = if (adequate) "READY" else "INSUFFICIENT_DATA",
       n = nrow(data), counts = counts, partitions = partitions,
       validation_start = format(validation_start, "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
       test_start = format(test_start, "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"))
}

metadata_features <- function(runs, workflows, default_branch) {
  time <- as.POSIXlt(runs$created, tz = "UTC")
  features <- cbind(
    pull_request = as.numeric(runs$event == "pull_request"),
    push = as.numeric(runs$event == "push"),
    default_branch = as.numeric(!is.na(runs$head_branch) &
                                  runs$head_branch == default_branch),
    hour_sin = sin(2 * pi * time$hour / 24),
    hour_cos = cos(2 * pi * time$hour / 24),
    weekend = as.numeric(time$wday %in% c(0L, 6L))
  )
  for (workflow in workflows) {
    features <- cbind(features, as.numeric(runs$workflow_id == workflow))
    colnames(features)[ncol(features)] <- paste0("workflow_", workflow)
  }
  features <- cbind(features, unknown_workflow =
                      as.numeric(!runs$workflow_id %in% workflows))
  if (any(!is.finite(features))) stop("Non-finite modeling features.", call. = FALSE)
  features
}

learn_metadata <- function(snapshot) {
  if (snapshot$endpoints$runs$status != "COMPLETE") {
    return(list(status = "INCOMPLETE_COLLECTION", model = NULL))
  }
  runs <- metadata_run_table(snapshot)
  split <- metadata_split(runs)
  if (split$status != "READY") return(c(split, list(model = NULL)))
  partitions <- split$partitions
  workflows <- sort(unique(partitions$train$workflow_id))
  default_branch <- snapshot$endpoints$repository$data$default_branch
  x <- lapply(partitions, metadata_features, workflows = workflows,
              default_branch = default_branch)
  y <- lapply(partitions, function(part) as.numeric(part$conclusion != "success"))
  network <- network_fit(x$train, y$train)
  logistic <- network_fit(x$train, y$train, hidden = integer())
  baseline <- mean(y$train)
  scores <- lapply(c("validation", "test"), function(part) {
    list(
      neural = probability_metrics(y[[part]], network_predict(network, x[[part]])),
      logistic = probability_metrics(y[[part]], network_predict(logistic, x[[part]])),
      historical_rate = probability_metrics(y[[part]], rep(baseline, length(y[[part]])))
    )
  })
  names(scores) <- c("validation", "test")
  beats_baselines <- all(vapply(scores, function(score) {
    score$neural$brier < min(score$logistic$brier, score$historical_rate$brier) &&
      score$neural$log_loss < min(score$logistic$log_loss, score$historical_rate$log_loss)
  }, logical(1)))
  ids <- lapply(partitions, function(part) part$id)
  predictions <- data.frame(
    run_id = partitions$test$id, html_url = partitions$test$html_url,
    actual_failure = y$test, experimental_failure_probability =
      network_predict(network, x$test)
  )
  list(status = if (beats_baselines) "EXPERIMENTAL_BASELINE_WIN" else "BASELINE_NOT_BEATEN",
       n = split$n, counts = split$counts, partition_ids = ids,
       validation_start = split$validation_start, test_start = split$test_start,
       scores = scores, predictions = predictions,
       model = list(network = network, logistic = logistic, workflows = workflows,
                    default_branch = default_branch, historical_rate = baseline,
                    feature_names = colnames(x$train)))
}

metadata_suggestions <- function(snapshot, learning) {
  runs <- metadata_run_table(snapshot)
  suggestions <- list()
  for (workflow in unique(runs$workflow_id)) {
    part <- runs[runs$workflow_id == workflow, , drop = FALSE]
    evaluated <- part$conclusion %in% c("success", "failure", "timed_out")
    failed <- part$conclusion %in% c("failure", "timed_out")
    if (sum(evaluated) >= 5L && sum(failed) / sum(evaluated) >= 0.2) {
      suggestions[[length(suggestions) + 1L]] <- list(
        kind = "REVIEW_CI_FAILURES", workflow_id = workflow,
        evaluated_runs = sum(evaluated), failed_runs = sum(failed),
        failure_fraction = sum(failed) / sum(evaluated),
        suggestion = "Inspect failed-run logs and compare recurring failures before proposing a code change.",
        evidence_urls = head(part$html_url[failed], 5L)
      )
    }
  }
  blocked <- runs$conclusion %in% c("action_required")
  if (any(blocked)) {
    suggestions[[length(suggestions) + 1L]] <- list(
      kind = "REVIEW_ACTION_REQUIRED", count = sum(blocked),
      suggestion = "Review runs requiring action; retain approval and permission safeguards.",
      evidence_urls = head(runs$html_url[blocked], 5L)
    )
  }
  suggestions[[length(suggestions) + 1L]] <- list(
    kind = "REVIEW_MODEL_EVIDENCE", learning_status = learning$status,
    suggestion = paste(
      "Inspect chronological validation and test metrics.",
      "Insufficient data or failure to beat baselines means do not rely on the neural model.",
      "Even a baseline win is experimental, not calibration or causal evidence."
    )
  )
  suggestions
}
