import subprocess
import base64
from acme_dns_azure.context import Context
from acme_dns_azure.log import setup_custom_logger
from acme_dns_azure.os_manager import FileManager

logger = setup_custom_logger(__name__)


class CertbotManager:
    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self._config = ctx.config
        self._work_dir = ctx.work_dir + "/"
        self._keyvault_acme_account_secret_name = ctx.config[
            "keyvault_account_secret_name"
        ]
        self._os_manager = FileManager()

        self._create_certbot_init_files()
        self._create_certbot_init_directories()
        if self.ctx.keyvault.secret_exists(self._keyvault_acme_account_secret_name):
            self._restore_acme_account_from_keyvault()

    def _create_certbot_init_files(self):
        logger.info("Creating init files...")
        certbot_ini_file_path = self._work_dir + "certbot.ini"
        certbot_ini_content = self._create_certbot_ini()
        self._os_manager.create_file(
            file_path=certbot_ini_file_path, lines=certbot_ini_content
        )

        certbot_dns_azure_ini_file_path = self._work_dir + "certbot_dns_azure.ini"
        certbot_dns_azure_ini_content = self._create_certbot_dns_azure_ini()
        self._os_manager.create_file(
            file_path=certbot_dns_azure_ini_file_path,
            lines=certbot_dns_azure_ini_content,
            chmod=0o600,
        )

    def _create_certbot_init_directories(self):
        logger.info("Creating init directories...")
        directories = [
            "config",
            "work",
            "logs",
            "config/live",
            "config/accounts",
            "config/archive",
            "config/renewal",
        ]

        for dir_name in directories:
            self._os_manager.create_dir(
                dir_path=self._work_dir + dir_name, exist_ok=False
            )

    def _restore_acme_account_from_keyvault(self):
        zipped_account_dir_data = base64.b64decode(
            self.ctx.keyvault.get_secret(self._keyvault_acme_account_secret_name).value
        )
        with open(self._work_dir + "accounts.zip", "wb") as f:
            f.write(zipped_account_dir_data)
        self._os_manager.unzip_archive(
            src_zip_path=self._work_dir + "accounts.zip",
            dest_dir_path=self._work_dir + "config/accounts",
        )
        self._os_manager.delete_file(self._work_dir + "accounts.zip")
        logger.info("Successfully restored acme accounts from keyvault")

    def _create_certbot_ini(self) -> [str]:
        lines = str(self._config["certbot.ini"]).splitlines()
        lines.append("config-dir = %s" % self._work_dir + "config")
        lines.append("work-dir = %s" % self._work_dir + "work")
        lines.append("logs-dir = %s" % self._work_dir + "logs")
        lines.append("email = %s" % self._config["email"])
        lines.append("preferred-challenges = dns")
        lines.append("authenticator = dns-azure")
        lines.append("agree-tos = true")
        lines.append("server = %s" % self._config["server"])

        if self._config["eab"]["enabled"] is True:
            lines.append(
                "eab-kid = %s"
                % self.ctx.keyvault.get_secret(
                    self._config["eab"]["kid_secret_name"]
                ).value
            )
            lines.append(
                "eab-hmac-key = %s"
                % self.ctx.keyvault.get_secret(
                    self._config["eab"]["hmac_key_secret_name"]
                ).value
            )

        return lines

    def _create_certbot_dns_azure_ini(self) -> [str]:
        lines = []
        if "sp_client_id" in self._config:
            logger.info(
                "Using Azure service principal '%s'", self._config["sp_client_id"]
            )
            lines.append("dns_azure_sp_client_id = %s" % self._config["sp_client_id"])
            lines.append(
                "dns_azure_sp_client_secret = %s" % self._config["sp_client_secret"]
            )
        else:
            logger.info(
                "Using Azure managed identity '%s'", self._config["managed_identity_id"]
            )
            lines.append(
                "dns_azure_msi_client_id = %s" % self._config["managed_identity_id"]
            )
        lines.append("dns_azure_tenant_id = %s" % self._config["tenant_id"])
        lines.append("dns_azure_environment = %s" % self._config["azure_environment"])

        idx = 0
        for certificate in self._config["certificates"]:
            for domain in certificate["domains"]:
                idx += 1
                lines.append(
                    "dns_azure_zone%i = %s:%s"
                    % (idx, domain["name"], domain["dns_zone_resource_id"])
                )
        return lines

    def renew_certificates(self):
        cert_names = self._get_certificate_names_from_config()
        for cert_name in cert_names:
            logger.info("Renewing cert %s", cert_name)
            base64_encoded_pfx = self.ctx.keyvault.get_certificate(name=cert_name).value
            (
                private_key,
                cert,
                chain,
                fullchain,
                domain,
            ) = self.ctx.keyvault.extract_pfx_data(base64_encoded_pfx)
            # TODO currently using domain from certificate itself. Need to refer to domain from config (and validate if matches with actual domain(s) form cert?). Should we loop for list of domain for this cert?
            self._create_certificate_files(
                domain=domain,
                certificate=cert.decode("utf-8"),
                chain=chain.decode("utf-8"),
                fullchain=fullchain.decode("utf-8"),
                privkey=private_key.decode("utf-8"),
            )

            if self._renew_certificate(domain):
                logger.info("Successfully renewed certificate for doamin %s", domain)
                new_pfx_data = self.ctx.keyvault.generate_pfx(
                    private_key_path=self._work_dir
                    + "config/live/"
                    + domain
                    + "/privkey.pem",
                    certificate_path=self._work_dir
                    + "config/live/"
                    + domain
                    + "/cert.pem",
                    chain_file_path=self._work_dir
                    + "config/live/"
                    + domain
                    + "/chain.pem",
                )
                self.ctx.keyvault.import_certificate(cert_name, new_pfx_data)

            elif not self._renew_certificate(domain):
                logger.error("Failed to renew certificate for doamin %s", domain)

        zip_archive_path = self._os_manager.zip_archive(
            src_dir_path=self._work_dir + "config/accounts/",
            dest_file_path=self._work_dir + "accounts.zip",
        )
        with open(zip_archive_path, "rb") as data:
            encoded_archive = base64.b64encode(data.read()).decode()
            self.ctx.keyvault.set_secret(
                self._keyvault_acme_account_secret_name, encoded_archive
            )

    def _get_certificate_names_from_config(self):
        return [o["name"] for o in self.ctx.config["certificates"]]

    def _renew_certificate(self, domain):
        try:
            result: subprocess.CompletedProcess = subprocess.run(
                args=self._generate_certonly_command(domain),
                capture_output=True,
                encoding="utf-8",
                check=True,
            )
            result.check_returncode()
        except subprocess.CalledProcessError as error:
            for error in error.stderr.splitlines():
                logger.error(error)
            return False
        # TODO if Cert is still valid is this success? Should we enable to pass the "--break-my-certs" param?
        for info in result.stdout.splitlines():
            logger.info(info)
        return True

    def _create_certificate_files(
        self, domain: str, certificate: str, chain: str, fullchain: str, privkey: str
    ):
        domain_file_path = self._work_dir + "config/renewal/" + domain + ".conf"
        self._os_manager.create_dir(self._work_dir + "config/live/" + domain)
        self._os_manager.create_dir(self._work_dir + "config/archive/" + domain)
        self._os_manager.create_file(
            file_path=domain_file_path, lines=self._create_domain_conf(domain)
        )
        self._os_manager.create_file(
            self._work_dir + "config/archive/" + domain + "/cert1.pem", [certificate]
        )
        self._os_manager.create_file(
            self._work_dir + "config/archive/" + domain + "/privkey1.pem", [privkey]
        )
        self._os_manager.create_file(
            self._work_dir + "config/archive/" + domain + "/chain1.pem", [chain]
        )
        self._os_manager.create_file(
            self._work_dir + "config/archive/" + domain + "/fullchain1.pem", [fullchain]
        )
        files = ["cert", "privkey", "chain", "fullchain"]
        for cert in files:
            self._os_manager.create_symlink(
                src="../../archive/" + domain + "/" + cert + "1.pem",
                dest=self._work_dir + "config/live/" + domain + "/" + cert + ".pem",
            )

    def _create_domain_conf(self, domain) -> [str]:
        lines = []
        lines.append("archive_dir = %s" % (self._work_dir + "config/archive/" + domain))
        lines.append(
            "cert = %s" % (self._work_dir + "config/live/" + domain + "/cert.pem")
        )
        lines.append(
            "privkey = %s" % (self._work_dir + "config/live/" + domain + "/privkey.pem")
        )
        lines.append(
            "chain = %s" % (self._work_dir + "config/live/" + domain + "/chain.pem")
        )
        lines.append(
            "fullchain = %s"
            % (self._work_dir + "config/live/" + domain + "/fullchain.pem")
        )
        lines.append("[renewalparams]")
        return lines

    def _generate_certonly_command(self, domain) -> [str]:
        command = [
            "certbot",
            "certonly",
            "-c",
            self._work_dir + "certbot.ini",
            "-m",
            self._config["email"],
            "-d",
            domain,
            "--no-reuse-key",
            "--new-key",
            "--dns-azure-credentials",
            self._work_dir + "certbot_dns_azure.ini",
            "--non-interactive",
            "-v",
        ]
        return command
