window.Rahmani = window.Rahmani || {};

(() => {
    const API_BASE_URL = window.MARKET_API_BASE_URL || (window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '');
    const apiUrl = (path) => `${API_BASE_URL}${path}`;
    const formatMoney = (number) => new Intl.NumberFormat('fa-IR').format(number);
    const toPersianDigits = (value) => String(value).replace(/[0-9]/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[digit]);
    const padIndex = (value) => toPersianDigits(String(value).padStart(2, '0'));
    const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[char]));

    const getCookie = (name) => {
        const match = document.cookie.split(';').map((item) => item.trim()).find((item) => item.startsWith(`${name}=`));
        return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : '';
    };

    const fetchJson = async (path, options = {}) => {
        const headers = { Accept: 'application/json', ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }
        const csrf = getCookie('csrftoken');
        if (csrf) headers['X-CSRFToken'] = csrf;
        const response = await fetch(apiUrl(path), { credentials: 'same-origin', ...options, headers });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || 'درخواست ناموفق بود.');
        return payload;
    };

    const calculateProductPrices = () => {
        const liveGold = document.getElementById('live-gold-price');
        const rawGoldPrice = Number.parseFloat(liveGold?.dataset.rawPrice || document.documentElement.dataset.gold18 || '0');
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

    const loadGoldRate = async () => {
        try {
            const payload = await fetchJson('/api/market/');
            const value = Number(payload.prices?.gold18?.value);
            if (Number.isFinite(value) && value > 0) document.documentElement.dataset.gold18 = String(value);
            calculateProductPrices();
        } catch (error) {
            calculateProductPrices();
        }
    };

    const productCardHtml = (product, index, total, featured = false) => {
        const image = product.images?.[0]?.url || 'assets/gold_necklace_1786118350826.png';
        const weight = toPersianDigits(product.weight);
        const featuredClass = featured ? ' product-card-featured' : '';
        return `
            <article class="product-card${featuredClass} reveal is-visible" data-product-id="${product.id}" data-weight="${product.weight}" data-making-charge="${product.making_charge}" data-profit="${product.profit}">
                <div class="product-media">
                    <span class="product-index">${padIndex(index)} / ${padIndex(total)}</span>
                    <img src="${escapeHtml(image)}" alt="${escapeHtml(product.name)}" loading="lazy">
                    <button class="product-action" type="button" data-product-id="${product.id}">مشاهده جزئیات <i class="ph ph-arrow-up-left"></i></button>
                </div>
                <div class="product-info">
                    <div class="product-title-row">
                        <h3>${escapeHtml(product.name)}</h3><span>${escapeHtml(product.sku || product.category_label)}</span>
                    </div>
                    <p class="product-note">${escapeHtml(product.note || product.category_label)}</p>
                    <div class="product-data"><span><i class="ph ph-scales"></i> ${weight} گرم</span><span><i class="ph ph-sparkle"></i> طلای ۱۸ عیار</span></div>
                    <div class="calculated-price"><span>قیمت نهایی</span><strong class="final-price">در حال محاسبه...</strong></div>
                </div>
            </article>
        `;
    };

    const revealVisible = (root) => {
        root.querySelectorAll('.reveal').forEach((item) => item.classList.add('is-visible'));
    };

    const bindProductActions = (root, products) => {
        root.querySelectorAll('[data-product-id].product-action, .product-card').forEach((element) => {
            const open = (event) => {
                if (event.target.closest('a')) return;
                const id = Number(element.dataset.productId || element.closest('.product-card')?.dataset.productId);
                const product = products.find((item) => item.id === id);
                if (product) openProductModal(product);
            };
            if (element.classList.contains('product-action')) {
                element.addEventListener('click', (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    open(event);
                });
            }
        });
    };

    const openProductModal = (product) => {
        const modal = document.getElementById('product-modal');
        if (!modal) {
            document.querySelector('.modal-trigger')?.click();
            return;
        }
        const images = product.images?.length ? product.images : [{ url: 'assets/gold_necklace_1786118350826.png' }];
        modal.querySelector('[data-product-title]').textContent = product.name;
        modal.querySelector('[data-product-note]').textContent = product.note || product.category_label;
        modal.querySelector('[data-product-meta]').innerHTML = `
            <span>${product.category_label}</span>
            <span>${product.sku || 'بدون کد'}</span>
            <span>${toPersianDigits(product.weight)} گرم</span>
        `;
        modal.querySelector('[data-product-gallery]').innerHTML = images.map((image) => `<img src="${image.url}" alt="${product.name}">`).join('');
        const priceHost = modal.querySelector('[data-product-price]');
        priceHost.dataset.weight = product.weight;
        priceHost.dataset.makingCharge = product.making_charge;
        priceHost.dataset.profit = product.profit;
        priceHost.className = 'product-card';
        priceHost.innerHTML = '<strong class="final-price">در حال محاسبه...</strong>';
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');
        calculateProductPrices();
    };

    const initProductModal = () => {
        const modal = document.getElementById('product-modal');
        if (!modal) return;
        const close = () => {
            modal.classList.remove('is-open');
            modal.setAttribute('aria-hidden', 'true');
            if (!document.querySelector('.modal-overlay.is-open')) document.body.classList.remove('modal-open');
        };
        modal.querySelector('.modal-close')?.addEventListener('click', close);
        modal.addEventListener('click', (event) => {
            if (event.target === modal) close();
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && modal.classList.contains('is-open')) close();
        });
    };

    const renderProducts = (root, products, { featuredFirst = false } = {}) => {
        if (!root) return;
        if (!products.length) {
            root.innerHTML = '<p class="catalog-empty">در این دسته هنوز قطعه‌ای ثبت نشده است.</p>';
            return;
        }
        root.innerHTML = products.map((product, index) => productCardHtml(product, index + 1, products.length, featuredFirst && index === 0)).join('');
        revealVisible(root);
        bindProductActions(root, products);
        calculateProductPrices();
    };

    const initChrome = () => {
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
    };

    const initConsultationModal = () => {
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
            if (!document.querySelector('.modal-overlay.is-open')) document.body.classList.remove('modal-open');
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
    };

    const initHomeCatalog = async () => {
        const root = document.getElementById('featured-products');
        if (!root) return;
        try {
            const featured = await fetchJson('/api/products/?featured=1&limit=3');
            const payload = featured.products.length ? featured : await fetchJson('/api/products/?limit=3');
            renderProducts(root, payload.products);
        } catch (error) {
            root.innerHTML = '<p class="catalog-empty">در حال حاضر نمایش کالکشن ممکن نیست.</p>';
        }
    };

    const CATEGORY_LABELS = {
        ring: 'انگشتر',
        earring: 'گوشواره',
        necklace: 'گردنبند',
        bracelet: 'دستبند',
        other: 'سایر'
    };

    const initProductsPage = async () => {
        const root = document.getElementById('catalog-grid');
        const filters = document.getElementById('catalog-filters');
        if (!root || !filters) return;

        // Read category from URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        let currentCategory = urlParams.get('category') || '';

        // Show filter banner if category is set from URL
        const showFilterBanner = (catId) => {
            let banner = document.getElementById('filter-banner');
            if (!banner) {
                banner = document.createElement('div');
                banner.id = 'filter-banner';
                banner.className = 'filter-banner';
                const catalogPage = document.querySelector('.catalog-page');
                if (catalogPage) catalogPage.prepend(banner);
            }
            if (catId && CATEGORY_LABELS[catId]) {
                banner.innerHTML = `<span>فیلتر <strong>${CATEGORY_LABELS[catId]}</strong> برای شما فعال شد. می‌توانید فیلترها را تغییر دهید.</span><button onclick="this.parentElement.remove()" type="button" aria-label="بستن">✕</button>`;
                banner.style.display = 'flex';
            } else {
                banner.style.display = 'none';
            }
        };

        showFilterBanner(currentCategory);

        const paint = async () => {
            const query = currentCategory ? `?category=${encodeURIComponent(currentCategory)}` : '';
            const payload = await fetchJson(`/api/products/${query}`);
            filters.innerHTML = [
                `<button class="catalog-filter${currentCategory === '' ? ' is-active' : ''}" type="button" data-category="">همه</button>`,
                ...payload.categories.map((category) => `
                    <button class="catalog-filter${currentCategory === category.id ? ' is-active' : ''}" type="button" data-category="${category.id}">
                        ${category.label}
                    </button>
                `)
            ].join('');
            filters.querySelectorAll('.catalog-filter').forEach((button) => {
                button.addEventListener('click', () => {
                    currentCategory = button.dataset.category || '';
                    showFilterBanner(currentCategory);
                    // Update URL without reload
                    const newUrl = currentCategory
                        ? `${window.location.pathname}?category=${encodeURIComponent(currentCategory)}`
                        : window.location.pathname;
                    window.history.replaceState({}, '', newUrl);
                    paint().catch(() => {
                        root.innerHTML = '<p class="catalog-empty">بارگذاری محصولات با خطا روبه‌رو شد.</p>';
                    });
                });
            });
            renderProducts(root, payload.products);
        };
        try {
            await paint();
        } catch (error) {
            root.innerHTML = '<p class="catalog-empty">بارگذاری محصولات با خطا روبه‌رو شد.</p>';
        }
    };

    Object.assign(window.Rahmani, {
        apiUrl,
        fetchJson,
        formatMoney,
        toPersianDigits,
        getCookie,
        calculateProductPrices,
        loadGoldRate,
        initChrome,
        initConsultationModal,
        initHomeCatalog,
        initProductsPage,
        initProductModal,
    });

    document.addEventListener('DOMContentLoaded', () => {
        initChrome();
        initConsultationModal();
        initProductModal();
        const page = document.body.dataset.page;
        if (page === 'home') initHomeCatalog();
        if (page === 'products') initProductsPage();
        if (page !== 'panel') loadGoldRate();
    });
})();
