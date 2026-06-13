from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .api import ShenzhenWaterData
from .const import CONF_CUSTOMER_CODES, DATA_COORDINATOR, DOMAIN

UNIT_CNY = "CNY"
UNIT_CUBIC_METERS = "m³"


@dataclass(frozen=True, kw_only=True)
class ShenzhenWaterSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[ShenzhenWaterData], float | int | str | None]
    attrs_fn: Callable[[ShenzhenWaterData], dict[str, Any]] | None = None


SENSORS: tuple[ShenzhenWaterSensorEntityDescription, ...] = (
    ShenzhenWaterSensorEntityDescription(
        key="latest_bill",
        translation_key="latest_bill",
        value_fn=lambda data: data.latest_bill.bill_month if data.latest_bill else None,
        attrs_fn=lambda data: _latest_bill_attributes(data),
    ),
    ShenzhenWaterSensorEntityDescription(
        key="total_amount",
        translation_key="total_amount",
        native_unit_of_measurement=UNIT_CNY,
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda data: data.latest_bill.total_amount if data.latest_bill else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="water_amount",
        translation_key="water_amount",
        native_unit_of_measurement=UNIT_CNY,
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda data: data.latest_bill.water_amount if data.latest_bill else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="sewage_amount",
        translation_key="sewage_amount",
        native_unit_of_measurement=UNIT_CNY,
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda data: data.latest_bill.sewage_amount if data.latest_bill else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="garbage_amount",
        translation_key="garbage_amount",
        native_unit_of_measurement=UNIT_CNY,
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda data: data.latest_bill.garbage_amount if data.latest_bill else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="need_pay",
        translation_key="need_pay",
        native_unit_of_measurement=UNIT_CNY,
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda data: data.latest_bill.need_pay if data.latest_bill else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="water_consumption",
        translation_key="water_consumption",
        native_unit_of_measurement=UNIT_CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.latest_bill.water_consumption if data.latest_bill else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="payment_status",
        translation_key="payment_status",
        value_fn=lambda data: data.latest_bill.payment_status if data.latest_bill else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="due_date",
        translation_key="due_date",
        value_fn=lambda data: data.latest_bill.due_date if data.latest_bill else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="meter_current_reading",
        translation_key="meter_current_reading",
        native_unit_of_measurement=UNIT_CUBIC_METERS,
        value_fn=lambda data: data.latest_bill.meter_current_reading
        if data.latest_bill
        else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="meter_previous_reading",
        translation_key="meter_previous_reading",
        native_unit_of_measurement=UNIT_CUBIC_METERS,
        value_fn=lambda data: data.latest_bill.meter_previous_reading
        if data.latest_bill
        else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="meter_current_date",
        translation_key="meter_current_date",
        value_fn=lambda data: data.latest_bill.meter_current_date
        if data.latest_bill
        else None,
    ),
    ShenzhenWaterSensorEntityDescription(
        key="meter_previous_date",
        translation_key="meter_previous_date",
        value_fn=lambda data: data.latest_bill.meter_previous_date
        if data.latest_bill
        else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    customer_code = entry.data[CONF_CUSTOMER_CODES][0]
    async_add_entities(
        ShenzhenWaterSensor(coordinator, entry, customer_code, description)
        for description in SENSORS
    )


class ShenzhenWaterSensor(CoordinatorEntity, SensorEntity):
    entity_description: ShenzhenWaterSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        customer_code: str,
        description: ShenzhenWaterSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, customer_code)},
            "name": f"深圳水务 {customer_code}",
            "manufacturer": "深圳水务集团",
        }

    @property
    def native_value(self) -> float | int | str | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)


def _latest_bill_attributes(data: ShenzhenWaterData) -> dict[str, Any]:
    if data.latest_bill is None:
        return {
            "result_code": data.result_code,
            "result_message": data.result_message,
        }
    bill = data.latest_bill
    return {
        "customer_code": bill.customer_code,
        "bill_month": bill.bill_month,
        "total_amount": bill.total_amount,
        "water_amount": bill.water_amount,
        "sewage_amount": bill.sewage_amount,
        "garbage_amount": bill.garbage_amount,
        "late_fee": bill.late_fee,
        "need_pay": bill.need_pay,
        "water_consumption": bill.water_consumption,
        "water_after_reduced": bill.water_after_reduced,
        "due_date": bill.due_date,
        "payment_status": bill.payment_status,
        "water_status": bill.water_status,
        "sewage_status": bill.sewage_status,
        "garbage_status": bill.garbage_status,
        "meter_code": bill.meter_code,
        "meter_current_reading": bill.meter_current_reading,
        "meter_previous_reading": bill.meter_previous_reading,
        "meter_current_date": bill.meter_current_date,
        "meter_previous_date": bill.meter_previous_date,
        "water_use_days": bill.water_use_days,
        "result_code": data.result_code,
        "result_message": data.result_message,
    }
