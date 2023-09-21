import subprocess
from acme_dns_azure.context import Context
from acme_dns_azure.log import setup_custom_logger
from acme_dns_azure.os_manager import FileManager

logger = setup_custom_logger(__name__)

class CertbotManager():
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

        self._config = ctx.config
        self._work_dir = ctx.work_dir + '/'
        self._os_manager = FileManager()

        self._create_certbot_init_files()
        self._create_certbot_init_directories()
    
    def _create_certbot_init_files(self):
        logger.info("Creating init files...")
        certbot_ini_file_path = self._work_dir + 'certbot.ini'
        certbot_ini_content = self._create_certbot_ini()
        self._os_manager.create_file(file_path=certbot_ini_file_path, lines=certbot_ini_content)
        
        certbot_dns_azure_ini_file_path = self._work_dir + 'certbot_dns_azure.ini'
        certbot_dns_azure_ini_content = self._create_certbot_dns_azure_ini()
        self._os_manager.create_file(file_path=certbot_dns_azure_ini_file_path, lines=certbot_dns_azure_ini_content)

    def _create_certbot_init_directories(self):
        logger.info("Creating init directories...")
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
        lines = str(self._config['certbot.ini']).splitlines()
        lines.append('email = %s' % self._config['email'])
        lines.append('preferred-challenges = dns')
        lines.append('authenticator = dns-azure')
        lines.append('agree-tos = true')
        lines.append('server = https://%s/directory' % self._config['server'])

        if self._config['eab']['enabled'] == True:
            lines.append('eab-kid = %s' % self.ctx.keyvault.get_secret(self._config['eab']['kid_secret_name']).value)
            lines.append('eab-hmac-key = %s' % self.ctx.keyvault.get_secret(self._config['eab']['hmac_key_secret_name']).value)

        return lines

    def _create_certbot_dns_azure_ini(self) -> [str]:
        lines = []
        if 'sp_client_id' in self._config:
            logger.info("Using Azure service principal '%s'" % self._config['sp_client_id'])
            lines.append('dns_azure_sp_client_id = %s' % self._config['sp_client_id'])
            lines.append('dns_azure_sp_client_secret = %s' % self._config['sp_client_secret'])
        else:
            logger.info("Using Azure managed identity '%s'" % self._config['managed_identity_id'])
            lines.append('dns_azure_msi_client_id = %s' % self._config['managed_identity_id'])
        lines.append('dns_azure_tenant_id = %s'  % self._config['tenant_id'])
        lines.append('dns_azure_environment = %s' % self._config['azure_environment'])

        idx = 0
        for certificate in self._config['certificates']:
            for domain in certificate['domains']:
                idx += 1
                #TODO: follow CNAME
                lines.append('dns_azure_zone%i = %s:%s' % (idx, domain['name'], domain['dns_zone_resource_id']))
        return lines
    
    def renew_certificate(self, domain):
        try:
            result : subprocess.CompletedProcess = subprocess.run(
                args=self._generate_certonly_command(domain),
                capture_output=True,
                check=True)
            result.check_returncode()
        except subprocess.CalledProcessError as error:
            logger.error(error.stderr)
            return False
        return True
    
    def register_domain_files(self, domain: str, certificate: str, chain : str, fullchain : str, privkey : str):
        domain_file_path=self._work_dir + 'config/renewal/' + domain
        self._os_manager.create_dir(self._work_dir + 'config/live/' + domain)
        self._os_manager.create_file(file_path=domain_file_path, lines=self._create_domain_conf(domain))
        self._os_manager.create_file(self._work_dir + 'config/archive/' + domain + '/cert.pem', [certificate])
        self._os_manager.create_file(self._work_dir + 'config/archive/' + domain + '/privkey.pem', [privkey])
        self._os_manager.create_file(self._work_dir + 'config/archive/' + domain + '/chain.pem', [chain])
        self._os_manager.create_file(self._work_dir + 'config/archive/' + domain + '/fullchain.pem', [fullchain])
        files = [
            "cert.pem",
            "privkey.pem",
            "chain.pem",
            "fullchain.pem"
        ]
        for cert in files:
            self._os_manager.create_symlink(
                src='../../archive/' + domain + '/' + cert,
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
            self._config['email'],
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
        
