#!/usr/bin/env python3
import dns.resolver
import dns.message
import dns.query
import dns.name
import time
import os
from datetime import datetime

HOSTNAME_FILE = "queries2.txt"
OUTPUT_CSV = "/home/mininet/ass_2/h2_results.csv"
TRACE_LOG = "/home/mininet/ass_2/dns_log2.txt"

# Basic memory storage for resolved domains
domain_cache = {}

# Primary name server addresses for step-by-step resolution
PRIMARY_SERVERS = [
    "198.41.0.4",      # a.root-servers.net
    "199.9.14.201",    # b.root-servers.net
    "192.33.4.12",     # c.root-servers.net
]

def write_trace(message: str):
    """Add trace messages to log file."""
    with open(TRACE_LOG, "a") as trace_file:
        trace_file.write(message + "\n")

def step_by_step_lookup(hostname):
    """Custom step-by-step DNS resolver with comprehensive tracing."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lookup_start = time.perf_counter()
    lookup_method = "Iterative"

    if hostname in domain_cache:
        write_trace(f"{current_time} | {hostname} | {lookup_method} | CACHE | Step: Cache | Response: {domain_cache[hostname]} | RTT: 0 ms | Total: 0 ms | Cache HIT")
        return domain_cache[hostname], 0.0, "HIT"

    target_name = dns.name.from_text(hostname)
    query_target = target_name
    resolved_addresses = None
    accumulated_rtt = 0.0

    # Phase 1: Query root servers
    for root_server in PRIMARY_SERVERS:
        phase_start = time.perf_counter()
        try:
            dns_query = dns.message.make_query(query_target, dns.rdatatype.A)
            root_response = dns.query.udp(dns_query, root_server, timeout=3)
            phase_duration = (time.perf_counter() - phase_start) * 1000
            accumulated_rtt += phase_duration
            write_trace(f"{current_time} | {hostname} | {lookup_method} | {root_server} | Step: Root | Response: Referral | RTT: {phase_duration:.2f} ms | Cache MISS")
            
            # Extract TLD server address from response
            if root_response.additional:
                for resource_record in root_response.additional:
                    if resource_record.rdtype == dns.rdatatype.A:
                        tld_server = resource_record.items[0].address
                        break
                else:
                    continue
                break
        except Exception as error:
            write_trace(f"{current_time} | {hostname} | {lookup_method} | {root_server} | Step: Root | Response: FAIL ({error}) | RTT: - | Cache MISS")
            continue
    else:
        return None, accumulated_rtt, "MISS"

    # Phase 2: Query TLD server
    try:
        phase_start = time.perf_counter()
        dns_query = dns.message.make_query(query_target, dns.rdatatype.A)
        tld_response = dns.query.udp(dns_query, tld_server, timeout=3)
        phase_duration = (time.perf_counter() - phase_start) * 1000
        accumulated_rtt += phase_duration
        write_trace(f"{current_time} | {hostname} | {lookup_method} | {tld_server} | Step: TLD | Response: Referral | RTT: {phase_duration:.2f} ms | Cache MISS")

        # Extract authoritative server address
        authoritative_server = None
        if tld_response.additional:
            for resource_record in tld_response.additional:
                if resource_record.rdtype == dns.rdatatype.A:
                    authoritative_server = resource_record.items[0].address
                    break
    except Exception as error:
        write_trace(f"{current_time} | {hostname} | {lookup_method} | {tld_server} | Step: TLD | Response: FAIL ({error}) | RTT: - | Cache MISS")
        return None, accumulated_rtt, "MISS"

    # Phase 3: Query authoritative server
    try:
        phase_start = time.perf_counter()
        dns_query = dns.message.make_query(query_target, dns.rdatatype.A)
        auth_response = dns.query.udp(dns_query, authoritative_server, timeout=3)
        phase_duration = (time.perf_counter() - phase_start) * 1000
        accumulated_rtt += phase_duration

        if auth_response.answer:
            resolved_addresses = [record_data.address for answer_rr in auth_response.answer for record_data in answer_rr.items if answer_rr.rdtype == dns.rdatatype.A]
            write_trace(f"{current_time} | {hostname} | {lookup_method} | {authoritative_server} | Step: Authoritative | Response: {resolved_addresses} | RTT: {phase_duration:.2f} ms | Cache MISS")
        else:
            write_trace(f"{current_time} | {hostname} | {lookup_method} | {authoritative_server} | Step: Authoritative | Response: NO ANSWER | RTT: {phase_duration:.2f} ms | Cache MISS")

    except Exception as error:
        write_trace(f"{current_time} | {hostname} | {lookup_method} | {authoritative_server} | Step: Authoritative | Response: FAIL ({error}) | RTT: - | Cache MISS")

    complete_time = (time.perf_counter() - lookup_start) * 1000
    if resolved_addresses:
        domain_cache[hostname] = resolved_addresses
        write_trace(f"{current_time} | {hostname} | TOTAL | TotalTime: {complete_time:.2f} ms | Cache Stored\n")
    else:
        write_trace(f"{current_time} | {hostname} | TOTAL | TotalTime: {complete_time:.2f} ms | No Response\n")

    return resolved_addresses, complete_time, "MISS"

def run_tests():
    if not os.path.exists(HOSTNAME_FILE):
        print(f"[ERROR] Query file not found: {HOSTNAME_FILE}")
        return

    with open(HOSTNAME_FILE) as file_reader:
        domain_list = [line.strip() for line in file_reader if line.strip()]

    query_count = len(domain_list)
    print(f"Running {query_count} DNS queries...\n")

    successful_lookups, failed_lookups, total_response_time = 0, 0, 0.0

    for index, hostname in enumerate(domain_list, 1):
        addresses, response_time, cache_result = step_by_step_lookup(hostname)
        if addresses:
            print(f"[{index}/{query_count}] {hostname} -> {', '.join(addresses)} ({response_time:.1f} ms, {cache_result})")
            successful_lookups += 1
            total_response_time += response_time
        else:
            print(f"[{index}/{query_count}] {hostname} -> FAIL")
            failed_lookups += 1
        time.sleep(0.3)

    mean_response_time = total_response_time / successful_lookups if successful_lookups else 0.0
    with open(OUTPUT_CSV, "a") as csv_writer:
        csv_writer.write(f"H1,{query_count},{successful_lookups},{failed_lookups},{mean_response_time:.2f}\n")

    print(f"\nResults saved to {OUTPUT_CSV}")
    print(f"Detailed log saved to {TRACE_LOG}")

if __name__ == "__main__":
    run_tests()
