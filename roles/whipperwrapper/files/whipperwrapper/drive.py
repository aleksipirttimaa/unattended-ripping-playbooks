import fcntl
import os
import subprocess as sb
from time import sleep

# https://github.com/torvalds/linux/blob/master/include/uapi/linux/cdrom.h

CDROM_DRIVE_STATUS = 0x5326

CDS_NO_INFO = 0
CDS_NO_DISC = 1
CDS_TRAY_OPEN = 2
CDS_DRIVE_NOT_READY = 3
CDS_DISC_OK = 4

def status(drive_path):
    fd = os.open(drive_path, os.O_RDONLY | os.O_NONBLOCK)
    s = fcntl.ioctl(fd, CDROM_DRIVE_STATUS)
    os.close(fd)
    return s

class ClosedTray():
    def __init__(self, drive_path):
        self.drive_path = drive_path

    def __enter__(self):
        """Block until a disk is ready"""
        print("Ready for a disk..")
        while status(self.drive_path) != CDS_DISC_OK:
            sleep(1)
        sleep(1)

    def __exit__(self, _exc_type, _exc_value, _exc_traceback):
        """Always open tray"""
        if status(self.drive_path) != CDS_TRAY_OPEN:
            sb.run(["eject", self.drive_path], check=True)
