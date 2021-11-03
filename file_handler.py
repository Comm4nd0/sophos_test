import logging
import magic
import pyminizip
from watchdog.events import FileSystemEventHandler
from configparser import ConfigParser
from datetime import datetime
from os import path, remove, mkdir, chmod, getcwd, chdir
from glob import glob
from stat import *
from commonregex import CommonRegex
from re import findall
from json import loads, dumps
from json.decoder import JSONDecodeError

logger = logging.getLogger(__name__)


class Handler(FileSystemEventHandler):
    def __init__(self, monitor_dir):
        self.config = ConfigParser()
        self.config.read('settings.cfg')
        self.monitor_dir = monitor_dir
        self.cwd = getcwd()

    def on_any_event(self, event):
        event_types = ("created", "moved")

        if event.is_directory:
            return None

        if event.event_type in event_types:
            logger.debug(f"Event: {event.event_type} - {event.src_path}")
            # Event is created, you can process it now
            logger.info("File detected - % s." % event.src_path)

            # ensure detected file mime type is allowed and has contents.
            mime = magic.Magic(mime=True)
            try:
                if mime.from_file(event.src_path) in self.config['files']['allowed_file_types'] and \
                        self.monitor_dir in event.src_path:
                    logger.info(f"Mime type verified: Text file")
                    # prepare output dir
                    self.prep_output_dir()
                    # start zip process
                    self.create_zip(event.src_path)
                elif mime.from_file(event.src_path) in self.config['files']['allowed_compression_file_types'] and \
                        self.monitor_dir in event.src_path:
                    logger.info(f"Mime type verified: Compressed file")
                    # unzip_file and extract
                    self.unzip_file(event.src_path)
                    # run pii filter and save PII_filter_<original_file_name>_.txt
                    self.pii_filter()
                else:
                    logger.critical(f"Detected file not in scope for processing")
                    return None
            except FileNotFoundError:
                # file has been removed since initial detection
                logger.warning(f"File has been removed during processing: {event.src_path}")
                return None

        else:
            return None

    def prep_output_dir(self):
        """
        Validate directory exits and empty prior to creating zip
        :return: True
        """
        logging.info("Preparing output directory")

        if path.exists(self.config['file_paths']['output_dir']):
            # iterate over any existing files and delete
            existing_files = glob(path.join(self.config['file_paths']['output_dir'], "*.zip"))
            for file in existing_files:
                logging.debug(f"Deleting {file} from output directory")
                try:
                    remove(file)
                except Exception as error:
                    # catch any system level errors
                    logging.warning(f"Unable to delete {file}, see debug for more information")
                    logging.debug(error)
        else:
            # create directory
            mkdir(self.config['file_paths']['output_dir'])

    def create_zip(self, file):
        """
        Create zip file and store in output directory with YYYY_MM_DD_hh_mm_ss_am/pm date format
        :return: True
        """
        date = datetime.now()
        time_stamp = date.strftime("%Y_%m_%d_%I_%M_%S_%p")
        output_path = path.join(self.config['file_paths']['output_dir'], f"{time_stamp}.zip")
        try:
            pyminizip.compress(file, None, output_path, time_stamp, 1)
            # set 755 permissions on .zip
            chmod(output_path, S_IRUSR | S_IWUSR | S_IXUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH)
            logger.info(f"New zip file created for later decoding: {output_path}")
        except Exception as error:
            # catch any error that might happen from system e.g. permission/disk space errors
            logger.critical("Unable to creat zip file. See debug for more information")
            logger.debug(error)

    def unzip_file(self, file):
        """
        Obtain password from detected file(.zip) name.
        uncompress file and output to same directory.
        :param file: string: detected file path to unzip
        :return: None
        """
        password = path.splitext(path.basename(file))[0]
        pyminizip.uncompress(file, password, "tmp/", 0)

        # ensure working directory is returned to root of program
        chdir(self.cwd)

    def pii_filter(self):
        """
        Open file and run PII filter.
        Save file to same directory but with filter applied.
        :param file: string: path to file requiring filter
        :return: Boolean
        """
        files_to_process = glob(path.join(getcwd(), "tmp/*"))
        logging.debug(files_to_process)
        for file in files_to_process:
            logging.info(f"Running PII filtering on: {file}")
            with open(file, 'rb') as file_raw:
                file_contents_encoded = file_raw.read()

            parsed_text = CommonRegex(file_contents_encoded.decode("utf-8").replace(" ", ""))
            file_contents = file_contents_encoded.decode("utf-8").replace(" ", "")
            for item in parsed_text.phones:
                file_contents = file_contents.replace(item, "<phone>")
                logging.debug(f"Replaced: {item} - with: <phone>")
            for item in parsed_text.emails:
                file_contents = file_contents.replace(item, "<email>")
                logging.debug(f"Replaced: {item} - with: <email>")
            for item in parsed_text.ips:
                file_contents = file_contents.replace(item, "<ip>")
                logging.debug(f"Replaced: {item} - with: <ip>")

            # custom regex
            # windows users file path
            reg_matches = findall(r"[a-zA-Z]:.*\bUsers.*", file_contents)
            for result in reg_matches:
                split_path = result.split("\\\\")
                replacement_path = f"<d>:\\\\Users\\\\<u>"
                for item in split_path[3:]:
                    replacement_path += f"\\\\{item}"
                file_contents = file_contents.replace(result, replacement_path)
                logging.debug(f"Replaced: {result} - with: {replacement_path}")

            # linux users file path
            reg_matches = findall(r"/home/.*", file_contents)
            for result in reg_matches:
                split_path = result.split("/")
                replacement_path = f"/home/<u>"
                for item in split_path[3:]:
                    replacement_path += f"/{item}"
                file_contents = file_contents.replace(result, replacement_path)
                logging.debug(f"Replaced: {result} - with: {replacement_path}")

            # attempt json loading and look for name key
            try:
                data = loads(file_contents)
                logging.debug("File contains json")
                for object in data:
                    if "name" in object:
                        # potentially name value found
                        logging.info(f"Replaced: {object['name']} - with: <name>")
                        object['name'] = "<name>"
                file_contents = dumps(data)
            except JSONDecodeError:
                # not json content
                logging.debug("File does not contain json")
                pass


            # save filtered file content to new file
            logging.info(f"Creating PII filtered file: {path.join(self.config['file_paths']['output_dir'], f'PII_filtered_{path.basename(file)}')}")
            f = open(path.join(self.cwd, 'filtered', f'PII_filtered_{path.basename(file)}'), "w")
            f.write(file_contents)
            f.close()

            # clean up
            remove(file)
        return True

