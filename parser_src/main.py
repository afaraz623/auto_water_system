import os
import re
import time
import pickle
from datetime import datetime, timedelta

import pandas as pd
import tabula as tb
import Levenshtein as lev
import paho.mqtt.client as mqtt

from logs import log_init, log


# Constants
ATTACHMENT_PATH = 'attachments'
TOPIC = 'parsed_data'
BROKER_IP = '192.168.100.3'
BROKER_PORT = 1883

FIRST_REAL_ROW = 1
SECOND_ROW = 2
COL_NAMES = ['Date', 'Street', 'On Time', 'Off Time', 'Duration']
VALID_STRTS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15']
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

# spliting the valid_strts list into two parts for 'Date' column varification
GROUP_ONE = VALID_STRTS[:7] 
GROUP_TWO = VALID_STRTS[7:]

# Helper Functions
def unscramble_data(t_df, s_df, p_df):
    t_df = t_df.astype(str)
    t_df = t_df.applymap(lambda x: re.sub(r'(^[\s,]+|[\s,]+$)|(\s*,\s*)|hours|hour', '', x).strip().split('\r'))
    t_df = t_df.applymap(lambda lst: [x.replace(';', ':') for x in lst])
    t_df = t_df.applymap(lambda lst: [x.replace('pm', 'PM') for x in lst])
    t_df = t_df.applymap(lambda lst: [x.replace('am', 'AM') for x in lst])
    t_df = t_df.applymap(lambda lst: [x.replace(' ', ':') for x in lst])
    t_df = t_df.explode(0).explode(1).explode(2)

    temp = []
    for strt_num in s_df[0]:
        strt_num = re.sub(r'(^[\s,]+|[\s,]+$)|(\s*,\s*)', '', strt_num).strip()   
        for i in strt_num.split('\r'):
            temp.append(i)

    s_df = pd.DataFrame(temp)

    p_df.drop(1, axis=1, inplace=True)
    p_df = p_df.astype(str)
    p_df = p_df.applymap(lambda x: re.sub(r'(^[\s,]+|[\s,]+$)|(\s*,\s*)|,{2,}', '', x).strip())
    p_df = p_df.applymap(lambda x: re.sub(r'^[^\d]*(?=\d)', '', x))
    p_df = p_df.applymap(lambda x: re.sub(r'(\d{2})([a-zA-Z]+)(\d{4})', r'\1;\2;\3', x))

    # renaming columns of dataframes
    t_df.rename(columns={0 : 'On Time', 1 : 'Off Time', 2 : 'Duration'}, inplace=True)
    s_df.rename(columns={0 : 'Street'}, inplace=True)
    p_df.rename(columns={0 : 'Date'}, inplace=True)

    return [p_df, s_df, t_df]

def check_date(date, index, v_dates):
    if isinstance(date, str):
        if date in ['', 'nan']:
            return date
        
        elif re.match(r'^\d{2};[a-zA-Z]+;\d{4}$', date):
            v_dates.append(index) # appeading valid date indices for further use
            
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
            return 'marker' # leaving marker where date is malformed

def fix_date(df, row, v_dates):
    if row == 1: # if the first date is malformed
        next_date = datetime.strptime(df.loc[v_dates[0], 'Date'], '%d-%m-%Y')
        prev_date = next_date - timedelta(days=1)
        
        return prev_date

    else:
        temp_lst = sorted(v_dates + [row]) # the fucking clever way
        idx = temp_lst.index(row)
        
        prev_date = datetime.strptime(df.loc[temp_lst[idx - 1], 'Date'], '%d-%m-%Y')
        next_date = prev_date + timedelta(days=1)

        return next_date

def convert_time_24(time):
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

def publish_dataframe(broker_ip, broker_port, topic, serialized_data):
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            log.info(f'Connected to MQTT broker with result code: {str(rc)}')

    try:
        client = mqtt.Client('parser')
        client.on_connect = on_connect
        client.connect(broker_ip, broker_port, 60)

        client.loop_start()
        client.publish(topic, serialized_data, qos=0) 
        client.disconnect()
        client.loop_stop()

        return True

    except ValueError as ve:
        log.error(f'Error Cause: {ve}')
        return False


