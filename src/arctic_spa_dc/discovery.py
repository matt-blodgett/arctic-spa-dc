"""
Arctic Spa network discovery

This will do a UDP probe of all the devices on the given network to
determine if any of them are an Arctic Spa device

```
searcher = NetworkSearch('192.168.100.5', 24)
results = searcher.search()
```

"""


import socket
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed


def udp_probe(
    host: str,
    query: bytes,
    query_port: int,
    response: bytes,
    timeout: float = 1.0
) -> bool:
    """
    Sends a UDP query to the host and waits for a response.
    Returns True if the expected response is received.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        # Bind to an ephemeral port to avoid conflicts
        sock.bind(('', 0))
        sock.sendto(query, (host, query_port))
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                if addr[0] == host and data.startswith(response):
                    return True
            except socket.timeout:
                break
            except ConnectionResetError:
                break
    finally:
        sock.close()
    return False


class NetworkSearch:
    """
    Searches the network for an Arctic Spa device

    Provide the local IP address of the scanning machine and the subnet
    ```
    searcher = NetworkSearch('192.168.100.5', 24)
    results = searcher.search()

    print(f'Found {len(results)} devices')
    ```
    """

    QUERY_PORT = 9131
    RESPONSE_PORT = 33327
    QUERY = b"Query,BlueFalls,"
    RESPONSE = b"Response,BlueFalls,"

    def __init__(self, ip_address: str, netmask: int) -> None:
        self._ip_address = ip_address
        self._network = ipaddress.ip_network(f'{ip_address}/{netmask}', strict=False)

    def search(self, timeout: float = 1.0, max_workers: int = 50) -> list:
        """
        Searches the network for any Arctic Spa devices and returns a list of IP addresses, using threads for speed.
        """
        hosts = [str(host) for host in self._network.hosts()]
        found = []

        def probe(host_str):
            got_valid_response = udp_probe(
                host_str,
                self.QUERY,
                self.QUERY_PORT,
                self.RESPONSE,
                timeout
            )
            return host_str if got_valid_response else None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(probe, host): host for host in hosts}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found.append(result)
        return found
