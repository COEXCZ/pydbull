try:
    import django
except ImportError as e:
    raise ImportError("Can't use `pydbull.django` module without Django installed in your environment.") from e

from .adapter import *
