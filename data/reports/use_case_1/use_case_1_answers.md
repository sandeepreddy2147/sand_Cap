# Use Case 1 answers

## Task 1: Load
The file has 498 rows and 20 columns. See the notebook for the first 10 rows and the data types.

## Task 2: Clean
Dates were converted with %m/%d/%Y. location_desc missing values were set to UNKNOWN. Coordinates were left empty where missing. Text columns were stripped and set to upper case.

## Task 4: Missing values
Highest missing percentage is 5.82% (x_coordinate). Columns above 50% missing: none, so none must be dropped.

## Task 5: Database
498 rows were written to the crime table (sqlite).

## Question 1: How many unique crime types exist?
23 unique crime types (primary_type) appear in the 498 crime records. THEFT is the largest with 105 records. The IUCR reference file defines 33 types, and 97 distinct IUCR codes are used.

## Question 2: Are there anomalies in date formats?
Only minor ones. The dates are text such as 5/3/2016 (month/day/year) and 498 of 498 parse with the explicit format %m/%d/%Y. Check results: dates not in M/D/YYYY format: 0; dates that could not be parsed: 0; dates that contain a time of day: 0; dates in the future: 0; update date earlier than crime date: 0; source 'year' different from the year in 'date': 0; dates without zero padding (5/3/2016 instead of 05/03/2016): 497. The only non-standard pattern is the missing zero padding (497 of 498 values), which does not affect parsing. Because no date has a time of day (0 do), every Hour is 0, which matters in Use Case 3. A separate file problem: the last lines of the CSV (file lines [498, 499]) have an unclosed quote in the location column.

## Question 3: Are there obvious outliers?
Yes, in the following measures. Outliers by the IQR rule: x_coordinate: 0; y_coordinate: 0; latitude: 0; longitude: 0; days from crime to update: 59; crimes per day: 11. 0 coordinates fall outside the Chicago bounding box (latitude 41.6 to 42.1, longitude -87.95 to -87.5). The two busiest dates (2016-05-04, 2016-05-03) hold 88.96% of all crimes, which shows the file is a sample that covers a few dates heavily, not the whole city for a full period.
