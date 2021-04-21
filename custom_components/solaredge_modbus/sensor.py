import datetime
import asyncio
import traceback

from time import sleep

from datetime import timedelta
import logging

from homeassistant.const import CONF_SCAN_INTERVAL

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from homeassistant.helpers.entity import Entity

from . import DOMAIN as SOLAREDGE_DOMAIN
from .meter_sensor import SolarEdgeMeterSensor

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:power-plug"
SCAN_INTERVAL = timedelta(seconds=5)

values = {}

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return

    _LOGGER.debug("fetching modbus client")
    client = hass.data.get(SOLAREDGE_DOMAIN)
    scan_interval = discovery_info[CONF_SCAN_INTERVAL]
    unit_id = discovery_info["unit_id"]
    read_meter1 = discovery_info["read_meter1"]
    read_meter2 = discovery_info["read_meter2"]
    read_meter3 = discovery_info["read_meter3"]
    additional_inverter_unit_id = discovery_info["additional_inverter_unit_id"]

    async_add_entities([SolarEdgeModbusSensor(client, unit_id, scan_interval)], True)

    if additional_inverter_unit_id > 0:
        async_add_entities([SolarEdgeModbusSensor(client, additional_inverter_unit_id, scan_interval)], True)

    if read_meter1:
        async_add_entities([SolarEdgeMeterSensor(client, unit_id, 1, scan_interval)], True)

    if read_meter2:
        async_add_entities([SolarEdgeMeterSensor(client, unit_id, 2, scan_interval)], True)

    if read_meter3:
        async_add_entities([SolarEdgeMeterSensor(client, unit_id, 3, scan_interval)], True)


