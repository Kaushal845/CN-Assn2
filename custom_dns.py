#!/usr/bin/env python3
"""
Step-by-Step DNS Lookup Service
------------------------------
Simple DNS server that performs domain name resolution by querying servers iteratively.
Binds to 10.0.0.5 and processes incoming DNS requests through hierarchical lookups.
"""

import socket
import time
import sys
from dnslib import DNSRecord

# Primary DNS root server addresses
NAME_SERVERS = [
    "198.41.0.4",      # a.root-servers.net
    "199.9.14.201",    # b.root-servers.net
    "192.33.4.12",     # c.root-servers.net
]


def hierarchical_lookup(request_bytes):
    """
    Execute domain name resolution by querying DNS servers step-by-step.
    Returns: (response_data, trace_info, elapsed_ms, target_domain)
    """
    dns_request = DNSRecord.parse(request_bytes)
    target_name = str(dns_request.q.qname)

    trace_info = []
    begin_time = time.time()
    active_servers = NAME_SERVERS
    final_response = None
    lookup_step = 0

    while True:
        lookup_step += 1
        received_reply = False
        reply_data = None
        contacted_server = None

        # Query each server in the current server list
        for name_server in active_servers:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
                udp_sock.settimeout(2)
                query_start = time.time()
                try:
                    udp_sock.sendto(request_bytes, (name_server, 53))
                    reply_data, _ = udp_sock.recvfrom(2048)
                    query_end = time.time()
                    response_time = (query_end - query_start) * 1000
                    received_reply = True
                    contacted_server = name_server
                    break
                except socket.timeout:
                    trace_info.append({
                        "step": lookup_step,
                        "mode": "Iterative",
                        "stage": "Timeout",
                        "server": name_server,
                        "rtt": None,
                        "response": ["No response (timeout)"]
                    })

        # Exit if no servers responded
        if not received_reply:
            break

        parsed_reply = DNSRecord.parse(reply_data)

        # Identify resolution phase
        if lookup_step == 1:
            phase = "Root"
        elif len(parsed_reply.auth) > 0 and not parsed_reply.rr:
            phase = "TLD"
        else:
            phase = "Authoritative"

        # Build response description
        reply_summary = []
        available_records = parsed_reply.rr or parsed_reply.auth or []
        if available_records:
            for record in available_records:
                reply_summary.append(f"{record.rname} -> {record.rtype} -> {record.rdata}")
        else:
            reply_summary.append("Referral or empty response")

        trace_info.append({
            "step": lookup_step,
            "mode": "Iterative",
            "stage": phase,
            "server": contacted_server,
            "rtt": round(response_time, 2),
            "response": reply_summary
        })

        # Check if we have the final answer
        if parsed_reply.rr:
            final_response = reply_data
            break

        # Find next nameserver addresses
        next_server_ips = [str(record.rdata) for record in parsed_reply.ar if record.rtype == 1]

        if not next_server_ips:
            # Look up nameserver addresses if not provided directly
            server_names = [str(record.rdata) for record in parsed_reply.auth if record.rtype == 2]
            if not server_names:
                break

            next_server_ips = []
            for server_name in server_names:
                ns_query = DNSRecord.question(server_name)
                ns_response, ns_trace, _, _ = hierarchical_lookup(bytes(ns_query.pack()))
                trace_info.extend(ns_trace)
                if ns_response:
                    ns_parsed = DNSRecord.parse(ns_response)
                    for record in ns_parsed.rr:
                        if record.rtype == 1:
                            next_server_ips.append(str(record.rdata))

        if not next_server_ips:
            break

        active_servers = next_server_ips

    elapsed_time = (time.time() - begin_time) * 1000
    return final_response, trace_info, round(elapsed_time, 2), target_name


def start_service():
    """Launch DNS service on 10.0.0.5:53 to handle domain resolution requests."""
    output_file = sys.argv[1] if len(sys.argv) > 1 else "resolver_log.txt"

    with open(output_file, "a") as log_handle:
        def write_output(*args, **kwargs):
            """Write to both console and log file."""
            print(*args, **kwargs)
            print(*args, **kwargs, file=log_handle)
            log_handle.flush()

        session_header = f"\n===== New Run at {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n"
        log_handle.write(session_header)
        print(session_header.strip())

        write_output("DNS Resolver running on 10.0.0.5:53 ...")
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind(("10.0.0.5", 53))  # DNSR IP

        while True:
            try:
                request_data, client_addr = udp_socket.recvfrom(512)
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                reply_data, trace_log, duration, domain_name = hierarchical_lookup(request_data)

                write_output(f"\n[{timestamp}] Query from {client_addr[0]} for {domain_name}")
                for trace_entry in trace_log:
                    write_output(f"  Step {trace_entry['step']} | Mode: {trace_entry['mode']} | "
                              f"Stage: {trace_entry['stage']} | Server: {trace_entry['server']} | "
                              f"RTT: {trace_entry['rtt']} ms")
                    write_output("    Response:")
                    for response_line in trace_entry['response']:
                        write_output(f"      {response_line}")
                    write_output()

                write_output(f"  Total resolution time: {duration} ms")

                if reply_data:
                    udp_socket.sendto(reply_data, client_addr)
                else:
                    write_output("  Resolution failed.\n")

            except KeyboardInterrupt:
                write_output("\nShutting down DNS Resolver...")
                break
            except Exception as error:
                write_output(f"Error: {error}")
                continue


if __name__ == "__main__":
    start_service()
