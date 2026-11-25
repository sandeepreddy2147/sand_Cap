# Viva questions and answers

Sections: 1 Project, 2 Use Case 1, 3 Use Case 2, 4 Use Case 3, 5 Use Case 4, 6 Pandas, 7 NumPy, 8 Matplotlib and Seaborn, 9 SQL, 10 MySQL, 11 SQLAlchemy, 12 Flask, 13 Testing, 14 AWS, 15 Big data.

Numbers in the project answers come from the supplied sample: 498 crimes, 20 columns.

---

## 1. Project overview

**Q1. Explain the project in one minute.**
The project reads six Chicago CSV files, cleans the crime data with Pandas, stores it in a database (MySQL, or SQLite when MySQL is not running), analyses it in four notebooks, and shows the data in a Flask website that supports create, read, update and delete (CRUD) for crime records.

**Q2. What are the four use cases?**
1. Load and clean the data and insert it into the database.
2. Exploratory analysis and charts (trend, categories, arrests, heatmap, communities).
3. Statistical insights (hourly pattern, IQR outliers by community, correlation).
4. SQL reporting (summary tables, queries, views, Pandas integration, charts from the database).

**Q3. Which files are used and what does each contain?**
`chicago_crime_dataset.csv` has the crimes (498 rows). `iucr_codes.csv` maps the IUCR code to the crime type. `chicago_city_community.csv` has the 77 community areas with population. `chicago_district_ps_info.csv` has police districts. `chicago_police_beat_info.csv` has beats. `chicago_ward_offices.csv` has the wards.

**Q4. What is the project folder structure?**
`data/raw` (inputs), `notebooks` (four use cases and `db_config.py`), `data/reports` (answers and charts), `database` (SQLite files), `app` (Flask), `tests` (pytest), `docs`.

**Q5. Why did you use a SQLite fallback?**
MySQL may not be installed or running on every computer. `db_config.py` tries MySQL first when `MYSQL_USER` is set in `.env`, and uses SQLite when it cannot connect. The table design and SQL are the same for both, so the notebooks run anywhere.

**Q6. What are the limitations of the data?**
It is a sample: 490 of 498 records are from 2016, and 88.96% fall on two dates (2016-05-03 and 2016-05-04). The dates have no time of day. So the yearly and monthly results show which dates the sample has, not real trends, and the hourly chart is one point.

**Q7. What would you do next with the full dataset?**
Load it in chunks, add a time column to get a real hourly pattern, compute rates per 1,000 residents using the population column, and run the same notebooks.

**Q8. How do the notebooks connect to each other?**
Notebook 01 writes the cleaned `crime` table. Notebooks 02, 03 and 04 read that table, so 01 must run first.

---

## 2. Use Case 1: load and clean

**Q9. How did you load the CSV and why was a fix needed?**
With `pd.read_csv`. The last two lines have an opening quote in `location` that is never closed. The code finds lines with an odd number of `"` characters and closes them in memory with `io.StringIO`. The file on disk is unchanged.

**Q10. How many rows and columns are there?**
498 rows and 20 columns.

**Q11. How did you convert the date column?**
`pd.to_datetime(text, format="%m/%d/%Y", errors="coerce")`. An explicit format avoids wrong guesses (5/3/2016 could be 5 March or 3 May). `errors="coerce"` turns bad values into `NaT` so they can be counted. Result: 0 unparsed dates.

**Q12. What missing values were found and how were they handled?**
`location_desc` was missing in about 0.8% of rows and was filled with `UNKNOWN`. The coordinates and `location` were missing in 5.82% of rows. They were left empty, because invented positions would be wrong and counts do not need them.

**Q13. How did you standardise categorical columns?**
Strip spaces, collapse repeated spaces and convert to upper case (`str.strip().str.replace(r"\s+", " ").str.upper()`). The IUCR file header `PRIMARY_TYPE ` has a trailing space, so column names are stripped as well.

