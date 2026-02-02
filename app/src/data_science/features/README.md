[Whimsical](https://whimsical.com/treasury-forecasting-features-AraH53BCbXwJMTbMAfSksw)



![img](../../images/features_dag.png)


# Feature List

Here is the list of features that need to be implemented:


- Standard time series features:
  - [ ] day of the week
  - [ ] day of the month
  - [ ] day of the year
  - [ ] month
  - [ ] year
  - [ ] week
  - [ ] workday
  - [ ] is_weekend
  - [ ] is_holiday
  - [ ] is_first_day_of_month
  - [ ] is_last_day_of_month
  - [ ] is_mid_month
  - [ ] is_quarter_start
  - [ ] is_quarter_end
  

- [ ] Calendar features:
  - [ ] distance since previous holiday
  - [ ] distance until next holiday
  - [ ] distance since previous first work day of month
  - [ ] distance until next first work day of month
  - [ ] distance since previous last work day of month
  - [ ] distance until next last work day of month
  - [ ] distance since previous mid-month work day
  - [ ] distance until next mid-month work day


- rolling average features:
  - [ ] rolling `average` of the X previous 'last day of month' values [3, 6, 12, 24] (if we predict another day of the month, we can use that day - should use reference day)
  - [ ] rolling `std` of the X previous 'last day of month' values [3, 6, 12, 24] (if we predict another day of the month, we can use that day - should use reference day)
  - [ ] rolling `max` of the X previous 'last day of month' values [3, 6, 12, 24] (if we predict another day of the month, we can use that day - should use reference day)
  - [ ] rolling `min` of the X previous 'last day of month' values [3, 6, 12, 24] (if we predict another day of the month, we can use that day - should use reference day)
  - [ ] rolling `sum` of the X previous 'last day of month' values [3, 6, 12, 24] (if we predict another day of the month, we can use that day - should use reference day)
  - [ ] rolling `median` of the X previous 'last day of month' values [3, 6, 12, 24] (if we predict another day of the month, we can use that day - should use reference day)

  - [ ] rolling `average` of the previous X days before the reference day [X=4, 9, 14] (excluding weekends)
  - [ ] rolling `average` of the previous X days before the reference day [X=4, 9, 14] (including weekends)
  - [ ] rolling `std` of the previous X days before the reference day [X=4, 9, 14] (excluding weekends)
  - [ ] rolling `std` of the previous X days before the reference day [X=4, 9, 14] (including weekends)
  - [ ] rolling `max` of the previous X days before the reference day [X=4, 9, 14] (excluding weekends)
  - [ ] rolling `max` of the previous X days before the reference day [X=4, 9, 14] (including weekends)
  - [ ] rolling `min` of the previous X days before the reference day [X=4, 9, 14] (excluding weekends)
  - [ ] rolling `min` of the previous X days before the reference day [X=4, 9, 14] (including weekends)
  - [ ] rolling `sum` of the previous X days before the reference day [X=4, 9, 14] (excluding weekends)
  - [ ] rolling `sum` of the previous X days before the reference day [X=4, 9, 14] (including weekends)
  - [ ] rolling `median` of the previous X days before the reference day [X=4, 9, 14] (excluding weekends)
  - [ ] rolling `median` of the previous X days before the reference day [X=4, 9, 14] (including weekends)

- [] Seasonality features:
  - [ ] sine and cosine of the day of the week
  - [ ] sine and cosine of the day of the month
  - [ ] sine and cosine of the week of the year
  - [ ] sine and cosine of the month of the year

- [] Time series features (only for the last business day of the month):
  - [ ] time series age: number of days since the first observation by dimension
  - [ ] recency: number of days since the last observation by dimension
  - [ ] frequency: number of observations by dimension
  - [ ] trend: linear regression coefficient for the time series

