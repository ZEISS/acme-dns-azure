import pytest
from mock import patch

import os
import filecmp
from acme_dns_azure.certbot_manager import CertbotManager
from acme_dns_azure.context import Context
import acme_dns_azure.config as config

path_to_current_file = os.path.realpath(__file__)
current_directory = os.path.split(path_to_current_file)[0]
resources_dir = current_directory + "/resources/" 

def certbot_manager_init(self, 
                working_dir
                 ) -> None:
        ctx = Context()
        ctx.config = config.load_from_file(resources_dir + 'config.yaml')
        ctx.credentials = '...'        
        ctx.config['azure_environment'] = 'AzurePublicCloud'             #TODO: Read from Azure client
        ctx.config['tenant_id'] = '56578228-5913-11ee-8c99-0242ac120002' #TODO: Read from Azure client
        
        from acme_dns_azure.os_manager import FileManager
        self.ctx = ctx
        self._config = ctx.config
        self._work_dir = working_dir
        self._os_manager = FileManager()
        self._create_certbot_init_files()
        self._create_certbot_init_directories()

@patch.object(CertbotManager, "__init__", certbot_manager_init)
def test_certbot_ini_is_created(working_dir, working_server, cleanup_certbot_init_files, cleanup_certbot_config_dir):
    CertbotManager(working_dir)
    assert(os.path.exists(working_dir + 'certbot.ini'))
    
@patch.object(CertbotManager, "__init__", certbot_manager_init)
def test_certbot_dns_azure_ini_is_created(working_dir, cleanup_certbot_init_files, cleanup_certbot_config_dir):
    CertbotManager(working_dir)
    assert(os.path.exists(working_dir + 'certbot_dns_azure.ini'))
    
@patch.object(CertbotManager, "__init__", certbot_manager_init)
def test_certbot_ini_is_created_correctly(working_dir, cleanup_certbot_init_files, cleanup_certbot_config_dir):
    CertbotManager(working_dir)
    expected_lines = [
        "key-type = rsa",
        "rsa-key-size = 2048",
        f"config-dir = {working_dir}config",
        f"work-dir = {working_dir}work",
        f"logs-dir = {working_dir}logs",
        "email = me@example.org",
        "preferred-challenges = dns",
        "authenticator = dns-azure",
        "agree-tos = true",
        "server = https://acme-staging-v02.api.letsencrypt.org/directory"
    ]
    with open(working_dir + 'certbot.ini') as data:
        for line in data:
            assert line.strip() in expected_lines
    
@patch.object(CertbotManager, "__init__", certbot_manager_init)
def test_certbot_dns_azure_ini_is_created_correctly(working_dir, cleanup_certbot_init_files, cleanup_certbot_config_dir):
    CertbotManager(working_dir)
    assert(filecmp.cmp(working_dir + 'certbot_dns_azure.ini', resources_dir + 'certbot_init/expected_certbot_dns_azure.ini'))
    
@patch.object(CertbotManager, "__init__", certbot_manager_init)
def test_certbot_directories_are_created(working_dir, cleanup_certbot_init_files, cleanup_certbot_config_dir):
    CertbotManager(working_dir)
    base_dirs = ['config', 'work', 'logs']
    for base_dir in base_dirs:
        assert(os.path.isdir(working_dir + base_dir))
    
@patch.object(CertbotManager, "__init__", certbot_manager_init)
def test_certbot_domain_file_structure_is_created_successfully(working_dir, cleanup_certbot_init_files, cleanup_certbot_config_dir):
    manager = CertbotManager(working_dir)
    domain = "test.my.domain"
    manager._create_certificate_files(domain, 
                                  certificate="cert",
                                  chain="chain",
                                  fullchain="fullchain",
                                  privkey="privkey")
    expected_files = [
        working_dir + 'config/archive/' + domain + '/' + 'cert1.pem',
        working_dir + 'config/archive/' + domain + '/' + 'chain1.pem',
        working_dir + 'config/archive/' + domain + '/' + 'fullchain1.pem',
        working_dir + 'config/archive/' + domain + '/' + 'privkey1.pem'
    ]
    for a in expected_files:
        assert(os.path.exists(a))
    result = open(working_dir + 'config/archive/' + domain + '/' + 'cert1.pem', 'rb').read()
    assert(result == b'cert\n')
    result = open(working_dir + 'config/archive/' + domain + '/' + 'chain1.pem', 'rb').read()
    assert(result == b'chain\n')
    result = open(working_dir + 'config/archive/' + domain + '/' + 'fullchain1.pem', 'rb').read()
    assert(result == b'fullchain\n')
    result = open(working_dir + 'config/archive/' + domain + '/' + 'privkey1.pem', 'rb').read()
    assert(result == b'privkey\n')
    
    expected_symlinks = [
        working_dir + 'config/live/' + domain + '/' + 'cert.pem',
        working_dir + 'config/live/' + domain + '/' + 'chain.pem',
        working_dir + 'config/live/' + domain + '/' + 'fullchain.pem',
        working_dir + 'config/live/' + domain + '/' + 'privkey.pem'
    ]
    for a in expected_symlinks:
        assert(os.path.islink(a))