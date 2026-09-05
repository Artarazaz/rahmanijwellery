document.addEventListener('DOMContentLoaded', () => {
    const { fetchJson } = window.Rahmani;
    const loginView = document.getElementById('panel-login');
    const deskView = document.getElementById('panel-desk');
    const loginForm = document.getElementById('login-form');
    const productForm = document.getElementById('product-form');
    const productList = document.getElementById('panel-product-list');
    const userLabel = document.getElementById('panel-user');
    const imagesInput = document.getElementById('product-images');
    const preview = document.getElementById('image-preview');
    let currentId = null;
    let keepImageIds = [];
    const statusNodes = () => document.querySelectorAll('.panel-status');
    const setStatus = (message, isError = false) => {
        statusNodes().forEach((node) => {
            node.textContent = message || '';
            node.classList.toggle('is-error', Boolean(isError && message));
        });
    };

    const showDesk = (username) => {
        loginView.hidden = true;
        deskView.hidden = false;
        userLabel.textContent = username;
    };

    const showLogin = () => {
        loginView.hidden = false;
        deskView.hidden = true;
        currentId = null;
        keepImageIds = [];
    };

    const resetForm = () => {
        productForm.reset();
        currentId = null;
        keepImageIds = [];
        preview.innerHTML = '';
        document.getElementById('product-published').checked = true;
        document.getElementById('form-title').textContent = 'افزودن محصول جدید';
        document.getElementById('submit-label').textContent = 'افزودن به ویترین';
    };

    const renderPreview = (images) => {
        preview.innerHTML = images.map((image) => `
            <figure class="panel-thumb" data-image-id="${image.id || ''}">
                <img src="${image.url}" alt="">
                ${image.id ? '<button type="button" class="panel-thumb-remove" aria-label="حذف عکس">×</button>' : ''}
            </figure>
        `).join('');
        preview.querySelectorAll('.panel-thumb-remove').forEach((button) => {
            button.addEventListener('click', () => {
                const figure = button.closest('.panel-thumb');
                const imageId = Number(figure.dataset.imageId);
                keepImageIds = keepImageIds.filter((id) => id !== imageId);
                figure.remove();
            });
        });
    };

    const fillForm = (product) => {
        currentId = product.id;
        keepImageIds = (product.images || []).map((image) => image.id);
        productForm.name.value = product.name;
        productForm.sku.value = product.sku || '';
        productForm.category.value = product.category;
        productForm.weight.value = product.weight;
        productForm.making_charge.value = product.making_charge;
        productForm.profit.value = product.profit;
        productForm.note.value = product.note || '';
        document.getElementById('product-published').checked = product.is_published;
        document.getElementById('product-featured').checked = product.is_featured;
        imagesInput.value = '';
        renderPreview(product.images || []);
        document.getElementById('form-title').textContent = `ویرایش ${product.name}`;
        document.getElementById('submit-label').textContent = 'ذخیره تغییرات';
    };

    const renderList = (products) => {
        if (!products.length) {
            productList.innerHTML = '<p class="catalog-empty">هنوز محصولی ثبت نشده است.</p>';
            return;
        }
        productList.innerHTML = products.map((product) => {
            const image = product.images?.[0]?.url || '';
            return `
                <article class="panel-row">
                    <div class="panel-row-media">${image ? `<img src="${image}" alt="${product.name}">` : ''}</div>
                    <div class="panel-row-copy">
                        <strong>${product.name}</strong>
                        <span>${product.category_label} · ${product.weight} گرم · اجرت ${Number(product.making_charge).toLocaleString('fa-IR')}</span>
                    </div>
                    <div class="panel-row-actions">
                        <button type="button" data-edit="${product.id}">ویرایش</button>
                        <button type="button" class="danger" data-delete="${product.id}">حذف</button>
                    </div>
                </article>
            `;
        }).join('');
        productList.querySelectorAll('[data-edit]').forEach((button) => {
            button.addEventListener('click', () => {
                const product = products.find((item) => String(item.id) === button.dataset.edit);
                if (product) {
                    fillForm(product);
                    productForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
        productList.querySelectorAll('[data-delete]').forEach((button) => {
            button.addEventListener('click', async () => {
                if (!window.confirm('این محصول از ویترین حذف شود؟')) return;
                try {
                    await fetchJson(`/api/studio/products/${button.dataset.delete}/`, { method: 'DELETE' });
                    setStatus('محصول حذف شد.');
                    if (String(currentId) === button.dataset.delete) resetForm();
                    await loadDesk();
                } catch (error) {
                    setStatus(error.message, true);
                }
            });
        });
    };

    const loadDesk = async () => {
        const payload = await fetchJson('/api/studio/products/');
        const categorySelect = productForm.category;
        if (categorySelect.options.length <= 1) {
            categorySelect.innerHTML = payload.categories.map((category) => `<option value="${category.id}">${category.label}</option>`).join('');
        }
        renderList(payload.products);
    };

    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        setStatus('');
        try {
            await fetchJson('/api/studio/session/');
            const payload = await fetchJson('/api/studio/login/', {
                method: 'POST',
                body: JSON.stringify({
                    username: loginForm.username.value.trim(),
                    password: loginForm.password.value,
                }),
            });
            showDesk(payload.username);
            await loadDesk();
        } catch (error) {
            setStatus(error.message, true);
        }
    });

    document.getElementById('logout-button')?.addEventListener('click', async () => {
        await fetchJson('/api/studio/logout/', { method: 'POST' });
        showLogin();
        loginForm.reset();
        setStatus('خارج شدید.');
    });

    document.getElementById('reset-form')?.addEventListener('click', resetForm);

    imagesInput?.addEventListener('change', () => {
        const files = Array.from(imagesInput.files || []);
        const extras = files.map((file) => ({ url: URL.createObjectURL(file) }));
        const current = keepImageIds.map((id) => {
            const img = preview.querySelector(`[data-image-id="${id}"] img`);
            return img ? { id, url: img.getAttribute('src') } : null;
        }).filter(Boolean);
        renderPreview([...current, ...extras]);
    });

    productForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        setStatus('');
        const data = new FormData(productForm);
        data.set('is_published', document.getElementById('product-published').checked ? 'true' : 'false');
        data.set('is_featured', document.getElementById('product-featured').checked ? 'true' : 'false');
        data.set('keep_image_ids', keepImageIds.join(','));
        Array.from(imagesInput.files || []).forEach((file) => data.append('images', file));
        try {
            const path = currentId ? `/api/studio/products/${currentId}/` : '/api/studio/products/create/';
            await fetchJson(path, { method: 'POST', body: data });
            setStatus(currentId ? 'تغییرات ذخیره شد.' : 'محصول به ویترین اضافه شد.');
            resetForm();
            await loadDesk();
        } catch (error) {
            setStatus(error.message, true);
        }
    });

    (async () => {
        try {
            const session = await fetchJson('/api/studio/session/');
            if (session.authenticated) {
                showDesk(session.username);
                await loadDesk();
            } else {
                showLogin();
            }
        } catch (error) {
            showLogin();
            setStatus(error.message, true);
        }
    })();
});
