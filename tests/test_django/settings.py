SECRET_KEY = 1

INSTALLED_APPS = [
    "tests.test_django.tests",  # to be able to create models in tests
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite3",
    }
}
