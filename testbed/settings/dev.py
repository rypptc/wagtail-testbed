from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-o0#-+kd=12*ek$lkg07ml^nht6e#-g#vma(wltkozf2)685cgd"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}

try:
    from .local import *
except ImportError:
    pass
