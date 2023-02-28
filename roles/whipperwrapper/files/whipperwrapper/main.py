#!/usr/bin/env python3

import argparse
import os
import subprocess as sb
from shutil import which

from drive import ClosedTray
from session import UnattendedSession, FORKING_WHIPPER, UPLOADING, UPLOADED
import wrapper

def assert_dir(fn):
    if not os.path.isdir(fn):
        raise FileNotFoundError(f"No such directory: {fn}")

def assert_command(command):
    if not which(command):
        raise FileNotFoundError(f"No such command: {command}")

def whipper_cmd(args):
    try:
        assert_command("whipper")
    except FileNotFoundError:
        # If whipper is not installed, expect to find it from venv
        # TODO: jank
        return os.path.join(args.venv_dir, "bin/whipper")
    return "whipper"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--drive", type=str, help="Path to cd drive")
    parser.add_argument("--log_dir", type=str, help="Path to log directory")
    parser.add_argument("--new_dir", type=str, help="Path to ripping directory")
    parser.add_argument("--failed_dir", type=str, help="Path to failed directory")
    parser.add_argument("--done_dir", type=str, help="Path to done directory")
    parser.add_argument("--venv_dir", type=str, help="Path to whipper venv")
    parser.add_argument("--http_endpoint", type=str, help="HTTP endpoint for updates")
    parser.add_argument("--http_log_endpoint", type=str, help="HTTP endpoint for log files")
    parser.add_argument("--http_auth", type=str, help="HTTP Basic auth user:pass")
    parser.add_argument("--rsync_dest", type=str, help="enable rsync and specify DEST")
    parser.add_argument("--rsync_bwlimit", type=str, help="set rsync --bwlimit=KBPS")
    parser.add_argument("--rsync_e", type=str, help="set rsync -e")
    parser.add_argument("--rsync_log-file", type=str, help="set rsync --log-file")
    parser.add_argument("--rsync_temp-dir", type=str, help="set rsync --temp-dir")
    args = parser.parse_args()

    if not os.path.exists(args.drive):
        raise FileNotFoundError(f"No such drive: {args.drive}")

    assert_dir(args.log_dir)
    assert_dir(args.new_dir)
    assert_dir(args.done_dir)

    assert_command("eject")

    if args.rsync_dest:
        assert_command("rsync")

    # Wait for a closed tray (that has a disc) and open it at the end
    with ClosedTray(args.drive):
        # UnattendedSession is state of this ripping session
        with UnattendedSession(args) as session:
            session.enter_stage(FORKING_WHIPPER)
            # post update over HTTP
            session.post()

            os.mkdir(session.new_path)

            wr = sb.Popen([
                    whipper_cmd(args),
                    "-c", "False",           # drive auto close
                    "cd",
                    "-d", args.drive,        # drive
                    "rip",
                    "-W", session.new_path], # working directory
                encoding="utf-8", stdout=sb.PIPE, stderr=sb.STDOUT)

            while True:
                if wr.poll() != None:
                    # TODO: jank
                    # whipper has terminated
                    break

                line = wr.stdout.readline()
                if not line:
                    # whipper has terminated
                    break

                line = line.rstrip("\n")
                session.info(f"whipper: {line}")
                session.whipper_lines.append(line)
                wrapper.parse(line, session)

            # wait to get returncode
            wr.wait()
            session.info(f"whipper exited with code: {wr.returncode}")

            wrapper.parse_all(wr.returncode, session)

            if session.failed():
                # move results from new/{slug} to failed/{slug}
                os.rename(session.new_path, session.failed_path)
                session.user_progress = "Couldn't rip."
            else:
                # move results from new/{slug} to done/{slug}
                os.rename(session.new_path, session.done_path)

                # TODO: .log already contains some drive info
                # but it'd be good to be able to link sessions with
                # disc_upload contents

                session.enter_stage(UPLOADING)

                if not args.rsync_dest:
                    session.user_progress = "Ripping succeeded."

                else:
                    session.user_progress = "Uploading files.."
                    session.post()

                    rs_args = ["rsync", "--verbose", "--archive", "--safe-links", "--delay-updates"]

                    if args.rsync_bwlimit:
                        bwlimit = args.rsync_bwlimit
                        rs_args.append(f"--bwlimit={bwlimit}")

                    if args.rsync_e:
                        rsh = args.rsync_e
                        rs_args.append(f"-e={rsh}")

                    if args.rsync_log_file:
                        log_file = args.rsync_log_file
                        rs_args.append(f"--log-file={log_file}")

                    if args.rsync_tmp_dir:
                        tmp_dir = args.rsync_tmp_dir
                        rs_args.append(f"--tmp-dir={tmp_dir}")

                    rs_args.append(session.done_path)

                    rs_args.append(args.rsync_dest)

                    rs_invokation = " ".join(rs_args)
                    session.debug(f"Invoking rsync with: {rs_invokation}")



                    rs = sb.Popen(rs_args, encoding="utf-8", stdout=sb.STDOUT, stderr=sb.STDOUT)
                    rs.wait()
                    session.info(f"rsync exited with code: {rs.returncode}")

                    if rs.returncode == 0:
                        session.user_progress = ""
                        session.enter_stage(UPLOADED)
