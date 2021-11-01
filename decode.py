import sys
import logging
from configparser import ConfigParser
from watchdog.observers import Observer
from file_handler import Handler
from funtions import validate_dirs


class Decode:
    def __init__(self):
        # initialise config
        self.config = ConfigParser()
        self.config.read('settings.cfg')
        self.monitor_dir = self.config['file_paths']['output_dir']

        # initialise basic logging to stdout and monitor.log
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler("logs/decode.log"),
                logging.StreamHandler()
            ]
        )

        # create event handler
        self.event_handler = Handler(self.monitor_dir)

        # initialise observer
        self.observer = Observer()

    def run(self):
        # run validation
        self.validation()

        # start directory observer
        self.observer.schedule(self.event_handler, self.monitor_dir, recursive=False)
        self.observer.start()

        try:
            while self.observer.is_alive():
                self.observer.join(1)
        finally:
            self.observer.stop()
            self.observer.join()

    def validation(self):
        """
        Run validation of monitor directory,...
        :return: boolean
        """
        logging.info("Running validation")
        # validate monitor dir
        if not validate_dirs(self.monitor_dir):
            # prevent program from running, as this is a prereq to other functions
            logging.critical(f"Failed to validate dir: {self.monitor_dir}")
            sys.exit(f"Failed to validate dir: {self.monitor_dir}")
        else:
            logging.info(f"Monitor directory validated")

        validate_dirs('tmp')
        validate_dirs('filtered')


if __name__ == "__main__":
    Decode().run()
