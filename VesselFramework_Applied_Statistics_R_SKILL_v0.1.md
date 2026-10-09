# Applied Statistics in R — Analysis and Reporting Skill

## Purpose and scope

This skill organizes the supplied course procedures for five common questions:

1. Are two quantitative variables associated? **Pearson or Spearman correlation**
2. Do the same participants' scores differ before and after? **Paired t-test or Wilcoxon signed-rank test**
3. Do two independent groups differ on an outcome? **Independent t-test or Mann–Whitney (Wilcoxon rank-sum) test**
4. Does one categorical variable follow a specified distribution? **Chi-Square Goodness-of-Fit**
5. Are two categorical variables associated? **Chi-Square Test of Independence**

For the AA 5221 four-test final project, see the
[workflow overview](docs/final-project-workflow-overview.md) for the
research-question-to-dataset mapping, script order, report structure, and private
submission checklist.

It is an instructional workflow, not a statistical software feature or evidence
that an analysis is valid. Follow the instructor's assignment rubric where it
specifies a decision rule. Course rules below are labeled as such; they are not
universal substitutes for checking the design, assumptions, and research
question. An observational association or group difference does not by itself
establish causation.

## Shared project workflow

### 1. Define the question and data structure

Before opening RStudio, record:

- the research question and null/alternative hypotheses;
- the unit of observation and whether measurements are paired or independent;
- the outcome and grouping/predictor variables, their units, and the dataset source;
- inclusion/exclusion rules, missing-data handling, and the assignment's reporting requirements.

For an assignment, then follow this sequence: identify the design and variable
types; choose the matching procedure below; import and verify the assigned data;
calculate descriptive summaries and required diagnostics; run the selected
inferential test once; calculate its matching effect size; write the result in
the assigned format; knit and inspect the HTML; and submit the requested file or
link. Keep the script, report, and source data together without publishing
identifiable or restricted information.

Install required packages once, then load the packages needed by the selected
procedure at the start of each R session:

```r
install.packages(c(
  "readxl", "ggpubr", "dplyr", "effectsize", "effsize", "rstatix"
))
```

Do not rerun package installation in every analysis. For a reproducible report,
record the packages used and their versions when required by the course.

Choose the test from the design, not from which result appears more favorable:

| Design and question | Candidate procedure |
|---|---|
| Two quantitative variables measured on the same observational units | Pearson or Spearman correlation |
| Same participants measured twice (or otherwise matched pairs) | Paired t-test or Wilcoxon signed-rank |
| Two unrelated groups and one quantitative outcome | Independent t-test or Mann–Whitney / Wilcoxon rank-sum |
| One categorical variable compared with specified expected proportions | Chi-Square Goodness-of-Fit |
| Association between two categorical variables | Chi-Square Test of Independence |

Do not treat repeated observations from the same person as independent groups.
Do not describe either variable in a correlation as a causal independent or
dependent variable.

### 2. Prepare and inspect the data

Use the course's approved point-and-click import procedure or an explicit,
reproducible import line. Retain the original file unchanged and work from a
clearly named analysis copy.

1. Confirm the expected columns, units, group labels, and number of observations.
2. Identify missing, duplicated, impossible, or miscoded values. Check suspected
   outliers against the source; do not remove legitimate observations solely
   because they are unusual.
3. For paired data, retain only complete Before/After pairs for analyses that
   require both scores. Never remove missing values from each vector separately,
   because that can break participant pairing.
4. For two-group analyses, verify there are exactly two intended groups and that
   observations are independent between groups.
5. Record any exclusions and the resulting analysis sample size.

### 3. Describe, visualize, and check assumptions

Calculate descriptive statistics appropriate to the question. Plot the raw data
before selecting or reporting a test:

- Correlation: scatterplot; assess linearity for Pearson or monotonicity for
  Spearman, direction, and influential/outlying observations.
- Paired comparison: inspect paired scores and the **After − Before difference
  scores**; assess the difference-score distribution and potential outliers.
- Independent groups: inspect distributions and boxplots separately by group;
  assess group independence and potential outliers.
- Categorical counts: inspect frequency/contingency tables and expected counts;
  normality checks do not apply to categorical count data.

