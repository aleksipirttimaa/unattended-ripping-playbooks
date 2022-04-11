# Unattended ripping with whipper

Whipper: https://github.com/whipper-team/whipper

## Proposed system

0. systemd (re)starts our unit
1. Sleep until a disk is inserted
2. Fork Whipper
3. Follow the status of the process (Consume logs, post updates over HTTP)
4. Ensure a good result
5. Move files to `done/{session_slug}` for later storage
6. Open tray
7. (repeat)

```text
/var/local/whipper
│   done
│   └── 20211205-2036-bbbbbbbb
│       └── Artist name - Album name - 2004
│           └── CD1
│               ├── 01 - Artist name - Track name.flac
│                   [ ... ]
│               ├── 12 - Artist name - Track name.flac
│               ├── Artist name - Album name - 2004.cue
│               ├── Artist name - Album name - 2004.log  [ EAC-like log ]
│               ├── Artist name - Album name - 2004.m3u
│               └── Artist name - Album name - 2004.toc
├── failed
│   └── 20211205-2011-aaaaaaaa
│       └── Artist name - Album name - 2013
│           └──   [this session failed earlier, stored for debug]
├── log                          [all logs are retained]
│   ├── 20211205-2011-aaaaaaaa.log   [this session failed]
│   ├── 20211205-2036-bbbbbbbb.log   [this session is done]
│   └── 20211205-2050-cccccccc.log   [this session is ongoing]
├── new
│   └── 20211205-2050-cccccccc
│       └── Artist name - Album name - 2013
│           └──   [whipper is currently ripping these files]
├── src
│   └── whipperwrapper
│       └──   [...]
└── venv
    └──   [...]
```

## Whipperwrapper

Whipperwrapper wraps whipper and is the piece between a systemd unit and whipper. It waits for a disk, handles errors, ensures that the tray is opened at the end and provides real-time status updates over HTTP.

Source resides in `roles/whipperwrapper/files/whipperwrapper`.

## Run the playbook

Targeting Debian 11.

Example development setup:

```sh
ansible-playbook -i inventory.ini devel.yml
```

The remote will checkout whipper and plugins from github.com.

## Configure whipper

### Offset

Every drive that's going to be used needs to have a valid offset configured. Whipper stores this info in: `~/.config/whipper/whipper.conf`

Read more about `whipper.conf`. https://github.com/whipper-team/whipper/issues/283

This process requires a well-known (by AccurateRIP) CD inserted.

Source the whipper venv:

```sh
sudo -u whipper bash
. /var/local/whipper/venv/bin/activate
```

and find the offset for your drive `sr0`:

```sh
whipper offset find -d /dev/sr0
```

This works by iterating through a preterminated set of offsets, until one is found, that produces correct results.

### Analyze

You can use the `analyze` command to discover your drive's capabilites.

```sh
whipper drive analyze -d /dev/sr0
```

Running this will add `defeats_cache = True` to your drive's config, if applicable.

### Filenames

In this project the following file name templates are used:

```sh
cat <<EOF > ~/.config/whipper/whipper.conf
[whipper.cd.rip]
track_template = %%A - %%d - %%y/CD%%N/%%t - %%a - %%n
disc_template = %%A - %%d - %%y/CD%%N/%%A - %%d - %%y
EOF
```

If you ran the playbook, this was done automatically.

## Systemd unit

Enable and start the systemd unit:

```sh
systemd enable --now whipperwrapper@sr0.service
```

## HTTP updates

Whipperwrapper can provide updates of it's status over HTTP.

Only a one kind of HTTP request is produced. Use `session.py` for reference, some examples are included in `example_http_updates`

```text
POST {endpoint_path}/{session_slug}
```

It is assumed that the locally generated `session_slug` is unique.

### Enabling updates

Enable this functionality by setting command-line params `--http-endpoint` and `--http-auth`, in the systemd unit:

```sh
systemctl edit --full whipperwrapper@.service
```

```text
ExecStart= ... \
  --http_endpoint "https://status.example/update" \
  --http_auth "user:pass"  # optional
```

# whipper-plugin-eaclogger

https://github.com/whipper-team/whipper-plugin-eaclogger

eaclogger is a plugin that enables whipper to output EAC-like log output. It is also included in the playbook.

The output is saved as a file to the expected location.

```sh
cat <<EOF > ~/.config/whipper/whipper.conf
[whipper.cd.rip]
logger = eac
EOF
```
