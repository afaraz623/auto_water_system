import logging as log
import colorlog

def log_init(log_lvl):
    logger = log.getLogger()
    logger.setLevel(log_lvl) # setting default level to lowest

    dark_grey = '\033[90m' #defining ANSI escape codes for colour

    # colour formatter with custom color and formatting
    log_formatter = colorlog.ColoredFormatter(
        f'%(bold)s{dark_grey}%(asctime)s %(log_color)s%(levelname)-8s{dark_grey}%(reset)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG' : 'purple',
            'INFO': 'blue',   
            'WARNING': 'yellow',
            'ERROR': 'red', 
            'CRITICAL': 'red'   
        }
    )

    # handler for logging
    handler = log.StreamHandler()
    handler.setFormatter(log_formatter)
    logger.addHandler(handler)