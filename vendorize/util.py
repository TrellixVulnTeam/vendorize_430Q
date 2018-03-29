import contextlib
import os
from urllib.parse import urlparse


@contextlib.contextmanager
def chdir(path: str):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield path
    finally:
        os.chdir(cwd)


def host_not_vendorized(location: str, allowed_hosts: list) -> bool:
    url = urlparse(location)
    host = url.netloc
    return bool(host and host not in allowed_hosts)
