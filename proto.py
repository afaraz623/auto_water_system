import Levenshtein as lev
from datetime import datetime, timedelta
import calendar
import pandas as pd
import re


date_unformatted = {'Date' : ['31;Augest;2023', '01;September;2023', '02;Smber;2023']}

combined_df = pd.DataFrame(date_unformatted)

# spell correction and formating the date column
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
valid_date_indices = []

def check_date(date, index):
    if isinstance(date, str):
        if date in ['', 'nan']:
            return date
        
        elif re.match(r'^\d{2};[a-zA-Z]+;\d{4}$', date):
            valid_date_indices.append(index)
            
            split_date = date.split(';')
            corrected_month = min(months, key=lambda x: lev.distance(x.lower(), split_date[1].lower()))
            corrected_month = datetime.strptime(corrected_month, '%B')

            temp = []
            for part in split_date:
                if part == split_date[1]:
                    temp.append(corrected_month.strftime('%m'))
                else:
                    temp.append(part)
            return '-'.join(temp)
        
        return 'marker'

for i in range(len(combined_df)):
    combined_df.loc[i, 'Date'] = check_date(combined_df.loc[i, 'Date'], i)

print(combined_df)

def adjust_date(i):
        if x > i:
            idx = x
            next_date = datetime.strptime(combined_df.loc[idx, 'Date'], '%d-%m-%Y')
            prev_date = next_date - timedelta(days=1)
            
            return prev_date

        if x < i:
            idx = x
            prev_date = datetime.strptime(combined_df.loc[idx, 'Date'], '%d-%m-%Y')
            next_date = prev_date + timedelta(days=1)

            return next_date
idx = None
for i in range(len(combined_df)):    
    for x in valid_date_indices:    
        if combined_df.loc[i, 'Date'] == 'marker':
            if i == 0:
                combined_df.loc[i, 'Date'] = adjust_date(i).strftime('%d-%m-%Y')
            else:
                combined_df.loc[i, 'Date'] = adjust_date(i).strftime('%d-%m-%Y')

print(combined_df)