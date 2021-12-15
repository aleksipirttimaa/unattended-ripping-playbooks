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

STDOUT_FORMAT = "%(_id)s: %(levelname)s %(message)s"
LOG_FORMAT = "%(asctime)s %(_id)s: %(levelname)s %(message)s"

def session_id() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M") \
        + "-" + str(uuid.uuid4()).split("-", maxsplit=1)[0]

class UnattendedSession():
    def __init__(self, args):
        self._id = session_id()

        self.drive = args.drive

        # paths
        self._log_fn = None
        if args.log_dir:
            self._log_fn = path.abspath(path.join(args.log_dir, self._id + ".log"))
        self.new_path = path.abspath(path.join(args.new_dir, self._id))
        self.failed_path = path.abspath(path.join(args.failed_dir, self._id))
        self.done_path = path.abspath(path.join(args.done_dir, self._id))

        # logger
        self._logger = logging.getLogger()
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter(STDOUT_FORMAT))
        self._logger.addHandler(stdout_handler)
        if self._log_fn:
            file_handler = logging.FileHandler(self._log_fn, mode="w")
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            self._logger.addHandler(file_handler)
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

    def __enter__(self):
        self._logger.info(f"Using drive {self.drive} on {socket.gethostname()}", extra=self.extra())
        return self

    def extra(self):
        return {
            "_id": self._id,
            "drive": self.drive,
        }

    def enter_stage(self, stage):
        self._stage = stage
        self.debug(f"Entering stage {stage}.")

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
                "user_progress": self.user_progress,
            }
            try:
                res = requests.post(self._http_endpoint + self._id,
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

    def failed(self):
        return self._failed != ""

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is None:
            self.debug("Session ended cleanly")
        else:
            if self._failed == "":
                self._failed = "Unexpected exception"
                self.post()
            self._logger.exception(exc_traceback, extra=self.extra())