Use Shapiro–Wilk only as one normality diagnostic. A p-value above .05 does not
prove normality, and a p-value below .05 does not automatically identify a data
error. Interpret it alongside plots, sample size, and the design. If the test
cannot be computed for the available observations, document that rather than
inventing a result.

### 4. Select one test and report its matching effect size

Apply the relevant course decision rule in the sections below. Do not run both
tests and choose whichever gives the preferred p-value. Report the statistic,
degrees of freedom where applicable, p-value, effect-size estimate, sample size,
and descriptive statistics requested by the assignment. State the direction
using the same subtraction/group order used in the analysis.

Statistical significance is not effect size, practical importance, or causation.
Avoid describing p > .05 as proof of no difference/relationship.
For the supplied course reporting rule, report p-values below .001 as `p < .001`,
`.001 ≤ p < .05` to three decimals, and values above .05 as `p > .05`; follow
the instructor's instructions for exactly .05 and other rounding boundaries.

### 5. Reproduce and share the report

1. Keep the final R script with the dataset name, variable names, decisions, and
   interpretation comments filled in.
2. Copy the relevant script into an R Markdown document and place code in
   executable R chunks. Add written interpretation near the corresponding output.
3. Knit to HTML and inspect the rendered code, results, tables, and plots.
4. Save the HTML and source files according to course instructions.
5. Publish to RPubs only when required and authorized. Check that the public
   report does not expose participant identifiers, private data, or file paths.
   Open the published link and verify what a viewer can access.

## Procedure A: Pearson or Spearman correlation

### Question and assumptions

Correlation describes the direction and strength of association between two
quantitative variables. It does not establish cause and effect. There is no
required causal IV/DV distinction.

**Course selection rule:** use Pearson when the scatterplot is approximately
linear and both variables meet the course's normality rule. If either variable
does not meet that rule, use Spearman. Independently of this rule, Pearson
targets linear association and Spearman targets monotonic rank association;
Spearman is not a general remedy for every unusual distribution or a
non-monotonic relationship. Check independence of observations and influential
points for either analysis.

### R workflow

Replace the dataset and column names with the actual names. Check missingness
and pair alignment before computing statistics. The paired complete-case data
below ensures both variables refer to the same observations.

```r
library(readxl)
library(ggpubr)

DatasetName <- read_excel("path/to/data.xlsx")
correlation_data <- DatasetName[
  complete.cases(DatasetName[c("Variable1", "Variable2")]),
  c("Variable1", "Variable2")
]

ggscatter(
  correlation_data,
  x = "Variable1",
  y = "Variable2",
  add = "reg.line",
  xlab = "Variable 1",
  ylab = "Variable 2"
)

summary(correlation_data$Variable1)
sd(correlation_data$Variable1)
summary(correlation_data$Variable2)
sd(correlation_data$Variable2)

hist(correlation_data$Variable1)
hist(correlation_data$Variable2)
shapiro.test(correlation_data$Variable1)
shapiro.test(correlation_data$Variable2)

# Select one method based on the research question, plot, assumptions, and course rule.
cor.test(
  correlation_data$Variable1,
  correlation_data$Variable2,
  method = "pearson"
)
# Or use method = "spearman".
```

For `cor.test`, use the reported correlation coefficient (`r` for Pearson,
`rho` for Spearman) and p-value. Pearson's test reports degrees of freedom;
Spearman's usual R output does not report them. Report the actual coefficient
sign and magnitude. The supplied course bands are: absolute coefficient
0.00–0.19 very weak, 0.20–0.39 weak, 0.40–0.59 moderate, 0.60–0.79 strong,
and 0.80–1.00 very strong. Treat these as course conventions, not universal
boundaries.

### Reporting checklist

- Name Pearson or Spearman and the two variables.
- Include requested descriptive statistics and the exact coefficient, test
  statistic/degrees of freedom when provided, and p-value.
- State direction and strength using the course's rubric.
- Describe association, not causation. Avoid “as X increased, Y increased”
  unless the observational nature and noncausal meaning are clear.

