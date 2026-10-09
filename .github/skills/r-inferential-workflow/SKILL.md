---
name: r-inferential-workflow
description: >
  Build reproducible R and RMarkdown workflows for paired and independent
  comparisons, categorical association, and correlation. Use for statistical
  coursework and Excel-based organizational research, with assumption checks,
  accurate reporting, and private deliverables.
---

# R inferential workflow

## Boundaries and inputs

- Read the assignment, variable definitions, rubric, and instructor examples
  before selecting methods. Record which dataset and variables answer each
  question. Do not join datasets merely because both contain an ID column.
- Request inaccessible workbooks rather than fabricating observations or
  results. Do not bypass authentication.
- Keep student data, assignment scripts, reports, and synthetic validation
  fixtures outside the public repository, preferably in the user's private
  course folder. Never publish to RPubs or commit a completed assignment.
- Distinguish synthetic software checks from analysis of the supplied data.
  Follow the course's academic-integrity and AI-disclosure requirements.

## Environment

Run `Rscript r/setup.R` from the repository to install the declared packages.
Base R's `stats` supplies the inferential tests; `readxl` reads Excel,
`effsize` supports Cohen's d, and `knitr`/`rmarkdown` support reporting.
RMarkdown rendering additionally requires Pandoc, available through RStudio
or the cloud setup workflow. Verify availability rather than assuming it.
On Linux, source installation of the rendering dependency `fs` requires
libuv headers; the cloud workflow installs `libuv1-dev` explicitly. Diagnose
the first dependency build error rather than hiding downstream package failures.
Run `Rscript r/test_statistics_environment.R` for synthetic smoke checks.

## Data checks

1. Import named workbooks with `readxl::read_excel()`. Validate required column
   names, numeric types, finite values, scale bounds, category labels, and IDs.
2. Check independence and the unit of analysis from the study design, not an
   automated statistical test. Pair repeated observations by employee.
3. Report missing-value counts and each analysis's complete-case sample size.
   Filter paired values together; never drop each measurement independently.
4. Produce descriptive statistics, boxplots, histograms, Q-Q plots, and a
   scatterplot as appropriate. Investigate outliers; never delete legitimate
   observations merely to achieve significance or normality.
5. Apply the instructor's stated decision rule. A nonsignificant Shapiro-Wilk
   result is not proof of normality. Assess linearity/monotonicity, outliers,
   difference-score symmetry, and group variance assumptions separately.

## Selecting one test per question

| Design | Parametric test | Alternative | Main checks |
| --- | --- | --- | --- |
| Same people measured twice | Paired/dependent t-test | Wilcoxon signed-rank | Normality of differences, not separate time points; symmetry for a signed-rank location interpretation |
| Different people in two groups | Independent t-test | Mann-Whitney U | Within-group distributions; equal variance if using a pooled t-test |
| Two categorical variables | Chi-square independence | Consult instructor if expected counts are inadequate | Contingency table, expected counts, independent observations |
| One categorical variable versus specified proportions | Chi-square goodness of fit | Consult instructor if expected counts are inadequate | Explicit expected proportions and expected counts |
| Two quantitative variables | Pearson correlation | Spearman correlation | Distribution rule, linear versus monotonic relationship, influential outliers |

- Goodness of fit concerns one categorical variable and specified expected
  proportions; it is not the test for association between two categories.
- Use Welch's independent t-test unless the course explicitly assumes equal
  variances. When it does, use `var.equal = TRUE` and disclose that assumption.
- Choose tail direction before examining results. Follow the instructor's
  examples; do not select a one-sided test after seeing the observed effect.
- Use explicit missing-value filtering before calling test functions.
- For rank tests with ties/zeros, disclose approximate inference and use
  `exact = FALSE`. Do not suppress unrelated warnings.
- For chi-square, print expected counts and the correction choice.
  Flag inadequate expected counts; do not silently switch to another family.
- Rank tests compare rank/distribution behavior, not means. Interpret them
  as median/location shifts only when additional shape assumptions hold.

## User-supplied teaching widgets

