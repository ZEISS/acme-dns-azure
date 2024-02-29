try:
    import logging
    import datetime
    from typing import List

    import azure.functions as func

    from acme_dns_azure.data import (
        RotationResult,
        CertbotResult,
    )
    from acme_dns_azure.client import AcmeDnsAzureClient
except ImportError as ex:
    import logging

    logging.exception("Failed to import")
    raise ImportError from ex
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
