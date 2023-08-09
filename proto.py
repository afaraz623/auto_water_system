import Levenshtein as lev
from datetime import datetime, timedelta


date_unformatted = '06;Augist;2023'

months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

split_date = date_unformatted.split(';')

temp = []
for part in split_date:
    if part == split_date[1]:
        corrected_month = min(months, key=lambda x: lev.distance(x.lower(), part.lower()))
        corrected_month = datetime.strptime(corrected_month, '%B')
        temp.append(corrected_month.strftime('%m'))
    else:
        temp.append(part)

print('-'.join(temp))