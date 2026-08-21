document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.MARKET_API_BASE_URL || (window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '');
    const apiUrl = (path) => `${API_BASE_URL}${path}`;
    const formatMoney = (number) => new Intl.NumberFormat('fa-IR').format(number);
    const toPersianDigits = (value) => String(value).replace(/[0-9]/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[digit]);
    const unitLabels = { toman: 'تومان', rial: 'ریال', usd: 'دلار' };

    // Product prices are recalculated whenever the live 18K value changes.
    const calculateProductPrices = () => {
        const liveGold = document.getElementById('live-gold-price');
        const rawGoldPrice = Number.parseFloat(liveGold?.dataset.rawPrice || '0');

        document.querySelectorAll('.product-card').forEach((product) => {
            const price = product.querySelector('.final-price');
            if (!price) return;
            if (!Number.isFinite(rawGoldPrice) || rawGoldPrice <= 0) {
                price.textContent = 'در انتظار نرخ زنده';
                return;
            }
            const weight = Number.parseFloat(product.dataset.weight) || 0;
            const makingCharge = Number.parseFloat(product.dataset.makingCharge) || 0;
            const profitPercent = Number.parseFloat(product.dataset.profit) || 7;
            const preProfit = (weight * rawGoldPrice) + makingCharge;
            const finalPrice = Math.round(preProfit + ((preProfit * profitPercent) / 100));
            price.innerHTML = `${formatMoney(finalPrice)} <small>تومان</small>`;
        });
    };

    calculateProductPrices();

    // Mobile navigation.
    const menuToggle = document.getElementById('menu-toggle');
    const mainNav = document.getElementById('main-nav');
    if (menuToggle && mainNav) {
        menuToggle.addEventListener('click', () => {
            const isOpen = mainNav.classList.toggle('is-open');
            menuToggle.setAttribute('aria-expanded', String(isOpen));
            menuToggle.innerHTML = isOpen ? '<i class="ph ph-x"></i>' : '<i class="ph ph-list"></i>';
        });

        mainNav.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
            mainNav.classList.remove('is-open');
            menuToggle.setAttribute('aria-expanded', 'false');
            menuToggle.innerHTML = '<i class="ph ph-list"></i>';
        }));
    }

    const siteHeader = document.getElementById('site-header');
    window.addEventListener('scroll', () => siteHeader?.classList.toggle('scrolled', window.scrollY > 20), { passive: true });

    // Lightweight entrance motion for an editorial first impression.
    const revealItems = document.querySelectorAll('.reveal');
    if ('IntersectionObserver' in window) {
        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });
        revealItems.forEach((item) => revealObserver.observe(item));
    } else {
        revealItems.forEach((item) => item.classList.add('is-visible'));
    }

    // Chart.js is fed only by saved market snapshots; no mock values are used.
    const canvas = document.getElementById('priceChart');
    const chartContainer = canvas?.closest('.chart-container');
    const chartFallback = chartContainer?.querySelector('.chart-fallback');
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
        normalChartGradient.addColorStop(0, 'rgba(184, 149, 86, .28)');
        normalChartGradient.addColorStop(1, 'rgba(184, 149, 86, 0)');
        fullscreenChartGradient = ctx.createLinearGradient(0, 0, 0, 300);
        fullscreenChartGradient.addColorStop(0, 'rgba(214, 182, 109, .38)');
        fullscreenChartGradient.addColorStop(.55, 'rgba(184, 149, 86, .24)');
        fullscreenChartGradient.addColorStop(1, 'rgba(184, 149, 86, .15)');

        Chart.defaults.font.family = 'Vazirmatn';
        Chart.defaults.color = '#81786e';
        priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{ data: [], borderColor: '#d6b66d', backgroundColor: normalChartGradient, borderWidth: 1.5, pointBackgroundColor: '#0d0c0b', pointBorderColor: '#d6b66d', pointBorderWidth: 1.5, pointRadius: 3, pointHoverRadius: 5, fill: true, tension: .42 }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { backgroundColor: '#211d18', borderColor: 'rgba(184,149,86,.4)', borderWidth: 1, titleFont: { family: 'Vazirmatn' }, bodyFont: { family: 'Vazirmatn' }, padding: 12, displayColors: false, callbacks: { label: (context) => `${formatMoney(context.raw)} تومان` } }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { font: { size: 9 } } },
                    y: { grid: { color: 'rgba(232,226,215,.07)' }, border: { display: false }, ticks: { font: { size: 9 }, callback: (value) => formatMoney(value) } }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });
    }

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

    const renderMarket = (payload) => {
        const marketMap = {
            gold18: 'live-gold-price',
            gold24: 'live-gold24-price',
            usd: 'live-dollar-price',
            eur: 'live-euro-price',
            silver: 'live-silver-price',
            tether: 'live-tether-price',
            coin_full: 'live-coin-full-price',
            coin_half: 'live-coin-half-price',
            coin_quarter: 'live-coin-quarter-price',
            ounce: 'live-ounce-price',
            oil: 'live-oil-price'
        };
        Object.entries(marketMap).forEach(([symbol, id]) => {
            const element = document.getElementById(id);
            const card = element?.closest('.price-card');
            const price = payload.prices?.[symbol];
            if (!element || !price || !Number.isFinite(Number(price.value))) return;
            const displayUnit = unitLabels[price.unit] || unitLabels[payload.unit] || price.unit || payload.unit || 'تومان';
            element.dataset.rawPrice = String(price.value);
            element.innerHTML = `${formatMoney(Number(price.value))} <small>${displayUnit}</small>`;
            renderTrend(card, price.change_percent);
        });
        calculateProductPrices();

        Object.entries(payload.chart || {}).forEach(([period, source]) => setChartData(period, source));
        const status = document.querySelector('.market-status');
        if (status) {
            status.classList.toggle('is-stale', Boolean(payload.stale));
            status.classList.toggle('is-error', false);
        }
    };

    const renderMarketError = () => {
        const status = document.querySelector('.market-status');
        if (!status) return;
        status.classList.remove('is-stale');
        status.classList.add('is-error');
    };

    let marketRequestInFlight = false;
    const loadMarketData = async () => {
        if (marketRequestInFlight) return;
        marketRequestInFlight = true;
        try {
            const response = await fetch(apiUrl('/api/market/'), { headers: { Accept: 'application/json' } });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || 'Market API unavailable');
            renderMarket(payload);
        } catch (error) {
            renderMarketError();
            console.warn('Market API request failed', error);
        } finally {
            marketRequestInFlight = false;
        }
    };

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

    // Fullscreen view for the market room.
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

    loadMarketData();
    window.setInterval(loadMarketData, 5000);

    // Consultation modal.
    const consultationModal = document.getElementById('consultation-modal');
    const modalCloseButton = document.getElementById('modal-close');
    const modalTriggers = document.querySelectorAll('.modal-trigger[data-modal="consultation"]');
    let lastFocusedElement = null;

    const openConsultationModal = () => {
        if (!consultationModal) return;
        lastFocusedElement = document.activeElement;
        consultationModal.classList.add('is-open');
        consultationModal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');
        modalCloseButton?.focus();
    };

    const closeConsultationModal = () => {
        if (!consultationModal) return;
        consultationModal.classList.remove('is-open');
        consultationModal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('modal-open');
        if (lastFocusedElement instanceof HTMLElement) lastFocusedElement.focus();
    };

    modalTriggers.forEach((trigger) => trigger.addEventListener('click', (event) => {
        event.preventDefault();
        openConsultationModal();
    }));

    modalCloseButton?.addEventListener('click', closeConsultationModal);
    consultationModal?.addEventListener('click', (event) => {
        if (event.target === consultationModal) closeConsultationModal();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && consultationModal?.classList.contains('is-open')) closeConsultationModal();
    });
});