**Q14. How were the new features made?**
`Year = Date.dt.year`, `Month = Date.dt.month`, `DayOfWeek = Date.dt.day_name()`.

**Q15. How did NumPy help with missing values?**
`np.round(df.isna().to_numpy().mean(axis=0) * 100, 2)` gives the percentage per column. `np.where(missing_pct > 50)` finds columns above 50%. None exist (highest is 5.82%), so no column must be dropped.

**Q16. When can a column with more than 50% missing be dropped?**
When it is not needed for the analysis and cannot be filled reliably. If it is important, consider imputing it, getting the data from another source, or keeping it with a missing flag.

**Q17. How many unique crime types exist?**
23 (`primary_type`). THEFT is the largest with 105 records. The IUCR reference file defines 33 types. 97 distinct IUCR codes are used.

**Q18. Are there date format anomalies?**
Only minor ones. 497 of 498 dates have no zero padding (5/3/2016), which does not stop parsing. No date has a time, none is in the future, none was updated before the crime date.

**Q19. Are there outliers?**
By the IQR rule there are none in the coordinates. There are 59 outliers in the days between the crime and its update, and 11 in crimes per day. Two dates hold 88.96% of all crimes.

**Q20. How is the `crime` table designed?**
One row per crime with `id` as primary key, date and its features, crime type columns, boolean `arrest` and `domestic`, location codes, nullable coordinates, and indexes on year, crime type and community (the columns used for grouping). Column names such as `crime_year` avoid MySQL keywords like `YEAR`.

**Q21. How is the data written to the database?**
SQLAlchemy creates the table from a `Table` definition, then `DataFrame.to_sql(..., if_exists="append")` inserts rows. With MySQL the URL is `mysql+pymysql://user:password@host:3306/chicago_crime`. The table is dropped and rebuilt first, so reruns give the same result.

**Q22. What is PyMySQL?**
A pure-Python MySQL driver. SQLAlchemy uses it through the `mysql+pymysql` URL.

---

## 3. Use Case 2: exploratory analysis

**Q23. Is crime increasing or decreasing?**
The chart goes from 2 crimes in 2012 to 490 in 2016, but the sample has 1 to 3 dates in most years and no year is fully covered. The rise reflects the dates in the file, not a real trend.

**Q24. Which crime category is most frequent?**
THEFT with 105 records (21.08%), then BATTERY with 85 (17.07%). The top 10 of 23 categories cover 89.55%.

**Q25. What is the arrest rate and how is it calculated?**
`df["Arrest"].mean() * 100`. `True` counts as 1, so the mean is the share of arrests: 124 of 498, which is 24.90%.

**Q26. Is the arrest rate consistent across years?**
It cannot be judged. Only 2016 has enough records (490, arrest rate 24.3%). The other years have 1 to 4 records, so rates of 0% to 100% are not meaningful.

**Q27. How was the month by weekday heatmap built?**
`pd.crosstab(df.Month, df.DayOfWeek)`, reindexed to all 12 months and 7 weekdays with 0 for missing pairs, drawn with `sns.heatmap`. The busiest cell is May / Wednesday (299).

**Q28. Which month has the highest crime frequency?**
May with 447 crimes (89.76%). The sample has few dates, so this is not a seasonal result.

**Q29. Which community area has the most crimes?**
Austin (code 25) with 34 crimes (6.83%). The top 10 areas cover 35.94%.

**Q30. Why use percentages next to counts?**
Counts depend on the size of the dataset. Percentages show each category's share and make results comparable.

---

## 4. Use Case 3: statistics

**Q31. Why is the hourly chart a single point?**
`Date.dt.hour` is 0 for all rows because the source dates have no time of day. A dataset with times would give a real hourly curve.

**Q32. What is the IQR method?**
`IQR = Q3 - Q1`. A value is an outlier if it is below `Q1 - 1.5*IQR` or above `Q3 + 1.5*IQR`. Beyond `Q3 + 3*IQR` it is an extreme outlier.

