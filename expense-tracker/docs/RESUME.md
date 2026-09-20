# Resume & Interview Kit

## Project title
**Expense Tracker & Analytics: SQL + Python + Streamlit**

## One-line description (for the Projects section)
Built an end-to-end personal-finance analytics application with a normalised SQLite database, SQL window-function analytics, pandas analysis, and an interactive Streamlit dashboard.

## Resume bullets (pick 3–5)
- Designed a normalised **SQLite** schema (4 tables, foreign keys, CHECK constraints, indexes) and wrote 7 analytical **SQL** queries using **CTEs and window functions** (`LAG`, `RANK`, running totals) for MoM trends, budget variance and savings rate.
- Built an analytics layer in **Python (pandas, NumPy)** covering category share, weekday spending patterns, budget utilisation and a **linear-trend forecast** of next-month spend.
- Implemented **anomaly detection** using a robust median/MAD modified z-score; identified and fixed a *masking* flaw in a plain z-score approach, catching 3 of 3 injected outliers with zero false positives.
- Developed an interactive **Streamlit + Plotly dashboard** (KPIs, budget-vs-actual, category × month heatmap, CSV export) that lets users filter by date and category and add transactions.
- Engineered the project to industry standards: layered architecture (repository / analytics / CLI), input validation, **35 pytest unit tests**, **Ruff** linting and formatting, packaged with `pyproject.toml`, and a VS Code debug/task configuration.
- Created a reproducible synthetic-data generator (600+ INR transactions, 12 months, seasonality and rent/salary changes) so the project runs end-to-end with a single command.

## Skills keywords for ATS
Python · SQL · SQLite · pandas · NumPy · Plotly · Streamlit · Data Cleaning · Exploratory Data Analysis · Window Functions · CTEs · Data Modelling · Anomaly Detection · Forecasting · Dashboarding · Data Visualization · pytest · Git · KPI Reporting

## Interview talking points

**Why did you build this?**
To practise the full analyst pipeline (modelling, querying, analysing, visualising, communicating) on data where I could control the ground truth and verify my methods.

**Why median/MAD instead of a normal z-score?**
My first implementation used mean and standard deviation and missed a ₹24,500 medical expense: large outliers inflate the standard deviation, which hides them ("masking"). Median and MAD are robust to that, so the score correctly flagged all three injected anomalies.

**Why exclude the current month from the forecast?**
The current month is incomplete, so including it would drag the trend down artificially.

**How did you validate correctness?**
Unit tests against small hand-computed datasets (e.g. monthly totals, MoM %, budget statuses, forecast on a perfect linear series), plus running every SQL query against the seeded database.

**What would you do next?**
Bank-statement CSV import with rule-based categorisation, recurring-expense detection, and CI with GitHub Actions.

**How does the design keep analytics testable?**
Analytics functions take DataFrames and return DataFrames with no database access, and all SQL is isolated in a repository class.

## GitHub checklist
- [ ] Replace "Your Name" in `LICENSE`
- [ ] Take 2–3 dashboard screenshots into `docs/images/` and embed them at the top of the README
- [ ] Add a repo description and topics: `data-analysis`, `python`, `sql`, `streamlit`, `pandas`, `dashboard`
- [ ] Link the repo (and a Streamlit Community Cloud demo, if you deploy it) on your resume and LinkedIn
