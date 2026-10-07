"""
Example demonstrating AddressInfo methods.

This example shows various AddressInfo operations:
- Getting regions
- Getting address items with filters
- Getting address details
- Checking hierarchy relationships
"""

from fias_public_api import AddressType, SyncFPA, get_token_sync


def main():
    # Get token and create client
    token = get_token_sync()
    api = SyncFPA(token, address_type=AddressType.MUNICIPALITY)

    print("📍 AddressInfo Methods Examples\n")

    # Example 1: Get all regions
    print("1️⃣ Getting all regions...")
    try:
        regions = api.get_regions()
        addresses = regions.get("addresses", [])
        print(f"✅ Found {len(addresses)} regions")

        if addresses:
            print("\n📋 First 5 regions:")
            for i, region in enumerate(addresses[:5], 1):
                print(
                    f"   {i}. {region.get('full_name', 'N/A')} (ID: {region.get('object_id', 'N/A')})"
                )
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 2: Get address items with filters
    print("\n2️⃣ Getting address items with filters...")
    try:
        # Get regions first to use as parent
        regions = api.get_regions()
        if regions.get("addresses"):
            first_region = regions["addresses"][0]
            # Get child items for the region
            items = api.get_address_items(
                path=first_region.get("path"),
                address_level=2,  # District level
                include_descendants=False,
            )
            addresses = items.get("addresses", [])
            print(
                f"✅ Found {len(addresses)} items for region {first_region.get('full_name')}"
            )

            if addresses:
                print("\n📋 First 3 items:")
                for i, item in enumerate(addresses[:3], 1):
                    print(f"   {i}. {item.get('full_name', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 3: Get address details
    print("\n3️⃣ Getting address details...")
    try:
        # Use a known object ID (Moscow region example)
        object_id = 77  # Moscow region ID (example)
        details = api.get_details(object_id)

        if "address_details" in details:
            addr_details = details["address_details"]
            print(f"✅ Details retrieved for object {object_id}")
            print(f"   Postal code: {addr_details.get('postal_code', 'N/A')}")
            print(f"   OKATO: {addr_details.get('okato', 'N/A')}")
            print(f"   OKTMO: {addr_details.get('oktmo', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 4: Check if element is descendant
    print("\n4️⃣ Checking hierarchy relationships...")
    try:
        regions = api.get_regions()
        if len(regions.get("addresses", [])) >= 2:
            ancestor = regions["addresses"][0].get("object_id")
            descendant = regions["addresses"][1].get("object_id")

            result = api.is_descendant(ancestor=ancestor, descendant=descendant)
            is_desc = result.get("check", False)
            print(f"✅ Is {descendant} descendant of {ancestor}? {is_desc}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 5: Check if element has descendants
    print("\n5️⃣ Checking if element has descendants...")
    try:
        regions = api.get_regions()
        if regions.get("addresses"):
            parent_id = regions["addresses"][0].get("object_id")

            result = api.has_descendants(parent=parent_id, up_to_level=5)
            has_desc = result.get("check", False)
            print(f"✅ Does {parent_id} have descendants up to level 5? {has_desc}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 6: Get FIAS object types
    print("\n6️⃣ Getting FIAS object types...")
    try:
        types = api.get_fias_object_types()
        type_list = types.get("types", [])
        print(f"✅ Found {len(type_list)} object types")

        if type_list:
            print("\n📋 First 5 types:")
            for i, obj_type in enumerate(type_list[:5], 1):
                print(
                    f"   {i}. {obj_type.get('type_name', 'N/A')} (Level: {obj_type.get('address_level', 'N/A')})"
                )
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
