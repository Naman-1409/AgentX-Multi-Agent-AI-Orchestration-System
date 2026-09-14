let currentTempC = 20;
let isCelsius = true;

async function fetchWeather() {
  const cityInput = document.getElementById('city-input');
  const city = (cityInput.value || 'London').trim();
  const tempEl = document.getElementById('temp-display');
  const condEl = document.getElementById('condition-display');
  const locEl = document.getElementById('location-display');
  const windEl = document.getElementById('wind-speed');
  const dirEl = document.getElementById('wind-dir');

  try {
    condEl.textContent = '⏳ Querying satellite forecast...';
    const geoRes = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1`);
    const geoData = await geoRes.json();
    if (!geoData.results || geoData.results.length === 0) {
      condEl.textContent = '❌ City not found. Try another city.';
      return;
    }

    const loc = geoData.results[0];
    const wRes = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${loc.latitude}&longitude=${loc.longitude}&current_weather=true`);
    const wData = await wRes.json();
    const curr = wData.current_weather;

    currentTempC = curr.temperature;
    locEl.textContent = `📍 ${loc.name}, ${loc.country || ''} (${loc.latitude.toFixed(2)}°, ${loc.longitude.toFixed(2)}°)`;
    windEl.textContent = `${curr.windspeed} km/h`;
    dirEl.textContent = `${curr.winddirection}°`;
    condEl.textContent = `🌤️ Live Forecast Synchronized`;

    updateTempDisplay();
  } catch (err) {
    condEl.textContent = '⚠️ Network error: ' + err.message;
  }
}

function toggleUnits() {
  isCelsius = !isCelsius;
  updateTempDisplay();
}

function updateTempDisplay() {
  const tempEl = document.getElementById('temp-display');
  if (isCelsius) {
    tempEl.textContent = `${currentTempC.toFixed(1)} °C`;
  } else {
    const tempF = (currentTempC * 9/5) + 32;
    tempEl.textContent = `${tempF.toFixed(1)} °F`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  fetchWeather();
  const input = document.getElementById('city-input');
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') fetchWeather();
    });
  }
});