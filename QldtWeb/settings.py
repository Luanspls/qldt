import os
import sys
import dj_database_url
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv

# load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

# DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
DEBUG = True

RAILWAY_DOMAIN = os.environ.get('RAILWAY_STATIC_URL', '').replace('https://', '') or 'qldt.up.railway.app'

ALLOWED_HOSTS = ['*']
# ALLOWED_HOSTS = [
#     RAILWAY_DOMAIN,
#     'localhost',
#     '127.0.0.1',
#     '0.0.0.0',
#     '.railway.app',  # Cho phép tất cả subdomain railway
# ]

# CSRF_TRUSTED_ORIGINS = [
#     f'https://{RAILWAY_DOMAIN}',
#     f'https://*.{RAILWAY_DOMAIN}',
#     'https://*.railway.app',
# ]

# # 

# # CORS methods và headers
# CORS_ALLOW_METHODS = [
#     'DELETE',
#     'GET', 
#     'OPTIONS',
#     'PATCH',
#     'POST',
#     'PUT',
# ]

# CORS_ALLOW_HEADERS = [
#     'accept',
#     'accept-encoding',
#     'authorization',
#     'content-type',
#     'dnt',
#     'origin',
#     'user-agent',
#     'x-csrftoken',
#     'x-requested-with',
# ]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'products',
    # 'crispy_bootstrap5',
    # 'django_htmx',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # 'products.middleware.DatabaseHealthCheckMiddleware',  # THÊM DÒNG NÀY
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'QldtWeb.urls'

WSGI_APPLICATION = 'QldtWeb.wsgi.application'

# Template settings
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'), 
            ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Lấy DATABASE_URL từ environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    db_config = dj_database_url.parse(DATABASE_URL)
    
    # Thêm connection options chi tiết
    db_config.update({
        'CONN_MAX_AGE': 60,  # Giữ connection 60 giây
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 30,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        }
    })
    
    DATABASES = {
        'default': db_config
    }
else:
    # Fallback configuration
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# print(f"✅ Database HOST: {DATABASES['default'].get('HOST', 'N/A')}")
# print(f"✅ Database CONN_MAX_AGE: {DATABASES['default'].get('CONN_MAX_AGE', 'N/A')}")

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'postgres',
#         'USER': 'postgres',
#         'PASSWORD': 'c10.54321@',  # THAY THẾ
#         'HOST': 'aws-0-ap-southeast-1.pooler.supabase.co',  # Dùng connection pooling
#         'PORT': '5432',
#         'CONN_MAX_AGE': 60,
#         'OPTIONS': {
#             'sslmode': 'require',
#             'connect_timeout': 30,
#             'keepalives': 1,
#             'keepalives_idle': 30,
#             'keepalives_interval': 10,
#             'keepalives_count': 5,
#         }
#     }
# }

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
# SESSION_CACHE_ALIAS = 'default'

# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#         'LOCATION': 'unique-snowflake',
#     }
# }

# Security
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# CORS settings cho phép frontend truy cập
# CORS_ALLOWED_ORIGINS = [
#     "https://qldtweb-production.vercel.app",
#     "http://localhost:3000",
#     "http://127.0.0.1:3000",
# ]
# Hoặc cho phép tất cả origins (chỉ cho development)
CORS_ALLOW_ALL_ORIGINS = True

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'products/static'),
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# # Login/Logout URLs
# LOGIN_URL = '/admin/login/'
# LOGIN_REDIRECT_URL = '/admin/'
# LOGOUT_REDIRECT_URL = '/admin/'

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY')

if DEBUG:
    LOGGING = {
        'version': 1,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'stream': sys.stdout,
            }
        },
        'root': {
            'handlers': ['console'],
            'level': 'DEBUG'
        }
    }

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}