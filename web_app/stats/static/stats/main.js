document.addEventListener('DOMContentLoaded', async () => {
    const tg = window.Telegram.WebApp;
    tg.ready();
    if (tg.requestFullscreen) {
        tg.requestFullscreen();
    } else {
        tg.expand();
    }

    const loader = document.getElementById('loader');
    const mainContent = document.getElementById('main-content');
    const apiUrl = document.body.dataset.apiUrl;
    const initData = tg.initData;

    // Редирект на 403, если зашли не через Telegram
    if (!initData) {
        window.location.href = '/forbidden/';
        return;
    }

    try {
        const response = await fetch(apiUrl, {
            headers: {
                'Authorization': `tma ${initData}`
            }
        });

        if (!response.ok) {
            window.location.href = '/forbidden/';
            return;
        }

        const data = await response.json();
        renderStats(data);

        loader.classList.add('hidden');
        mainContent.classList.remove('hidden');
    } catch (err) {
        window.location.href = '/forbidden/';
    }

    function renderStats(data) {
        const panelsContainer = document.getElementById('panels-container');
        const chartContainer = document.getElementById('chart-container');
        const ecoContainer = document.getElementById('eco-container');

        panelsContainer.innerHTML = '';
        chartContainer.innerHTML = '';

        data.planets_data.forEach((planet, index) => {
            const cycleNum = (index % 6) + 1;

            const upperCitiesHtml = planet.cities_data.map(city => `
                <div class="${city.development === 0 ? 'dead-city' : 'city'}">${escapeHtml(city.name)}</div>
            `).join('');

            const lowerCitiesHtml = planet.cities_data.map(city => `
                <div class="${city.development === 0 ? 'dead-percentage' : 'city'}">${city.development}%</div>
            `).join('');

            panelsContainer.insertAdjacentHTML('beforeend', `
                <p class="name"><strong>${escapeHtml(planet.name)}</strong></p>
                <div class="panel">
                    <div class="upper-half-${cycleNum}">${upperCitiesHtml}</div>
                    <div class="lower-half">${lowerCitiesHtml}</div>
                </div>
            `);

            chartContainer.insertAdjacentHTML('beforeend', `
                <div class="bar" style="height: ${planet.bar_height}%;">
                    <span class="value">${planet.rate_of_life}%</span>
                    <span class="label">${escapeHtml(planet.name)}</span>
                </div>
            `);
        });

        ecoContainer.textContent = ` Уровень аномалии 🌌: ${data.anomaly_level}%`;
    }

    function escapeHtml(str) {
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
});
