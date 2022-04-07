import datetime
import asyncio
import traceback

from time import sleep

from datetime import timedelta
import logging

from homeassistant.const import CONF_SCAN_INTERVAL

from pyModbusTCP.client import ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from homeassistant.helpers.entity import Entity

from . import DOMAIN as SOLAREDGE_DOMAIN

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:power-plug"
SCAN_INTERVAL = timedelta(seconds=5)

values = {}
meter1_values = {}

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return

    _LOGGER.debug("fetching modbus client")
    client = hass.data.get(SOLAREDGE_DOMAIN)
    scan_interval = discovery_info[CONF_SCAN_INTERVAL]
    useMeter1 = discovery_info["read_meter1"]

    async_add_entities([SolarEdgeModbusSensor(client, scan_interval)], True)

    if useMeter1:
        async_add_entities([SolarEdgeMeterSensor(client, scan_interval)], True)


class SolarEdgeModbusSensor(Entity):
    def __init__(self, client, scan_interval):
        _LOGGER.debug("creating modbus sensor")
        print("creating modbus sensor")

        self._client = client

        self._scan_interval = scan_interval
        self._state = 0
        self._device_state_attributes = {}

    def round(self, floatval):
        return round(floatval, 2)

    @property
    def extra_state_attributes(self):
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
        while True:
            try:
                reading = self._client.read_holding_registers(40069, 39)
                if reading:
                    data = BinaryPayloadDecoder.fromRegisters(reading, byteorder=Endian.Big, wordorder=Endian.Big)

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
        return "SolarEdge Modbus"

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
        return "SolarEdge"


