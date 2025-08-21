import time
import socket
import struct

from enum import IntEnum
from enum import StrEnum

from arctic_spa_dc.packet import Packet

from arctic_spa_dc.proto import Live_pb2
from arctic_spa_dc.proto import Command_pb2
from arctic_spa_dc.proto import Settings_pb2
from arctic_spa_dc.proto import Configuration_pb2
from arctic_spa_dc.proto import Peak_pb2
from arctic_spa_dc.proto import Clock_pb2
from arctic_spa_dc.proto import Information_pb2
from arctic_spa_dc.proto import Error_pb2
from arctic_spa_dc.proto import Router_pb2
from arctic_spa_dc.proto import Filter_pb2
from arctic_spa_dc.proto import Peripheral_pb2
from arctic_spa_dc.proto import OnzenLive_pb2
from arctic_spa_dc.proto import OnzenSettings_pb2
from arctic_spa_dc.proto import MobileAuthenticate_pb2
from arctic_spa_dc.proto import MobileAvailableSpas_pb2
from arctic_spa_dc.proto import MobileSpaRegistration_pb2
from arctic_spa_dc.proto import MobileWifiDetails_pb2
from arctic_spa_dc.proto import Lpc_pb2


class MessageType(IntEnum):
    LIVE = 0
    COMMAND = 1
    SETTINGS = 2
    CONFIGURATION = 3
    PEAK = 4
    CLOCK = 5
    INFORMATION = 6
    ERROR = 7
    FIRMWARE = 8
    ROUTER = 9
    HEARTBEAT = 10
    FILTERS = 13
    PERIPHERAL = 16
    ONZEN_LIVE = 48
    ONZEN_COMMAND = 49
    ONZEN_SETTINGS = 50
    MOBILE_AUTHENTICATE = 80
    MOBILE_SPA = 81
    MOBILE_AVAILABLE_SPAS = 82
    MOBILE_ASSOCIATE_ACK = 83
    MOBILE_SPA_REGISTRATION = 84
    MOBILE_WIFI_DETAILS = 85
    lpc_live = 112
    lpc_command = 113
    lpc_info = 114
    lpc_config = 115
    lpc_preferences = 116
    lpc_lights = 117
    lpc_schedule = 118
    lpc_peak_devices = 119
    lpc_clock = 120
    lpc_error = 121
    lpc_measurements = 122
    lpc_diagnostic_command = 123
    lpc_power = 124
    lpc_enabled_devices = 125
    reset = 127
    lpc_android_topside_info = 144
    firmware_success = 194
    firmware_failure = 195
    firmware_started = 196


