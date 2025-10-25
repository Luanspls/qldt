import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# def get_database_config():
#     """Lấy cấu hình database an toàn"""
#     supabase_url = os.environ.get('SUPABASE_URL')
    
#     if not supabase_url:
#         # Fallback to SQLite
#         return {
#             'default': {
#                 'ENGINE': 'django.db.backends.sqlite3',
#                 'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#             }
#         }
    
#     try:
#         # Parse Supabase URL
#         from urllib.parse import urlparse
#         result = urlparse(supabase_url)
        
#         return {
#             'default': {
#                 'ENGINE': 'django.db.backends.postgresql',
#                 'NAME': 'postgres',
#                 'USER': 'postgres',
#                 'PASSWORD': result.password,
#                 'HOST': result.hostname,
#                 'PORT': result.port or 5432,
#                 'OPTIONS': {
#                     'connect_timeout': 30,
#                     'sslmode': 'require',
#                 },
#             }
#         }
#     except Exception as e:
#         print(f"Database config error: {e}, using SQLite fallback")
#         return {
#             'default': {
#                 'ENGINE': 'django.db.backends.sqlite3',
#                 'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#             }
#         }

# DATABASES = get_database_config()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key')

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'ignore_chrome_devtools': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: not (
                'GET /.well-known/appspecific/com.chrome.devtools.json HTTP/1.1' in record.getMessage()
            ),
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'], 
            'level': 'DEBUG',  # INFO, WARNING, ERROR
            'propagate': True,
        },
    },
}

ALLOWED_HOSTS = ['*']  # Cho phép tất cả host, trong production nên hạn chế

# Application definition

INSTALLED_APPS = [
    # 'django.contrib.admin',
    # 'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'products',
    'django_extensions',
    'crispy_bootstrap5',
    'django_htmx',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'QldtWeb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                # 'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'QldtWeb.wsgi.application'

# Database
# Ở đây chúng ta dùng Supabase, nên không cần cấu hình database của Django
# Nhưng Django vẫn cần database cho các model mặc định (như user, session)
# Có thể dùng SQLite cho free tier, nhưng lưu ý Railway có ephemeral storage (mất dữ liệu khi redeploy)
# Hoặc dùng Supabase cho cả database của Django (khuyến nghị)

DATABASES = {
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': BASE_DIR / 'db.sqlite3',
    # },
    'default': {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get('DB_NAME', 'postgres'),
        "USER": os.environ.get('DB_USER', 'postgres'),
        "PASSWORD": os.environ.get('DB_PASSWORD'),
        # "HOST": "localhost",
        "HOST": os.environ.get('DB_HOST'),
        "PORT": os.environ.get('DB_PORT', '5432'),
        'SCHEMA': 'public',
        'OPTIONS': {
            'connect_timeout': 30,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        },
    }
}

# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://your-frontend-domain.vercel.app",
]

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')