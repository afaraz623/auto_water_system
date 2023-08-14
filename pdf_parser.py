from datetime import datetime, timedelta
import Levenshtein as lev
import pandas as pd
import tabula as tb
import numpy
import os
import re

# files = ['test1.pdf', 'test2.pdf', 'test4.pdf']
file = 'samples/test4.pdf'

timing_data = tb.read_pdf(file, pages='all', area = (60, 325, 918, 770), pandas_options={'header': None}, lattice=True, multiple_tables=True)
street_data = tb.read_pdf(file, pages='all', area = (58, 270, 918, 310), pandas_options={'header': None}, lattice=True, multiple_tables=True)
period_data = tb.read_pdf(file, pages='all', area = (60, 150, 918, 250), pandas_options={'header': None}, lattice=True, multiple_tables=True)

timing_df = pd.concat(timing_data, ignore_index=True)
street_df = pd.concat(street_data, ignore_index=True)
period_df = pd.concat(period_data, ignore_index=True)

####################################[Cleaning Data]#################################### 
timing_df = timing_df.astype(str)
timing_df = timing_df.applymap(lambda x: re.sub(r'(^[\s,]+|[\s,]+$)|(\s*,\s*)|hours|hour', '', x).strip().split('\r'))
timing_df = timing_df.applymap(lambda lst: [x.replace(';', ':') for x in lst])
timing_df = timing_df.applymap(lambda lst: [x.replace('pm', 'PM') for x in lst])
timing_df = timing_df.applymap(lambda lst: [x.replace('am', 'AM') for x in lst])

timing_df = timing_df.applymap(lambda lst: [x.replace(' ', ':') for x in lst])
timing_df = timing_df.explode(0).explode(1).explode(2)

temp = []
for strt_num in street_df[0]:
    strt_num = re.sub(r'(^[\s,]+|[\s,]+$)|(\s*,\s*)', '', strt_num).strip()   
    for i in strt_num.split('\r'):
        temp.append(i)

street_df = pd.DataFrame(temp)

period_df.drop(1, axis=1, inplace=True)
period_df = period_df.astype(str)
period_df = period_df.applymap(lambda x: re.sub(r'(^[\s,]+|[\s,]+$)|(\s*,\s*)|,{2,}', '', x).strip())
period_df = period_df.applymap(lambda x: re.sub(r'^[^\d]*(?=\d)', '', x))
period_df = period_df.applymap(lambda x: re.sub(r'(\d{2})([a-zA-Z]+)(\d{4})', r'\1;\2;\3', x))

# renaming columns and combining dataframes
timing_df.rename(columns={0 : 'On Time', 1 : 'Off Time', 2 : 'Duration'}, inplace=True)
street_df.rename(columns={0 : 'Street'}, inplace=True)
period_df.rename(columns={0 : 'Date'}, inplace=True)

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
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
valid_dates = []

def check_date(date, index):
    if isinstance(date, str):
        if date in ['', 'nan']:
            return date
        
        elif re.match(r'^\d{2};[a-zA-Z]+;\d{4}$', date):
            valid_dates.append(index)
            
            split_date = date.split(';')
            corrected_month = min(MONTHS, key=lambda x: lev.distance(x.lower(), split_date[1].lower()))
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
FIRST_REAL_ROW = 1
for i in range(FIRST_REAL_ROW, len(combined_df)):    
    for x in valid_dates:    
        if combined_df.loc[i, 'Date'] == 'marker':
            if i == FIRST_REAL_ROW:
                combined_df.loc[i, 'Date'] = adjust_date(i).strftime('%d-%m-%Y')
            else:
                combined_df.loc[i, 'Date'] = adjust_date(i).strftime('%d-%m-%Y')

# formating On and Off columns into 24hrs
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

for x in ['On Time', 'Off Time']:
    for i in range(FIRST_REAL_ROW, len(combined_df)):
        combined_df.loc[i, x] = convert_time(combined_df.loc[i, x])

####################################[Verifying Data]#################################### 
# checking streets
VALID_STRTS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15']
verified_strts = 0
street_passed = False

for strt in combined_df['Street']:
    if strt in VALID_STRTS:
        verified_strts += 1

if verified_strts == len(combined_df['Street']) - 1: # not counting the 'nan' value in first row
    street_passed = True

if not street_passed:
    raise ValueError('Street elements do not match predefined street numbers')

# spliting the valid_strts list into two parts for 'Date' column varification
GROUP_ONE = VALID_STRTS[:7]
GROUP_TWO = VALID_STRTS[7:]

# matching street numbers with designated dates and extending the dates to their respective rows
date = datetime.strptime(combined_df.loc[1, 'Date'], '%d-%m-%Y') 
incre_date = False

for i in range(len(combined_df)):
    street_number = combined_df['Street'].iloc[i]

    if street_number in GROUP_ONE:
        if incre_date:
            date += timedelta(days=1)
            incre_date = False
        combined_df.loc[i, 'Date'] = date.strftime('%d-%m-%Y')

    elif street_number in GROUP_TWO:
        if not incre_date:
            date += timedelta(days=1)
            incre_date = True
        combined_df.loc[i, 'Date'] = date.strftime('%d-%m-%Y')

# checking dates
# using the bigger date minus smaller date to measure diff of 1
prev_date = datetime.strptime(combined_df.loc[FIRST_REAL_ROW, 'Date'], '%d-%m-%Y')
SECOND_ROW = 2

for i in range(SECOND_ROW, len(combined_df)):
    curr_date = datetime.strptime(combined_df.loc[i, 'Date'], '%d-%m-%Y')
    diff = curr_date - prev_date

    if diff == timedelta(days=0):
        continue

    if diff != timedelta(days=1):
        raise ValueError('Dates are not incremental by one.')
    
    prev_date = curr_date

# checking timing
time_format = '%Y-%m-%d %H:%M:%S'
default_date = '1970-01-01'  # just for time calculation

for i in range(FIRST_REAL_ROW, len(combined_df)):
    duration = float(combined_df.loc[i, 'Duration'])

    time_on = datetime.strptime(default_date + ' ' + combined_df.loc[i, 'On Time'], time_format)
    time_off = datetime.strptime(default_date + ' ' + combined_df.loc[i, 'Off Time'], time_format)

    if time_off < time_on:
        time_off += timedelta(days=1)

    diff = time_off - time_on

    diff_seconds = diff.total_seconds()
    diff_hours = diff_seconds / 3600

    if duration - diff_hours != 0:
        try:
            combined_df.loc[i, 'Duration'] = re.sub(r'.0', '', str(diff_hours))
        except:
            print(f'Timing do not match duration values. idx: {i-1}')

combined_df.drop(0, axis=0, inplace=True)
combined_df.reset_index(drop=True, inplace= True)

####################################[Filtering Data]#################################### 
# filtering only useful data
filter_target = combined_df['Street'] == '5'
filter_cols = ['Date', 'On Time', 'Duration']
filtered_df = combined_df[filter_target][filter_cols].copy().reset_index(drop=True)

print(filtered_df)

filtered_df.to_csv('result.csv', encoding='utf-8-sig')


