# solaredge-modbus-hass
A custom platform component/sensor for reading SolarEdge Modbus TCP into Home Assistant https://home-assistant.io/

# Benefits compared to Home Assistant built in Modbus component

When reading multiple registers with HA default Modbus, it will do one reading per register.

SolarEdge that use a sunspec implementation (https://www.solaredge.com/sites/default/files/sunspec-implementation-technical-note.pdf) send values in one register and the scale factor in another.

This means that for example 20 watts can be represented using a value of 20000 and a scale factor or -3 so that 20000 * 10^-3 = 20

The problem that occur if reading lots of registers with one reading each, is that the SolarEdge inverter can actually change the scale factor between two of the readings done by Home Assistant, such as you first get 20000 in the value, then before the next reading is complete the sun can quickly make your inverter produce more energy changing both value and the scale factor so when HA read the scale factor it could become -2 instead, then when calculating the final result you'll end up with a factor 10 or more incorrect value.

This component reads all registers every reading to make sure it can't get out of sync!

# How to install

Though HACS:
Add custom repository: https://github.com/erikarenhill/solaredge-modbus-hass/

Or manual install:
Copy custom_components/solaredge_modbus to your hass data directory (where your configuration.yaml lives). It should go into the same directory structure (YOUR_CONFIG_DIRECTORY/custom_components/solaredge_modbus)

See [sample-configuration.yaml](sample-configuration.yaml) for information how to configure, and how to extract attributes into custom template sensors.

# Upgrading from the old `platform: template` format

Home Assistant no longer supports template sensors defined under `sensor:` with `platform: template`, the format earlier versions of `sample-configuration.yaml` used. After upgrading Home Assistant, every sensor defined that way disappears, and any utility meter built on them (such as `solar_production_daily`) stops counting. Home Assistant shows a Repairs issue for `platform: template` and logs:

```
Configuring the template integration under the sensor platform key is not supported, it must be configured under its own template key instead
```

The integration itself keeps working: `sensor.solaredge_modbus` and its attributes are still updated. Only the template sensors are gone.

To fix it, move the template sensors to the top-level `template:` key, as in the current [sample-configuration.yaml](sample-configuration.yaml). Set `default_entity_id` to the old entity ID so utility meters, automations, dashboards and history keep working:

Old format:

```yaml
sensor:
  - platform: template
    sensors:
      solaredge_lifetime_production:
        friendly_name: "Lifetime production"
        value_template: "{{ (state_attr('sensor.solaredge_modbus', 'ac_lifetimeproduction') / 1000.0) | round(2) }}"
        unit_of_measurement: 'kWh'
```

New format:

```yaml
template:
  - sensor:
      - default_entity_id: sensor.solaredge_lifetime_production
        name: "Lifetime production"
        unit_of_measurement: "kWh"
        device_class: energy
        state_class: total_increasing
        availability: "{{ state_attr('sensor.solaredge_modbus', 'ac_lifetimeproduction') | float(0) > 0 }}"
        state: "{{ (state_attr('sensor.solaredge_modbus', 'ac_lifetimeproduction') / 1000.0) | round(2) }}"
```

The key renames are `friendly_name` → `name`, `value_template` → `state`, and the object key → `default_entity_id`. Check the configuration and restart Home Assistant afterwards.

Utility meters built on these sensors start counting again from the current reading. The energy produced while the sensor was missing is not added to the meters.

# Energy dashboard

To use solar production in the Energy dashboard, select `sensor.solaredge_lifetime_production` (or a utility meter built on it) as the solar production source. It needs `device_class: energy` and `state_class: total_increasing`, as in the sample configuration.

# Enable readings from external RS485 meter

Just add "read_meter1: true" to the configuration block. For now it only supports one external meter for getting values such as current (own) power consumption, grid power, etc.... so you can calculate your own consumption from the solar panels and import/export for example. Thanks to [awulf](https://github.com/awulf) for contributing with code and testing for this feature.




---


If you like this component, you can always buy me a coffee

<a href="https://www.buymeacoffee.com/gax2VUf" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-yellow.png" alt="Buy Me A Coffee" style="height: 20px !important;width: 100px !important;" ></a>
