from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import HevyCoordinator

SENSORS = (
    ("workout_count", "Workout Count", None, "workouts"),
    ("last_workout_at", "Last Workout At", SensorDeviceClass.TIMESTAMP, None),
    ("last_workout_duration", "Last Workout Duration", None, "min"),
    ("last_workout_volume", "Last Workout Volume", None, "kg"),
    ("weekly_volume", "Weekly Volume", None, "kg"),
    ("current_streak", "Current Streak", None, "days"),
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator: HevyCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    entities.append(HevyWorkoutCountSensor(coordinator, entry))
    entities.append(HevyLastWorkoutAtSensor(coordinator, entry))
    entities.append(HevyLastWorkoutDurationSensor(coordinator, entry))
    entities.append(HevyLastWorkoutVolumeSensor(coordinator, entry))
    entities.append(HevyWeeklyVolumeSensor(coordinator, entry))
    entities.append(HevyStreakSensor(coordinator, entry))

    async_add_entities(entities)

class HevyBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HevyCoordinator, entry: ConfigEntry, key: str, name: str):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        acct = coordinator.data.get("account") or {}
        uid = acct.get("id", "me")
        self._attr_unique_id = f"{entry.entry_id}_{uid}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, uid)},
            "name": acct.get("full_name") or acct.get("username") or "Hevy",
            "manufacturer": "Hevy",
            "model": "Hevy API",
        }

class HevyWorkoutCountSensor(HevyBaseSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "workout_count", "Workout Count")

    @property
    def native_value(self):
        return self.coordinator.data.get("workout_count")

class HevyLastWorkoutAtSensor(HevyBaseSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "last_workout_at", "Last Workout At")

    @property
    def native_value(self):
        latest = self.coordinator.data.get("latest") or {}
        return latest.get("started_at")

class HevyLastWorkoutDurationSensor(HevyBaseSensor):
    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "last_workout_duration", "Last Workout Duration")

    @property
    def native_value(self):
        latest = self.coordinator.data.get("latest") or {}
        return latest.get("duration_min")

class HevyLastWorkoutVolumeSensor(HevyBaseSensor):
    _attr_native_unit_of_measurement = "kg"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "last_workout_volume", "Last Workout Volume")

    @property
    def native_value(self):
        latest = self.coordinator.data.get("latest") or {}
        return latest.get("total_volume")

class HevyWeeklyVolumeSensor(HevyBaseSensor):
    _attr_native_unit_of_measurement = "kg"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "weekly_volume", "Weekly Volume")

    @property
    def native_value(self):
        return self.coordinator.data.get("weekly_volume")

class HevyStreakSensor(HevyBaseSensor):
    _attr_native_unit_of_measurement = "days"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "current_streak", "Current Streak")

    @property
    def native_value(self):
        # Hevy API may not provide streak directly; compute best-effort from 'last_workout_at' only.
        # If last workout was today => streak at least 1, else 0.
        latest = self.coordinator.data.get("latest") or {}
        started = latest.get("started_at")
        if not started:
            return None
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(str(started).replace("Z","+00:00"))
            now = datetime.now(timezone.utc)
            if dt.date() == now.date():
                return 1
            return 0
        except Exception:
            return None
