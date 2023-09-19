import os
import pytest
# from mock import patch

@pytest.fixture(scope="function", autouse=True)
def working_dir():
    return './'

@pytest.fixture(scope="function", autouse=True)
def working_server():
    return 'testserver'

@pytest.fixture(scope="function", autouse=False)
def cleanup_certbot_init_files(working_dir):
    yield
    os.remove(working_dir + 'certbot.ini')
    os.remove(working_dir + 'certbot_dns_azure.ini')