# Base scanning script to scan ports 1 through 1024 and list any
# that are open.


import argparse                     # Handle cli flags
import socket                       # raw network connections

def scan_port(host, port):
    try:
        s = socket.socket()         # creates a new TCP socket object
        s.settimeout(1)             # gives each new connection attempt 1 second before giving up
        s.connect((host, port))     # tries to open a connection - succeeds if port is open
        s.close()                   # cleanly closes the connection
        return True
    except:
        return False                # any error (refused, timeout) = port closed/filtered

parser = argparse.ArgumentParser(description="Simple TCP port scanner")             # creates the CLI argument parser
parser.add_argument("host", help="Target IP or hostname")                           # positional arg - required, no flag needed
parser.add_argument("--ports", default="1-1024", help="Port range, e.g. 1-1024")    # optional flag, defaults to 1-1024 if omitted
args = parser.parse_args()                                                          # reads what the user actually typed and stores it

start, end = map(int, args.ports.split("-"))                                        # "1-1024" -> splits on "-" -> converts both to int -> start=1, end=1024

print(f"Scanning {args.host} ports {start}-{end} ...\n")                            # prints target name and port spread

for port in range(start, end + 1):                                                  # loops every port number in the range (+1 because range() excludes the end)
    if scan_port(args.host, port):                                                  # calls the function - only prints if it returned True
        print(f"[OPEN] {port}")                                                     # f-string - injects the port number into the output string

print("\nScan complete.")                                                           # prints to signify completion