def main():
    log_init(log.DEBUG)
    log.info("parser started!")

    if not os.path.exists(ATTACHMENT_PATH):
        os.makedirs(ATTACHMENT_PATH)

    while True: # main loop
        while True:
            try: 
                file_name = None
                while not any(filename.lower().endswith('.pdf') for filename in os.listdir(ATTACHMENT_PATH)):
                    time.sleep(10) # refreshing every 60 seconds. 10 for debugging
                
                for filename in os.listdir(ATTACHMENT_PATH):
                    if filename.lower().endswith('.pdf'):
                        file_name = filename
                        break

                if file_name:
                    attachment_pdf_path = os.path.join(ATTACHMENT_PATH, f'{file_name}') 
                    log.info(f'{file_name} received')
                
                timing_df = pd.concat(tb.read_pdf(attachment_pdf_path, pages='all', area = (60, 325, 918, 770), pandas_options={'header': None}, lattice=True, multiple_tables=True), ignore_index=True)
                street_df = pd.concat(tb.read_pdf(attachment_pdf_path, pages='all', area = (58, 270, 918, 310), pandas_options={'header': None}, lattice=True, multiple_tables=True), ignore_index=True)
                period_df = pd.concat(tb.read_pdf(attachment_pdf_path, pages='all', area = (60, 150, 918, 250), pandas_options={'header': None}, lattice=True, multiple_tables=True), ignore_index=True)

#--------------------------------------------[Cleaning Data]--------------------------------------------#

                cleaned_df_list = unscramble_data(timing_df, street_df, period_df)
                
                combined_df = pd.concat(cleaned_df_list, axis=1)

                combined_df.iloc[0] = 'nan' # added temporarily to make indices match pdf's
                
                for col in COL_NAMES: # removing extra column names without attacfing index
                    combined_df = combined_df[~combined_df[col].str.contains(col, case=False, na=False)]
                combined_df.reset_index(drop=True, inplace=True)

                verified_dates = []
                for row in range(len(combined_df)):
                    combined_df.loc[row, 'Date'] = check_date(combined_df.loc[row, 'Date'], row, verified_dates)

                for row in range(FIRST_REAL_ROW, len(combined_df)):       
                        if combined_df.loc[row, 'Date'] == 'marker':
                            combined_df.loc[row, 'Date'] = fix_date(combined_df, row, verified_dates).strftime('%d-%m-%Y')

                for col in ['On Time', 'Off Time']:
                    for row in range(FIRST_REAL_ROW, len(combined_df)):
                        combined_df.loc[row, col] = convert_time_24(combined_df.loc[row, col])
                break
            
            except Exception as e:
                log.error(f'Error caused during: {e}')
                
                os.remove(attachment_pdf_path)
                log.info(f'{file_name} deleted!')
                
                continue

#--------------------------------------------[Verifying Data]--------------------------------------------#
        # checking streets
        verified_strts = 0
        street_passed = False

        for strt in combined_df['Street']:
            if strt in VALID_STRTS:
                verified_strts += 1

        if verified_strts == len(combined_df['Street']) - 1: # not counting the 'nan' value in first row
            street_passed = True

        if not street_passed:
            log.critical('Street elements do not match predefined street numbers')

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
        prev_date = datetime.strptime(combined_df.loc[FIRST_REAL_ROW, 'Date'], '%d-%m-%Y')
        for i in range(SECOND_ROW, len(combined_df)):
            curr_date = datetime.strptime(combined_df.loc[i, 'Date'], '%d-%m-%Y')
            diff = curr_date - prev_date # using the bigger date minus smaller date to measure diff of 1

            if diff == timedelta(days=0):
                continue

            if diff != timedelta(days=1):
                log.critical('Dates are not incremented by one.')
            
            prev_date = curr_date

        # checking timing
        time_format = '%Y-%m-%d %H:%M:%S'
        dummy_date = '1970-01-01'  # just for time calculation

        for i in range(FIRST_REAL_ROW, len(combined_df)):
            duration = float(combined_df.loc[i, 'Duration'])

            time_on = datetime.strptime(dummy_date + ' ' + combined_df.loc[i, 'On Time'], time_format)
            time_off = datetime.strptime(dummy_date + ' ' + combined_df.loc[i, 'Off Time'], time_format)

            if time_off < time_on:
                time_off += timedelta(days=1)

            diff = time_off - time_on

            diff_seconds = diff.total_seconds()
            diff_hours = diff_seconds / 3600 # 60min * 60sec = total secs in 1 hr

            if duration - diff_hours != 0:
                try:
                    combined_df.loc[i, 'Duration'] = re.sub(r'.0', '', str(diff_hours))
                except:
                    log.critical(f'Timing do not match duration values. idx: {i-1}')

        # removing the temporary 'nan' row and reseting the index
        combined_df.drop(0, axis=0, inplace=True)
        combined_df.reset_index(drop=True, inplace= True)
        
#--------------------------------------------[Filtering Data]--------------------------------------------#

        filter_target = combined_df['Street'] == '5' # filtering useful data only
        filter_cols = ['Date', 'On Time', 'Duration']
        filtered_df = combined_df[filter_target][filter_cols].copy().reset_index(drop=True)

        serialized_data = pickle.dumps(filtered_df)

        if publish_dataframe(BROKER_IP, BROKER_PORT, TOPIC, serialized_data):
            log.info('published data successful')
        else:
            log.error('published data unsuccessful')
        
        os.remove(attachment_pdf_path)
        log.info(f'{file_name} deleted')


if __name__ == '__main__':
    main()