import re

from session import READING_TOC, RIPPING

def any_line_matches(r, lines):
    for line in lines:
        if re.match(r, line):
            return True
    return False

def search_first_matching_line(r, lines, group=None):
    for line in lines:
        search = re.search(r, line)
        if search:
            if group:
                return search.group(group)
            return search
    return None

def parse(line, session):
    """Call to parse individual line, mutating session"""
    if re.match(r"^Reading TOC\W+0\W+%", line):
        session.enter_stage(READING_TOC)
        session.user_progress = "Identifying release.."
        session.post()
        return

    search_disc_id = re.search(r"^MusicBrainz disc id (.*)$", line)
    if search_disc_id:
        session.mb_disc_id = search_disc_id.group(1)
        return

    search_lookup_url = re.search(r"^MusicBrainz lookup URL ([^ ]*)", line)
    if search_lookup_url:
        session.mb_lookup_url = search_lookup_url.group(1)
        return

    if re.match(r"Matching releases:", line):
        session.enter_stage(RIPPING)
        session.post()
        return

    search_verifying_track = re.search(r"^Verifying track ([0-9]+) of ([0-9]+)", line)
    if search_verifying_track:
        n = search_verifying_track.group(1)
        total = search_verifying_track.group(2)
        new_progress = f"Ripped {n} of {total} tracks."
        if new_progress != session.user_progress:
            session.user_progress = new_progress
            session.post()

def parse_all(returncode, session):
    """Call after whipper has exited, to parse its output as a whole"""
    if any_line_matches(
        r"Submit this disc to MusicBrainz at the above URL.",
        session.whipper_lines):
        session.fail(reason="Submit this disc to MusicBrainz.")
        return

    # FIXME: ensure accurate rip
    #ar_all_accurate = False
    #if any_line_matches(r"rip accurate", session.whipper_lines):
    #    ar_all_accurate = True
    #
    #if any_line_matches(r"rip NOT accurate", session.whipper_lines):
    #    ar_all_accurate = False

    n_tracks = search_first_matching_line(
        r"^Disc duration: [0-9:.]+, ([0-9]+) audio tracks$",
        session.whipper_lines, group=1)

    try:
        session.n_tracks = int(n_tracks)
    except (TypeError, ValueError):
        session.fail(reason="Unknown track count")
        return

    if session.n_tracks < 1:
        # cd-rom's have no tracks or something..
        session.fail(reason="No tracks")
        return

    # FIXME
    #if not ar_all_accurate:
    #    session.fail(reason="Inaccurate rip. (see whipper output for details)")
    #    return

    if returncode != 0:
        session.fail(reason=f"whipper failed with unknown error code {returncode}")
        return
