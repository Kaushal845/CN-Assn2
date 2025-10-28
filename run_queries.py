#!/usr/bin/env python3
import dns.resolver
import time, os

DOMAIN_LIST = "/home/mininet/ass_2/queries2.txt"
RESULTS_PATH = "/home/mininet/ass_2/h24_results.csv"

def lookup_hostname(hostname):
    dns_client = dns.resolver.Resolver()
    dns_client.timeout = 3
    dns_client.lifetime = 3
    try:
        begin = time.perf_counter()
        result = dns_client.resolve(hostname, "A")
        duration = (time.perf_counter() - begin) * 1000
        addresses = [record.address for record in result]
        return addresses, duration
    except Exception as error:
        return None, None

def execute_tests():
    if not os.path.exists(DOMAIN_LIST):
        print(f"[ERROR] Query file not found: {DOMAIN_LIST}")
        return

    with open(DOMAIN_LIST) as file_handle:
        hostnames = [line.strip() for line in file_handle if line.strip()]

    query_count = len(hostnames)
    print(f"Running {query_count} DNS queries from {DOMAIN_LIST}...\n")

    resolved_count = 0
    failed_count = 0
    cumulative_time = 0.0

    for index, hostname in enumerate(hostnames, start=1):
        addresses, response_time = lookup_hostname(hostname)
        if addresses:
            print(f"[{index}/{query_count}] {hostname} -> {', '.join(addresses)} ({response_time:.1f} ms)")
            resolved_count += 1
            cumulative_time += response_time
        else:
            print(f"[{index}/{query_count}] {hostname} -> FAIL")
            failed_count += 1

        time.sleep(0.3)  # brief pause between requests

    mean_latency = cumulative_time / resolved_count if resolved_count > 0 else 0.0

    print("\n=== Summary ===")
    print(f"Total queries: {query_count}")
    print(f"Successful: {resolved_count}")
    print(f"Failed: {failed_count}")
    print(f"Average latency: {mean_latency:.2f} ms")

    # Write results to CSV file
    with open(RESULTS_PATH, "a") as output_handle:
        output_handle.write(f"H1,{query_count},{resolved_count},{failed_count},{mean_latency:.2f}\n")

    print(f"\nResults saved to {RESULTS_PATH}")

if __name__ == "__main__":
    execute_tests()