class Message:
    """
    Wrapper for a protobuf message
    """

    MESSAGE_TYPE_DECODERS = {
        MessageType.LIVE: Live_pb2.Live,
        MessageType.COMMAND: Command_pb2.Command,
        MessageType.SETTINGS: Settings_pb2.Settings,
        MessageType.CONFIGURATION: Configuration_pb2.Configuration,
        MessageType.PEAK: Peak_pb2.Peak,
        MessageType.CLOCK: Clock_pb2.Clock,
        MessageType.INFORMATION: Information_pb2.Information,
        MessageType.ERROR: Error_pb2.Error,
        MessageType.ROUTER: Router_pb2.Router,
        MessageType.FILTERS: Filter_pb2.Filter,
        MessageType.PERIPHERAL: Peripheral_pb2.Peripheral,
        MessageType.ONZEN_LIVE: OnzenLive_pb2.OnzenLive,
        MessageType.ONZEN_SETTINGS: OnzenSettings_pb2.OnzenSettings,
        MessageType.MOBILE_AUTHENTICATE: MobileAuthenticate_pb2.MobileAuthenticate,
        MessageType.MOBILE_AVAILABLE_SPAS: MobileAvailableSpas_pb2.MobileAvailableSpas,
        MessageType.MOBILE_SPA_REGISTRATION: MobileSpaRegistration_pb2.MobileSpaRegistration,
        MessageType.MOBILE_WIFI_DETAILS: MobileWifiDetails_pb2.MobileWifiDetails,
        MessageType.lpc_live: Lpc_pb2.lpc_live,
        MessageType.lpc_command: Lpc_pb2.lpc_command,
        MessageType.lpc_info: Lpc_pb2.lpc_info,
        MessageType.lpc_config: Lpc_pb2.lpc_config,
        MessageType.lpc_preferences: Lpc_pb2.lpc_preferences,
        MessageType.lpc_lights: Lpc_pb2.lpc_lights,
        MessageType.lpc_schedule: Lpc_pb2.lpc_schedule,
        MessageType.lpc_peak_devices: Lpc_pb2.lpc_peak_devices,
        MessageType.lpc_clock: Lpc_pb2.lpc_clock,
        MessageType.lpc_error: Lpc_pb2.lpc_error,
        MessageType.lpc_measurements: Lpc_pb2.lpc_measurements,
        MessageType.lpc_diagnostic_command: Lpc_pb2.lpc_diagnostic_command,
        MessageType.lpc_power: Lpc_pb2.lpc_power
    }

    def __init__(self, message_type: MessageType, counter: int, checksum: bytes, payload: bytes):
        self.decoder = self.MESSAGE_TYPE_DECODERS.get(message_type)

        if not self.decoder:
            raise ValueError(f'No protobuf class defined to decode message type "{message_type.name}"')

        self.message_type = message_type
        self.counter = counter
        self.checksum = checksum
        self.payload = payload
        self.data = self._decode(payload)

    def _decode(self, payload: bytes):
        data = self.decoder()
        data.ParseFromString(payload)
        return data

    def _checksum_str(self) -> str:
        return ''.join(map(lambda digit: f'{digit:0X}', self.checksum))

    def __getattr__(self, __name: str):
        return getattr(self.data, __name)

    def __str__(self):
        s = f'<{self.message_type.name}'
        s += f' counter: {self.counter},'
        s += f' checksum: {self._checksum_str()}>'
        s += f'\ndata:\n{self.data}\nend data'
        return s


class DecodeError(Exception):
    """
    Error decoding a message
    """

    def __init__(self, reason_str: str):
        super().__init__(reason_str)


class ArcticSpaProtocol:
    """
    Network protocol decoder
    """

    HEADER_SIZE = 20
    PREAMBLE = b'\xab\xad\x1d\x3a'

    def decode(self, data: bytes) -> list[Message]:
        """
        Decodes the raw data into a list of messages
        """
        messages = []

        to_decode = data

        while len(to_decode) > 0:
            message, remainder = self.decode_one(to_decode)
            messages.append(message)

            to_decode = remainder

        return messages

    def decode_one(self, data: bytes) -> tuple[Message, bytes]:
        """
        Decodes the first message of the data and return any undecoded data
        """
        if len(data) < ArcticSpaProtocol.HEADER_SIZE:
            raise DecodeError(f'Expecting at least {ArcticSpaProtocol.HEADER_SIZE} bytes, got {len(data)}')

        if data[0:4] != ArcticSpaProtocol.PREAMBLE:
            raise DecodeError('Data does not start with correct preamble')

        header = struct.unpack('!xxxxBBBBIIHH', data[0:ArcticSpaProtocol.HEADER_SIZE])

        message_type = MessageType(header[6])
        length = header[7]
        payload = data[ArcticSpaProtocol.HEADER_SIZE : (ArcticSpaProtocol.HEADER_SIZE + length)]

        message = None

        if message_type != MessageType.HEARTBEAT:
            checksum = bytes(header[0:4])
            counter = header[4]

            if message_type in Message.MESSAGE_TYPE_DECODERS:
                message = Message(message_type, counter, checksum, payload)

        remainder = data[ArcticSpaProtocol.HEADER_SIZE + length :]

        return message, remainder


class CommandType(StrEnum):
    TEMPERATURE_SETPOINT_FAHRENHEIT = 'set_temperature_setpoint_fahrenheit'
    PUMP_1 = 'set_pump_1'
    PUMP_2 = 'set_pump_2'
    PUMP_3 = 'set_pump_3'
    PUMP_4 = 'set_pump_4'
    PUMP_5 = 'set_pump_5'
    BLOWER_1 = 'set_blower_1'
    BLOWER_2 = 'set_blower_2'
    LIGHTS = 'set_lights'
    STEREO = 'set_stereo'
    FILTER = 'set_filter'
    ONZEN = 'set_onzen'
    OZONE = 'set_ozone'
    EXHAUST_FAN = 'set_exhaust_fan'
    SAUNA_STATE = 'set_sauna_state'
    SAUNA_TIME_LEFT = 'set_sauna_time_left'
    ALL_ON = 'set_all_on'
    FOGGER = 'set_fogger'
    SPABOY_BOOST = 'set_spaboy_boost'
    PACK_RESET = 'set_pack_reset'
    LOG_DUMP = 'set_log_dump'
    SDS = 'set_sds'
    YESS = 'set_yess'


