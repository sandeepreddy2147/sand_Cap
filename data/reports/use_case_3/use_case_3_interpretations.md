# Use Case 3 interpretations

## Task 1: Crime intensity by time
All 498 crimes have Hour = 0. The dates in the source file are plain dates such as 5/3/2016 with no time of day, so pandas sets the time to midnight. The line graph is therefore a single spike at that hour and does not show when crimes happen during the day. Data that includes the time of day would give a real hourly curve. The code is ready for it, because it only needs the date column to include the time.

## Task 2: Community area outliers (IQR)
There are 77 community areas with a mean of 6.47 crimes (median 5, standard deviation 5.95). The mean is above the median, so a few high areas pull it up. IQR: Q1 2, Q3 9, upper fence 19.5. 3 area(s) are outliers: Austin (34), Near North Side (20), Humboldt Park (20). 1 are beyond the extreme fence of 30.0. The highest area is Austin with 34 crimes. Counts are raw and not adjusted for population or for the dates the sample covers.

## Task 3: Correlation of numeric features
Strongest pairs overall: beat_num and district_code (+1.00); community_code and latitude (-0.74); district_code and ward_no (+0.72); beat_num and ward_no (+0.72); ward_no and latitude (+0.70). Most of the strong pairs are between location codes (beat, district, ward, community, latitude, longitude). They describe the same place in different ways, so a high value there is expected and says nothing new. Strongest pairs that are not both location columns: Year and DayOfWeekNum (-0.31); Month and DayOfWeekNum (-0.26); DayOfWeekNum and Arrest (+0.19). Arrest is most related to DayOfWeekNum (+0.19), which is weak (below 0.3 in size). Correlation shows that two columns move together, not that one causes the other. Year and Month are tied to the few dates in the sample.
