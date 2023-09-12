import re
from datetime import datetime, timedelta
import argparse
import threading

import Levenshtein as lev
import pandas as pd
import tabula as tb

from logs import log_init, debug_status, log, Status


# Constants
DEBUG_DF_LEN = 50
NUM_KEYWORDS_THES = 2
CLIPPING_UNITS = 5

COL_NAMES = ["Date", "Street", "On Time", "Off Time", "Duration"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
STREETS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"]
TIMING = ["01:00", "05:00", "07:00", "10:00", "13:00", "16:00", "19:00", "22:00"]

ALIGN = "AP"


# Tweak_area helper Functions
def extract_pdf(path: str, adjusted_area: list) -> pd.DataFrame:
    	return pd.concat(tb.read_pdf(path,
                                     pages="all",
                                     area=adjusted_area,
                                     pandas_options={"header": None},
                                     lattice=True,
                                     multiple_tables=True),
                    		     ignore_index=True)

def find_keyword(keyword: str, df: pd.DataFrame, expand_right: bool) -> bool:
	how_many = 0
	first_column = df.iloc[:, 0]

	if ";" in keyword:
		seperated = keyword.split(";")
		keyword = seperated[0]

	if not expand_right:
		first_column = df.iloc[:, -1]
		if ";" in keyword: keyword = seperated[1]

	for row in first_column:
		if re.search(rf'\b{keyword}\b', str(row), re.IGNORECASE):
			how_many += 1
	
	if how_many >= NUM_KEYWORDS_THES: 
		return True
	return False

# This function begins by extracting data from the right side with a ball park area (bpa), It then refines this area of interest (AOI) through   
# iterations while checking each column for specific keywords. If it finds two or more keywords in a single column, it starts shrinking the area 
# from the left side. This iterative process continues until it obtains a single-column extraction with the best-defined area of interest.
#	  
#	|  bpa --> AOI <-- bpa  |
#
def tweak_area(df: pd.DataFrame, path: str, keyword: str, area: list, expected_columns: int, expand_right: bool) -> pd.DataFrame:

	if find_keyword(keyword, df,expand_right ) and len(df.columns) == expected_columns:
		return df

	if expand_right: 
		if find_keyword(keyword, df, expand_right):
			expand_right = False

		df = extract_pdf(path, area)
		area[1] += CLIPPING_UNITS #--------> AOI
		log.debug(f"{keyword} - expand right - {area}")
		return tweak_area(df, path, keyword, area, expected_columns, expand_right)

	df = extract_pdf(path, area)
	area[3] -= CLIPPING_UNITS # AOI <--------
	log.debug(f"{keyword} - expand left - {area}")
	return tweak_area(df, path, keyword, area, expected_columns, expand_right)

# This function processes a DataFrame of dates, identifying the first occurrence of a "marker" date. It then replaces the marker date with a 
# corrected date derived from the next valid date, considering the date offset. The function logs and returns the first corrected date as a string.
def get_first_date(date: pd.DataFrame) -> str:
	search_value = "marker"
	valid_date_indices = []
	marker_indices = []

	if date.at[0, "Date"] != search_value:
		log.debug(f"Date - 1st date is not a marker - {date.at[0, 'Date']}")
		return date.at[0, "Date"]
	
	marker_indices = date.index[date["Date"] == search_value].tolist()
	valid_date_indices = date.index[date["Date"] != search_value].tolist()

	for _ in marker_indices:
		if _ != len(date) - 1: # dont care about the last date
			next_valid_idx = min(list(filter(lambda x: x > _, valid_date_indices)))
			valid_date = datetime.strptime(date.at[next_valid_idx, "Date"], '%d-%m-%Y')

			corrected = valid_date - timedelta(days=next_valid_idx - _)

			date.at[_, "Date"] = corrected.strftime('%d-%m-%Y')

	log.debug(f"Date - 1st date after substituting marker - {date.at[0, 'Date']}")
	return date.at[0, "Date"]

def convert_to_24_hours(time_str: str) -> str:
	if re.match(r'\d{1,2}:\d{2};[APap][Mm]', time_str):
		time_12h = datetime.strptime(time_str, '%I:%M;%p')
		time_24h = time_12h.strftime('%H:%M')
		return time_24h
	return time_str

# This function generates a DataFrame of structured dates based on input DataFrames for streets and time, and a given correction date. 
# It splits the streets into two groups, applies a day increment, and generates dates accordingly. Dates are incremented alternately for 
# the two street groups, and the resulting dates are returned in a DataFrame.
def add_structured_dates(street: pd.DataFrame, time: pd.DataFrame, corr_date: datetime) -> pd.DataFrame:
	date = datetime.strptime(corr_date, '%d-%m-%Y')

	# spliting the STREETS list into two groups and masking them
	mask_group_one = street.isin(STREETS[:7]).any(axis=1)
	mask_group_two = street.isin(STREETS[7:]).any(axis=1)

	day_incre = timedelta(days=1)
	generated_dates = []
	incre_date = False

	for _ in range(len(street)):
		if mask_group_one[_]:
			if incre_date:
				date += day_incre
				incre_date = False
			generated_dates.append(date.strftime('%d-%m-%Y'))

		elif mask_group_two[_]:
			if not incre_date:
				date += day_incre
				incre_date = True
			generated_dates.append(date.strftime('%d-%m-%Y'))

	date_df = pd.DataFrame({"Date": generated_dates})
	return date_df

# This function adjusts the "Duration" column in a DataFrame of date and time records. It computes the time difference between "On Time" 
# and "Off Time," handles cases where "Off Time" spans the next day, and updates the "Duration" column to match the calculated hours. 
# If the "Duration" aligns with the calculation, it remains unchanged; otherwise, it's modified. Any trailing ".0" in the "Duration" column 
# is also removed.
def correct_duration(date: pd.DataFrame) -> pd.DataFrame:
	time_format = "%Y-%m-%d %H:%M"
	dummy_date = '1970-01-01'  # just for time calculation
	
	for _ in range(len(date)):
		duration = date.at[_, "Duration"]

		if duration == ALIGN:
			continue

		time_on = datetime.strptime(dummy_date + " " + date.at[_, "On Time"], time_format)
		time_off = datetime.strptime(dummy_date + " " + date.at[_, "Off Time"], time_format)

		if time_off < time_on: 
			time_off += timedelta(days=1)

		diff = time_off - time_on

		diff_seconds = diff.total_seconds()
		diff_hours = diff_seconds / 3600 # 60min * 60sec = total secs in 1 hr

		if float(duration) - diff_hours != 0:
			print(str(diff_hours))
			date.at[_, "Duration"] = re.sub(r'.0', '', str(diff_hours))
	return date

# This function merges data from three DataFrames (date, street, and time) based on alignment markers, combining sections of data between 
# markers, aligning rows using their indices, and returning the result.
def merge_from_alignment(date: pd.DataFrame, street: pd.DataFrame, time: pd.DataFrame) -> pd.DataFrame:
	temp_1 = []
	temp_2 = []

	strt_indices = street.index[street["Street"] == ALIGN].tolist()
	time_indices = time.index[time["On Time"] == ALIGN].tolist()

	# stopping points
	strt_indices.append(len(street))
	time_indices.append(len(time))

	for _ in range(len(strt_indices) - 1):
		street_sect = street.iloc[strt_indices[_] + 1:strt_indices[_ + 1]]
		temp_1.append(street_sect)

		time_sect = time.iloc[time_indices[_] + 1:time_indices[_ + 1]]
		temp_2.append(time_sect)

	merged_df = pd.merge(pd.concat(temp_1, axis=0), pd.concat(temp_2, axis=0), left_index=True, right_index=True, how='outer')
	merged_df = merged_df.reset_index(drop=True)

	merged_df = pd.concat([date, merged_df], axis=1)
	return merged_df

# This class provides methods for cleaning and formatting data in a DataFrame. It is designed to handle data with specific formatting issues such as 
# noise, carriage returns, double characters, and malformed dates, streets, and timings. The methods either remove the irrelevant data or mark malformed 
# data for further processing. 
class CleanData:
	def __init__(self):
		pass

	def _remove_noise(self, elem: str) -> str:
		elem = str(elem).lower().replace(";", ":").replace(",", ";").replace("hours", "").replace("hour", "").replace("am", "AM").replace("pm", "PM")
		# all characters except '/r', alphabets, numbers, colons and semi-colons are removed
		elem = re.sub(r'[^a-zA-Z0-9:;.\s]|(?!/r)', '', str(elem)).strip()
		return elem

	def _fix_carriage_return(self, df: pd.DataFrame) -> pd.DataFrame:
		num_of_cols = df.shape[1]

		for col in range(num_of_cols):
			df[col] = df[col].str.split('\r')
			df = df.explode(col)

		df.reset_index(drop=True, inplace=True)
		return df

	def _fix_double_chars(self, elem: str) -> str:
		elem = re.sub(r"\s+", "", elem)
		elem = re.sub(r";+", ";", elem)
		return elem

	def _add_alignment(self, elem: str) -> str:
		col_names_lower = [col.lower().replace(" ", "") for col in COL_NAMES]
		if elem in col_names_lower:
			return ALIGN # alignment point 
		return elem

	#########  MIGHT NEED MORE WORK  ######### 
	def _checking_malformed_date(self, date: str) -> str:
		if re.match(r'^\d{2};[a-zA-Z]+;\d{4}$', date):  
			split_date = date.split(';')
			
			corrected_month = min(MONTHS, key=lambda x: lev.distance(x.lower(), split_date[1]))
			numerical_month = MONTHS.index(corrected_month.title()) + 1 # cuz list index starts from 0
			
			split_date[1] = str(numerical_month)
			return "-".join(split_date)	
		return "marker" # leaving marker where date is malformed

	def _checking_malformed_street(self, street: str) -> str:
		if street == ALIGN:
			return street

		elif street in STREETS:
			return street 
		return None

	def _checking_malformed_timing(self, time: str) -> str:
		time = time.strip(";")
		
		if time == ALIGN or re.match(r'^\d{1}$|^\d{1}\.\d{1}$', time):
			return time
		
		elif re.match(r'^(0?[1-9]|1[0-2]):[0-5][0-9][apAP][mM]$', time):
			split_time = time[:-2]  
			am_pm = time[-2:]
			return f"{split_time};{am_pm}"
		return None
	 
	def clean_date(self, date: pd.DataFrame) -> pd.DataFrame:
		date = date.map(self._remove_noise)
		date = self._fix_carriage_return(date)
		date = date.map(self._fix_double_chars)

		date = date[date[0] != "Date".lower()]
		date = date.reset_index(drop=True)

		date = date.map(lambda x: x.split(";", 1)[1].rstrip(';'))
		date = date.map(self._checking_malformed_date)
		date.rename(columns={0 : "Date"}, inplace=True)
		return date

	def clean_street(self, street: pd.DataFrame) -> pd.DataFrame:
		street = street.map(self._remove_noise)
		street = self._fix_carriage_return(street)
		street = street.map(self._fix_double_chars)
		street = street.map(self._add_alignment)

		street = street.map(self._checking_malformed_street)
		street = street.dropna()
		street = street.reset_index(drop=True)
		street = street.rename(columns={0 : "Street"})
		return street

	def clean_time(self, time: pd.DataFrame) -> pd.DataFrame:
		time = time.map(self._remove_noise)
		time = self._fix_carriage_return(time)
		time = time.map(self._fix_double_chars)
		time = time.map(self._add_alignment)
		
		time = time.map(self._checking_malformed_timing)
		time = time.dropna()
		time = time.reset_index(drop=True)
		time = time.rename(columns={0 : "On Time", 1 : "Off Time", 2 : "Duration"})
		return time

# This class verifies data integrity in a combined DataFrame, including street matching, date incrementation, and timing validation. 
# It logs critical messages for failed verifications.
class VerifyData:
	def __init__(self):
		pass

	def _veri_street(self, street_sect: pd.DataFrame) -> bool:
		veri_strt = 0

		for _ in street_sect:
			if _ in STREETS:
				veri_strt += 1
		
		if veri_strt == len(street_sect):
			return True
		return False

	def _veri_dates(self, dates_sect: pd.DataFrame) -> bool:
		prev_date = datetime.strptime(dates_sect.iat[0], '%d-%m-%Y')

		for _ in range(1, len(dates_sect)):
			curr_date = datetime.strptime(dates_sect.iat[_], '%d-%m-%Y')
			diff = curr_date - prev_date # using the bigger minus smaller date to measure diff of 1

			if diff == timedelta(days=0): # avoid false trigger on date stretching
				continue
			
			if diff != timedelta(days=1):
				return False
			
			prev_date = curr_date
		return True

	def _veri_time(self, time_sect: pd.DataFrame) -> bool:
		valid_timing = 0
		
		for _ in time_sect["On Time"]:
			if _ in TIMING: valid_timing += 1
		
		if valid_timing != len(time_sect):
			return False
		return True
	
	def analyse(self, combined: pd.DataFrame) -> pd.DataFrame:
		if not self._veri_street(combined["Street"]):
			log.critical("Street - Street elements do not match predefined street numbers")

		if not self._veri_dates(combined["Date"]):
			log.critical("Date - Dates are not incremented by one")

		if not self._veri_time(combined):
			log.critical("Time - Timing do not match duration values")


def main():		
	# Debug format: LINE NUMBER - DATAFRAME - DOING WHAT? - ANY VALUE CHANGES IN PROGRESS OR PASS/FAIL
	log_init(log.DEBUG)

	parser = argparse.ArgumentParser(description='Extracts data from water schedule')
	parser.add_argument('-t', type=int, help='1-6: Select the pdf to test')
	args = parser.parse_args()

	test_num = args.t

	# Ball park areas and column sizes for each dataframe
	date_area_col   = ([40, 100, 920, 300], 1)
	street_area_col = ([40, 220, 920, 360], 1)
	timing_area_col = ([40, 275, 920, 830], 3)

	path = f"samples/test{test_num}.pdf"	
	unprocs = {}
	log.debug(f"Processing data of {path[8:]}: ")

	try: 
		date_thread = threading.Thread(target=lambda: unprocs.update({"date": tweak_area(extract_pdf(path, 
													     date_area_col[0]), 
													     path, 
													     "Date", 
													     date_area_col[0], 
													     date_area_col[1], 
													     expand_right=True)}))
		
		street_thread = threading.Thread(target=lambda: unprocs.update({"street": tweak_area(extract_pdf(path, 
														 street_area_col[0]), 
														 path, 
														 "Street", 
														 street_area_col[0], 
														 street_area_col[1], 
														 expand_right=True)}))
		
		timing_thread = threading.Thread(target=lambda: unprocs.update({"time": tweak_area(extract_pdf(path, 
														 timing_area_col[0]), 
														 path, 
														 "On Time;Duration", 
														 timing_area_col[0], 
														 timing_area_col[1], 
														 expand_right=True)}))
		
		date_thread.start()
		street_thread.start()
		timing_thread.start()

		threads = [date_thread, street_thread, timing_thread]

		for thread in threads:
			thread.join()

	except:
		status = Status.FAIL
	else:
		status = Status.PASS
	debug_status("ALL - Tweaking area to extract correct data", status)

	try:
		Cleaning  = CleanData()
		date_clean  = Cleaning.clean_date(unprocs["date"])
		street_clean = Cleaning.clean_street(unprocs["street"])
		time_clean = Cleaning.clean_time(unprocs["time"])

	except:
		status = Status.FAIL
	else:
		status = Status.PASS
	debug_status("ALL - Cleaning and formatting data", status)

	try:
		date_corrected = get_first_date(date_clean)
		generated_dates = add_structured_dates(street_clean, time_clean, date_corrected)

		time_converted = time_clean.map(convert_to_24_hours)
		time_duration_corrected = correct_duration(time_converted)
	
		combined = merge_from_alignment(generated_dates, street_clean, time_duration_corrected)
		
	except ValueError as ve:
		print(ve)
		status = Status.FAIL
	else:
		status = Status.PASS
	debug_status("ALL - Process date and time data for structured output using street and date information", status)

	try:
		Verifying = VerifyData()
		Verifying.analyse(combined)

	except ValueError as ve:
		print(ve)
		status = Status.FAIL
	else:
		status = Status.PASS
	debug_status("ALL - Verifying every element of df via their required methods", status)
	
	print(combined.head(DEBUG_DF_LEN))
	

if __name__ == "__main__":
	main()
