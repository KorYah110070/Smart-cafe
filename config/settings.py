"""
Django settings for Smart Cafe Reservation System.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-p2wqr1j2jj)r1u)(7l!rwe&+gx2j4vnf4feex!7=$r620vdh-i",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # โปรเจค Smart Cafe Reservation System
    "accounts",
    "tables",
    "reservations",
    "menus",
    "orders",
    "promotions",
    "ai_assistant",
    "dashboard",
    # Google Login (django-allauth) - ตามคำแนะนำอาจารย์ที่ปรึกษา
    # ตอนนี้เป็นแค่ "โครง" รอใส่ GOOGLE_OAUTH_CLIENT_ID/SECRET จริงจาก Google Cloud Console
    # ของบัญชีร้าน/มหาลัยเอง (ดูหมายเหตุด้านล่าง) ปุ่ม "เข้าสู่ระบบด้วย Google" จะซ่อนอัตโนมัติ
    # จนกว่าจะตั้งค่าจริง
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# ค่าเริ่มต้นใช้ SQLite เพื่อให้รันทดสอบได้ทันทีโดยไม่ต้องติดตั้ง PostgreSQL ก่อน
# ตอนจะใช้งานจริงตามสไลด์ (PostgreSQL) ให้ตั้งค่า environment variable USE_POSTGRES=True
# พร้อมค่า POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_HOST / POSTGRES_PORT

if os.environ.get("USE_POSTGRES") == "True":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "smart_cafe"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "th"
TIME_ZONE = "Asia/Bangkok"
USE_I18N = True
USE_TZ = True


# Static & media files
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Auth redirects
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "tables:floor_plan"
LOGOUT_REDIRECT_URL = "accounts:login"

# ตั้งค่ากฎการจองตามเอกสาร Business Rules ของโปรเจค
RESERVATION_MAX_EDIT_COUNT = 2          # แก้ไขการจองได้ไม่เกินกี่ครั้ง
RESERVATION_ARRIVAL_DEADLINE_HOUR = 20  # ต้องมาร้านก่อน 2 ทุ่มครึ่ง (20:30)
RESERVATION_ARRIVAL_DEADLINE_MINUTE = 30

# ---------------------------------------------------------------------------
# Google Login (django-allauth) - ตามคำแนะนำอาจารย์ที่ปรึกษา
# ---------------------------------------------------------------------------
# นี่คือ "โครง" ที่พร้อมใช้งานแล้ว แต่ยังไม่ใส่ค่าจริง เพราะต้องสร้าง OAuth Client ID/Secret
# จาก Google Cloud Console (https://console.cloud.google.com/) ด้วยบัญชีของร้าน/มหาลัยเอง
# (Claude สร้างให้ไม่ได้เพราะเป็นบัญชีภายนอกของผู้ใช้)
#
# ขั้นตอนตอนพร้อมใช้งานจริง:
#   1. ไปที่ Google Cloud Console > สร้างโปรเจกต์ > APIs & Services > Credentials
#   2. สร้าง "OAuth client ID" ประเภท Web application
#   3. ใส่ Authorized redirect URI เป็น: <โดเมนจริง>/accounts/social/google/login/callback/
#      (ตอน dev ในเครื่องใช้ http://127.0.0.1:8000/accounts/social/google/login/callback/)
#   4. เอา Client ID/Secret ที่ได้มาตั้งเป็น environment variable ก่อนรันเซิร์ฟเวอร์:
#      GOOGLE_OAUTH_CLIENT_ID=... และ GOOGLE_OAUTH_CLIENT_SECRET=...
#   5. ปุ่ม "เข้าสู่ระบบด้วย Google" ที่หน้า Login จะปรากฏขึ้นเองทันทีที่ตั้งค่าทั้งสองนี้ไว้
#      (ไม่ต้องแก้โค้ดเพิ่ม) - บัญชีที่สมัครผ่าน Google จะได้ role='customer' เป็นค่าเริ่มต้น
#      เหมือนสมัครสมาชิกปกติ
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_LOGIN_ENABLED = bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "secret": GOOGLE_OAUTH_CLIENT_SECRET,
            "key": "",
        },
        "SCOPE": ["profile", "email"],
    }
}

# ยังไม่มีระบบส่งอีเมลจริง จึงปิดการยืนยันอีเมลไว้ก่อน (ไม่งั้นสมัครผ่าน Google ไม่ได้เพราะรอยืนยันอีเมลตลอด)
ACCOUNT_EMAIL_VERIFICATION = "none"
# สมัครบัญชีใหม่อัตโนมัติจากข้อมูล Google เลย ไม่ต้องมีหน้ากรอกข้อมูลเพิ่ม
SOCIALACCOUNT_AUTO_SIGNUP = True
# กดปุ่มแล้วพาไปหน้า Google ทันที ไม่ต้องผ่านหน้ายืนยันกลางของ allauth ก่อน
SOCIALACCOUNT_LOGIN_ON_GET = True
