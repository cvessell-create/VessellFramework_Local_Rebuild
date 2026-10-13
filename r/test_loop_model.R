source("r/loop_model.R")

stopifnot(all(robust_z(c(1, 1, 1)) == 0))
z <- robust_z(c(10, 11, 9, 10, 12, 10, 100))
stopifnot(abs(z[7]) > 3.5, all(abs(z[-7]) < 3.5))

set.seed(7)
n <- 40
episodes <- data.frame(
  mission = rep(0:4, length.out = n),
  kills = sample(0:8, n, replace = TRUE),
  hp = sample(0:100, n, replace = TRUE),
  stuck = sample(0:3, n, replace = TRUE),
  seconds = c(stats::runif(n - 1, 60, 120), 2000),
  stringsAsFactors = FALSE
)
episodes$outcome <- ifelse(stats::runif(n) < 0.3 + 0.005 * episodes$hp, "complete", "timeout")
episodes$fitness <- episodes$kills * 50 + episodes$hp * 2 - episodes$seconds

result <- loop_model(episodes)
stopifnot(result$n == n, result$outliers >= 1)
stopifnot(result$accuracy >= 0, result$accuracy <= 1, is.finite(result$log_loss))
stopifnot("hp" %in% names(result$coefficients))
cat("loop_model R tests passed\n")
