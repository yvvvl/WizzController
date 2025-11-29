import asyncio
from pywizlight import discovery
from typing import List, Dict

class BulbDiscovery:
    @staticmethod
    async def discover_bulbs(timeout: int = 3) -> List[Dict[str, str]]:
        """Discover WiZ bulbs on the network.

        Args:
            timeout (int): Time in seconds to wait for discovery.

        Returns:
            List[Dict[str, str]]: A list of discovered bulbs with their IP and MAC addresses.
        """
        try:
            devices = await discovery.discover_lights(broadcast_space="192.168.1.255", wait_time=timeout)
            return [
                {"ip": bulb.ip, "mac": getattr(bulb, "mac", None)}
                for bulb in devices
            ]
        except Exception as e:
            print(f"Error during bulb discovery: {e}")
            return []

# Example usage
if __name__ == "__main__":
    async def main():
        bulbs = await BulbDiscovery.discover_bulbs()
        print("Discovered bulbs:", bulbs)

    asyncio.run(main())