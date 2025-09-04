# Homevolt Local Integration for Home Assistant

This is a custom integration for Home Assistant that connects to a Homevolt Energy Management System (EMS) and provides sensor data.

## Features

- Monitors the state of your Homevolt Local
- Displays battery level with dynamic icons
- Shows error information when available
- Configurable through the Home Assistant UI

## Installation

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add the URL of this repository and select "Integration" as the category
3. Click "Install" on the Homevolt Local integration
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/homevolt_local` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Homevolt Local"
4. Follow the configuration steps:
   - Enter the IP address or hostname of your first Homevolt system
   - Enter your username and password
   - Configure optional settings (SSL verification, scan interval, timeout)
   - Add additional IP addresses for linked systems (optional)
   - Select which system should be considered the main system (if you added multiple)
   - Confirm the configuration

### Multiple IP Addresses

If your Homevolt system has multiple IP addresses (for example, if you have multiple controllers that are linked together), you can now add all IP addresses during the initial setup process. This creates a single integration instance that manages all your linked systems.

Benefits of this approach:
- All systems are managed by a single integration instance
- Data from all systems is merged automatically
- Duplicate devices and sensors are automatically detected and prevented
- You can designate one system as the "main system" which will be used as the primary data source

During setup, you'll be guided through:
1. Adding your first system (IP/hostname, credentials, and settings)
2. Adding additional systems one by one (with an option to add more after each)
3. Selecting which system should be considered the main system
4. Confirming the final configuration

The integration uses unique identifiers for each device based on their internal IDs, ensuring that the same physical device is represented only once in Home Assistant, regardless of which IP address it's accessed through.

## Devices and Sensors

This integration detects and creates separate devices for each Energy Management System (EMS) unit and sensor found in your Homevolt Local system. Each device has its own set of sensors, and there are also aggregated sensors that show combined data from all devices.

### Aggregated Sensors

These sensors show combined data from all EMS units:

1. **Homevolt Status**: Shows the current state of the EMS with a dynamic icon that changes based on the battery level
2. **Homevolt Error**: Shows error information when available
3. **Homevolt Total SoC**: Shows the total state of charge as a percentage
4. **Homevolt Power**: Shows the current power in watts
5. **Homevolt Energy Produced**: Shows the energy produced in kilowatt-hours
6. **Homevolt Energy Consumed**: Shows the energy consumed in kilowatt-hours

### EMS Device-Specific Sensors

Each EMS device will have the following sensors:

1. **Homevolt battery SoC**: Shows the state of charge for the battery as a percentage
2. **Status**: Shows the current state of the specific EMS device
3. **Power**: Shows the power of the specific EMS device in watts
4. **Energy Produced**: Shows the energy produced by the specific EMS device in kilowatts
5. **Energy Consumed**: Shows the energy consumed by the specific EMS device in kilowatts
6. **Error**: Shows error information specific to the device when available

### Sensor Devices

The integration also creates separate devices for each sensor in the system:

#### Grid Sensor

The Grid sensor device provides information about the power flow to and from the grid:

1. **Power**: Shows the current power flow in watts (positive for import, negative for export)
2. **Energy Imported**: Shows the total energy imported from the grid in kilowatt-hours
3. **Energy Exported**: Shows the total energy exported to the grid in kilowatt-hours

#### Solar Sensor

The Solar sensor device provides information about your solar production:

1. **Power**: Shows the current solar power production in watts
2. **Energy Imported**: Shows the total energy imported from the solar system in kilowatt-hours
3. **Energy Exported**: Shows the total energy exported to the solar system in kilowatt-hours

#### Load Sensor

The Load sensor device provides information about your household consumption:

1. **Power**: Shows the current power consumption in watts
2. **Energy Imported**: Shows the total energy imported by the loads in kilowatt-hours
3. **Energy Exported**: Shows the total energy exported by the loads in kilowatt-hours

## Example Dashboard

Here is an example dashboard configuration that you can use to display your Homevolt sensors. You can add this to your Home Assistant Dashboards by choosing "Raw configuration editor" and pasting the code below.

**Note:** You will likely need to replace some of the placeholder entity IDs (e.g., `sensor.REPLACE_WITH_YOUR_GRID_POWER_SENSOR`) with the actual entity IDs from your Home Assistant instance. You can find the entity IDs in Home Assistant under **Settings -> Devices & Services -> Entities**.

The aggregated sensors (e.g., `sensor.homevolt_total_soc`) should have stable entity IDs. However, sensors for Grid, Solar, Load, and individual EMS units may have entity IDs that vary depending on your setup (e.g., `sensor.power_2`, `sensor.power_3`). Please verify all entity IDs before using this dashboard.

```yaml
#
# Note: You will need to replace some of the placeholder entity IDs below with the
# actual entity IDs from your Home Assistant instance. You can find the entity IDs
# in Home Assistant under Settings -> Devices & Services -> Entities.
#
# The aggregated sensors (e.g., sensor.homevolt_total_soc) should have stable names.
# However, sensors for Grid, Solar, Load, and individual EMS units may have
# entity IDs that vary (e.g., sensor.power_2, sensor.power_3). Please verify all
# entity IDs before using this dashboard.
#
title: Homevolt Energy Dashboard
views:
  - path: default_view
    title: Home
    icon: mdi:home
    cards:
      - type: markdown
        content: >
          # Homevolt - Overview
      - type: grid
        columns: 2
        square: false
        cards:
          - type: gauge
            entity: sensor.homevolt_total_soc
            name: Total Battery SoC
            min: 0
            max: 100
            segments:
              - from: 0
                color: '#db4437'
              - from: 20
                color: '#ffa600'
              - from: 60
                color: '#43a047'
          - type: entity
            entity: sensor.homevolt_status
            name: System Status
          - type: entity
            entity: sensor.homevolt_power
            name: Battery Power Flow
          - type: entity
            entity: sensor.homevolt_current_schedule
            name: Current Schedule

      - type: markdown
        content: >
          ## Energy Flow (Current Power)
      - type: grid
        columns: 3
        square: false
        cards:
          - type: sensor
            entity: sensor.REPLACE_WITH_YOUR_GRID_POWER_SENSOR
            name: Grid
            graph: line
          - type: sensor
            entity: sensor.REPLACE_WITH_YOUR_SOLAR_POWER_SENSOR
            name: Solar
            graph: line
          - type: sensor
            entity: sensor.REPLACE_WITH_YOUR_LOAD_POWER_SENSOR
            name: House
            graph: line

      - type: markdown
        content: >
          ## Energy Totals (Lifetime)
      - type: entities
        show_header_toggle: false
        entities:
          - entity: sensor.homevolt_energy_produced
            name: Battery - Energy Produced
          - entity: sensor.homevolt_energy_consumed
            name: Battery - Energy Consumed
          - entity: sensor.REPLACE_WITH_YOUR_GRID_ENERGY_IMPORTED_SENSOR
            name: Grid - Energy Imported
          - entity: sensor.REPLACE_WITH_YOUR_GRID_ENERGY_EXPORTED_SENSOR
            name: Grid - Energy Exported
          - entity: sensor.REPLACE_WITH_YOUR_SOLAR_ENERGY_EXPORTED_SENSOR
            name: Solar - Energy Produced
          - entity: sensor.REPLACE_WITH_YOUR_LOAD_ENERGY_IMPORTED_SENSOR
            name: House - Energy Consumed

      - type: markdown
        content: >
          ## EMS Devices

          *Note: If you have multiple EMS devices, you can duplicate the card below for each one.*
      - type: entities
        title: "EMS Device 1"
        show_header_toggle: false
        entities:
          - entity: sensor.REPLACE_WITH_YOUR_EMS_1_STATUS_SENSOR
            name: Status
          - entity: sensor.REPLACE_WITH_YOUR_EMS_1_BATTERY_SOC_SENSOR
            name: Battery SoC
          - entity: sensor.REPLACE_WITH_YOUR_EMS_1_POWER_SENSOR
            name: Power
          - entity: sensor.REPLACE_WITH_YOUR_EMS_1_ENERGY_PRODUCED_SENSOR
            name: Energy Produced
          - entity: sensor.REPLACE_WITH_YOUR_EMS_1_ENERGY_CONSUMED_SENSOR
            name: Energy Consumed
          - entity: sensor.REPLACE_WITH_YOUR_EMS_1_ERROR_SENSOR
            name: Error
```

## Troubleshooting

- If you encounter connection issues, check your API URL and credentials
- Verify that your Homevolt Local is online and accessible from your Home Assistant instance
- Check the Home Assistant logs for detailed error messages

## Development

### Development Container

This project includes a development container configuration that provides a consistent development environment with all the necessary tools and dependencies pre-installed. The development container supports both VS Code and PyCharm.

For more information on how to use the development container, see the [.devcontainer/README.md](.devcontainer/README.md) file.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
