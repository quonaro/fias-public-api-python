"""
Example demonstrating Location methods.

This example shows how to get location by IP address.
"""

from fias_public_api import AddressType, SyncFPA, get_token_sync


def main():
    # Get token and create client
    token = get_token_sync()
    api = SyncFPA(token, address_type=AddressType.MUNICIPALITY)

    print("🌍 Location Methods Examples\n")

    # Example 1: Get location by IP (default address type)
    print("1️⃣ Getting location by IP (default type)...")
    try:
        # Using Google DNS IP as example
        ip_address = "8.8.8.8"
        results = api.get_location_by_ip(ip=ip_address)
        addresses = results.get("addresses", [])
        print(f"✅ Found {len(addresses)} addresses for IP {ip_address}")

        if addresses:
            print("\n📋 Location information:")
            for i, addr in enumerate(addresses[:3], 1):
                print(f"   {i}. {addr.get('full_name', 'N/A')}")
                print(f"      Region code: {addr.get('region_code', 'N/A')}")
                print(f"      Path: {addr.get('path', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 2: Get location by IP with specific address type
    print("\n2️⃣ Getting location by IP (administrative type)...")
    try:
        ip_address = "8.8.8.8"
        results = api.get_location_by_ip(
            ip=ip_address, address_type=AddressType.ADMINISTRATIVE
        )
        addresses = results.get("addresses", [])
        print(f"✅ Found {len(addresses)} addresses (administrative type)")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 3: Get location for different IPs
    print("\n3️⃣ Getting locations for multiple IPs...")
    test_ips = [
        "8.8.8.8",  # Google DNS
        "1.1.1.1",  # Cloudflare DNS
        "77.88.8.8",  # Yandex DNS (Russia)
    ]

    for ip in test_ips:
        try:
            results = api.get_location_by_ip(ip=ip)
            addresses = results.get("addresses", [])
            if addresses:
                location = addresses[0].get("full_name", "N/A")
                print(f"   {ip} -> {location}")
            else:
                print(f"   {ip} -> Location not found")
        except Exception as e:
            print(f"   {ip} -> Error: {e}")


if __name__ == "__main__":
    main()
