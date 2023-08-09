import os
import re
from datetime import datetime, timedelta
import Levenshtein as lev
import pandas as pd
import tabula as tb

# files = ['test1.pdf', 'test2.pdf', 'test4.pdf']
file = 'test3.pdf'

timing_data = tb.read_pdf(file, pages='all', area = (60, 325, 918, 770), pandas_options={'header': None}, lattice=True, multiple_tables=True)
street_data = tb.read_pdf(file, pages='all', area = (58, 270, 918, 310), pandas_options={'header': None}, lattice=True, multiple_tables=True)
period_data = tb.read_pdf(file, pages='all', area = (60, 150, 918, 250), pandas_options={'header': None}, lattice=True, multiple_tables=True)

timing_df = pd.concat(timing_data, ignore_index=True)
street_df = pd.concat(street_data, ignore_index=True)
period_df = pd.concat(period_data, ignore_index=True)

# cleaning data 
timing_df = timing_df.astype(str)
timing_df = timing_df.applymap(lambda x: re.sub(r'(^[\s,]+|[\s,]+$)|(\s*,\s*)|hours|hour', '', x).strip().split('\r'))
timing_df = timing_df.applymap(lambda lst: [x.replace(';', ':') for x in lst])
timing_df = timing_df.applymap(lambda lst: [x.replace('pm', 'PM') for x in lst])
timing_df = timing_df.applymap(lambda lst: [x.replace('am', 'AM') for x in lst])
timing_df = timing_df.explode(0).explode(1).explode(2)

temp1 = []
for strt_num in street_df[0]:
    strt_num = re.sub(r'(^[\s,]+|[\s,]+$)|(\s*,\s*)', '', strt_num).strip()   
    for i in strt_num.split('\r'):
        temp1.append(i)

street_df = pd.DataFrame(temp1)

period_df.drop(1, axis=1, inplace=True)
period_df = period_df.astype(str)
period_df = period_df.applymap(lambda x: re.sub(r'(^[\s,]+|[\s,]+$)|(\s*,\s*)|,{2,}', '', x).strip())
period_df = period_df.applymap(lambda x: re.sub(r'^[^\d]*(?=\d)', '', x))
period_df = period_df.applymap(lambda x: re.sub(r'(\d{2})([a-zA-Z]+)(\d{4})', r'\1;\2;\3', x))

# renaming columns and combining dataframes
timing_col = { 0 : 'On Time', 1 : 'Off Time', 2 : 'Duration' }
street_col = { 0 : 'Street' }
period_col = { 0 : 'Date'}

timing_df.rename(columns=timing_col, inplace=True)
street_df.rename(columns=street_col, inplace=True)
period_df.rename(columns=period_col, inplace=True)

combined_df = pd.concat([period_df, street_df, timing_df], axis=1)

# fixing extracted colume names in rows without messing up the index
combined_df.iloc[0] = 'nan' # added temporarily
combined_df = combined_df[~combined_df['Date'].str.contains('Date', case=False, na=False)]
combined_df = combined_df[~combined_df['Street'].str.contains('Street', case=False, na=False)]
combined_df = combined_df[~combined_df['On Time'].str.contains('On Time', case=False, na=False)]
combined_df = combined_df[~combined_df['Off Time'].str.contains('Off Time', case=False, na=False)]
combined_df = combined_df[~combined_df['Duration'].str.contains('Duration', case=False, na=False)]
combined_df.reset_index(drop=True, inplace=True)

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
        else:
            return 'marker'

for i in range(len(combined_df)):
    combined_df.loc[i, 'Date'] = check_date(combined_df.loc[i, 'Date'], i)

prev_idx = None
for i in range(1, len(combined_df)):    
    if combined_df.loc[i, 'Date'] == 'marker':
        for x in valid_date_indices:
            if x < i:
                prev_idx = x
        
        prev_date = datetime.strptime(combined_df.loc[prev_idx , 'Date'], '%d-%m-%Y')
        next_date = prev_date + timedelta(days=1)
        
        if next_date.month != prev_date.month:
            next_date = prev_date.replace(day=1) + timedelta(days=1)
        
        combined_df.loc[i, 'Date'] = next_date.strftime('%d-%m-%Y')

# verifying data
valid_strts = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15']
verified_strts = 0
street_passed = False

for strt in combined_df['Street']:
    if strt in valid_strts:
        verified_strts += 1

if verified_strts == len(combined_df['Street']) - 1: # not counting the 'nan' value in first row
    street_passed = True

if not street_passed:
    raise ValueError('Street elements do not match predefined street numbers')

# spliting the valid_strts list into two parts for 'Date' column varification
group_one = valid_strts[:7]
group_two = valid_strts[7:]

date = datetime.strptime(combined_df.loc[1, 'Date'], '%d-%m-%Y') 
incre_date = False

for i in range(len(combined_df)):
    street_number = combined_df['Street'].iloc[i]

    if street_number in group_one:
        if incre_date:
            date += timedelta(days=1)
            incre_date = False
        combined_df.loc[i, 'Date'] = date.strftime('%d-%m-%Y')

    elif street_number in group_two:
        if not incre_date:
            date += timedelta(days=1)
            incre_date = True
        combined_df.loc[i, 'Date'] = date.strftime('%d-%m-%Y')

print(combined_df.head(50))

file = file.replace('.pdf', '.csv')
combined_df.to_csv(file, encoding='utf-8-sig')


