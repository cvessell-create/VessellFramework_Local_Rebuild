# Loop model in R: robust (MAD) outliers + binomial logistic regression on
# autopilot episodes. Mirrors vessell/loop_models.py for cross-checking.
# Usage: Rscript r/loop_model.R <episodes.csv> [out.json]

robust_z <- function(x) {
  mad_x <- stats::median(abs(x - stats::median(x)))
  if (mad_x == 0) return(rep(0, length(x)))
  0.6745 * (x - stats::median(x)) / mad_x
}

loop_model <- function(episodes, threshold = 3.5) {
  episodes$cleared <- as.integer(episodes$outcome == "complete")
  episodes$outlier <- as.integer(
    abs(robust_z(episodes$fitness)) > threshold | abs(robust_z(episodes$seconds)) > threshold
  )
  fit <- suppressWarnings(stats::glm(
    cleared ~ mission + kills + hp + stuck + outlier,
    data = episodes, family = stats::binomial()
  ))
  probs <- stats::fitted(fit)
  eps <- 1e-12
  list(
    n = nrow(episodes),
    outliers = sum(episodes$outlier),
    coefficients = as.list(stats::coef(fit)),
    converged = fit$converged,
    accuracy = mean((probs >= 0.5) == (episodes$cleared == 1)),
    log_loss = -mean(episodes$cleared * log(probs + eps) +
      (1 - episodes$cleared) * log(1 - probs + eps)),
    separation_warning = any(probs < 1e-8 | probs > 1 - 1e-8),
    note = "descriptive fit on post-episode features; not a predictive model"
  )
}

if (sys.nframe() == 0L) {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) < 1) stop("usage: Rscript r/loop_model.R <episodes.csv> [out.json]")
  result <- loop_model(utils::read.csv(args[[1]], stringsAsFactors = FALSE))
  text <- jsonlite::toJSON(result, auto_unbox = TRUE, pretty = TRUE, digits = 6)
  if (length(args) >= 2) writeLines(text, args[[2]]) else cat(text, "\n")
}
