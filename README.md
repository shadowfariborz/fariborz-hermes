# Fariborz + Hermes Railway Template

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new/deploy?repo=shadowfariborz/fariborz-hermes)

ربات تلگرام هوشمند فریبرز + Hermes Agent در یک پروژه واحد

## قابلیت‌ها

### 🤖 هوش مصنوعی (Hermes)
- چت هوشمند با مدل‌های OpenAI/Anthropic/OpenRouter
- پشتیبانی از عکس و صدا
- حافظه مکالمه

### 🎮 فریبرز (Public Bot)
- 💬 چت هوشمند (گروه + پی‌وی)
- 🎤 پیام صوتی → متن
- 🔊 متن → صدا
- 🎨 ساخت عکس
- 🎵 شناسایی آهنگ (ACRCloud)
- 🦖 بازی دایناسور با رتبه‌بندی
- 📢 ارسال همگانی به گروه‌ها
- 👨‍💻 پنل مدیریت ادمین
- 📅 تاریخ شمسی و ساعت
- 👋 پیام خوش‌آمدگویی سفارشی
- 🎁 سیستم دول/پروکسی

## متغیرهای محیطی

### 🔑 الزامی
| متغیر | توضیح |
|--------|--------|
| `OPENAI_API_KEY` | کلید OpenAI |
| `TELEGRAM_BOT_TOKEN` | توکن بات شخصی (Hermes) |

### 🎮 فریبرز (اختیاری)
| متغیر | توضیح |
|--------|--------|
| `FARIBORZ_BOT_TOKEN` | توکن بات عمومی فریبرز |
| `ADMIN_ID` | آیدی عددی ادمین اصلی |
| `ADMIN2_ID` | آیدی عددی ادمین دوم |
| `BOT_PORT` | پورت فریبرز (پیش‌فرض: 8001) |

### 🎵 ACRCloud (اختیاری - شناسایی آهنگ)
| متغیر | توضیح |
|--------|--------|
| `ACR_HOST` | هاست ACRCloud |
| `ACR_ACCESS_KEY` | کلید دسترسی |
| `ACR_SECRET_KEY` | کلید مخفی |

## راهنمای دپلوی

1. دکمه بالا بزن
2. متغیرها رو پر کن
3. Deploy بزن

### بات شخصی (Hermes)
آدرس پابلیک + `/setup` بزن

### بات عمومی (فریبرز)
آدرس پابلیک سرویس + `:8001/setup` بزن

## ساختار

```
fariborz-hermes/
├── bot.py              # فریبرز بات
├── Dockerfile          # کانتینر
├── scripts/
│   └── entrypoint.sh   # اجرای هرمس + فریبرز
├── skills/             # مهارت‌های هرمس
├── plugins/            # پلاگین‌های هرمس
└── README.md
```
