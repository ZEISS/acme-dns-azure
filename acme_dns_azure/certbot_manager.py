import subprocess
import base64
import traceback
from typing import List
from acme_dns_azure.context import Context
from acme_dns_azure.log import setup_custom_logger
from acme_dns_azure.os_manager import FileManager
from acme_dns_azure.data import (
    RotationResult,
    DomainReference,
    RotationCertificate,
    CertbotResult,
)

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
        try:
            zipped_account_dir_data = base64.b64decode(
                self.ctx.keyvault.get_secret(
                    self._keyvault_acme_account_secret_name
                ).value
            )
            with open(self._work_dir + "accounts.zip", "wb") as f:
                f.write(zipped_account_dir_data)
            self._os_manager.unzip_archive(
                src_zip_path=self._work_dir + "accounts.zip",
                dest_dir_path=self._work_dir + "config/accounts",
            )
            self._os_manager.delete_file(self._work_dir + "accounts.zip")
            logger.info("Successfully restored acme accounts from keyvault")
        except Exception:
            logger.exception(
                "Unknown error in restoring ACME account info from keyvault."
            )

    def _create_certbot_ini(self) -> List[str]:
        lines = str(self._config["certbot.ini"]).splitlines()
        lines = [s.strip() for s in lines]
        lines.append("config-dir = %s" % self._work_dir + "config")
        lines.append("work-dir = %s" % self._work_dir + "work")
        lines.append("logs-dir = %s" % self._work_dir + "logs")
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

    def _create_certbot_dns_azure_ini(self) -> List[str]:
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
                name = domain["name"]
                if name.startswith("*."):
                    logger.info("Handling wildard request %s.", name)
                    name = name.replace("*.", "")
                idx += 1
                lines.append(
                    "dns_azure_zone%i = %s:%s"
                    % (idx, name, domain["dns_zone_resource_id"])
                )
        return lines

    def renew_certificates(self) -> List[RotationResult]:
        certs: List[RotationCertificate] = self._get_certificate_from_config()
        results: List[RotationResult] = []
        for cert_def in certs:
            config_domains = []
            for domain_ref in cert_def.domains:
                config_domains.append(domain_ref.domain_name)
            try:
                if self.ctx.keyvault.certificate_exists(cert_def.key_vault_cert_name):
                    logger.info("Renewing cert %s", cert_def.key_vault_cert_name)
                    base64_encoded_pfx = self.ctx.keyvault.get_certificate(
                        name=cert_def.key_vault_cert_name
                    ).value
                    (
                        private_key,
                        cert,
                        chain,
                        fullchain,
                        certificate_domains,
                    ) = self.ctx.keyvault.extract_pfx_data(base64_encoded_pfx)

                    if (set(certificate_domains) != set(config_domains)) and (
                        self._config["update_cert_domains"] is False
                    ):
                        logger.warning(
                            "Skipping renewal of cert %s due to multi-domain conflict in cert and config.\n Cert: %s\n Config: %s",
                            cert_def.key_vault_cert_name,
                            certificate_domains,
                            config_domains,
                        )
                        results.append(RotationResult(cert_def, CertbotResult.SKIPPED))
                        continue

                    self._create_certificate_files(
                        certbot_cert_name=cert_def.certbot_cert_name,
                        certificate=cert.decode("utf-8"),
                        chain=chain.decode("utf-8"),
                        fullchain=fullchain.decode("utf-8"),
                        privkey=private_key.decode("utf-8"),
                        renew_before_expiry=cert_def.renew_before_expiry,
                    )
                else:
                    logger.info(
                        "Creating new certificate %s", cert_def.key_vault_cert_name
                    )

                certbot_result: CertbotResult = self._create_or_renew_certificate(
                    cert_name=cert_def.certbot_cert_name, domains=config_domains
                )
                if (
                    certbot_result == CertbotResult.RENEWED
                    or certbot_result == CertbotResult.CREATED
                ):
                    logger.info(
                        "Successfully renewed certificate %s",
                        cert_def.certbot_cert_name,
                    )
                    new_pfx_data = self.ctx.keyvault.generate_pfx(
                        private_key_path=self._work_dir
                        + "config/live/"
                        + cert_def.certbot_cert_name
                        + "/privkey.pem",
                        certificate_path=self._work_dir
                        + "config/live/"
                        + cert_def.certbot_cert_name
                        + "/cert.pem",
                        chain_file_path=self._work_dir
                        + "config/live/"
                        + cert_def.certbot_cert_name
                        + "/chain.pem",
                    )
                    self.ctx.keyvault.import_certificate(
                        cert_def.key_vault_cert_name, new_pfx_data
                    )
                elif certbot_result == CertbotResult.FAILED:
                    logger.exception(
                        "Failed to renew certificate %s", cert_def.certbot_cert_name
                    )
                if certbot_result == CertbotResult.STILL_VALID:
                    logger.info(
                        "Skipped renewal %s - still valid.", cert_def.certbot_cert_name
                    )

                results.append(
                    RotationResult(certificate=cert_def, result=certbot_result)
                )
            except Exception:
                logger.exception("Unknown error in renewal of certficate")
                results.append(
                    RotationResult(
                        certificate=cert_def,
                        result=CertbotResult.FAILED,
                        message=traceback.format_exc(),
                    )
                )
        try:
            zip_archive_path = self._os_manager.zip_archive(
                src_dir_path=self._work_dir + "config/accounts/",
                dest_file_path=self._work_dir + "accounts.zip",
            )
            logger.info("Uploading ACME account information...")
            with open(zip_archive_path, "rb") as data:
                encoded_archive = base64.b64encode(data.read()).decode()
                self.ctx.keyvault.set_secret(
                    self._keyvault_acme_account_secret_name, encoded_archive
                )
        except Exception:
            logger.exception(
                "Unknown error in uploading ACME account information to keyvault"
            )
        return results

    def _get_certificate_from_config(self) -> List[RotationCertificate]:
        certificates = []
        for o in self._config["certificates"]:
            cert_name = o["name"]
            domains = []
            renew_before_expiry = None
            if renew_before_expiry in o:
                renew_before_expiry = int(o["renew_before_expiry"])
            for domain in o["domains"]:
                dns_zone_resource_id = domain["dns_zone_resource_id"]
                name = domain["name"]
                domains.append(
                    DomainReference(
                        dns_zone_resource_id=dns_zone_resource_id, domain_name=name
                    )
                )
            certificates.append(
                RotationCertificate(
                    key_vault_cert_name=cert_name,
                    certbot_cert_name=cert_name,
                    domains=domains,
                    renew_before_expiry=renew_before_expiry,
                )
            )
        return certificates

    def _create_or_renew_certificate(
        self, cert_name: str, domains: List[str]
    ) -> CertbotResult:
        try:
            result: subprocess.CompletedProcess = subprocess.run(
                args=self._generate_certonly_command(cert_name, domains),
                capture_output=True,
                encoding="utf-8",
                check=True,
            )
            result.check_returncode()
        except subprocess.CalledProcessError as error:
            for error in error.stderr.splitlines():
                logger.error(error)
            return CertbotResult.FAILED
        for info in result.stdout.splitlines():
            logger.info(info)
        for info in result.stdout.splitlines():
            if "Certificate not yet due for renewal" in info:
                logger.info("Cert %s skipped. Not yet due for renewal.", cert_name)
                return CertbotResult.STILL_VALID
            if "Requesting a certificate for" in info:
                logger.info("Creating new cert %s.", cert_name)
                return CertbotResult.CREATED
            if "Renewing an existing certificate" in info:
                logger.info("Renewing %s.", cert_name)
        return CertbotResult.RENEWED

    def _create_certificate_files(
        self,
        certbot_cert_name: str,
        certificate: str,
        chain: str,
        fullchain: str,
        privkey: str,
        renew_before_expiry: int = None,
    ):
        domain_file_path = (
            self._work_dir + "config/renewal/" + certbot_cert_name + ".conf"
        )
        self._os_manager.create_dir(self._work_dir + "config/live/" + certbot_cert_name)
        self._os_manager.create_dir(
            self._work_dir + "config/archive/" + certbot_cert_name
        )
        self._os_manager.create_file(
            file_path=domain_file_path,
            lines=self._create_domain_conf(certbot_cert_name, renew_before_expiry),
        )
        self._os_manager.create_file(
            self._work_dir + "config/archive/" + certbot_cert_name + "/cert1.pem",
            [certificate],
        )
        self._os_manager.create_file(
            self._work_dir + "config/archive/" + certbot_cert_name + "/privkey1.pem",
            [privkey],
        )
        self._os_manager.create_file(
            self._work_dir + "config/archive/" + certbot_cert_name + "/chain1.pem",
            [chain],
        )
        self._os_manager.create_file(
            self._work_dir + "config/archive/" + certbot_cert_name + "/fullchain1.pem",
            [fullchain],
        )
        files = ["cert", "privkey", "chain", "fullchain"]
        for cert in files:
            self._os_manager.create_symlink(
                src="../../archive/" + certbot_cert_name + "/" + cert + "1.pem",
                dest=self._work_dir
                + "config/live/"
                + certbot_cert_name
                + "/"
                + cert
                + ".pem",
            )

    def _create_domain_conf(
        self, certbot_cert_name, renew_before_expiry: int = None
    ) -> List[str]:
        lines = []
        lines.append(
            "archive_dir = %s"
            % (self._work_dir + "config/archive/" + certbot_cert_name)
        )
        lines.append(
            "cert = %s"
            % (self._work_dir + "config/live/" + certbot_cert_name + "/cert.pem")
        )
        lines.append(
            "privkey = %s"
            % (self._work_dir + "config/live/" + certbot_cert_name + "/privkey.pem")
        )
        lines.append(
            "chain = %s"
            % (self._work_dir + "config/live/" + certbot_cert_name + "/chain.pem")
        )
        lines.append(
            "fullchain = %s"
            % (self._work_dir + "config/live/" + certbot_cert_name + "/fullchain.pem")
        )

        if renew_before_expiry:
            lines.append(f"renew_before_expiry = {renew_before_expiry} days")

        lines.append("[renewalparams]")

        return lines

    def _generate_certonly_command(
        self, cert_name: str, domains: List[str]
    ) -> List[str]:
        command = [
            "certbot",
            "certonly",
            "--cert-name",
            cert_name,
            "-c",
            self._work_dir + "certbot.ini",
            "--dns-azure-credentials",
            self._work_dir + "certbot_dns_azure.ini",
            "--non-interactive",
            "-v",
        ]
        for domain in domains:
            command.append("-d")
            command.append(domain)

        return command
