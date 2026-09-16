import argparse
import re
from collections import Counter

FAILED_LOGIN_PATTERN = re.compile(r'Failed password for .+ from (\d+\.\d+\.\d+\.\d+)')

def parse_log(filepath, threshold):
    failed_attempts = []
    with open(filepath, 'r', errors='ignore') as f:
        for line in f:
            match = FAILED_LOGIN_PATTERN.search(line)
            if match:
                failed_attempts.append(match.group(1))

    ip_counts = Counter(failed_attempts)

    print(f"\n{'='*45}")
    print(f"  Auth Log Analysis: {filepath}")
    print(f"{'='*45}")
    print(f"  Total failed attempts: {len(failed_attempts)}")
    print(f"  Unique source IPs:     {len(ip_counts)}")
    print(f"{'='*45}\n")

    flagged = {ip: count for ip, count in ip_counts.items() if count >= threshold}

    if flagged:
        print(f"[!] IPs exceeding threshold ({threshold} attempts):\n")
        for ip, count in sorted(flagged.items(), key=lambda x: x[1], reverse=True):
            print(f"    {ip:<20} {count} attempts  <-- INVESTIGATE")
    else:
        print(f"[+] No IPs exceeded the threshold of {threshold} attempts.")

    print()

parser = argparse.ArgumentParser(description="SSH brute force detector")
parser.add_argument("logfile", help="Path to auth.log")
parser.add_argument("--threshold", type=int, default=5, help="Alert threshold (default: 5)")
args = parser.parse_args()

parse_log(args.logfile, args.threshold)