Use the assignment's required p-value format. The supplied course rule is
`p < .001` for values below .001, the exact p-value to three decimals for
`.001 ≤ p < .05`, and `p > .05` for nonsignificant results. If the p-value is
exactly .05 or a rounding boundary makes the category unclear, report the
unrounded value according to instructor guidance rather than changing its
meaning through rounding.

```r
# Pearson:
# A Pearson correlation tested the relationship between Variable1
# (M = xx.xx, SD = xx.xx) and Variable2 (M = xx.xx, SD = xx.xx).
# The relationship was / was not statistically significant,
# r(df) = .xx, p = .xxx.
# The relationship was positive / negative and very weak / weak / moderate / strong / very strong.

# Spearman:
# A Spearman correlation tested the relationship between Variable1 (Mdn = xx.xx)
# and Variable2 (Mdn = xx.xx).
# The relationship was / was not statistically significant, rho = .xx, p = .xxx.
# The relationship was positive / negative and very weak / weak / moderate / strong / very strong.
```

## Procedure B: paired t-test or Wilcoxon signed-rank test

### Question and assumptions

Use this design when each Before score is paired with the same participant's
After score (or with a prespecified matched case). Define the difference as
**After − Before**. The paired t-test's normality assumption concerns these
difference scores, not Before and After separately.

**Course selection rule:** if the difference scores are treated as normally
distributed under the course's Shapiro–Wilk decision rule, use a paired t-test;
otherwise use the Wilcoxon signed-rank test. Also inspect the difference-score
plot and outliers. The signed-rank test is a rank-based paired procedure; a
location-shift interpretation generally also relies on a reasonably symmetric
difference distribution. State the selected method and limitations.

### R workflow

```r
library(readxl)
library(ggpubr)
library(effsize)
library(rstatix)

DatasetName <- read_excel("path/to/data.xlsx")

# Keep complete pairs so each Before remains matched to its After score.
paired <- DatasetName[
  complete.cases(DatasetName[c("ScoresBefore", "ScoresAfter")]),
  c("ScoresBefore", "ScoresAfter")
]
Before <- paired$ScoresBefore
After <- paired$ScoresAfter
Differences <- After - Before

mean(Before)
median(Before)
sd(Before)
mean(After)
median(After)
sd(After)
nrow(paired)

hist(Differences, breaks = 15, col = "blue", border = "white")
boxplot(
  Differences,
  main = "Distribution of Score Differences (After - Before)",
  ylab = "Difference in Scores",
  col = "blue",
  border = "darkblue"
)
shapiro.test(Differences)

# Choose one procedure. This order makes the reported contrast After - Before.
t.test(After, Before, paired = TRUE)
cohen.d(After, Before, paired = TRUE)

wilcox.test(After, Before, paired = TRUE)

# Optional r effect size for the paired Wilcoxon test.
paired_long <- data.frame(
  id = rep(seq_along(Before), 2),
  time = factor(
    rep(c("Before", "After"), each = length(Before)),
    levels = c("Before", "After")
  ),
  score = c(Before, After)
)
wilcox_effsize(paired_long, score ~ time, paired = TRUE)
```

Report the t-test's `t`, degrees of freedom, p-value, and Cohen's d. The
`After, Before` argument order makes positive differences mean After scores are
higher; preserve this convention when interpreting effect direction.

For Wilcoxon, report R's statistic as printed (`V`), not as a renamed statistic,
and report its p-value. Report the signed-rank effect size `r` only as required
by the assignment. If there are many tied or zero differences, note that these
can affect the test's calculation and interpretation.

### Reporting checklist

- State that the observations are paired and define the direction as
  After − Before.
- Report the Before/After means and SDs for a t-test, or medians for the
  signed-rank report, as requested.
- Use the test's displayed statistic and p-value; do not reverse the wording
  relative to the chosen subtraction order.
- Report outlier/normality observations separately from the inferential result.

```r
# Paired t-test:
# A paired t-test assessed the difference in OutcomeVariable between Before and After.
# Before scores (M = xx.xx, SD = xx.xx) were significantly / not significantly
# different from After scores (M = xx.xx, SD = xx.xx), t(df) = x.xx, p = .xxx.
# Cohen's d = x.xx.

# Wilcoxon signed-rank:
# A Wilcoxon signed-rank test assessed the difference in OutcomeVariable between Before and After.
# Before scores (Mdn = xx.xx) were significantly / not significantly different
# from After scores (Mdn = xx.xx), V = xx, p = .xxx.
# If required and statistically significant: the effect size was small / medium / large, r = .xx.
```