**Q33. What were the outliers among community areas?**
Q1 = 2, Q3 = 9, upper fence 19.5. Austin (34), Near North Side (20) and Humboldt Park (20) are outliers. Austin is also beyond the extreme fence (30). The mean per area is 6.47 and the median is 5.

**Q34. Why include areas with zero crimes?**
All 77 areas are in the data. Leaving out areas with no crimes would raise the mean and give a wrong picture.

**Q35. What does a box plot show?**
The median (line), Q1 to Q3 (box), the whiskers (data within the fences) and points beyond the whiskers (outliers).

**Q36. What does `df.corr()` calculate?**
The Pearson correlation between numeric columns, from -1 to +1. The heatmap shows it as colours.

**Q37. What did the correlation matrix show?**
The strongest values are between location columns (beat and district, +1.00; community and latitude, -0.74), which describe the same place in different ways. Arrest has only weak links (the strongest is with day of week, +0.19).

**Q38. Does correlation mean causation?**
No. It only shows that two columns move together. A third factor or chance can explain it.

**Q39. Why was `Hour` left out of the correlation?**
It has one value, so its variance is zero and its correlation is undefined (NaN).

---

## 5. Use Case 4: SQL reporting

**Q40. What summary tables were made?**
`summary_crime_yearly`, `summary_crime_by_category` and `summary_arrest_yearly`. They store ready results so reports do not scan every crime row.

**Q41. How were they loaded?**
With the MySQL Connector (`mysql.connector`), using `cursor.executemany` and `%s` placeholders. SQLite uses `?`. The code selects the placeholder automatically.

**Q42. Why use placeholders instead of f-strings for values?**
They prevent SQL injection and handle quoting and types correctly.

**Q43. What are the three required queries?**
Crimes per year (`GROUP BY crime_year`), top 5 types with percentages (`COUNT(*)`, a sub-query for the total, `ORDER BY ... LIMIT 5`) and arrests per year (`SUM(CASE WHEN arrest = 1 THEN 1 ELSE 0 END)`).

**Q44. What is a view and why use one?**
A saved query that works like a table. It always shows current data, hides complex SQL, and can limit which columns users see. The project has `vw_crime_yearly` and `vw_crime_by_category`.

**Q45. Does a view store data?**
A normal view does not. It runs its query each time. A materialized view stores the result (MySQL has none built in, which is why summary tables are used).

**Q46. How do you read a view into Pandas?**
`pd.read_sql("SELECT * FROM vw_crime_yearly", conn)`. MySQL returns `DECIMAL` as Python `Decimal`, so numeric columns are converted with `pd.to_numeric`.

**Q47. Which charts come from the database?**
Crimes and arrests per year, top 10 crime types, monthly frequency, top 10 communities (join with `ref_community`) and crimes by district (join with `ref_district`).

**Q48. Why were `ref_community` and `ref_district` created?**
The crime table stores only codes. Joining reference tables gives names for the charts.

---

## 6. Pandas

**Q49. What is a DataFrame and a Series?**
A DataFrame is a 2-D labelled table. A Series is one labelled column (1-D).

**Q50. `loc` vs `iloc`?**
`loc` selects by label, `iloc` by integer position.

**Q51. How do you find and fill missing values?**
`isna().sum()` counts them. `fillna(value)` fills them, `dropna()` removes them. Interpolation or group-wise means are other options.

**Q52. `groupby` vs `pivot_table` vs `crosstab`?**
`groupby` aggregates by keys. `pivot_table` reshapes with an aggregation into a grid. `crosstab` is a quick frequency table of two columns.

**Q53. `merge` vs `join` vs `concat`?**
`merge` joins on columns (like SQL). `join` joins on the index. `concat` stacks frames along an axis.

**Q54. What does `apply` do and when should it be avoided?**
It runs a function on rows or columns. It is slow compared with vectorised operations, so use vectorised methods first.

**Q55. What is `astype` for? What are `category` and `string` dtypes?**
`astype` converts types. `category` saves memory for repeated values. `string` is a proper text type with missing value support.

