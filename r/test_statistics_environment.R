required_packages <- c("readxl", "effsize", "knitr", "rmarkdown")
missing <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]
if (length(missing)) {
  stop("Run Rscript r/setup.R; missing packages: ", paste(missing, collapse = ", "))
}

before <- 50 + 10 * qnorm(ppoints(100))
change <- 5 + 2 * qnorm(ppoints(100))
after <- before + change
stopifnot(shapiro.test(change)$p.value > 0.05)
paired <- t.test(after, before, paired = TRUE)
stopifnot(paired$p.value < 0.001, unname(paired$estimate) > 0)

group1 <- 60 + 10 * qnorm(ppoints(100))
group2 <- 70 + 10 * qnorm(ppoints(100))
independent <- t.test(group1, group2, var.equal = TRUE)
stopifnot(independent$p.value < 0.001)
stopifnot(is.finite(effsize::cohen.d(group1, group2)$estimate))

counts <- matrix(c(40, 10, 10, 40), nrow = 2)
categorical <- chisq.test(counts, correct = TRUE)
stopifnot(all(categorical$expected >= 5), categorical$p.value < 0.001)

satisfaction <- after / 12 + 0.2 * sin(seq_along(after))
correlation <- cor.test(after, satisfaction, method = "pearson")
stopifnot(correlation$estimate > 0, correlation$p.value < 0.001)

skewed <- rep(c(0, 1, 2, 20), c(60, 20, 10, 10))
stopifnot(shapiro.test(skewed)$p.value < 0.05)
stopifnot(is.finite(wilcox.test(skewed + 1, skewed, paired = TRUE,
                             exact = FALSE)$p.value))
stopifnot(is.finite(wilcox.test(skewed, skewed + 1, exact = FALSE)$p.value))
stopifnot(is.finite(cor.test(skewed, skewed + 1, method = "spearman",
                          exact = FALSE)$p.value))

cat("R statistics smoke checks passed (synthetic data only).\n")
