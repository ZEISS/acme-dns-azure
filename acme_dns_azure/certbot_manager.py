from acme_dns_azure.os_manager import FileManager

class CertbotConfiguration():
    def __init__(self) -> None:
        pass

class CertbotManager():
    def __init__(self, 
                 server : str,
                 dns_azure_sp_client_id: str,
                 user_managed_identity_id : str,
                 dns_azure_sp_client_secret: str,
                 dns_azure_zones: [str],
                 dns_azure_tenant_id: str = '82913d90-8716-4025-a8e8-4f8dfa42b719',
                 work_dir : str = "./", 
                 key_type : str = 'rsa',
                 key_size : int = 2048
                 ) -> None:
        self._dns_azure_sp_client_id = dns_azure_sp_client_id
        self._user_managed_identity_id = user_managed_identity_id
        self._dns_azure_sp_client_secret = dns_azure_sp_client_secret
        self._dns_azure_zones = dns_azure_zones
        self._server = server
        self._dns_azure_tenant_id = dns_azure_tenant_id
        self._key_type = key_type
        self._key_size = key_size
        self._work_dir = work_dir
        self._os_manager = FileManager()
        self._create_certbot_init_files()
    
    def _create_certbot_init_files(self):
        certbot_ini_file_path = self._work_dir + 'certbot.ini'
        certbot_ini_content = self._create_certbot_ini()
        self._os_manager.create_file(file_path=certbot_ini_file_path, lines=certbot_ini_content)
        
        certbot_dns_azure_ini_file_path = self._work_dir + 'certbot_dns_azure.ini'
        certbot_dns_azure_ini_content = self._create_certbot_dns_azure_ini()
        self._os_manager.create_file(file_path=certbot_dns_azure_ini_file_path, lines=certbot_dns_azure_ini_content)
    
    def _create_certbot_ini(self) -> [str]:
        lines = []
        lines.append('preferred-challenges = dns')
        lines.append('key-type = %s' %self._key_type)
        lines.append('key-size = %d' %self._key_size)
        lines.append('authenticator = dns-azure')
        lines.append('agree-tos = true')
        lines.append('server = %s' %self._server)
        return lines
    
    def _create_certbot_dns_azure_ini(self) -> [str]:
        lines = []
        lines.append('dns_azure_sp_client_id = %s' %self._dns_azure_sp_client_id)
        lines.append('user_managed_identity = %s' %self._user_managed_identity_id)
        lines.append('dns_azure_sp_client_secret = %s' %self._dns_azure_sp_client_secret)
        lines.append('dns_azure_tenant_id = %s'  %self._dns_azure_tenant_id)
        lines.append('dns_azure_environment = AzurePublicCloud')
        for idx, x in enumerate(self._dns_azure_zones):
            lines.append('dns_azure_zone{}  = {}'.format(self._dns_azure_zones[idx], x))
        return lines
    
    