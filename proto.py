import Levenshtein as lev
from datetime import datetime, timedelta, date
import calendar
import pandas as pd
import re

data = { 'On Time' :  ['12:00:AM', '12:00:PM', '7:00:PM', '1:00:AM', '5:00:AM', '11:00:PM', '10:30:AM'],
         'Off Time' : ['3:00:AM', '3:00:PM', '10:00:PM', '4:00:AM', '9:00:AM', '2:00:AM', '2:30:PM'] }

df = pd.DataFrame(data)

def convert_time(time):
    temp = []
    temp = time.split(':')

    if temp[0] == '12':
        if temp[2] == 'AM':
            temp[0] = '00'
        temp[2] = '00'
    
    elif len(temp[0]) == 1:
        if temp[2] == 'PM':
            temp[0] = str(int(temp[0]) + 12)
        else:
            temp[0] = '0' + temp[0]
        temp[2] = '00'

    if temp[2] == 'PM':
        temp[0] = str(int(temp[0]) + 12)
        
    temp[2] = '00'
    
    return ':'.join(temp)

for col in ['On Time', 'Off Time']:
    for i in range(len(df)):
        df.loc[i, col] = convert_time(df.loc[i, col])

time_format = '%Y-%m-%d %H:%M:%S'
default_date = '1970-01-01'  # You can use any date as a default, just for time calculation
for i in range(len(df)):

    time_on = datetime.strptime(default_date + ' ' + df.loc[i, 'On Time'], time_format)
    time_off = datetime.strptime(default_date + ' ' + df.loc[i, 'Off Time'], time_format)

    if time_off < time_on:
        time_off += timedelta(days=1)

    time_difference_timedelta = time_off - time_on

    time_difference_seconds = time_difference_timedelta.total_seconds()
    time_difference_hours = time_difference_seconds / 3600

    print(time_difference_hours)