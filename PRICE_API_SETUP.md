# راه‌اندازی API قیمت بازار

این پروژه برای قیمت زنده‌ی بازار ایران از یک provider سمت سرور استفاده می‌کند. مقدارها در مرورگر hard-code نشده‌اند و API هر ۱۰ ثانیه cache می‌شود تا هم پاسخ سریع باشد و هم به provider فشار اضافه وارد نشود.

حالت پیش‌فرض پروژه `MARKET_PROVIDER=tgju_scrape` است و جدول عمومی صفحات TGJU را می‌خواند؛ بنابراین برای راه‌اندازی اولیه API Key لازم نیست. این حالت فقط HTML عمومی را با timeout و cache می‌خواند، anti-bot را دور نمی‌زند و با تغییر ساختار صفحه ممکن است نیاز به اصلاح داشته باشد. استفاده‌ی دائمی را فقط در صورتی انجام بده که با قوانین و اجازه‌ی TGJU سازگار باشد؛ خود TGJU برای مصرف پایدار، ویجت و وب‌سرویس رسمی ارائه می‌کند.

## تنظیمات

1. از سرویس وب TGJU یک endpoint و token معتبر دریافت کن.
2. متغیرهای فایل `.env.example` را در محیط اجرای Django تنظیم کن. خود Django این متغیرها را از محیط می‌خواند؛ بنابراین نیازی به قرار دادن token در `index.html` یا `script.js` نیست.
3. اگر provider مقدارها را به ریال می‌دهد، `MARKET_PROVIDER_UNIT=rial` را نگه دار. خروجی سایت در این حالت به تومان تبدیل می‌شود.
4. migrationها را اجرا کن و سرور را با همان محیط اجرا بالا بیاور.

## APIهای عمومی سایت

- `GET /api/market/` قیمت‌های طلای ۱۸ و ۲۴، دلار، یورو، نقره، درصد تغییر نسبت به snapshot قبلی، وضعیت stale و سه بازه‌ی نمودار را برمی‌گرداند.
- `GET /api/market/history/?period=hourly&limit=7` تاریخچه‌ی واقعی ذخیره‌شده را برای `hourly`، `daily` یا `monthly` برمی‌گرداند.

برای فعال‌کردن خواندن صفحه‌ی عمومی TGJU:

```text
MARKET_PROVIDER=tgju_scrape
TGJU_SCRAPE_URL=https://www.tgju.org/home
TGJU_SCRAPE_GOLD_URL=https://www.tgju.org/gold-chart
MARKET_PROVIDER_UNIT=rial
MARKET_DISPLAY_UNIT=toman
```

تا وقتی provider و token تنظیم نشده باشد، API به‌جای نمایش داده‌ی ساختگی با وضعیت `503` پاسخ می‌دهد. اگر provider موقتاً قطع شود، آخرین snapshot با `stale: true` نمایش داده می‌شود تا کاربر بداند قیمت زنده نیست.

## منابع provider

- [TGJU Web Services](https://english.tgju.org/api)
- [TGJU Market Data Widget](https://www.tgju.org/widget/get/market-data)

صفحه‌ی ویجت رسمی TGJU کد `<tgju type="market-data" ...>` و اسکریپت `https://api.tgju.org/v1/widget/v2` را ارائه می‌کند و برای استفاده‌ی پایدارتر از scraping مناسب‌تر است.

فرمت نهایی پاسخ provider ممکن است بر اساس پلن یا endpoint متفاوت باشد؛ adapter این پروژه envelopeهای رایج JSON و کلیدهای `price`، `value`، `last` و `p` را پشتیبانی می‌کند. اگر endpoint اختصاصی‌ات نام فیلد دیگری دارد، فقط parser در `prices/services.py` باید با همان schema تطبیق داده شود.
