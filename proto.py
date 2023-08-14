import Levenshtein as lev
from datetime import datetime, timedelta
import calendar
import pandas as pd
import re

data = { 'Timing' : ['12:00:AM', '12:00:PM', '7:00:PM', '1:00:AM', '5:00:AM', '11:00:PM', '10:30:AM'] }

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

for i in range(len(df)):
    df.loc[i, 'Timing'] = convert_time(df.loc[i, 'Timing'])

print(df)