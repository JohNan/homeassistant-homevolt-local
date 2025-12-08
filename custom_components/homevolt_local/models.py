"""Data models for the Homevolt Local integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from custom_components.homevolt_local import ATTR_EUID
from custom_components.homevolt_local.const import (
    ATTR_AGGREGATED,
    ATTR_AVAILABLE,
    ATTR_BMS_INFO,
    ATTR_ECU_ID,
    ATTR_EMS,
    ATTR_EMS_INFO,
    ATTR_ENERGY_EXPORTED,
    ATTR_ENERGY_IMPORTED,
    ATTR_INV_INFO,
    ATTR_NODE_ID,
    ATTR_PHASE,
    ATTR_SENSORS,
    ATTR_TIMESTAMP,
    ATTR_TOTAL_POWER,
    ATTR_TYPE,
)


@dataclass
class ScheduleEntry:
    """Model for a single schedule entry."""

    id: int
    type: str
    from_time: str
    to_time: str
    setpoint: int | None = None
    offline: bool | None = None
    max_discharge: str | None = None
    max_charge: str | None = None


@dataclass
class EmsInfo:
    """Model for EMS information."""

    protocol_version: int
    fw_version: str
    rated_capacity: int
    rated_power: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmsInfo:
        """Create an EmsInfo object from a dictionary."""
        return cls(
            protocol_version=data.get("protocol_version", 0),
            fw_version=data.get("fw_version", ""),
            rated_capacity=data.get("rated_capacity", 0),
            rated_power=data.get("rated_power", 0),
        )


@dataclass
class BmsInfo:
    """Model for BMS information."""

    fw_version: str
    serial_number: str
    rated_cap: int
    id: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BmsInfo:
        """Create a BmsInfo object from a dictionary."""
        return cls(
            fw_version=data.get("fw_version", ""),
            serial_number=data.get("serial_number", ""),
            rated_cap=data.get("rated_cap", 0),
            id=data.get("id", 0),
        )


@dataclass
class InvInfo:
    """Model for inverter information."""

    fw_version: str
    serial_number: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InvInfo:
        """Create an InvInfo object from a dictionary."""
        return cls(
            fw_version=data.get("fw_version", ""),
            serial_number=data.get("serial_number", ""),
        )


@dataclass
class EmsConfig:
    """Model for EMS configuration."""

    grid_code_preset: int
    grid_code_preset_str: str
    control_timeout: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmsConfig:
        """Create an EmsConfig object from a dictionary."""
        return cls(
            grid_code_preset=data.get("grid_code_preset", 0),
            grid_code_preset_str=data.get("grid_code_preset_str", ""),
            control_timeout=data.get("control_timeout", False),
        )


@dataclass
class InvConfig:
    """Model for inverter configuration."""

    ffr_fstart_freq: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InvConfig:
        """Create an InvConfig object from a dictionary."""
        return cls(
            ffr_fstart_freq=data.get("ffr_fstart_freq", 0),
        )


@dataclass
class EmsControl:
    """Model for EMS control."""

    mode_sel: int
    pwr_ref: int
    freq_res_mode: int
    freq_res_pwr_fcr_n: int
    freq_res_pwr_fcr_d_up: int
    freq_res_pwr_fcr_d_down: int
    freq_res_pwr_ref_ffr: int
    act_pwr_ch_lim: int
    act_pwr_di_lim: int
    react_pwr_pos_limit: int
    react_pwr_neg_limit: int
    freq_test_seq: int
    data_usage: int
    allow_dfu: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmsControl:
        """Create an EmsControl object from a dictionary."""
        return cls(
            mode_sel=data.get("mode_sel", 0),
            pwr_ref=data.get("pwr_ref", 0),
            freq_res_mode=data.get("freq_res_mode", 0),
            freq_res_pwr_fcr_n=data.get("freq_res_pwr_fcr_n", 0),
            freq_res_pwr_fcr_d_up=data.get("freq_res_pwr_fcr_d_up", 0),
            freq_res_pwr_fcr_d_down=data.get("freq_res_pwr_fcr_d_down", 0),
            freq_res_pwr_ref_ffr=data.get("freq_res_pwr_ref_ffr", 0),
            act_pwr_ch_lim=data.get("act_pwr_ch_lim", 0),
            act_pwr_di_lim=data.get("act_pwr_di_lim", 0),
            react_pwr_pos_limit=data.get("react_pwr_pos_limit", 0),
            react_pwr_neg_limit=data.get("react_pwr_neg_limit", 0),
            freq_test_seq=data.get("freq_test_seq", 0),
            data_usage=data.get("data_usage", 0),
            allow_dfu=data.get("allow_dfu", False),
        )


@dataclass
class EmsData:
    """Model for EMS data."""

    timestamp_ms: int
    state: int
    state_str: str
    info: int
    info_str: list[str]
    warning: int
    warning_str: list[str]
    alarm: int
    alarm_str: list[str]
    phase_angle: int
    frequency: int
    phase_seq: int
    power: int
    apparent_power: int
    reactive_power: int
    energy_produced: int
    energy_consumed: int
    sys_temp: int
    avail_cap: int
    freq_res_state: int
    soc_avg: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmsData:
        """Create an EmsData object from a dictionary."""
        return cls(
            timestamp_ms=data.get("timestamp_ms", 0),
            state=data.get("state", 0),
            state_str=data.get("state_str", ""),
            info=data.get("info", 0),
            info_str=data.get("info_str", []),
            warning=data.get("warning", 0),
            warning_str=data.get("warning_str", []),
            alarm=data.get("alarm", 0),
            alarm_str=data.get("alarm_str", []),
            phase_angle=data.get("phase_angle", 0),
            frequency=data.get("frequency", 0),
            phase_seq=data.get("phase_seq", 0),
            power=data.get("power", 0),
            apparent_power=data.get("apparent_power", 0),
            reactive_power=data.get("reactive_power", 0),
            energy_produced=data.get("energy_produced", 0),
            energy_consumed=data.get("energy_consumed", 0),
            sys_temp=data.get("sys_temp", 0),
            avail_cap=data.get("avail_cap", 0),
            freq_res_state=data.get("freq_res_state", 0),
            soc_avg=data.get("soc_avg", 0),
        )


@dataclass
class BmsData:
    """Model for BMS data."""

    energy_avail: int
    cycle_count: int
    soc: int
    state: int
    state_str: str
    alarm: int
    alarm_str: list[str]
    tmin: int
    tmax: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BmsData:
        """Create a BmsData object from a dictionary."""
        return cls(
            energy_avail=data.get("energy_avail", 0),
            cycle_count=data.get("cycle_count", 0),
            soc=data.get("soc", 0),
            state=data.get("state", 0),
            state_str=data.get("state_str", ""),
            alarm=data.get("alarm", 0),
            alarm_str=data.get("alarm_str", []),
            tmin=data.get("tmin", 0),
            tmax=data.get("tmax", 0),
        )


@dataclass
class EmsPrediction:
    """Model for EMS prediction."""

    avail_ch_pwr: int
    avail_di_pwr: int
    avail_ch_energy: int
    avail_di_energy: int
    avail_inv_ch_pwr: int
    avail_inv_di_pwr: int
    avail_group_fuse_ch_pwr: int
    avail_group_fuse_di_pwr: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmsPrediction:
        """Create an EmsPrediction object from a dictionary."""
        return cls(
            avail_ch_pwr=data.get("avail_ch_pwr", 0),
            avail_di_pwr=data.get("avail_di_pwr", 0),
            avail_ch_energy=data.get("avail_ch_energy", 0),
            avail_di_energy=data.get("avail_di_energy", 0),
            avail_inv_ch_pwr=data.get("avail_inv_ch_pwr", 0),
            avail_inv_di_pwr=data.get("avail_inv_di_pwr", 0),
            avail_group_fuse_ch_pwr=data.get("avail_group_fuse_ch_pwr", 0),
            avail_group_fuse_di_pwr=data.get("avail_group_fuse_di_pwr", 0),
        )


@dataclass
class EmsVoltage:
    """Model for EMS voltage."""

    l1: int
    l2: int
    l3: int
    l1_l2: int
    l2_l3: int
    l3_l1: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmsVoltage:
        """Create an EmsVoltage object from a dictionary."""
        return cls(
            l1=data.get("l1", 0),
            l2=data.get("l2", 0),
            l3=data.get("l3", 0),
            l1_l2=data.get("l1_l2", 0),
            l2_l3=data.get("l2_l3", 0),
            l3_l1=data.get("l3_l1", 0),
        )


@dataclass
class EmsCurrent:
    """Model for EMS current."""

    l1: int
    l2: int
    l3: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmsCurrent:
        """Create an EmsCurrent object from a dictionary."""
        return cls(
            l1=data.get("l1", 0),
            l2=data.get("l2", 0),
            l3=data.get("l3", 0),
        )


@dataclass
class EmsAggregate:
    """Model for EMS aggregate."""

    imported_kwh: float
    exported_kwh: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmsAggregate:
        """Create an EmsAggregate object from a dictionary."""
        return cls(
            imported_kwh=data.get("imported_kwh", 0.0),
            exported_kwh=data.get("exported_kwh", 0.0),
        )


@dataclass
class PhaseData:
    """Model for phase data."""

    voltage: float
    amp: float
    power: float
    pf: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PhaseData:
        """Create a PhaseData object from a dictionary."""
        return cls(
            voltage=data.get("voltage", 0.0),
            amp=data.get("amp", 0.0),
            power=data.get("power", 0.0),
            pf=data.get("pf", 0.0),
        )


@dataclass
class SensorData:
    """Model for sensor data."""

    type: str
    node_id: int
    euid: str
    interface: int
    available: bool
    rssi: int
    average_rssi: float
    pdr: float
    phase: list[PhaseData]
    frequency: int
    total_power: int
    energy_imported: float
    energy_exported: float
    timestamp: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SensorData:
        """Create a SensorData object from a dictionary."""
        return cls(
            type=data.get(ATTR_TYPE, ""),
            node_id=data.get(ATTR_NODE_ID, 0),
            euid=data.get(ATTR_EUID, ""),
            interface=data.get("interface", 0),
            available=data.get(ATTR_AVAILABLE, False),
            rssi=data.get("rssi", 0),
            average_rssi=data.get("average_rssi", 0.0),
            pdr=data.get("pdr", 0.0),
            phase=[PhaseData.from_dict(phase) for phase in data.get(ATTR_PHASE, [])],
            frequency=data.get("frequency", 0),
            total_power=data.get(ATTR_TOTAL_POWER, 0),
            energy_imported=data.get(ATTR_ENERGY_IMPORTED, 0.0),
            energy_exported=data.get(ATTR_ENERGY_EXPORTED, 0.0),
            timestamp=data.get(ATTR_TIMESTAMP, 0),
        )


@dataclass
class EmsDevice:
    """Model for an EMS device."""

    ecu_id: int
    ecu_host: str
    ecu_version: str
    error: int
    error_str: str
    op_state: int
    op_state_str: str
    ems_info: EmsInfo
    bms_info: list[BmsInfo]
    inv_info: InvInfo
    ems_config: EmsConfig
    inv_config: InvConfig
    ems_control: EmsControl
    ems_data: EmsData
    bms_data: list[BmsData]
    ems_prediction: EmsPrediction
    ems_voltage: EmsVoltage
    ems_current: EmsCurrent
    ems_aggregate: EmsAggregate
    error_cnt: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmsDevice:
        """Create an EmsDevice object from a dictionary."""
        if not data:
            # Return a default EmsDevice with empty values
            return cls(
                ecu_id=0,
                ecu_host="",
                ecu_version="",
                error=0,
                error_str="",
                op_state=0,
                op_state_str="",
                ems_info=EmsInfo(
                    protocol_version=0, fw_version="", rated_capacity=0, rated_power=0
                ),
                bms_info=[],
                inv_info=InvInfo(fw_version="", serial_number=""),
                ems_config=EmsConfig(
                    grid_code_preset=0, grid_code_preset_str="", control_timeout=False
                ),
                inv_config=InvConfig(ffr_fstart_freq=0),
                ems_control=EmsControl(
                    mode_sel=0,
                    pwr_ref=0,
                    freq_res_mode=0,
                    freq_res_pwr_fcr_n=0,
                    freq_res_pwr_fcr_d_up=0,
                    freq_res_pwr_fcr_d_down=0,
                    freq_res_pwr_ref_ffr=0,
                    act_pwr_ch_lim=0,
                    act_pwr_di_lim=0,
                    react_pwr_pos_limit=0,
                    react_pwr_neg_limit=0,
                    freq_test_seq=0,
                    data_usage=0,
                    allow_dfu=False,
                ),
                ems_data=EmsData(
                    timestamp_ms=0,
                    state=0,
                    state_str="",
                    info=0,
                    info_str=[],
                    warning=0,
                    warning_str=[],
                    alarm=0,
                    alarm_str=[],
                    phase_angle=0,
                    frequency=0,
                    phase_seq=0,
                    power=0,
                    apparent_power=0,
                    reactive_power=0,
                    energy_produced=0,
                    energy_consumed=0,
                    sys_temp=0,
                    avail_cap=0,
                    freq_res_state=0,
                    soc_avg=0,
                ),
                bms_data=[],
                ems_prediction=EmsPrediction(
                    avail_ch_pwr=0,
                    avail_di_pwr=0,
                    avail_ch_energy=0,
                    avail_di_energy=0,
                    avail_inv_ch_pwr=0,
                    avail_inv_di_pwr=0,
                    avail_group_fuse_ch_pwr=0,
                    avail_group_fuse_di_pwr=0,
                ),
                ems_voltage=EmsVoltage(l1=0, l2=0, l3=0, l1_l2=0, l2_l3=0, l3_l1=0),
                ems_current=EmsCurrent(l1=0, l2=0, l3=0),
                ems_aggregate=EmsAggregate(imported_kwh=0.0, exported_kwh=0.0),
                error_cnt=0,
            )

        return cls(
            ecu_id=data.get(ATTR_ECU_ID, 0),
            ecu_host=data.get("ecu_host", ""),
            ecu_version=data.get("ecu_version", ""),
            error=data.get("error", 0),
            error_str=data.get("error_str", ""),
            op_state=data.get("op_state", 0),
            op_state_str=data.get("op_state_str", ""),
            ems_info=EmsInfo.from_dict(data.get(ATTR_EMS_INFO, {}))
            if ATTR_EMS_INFO in data
            else EmsInfo(
                protocol_version=0, fw_version="", rated_capacity=0, rated_power=0
            ),
            bms_info=[BmsInfo.from_dict(bms) for bms in data.get(ATTR_BMS_INFO, [])],
            inv_info=InvInfo.from_dict(data.get(ATTR_INV_INFO, {}))
            if ATTR_INV_INFO in data
            else InvInfo(fw_version="", serial_number=""),
            ems_config=EmsConfig.from_dict(data.get("ems_config", {}))
            if "ems_config" in data
            else EmsConfig(
                grid_code_preset=0, grid_code_preset_str="", control_timeout=False
            ),
            inv_config=InvConfig.from_dict(data.get("inv_config", {}))
            if "inv_config" in data
            else InvConfig(ffr_fstart_freq=0),
            ems_control=EmsControl.from_dict(data.get("ems_control", {}))
            if "ems_control" in data
            else EmsControl(
                mode_sel=0,
                pwr_ref=0,
                freq_res_mode=0,
                freq_res_pwr_fcr_n=0,
                freq_res_pwr_fcr_d_up=0,
                freq_res_pwr_fcr_d_down=0,
                freq_res_pwr_ref_ffr=0,
                act_pwr_ch_lim=0,
                act_pwr_di_lim=0,
                react_pwr_pos_limit=0,
                react_pwr_neg_limit=0,
                freq_test_seq=0,
                data_usage=0,
                allow_dfu=False,
            ),
            ems_data=EmsData.from_dict(data.get("ems_data", {}))
            if "ems_data" in data
            else EmsData(
                timestamp_ms=0,
                state=0,
                state_str="",
                info=0,
                info_str=[],
                warning=0,
                warning_str=[],
                alarm=0,
                alarm_str=[],
                phase_angle=0,
                frequency=0,
                phase_seq=0,
                power=0,
                apparent_power=0,
                reactive_power=0,
                energy_produced=0,
                energy_consumed=0,
                sys_temp=0,
                avail_cap=0,
                freq_res_state=0,
                soc_avg=0,
            ),
            bms_data=[BmsData.from_dict(bms) for bms in data.get("bms_data", [])],
            ems_prediction=EmsPrediction.from_dict(data.get("ems_prediction", {}))
            if "ems_prediction" in data
            else EmsPrediction(
                avail_ch_pwr=0,
                avail_di_pwr=0,
                avail_ch_energy=0,
                avail_di_energy=0,
                avail_inv_ch_pwr=0,
                avail_inv_di_pwr=0,
                avail_group_fuse_ch_pwr=0,
                avail_group_fuse_di_pwr=0,
            ),
            ems_voltage=EmsVoltage.from_dict(data.get("ems_voltage", {}))
            if "ems_voltage" in data
            else EmsVoltage(l1=0, l2=0, l3=0, l1_l2=0, l2_l3=0, l3_l1=0),
            ems_current=EmsCurrent.from_dict(data.get("ems_current", {}))
            if "ems_current" in data
            else EmsCurrent(l1=0, l2=0, l3=0),
            ems_aggregate=EmsAggregate.from_dict(data.get("ems_aggregate", {}))
            if "ems_aggregate" in data
            else EmsAggregate(imported_kwh=0.0, exported_kwh=0.0),
            error_cnt=data.get("error_cnt", 0),
        )


@dataclass
class HomevoltData:
    """Model for Homevolt data."""

    type: str = field(metadata={"json_field_name": "$type"})
    ts: int
    ems: list[EmsDevice]
    aggregated: EmsDevice
    sensors: list[SensorData]
    schedules: list[ScheduleEntry] = field(default_factory=list)
    schedule_count: int | None = None
    schedule_current_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HomevoltData:
        """Create a HomevoltData object from a dictionary."""
        return cls(
            type=data.get("$type", ""),
            ts=data.get("ts", 0),
            ems=[EmsDevice.from_dict(ems) for ems in data.get(ATTR_EMS, [])],
            aggregated=EmsDevice.from_dict(data.get(ATTR_AGGREGATED, {})),
            sensors=[
                SensorData.from_dict(sensor) for sensor in data.get(ATTR_SENSORS, [])
            ],
            schedules=data.get("schedules", []),  # Will be populated by the coordinator
            schedule_count=data.get("schedule_count"),
            schedule_current_id=data.get("schedule_current_id"),
        )
