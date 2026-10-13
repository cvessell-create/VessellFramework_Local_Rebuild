source("r/system_readout.R")

setup_r_environment <- function() {
  readout_status <- "failed"
  r_system_readout_update("setup", "invoked")
  on.exit(r_system_readout_update("setup", readout_status), add = TRUE)

  required_packages <- c(
    "DBI", "RSQLite", "jsonlite", "uuid",
    "readxl", "effsize", "knitr", "rmarkdown"
  )
  if (getRversion() < "4.1.0") {
    stop("Vessell's R environment requires R 4.1.0 or newer.")
  }

  installed <- utils::installed.packages()[, "Version"]
  missing_packages <- setdiff(required_packages, names(installed))
  if (length(missing_packages)) {
    utils::install.packages(missing_packages, repos = "https://cloud.r-project.org")
    installed <- utils::installed.packages()[, "Version"]
  }
  unavailable_packages <- setdiff(required_packages, names(installed))
  if (length(unavailable_packages)) {
    stop(
      "Unable to install R packages: ",
      paste(unavailable_packages, collapse = ", ")
    )
  }

  cat("R memory-store and statistics environment is ready.\n")
  cat("R version: ", as.character(getRversion()), "\n", sep = "")
  for (package in required_packages) {
    cat(package, ": ", installed[[package]], "\n", sep = "")
  }
  readout_status <- "completed"
  invisible(NULL)
}

setup_r_environment()
