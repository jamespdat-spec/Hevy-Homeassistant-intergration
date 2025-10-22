# Hevy for Home Assistant (HACS)

Track your **Hevy** workouts in Home Assistant: last workout, weekly volume, workout count, streak, and more.

> **Requirements**
> - Hevy **Pro** (API access)
> - Your **Hevy Developer API key**
> - Your **Hevy email/username** and **password**

This is a **custom integration** you can install via **HACS** (Custom repositories) or manually.

---

## Features (v0.1.0)

- UI-based setup (Config Flow)
- Secure login against Hevy (`/login`) using your email/username + password
- Uses your Hevy Developer API key (`x-api-key`)
- Sensors:
  - `sensor.hevy_workout_count`
  - `sensor.hevy_last_workout_at`
  - `sensor.hevy_last_workout_duration`
  - `sensor.hevy_last_workout_volume`
  - `sensor.hevy_weekly_volume`
  - `sensor.hevy_current_streak`
- Adjustable update interval (default 30 min)
- Robust error handling, auth re-use & re-login
- Diagnostics (Enable debugging in HA to see API traces)

> **Note**: Hevy’s API is evolving and officially limited to Pro users. Endpoints/fields may change.
> The integration tries to degrade gracefully.

## Install

### HACS (recommended)

1. HACS → **Integrations** → **⋮** → **Custom repositories**
2. Add this repo URL and select **Integration**.
3. Install **Hevy** and **Restart** Home Assistant.
4. Settings → Devices & Services → **Add Integration** → **Hevy**.

### Manual

Copy `custom_components/hevy/` into your Home Assistant `custom_components/` folder and restart.

## Configuration

During setup you’ll be asked for:

- **API Key** (from Hevy Developer settings)
- **Email or Username**
- **Password**
- **Update interval** (optional)

The integration stores an `auth-token` after login and refreshes it when needed.

## Entities

- **Workout Count** – total number of workouts in your account
- **Last Workout At** – timestamp of your most recent workout
- **Last Workout Duration** – minutes
- **Last Workout Volume** – total weight lifted in your latest workout
- **Weekly Volume** – total weight lifted during the rolling last 7 days
- **Current Streak** – consecutive days with a workout

If a field is not available from the API, its sensor will be `unknown` (integration will try fallbacks).

## Services

- `hevy.refresh` — force an immediate data refresh

## Troubleshooting

- Ensure you have **Hevy Pro** and a valid **API key**.
- If you change your Hevy password, reconfigure the integration.
- Enable logging to file and share snippets when opening issues.

```yaml
logger:
  default: warning
  logs:
    custom_components.hevy: debug
```

## Privacy

Your credentials and token are stored in Home Assistant’s encrypted storage
(config entries). The integration only pulls workout/account data to compute
metrics and does not upload your HA data anywhere.

## Credits

- Hevy API docs: https://api.hevyapp.com/docs/
- Community reverse-engineering notes and examples
- Inspired by UnderTheBar and other clients

## License

MIT
