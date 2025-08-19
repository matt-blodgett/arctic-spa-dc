# Arctic Spa Direct Connect

A Python interface for communicating directly with Arctic Spa brand hot tubs.

## Overview

Arctic Spa hot tubs communicate over TCP using protobuf messages. By writing a packet with one or more message type integers to the connection with the device, the onboard controller in the hot tub will respond to each requested message type with a corresponding protobuf message.

In this way, we can gather practically any desired information about the hot tub. This includes the current status of the pumps, lights and heaters as well as details on the specific hot tubs capabilities (whether it has 3 pumps or 4 for instance), serial numbers, firmware versions and more.

We can also send "command" packets to do things such as set the temperature setpoint, pump statuses, lights, etc.

## Setup

To compile the protobuf message definitions:

1. Run `apt update && apt install -y protobuf-compiler`
2. Run `make`

## Usage

Create a client instance and connect:

```python
from arctic_spa_dc.client import ArcticSpaClient
from arctic_spa_dc.client import MessageType
from arctic_spa_dc.client import CommandType


async def main():
    host = '192.168.0.0'

    arctic_spa_client = ArcticSpaClient(host)

    connected = await arctic_spa_client.connect()
    if not connected:
        exit(-1)
```

Now we can request a status update from the device:

```python
message = await arctic_spa_client.fetch_one(MessageType.LIVE)
print(message)
```

Or send a command to turn on the lights:

```python
await arctic_spa_client.write_command(CommandType.LIGHTS, True)
```

For more details, see [/example/demo.py](./example/demo.py)

## Acknowledgments

Inspired by, and uses code from, the following projects:

| Author | Repository |
| -| - |
| Steve Pomeroy | https://github.com/xxv/arctic-spa |
| Patrick Ohlson | https://github.com/Patrick-Ohlson/SpaBoii |

## License

Licensed under the [Apache 2.0 software license](./LICENSE).

## Disclaimer

This project is not affiliated in any way with the Arctic Spas company or brand.

A hot tub is a significant financial investment and there is inherent risk in using unauthorized third party tools to poke around under the hood.

You take full responsibility for any issues arising from the use of this code.
