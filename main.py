#!/usr/bin/env python3
# Controlling my Govee H6002, Bluetooth name of "ihoment_H6002_A18B"
# TODO support more than one light, if I ever get another one
import datetime
import logging
import sys
import time
from functools import reduce
from operator import xor

import astral
import click
import pexpect

LIGHT = "7C:A6:B0:3F:A1:8B"  # CHANGEME
UUID_CONTROL_CHARACTERISTIC = "00010203-0405-0607-0809-0a0b0c0d2b11"
HANDLE = "0x0011"
HCI_DEVICE = "hci0"
COMMAND = "gatttool"
ARGS = [
    "--adapter",
    HCI_DEVICE,
    "--interactive",
    "--device",
    LIGHT,
]  # gatttool non-interactive does not work for me, thus pexpect needed
COMMAND_RETRIES = 10
PACKET_IDENTIFIER = {"INDICATOR": 0x33, "KEEPALIVE": 0xAA}  # Indicator
PACKET_TYPE = {"POWER": 0x01, "BRIGHTNESS": 0x04}
PACKET_TYPE_ARGUMENT = {
    "POWER": {"ON": 0x01, "OFF": 0x00},
    "BRIGHTNESS": {0: 0x00, 255: 0xFF},  # Just for reference
}
PACKET_PAD = 0x00
PACKET_SIZE = 20  # bytes
LOCATION = "Los Angeles"


class Config(object):
    def __init__(self):
        self.verbosity = False


pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.option(
    "--verbosity",
    type=click.Choice(["info", "debug", "warning"], case_sensitive=False),
    default="info",
)
def cli(verbosity):
    """Control Govee light via Bluetooth LE as best as possible"""
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=verbosity.upper()
    )


def govee_set_brightness(percent):
    """Can't really notice brightness > 30%"""
    logging.debug(f"govee_set_brightness: percent: {percent}")
    packet = bytearray(
        [
            PACKET_IDENTIFIER["INDICATOR"],
            PACKET_TYPE["BRIGHTNESS"],
            round(percent / 100 * 0xFF),
        ]
    )
    send_packet(add_data(packet))


def govee_set_power(state):
    """Set power to on or off"""
    logging.debug(f"govee_set_power: state: {state}")
    packet = bytearray(
        [
            PACKET_IDENTIFIER["INDICATOR"],
            PACKET_TYPE["POWER"],
            PACKET_TYPE_ARGUMENT["POWER"][state.upper()],
        ]
    )
    send_packet(add_data(packet))


def add_data(packet):
    """Add padding to packet, plus the XOR byte. Total packet is 20 bytes."""
    for _ in range(
        (PACKET_SIZE - 1) - len(packet)
    ):  # Pad the rest of packet minus 1 byte, with PACKET_PAD
        packet.append(PACKET_PAD)
    # https://stackoverflow.com/questions/33970373/xor-of-elements-of-a-list-tuple
    packet.append(reduce(xor, map(int, packet)))
    return packet.hex()


def send_packet(packet):
    """Send a packet, in hex format. Keeping it simple with retry logic.
    BLE is a bit flaky with this bulb, believe it's due to the required
    2 second keep-alive packet. Rather than try to implement
    that, just retry 10 times.
    """
    retries = 0
    error = True
    logging.debug(f"send_packet: packet: {packet}")
    while retries < COMMAND_RETRIES and error is True:
        try:
            child = pexpect.spawn(COMMAND, ARGS)
            if logging.DEBUG >= logging.root.level:
                child.logfile = sys.stdout.buffer
            child.expect(r"\[LE\]>", timeout=5)
            child.sendline("connect")
            child.expect(r"Connection successful", timeout=7)  # Usually fails
            child.sendline(f"char-write-cmd {HANDLE} {packet}")
            child.expect(r"\[LE\]>", timeout=5)
            child.sendline("quit")
            child.expect(pexpect.EOF)
            error = False
        except pexpect.exceptions.TIMEOUT:
            retries += 1
            error = True
            child.sendline("quit")  # Just restart the whole gatttool
            logging.debug(f"send_packet: retries: {retries}")
            time.sleep(5)


@cli.command()
@click.option(
    "--on",
    "transformation",
    flag_value="on",
)
@click.option("--off", "transformation", flag_value="off")
def power(transformation):
    """Turn on or off the light"""
    if transformation:
        govee_set_power(transformation.upper())
    else:
        raise click.UsageError("Need --on or --off option")


@cli.command()
@click.option("--percent", required=True, type=click.IntRange(1, 100, clamp=True))
def brightness(percent):
    """From 1 to 100. For my H6002, brightness over about 30% is not noticeably
    different than 100%. Zero percent is not 'off'."""
    send_packet(govee_set_brightness(percent))


@cli.command()
def home_automation():
    """Turn on at dusk and turn off by 22:00"""
    a = astral.Astral()
    location = a[LOCATION]
    local_now = datetime.datetime.now()
    if local_now.hour == 22:
        govee_set_power("off")
    elif local_now.hour >= 21 and local_now.minute >= 45:
        govee_set_brightness(5)
    elif (
        datetime.datetime.now(datetime.timezone.utc)
        >= location.sun(local=False)["dusk"]
    ):
        govee_set_power("on")
        govee_set_brightness(100)


if __name__ == "__main__":
    cli()