**Q56. What is `value_counts()`?**
It counts unique values, sorted from most to least frequent.

**Q57. How to handle big CSV files?**
`chunksize` in `read_csv`, `usecols`, `dtype` settings, or tools like Dask, Polars or Spark.

**Q58. What does `errors="coerce"` do?**
It turns invalid values into `NaT` or `NaN` instead of raising an error.

**Q59. What is `.dt`?**
The datetime accessor: `.dt.year`, `.dt.month`, `.dt.day_name()`, `.dt.hour`.

---

## 7. NumPy

**Q60. Why is NumPy faster than Python lists?**
Arrays are stored in a contiguous block with one data type, and operations are vectorised in compiled C code.

**Q61. What is broadcasting?**
NumPy's rule for combining arrays of different shapes by stretching the smaller one, for example adding a scalar to an array.

**Q62. How are NaN values handled?**
`np.isnan`, `np.nanmean`, `np.nanpercentile`. Normal `mean` returns NaN if any value is NaN.

**Q63. `np.percentile` vs `np.median`?**
The median is the 50th percentile. `np.percentile(a, [25, 75])` gives Q1 and Q3 for the IQR.

**Q64. `np.where`?**
Returns indices where a condition is true, or chooses between two values: `np.where(cond, a, b)`.

**Q65. Sample vs population standard deviation?**
`np.std(a)` uses `ddof=0` (population). `ddof=1` divides by n-1 (sample). The project uses `ddof=1`.

---

## 8. Matplotlib and Seaborn

**Q66. Matplotlib vs Seaborn?**
Matplotlib is the base plotting library with full control. Seaborn is built on it and gives statistical charts (heatmap, box plot, bar plot with palettes) with less code.

**Q67. What are `fig` and `ax`?**
`fig` is the whole figure, `ax` is one set of axes (a chart) in it. `fig, ax = plt.subplots()` creates both.

**Q68. Which chart for which question?**
Line for a trend over time, bar for category comparison, heatmap for two categorical dimensions, box plot for spread and outliers, scatter for the relation of two numbers.

**Q69. How do you save a chart?**
`fig.savefig(path, dpi=130, bbox_inches="tight")`. `bbox_inches="tight"` stops labels from being cut off.

**Q70. Why is a heatmap good for month by weekday?**
Colour shows intensity, so busy and quiet cells are visible immediately.

---

## 9. SQL

**Q71. `WHERE` vs `HAVING`?**
`WHERE` filters rows before grouping. `HAVING` filters groups after aggregation.

**Q72. Order of execution of a query?**
`FROM`/`JOIN`, `WHERE`, `GROUP BY`, `HAVING`, `SELECT`, `ORDER BY`, `LIMIT`.

**Q73. Types of joins?**
`INNER` (matching rows only), `LEFT` (all left rows), `RIGHT`, `FULL`, `CROSS`. The district chart uses `LEFT JOIN` so crimes without a matching district stay in the result.

**Q74. `COUNT(*)` vs `COUNT(column)`?**
`COUNT(*)` counts rows. `COUNT(column)` skips NULLs.

**Q75. What is a primary key, a foreign key and an index?**
A primary key is a unique, non-null row identifier. A foreign key points to a primary key in another table. An index speeds up searches and grouping but slows writes slightly.

**Q76. What is normalisation?**
Organising tables to remove repeated data (1NF, 2NF, 3NF). The Flask database is a star schema (a fact table `fact_crime` with dimension tables), which is built for reporting.

