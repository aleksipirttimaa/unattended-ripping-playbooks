import datetime
import logging
import uuid
import socket
import sys
from os import path

import requests
from requests.auth import HTTPBasicAuth

UNKNOWN = "unknown"
FORKING_WHIPPER = "forking_whipper"
READING_TOC = "reading_toc"
RIPPING = "ripping"
UPLOADING = "uploading"
UPLOADED = "uploaded"

#STDOUT_FORMAT = "%(slug)s: %(levelname)s %(message)s"
STDOUT_FORMAT = "%(levelname)s %(message)s"

#LOG_FORMAT = "%(asctime)s %(slug)s: %(levelname)s %(message)s"
LOG_FORMAT = "%(asctime)s: %(levelname)s %(message)s"

def session_slug() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M") \
        + "-" + str(uuid.uuid4()).split("-", maxsplit=1)[0]

class UnattendedSession():
    def __init__(self, args):
        self._slug = session_slug()

        self.drive = args.drive

        # paths
        self._log_fn = None
        if args.log_dir:
            self._log_fn = path.abspath(path.join(args.log_dir, self._slug + ".log"))
        self.new_path = path.abspath(path.join(args.new_dir, self._slug))
        self.failed_path = path.abspath(path.join(args.failed_dir, self._slug))
        self.done_path = path.abspath(path.join(args.done_dir, self._slug))

        # logger
        self._logger = logging.getLogger()
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter(STDOUT_FORMAT))
        self._logger.addHandler(stdout_handler)
        self._logger_file_handler = None
        if self._log_fn:
            self._logger_file_handler = logging.FileHandler(self._log_fn, mode="w")
            self._logger_file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            self._logger.addHandler(self._logger_file_handler)
        self._logger.setLevel(logging.DEBUG)

        # stage
        self._stage = UNKNOWN
        # reason of fail
        self._failed = ""

        # user readable progress string
        self.user_progress = ""

        self.whipper_lines = []

        # updates
        self._http_endpoint = args.http_endpoint
        self._http_log_endpoint = args.http_log_endpoint
        self._http_auth = None
        if args.http_auth:
            creds = args.http_auth.split(":", maxsplit=1)
            self._http_auth = HTTPBasicAuth(creds[0], creds[1])

        # detected number of tracks
        self.n_tracks = None

        # MusicBrainz
        self.mb_disc_id = ""
        # If MB doesn't match TOC, user should follow this URL
        self.mb_lookup_url = ""
        # a disc id may relate to multiple releases
        self.mb_releases = []

        # UI info
        self.album = ""
        self.albumartist = ""

        self._exit = False

    def __enter__(self):
        self._logger.info(f"Using drive {self.drive} on {socket.gethostname()}", extra=self.extra())
        return self

    def extra(self):
        return {
            "slug": self._slug,
            "drive": self.drive,
        }

    def enter_stage(self, stage):
        self._stage = stage
        self.debug(f"Entering stage {stage}.")

    def in_stage(self, stage):
        return self._stage == stage

    def fail(self, reason: str):
        self._failed = reason
        self._logger.warning(
            f"Failed: {reason}, results remain in {self.failed_path}.", extra=self.extra())

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, extra=self.extra(), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, extra=self.extra(), *args, **kwargs)

    def post(self):
        if self._http_endpoint:
            self.debug(f"Posting update to {self._http_endpoint}")
            body = {
                "hostname": socket.gethostname(),
                "drive_path": self.drive,
                "stage": self._stage,
                "failed": self._failed,
                "mb_disc_id": self.mb_disc_id,
                "mb_lookup_url": self.mb_lookup_url,
                "mb_releases": "\n".join(self.mb_releases),
                "user_progress": self.user_progress,
                "album": self.album,
                "albumartist": self.albumartist,
                "whipper_exited": self._exit,
            }
            try:
                res = requests.post(self._http_endpoint + self._slug,
                    json=body, auth=self._http_auth, timeout=10)
            except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as err:
                self._logger.error("Posting session over HTTP encountered an issue",
                    extra=self.extra())
                self._logger.exception(err, extra=self.extra())
                return
            self.info(f"Session server replied with HTTP {res.status_code}")
            self.debug(res.text)
        else:
            self.debug("Update won't be posted, no HTTP endpoint")

    def upload_log(self):
        if self._log_fn and self._http_log_endpoint:
            self.debug(f"Uploading log to {self._http_log_endpoint}")
            self._logger_file_handler.flush()
            with open(self._log_fn, "rb") as log_file:
                try:
                    res = requests.post(self._http_log_endpoint + lörslärä,
                        data=log_file, auth=self._http_auth, timeout=10)
                except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as err:
                    self._logger.error("Uploading log over HTTP encountered an issue",
                        extra=self.extra())
                    self._logger.exception(err, extra=self.extra())
                    return
            self.info(f"Log server replied with HTTP {res.status_code}")
            self.debug(res.text)
        else:
            self.debug("Log file not uploaded")

    def failed(self):
        return self._failed != ""

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._exit = True
        if exc_type is None:
            self.debug("Session ended cleanly")
        else:
            if self._failed == "":
                self._failed = "Unexpected exception"
            self._logger.exception(exc_traceback, extra=self.extra())
        self.post()
        self.upload_log()