class PumpStatus(IntEnum):
    PUMP_OFF = 0
    PUMP_LOW = 1
    PUMP_HIGH = 2


class SaunaState(IntEnum):
    SAUNA_IDLE = 0
    SAUNA_TIMER = 1
    SAUNA_PRESET_A = 2
    SAUNA_PRESET_B = 3
    SAUNA_PRESET_C = 4


MIN_TEMPERATURE = 59
MAX_TEMPERATURE = 104


def assert_connected(func):
    def wrapper(self, *args, **kwargs):
        if not self.is_connected():
            raise ConnectionError('No open connection')
        return func(self, *args, **kwargs)
    return wrapper


class ArcticSpaClient:
    """
    Interface for communicating with Arctic Spa hot tubs
    """

    def __init__(self, host: str = None, port: int = None):
        """
        Configures a new client

        Initialize a connection by calling `.connect()` or using the `with` keyword
        Close the connection when finished by calling `.disconnect()`

        The client can be used in a few ways:
            * Calling `.poll_messages()` to receive multiple requested messages
            * Calling `.fetch_one()` to receive a single requested message
            * Calling `.write_requested_messages()` and then reading
                back with `.read_messages()` or `.read_raw_stream_data()`
        """
        self.host = host
        self.port = port or 65534

        self._proto = ArcticSpaProtocol()
        self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.disconnect()

    def __del__(self):
        """
        Attempt to close connection if not already closed
        """
        if self.is_connected():
            self._conn.close()

    def connect(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: float | None = 5.0,
        attempts: int = 1
    ) -> bool:
        """
        Opens a connection to the host device
        """
        self.disconnect()

        if host:
            self.host = host

        if port:
            self.port = port

        if not self.host:
            raise ValueError('No host value specified; cannot connect!')

        attempt = 0
        while attempt < attempts:
            try:
                self._conn = socket.create_connection((self.host, self.port), timeout)
                break
            except socket.timeout:
                attempt += 1
            except (OSError, ConnectionRefusedError):
                return False

        return self.is_connected()

    def disconnect(self) -> None:
        """
        Closes the connection to the host device
        """
        if self._conn:
            try:
                self._conn.shutdown(2)
                self._conn.close()
            except Exception:
                pass

            self._conn = None

    def is_connected(self) -> bool:
        """
        Checks if there is an active connection to the host device
        """
        return self._conn is not None

    @staticmethod
    def _get_message_type_packet_bytes(message_type: MessageType) -> bytes:
        """
        Crafts a command packet in bytes based on the numeric message type
        """
        packet_type = message_type.value
        packet = Packet(packet_type, bytearray())
        packet_bytes = packet.serialize()
        return packet_bytes

    @assert_connected
    def write_requested_messages(
        self,
        message_types: MessageType | list[MessageType] | tuple[MessageType] | set[MessageType]
    ) -> None:
        """
        Requests the specified messages from the host device by crafting a command packet
            and writing it over the open connection
        """
        if isinstance(message_types, MessageType):
            message_types = [message_types]
        elif isinstance(message_types, (list, tuple)):
            message_types = set(message_types)

        command_packet_bytes = b''
        for message_type in message_types:
            command_packet_bytes += self._get_message_type_packet_bytes(message_type)

        self._conn.sendall(command_packet_bytes)

    @assert_connected
    def read_raw_stream_data(self) -> bytes:
        """
        Reads data sent over the network from the host device
        """
        return self._conn.recv(2048)

    @assert_connected
    def read_messages(self) -> list[Message]:
        """
        Reads data sent over the network from the host device and returns any received and parsed protobuf messages
        """
        data = self.read_raw_stream_data()
        return self._proto.decode(data)

    def _poll_messages(
        self,
        message_types: list[MessageType] | tuple[MessageType] | set[MessageType],
        timeout: float | None = 5.0
    ) -> dict:
        """
        Polls the host device until all requested message data has been recieved
        """
        start = time.time()
        requested_messages = {
            message_type: None for message_type in message_types
        }
        missing_messages = True
        while missing_messages:
            if timeout and (time.time() - start) > timeout:
                raise TimeoutError('Timeout waiting for messages')
            for message in self.read_messages():
                if message:
                    requested_messages[message.message_type] = message
            missing_messages = None in requested_messages.values()
        return requested_messages

    @assert_connected
    def poll_messages(
        self,
        message_types: MessageType | list[MessageType] | tuple[MessageType] | set[MessageType],
        timeout: float | None = 5.0
    ) -> dict:
        """
        1. Sends a request to the host device for the requested message types
        2. Waits until all message data has been returned over the connection
        3. Returns the most recent parsed message data of each requested type

        Note: May return message types that were not requested in addition to the requested types.
        """
        if isinstance(message_types, MessageType):
            message_types = [message_types]
        elif isinstance(message_types, (list, tuple)):
            message_types = set(message_types)

        self.write_requested_messages(message_types)
        return self._poll_messages(message_types=message_types, timeout=timeout)

    @assert_connected
    def fetch_one(
        self,
        message_type: MessageType,
        timeout: float | None = 5.0
    ) -> Message:
        """
        Returns only a single message requested from `.poll_messages()`
        """
        messages = self.poll_messages(message_type, timeout=timeout)
        message = messages[message_type]
        return message

    @staticmethod
    def _validate_command(
        command_type: CommandType,
        command_value: int | bool | PumpStatus | SaunaState
    ) -> tuple[str, int] | tuple[str, bool]:
        """
        Validates the requested value based on the command type being set
        """
        command_type_value_class = {
            CommandType.TEMPERATURE_SETPOINT_FAHRENHEIT: int,
            CommandType.PUMP_1: PumpStatus,
            CommandType.PUMP_2: PumpStatus,
            CommandType.PUMP_3: PumpStatus,
            CommandType.PUMP_4: PumpStatus,
            CommandType.PUMP_5: PumpStatus,
            CommandType.BLOWER_1: PumpStatus,
            CommandType.BLOWER_2: PumpStatus,
            CommandType.LIGHTS: bool,
            CommandType.STEREO: bool,
            CommandType.FILTER: bool,
            CommandType.ONZEN: bool,
            CommandType.OZONE: bool,
            CommandType.EXHAUST_FAN: bool,
            CommandType.SAUNA_STATE: SaunaState,
            CommandType.SAUNA_TIME_LEFT: int,
            CommandType.ALL_ON: bool,
            CommandType.FOGGER: bool,
            CommandType.SPABOY_BOOST: bool,
            CommandType.PACK_RESET: bool,
            CommandType.LOG_DUMP: bool,
            CommandType.SDS: bool,
            CommandType.YESS: bool
        }

        value_class = command_type_value_class.get(command_type)

        if not value_class:
            raise ValueError(f'Invalid command type "{command_type}"')

        elif not isinstance(command_value, value_class):
            raise TypeError(f'Invalid type for "{command_type}"; should be "{value_class.__name__}"')

        elif command_type == CommandType.TEMPERATURE_SETPOINT_FAHRENHEIT:
            if command_value < MIN_TEMPERATURE:
                raise ValueError(f'Invalid value of {command_value} for "{command_type}"; less than the minimum temperature of {MIN_TEMPERATURE}')
            elif command_value > MAX_TEMPERATURE:
                raise ValueError(f'Invalid value of {command_value} for "{command_type}"; greater than the maximum temperature of {MAX_TEMPERATURE}')

        property_name = command_type.value
        raw_value = command_value

        if not isinstance(raw_value, (int, bool)):
            raw_value = command_value.value

        return property_name, raw_value

    @assert_connected
    def write_command(
        self,
        command_type: CommandType,
        command_value: int | bool | PumpStatus | SaunaState
    ) -> None:
        """
        Validates the requested update, then crafts and sends a command packet to the host device
        """
        property_name, raw_value = self._validate_command(command_type, command_value)

        command = Command_pb2.Command()
        setattr(command, property_name, raw_value)

        buffer = command.SerializeToString()

        command_packet = Packet(MessageType.COMMAND.value, buffer)
        command_packet_bytes = command_packet.serialize()

        self._conn.sendall(command_packet_bytes)
