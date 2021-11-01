import sys
import logging
from configparser import ConfigParser
from watchdog.observers import Observer
from file_handler import Handler
from funtions import validate_dirs


class FileMonitor:
    def __init__(self):
        # initialise config
        self.config = ConfigParser()
        self.config.read('settings.cfg')
        self.monitor_dir = self.config['file_paths']['monitor_dir']
        self.output_dir = self.config['file_paths']['output_dir']

        # initialise basic logging to stdout and monitor.log
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler("logs/monitor.log"),
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
        Run validation of directories,...
        :return: boolean
        """
        logging.info("Running validation")
        # validate monitor dir
        if not validate_dirs(self.monitor_dir):
            logging.critical(f"Failed to validate dir: {self.monitor_dir}")
            sys.exit(f"Failed to validate dir: {self.monitor_dir}")
        else:
            logging.info(f"Monitor directory validated")

        # validate output dir
        if not validate_dirs(self.output_dir):
            logging.critical(f"Failed to validate dir: {self.output_dir}")
            sys.exit(f"Failed to validate dir: {self.output_dir}")
        else:
            logging.info(f"Output directory validated")



if __name__ == "__main__":
    FileMonitor().run()
