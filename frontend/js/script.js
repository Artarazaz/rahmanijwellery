document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.MARKET_API_BASE_URL || (window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '');
    const apiUrl = (path) => `${API_BASE_URL}${path}`;
    const formatMoney = (number) => new Intl.NumberFormat('fa-IR').format(number);
    const toPersianDigits = (value) => String(value).replace(/[0-9]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[d]);
    const unitLabels = { toman: 'تومان', rial: 'ریال', usd: 'دلار' };
    const calculateProductPrices = () => window.Rahmani?.calculateProductPrices?.();

    // ── Chart setup ──
    const canvas = document.getElementById('priceChart');
    const chartContainer = canvas?.closest('.chart-container');
    const chartDataSources = {
        hourly: { labels: [], data: [] },
        daily: { labels: [], data: [] },
        monthly: { labels: [], data: [] }
    };
    let currentPeriod = 'hourly';
    let priceChart = null;
    let normalChartGradient = null;
    let fullscreenChartGradient = null;

    const setChartData = (period, source) => {
        const labels = Array.isArray(source?.labels) ? source.labels : [];
        const values = Array.isArray(source?.values) ? source.values : (source?.data || []);
        chartDataSources[period] = { labels, data: values.map(Number).filter(Number.isFinite) };
        if (period !== currentPeriod || !priceChart) return;
        priceChart.data.labels = chartDataSources[period].labels;
        priceChart.data.datasets[0].data = chartDataSources[period].data;
        priceChart.update('none');
        chartContainer?.classList.toggle('has-chart', chartDataSources[period].data.length > 0);
    };

    if (canvas && window.Chart) {
        const ctx = canvas.getContext('2d');
        normalChartGradient = ctx.createLinearGradient(0, 0, 0, 300);
        normalChartGradient.addColorStop(0, 'rgba(232, 176, 138, .28)');
        normalChartGradient.addColorStop(1, 'rgba(232, 176, 138, 0)');
        fullscreenChartGradient = ctx.createLinearGradient(0, 0, 0, 300);
        fullscreenChartGradient.addColorStop(0, 'rgba(240, 200, 160, .38)');
        fullscreenChartGradient.addColorStop(.55, 'rgba(232, 176, 138, .24)');
        fullscreenChartGradient.addColorStop(1, 'rgba(232, 176, 138, .15)');

        Chart.defaults.font.family = 'Vazirmatn';
        Chart.defaults.color = '#b8a99a';
        priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{ data: [], borderColor: '#f0c8a0', backgroundColor: normalChartGradient, borderWidth: 1.5, pointBackgroundColor: '#0d0c0b', pointBorderColor: '#f0c8a0', pointBorderWidth: 1.5, pointRadius: 3, pointHoverRadius: 5, fill: true, tension: .42 }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { backgroundColor: '#211d18', borderColor: 'rgba(232,176,138,.4)', borderWidth: 1, titleFont: { family: 'Vazirmatn' }, bodyFont: { family: 'Vazirmatn' }, padding: 12, displayColors: false, callbacks: { label: (context) => `${formatMoney(context.raw)} تومان` } }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { font: { size: 9 } } },
                    y: { grid: { color: 'rgba(255,244,233,.07)' }, border: { display: false }, ticks: { font: { size: 9 }, callback: (value) => formatMoney(value) } }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });
    }

    // ── Render helpers ──
    const renderTrend = (card, change) => {
        const trend = card?.querySelector('.trend');
        if (!trend) return;
        const numericChange = Number(change);
        if (!Number.isFinite(numericChange)) {
            trend.className = 'trend neutral';
            trend.innerHTML = '<i class="ph ph-minus"></i> در انتظار مقایسه';
            return;
        }
        const direction = numericChange > 0 ? 'positive' : numericChange < 0 ? 'negative' : 'neutral';
        const icon = numericChange > 0 ? 'ph-arrow-up-left' : numericChange < 0 ? 'ph-arrow-down-left' : 'ph-minus';
        const prefix = numericChange > 0 ? '+' : '';
        trend.className = `trend ${direction}`;
        trend.innerHTML = `<i class="ph ${icon}"></i> ${prefix}${toPersianDigits(numericChange.toFixed(2))}٪ نسبت به اولین قیمت امروز`;
    };

    const renderMarket = (prices) => {
        const marketMap = {
            gold18: 'live-gold-price',
            gold24: 'live-gold24-price',
            usd: 'live-dollar-price',
            eur: 'live-euro-price',
            dirham: 'live-dirham-price',
            tether: 'live-tether-price',
            silver: 'live-silver-price',
            coin_full: 'live-coin-full-price',
            coin_old: 'live-coin-old-price',
            coin_half: 'live-coin-half-price',
            coin_quarter: 'live-coin-quarter-price',
            ounce: 'live-ounce-price',
            silver_ounce: 'live-silver-ounce-price',
            oil: 'live-oil-price'
        };
        const globalSymbols = new Set(['ounce', 'silver_ounce', 'oil']);
        Object.entries(marketMap).forEach(([symbol, id]) => {
            const element = document.getElementById(id);
            const card = element?.closest('.price-card');
            const value = prices[symbol];
            if (!element || value == null || !Number.isFinite(Number(value))) return;
            const isGlobal = globalSymbols.has(symbol);
            const displayValue = isGlobal ? Number(value) : Math.round(Number(value) / 10);
            const unit = isGlobal ? 'دلار' : 'تومان';
            element.dataset.rawPrice = String(value);
            element.textContent = formatMoney(displayValue);
            const unitEl = card?.querySelector('.price-unit');
            if (unitEl) unitEl.textContent = unit;
            renderTrend(card, null);
        });
        calculateProductPrices();

        // Populate ticker strip
        const tickerGold18 = document.getElementById('ticker-gold18');
        const tickerGold24 = document.getElementById('ticker-gold24');
        const tickerCoin = document.getElementById('ticker-coin');
        const tickerUsd = document.getElementById('ticker-usd');
        const tickerOunce = document.getElementById('ticker-ounce');
        if (tickerGold18 && prices.gold18) tickerGold18.textContent = formatMoney(Math.round(prices.gold18 / 10)) + ' تومان';
        if (tickerGold24 && prices.gold24) tickerGold24.textContent = formatMoney(Math.round(prices.gold24 / 10)) + ' تومان';
        if (tickerCoin && prices.coin_full) tickerCoin.textContent = formatMoney(Math.round(prices.coin_full / 10)) + ' تومان';
        if (tickerUsd && prices.usd) tickerUsd.textContent = formatMoney(Math.round(prices.usd / 10)) + ' تومان';
        if (tickerOunce && prices.ounce) tickerOunce.textContent = '$' + formatMoney(prices.ounce);

        const status = document.querySelector('.market-status');
        if (status) {
            status.classList.remove('is-stale', 'is-error');
        }
    };

    const renderMarketError = () => {
        const status = document.querySelector('.market-status');
        if (!status) return;
        status.classList.remove('is-stale');
        status.classList.add('is-error');
    };

    // ── Pure HTML web scraping from tgju.org ──
    const PERSIAN_DIGITS_RE = /[۰-۹٠-٩]/g;
    const persianToLatin = (ch) => {
        const all = '۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩';
        const idx = all.indexOf(ch);
        return idx >= 0 ? String(idx % 10) : ch;
    };

    const parsePrice = (text) => {
        if (text == null) return null;
        const cleaned = String(text).replace(/[,٬+%]/g, '').trim();
        const match = cleaned.match(/-?\d+(?:\.\d+)?/);
        if (!match) return null;
        const n = Number(match[0]);
        return Number.isFinite(n) ? n : null;
    };

    const normaliseText = (t) => t
        .replace(/ي/g, 'ی').replace(/ك/g, 'ک')
        .replace(/‌/g, ' ').replace(/\s+/g, ' ').trim();

    // Symbol mapping: Persian label → internal symbol
    const LABEL_MAP = [
        ['طلای ۱۸ عیار', 'gold18'],
        ['طلای 24 عیار', 'gold24'], ['طلای ۲۴ عیار', 'gold24'],
        ['دلار', 'usd'],
        ['یورو', 'eur'],
        ['درهم امارات', 'dirham'], ['درهم', 'dirham'],
        ['تتر', 'tether'],
        ['سکه امامی', 'coin_full'],
        ['سکه بهار آزادی', 'coin_old'],
        ['نیم سکه', 'coin_half'],
        ['ربع سکه', 'coin_quarter'],
        ['نقره ۹۲۵', 'silver'], ['گرم نقره', 'silver'],
        ['انس جهانی طلا', 'ounce'], ['انس طلا', 'ounce'],
        ['انس نقره', 'silver_ounce'], ['انس جهانی نقره', 'silver_ounce'],
        ['نفت برنت', 'oil'],
    ];

    const MR_MAP = {
        geram18: 'gold18', geram24: 'gold24',
        price_dollar_rl: 'usd', price_eur: 'eur',
        price_aed: 'dirham', 'crypto-tether': 'tether',
        sekee: 'coin_full', sekeb: 'coin_old',
        nim: 'coin_half', rob: 'coin_quarter',
        silver_999: 'silver',
        ons: 'ounce', silver: 'silver_ounce',
        oil_brent: 'oil',
    };

    const symbolForLabel = (label) => {
        const norm = normaliseText(label);
        if (!norm || norm.includes('ذاتی')) return null;
        for (const [needle, symbol] of LABEL_MAP) {
            if (norm.includes(needle)) return symbol;
        }
        return null;
    };

    const scrapeTGJUPricesFromHTML = async () => {
        const resp = await fetch(apiUrl('/api/scrape-proxy/'), {
            headers: { 'Accept': 'text/html' },
        });
        if (!resp.ok) throw new Error(`TGJU proxy ${resp.status}`);
        const html = await resp.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const found = {};

        // Extract from <tr> rows
        doc.querySelectorAll('tr[data-market-row]').forEach(tr => {
            const mr = tr.getAttribute('data-market-row');
            const mapped = MR_MAP[mr];
            if (mapped && found[mapped] == null) {
                const dp = tr.getAttribute('data-price');
                if (dp) {
                    const v = parsePrice(dp);
                    if (v != null) found[mapped] = v;
                }
            }
        });

        // Extract from table cells by label
        doc.querySelectorAll('tr').forEach(tr => {
            const cells = tr.querySelectorAll('td, th');
            if (cells.length < 2) return;
            const label = cells[0].textContent;
            const symbol = symbolForLabel(label);
            if (symbol && found[symbol] == null) {
                const v = parsePrice(cells[1].textContent);
                if (v != null) found[symbol] = v;
            }
        });

        // Extract from <li id="l-..."> ticker items
        doc.querySelectorAll('li[id^="l-"]').forEach(li => {
            const slug = li.id.replace(/^l-/, '');
            const mapped = MR_MAP[slug];
            if (mapped && found[mapped] == null) {
                const priceEl = li.querySelector('.info-price, [class*="price"]');
                if (priceEl) {
                    const v = parsePrice(priceEl.textContent);
                    if (v != null) found[mapped] = v;
                }
            }
        });

        return found;
    };

    // ── Main data loader ──
    let marketRequestInFlight = false;
    const loadMarketData = async () => {
        if (marketRequestInFlight) return;
        marketRequestInFlight = true;
        try {
            const prices = await scrapeTGJUPricesFromHTML();
            if (prices.gold18) {
                renderMarket(prices);
                return;
            }
        } catch (err) {
            console.warn('TGJU scrape failed:', err);
        } finally {
            marketRequestInFlight = false;
        }
        renderMarketError();
    };

    // ── Chart period toggle ──
    document.querySelectorAll('.btn-toggle').forEach((button) => button.addEventListener('click', () => {
        document.querySelectorAll('.btn-toggle').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        currentPeriod = button.dataset.period;
        const source = chartDataSources[currentPeriod];
        if (priceChart && source) {
            priceChart.data.labels = source.labels;
            priceChart.data.datasets[0].data = source.data;
            priceChart.update();
            chartContainer?.classList.toggle('has-chart', source.data.length > 0);
        }
    }));

    // ── Fullscreen ──
    const fullscreenButton = document.getElementById('fullscreen-toggle');
    const fullscreenExitButton = document.getElementById('fullscreen-exit');
    const fullscreenTarget = document.querySelector('.market-board');
    const updateChartGradient = () => {
        if (!priceChart || !normalChartGradient || !fullscreenChartGradient) return;
        const isFullscreen = document.fullscreenElement === fullscreenTarget || fullscreenTarget?.classList.contains('is-fallback-fullscreen');
        priceChart.data.datasets[0].backgroundColor = isFullscreen ? fullscreenChartGradient : normalChartGradient;
        priceChart.update('none');
    };
    const updateFullscreenButton = () => {
        const isFullscreen = document.fullscreenElement === fullscreenTarget || fullscreenTarget?.classList.contains('is-fallback-fullscreen');
        if (fullscreenButton) {
            fullscreenButton.setAttribute('aria-label', isFullscreen ? 'خروج از حالت تمام صفحه' : 'باز کردن قیمت‌ها در حالت تمام صفحه');
            fullscreenButton.innerHTML = isFullscreen ? '<i class="ph ph-arrows-in"></i><span>خروج از تمام صفحه</span>' : '<i class="ph ph-arrows-out"></i><span>مشاهده تمام صفحه</span>';
        }
    };
    const toggleFullscreen = async () => {
        try {
            if (fullscreenTarget?.classList.contains('is-fallback-fullscreen')) {
                fullscreenTarget.classList.remove('is-fallback-fullscreen');
                updateFullscreenButton();
            } else if (document.fullscreenElement) await document.exitFullscreen();
            else if (fullscreenTarget?.requestFullscreen) await fullscreenTarget.requestFullscreen();
            else {
                fullscreenTarget?.classList.add('is-fallback-fullscreen');
                updateFullscreenButton();
            }
        } catch (error) {
            fullscreenTarget?.classList.add('is-fallback-fullscreen');
            updateFullscreenButton();
        }
    };
    fullscreenButton?.addEventListener('click', toggleFullscreen);
    fullscreenExitButton?.addEventListener('click', toggleFullscreen);
    document.addEventListener('fullscreenchange', () => {
        updateFullscreenButton();
        updateChartGradient();
    });
    updateFullscreenButton();
    updateChartGradient();

    // ── Start: fetch every 5 seconds ──
    loadMarketData();
    window.setInterval(loadMarketData, 5000);
});