class SolarEdgeMeterSensor(Entity):
    def __init__(self, client, scan_interval):
        _LOGGER.debug("creating modbus meter#1 sensor")
        print("creating modbus meter#1 sensor")

        self._client = client

        self._scan_interval = scan_interval
        self._state = 0
        self._device_state_attributes = {}

    def round(self, floatval):
        return round(floatval, 2)

    @property
    def extra_state_attributes(self):
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
        while True:
            try:
		        
                reading = self._client.read_holding_registers(40188, 107)
                
                if reading:
                    data = BinaryPayloadDecoder.fromRegisters(reading, byteorder=Endian.Big, wordorder=Endian.Big)

                    # Identification
                    # 40188 C_SunSpec_DID (unit16)
                    # 40189 C_SunSpec_Length (unit16)
                    data.skip_bytes(4)

                    # Current
                    # #40190 - #40193
                    m1_ac_current = data.decode_16bit_int()
                    m1_ac_current_phase_a = data.decode_16bit_int()
                    m1_ac_current_phase_b = data.decode_16bit_int()
                    m1_ac_current_phase_c = data.decode_16bit_int()
                    
                    # #40194
                    m1_ac_current_scalefactor = 10**data.decode_16bit_int()

                    meter1_values['ac_current'] = self.round(m1_ac_current * m1_ac_current_scalefactor)
                    meter1_values['ac_current_phase_a'] = self.round(m1_ac_current_phase_a * m1_ac_current_scalefactor)
                    meter1_values['ac_current_phase_b'] = self.round(m1_ac_current_phase_b * m1_ac_current_scalefactor)
                    meter1_values['ac_current_phase_c'] = self.round(m1_ac_current_phase_c * m1_ac_current_scalefactor)

                    ################
                    # Voltage
                    ################

                    #40195-40198, AC Voltage LN, AB, BC and CA
                    m1_ac_voltage_phase_ln = data.decode_16bit_uint()
                    m1_ac_voltage_phase_an = data.decode_16bit_uint()
                    m1_ac_voltage_phase_bn = data.decode_16bit_uint()
                    m1_ac_voltage_phase_cn = data.decode_16bit_uint()

                    #40199-40202, AC Voltage LN, AN, BN and CN
                    m1_ac_voltage_phase_ll = data.decode_16bit_uint()
                    m1_ac_voltage_phase_ab = data.decode_16bit_uint()
                    m1_ac_voltage_phase_bc = data.decode_16bit_uint()
                    m1_ac_voltage_phase_ca = data.decode_16bit_uint()

                    #40203
                    m1_ac_voltage_phase_scalefactor = 10**data.decode_16bit_int()

                    meter1_values['ac_voltage_phase_ll'] = self.round(m1_ac_voltage_phase_ll * m1_ac_voltage_phase_scalefactor)
                    meter1_values['ac_voltage_phase_ab'] = self.round(m1_ac_voltage_phase_ab * m1_ac_voltage_phase_scalefactor)
                    meter1_values['ac_voltage_phase_bc'] = self.round(m1_ac_voltage_phase_bc * m1_ac_voltage_phase_scalefactor)
                    meter1_values['ac_voltage_phase_ca'] = self.round(m1_ac_voltage_phase_ca * m1_ac_voltage_phase_scalefactor)
        
                    meter1_values['ac_voltage_phase_ln'] = self.round(m1_ac_voltage_phase_ln * m1_ac_voltage_phase_scalefactor)
                    meter1_values['ac_voltage_phase_an'] = self.round(m1_ac_voltage_phase_an * m1_ac_voltage_phase_scalefactor)
                    meter1_values['ac_voltage_phase_bn'] = self.round(m1_ac_voltage_phase_bn * m1_ac_voltage_phase_scalefactor)
                    meter1_values['ac_voltage_phase_cn'] = self.round(m1_ac_voltage_phase_cn * m1_ac_voltage_phase_scalefactor)

                    #40204, Frequency
                    m1_ac_frequency = data.decode_16bit_int()

                    ################
                    # Power
                    ################

                    #40205
                    m1_ac_frequency_scalefactor = 10**data.decode_16bit_int()
                    meter1_values['ac_frequency'] = self.round(m1_ac_frequency * m1_ac_frequency_scalefactor)

                    #40206
                    m1_ac_power_output = data.decode_16bit_int()

                    data.skip_bytes(6) # Skip the phases

                    #40210
                    m1_ac_power_scalefactor = 10**data.decode_16bit_int()
                    meter1_values['ac_power_output'] = self.round(m1_ac_power_output * m1_ac_power_scalefactor)

                    #40211 Apparent Power
                    m1_ac_va = data.decode_16bit_uint()

                    data.skip_bytes(6) # Skip the phases

                    m1_ac_va_scalefactor = 10 ** data.decode_16bit_int()
                    meter1_values['ac_va'] = self.round(m1_ac_va * m1_ac_va_scalefactor)

                    #40216 Reactive Power
                    m1_ac_var = data.decode_16bit_uint()

                    data.skip_bytes(6) # Skip the phases

                    m1_ac_var_scalefactor = 10 ** data.decode_16bit_int()
                    meter1_values['ac_var'] = self.round(m1_ac_var * m1_ac_var_scalefactor)

                    #40221 Power Factor
                    m1_ac_pf = data.decode_16bit_uint()

                    data.skip_bytes(6) # Skip the phases

                    m1_ac_pf_scalefactor = 10 ** data.decode_16bit_int()
                    meter1_values['ac_pf'] = self.round(m1_ac_pf * m1_ac_pf_scalefactor)

                    ################
                    # Accumulated Energy
                    ################

                    # Real Energy
                    # ---------------

                    #40226
                    m1_exported = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases
                    
                    #40234
                    m1_imported = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases

                    #40095
                    m1_energy_scalefactor = 10**data.decode_16bit_uint()

                    # Total production entire lifetime
                    meter1_values['exported'] = self.round(m1_exported * m1_energy_scalefactor)
                    meter1_values['imported'] = self.round(m1_imported * m1_energy_scalefactor)

                    # Apparent Energy
                    # ---------------

                    #40243
                    m1_exported_va = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases
                    
                    #40251
                    m1_imported_va = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases

                    #40259
                    m1_energy_va_scalefactor = 10**data.decode_16bit_uint()

                    # Total production entire lifetime
                    meter1_values['exported_va'] = self.round(m1_exported_va * m1_energy_va_scalefactor)
                    meter1_values['imported_va'] = self.round(m1_imported_va * m1_energy_va_scalefactor)

                    # Reactive Energy
                    # ---------------

                    #40260
                    m1_imported_var_q1 = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases
                    
                    #40268
                    m1_imported_var_q2 = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases

                    #40276
                    m1_exported_var_q3 = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases

                    #40284
                    m1_exported_var_q4 = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases

                    #40293
                    m1_energy_var_scalefactor = 10**data.decode_16bit_uint()

                    # Total production entire lifetime
                    meter1_values['imported_var_q1'] = self.round(m1_imported_var_q1 * m1_energy_var_scalefactor)
                    meter1_values['imported_var_q2'] = self.round(m1_imported_var_q2 * m1_energy_var_scalefactor)
                    meter1_values['exported_var_q3'] = self.round(m1_exported_var_q3 * m1_energy_var_scalefactor)
                    meter1_values['exported_var_q4'] = self.round(m1_exported_var_q4 * m1_energy_var_scalefactor)
                    
                    # Events
                    # ---------------

                    #40097 
                    m1_events = data.decode_32bit_uint()
                    meter1_values['events'] = m1_events

                    # M_EVENT_Power_Failure 0x00000004 Loss of power or phase
                    # M_EVENT_Under_Voltage 0x00000008 Voltage below threshold (Phase Loss)
                    # M_EVENT_Low_PF 0x00000010 Power Factor below threshold (can indicate miss-associated voltage and current inputs in three phase systems)
                    # M_EVENT_Over_Current 0x00000020 Current Input over threshold (out of measurement range)
                    # M_EVENT_Over_Voltage 0x00000040 Voltage Input over threshold (out of measurement range)
                    # M_EVENT_Missing_Sensor 0x00000080 Sensor not connected

                    # Skip if incrementing counters have gone to 0, means something isn't right, usually happens on inverter startup
                    validValue = meter1_values['exported'] > 0 and meter1_values['imported'] > 0
                    if validValue:
                        self._state = meter1_values['ac_power_output']
                        self._device_state_attributes = meter1_values

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
        return "SolarEdge Modbus Meter #1"

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
        return "SolarEdge Meter#1"
