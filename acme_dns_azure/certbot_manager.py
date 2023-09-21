import subprocess
from acme_dns_azure.os_manager import FileManager
from acme_dns_azure.logger import LoggingHandler

class CertbotManager(LoggingHandler):
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
        self._os_manager = FileManager()
        self._create_certbot_init_files()
        self._create_certbot_init_directories()
    
    def _create_certbot_init_files(self):
        self._log.info("Creating init files...")
        certbot_ini_file_path = self._work_dir + 'certbot.ini'
        certbot_ini_content = self._create_certbot_ini()
        self._os_manager.create_file(file_path=certbot_ini_file_path, lines=certbot_ini_content)
        
        certbot_dns_azure_ini_file_path = self._work_dir + 'certbot_dns_azure.ini'
        certbot_dns_azure_ini_content = self._create_certbot_dns_azure_ini()
        self._os_manager.create_file(file_path=certbot_dns_azure_ini_file_path, lines=certbot_dns_azure_ini_content)

    def _create_certbot_init_directories(self):
        self._log.info("Creating init directories...")
        directories = [
            "config",
            "config/live",
            "config/accounts",
            "config/archive",
            "config/renewal"
        ]
        
        for dir_name in directories:
            self._os_manager.create_dir(dir_path=self._work_dir + dir_name, exist_ok=False)
    
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
        lines.append('dns_azure_environment = "AzurePublicCloud"')
        for idx, dns_zone in enumerate(self._dns_azure_zones):
            lines.append('dns_azure_zone{}  = {}'.format(idx+1, dns_zone))
        return lines
    
    def renew_certificate(self, domain):
        try:
            result : subprocess.CompletedProcess = subprocess.run(
                args=self._generate_certonly_command(domain),
                capture_output=True,
                check=True)
            result.check_returncode()
        except subprocess.CalledProcessError as error:
            self._log.error(error.stderr)
            return False
        return True
    
    def register_domain_file(self, domain):
        domain_file_path=self._work_dir + 'config/renewal/' + domain
        self._os_manager.create_file(file_path=domain_file_path, lines=self._create_domain_conf(domain))
        self._os_manager.create_dir(self._work_dir + 'config/live/' + domain)
        files = [
            "cert.pem",
            "privkey.pem",
            "chain.pem",
            "fullchain.pem"
        ]
        for cert in files:
            self._os_manager.create_symlink(
                src=self._work_dir + 'config/archive/' + domain + '/' + cert,
                dest=self._work_dir + 'config/live/' + domain + '/' + cert
            )
                
    def _create_domain_conf(self, domain) -> [str]:
        lines = []
        lines.append('archive_dir = %s' %(self._work_dir + 'config/archive/' + domain))
        files = [
            "cert.pem",
            "privkey.pem",
            "chain.pem",
            "fullchain.pem"
        ]
        for cert in files:
            lines.append('archive_dir = %s' %(self._work_dir + 'config/live/' + domain + '/' + cert))

        lines.append('[renewalparams]')
        return lines
    
    def _generate_certonly_command(self, domain) -> [str]:
        command = [
            "certbot", 
            "certonly",
            "-c",
            self._work_dir + "certbot.ini",
            "-m",
            "brian.rimek@zeiss.com",
            "-d",
            domain,
            "no-reuse-key",
            "--new-key",
            "--dns-azure-credentials",
            self._work_dir + "certbot-dns-azure.ini",
            "-v"
        ]
        #TODO email from config
        return command