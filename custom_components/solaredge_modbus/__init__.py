import logging

import voluptuous as vol

from pyModbusTCP.client import ModbusClient

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery

DOMAIN="solaredge_modbus"

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default="SolarEdge Modbus"): cv.string,
        vol.Optional("port", default=1502): cv.positive_int,
        vol.Optional(CONF_SCAN_INTERVAL, default=1): cv.positive_int,
        vol.Optional("read_meter1", default=False): cv.boolean,
        vol.Optional("read_battery", default=False): cv.boolean,
    })},
    extra=vol.ALLOW_EXTRA,
)


_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    """Set up the SolarEdge component."""
    conf = config.get(DOMAIN)

    _LOGGER.debug("creating modbus client begin")

    host = conf[CONF_HOST]
    port = conf["port"]

    client = ModbusClient(host, port=port, unit_id=1, auto_open=True)
    hass.data[DOMAIN] = client

    _LOGGER.debug("creating modbus client done")

    for component in ["sensor"]:
        discovery.load_platform(hass, component, DOMAIN, {CONF_NAME: DOMAIN, CONF_SCAN_INTERVAL: conf[CONF_SCAN_INTERVAL], "read_meter1": conf["read_meter1"], "read_battery": conf["read_battery"]}, config)

    return True
