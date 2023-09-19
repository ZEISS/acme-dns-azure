import pytest
import os

from acme_dns_azure.certbot_manager import CertbotManager

def test_certbot_ini_is_created(working_dir, cleanup_certbot_init_files):
    CertbotManager(work_dir=working_dir)
    assert(os.path.exists(working_dir + 'certbot.ini'))

def test_certbot_dns_azure_ini_is_created(working_dir, cleanup_certbot_init_files):
    CertbotManager(work_dir=working_dir)
    assert(os.path.exists(working_dir + 'certbot_dns_azure.ini'))