class SolarEdgeModbusSensor(Entity):
    def __init__(self, client, unit_id, scan_interval):
        _LOGGER.debug("creating modbus sensor")

        self._client = client

        self._scan_interval = scan_interval
        self._state = 0
        self._device_state_attributes = {}
        self._unit_id = unit_id

    def round(self, floatval):
        return round(floatval, 2)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._device_state_attributes

    @property
    def state(self):
        """Return the state of the device."""
        return self._state


    async def async_added_to_hass(self):
        _LOGGER.debug("added to hass, starting loop")
        loop = self.hass.loop
        task = loop.create_task(self.modbus_loop())

    async def modbus_loop(self):
        sleep(0.005)
        while True:
            try:		        
                reading = self._client.read_holding_registers(address=40069, count=39, unit=self._unit_id)
                if reading:
                    data = BinaryPayloadDecoder.fromRegisters(reading.registers, byteorder=Endian.Big, wordorder=Endian.Big)

                    data.skip_bytes(4)
                    #data.decode_16bit_uint()
                    #data.decode_16bit_uint()

                    #40072-40075
                    ac_total_current = data.decode_16bit_uint()
                    ac_current_phase_a = data.decode_16bit_uint()
                    ac_current_phase_b = data.decode_16bit_uint()
                    ac_current_phase_c = data.decode_16bit_uint()

                    #40076
                    ac_current_scalefactor = 10**data.decode_16bit_int()

                    values['ac_total_current'] = self.round(ac_total_current * ac_current_scalefactor)
                    values['ac_current_phase_a'] = self.round(ac_current_phase_a * ac_current_scalefactor)
                    values['ac_current_phase_b'] = self.round(ac_current_phase_b * ac_current_scalefactor)
                    values['ac_current_phase_c'] = self.round(ac_current_phase_c * ac_current_scalefactor)

                    #40077-40079, AC Voltage AB, BC and CA
                    ac_voltage_phase_ab = data.decode_16bit_uint()
                    ac_voltage_phase_bc = data.decode_16bit_uint()
                    ac_voltage_phase_ca = data.decode_16bit_uint()


                    #40080-40082, AC Voltage AN, BN and CN
                    ac_voltage_phase_a = data.decode_16bit_uint()
                    ac_voltage_phase_b = data.decode_16bit_uint()
                    ac_voltage_phase_c = data.decode_16bit_uint()

                    #40083
                    ac_voltage_phase_scalefactor = 10**data.decode_16bit_int()

                    values['ac_voltage_phase_ab'] = self.round(ac_voltage_phase_ab * ac_voltage_phase_scalefactor)
                    values['ac_voltage_phase_bc'] = self.round(ac_voltage_phase_bc * ac_voltage_phase_scalefactor)
                    values['ac_voltage_phase_ca'] = self.round(ac_voltage_phase_ca * ac_voltage_phase_scalefactor)
		
                    values['ac_voltage_phase_a'] = self.round(ac_voltage_phase_a * ac_voltage_phase_scalefactor)
                    values['ac_voltage_phase_b'] = self.round(ac_voltage_phase_b * ac_voltage_phase_scalefactor)
                    values['ac_voltage_phase_c'] = self.round(ac_voltage_phase_c * ac_voltage_phase_scalefactor)

                    #40084
                    ac_power_output = data.decode_16bit_int()

                    #40085
                    ac_power_scalefactor = 10**data.decode_16bit_int()
                    values['ac_power_output'] = self.round(ac_power_output * ac_power_scalefactor)

                    #40086 frequency
                    freq = data.decode_16bit_uint()
                    freq_scalefactor = 10 ** data.decode_16bit_int()
                    values['ac_frequency'] = self.round(freq * freq_scalefactor)

                    #AC VA
                    ac_va = data.decode_16bit_int()
                    ac_va_scalefactor = 10 ** data.decode_16bit_int()
                    values['ac_va'] = self.round(ac_va * ac_va_scalefactor)

                    #AC VAR
                    ac_var = data.decode_16bit_int()
                    ac_var_scalefactor = 10 ** data.decode_16bit_int()
                    values['ac_var'] = self.round(ac_var * ac_var_scalefactor)

                    #AC PF
                    ac_pf = data.decode_16bit_int()
                    ac_pf_scalefactor = 10 ** data.decode_16bit_int()
                    values['ac_pf'] = self.round(ac_pf * ac_pf_scalefactor)

                    #40094
                    lifetime = data.decode_32bit_uint()

                    #40095
                    lifetimeScaleFactor = 10**data.decode_16bit_uint()

                    #Total production entire lifetime
                    values['ac_lifetimeproduction'] = self.round(lifetime * lifetimeScaleFactor)

                    #40097 DC Current
                    dc_current = data.decode_16bit_uint()
                    dc_current_scalefactor = 10**data.decode_16bit_int()
                    values['dc_current'] = self.round(dc_current * dc_current_scalefactor)


                    #40099 DC Voltage
                    dc_voltage = data.decode_16bit_uint()
                    dc_voltage_scalefactor = 10**data.decode_16bit_int()
                    values['dc_voltage'] = self.round(dc_voltage * dc_voltage_scalefactor)


                    #40101 DC Power input
                    dc_power = data.decode_16bit_int()
                    dc_power_scalefactor = 10**data.decode_16bit_int()
                    values['dc_power_input'] = self.round(dc_power * dc_power_scalefactor)

                    #skip some bytes to read heat sink temperature and scale factor
                    data.skip_bytes(2)
                    temp_sink = data.decode_16bit_int()
                    data.skip_bytes(4)
                    temp_sink_scalefactor = 10 ** data.decode_16bit_int()
                    values['heat_sink_temperature'] = self.round(temp_sink * temp_sink_scalefactor)
		
                    #40108 Status
                    values['status'] = data.decode_16bit_uint()

                    #calculate efficiency
                    if values['dc_power_input'] > 0:
                        values['computed_inverter_efficiency'] = self.round( values['ac_power_output'] / values['dc_power_input'] * 100 )
                    else:
                        values['computed_inverter_efficiency'] = 0

                    #debug-print entire dictionary
                    #for x in values.keys():
                    #    print(x +" => " + str(values[x]))

                    # Skip if increamenting counter has gone to 0, or become too large, this happens on inverter startup
                    validValue = values['ac_lifetimeproduction'] > 0
                    try:
                        float(values['ac_lifetimeproduction'])
                    except Exception as e:
                        validValue = False

                    if validValue:
                        #main state is power production, other values can be fetched as attributes
                        self._state = values['ac_power_output']
                        self._device_state_attributes = values

                        #tell HA there is new data
                        self.async_schedule_update_ha_state()

                else:
                    if self._client.last_error() > 0:
                        _LOGGER.error(f'error {self._client.last_error()}')

            except Exception as e:
                _LOGGER.error(f'exception: {e}')
                print(traceback.format_exc())

            await asyncio.sleep(self._scan_interval)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"SolarEdge Modbus {self._unit_id}"

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return "W"

    @property
    def unique_id(self):
        return f"SolarEdge {self._unit_id}"