The supplied paired-test example labels Cohen's d = .65 “large,” while its
listed reference values place .50 near medium and .80 near large. These labels
are inconsistent; report the effect estimate and confirm the verbal category
against the instructor's rubric rather than silently choosing a cutoff.

The supplied Wilcoxon course bands are approximately `r = .10` small, `.30`
medium, and `.50` large. These are conventions for the assignment, not universal
boundaries.

## Procedure C: independent t-test or Mann–Whitney test

### Question and assumptions

Use this design to compare one quantitative outcome between two unrelated
groups. Each observation belongs to one group only. Do not use this procedure
for repeated or matched measurements.

**Course selection rule:** inspect the outcome within each group and run a
Shapiro–Wilk test in each. If both p-values are greater than .05, the course
selects an independent t-test; if either is below .05, it selects
Mann–Whitney/Wilcoxon rank-sum. A Shapiro–Wilk result does not prove or disprove
normality. The supplied course example uses `var.equal = TRUE`; use that only
when required by the assignment and justified by its assumptions. Otherwise,
the default Welch t-test in R does not assume equal variances.

Mann–Whitney compares ranks/distributions; it is not automatically a test of
medians unless the group distributions have suitably similar shapes. R prints
the Wilcoxon rank-sum statistic as `W`; preserve `W` in reporting rather than
relabeling the printed value as `U`.

### R workflow

```r
library(readxl)
library(dplyr)
library(ggpubr)
library(effectsize)
library(effsize)

DatasetName <- read_excel("path/to/data.xlsx")
independent <- DatasetName[
  complete.cases(DatasetName[c("GroupVariable", "OutcomeVariable")]),
  c("GroupVariable", "OutcomeVariable")
]
independent$GroupVariable <- factor(
  independent$GroupVariable,
  levels = c("Group1", "Group2")
)
stopifnot(!anyNA(independent$GroupVariable))
stopifnot(length(unique(independent$GroupVariable)) == 2)

independent %>%
  group_by(GroupVariable) %>%
  summarise(
    Mean = mean(OutcomeVariable, na.rm = TRUE),
    Median = median(OutcomeVariable, na.rm = TRUE),
    SD = sd(OutcomeVariable, na.rm = TRUE),
    N = sum(!is.na(OutcomeVariable)),
    .groups = "drop"
  )

hist(
  independent$OutcomeVariable[independent$GroupVariable == "Group1"],
  breaks = 15, col = "skyblue", border = "white"
)
hist(
  independent$OutcomeVariable[independent$GroupVariable == "Group2"],
  breaks = 15, col = "firebrick", border = "white"
)
ggboxplot(
  independent,
  x = "GroupVariable",
  y = "OutcomeVariable",
  color = "GroupVariable",
  palette = "jco",
  add = "jitter"
)

shapiro.test(
  independent$OutcomeVariable[
    independent$GroupVariable == "Group1"
  ]
)
shapiro.test(
  independent$OutcomeVariable[
    independent$GroupVariable == "Group2"
  ]
)

# Select one procedure using the design, diagnostics, and course rule.
t.test(
  OutcomeVariable ~ GroupVariable,
  data = independent,
  var.equal = TRUE
)
cohens_d(
  OutcomeVariable ~ GroupVariable,
  data = independent,
  pooled_sd = TRUE
)

wilcox.test(OutcomeVariable ~ GroupVariable, data = independent)
cliff.delta(OutcomeVariable ~ GroupVariable, data = independent)
```

Use only the selected inferential test and its matching effect size in the final
report. `cohens_d(..., pooled_sd = TRUE)` matches the equal-variance course
example. Cliff's delta sign depends on group ordering; report the group order
and use the `effsize` output's magnitude interpretation rather than Cohen's d
cutoffs. Follow the assignment's rule for whether effect sizes are reported
only after a statistically significant result.

### Reporting checklist

- Name the two groups and outcome; report group sample sizes and the requested
  means/SDs or medians.
