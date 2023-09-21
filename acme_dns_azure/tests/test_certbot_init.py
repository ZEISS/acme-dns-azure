import pytest
from mock import patch

import os
import filecmp
from acme_dns_azure.certbot_manager import CertbotManager

path_to_current_file = os.path.realpath(__file__)
current_directory = os.path.split(path_to_current_file)[0]
resources_dir = current_directory + "/resources/" 

def certbot_manager_init(self, 
                 server : str = 'testserver',
                 dns_azure_sp_client_id: str = '456-456',
                 user_managed_identity_id : str = '123-123',
                 dns_azure_sp_client_secret: str = 'my-secret',
                 dns_azure_zones: [str] = ['firstzone', 'secondzone'],
                 dns_azure_tenant_id: str = '789-789',
                 work_dir : str = "./", 
                 key_type : str = 'rsa',
                 key_size : int = 2048
                 ) -> None:
        super(CertbotManager, self).__init__()
        self._dns_azure_sp_client_id = dns_azure_sp_client_id
        self._user_managed_identity_id = user_managed_identity_id
        self._dns_azure_sp_client_secret = dns_azure_sp_client_secret
        self._dns_azure_zones = dns_azure_zones
        self._server = server
        self._dns_azure_tenant_id = dns_azure_tenant_id
        self._key_type = key_type
        self._key_size = key_size
        self._work_dir = work_dir
        from acme_dns_azure.os_manager import FileManager
        self._os_manager = FileManager()
        self._create_certbot_init_files()

@patch.object(CertbotManager, "__init__", certbot_manager_init)
def test_certbot_ini_is_created(working_dir, working_server, cleanup_certbot_init_files):
    CertbotManager()
    assert(os.path.exists(working_dir + 'certbot.ini'))
    
@patch.object(CertbotManager, "__init__", certbot_manager_init)
def test_certbot_dns_azure_ini_is_created(working_dir, cleanup_certbot_init_files):
    CertbotManager()
    assert(os.path.exists(working_dir + 'certbot_dns_azure.ini'))
    
@patch.object(CertbotManager, "__init__", certbot_manager_init)
def test_certbot_ini_is_created_correctly(working_dir, cleanup_certbot_init_files):
    CertbotManager()
    assert(filecmp.cmp(working_dir + 'certbot.ini', resources_dir + 'certbot_init/expected_certbot.ini'))
    
@patch.object(CertbotManager, "__init__", certbot_manager_init)
def test_certbot_dns_azure_ini_is_created_correctly(working_dir, cleanup_certbot_init_files):
    CertbotManager()
    assert(filecmp.cmp(working_dir + 'certbot_dns_azure.ini', resources_dir + 'certbot_init/expected_certbot_dns_azure.ini'))