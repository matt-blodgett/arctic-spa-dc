"""
Usage:
    For automatic discovery of your hot tub:
        python demo.py

    Optionally, specify an IP address:
        python demo.py "192.168.0.0"
"""


import sys
import time
import socket

from arctic_spa_dc.discovery import NetworkSearch
from arctic_spa_dc.client import ArcticSpaClient
from arctic_spa_dc.client import MessageType
from arctic_spa_dc.client import CommandType
from arctic_spa_dc.client import PumpStatus


def get_ip() -> str:
    """
    Gets the local address with the default route
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0)

    try:
        # doesn't even have to be reachable
        sock.connect(('10.254.254.254', 1))
        ip_addr = sock.getsockname()[0]
    except Exception:
        ip_addr = '127.0.0.1'
    finally:
        sock.close()

    return ip_addr


def find_hot_tub(local_addr: str, subnet_mask: int) -> str:
    """
    Scans the subnet for Arctic Spa hot tubs
    """

    print(f'Searching for hot tub from {local_addr}/{subnet_mask}...')

    searcher = NetworkSearch(local_addr, subnet_mask)
    results = searcher.search()

    host = None

    if len(results) >= 1:
        if len(results) > 1:
            print('Multiple hot tubs found - using the first')
        host = results[0]
        print(f'Found a hot tub @ {host}')
    else:
        print('No hot tubs found')

    return host


def get_arctic_spa_client() -> ArcticSpaClient:
    host = None
    if len(sys.argv) == 1:
        host = find_hot_tub(get_ip(), 24)
        if not host:
            print('Could not find a host device!')
            exit(-1)
    elif len(sys.argv) == 2:
        host = sys.argv[1]

    arctic_spa_client = ArcticSpaClient(host)

    print(f'connecting to host device @ {host}...')

    connected = arctic_spa_client.connect()

    if not connected:
        print('connecting failed!')
        exit(-1)

    print('connnected successfully')
    return arctic_spa_client


def test_commands():
    arctic_spa_client = get_arctic_spa_client()

    arctic_spa_client.write_command(CommandType.PUMP_1, PumpStatus.PUMP_HIGH)
    time.sleep(2)

    arctic_spa_client.write_command(CommandType.LIGHTS, True)
    time.sleep(2)

    message = arctic_spa_client.fetch_one(MessageType.LIVE)

    print(message)

    arctic_spa_client.disconnect()


def main():
    arctic_spa_client = get_arctic_spa_client()

    print('getting messages...')

    message = arctic_spa_client.fetch_one(MessageType.LIVE)

    print()
    print('Live')
    print('temperature_fahrenheit -', message.temperature_fahrenheit)
    print('temperature_setpoint_fahrenheit -', message.temperature_setpoint_fahrenheit)
    print('pump_1 -',  message.PumpStatus.Name(message.pump_1))
    print('pump_2 -', message.PumpStatus.Name(message.pump_2))
    print('pump_3 -', message.PumpStatus.Name(message.pump_3))
    print('pump_4 -', message.PumpStatus.Name(message.pump_4))
    print('pump_5 -', message.PumpStatus.Name(message.pump_5))
    print('blower_1 -', message.PumpStatus.Name(message.blower_1))
    print('blower_2 -', message.PumpStatus.Name(message.blower_2))
    print('lights -', message.lights)
    print('stereo -', message.stereo)
    print('heater_1 -', message.HeaterStatus.Name(message.heater_1))
    print('heater_2 -', message.HeaterStatus.Name(message.heater_2))
    print('filter -', message.FilterStatus.Name(message.filter))
    print('onzen -', message.onzen)
    print('ozone -', message.OzoneStatus.Name(message.ozone))
    print('exhaust_fan -', message.exhaust_fan)
    print('sauna -', message.SaunaStatus.Name(message.sauna))
    print('heater_adc -', message.heater_adc)
    print('economy -', message.economy)
    print('current_adc -', message.current_adc)
    print('all_on -', message.all_on)
    print('fogger -', message.fogger)
    print()

    message = arctic_spa_client.fetch_one(MessageType.ONZEN_LIVE)

    print()
    print('OnzenLive')
    print('guid -', message.guid)
    print('orp -', message.orp)
    print('ph_100 -', message.ph_100)
    print('current -', message.current)
    print('voltage -', message.voltage)
    print('current_setpoint -', message.current_setpoint)
    print('voltage_setpoint -', message.voltage_setpoint)
    print('pump1 -', message.pump1)
    print('pump2 -', message.pump2)
    print('orp_state_machine -', message.orp_state_machine)
    print('electrode_state_machine -', message.electrode_state_machine)
    print('electrode_id -', message.electrode_id)
    print('electrode_polarity -', message.Polarity.Name(message.electrode_polarity))
    print('electrode_1_resistance_1 -', message.electrode_1_resistance_1)
    print('electrode_1_resistance_2 -', message.electrode_1_resistance_2)
    print('electrode_2_resistance_1 -', message.electrode_2_resistance_1)
    print('electrode_2_resistance_2 -', message.electrode_2_resistance_2)
    print('command_mode -', message.command_mode)
    print('electrode_mAH -', message.electrode_mAH)
    print('ph_color -', message.Color.Name(message.ph_color))
    print('orp_color -', message.Color.Name(message.orp_color))
    print('electrode_wear -', message.electrode_wear)
    print()

    message = arctic_spa_client.fetch_one(MessageType.CONFIGURATION)

    print()
    print('Configuration')
    print('pump1 -', message.pump1)
    print('pump2 -', message.pump2)
    print('pump3 -', message.pump3)
    print('pump4 -', message.pump4)
    print('pump5 -', message.pump5)
    print('blower1 -', message.blower1)
    print('blower2 -', message.blower2)
    print('lights -', message.lights)
    print('stereo -', message.stereo)
    print('heater1 -', message.heater1)
    print('heater2 -', message.heater2)
    print('filter -', message.filter)
    print('onzen -', message.onzen)
    print('ozone_peak_1 -', message.ozone_peak_1)
    print('ozone_peak_2 -', message.ozone_peak_2)
    print('exhaust_fan -', message.exhaust_fan)
    print('powerlines -', message.Phase.Name(message.powerlines))
    print('breaker_size -', message.breaker_size)
    print('smart_onzen -', message.smart_onzen)
    print('fogger -', message.fogger)
    print('sds -', message.sds)
    print('yess -', message.yess)
    print()

    message = arctic_spa_client.fetch_one(MessageType.INFORMATION)

    print()
    print('Information')
    print('pack_serial_number -', message.pack_serial_number)
    print('pack_firmware_version -', message.pack_firmware_version)
    print('pack_hardware_version -', message.pack_hardware_version)
    print('pack_product_id -', message.pack_product_id)
    print('pack_board_id -', message.pack_board_id)
    print('topside_product_id -', message.topside_product_id)
    print('topside_software_version -', message.topside_software_version)
    print('guid -', message.guid)
    print('spa_type -', message.SpaType.Name(message.spa_type))
    print('website_registration -', message.website_registration)
    print('website_registration_confirm -', message.website_registration_confirm)
    print('mac_address -', message.mac_address)
    print('firmware_version -', message.firmware_version)
    print('product_code -', message.product_code)
    print('var_software_version -', message.var_software_version)
    print('spaboy_firmware_version -', message.spaboy_firmware_version)
    print('spaboy_hardware_version -', message.spaboy_hardware_version)
    print('spaboy_product_id -', message.spaboy_product_id)
    print('spaboy_serial_number -', message.spaboy_serial_number)
    print('rfid_firmware_version -', message.rfid_firmware_version)
    print('rfid_hardware_version -', message.rfid_hardware_version)
    print('rfid_product_id -', message.rfid_product_id)
    print('rfid_serial_number -', message.rfid_serial_number)
    print()

    message = arctic_spa_client.fetch_one(MessageType.SETTINGS)

    print()
    print('Settings')
    print('max_filtration_frequency -', message.max_filtration_frequency)
    print('min_filtration_frequency -', message.min_filtration_frequency)
    print('filtration_frequency -', message.filtration_frequency)
    print('max_filtration_duration -', message.max_filtration_duration)
    print('min_filtration_duration -', message.min_filtration_duration)
    print('filtration_duration -', message.filtration_duration)
    print('max_onzen_hours -', message.max_onzen_hours)
    print('min_onzen_hours -', message.min_onzen_hours)
    print('onzen_hours -', message.onzen_hours)
    print('max_onzen_cycles -', message.max_onzen_cycles)
    print('min_onzen_cycles -', message.min_onzen_cycles)
    print('onzen_cycles -', message.onzen_cycles)
    print('max_ozone_hours -', message.max_ozone_hours)
    print('min_ozone_hours -', message.min_ozone_hours)
    print('ozone_hours -', message.ozone_hours)
    print('max_ozone_cycles -', message.max_ozone_cycles)
    print('min_ozone_cycles -', message.min_ozone_cycles)
    print('ozone_cycles -', message.ozone_cycles)
    print('filter_suspension -', message.filter_suspension)
    print('flash_lights_on_error -', message.flash_lights_on_error)
    print('temperature_offset -', message.temperature_offset)
    print('sauna_duration -', message.sauna_duration)
    print('min_temperature -', message.min_temperature)
    print('max_temperature -', message.max_temperature)
    print('filtration_offset -', message.filtration_offset)
    print('spaboy_hours -', message.spaboy_hours)
    print()

    print('disconnecting')
    arctic_spa_client.disconnect()


if __name__ == '__main__':
    main()
