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

meter_values = {}

class SolarEdgeMeterSensor(Entity):
    def __init__(self, client, unit_id, scan_interval):
        _LOGGER.debug("creating modbus meter sensor #" + unit_id)
        print("creating modbus meter sensor #" + unit_id)

        self._client = client

        self._scan_interval = scan_interval
        self._state = 0
        self._device_state_attributes = {}
        self._unit_id = unit_id
        self._register_start = 40188

        if unit_id == 2:
            self._register_start = 40632
        elif unit_id == 3:
            self._register_start = 40537

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
        while True:
            sleep(0.005)
            try:
		        
                reading = self._client.read_holding_registers(self._register_start, 107)
                
                if reading:
                    data = BinaryPayloadDecoder.fromRegisters(reading, byteorder=Endian.Big, wordorder=Endian.Big)

                    # Identification
                    # 40188 C_SunSpec_DID (unit16)
                    # 40189 C_SunSpec_Length (unit16)
                    data.skip_bytes(4)

                    # Current
                    # #40190 - #40193
                    m_ac_current = data.decode_16bit_int()
                    m_ac_current_phase_a = data.decode_16bit_int()
                    m_ac_current_phase_b = data.decode_16bit_int()
                    m_ac_current_phase_c = data.decode_16bit_int()
                    
                    # #40194
                    m_ac_current_scalefactor = 10**data.decode_16bit_int()

                    meter_values['ac_current'] = self.round(m_ac_current * m_ac_current_scalefactor)
                    meter_values['ac_current_phase_a'] = self.round(m_ac_current_phase_a * m_ac_current_scalefactor)
                    meter_values['ac_current_phase_b'] = self.round(m_ac_current_phase_b * m_ac_current_scalefactor)
                    meter_values['ac_current_phase_c'] = self.round(m_ac_current_phase_c * m_ac_current_scalefactor)

                    ################
                    # Voltage
                    ################

                    #40195-40198, AC Voltage LN, AB, BC and CA
                    m_ac_voltage_phase_ln = data.decode_16bit_uint()
                    m_ac_voltage_phase_an = data.decode_16bit_uint()
                    m_ac_voltage_phase_bn = data.decode_16bit_uint()
                    m_ac_voltage_phase_cn = data.decode_16bit_uint()

                    #40199-40202, AC Voltage LN, AN, BN and CN
                    m_ac_voltage_phase_ll = data.decode_16bit_uint()
                    m_ac_voltage_phase_ab = data.decode_16bit_uint()
                    m_ac_voltage_phase_bc = data.decode_16bit_uint()
                    m_ac_voltage_phase_ca = data.decode_16bit_uint()

                    #40203
                    m_ac_voltage_phase_scalefactor = 10**data.decode_16bit_int()

                    meter_values['ac_voltage_phase_ll'] = self.round(m_ac_voltage_phase_ll * m_ac_voltage_phase_scalefactor)
                    meter_values['ac_voltage_phase_ab'] = self.round(m_ac_voltage_phase_ab * m_ac_voltage_phase_scalefactor)
                    meter_values['ac_voltage_phase_bc'] = self.round(m_ac_voltage_phase_bc * m_ac_voltage_phase_scalefactor)
                    meter_values['ac_voltage_phase_ca'] = self.round(m_ac_voltage_phase_ca * m_ac_voltage_phase_scalefactor)
        
                    meter_values['ac_voltage_phase_ln'] = self.round(m_ac_voltage_phase_ln * m_ac_voltage_phase_scalefactor)
                    meter_values['ac_voltage_phase_an'] = self.round(m_ac_voltage_phase_an * m_ac_voltage_phase_scalefactor)
                    meter_values['ac_voltage_phase_bn'] = self.round(m_ac_voltage_phase_bn * m_ac_voltage_phase_scalefactor)
                    meter_values['ac_voltage_phase_cn'] = self.round(m_ac_voltage_phase_cn * m_ac_voltage_phase_scalefactor)

                    #40204, Frequency
                    m_ac_frequency = data.decode_16bit_int()

                    ################
                    # Power
                    ################

                    #40205
                    m_ac_frequency_scalefactor = 10**data.decode_16bit_int()
                    meter_values['ac_frequency'] = self.round(m_ac_frequency * m_ac_frequency_scalefactor)

                    #40206
                    m_ac_power_output = data.decode_16bit_int()

                    data.skip_bytes(6) # Skip the phases

                    #40210
                    m_ac_power_scalefactor = 10**data.decode_16bit_int()
                    meter_values['ac_power_output'] = self.round(m_ac_power_output * m_ac_power_scalefactor)

                    #40211 Apparent Power
                    m_ac_va = data.decode_16bit_uint()

                    data.skip_bytes(6) # Skip the phases

                    m_ac_va_scalefactor = 10 ** data.decode_16bit_int()
                    meter_values['ac_va'] = self.round(m_ac_va * m_ac_va_scalefactor)

                    #40216 Reactive Power
                    m_ac_var = data.decode_16bit_uint()

                    data.skip_bytes(6) # Skip the phases

                    m_ac_var_scalefactor = 10 ** data.decode_16bit_int()
                    meter_values['ac_var'] = self.round(m_ac_var * m_ac_var_scalefactor)

                    #40221 Power Factor
                    m_ac_pf = data.decode_16bit_uint()

                    data.skip_bytes(6) # Skip the phases

                    m_ac_pf_scalefactor = 10 ** data.decode_16bit_int()
                    meter_values['ac_pf'] = self.round(m_ac_pf * m_ac_pf_scalefactor)

                    ################
                    # Accumulated Energy
                    ################

                    # Real Energy
                    # ---------------

                    #40226
                    m_exported = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases
                    
                    #40234
                    m_imported = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases

                    #40095
                    m_energy_scalefactor = 10**data.decode_16bit_uint()

                    # Total production entire lifetime
                    meter_values['exported'] = self.round(m_exported * m_energy_scalefactor)
                    meter_values['imported'] = self.round(m_imported * m_energy_scalefactor)

                    # Apparent Energy
                    # ---------------

                    #40243
                    m_exported_va = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases
                    
                    #40251
                    m_imported_va = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases

                    #40259
                    m_energy_va_scalefactor = 10**data.decode_16bit_uint()

                    # Total production entire lifetime
                    meter_values['exported_va'] = self.round(m_exported_va * m_energy_va_scalefactor)
                    meter_values['imported_va'] = self.round(m_imported_va * m_energy_va_scalefactor)

                    # Reactive Energy
                    # ---------------

                    #40260
                    m_imported_var_q1 = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases
                    
                    #40268
                    m_imported_var_q2 = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases

                    #40276
                    m_exported_var_q3 = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases

                    #40284
                    m_exported_var_q4 = data.decode_32bit_uint()
                    data.skip_bytes(12) # Skip phases

                    #40293
                    m_energy_var_scalefactor = 10**data.decode_16bit_uint()

                    # Total production entire lifetime
                    meter_values['imported_var_q1'] = self.round(m_imported_var_q1 * m_energy_var_scalefactor)
                    meter_values['imported_var_q2'] = self.round(m_imported_var_q2 * m_energy_var_scalefactor)
                    meter_values['exported_var_q3'] = self.round(m_exported_var_q3 * m_energy_var_scalefactor)
                    meter_values['exported_var_q4'] = self.round(m_exported_var_q4 * m_energy_var_scalefactor)
                    
                    # Events
                    # ---------------

                    #40097 
                    m_events = data.decode_32bit_uint()
                    meter_values['events'] = m_events

                    # M_EVENT_Power_Failure 0x00000004 Loss of power or phase
                    # M_EVENT_Under_Voltage 0x00000008 Voltage below threshold (Phase Loss)
                    # M_EVENT_Low_PF 0x00000010 Power Factor below threshold (can indicate miss-associated voltage and current inputs in three phase systems)
                    # M_EVENT_Over_Current 0x00000020 Current Input over threshold (out of measurement range)
                    # M_EVENT_Over_Voltage 0x00000040 Voltage Input over threshold (out of measurement range)
                    # M_EVENT_Missing_Sensor 0x00000080 Sensor not connected

                    
                    self._state = meter_values['ac_power_output']
                    self._device_state_attributes = meter_values

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
        return "SolarEdge Modbus Meter #" + self._unit_id

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
        return "SolarEdge Meter#" + self._unit_id
