required_packages <- c("DBI", "RSQLite", "jsonlite", "uuid")
missing_packages <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]

if (getRversion() < "4.1.0") {
  stop("Vessell's R memory environment requires R 4.1.0 or newer.")
}

if (length(missing_packages)) {
  install.packages(missing_packages, repos = "https://cloud.r-project.org")
}

unavailable_packages <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]
if (length(unavailable_packages)) {
  stop("Unable to install required R packages: ", paste(unavailable_packages, collapse = ", "))
}

cat("R memory-store environment is ready.\n")
cat("R version: ", as.character(getRversion()), "\n", sep = "")
for (package in required_packages) {
  cat(package, ": ", as.character(packageVersion(package)), "\n", sep = "")
}
