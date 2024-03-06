import logging
import datetime
import sys
import os
import stat
from typing import List
import azure.functions as func
from acme_dns_azure.data import (
    RotationResult,
    CertbotResult,
)
from acme_dns_azure.client import AcmeDnsAzureClient

app = func.FunctionApp()


@app.function_name(name="acmeDnsAzure")
@app.schedule(
    schedule="%ScheduleAcmeDnsAzure%",
    arg_name="acmeDnsAzureTimer",
    run_on_startup=False,
)
def main(acmeDnsAzureTimer: func.TimerRequest, context: func.Context) -> None:
    utc_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if acmeDnsAzureTimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Python timer trigger function ran at %s", utc_timestamp)

    acme_dns_config_env_name = "ACME_DNS_CONFIG"
    certbot_relative_path = ".python_packages/lib/site-packages/bin/certbot"
    packages_relative_path = ".python_packages/lib/site-packages"

    try:
        python_path: str = os.path.abspath("/".join([str(sys.executable), "../python"]))
        certbot_path: str = "/".join(
            [str(context.function_directory), certbot_relative_path]
        )
        packages_path: str = "/".join(
            [str(context.function_directory), packages_relative_path]
        )

        assert os.path.isfile(certbot_path)
        assert os.path.isfile(python_path)
        assert acme_dns_config_env_name in os.environ

        st = os.stat(certbot_path)
        os.chmod(certbot_path, st.st_mode | stat.S_IEXEC)

        os.environ["CERTBOT_PATH"] = certbot_path
        os.environ["PYTHON_INTERPRETER_PATH"] = python_path
        os.environ["PYTHONPATH"] = packages_path

        logging.info("Set environment variable CERTBOT_PATH: %s", certbot_path)
        logging.info(
            "Set environment variable PYTHON_INTERPRETER_PATH: %s", python_path
        )
        logging.info("Set environment variable PYTHONPATH: %s", packages_path)
    except Exception as exc:
        logging.exception(
            "Failed to setup Azure function environment for running renewal."
        )
        raise Exception from exc

    try:
        client = AcmeDnsAzureClient(config_env_var=acme_dns_config_env_name)
        results: List[RotationResult] = client.issue_certificates()
        for rotation in results:
            if rotation.result == CertbotResult.FAILED:
                logging.exception("Failed to rotate certificate %s.", rotation)
            if rotation.result == CertbotResult.SKIPPED:
                logging.warning("Skipped to rotate certificate %s.", rotation)
            else:
                logging.info(rotation)

    except Exception:
        logging.exception("Failed to rotate certificates")
