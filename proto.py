from datetime import datetime, timedelta

# Define two datetime objects
prev_date = datetime(1970, 1, 1, 22, 0, 0)
curr_date = datetime(1970, 1, 1, 1, 0, 0)

# Calculate the time difference
time_difference = prev_date - curr_date

if time_difference < timedelta(hours=10):

        print(True)

