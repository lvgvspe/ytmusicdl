import logging
import os

root = os.path.dirname(os.path.abspath(__file__))

class InfoFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno == logging.INFO

def create_logger(name):
    log_file = os.path.join(root, "app.log")
    error_file = os.path.join(root, "error.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Set logger level to DEBUG

    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Set file handler level to WARNING
    
    # Create error handler
    error_handler = logging.FileHandler(error_file)
    error_handler.setLevel(logging.ERROR)  # Set file handler level to WARNING

    # Create console handler with level INFO
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Set console handler level to DEBUG

    # Create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)
    # console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    # Add InfoFilter to the console handler
    info_filter = InfoFilter()
    console_handler.addFilter(info_filter)

    logger.info(f"Check errors at '{error_file}'.")

    return logger