- Report the independent t-test's `t`, degrees of freedom, and p-value, or
  Wilcoxon rank-sum's printed `W` and p-value.
- Report Cohen's d or Cliff's delta only as applicable, keeping its sign tied
  to the stated group order.
- Do not say the group medians differ based on Mann–Whitney unless the
  distribution-shape conditions support that interpretation.

```r
# Independent t-test:
# An independent t-test compared OutcomeVariable between Group1 and Group2.
# Group1 scores (M = xx.xx, SD = xx.xx) were significantly / not significantly
# different from Group2 scores (M = xx.xx, SD = xx.xx), t(df) = x.xx, p = .xxx.
# If required and statistically significant: Cohen's d = x.xx (small / medium / large / very large).

# Mann–Whitney / Wilcoxon rank-sum:
# A Mann–Whitney test compared OutcomeVariable between Group1 and Group2.
# Group1 scores (Mdn = xx.xx) were significantly / not significantly different
# from Group2 scores (Mdn = xx.xx), W = xx, p = .xxx.
# If required and statistically significant: Cliff's delta = x.xx (use effsize's magnitude label).
```

## Procedure D: Chi-Square Goodness-of-Fit

### Question and assumptions

Use this test for one categorical variable when the question is whether its
observed category counts differ from a prespecified expected distribution. The
expected proportions must be justified by the assignment's historical,
research, or theoretical reference, sum to 1, and correspond to the correct
categories. This is observational count analysis: there is no IV/DV distinction
and no normality assumption.

Each observation must be independent and belong to exactly one mutually
exclusive category. The supplied course rule requires every expected count to
be at least 5. Calculate and inspect expected counts before interpreting the
test. If that condition fails, do not present the asymptotic result as
trustworthy; consult the instructor about an appropriate exact or simulation
approach. Do not combine categories after seeing results unless the grouping is
substantively justified in advance.

### R workflow

Replace the example category labels and probabilities. Defining the factor
levels explicitly preserves categories with zero observed counts and aligns the
expected proportions by name.

```r
library(readxl)

DatasetName <- read_excel("path/to/data.xlsx")
category_data <- DatasetName$CategoryVariable
category_data <- category_data[!is.na(category_data)]

expected <- c(Category1 = 0.10, Category2 = 0.60, Category3 = 0.30)
stopifnot(
  length(expected) >= 2,
  !is.null(names(expected)),
  !anyDuplicated(names(expected)),
  all(is.finite(expected)),
  all(expected > 0),
  isTRUE(all.equal(sum(expected), 1))
)
stopifnot(all(unique(category_data) %in% names(expected)))

observed <- table(factor(category_data, levels = names(expected)))
stopifnot(identical(names(observed), names(expected)))
observed

barplot(
  observed,
  main = "CategoryVariable",
  xlab = "Category",
  ylab = "Frequency",
  col = rainbow(length(observed))
)

expected_counts <- sum(observed) * expected
expected_counts
if (any(expected_counts < 5)) {
  stop("An expected count is below 5; consult the instructor before using the asymptotic test.")
}

chi_result <- chisq.test(x = observed, p = expected)
chi_result
chi_result$expected
chi_result$stdres

# Cohen's w for the goodness-of-fit test.
w <- sqrt(as.numeric(chi_result$statistic) / sum(observed))
w
```

The degrees of freedom are the number of included categories minus 1. Report
the R statistic as χ², sample size `N = sum(observed)`, p-value, and Cohen's
`w`. The supplied course bands are `< .10` negligible, `.10–<.30` small,
`.30–<.50` moderate, and `≥ .50` large. Cohen's w can exceed 1. Standardized
residuals can help locate category-level discrepancies, but inspect them as
follow-up descriptions rather than treating each as a separate confirmatory
test.

```r
# A Chi-Square Goodness-of-Fit test assessed whether observed CategoryVariable
# frequencies differed from the expected distribution.
# The observed frequencies did / did not differ from expected frequencies,
# χ²(df, N = xxx) = xx.xx, p = .xxx.
# The difference was negligible / small / moderate / large (Cohen's w = x.xx).
```

## Procedure E: Chi-Square Test of Independence

### Question and assumptions