**Q77. Star schema vs flat table?**
A star schema separates facts from descriptive dimensions, saves space and keeps names consistent. A flat table (the notebook's `crime` table) is simpler for analysis.

**Q78. What is a window function?**
It calculates across related rows without collapsing them, for example `RANK() OVER (ORDER BY cnt DESC)` or a running total.

**Q79. What is a sub-query? Where is it used here?**
A query inside another query. The percentage uses `(SELECT COUNT(*) FROM crime)` to get the total.

**Q80. `DELETE` vs `TRUNCATE` vs `DROP`?**
`DELETE` removes selected rows and can be rolled back. `TRUNCATE` empties the table quickly. `DROP` removes the table itself.

**Q81. What is a transaction? What is ACID?**
A group of statements that succeed or fail together. ACID: atomicity, consistency, isolation, durability.

**Q82. What is SQL injection and how is it prevented?**
Attacker text changes the query. Prevent it with parameterised queries, never string-built SQL with user values.

---

## 10. MySQL

**Q83. What is MySQL?**
An open-source relational database management system (RDBMS) that uses SQL.

**Q84. InnoDB vs MyISAM?**
InnoDB supports transactions, foreign keys and row-level locking, and is the default. MyISAM does not support transactions.

**Q85. How does the connection work from Python?**
Through a driver: PyMySQL (with SQLAlchemy) or `mysql.connector`. You give host, port, user, password and database, then use a cursor to run SQL and `commit()` to save changes.

**Q86. Why `CREATE OR REPLACE VIEW` is not used in the notebook?**
SQLite does not support it. `DROP VIEW IF EXISTS` followed by `CREATE VIEW` works in both.

**Q87. What are common MySQL data types used here?**
`INT`, `BIGINT`, `VARCHAR(n)`, `DECIMAL(5,2)`, `DATETIME`, `TINYINT(1)`/`BOOLEAN`, `FLOAT`.

**Q88. What is a backup and how is it done in MySQL?**
A copy of the data for recovery. `mysqldump -u user -p chicago_crime > backup.sql` creates a logical backup.

---

## 11. SQLAlchemy

**Q89. What is SQLAlchemy?**
A Python SQL toolkit and ORM. It gives one API for different databases (MySQL, SQLite, PostgreSQL).

**Q90. Core vs ORM?**
Core works with tables and SQL expressions. The ORM maps Python classes to tables. The notebooks use Core (`Table`, `MetaData`).

**Q91. What is an engine?**
The object that manages connections to the database, created with `create_engine(url)`.

---

## 12. Flask

**Q92. What is Flask?**
A lightweight Python web framework. It handles routes, requests and templates, and leaves the rest to extensions.

**Q93. How does a request flow?**
Browser sends a request, Flask matches the URL to a route function, the function queries the database, renders a Jinja template and returns HTML.

**Q94. Which routes does the app have?**
`/` dashboard, `/crimes` list with filters and paging, `/crimes/<id>` detail, `/crimes/new`, `/crimes/<id>/edit`, `/crimes/<id>/delete`, `/communities`, `/insights`, `/charts`.

**Q95. How does CRUD map to SQL and HTTP?**
Create is `INSERT` (POST), Read is `SELECT` (GET), Update is `UPDATE` (POST), Delete is `DELETE` (POST).

**Q96. How does the app protect forms?**
A CSRF token is stored in the session and must match the form field on every POST, otherwise the app returns 400. Input is validated (case number unique, date not in the future, foreign keys must exist), and SQL uses `?` placeholders.

**Q97. What is Jinja2?**
The template engine Flask uses. It puts Python values into HTML with `{{ value }}` and control logic with `{% for %}`.

**Q98. What is the Flask `g` object and `teardown_appcontext`?**
`g` stores data during one request (the database connection). The teardown function closes it when the request ends.

**Q99. GET vs POST?**
GET reads data and appears in the URL. POST sends data that changes something and goes in the body.

**Q100. How do you run Flask in production?**
Not with the development server. Use a WSGI server such as Gunicorn or Waitress behind Nginx, set a real `FLASK_SECRET_KEY` and turn debug off.

**Q101. How are errors shown?**
Error handlers for 400, 404 and 503 render `error.html` with a clear message.

---

## 13. Testing

**Q102. What do the tests check?**
The website pages return 200, a POST without a CSRF token returns 400, an unknown crime returns 404, database keys have no orphans, case numbers are unique, the `crime` table has 498 rows and 23 types, text columns are upper case, the views match the table and the report files exist.

**Q103. Why test data, not only code?**
Wrong data gives wrong analysis even when the code runs. Data tests catch broken joins and duplicates.

**Q104. How do you run the tests?**
`python -m pytest tests`.

---

## 14. AWS

**Q105. How could this project run on AWS?**
Store CSVs in S3, run the database on Amazon RDS for MySQL, run the Flask app on EC2 (or Elastic Beanstalk, or a container on ECS), keep secrets in Secrets Manager, and run notebooks in SageMaker.

**Q106. What is S3?**
Object storage for files with high durability. It is used for raw data, backups and reports.

**Q107. What is RDS and why use it instead of MySQL on EC2?**
A managed relational database. AWS handles backups, patching, failover (Multi-AZ) and read replicas.

**Q108. What is EC2?**
Virtual servers. You choose the size and operating system and manage them yourself.

**Q109. What is Lambda?**
Serverless functions that run on events (a file lands in S3) and are billed per run time.

**Q110. What is IAM?**
The service for users, roles and permissions. Follow least privilege: give only the access that is needed.

**Q111. What are Glue, Athena and Redshift?**
Glue is a managed ETL and data catalog service. Athena runs SQL directly on files in S3. Redshift is a data warehouse for large analytical queries.

**Q112. What is a VPC and a security group?**
A VPC is a private network in AWS. A security group is a firewall for an instance: for example, allow port 3306 only from the web server.

**Q113. How do you keep the database password safe?**
Use environment variables or AWS Secrets Manager, never put it in code or Git. The project reads it from `.env`, which is in `.gitignore`.

**Q114. What is the difference between horizontal and vertical scaling?**
Vertical means a bigger machine. Horizontal means more machines behind a load balancer.

---

## 15. Big data

**Q115. What is big data?**
Data too large or fast for one machine and normal tools. It is described with the 5 Vs: volume, velocity, variety, veracity and value.

**Q116. Is this dataset big data?**
No. 498 rows fit in memory easily. The full Chicago crime dataset has millions of rows, which Pandas can still handle on one machine with enough memory, or in chunks.

**Q117. What is Hadoop?**
A framework with HDFS (distributed storage) and MapReduce (distributed processing) running on clusters.

**Q118. What is Spark and why is it faster than MapReduce?**
A distributed engine that keeps data in memory across steps, while MapReduce writes to disk between steps. PySpark gives a DataFrame API like Pandas.

**Q119. How would this analysis look in PySpark?**
`spark.read.csv(path, header=True)`, then `df.groupBy("year").count()` and `df.groupBy("primary_type").count().orderBy("count", ascending=False)`.

**Q120. What is partitioning?**
Splitting data by a key (such as year) so queries read only the needed parts. It is used in files (Parquet folders by year) and tables.

**Q121. Why is Parquet better than CSV?**
It is columnar and compressed, stores types, and lets engines read only the needed columns.

**Q122. What is ETL vs ELT?**
ETL transforms data before loading it. ELT loads raw data first and transforms it inside the warehouse. Notebook 01 is an ETL step.

**Q123. Data warehouse vs data lake?**
A warehouse holds structured, modelled data for reporting (star schema). A lake holds raw data in any format at low cost (S3).

**Q124. What is batch vs stream processing?**
Batch processes stored data at intervals. Streaming processes events as they arrive (Kafka, Spark Streaming).

**Q125. What is the CAP theorem?**
A distributed system cannot guarantee consistency, availability and partition tolerance all at once. During a network partition it must choose consistency or availability.

---

## Tips for the viva

* Say the limits of the data first (sample, few dates, no time of day). It shows you understand what the results can and cannot say.
* Explain choices, not only code: explicit date format, upper case, not filling coordinates, including zero-crime areas in the mean.
* Be ready to open a notebook and show the cell that answers a question.
