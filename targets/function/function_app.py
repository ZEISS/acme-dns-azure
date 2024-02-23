import os
import logging
import datetime
from typing import List

import azure.functions as func

from acme_dns_azure import (
    AcmeDnsAzureClient,
    RotationResult,
)

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

    try:
        client = AcmeDnsAzureClient(
            config_env_var=os.getenv("ACME_DNS_CONFIG_ENV_VAR_NAME")
        )
        results: List[RotationResult] = client.issue_certificates()
        for result in results:
            logging.info(result.result)

    except Exception:
        logging.exception("Failed to rotate certificates")
