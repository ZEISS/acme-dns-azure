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
from path_tree import DisplayPath
import time

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

    # Ensure packages were added to system PATH and are executable
    for root, dirs, files in os.walk(
        os.path.abspath("./.python_packages/lib/site-packages")
    ):
        if "bin" in dirs:
            path = os.path.abspath(os.path.join(root, "bin"))
            os.environ["PATH"] = path + ":" + os.environ.get("PATH")
            logging.info("Extended system PATH: %s", path)
        # if root.endswith("bin"):
        #     for file in files:
        #         path = os.path.join(root, file)
        #         mode = os.stat(path).st_mode
        #         if not bool(mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH):
        #             os.chmod(path, stat.S_IXOTH)
        #             logging.info("Modified file permissions: %s", path)

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
