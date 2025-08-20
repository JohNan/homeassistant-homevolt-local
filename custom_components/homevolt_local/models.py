"""Data models for the Homevolt Local integration."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Callable, Dict, List, Type, TypeVar

T = TypeVar("T")


def _create_from_dict(cls: Type[T]) -> Callable[[Dict[str, Any]], T]:
    """Create a from_dict method for a dataclass."""

    def from_dict(data: Dict[str, Any]) -> T:
        """Create a dataclass instance from a dictionary."""
        kwargs = {}
        for f in fields(cls):
            if f.name in data:
                kwargs[f.name] = data[f.name]
        return cls(**kwargs)

    return from_dict


@dataclass
class EmsInfo:
    """Model for EMS information."""

    protocol_version: int = 0
    fw_version: str = ""
    rated_capacity: int = 0
    rated_power: int = 0


@dataclass
class BmsInfo:
    """Model for BMS information."""

    fw_version: str = ""
    serial_number: str = ""
    rated_cap: int = 0
    id: int = 0


@dataclass
class InvInfo:
    """Model for inverter information."""

    fw_version: str = ""
    serial_number: str = ""


@dataclass
class EmsConfig:
    """Model for EMS configuration."""

    grid_code_preset: int = 0
    grid_code_preset_str: str = ""
    control_timeout: bool = False


@dataclass
class InvConfig:
    """Model for inverter configuration."""

    ffr_fstart_freq: int = 0


@dataclass
class EmsControl:
    """Model for EMS control."""

    mode_sel: int = 0
    pwr_ref: int = 0
    freq_res_mode: int = 0
    freq_res_pwr_fcr_n: int = 0
    freq_res_pwr_fcr_d_up: int = 0
    freq_res_pwr_fcr_d_down: int = 0
    freq_res_pwr_ref_ffr: int = 0
    act_pwr_ch_lim: int = 0
    act_pwr_di_lim: int = 0
    react_pwr_pos_limit: int = 0
    react_pwr_neg_limit: int = 0
    freq_test_seq: int = 0
    data_usage: int = 0
    allow_dfu: bool = False


@dataclass
class EmsData:
    """Model for EMS data."""

    timestamp_ms: int = 0
    state: int = 0
    state_str: str = ""
    info: int = 0
    info_str: List[str] = field(default_factory=list)
    warning: int = 0
    warning_str: List[str] = field(default_factory=list)
    alarm: int = 0
    alarm_str: List[str] = field(default_factory=list)
    phase_angle: int = 0
    frequency: int = 0
    phase_seq: int = 0
    power: int = 0
    apparent_power: int = 0
    reactive_power: int = 0
    energy_produced: int = 0
    energy_consumed: int = 0
    sys_temp: int = 0
    avail_cap: int = 0
    freq_res_state: int = 0
    soc_avg: int = 0


@dataclass
class BmsData:
    """Model for BMS data."""

    energy_avail: int = 0
    cycle_count: int = 0
    soc: int = 0
    state: int = 0
    state_str: str = ""
    alarm: int = 0
    alarm_str: List[str] = field(default_factory=list)
    tmin: int = 0
    tmax: int = 0


@dataclass
class EmsPrediction:
    """Model for EMS prediction."""

    avail_ch_pwr: int = 0
    avail_di_pwr: int = 0
    avail_ch_energy: int = 0
    avail_di_energy: int = 0
    avail_inv_ch_pwr: int = 0
    avail_inv_di_pwr: int = 0
    avail_group_fuse_ch_pwr: int = 0
    avail_group_fuse_di_pwr: int = 0


@dataclass
class EmsVoltage:
    """Model for EMS voltage."""

    l1: int = 0
    l2: int = 0
    l3: int = 0
    l1_l2: int = 0
    l2_l3: int = 0
    l3_l1: int = 0


@dataclass
class EmsCurrent:
    """Model for EMS current."""

    l1: int = 0
    l2: int = 0
    l3: int = 0


@dataclass
class EmsAggregate:
    """Model for EMS aggregate."""

    imported_kwh: float = 0.0
    exported_kwh: float = 0.0


@dataclass
class PhaseData:
    """Model for phase data."""

    voltage: float = 0.0
    amp: float = 0.0
    power: float = 0.0
    pf: float = 0.0


@dataclass
class SensorData:
    """Model for sensor data."""

    type: str = ""
    node_id: int = 0
    euid: str = ""
    interface: int = 0
    available: bool = True
    rssi: int = 0
    average_rssi: float = 0.0
    pdr: float = 0.0
    phase: List[PhaseData] = field(default_factory=list)
    frequency: int = 0
    total_power: int = 0
    energy_imported: float = 0.0
    energy_exported: float = 0.0
    timestamp: int = 0


@dataclass
class EmsDevice:
    """Model for an EMS device."""

    ecu_id: int = 0
    ecu_host: str = ""
    ecu_version: str = ""
    error: int = 0
    error_str: str = ""
    op_state: int = 0
    op_state_str: str = ""
    ems_info: EmsInfo = field(default_factory=EmsInfo)
    bms_info: List[BmsInfo] = field(default_factory=list)
    inv_info: InvInfo = field(default_factory=InvInfo)
    ems_config: EmsConfig = field(default_factory=EmsConfig)
    inv_config: InvConfig = field(default_factory=InvConfig)
    ems_control: EmsControl = field(default_factory=EmsControl)
    ems_data: EmsData = field(default_factory=EmsData)
    bms_data: List[BmsData] = field(default_factory=list)
    ems_prediction: EmsPrediction = field(default_factory=EmsPrediction)
    ems_voltage: EmsVoltage = field(default_factory=EmsVoltage)
    ems_current: EmsCurrent = field(default_factory=EmsCurrent)
    ems_aggregate: EmsAggregate = field(default_factory=EmsAggregate)
    error_cnt: int = 0


@dataclass
class HomevoltData:
    """Model for Homevolt data."""

    type: str = field(metadata={"json_field_name": "$type"}, default="")
    ts: int = 0
    ems: List[EmsDevice] = field(default_factory=list)
    aggregated: EmsDevice = field(default_factory=EmsDevice)
    sensors: List[SensorData] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HomevoltData:
        """Create a HomevoltData object from a dictionary."""
        return cls(
            type=data.get("$type", ""),
            ts=data.get("ts", 0),
            ems=[EmsDevice.from_dict(ems) for ems in data.get("ems", [])],
            aggregated=EmsDevice.from_dict(data.get("aggregated", {})),
            sensors=[
                SensorData.from_dict(sensor) for sensor in data.get("sensors", [])
            ],
        )


def _add_from_dict_methods():
    """Add from_dict methods to all dataclasses."""
    dataclasses = [
        EmsInfo,
        BmsInfo,
        InvInfo,
        EmsConfig,
        InvConfig,
        EmsControl,
        EmsData,
        BmsData,
        EmsPrediction,
        EmsVoltage,
        EmsCurrent,
        EmsAggregate,
        PhaseData,
        SensorData,
        EmsDevice,
    ]
    for dc in dataclasses:
        dc.from_dict = staticmethod(_create_from_dict(dc))


# Initialize the from_dict methods
_add_from_dict_methods()
