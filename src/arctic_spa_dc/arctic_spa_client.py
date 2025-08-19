import asyncio
import struct
from enum import IntEnum

from arctic_spa_dc.proto import arctic_spa_dc_pb2
from arctic_spa_dc.packet import Packet


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
        MessageType.LIVE: arctic_spa_dc_pb2.SpaLive,
        MessageType.SETTINGS: arctic_spa_dc_pb2.Settings,
        MessageType.CONFIGURATION: arctic_spa_dc_pb2.Configuration,
        MessageType.INFORMATION: arctic_spa_dc_pb2.Information,
        MessageType.ONZEN_LIVE: arctic_spa_dc_pb2.OnzenLive
    }

    def __init__(self, message_type: MessageType, counter: int, checksum: bytes, payload: bytes):
        if message_type not in self.MESSAGE_TYPE_DECODERS:
            raise ValueError(f'No protobuf class defined to decode message type "{message_type.name}"')

        self.message_type = message_type
        self.counter = counter
        self.checksum = checksum
        self.payload = payload
        self.data = self._decode(payload)

    def _decode(self, payload: bytes):
        decoder_class = self.MESSAGE_TYPE_DECODERS.get(self.message_type)

        if not decoder_class:
            raise ValueError(f'No protobuf class defined to decode message type "{self.message_type.name}"')

        data = decoder_class()
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


class SpaProtocol:
    """
    Spa network protocol decoder
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

        if len(data) < SpaProtocol.HEADER_SIZE:
            raise DecodeError(f'Expecting at least {SpaProtocol.HEADER_SIZE} bytes, got {len(data)}')

        if data[0:4] != SpaProtocol.PREAMBLE:
            raise DecodeError('Data does not start with correct preamble')

        header = struct.unpack('!xxxxBBBBIIHH', data[0:SpaProtocol.HEADER_SIZE])

        message_type = MessageType(header[6])
        length = header[7]
        payload = data[SpaProtocol.HEADER_SIZE : (SpaProtocol.HEADER_SIZE + length)]

        message = None

        if message_type != MessageType.HEARTBEAT:
            checksum = bytes(header[0:4])
            counter = header[4]

            if message_type in Message.MESSAGE_TYPE_DECODERS:
                message = Message(message_type, counter, checksum, payload)

        remainder = data[SpaProtocol.HEADER_SIZE + length :]

        return message, remainder


class ArcticSpaClient:
    """
    Interface for communicating with Arctic Spa hot tubs
    """

    def __init__(self, host: str = None, port: int = None):
        """
        Configures a new client

        Initialize a connection by calling `.connect()` or using the `async with` keywords
        Close the connection when finished by calling `.disconnect()`

        The client can be used in two ways:
            * Calling `.poll_messages()`
            * Calling `.write_requested_messages()` and then reading
                back with `.read_messages()` or `.read_raw_stream_data()`
        """

        self.host = host
        self.port = port or 65534

        self._proto = SpaProtocol()

        self._reader = None
        self._writer = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()

    def __del__(self):
        """
        Attempt to close connection if not already closed
        """

        if self.is_connected():
            try:
                asyncio.run(self.disconnect())
            except Exception:
                pass

    async def connect(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: float | None = 5.0,
        attempts: int = 1
    ) -> bool:
        """
        Opens a connection to the host device
        """

        await self.disconnect()

        if host:
            self.host = host

        if port:
            self.port = port

        if not self.host:
            raise ValueError('No host value specified; cannot connect!')

        attempt = 0

        while attempt < attempts:
            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=timeout
                )
            except TimeoutError:
                attempt += 1
            except (OSError, ConnectionRefusedError):
                return False

        return self.is_connected()

    async def disconnect(self) -> None:
        """
        Closes the connection to the host device
        """

        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

            self._reader = None
            self._writer = None

    def is_connected(self) -> bool:
        """
        Checks if there is an active connection to the host device
        """

        if self._writer:
            return not self._writer.is_closing()
        return False

    @staticmethod
    def _get_message_type_packet_bytes(message_type: MessageType) -> bytes:
        """
        Crafts a command packet in bytes based on the numeric message type
        """

        packet_type = message_type.value
        packet = Packet(packet_type, bytearray())
        packet_bytes = packet.serialize()
        return packet_bytes

    async def write_requested_messages(
        self,
        message_types: MessageType | list[MessageType] | tuple[MessageType] | set[MessageType]
    ) -> None:
        """
        Requests the specified messages from the host device by crafting a command packet
            and writing it over the open connection
        """

        if not self.is_connected():
            raise ConnectionError('No open connection')

        if isinstance(message_types, MessageType):
            message_types = [message_types]
        elif isinstance(message_types, (list, tuple)):
            message_types = set(message_types)

        command_packet = b''
        for message_type in message_types:
            command_packet += self._get_message_type_packet_bytes(message_type)

        self._writer.write(command_packet)
        await self._writer.drain()

    async def read_raw_stream_data(self) -> bytes:
        """
        Reads data sent over the network from the host device
        """

        return await self._reader.read(4096)

    async def read_messages(self) -> list[Message]:
        """
        Reads data sent over the network from the host device and returns any received and parsed protobuf messages
        """

        if not self.is_connected():
            raise ConnectionError('No open connection')

        data = await self.read_raw_stream_data()

        return self._proto.decode(data)

    async def _poll_messages(
        self,
        message_types: list[MessageType] | tuple[MessageType] | set[MessageType]
    ) -> dict:
        """
        Polls the host device until all requested message data has been recieved
        """

        requested_messages = {
            message_type.value: None for message_type in message_types
        }

        missing_messages = True
        while missing_messages:
            for message in await self.read_messages():
                if message:
                    requested_messages[message.message_type.value] = message
            missing_messages = None in requested_messages.values()

        return requested_messages

    async def poll_messages(
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

        if not self.is_connected():
            raise ConnectionError('No open connection')

        if isinstance(message_types, MessageType):
            message_types = [message_types]
        elif isinstance(message_types, (list, tuple)):
            message_types = set(message_types)

        await self.write_requested_messages(message_types)

        messages = await asyncio.wait_for(
            self._poll_messages(
                message_types=message_types
            ),
            timeout=timeout
        )
        # except asyncio.TimeoutError:

        return messages
