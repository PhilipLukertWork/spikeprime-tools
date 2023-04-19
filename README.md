# spikeprime-tools v0.1.0
Utilities for experimenting with LEGO SPIKE PRIME Hub

Code modified from https://github.com/nutki/spike-tools

Install Python 3.8.2. Enable Add to Path when installing <= THIS IS VERY IMPORTANT.

To install, just run install.bat etc. after downloading the whole repository.

-------------

The default device address to communicate with the hub is `/dev/ttyACM0` and otherwise can be specified with `--tty` option. The port path can be discovered with `sudo python -m serial.tools.list_ports`.

Access to serial ports usually needs a special privilege. To avoid running every command with `sudo`
you can do the follwing in Linux (needs logout to become effective). 
```sh
sudo adduser <user name> dialout
```

If the center led of the hub flashes red shortly after connecting and/or you see random characters
appearing when manually connecting to the hub via a terminal (something like `ATE1 E0 ~x~`), this
likely indicates a modem controller is trying to talk to the hub (which won't succeed). Under 
Linux this can be disbled with:
```sh
sudo systemctl disable ModemManager
```

## spikejsonrpcapispike.py
A module to communicate with the Spike Hub using JSON RPC. Can be used to manage program slots of the on brick selector.

```
usage: spikejsonrpcapispike.py [-h] [-t TTY] [--debug]
                               {list,ls,fwinfo,mv,upload,cp,rm,start,stop,display}
                               ...

Tools for Spike Hub RPC protocol

positional arguments:
  {list,ls,fwinfo,mv,upload,cp,rm,start,stop,display}
    list (ls)           List stored programs
    fwinfo              Show firmware version
    mv                  Changes program slot
    upload (cp)         Uploads a program and stats it. Default slot is 0
    rm                  Removes the program at a given slot
    start               Starts a program
    stop                Stop program execution
    display             Controls 5x5 LED matrix display

options:
  -h, --help            show this help message and exit
  -t TTY, --tty TTY     Spike Hub device path
  --debug               Enable debug
```

The programs launched with the default launcher need to be expressed in coroutines so they can be
exited properly. `hub/program_template.py` is an example skeleton program handling initialization.
It can be uploaded and executed with:
```sh
sudo ./spikejsonrpc.py upload hub/program_template.py
```
A slot can be specified, e.g., with `--to_slot 3`. And the execution can be skipped with `--no_start`.

## cp.py
Copy a file to the hub filesystem.
```
usage: cp.py [-h] [-t TTY] file [dir]
```

## convert_sound.py
Converts a sound file to a format accepted by `hub.sound.play()` method. Accepts any input format supported by `librosa`.

```
usage: convert_sound.py [-h] [-s START] [-d DURATION] file
```
