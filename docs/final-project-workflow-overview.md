# AA 5221 Final Project — Workflow Overview

## Purpose

Use this workflow to organize the final project from the supplied research
questions through the R analyses and private OneDrive submission. It maps each
question to its dataset, variables, design, and candidate inferential procedure.
The actual test variants and results depend on the assigned data and required
diagnostics; no results are supplied or inferred here.

## Research-question map

| Question | Dataset and variables | Design | Test family and decision |
|---|---|---|---|
| 1. Did Team 1 communication effectiveness increase after the workshop? | `Team1Data.xlsx`: `BeforeComm`, `AfterComm`; use `ID` to verify pairing | Paired scores for the same Team 1 employees | Paired t-test if the `AfterComm - BeforeComm` difference scores meet the course normality rule; otherwise Wilcoxon signed-rank |
| 2. After the workshop, is communication effectiveness different between Team 1 and Team 2? | `Team1vTeam2.xlsx`: `Team` (1 or 2), `CommScore` | Independent groups measured after the workshop | Independent t-test if each team's `CommScore` meets the course normality rule; otherwise Mann–Whitney / Wilcoxon rank-sum |
| 3. Is perceived workshop effectiveness associated with gender? | `Team1Data.xlsx`: `Effective` (Yes/No), `Gender` (male/female) | Two categorical variables from Team 1 | Chi-Square Test of Independence; verify expected cell counts |
| 4. Is job satisfaction positively related to communication effectiveness after the workshop? | `Team1Data.xlsx`: `Satisfaction`, `AfterComm` | Two quantitative variables for Team 1 | Pearson correlation for an approximately linear relationship when the course normality rule is met; otherwise Spearman correlation if a monotonic association is appropriate |

Use question 3's **Test of Independence**, not Goodness-of-Fit: it asks whether
two categorical variables are associated. Use question 1's paired procedure,
not an independent-groups test: the same Team 1 employees are measured before
and after. Question 2 compares different teams, and question 4 asks for an
association, not a causal effect.

## Project workflow

### 1. Prepare the project folder and files

Create `Final Project` inside the course's AA 5221 OneDrive folder. Place the
two supplied datasets there:

- `Team1Data.xlsx`
- `Team1vTeam2.xlsx`

Create the two project files there as well:

- `FinalProject.R`
- `FinalProject.Rmd`

Keep the original datasets unchanged. The R script and R Markdown report should
refer to the local files in this project folder or another stable path available
when the work is re-run.

### 2. Build one organized R script

Use one script and complete each research question from start to finish before
moving to the next question.

1. **Setup:** load `readxl` and the packages required for the tests/effect sizes
   selected; import both Excel files once as clearly named data frames. Package
   installation belongs in the Console, not in the knitted analysis.
2. **Research Question 1:** verify paired IDs and complete pairs; inspect
   `BeforeComm` and `AfterComm`; calculate `AfterComm - BeforeComm`; inspect the
   difference plot/outliers and Shapiro–Wilk result; select one paired test;
   calculate and report its matching effect size and result.
3. **Research Question 2:** verify the two `Team` groups and independent
   observations; summarize and plot `CommScore` by team; run Shapiro–Wilk within
   each team; select one independent test using the course rule; use the
   assignment's equal-variance assumption only if required; calculate and
   report the matching effect size.
4. **Research Question 3:** make a frequency/contingency table of `Effective`
   by `Gender`; check categories, missing data, independence, and expected cell
   counts; run the Chi-Square Test of Independence if its conditions are
   adequate; report χ², degrees of freedom, p-value, and Cramér's V. If expected
   counts are inadequate, follow the instructor's direction for an alternative
   rather than presenting the ordinary approximation as reliable.
5. **Research Question 4:** inspect a scatterplot of `Satisfaction` and
   `AfterComm`; check linearity/monotonicity, influential points, and the
   course's normality diagnostics; select Pearson or Spearman; report its
   coefficient, p-value, and requested descriptive statistics. A positive
   association alone does not show that satisfaction causes communication to
   improve or vice versa.
6. **Closeout:** report the actual sample size used for each test, document
   missing-value exclusions, and add concise interpretation comments below each
   question's output. Do not invent results before running the analyses.

Follow the detailed code and reporting guidance in the
[Applied Statistics in R skill](../VesselFramework_Applied_Statistics_R_SKILL_v0.1.md).
Use the course's test-selection and p-value tools only as aids; the study design,
data, and assignment instructions determine the analysis.

### 3. Create one R Markdown report

Create `FinalProject.Rmd` with a meaningful title and HTML output. Organize it
in the same order as the R script:

1. Brief scenario and analysis purpose.
2. Research Question 1: data/method, relevant code and output, result and
   interpretation.
3. Research Question 2: data/method, relevant code and output, result and
   interpretation.
4. Research Question 3: data/method, relevant code and output, result and
   interpretation.
5. Research Question 4: data/method, relevant code and output, result and
   interpretation.
6. A short overall conclusion that distinguishes statistical evidence from
   claims about workshop effectiveness or causation.

Include executable code chunks and the outputs needed to reproduce the results.
Knit the document and inspect the HTML for errors, missing figures, readable
tables, and consistent interpretations. Keep the `.Rmd` and knitted HTML private
with the project files; **do not publish to RPubs**.

### 4. Verify and submit

Before sharing, confirm that the `Final Project` OneDrive folder contains all
four required files:

- `Team1Data.xlsx`
- `Team1vTeam2.xlsx`
- `FinalProject.R`
- `FinalProject.Rmd`

Re-knit `FinalProject.Rmd` from the saved files, verify the analysis and results
match the R script, and confirm the OneDrive sharing permission is appropriate
for the instructor. Submit the OneDrive folder link through Canvas. Do not make
the work publicly visible.
