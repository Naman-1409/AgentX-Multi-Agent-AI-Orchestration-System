-- Schema DDL for Live Weather Radar App with 7-day forecast and temperature toggle
CREATE TABLE IF NOT EXISTS live_weather_radar_app_with_7_day_forecast_and_temperature_toggle_records (
    id VARCHAR(64) PRIMARY KEY,
    name TEXT NOT NULL,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_live_weather_radar_app_with_7_day_forecast_and_temperature_toggle_created ON live_weather_radar_app_with_7_day_forecast_and_temperature_toggle_records(created_at);