import os
import pytest
import shutil

# from mock import patch

testing_dir = "/tmp/acme_local_test/"


@pytest.fixture(scope="function", autouse=True)
def working_dir():
    return testing_dir


@pytest.fixture(scope="function", autouse=False)
def tmp_priv_key_path(working_dir):
    return working_dir + "privkey.pem"


@pytest.fixture(scope="function", autouse=False)
def tmp_cert_path(working_dir):
    return working_dir + "cert.pem"


@pytest.fixture(scope="function", autouse=True)
def working_server():
    return "testserver"


@pytest.fixture(scope="function", autouse=False)
def cleanup_certbot_init_files(working_dir):
    yield
    os.remove(working_dir + "certbot.ini")
    os.remove(working_dir + "certbot_dns_azure.ini")


@pytest.fixture(scope="function", autouse=False)
def cleanup_certbot_config_dir(working_dir):
    yield
    shutil.rmtree(working_dir + "config")
    shutil.rmtree(working_dir + "work")
    shutil.rmtree(working_dir + "logs")


@pytest.fixture(scope="function", autouse=False)
def cleanup_tmp_privkey_and_cert(tmp_priv_key_path, tmp_cert_path):
    yield
    os.remove(tmp_priv_key_path)
    os.remove(tmp_cert_path)


@pytest.fixture(scope="session", autouse=True)
def manage_test_dir():
    os.mkdir(testing_dir)
    yield
    shutil.rmtree(testing_dir)