The user supplied a code-checking widget twice and a statistical-test selector.
Treat the duplicate checker as one source, not independent corroboration.
The HTML was inspected as user-provided teaching material; no licence grant
for republication was supplied. Retain these original workflow notes, not a
copy of the instructor-branded HTML in this public repository.

The selector describes eight supported course routes:

| Measurement | Design | Course normality choice | Test |
| --- | --- | --- | --- |
| Categorical only | Two variables | Does not apply | Chi-square independence |
| Categorical only | One variable versus expected distribution | Does not apply | Chi-square goodness of fit |
| Categorical + continuous | Between subjects | Normal | Independent t-test |
| Categorical + continuous | Between subjects | Not normal | Mann-Whitney U |
| Categorical + continuous | Within subjects | Normal differences | Dependent t-test |
| Categorical + continuous | Within subjects | Nonnormal differences | Wilcoxon signed-rank |
| Continuous only | Relationship | Normal under the course rule | Pearson correlation |
| Continuous only | Relationship | Not normal under the course rule | Spearman correlation |

These are bounded course routes, not a universal automatic test-selection
algorithm. Confirm exactly two groups for these comparison tests. In a
wide-format paired dataset, the categorical condition is before/after even
though both measurement columns are numeric. Invalid or incomplete selections
must produce an explicit correction request, not a guessed recommendation.
Normality is not applicable to the categorical routes; expected counts still
matter.

### Checking group-subsetting code

The supplied checker trims surrounding whitespace and compares the answer
with one literal placeholder string. It does not parse R or verify the
dataset, columns, group labels, or statistical assumptions. Replacing the
placeholders as directed would generally fail that exact-string check.
Equivalent whitespace or quote styles can fail too. Do not label valid R
code incorrect solely because it differs from that placeholder.

An original generic pattern for a string-labelled group is:

```r
group_a <- StudyData$Score[StudyData$Condition == "A"]
```

For a numeric group code, use a numeric comparison, such as
`StudyData$Condition == 1`. Confirm the actual column type and labels first.
Handle missing values explicitly: base R subsetting with an `NA` comparison
can retain `NA` values. Use a documented complete-case dataset for the test
and its diagnostics. Both groups must come from the same outcome column.

To check syntax without running submitted code, use `parse(text = code)`;
syntax validity alone does not establish correct variable selection. Never
use `eval()`, `source()`, or shell execution on untrusted submitted answers.
Validate dataset/column references, comparison values, selected observations,
and downstream test behavior separately using trusted analysis code.

## Workflow and reporting

Complete each research question end-to-end before beginning the next:
question, dataset/variables, hypotheses, diagnostics, descriptive statistics,
one selected inferential test, effect size, and interpretation.

Report sample size, statistic, degrees of freedom where applicable, exact
p-value (or `p < .001`), confidence interval when available, effect-size
definition/direction, and limitations. For paired standardized mean change,
label `d_z = mean(after - before) / sd(after - before)` explicitly; other
paired Cohen's d conventions are not interchangeable. Print contingency counts
and within-group proportions for categorical associations.

Do not equate nonsignificance with equality, prove equivalence with an ordinary
test of difference, infer causation from a correlation, treat perceived
effectiveness as measured improvement, or claim turnover changed when it was
not measured. An uncontrolled pre/post comparison does not establish that the
intervention caused the change.

Use one standalone `.R` script for the analyses. Where suitable, label its
sections for `knitr::read_chunk()` and reuse them in one `.Rmd` to avoid
divergent code/results. Knit locally from a clean session and inspect the
rendered output. Remove validation fixtures and non-required outputs from the
submission folder, not from the evidence archive.

## Course-specific primary references

Verify the currently supplied course guidance; these pages informed the
initial workflow but are not universal statistical decision rules:

- [Paired comparisons](https://fsaffaf.github.io/AA5221/code/dependent_t_test_wilcoxon_signed_rank.html)
- [Independent comparisons](https://fsaffaf.github.io/AA5221/code/independent_t_test_mann_whitney_u.html)
- [Categorical association](https://fsaffaf.github.io/AA5221/code/chisquare_test_of_independence.html)
- [Correlation](https://fsaffaf.github.io/AA5221/code/correlations.html)
