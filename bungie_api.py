import requests
import json
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

API_KEY = '63513bb851474407919eb9dba2758d02'
ITEMS_JSON_URL = 'https://www.bungie.net/common/destiny2_content/json/en/DestinyInventoryItemDefinition-b480d136-fa1d-4c23-b04f-3b978d639fda.json'
LOOKUP_PATH = 'weapon_lookup.json'
LEGENDARY_TIER_HASH = 4008398120  # The tierTypeHash for legendary items

# Helper functions
def fetch_socket_details(socket_hash):
    try:
        response = requests.get(
            f'https://www.bungie.net/Platform/Destiny2/Manifest/DestinyInventoryItemDefinition/{socket_hash}/',
            headers={'X-API-Key': API_KEY}
        )
        response.raise_for_status()
        details = response.json()
        if 'Response' in details and 'displayProperties' in details['Response']:
            return socket_hash, details['Response']['displayProperties']['name']
        return socket_hash, None
    except requests.exceptions.RequestException as e:
        logger.error(f'Error fetching socket details for hash {socket_hash}: {e}')
        return socket_hash, None

def build_weapon_lookup():
    if os.path.exists(LOOKUP_PATH):
        with open(LOOKUP_PATH, 'r') as file:
            weapon_lookup = json.load(file)
            logger.info('Loaded weapon lookup from file')
            return weapon_lookup

    weapon_lookup = {}
    socket_cache = {}

    response = requests.get(ITEMS_JSON_URL)
    response.raise_for_status()
    data = response.json()

    socket_hashes = set()
    for item in data.values():
        if 'inventory' in item and item['inventory'].get('tierTypeHash') == LEGENDARY_TIER_HASH:
            if 'sockets' in item and 'socketEntries' in item['sockets']:
                socket_entries = item['sockets']['socketEntries']
                if len(socket_entries) > 0:
                    socket_hashes.add(socket_entries[0].get('singleInitialItemHash'))
                if len(socket_entries) > 12:
                    socket_hashes.add(socket_entries[12].get('singleInitialItemHash'))

    # Fetch socket details in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_socket = {executor.submit(fetch_socket_details, socket_hash): socket_hash for socket_hash in socket_hashes}
        for future in as_completed(future_to_socket):
            socket_hash, socket_name = future.result()
            if socket_name:
                socket_cache[socket_hash] = socket_name

    def get_damage_type_name(damageType):
        damageTypes = {
            1: 'Kinetic',
            2: 'Arc',
            3: 'Solar',
            4: 'Void',
            6: 'Stasis',
            7: 'Strand'
        }
        return damageTypes.get(damageType, 'Unknown')

    def get_ammo_type_name(ammoType):
        ammoTypes = {
            1: 'Primary',
            2: 'Energy',
            3: 'Power'
        }
        return ammoTypes.get(ammoType, 'Unknown')

    for item in data.values():
        if 'inventory' in item and item['inventory'].get('tierTypeHash') == LEGENDARY_TIER_HASH:
            if 'sockets' in item and 'socketEntries' in item['sockets']:
                socket_entries = item['sockets']['socketEntries']
                archetype_socket_hash = socket_entries[0].get('singleInitialItemHash') if len(socket_entries) > 0 else None
                deepsight_socket_hash = socket_entries[12].get('singleInitialItemHash') if len(socket_entries) > 12 else None

                if archetype_socket_hash in socket_cache and 'Frame' in socket_cache[archetype_socket_hash]:
                    archetype_name = socket_cache[archetype_socket_hash]
                    damage_type_name = get_damage_type_name(item.get('defaultDamageType', None))
                    craftable = deepsight_socket_hash in socket_cache and socket_cache[deepsight_socket_hash] == 'Empty Deepsight Socket'

                    if archetype_name != "Empty Frames Socket" and damage_type_name != 'Unknown':
                        weapon_lookup[item['hash']] = {
                            'name': item['displayProperties']['name'],
                            'icon': item['displayProperties'].get('icon', ''),
                            'iconWatermark': item.get('iconWatermark', ''),
                            'type': item['itemTypeDisplayName'],
                            'archetype': archetype_name,
                            'damageType': damage_type_name,
                            'ammoType': get_ammo_type_name(item['equippingBlock'].get('ammoType', None)) if 'equippingBlock' in item else 'Unknown',
                            'craftable': craftable
                        }
                        logger.debug(f'Weapon hash {item["hash"]} added with archetype {archetype_name}, craftable {craftable}, name {item["displayProperties"]["name"]}')

    with open(LOOKUP_PATH, 'w') as file:
        json.dump(weapon_lookup, file, indent=2)
        logger.info('Saved weapon lookup to file')

    return weapon_lookup

def get_legendary_guns():
    weapon_lookup = build_weapon_lookup()
    try:
        legendary_weapons = [
            {
                'name': item['name'],
                'hash': hash,
                'icon': item['icon'],
                'iconWatermark': item.get('iconWatermark', ''),
                'type': item['type'],
                'archetype': item['archetype'],
                'damageType': item['damageType'],
                'ammoType': item['ammoType'],
                'craftable': item['craftable']
            }
            for hash, item in weapon_lookup.items()
            if item['type'] != 'Unknown' and item['ammoType'] != 'Unknown'
        ]
        logger.info(f'Legendary guns fetched: {len(legendary_weapons)}')
        return legendary_weapons
    except requests.exceptions.RequestException as e:
        logger.error(f'Error fetching data: {e}')
        return []

if __name__ == '__main__':
    guns = get_legendary_guns()
    print(json.dumps(guns, indent=2))
