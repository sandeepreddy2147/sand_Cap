# Use Case 4 interpretations

## Task 1: Summary tables
Created and filled summary_crime_yearly (5 rows), summary_crime_by_category (23 rows) and summary_arrest_yearly (5 rows) through the sqlite connection.

## Task 2: Queries
Crime count per year: 2012: 2; 2013: 1; 2014: 1; 2015: 4; 2016: 490. Top 5 crime types: THEFT 105 (21.08%); BATTERY 85 (17.07%); CRIMINAL DAMAGE 49 (9.84%); OTHER OFFENSE 39 (7.83%); DECEPTIVE PRACTICE 38 (7.63%). Arrests per year: 2012: 2 of 2; 2013: 1 of 1; 2014: 0 of 1; 2015: 2 of 4; 2016: 119 of 490.

## Task 3: Views
vw_crime_yearly and vw_crime_by_category were created and return the same numbers as the Task 2 queries.

## Task 4: Pandas integration
Both views were read with pd.read_sql: vw_crime_yearly has 5 rows and vw_crime_by_category has 23 rows.

## Task 5: Overall
498 crimes in total, 124 with an arrest (24.90%).

## Task 5, Chart 1: Crimes and arrests per year
2016 has the most crimes (490 of 498) and 119 arrests (24.3%). Other years have only 1 to 4 records, so their arrest rates (0% to 100%) are not reliable. The sample covers few dates outside the peak year.

## Task 5, Chart 2: Top crime types
THEFT is the largest type with 105 crimes (21.08%), followed by BATTERY (17.07%). The top 5 types cover 63.45% of all crimes and the top 10 cover 89.55%. The view holds 23 crime types in total.

## Task 5, Chart 3: Monthly crime frequency
11 year-month periods have records. The busiest is 2016-05 with 445 crimes (89.4% of all crimes). The second highest has 22. A single month holding most records shows that the sample covers specific dates, not a full year, so this is not a seasonal pattern.

## Task 5, Chart 4: Top 10 community areas
Austin has the most crimes: 34 (6.8%). The top 10 areas together cover 35.9% of all crimes. These are raw counts, not adjusted for population.

## Task 5, Chart 5: Crimes by police district
22 police districts have crimes. Harrison (district 11) has the most with 40 crimes, and Lincoln has the fewest with 7. The median district has 23.5. Raw counts, not adjusted for district size or population.
