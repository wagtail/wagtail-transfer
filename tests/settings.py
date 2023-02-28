import os
from django.core.signals import setting_changed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/{{ docs_version }}/howto/deployment/checklist/


# Application definition
INSTALLED_APPS = [
    'tests',
    'wagtail_transfer',

    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail',

    'modelcluster',
    'taggit',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',

    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
]

ROOT_URLCONF = 'tests.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
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

WSGI_APPLICATION = 'tests.wsgi.application'


# Database
# https://docs.djangoproject.com/en/{{ docs_version }}/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',  # don't use the intentionally slow default password hasher
)

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'test-media')
MEDIA_URL = 'http://media.example.com/media/'

SECRET_KEY = 'not needed'

# Wagtail settings

WAGTAIL_SITE_NAME = "wagtail-transfer"
WAGTAILADMIN_BASE_URL = 'http://example.com'

WAGTAILTRANSFER_SOURCES = {
    'staging': {
        'BASE_URL': 'https://www.example.com/wagtail-transfer/',
        'SECRET_KEY': 'i-am-the-staging-example-secret-key',
    },
    'local': {
        # so that we can use the wagtail_transfer.auth.digest_for_source helper in API tests
        'BASE_URL': 'http://localhost/wagtail-transfer/',
        'SECRET_KEY': 'i-am-the-local-secret-key',
    }
}

WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS = [('wagtailimages.image', 'tagged_items', True), ('tests.advert', 'tagged_items', True)]

WAGTAILTRANSFER_SECRET_KEY = 'i-am-the-local-secret-key'

WAGTAILTRANSFER_UPDATE_RELATED_MODELS = ['wagtailimages.Image', 'tests.advert']

WAGTAILTRANSFER_LOOKUP_FIELDS = {
    'tests.category': ['name']
}

# some settings are modified in tests, in which case this caching interfers with the ability to test
# effectivley. Since settings are unlikely to change in the middle of usage in the real world, 
# it makes sense to clear these just inside our test settings
def clear_locator_cache(setting, value, **kwargs):
    from wagtail_transfer.locators import get_locator_for_model
    get_locator_for_model.cache_clear()

setting_changed.connect(clear_locator_cache)

# The default name for the Page -> Comment relation from Wagtail 2.15 onward. Setting this ensures that
# 2.13.x (from 2.13.5 onward) and 2.14.x (from 2.14.2 onward) adopt the 2.15 behaviour, allowing us to
# use the same test fixtures across all versions.
WAGTAIL_COMMENTS_RELATION_NAME = 'wagtail_admin_comments'
