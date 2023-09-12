import logging as log
import colorlog
from enum import Enum


class Status(Enum):
    PASS = 1
    FAIL = 2

def log_init(log_lvl) -> None:
	logger = log.getLogger()
	logger.setLevel(log_lvl)  

	dark_grey = '\033[90m' 

	log_formatter = colorlog.ColoredFormatter(
		f'%(bold)s{dark_grey}%(asctime)s %(log_color)s%(levelname)-8s{dark_grey}%(reset)s %(lineno)d - %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S',
		log_colors=
		{
			'DEBUG': 'green',
			'INFO': 'blue',
			'WARNING': 'yellow',
			'ERROR': 'red',
			'CRITICAL': 'bold_white,bg_red'
		}
	)

	handler = log.StreamHandler()
	handler.setFormatter(log_formatter)
	logger.addHandler(handler)

def debug_status(message: str, status_or_value) -> None:
	colour_mapping = {
		Status.PASS: '\033[32m',  # green
		Status.FAIL: '\033[31m',  # red
	}

	status_colour = colour_mapping.get(status_or_value, '')
	reset_colour = '\033[0m'  # reset color to default

	log.debug(f"{message} - {status_colour}{status_or_value.name}{reset_colour}")