Use this test to ask whether two categorical variables are associated. Create
one contingency table; rows and columns represent the categories of each
variable, and cells contain observed counts. It is observational and does not
require a causal IV/DV designation. A statistically significant association
does not establish that one variable causes the other.

Each case must be independent, and each variable's categories must be mutually
exclusive. The supplied course rule expects every cell's expected count to be
at least 5. Inspect the expected-count table. If the condition fails, the
ordinary Pearson chi-square approximation may be unreliable; for a 2 × 2 table
consider Fisher's exact test, or ask the instructor about an appropriate
simulation/exact method for the design. Do not silently report an asymptotic
chi-square p-value as definitive.

### R workflow

Keep only cases with both categorical values present. Factor levels are
explicitly supplied here to preserve the intended category set; replace them
with the actual mutually exclusive categories in the assignment.

```r
library(readxl)

DatasetName <- read_excel("path/to/data.xlsx")
independence_data <- DatasetName[
  complete.cases(DatasetName[c("Variable1", "Variable2")]),
  c("Variable1", "Variable2")
]
independence_data$Variable1 <- factor(
  independence_data$Variable1,
  levels = c("Level1", "Level2")
)
independence_data$Variable2 <- factor(
  independence_data$Variable2,
  levels = c("OutcomeA", "OutcomeB")
)
stopifnot(
  !anyNA(independence_data$Variable1),
  !anyNA(independence_data$Variable2),
  nlevels(droplevels(independence_data$Variable1)) >= 2,
  nlevels(droplevels(independence_data$Variable2)) >= 2
)

independence_table <- table(
  independence_data$Variable1,
  independence_data$Variable2
)
stopifnot(all(rowSums(independence_table) > 0), all(colSums(independence_table) > 0))
independence_table

barplot(
  independence_table,
  beside = TRUE,
  col = rainbow(nrow(independence_table)),
  legend = rownames(independence_table),
  xlab = "Variable2",
  ylab = "Frequency"
)

chi_result <- chisq.test(independence_table, correct = FALSE)
chi_result$expected
if (any(chi_result$expected < 5)) {
  if (all(dim(independence_table) == c(2, 2))) {
    fisher.test(independence_table)
  } else {
    set.seed(20261009)
    chisq.test(independence_table, simulate.p.value = TRUE, B = 10000)
  }
} else {
  chi_result
}

# Cramer's V from the Pearson chi-square statistic.
cramers_v <- sqrt(
  as.numeric(chi_result$statistic) /
    (sum(independence_table) * min(nrow(independence_table) - 1,
                                   ncol(independence_table) - 1))
)
cramers_v
```

When expected counts meet the course rule, report χ², degrees of freedom
`(rows − 1) × (columns − 1)`, p-value, and Cramér's V. If using Fisher's exact
or a simulated p-value because of small expected counts, report the method and
statistic/output actually used; do not pair that p-value with the asymptotic
chi-square result as if they were one test. For a simulated test, record `B`
and the random seed if reproducibility is required.

The supplied course bands are Cramér's V `< .10` negligible, `.10–<.30` small,
`.30–<.50` moderate, and `≥ .50` large. These are course conventions; strength
can depend on table dimensions. Cramér's V has no direction. Use observed
proportions or residuals to describe the pattern, with suitable caution about
multiple comparisons.

```r
# A Chi-Square Test of Independence assessed the association between Variable1 and Variable2.
# There was / was not evidence of an association, χ²(df) = xx.xx, p = .xxx.
# The association was negligible / small / moderate / large (Cramér's V = .xx).
```

## Reproducibility and release

- Keep a clean source dataset, analysis script, and rendered report; preserve
  the original data and document transformations.
- Replace every example dataset/column/group name before running the script.
- Ensure the report can be re-knit from the documented inputs and package setup.
- Distinguish the student's analysis and interpretation from software output.
- Do not publish identifiable or restricted participant data. Public availability
  of an RPubs page is a sharing decision, not evidence of analytical correctness.

Course-provided tools:

- [Inferential Test Selector](https://fsaffaf.github.io/AA5221/tools/inferential_test_selector.html)
- [P-Value Interpreter](https://fsaffaf.github.io/AA5221/tools/p_value_interpreter.html)
