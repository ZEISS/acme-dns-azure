import azure.functions as func

import sys
import os
import logging
import datetime
import tempfile
import subprocess

app = func.FunctionApp()

@app.function_name(name="acmeDnsAzure")
@app.schedule(schedule="%ScheduleAcmeDnsAzure%",
              arg_name="acmeDnsAzureTimer",
              run_on_startup=True) 

def main(acmeDnsAzureTimer: func.TimerRequest, context: func.Context) -> None:
   utc_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

   if acmeDnsAzureTimer.past_due:
      logging.info('The timer is past due!')

   logging.info('Python timer trigger function ran at %s', utc_timestamp)

   tempFilePath = tempfile.gettempdir()
   fp = tempfile.NamedTemporaryFile()
   fp.write(b'Hello world!')
   filesDirListInTemp = os.listdir(tempFilePath)
   logging.info('Temp files are %s', filesDirListInTemp)
   logging.info(context.function_directory)

   python_path = str(sys.executable)
   certbot_path = os.path.abspath("/".join([python_path, "../certbot"]))

   logging.info('Python path: %s', python_path)

   proc = subprocess.Popen([python_path, certbot_path,"--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   out, err = proc.communicate()

   logging.info('certbot subprocess result code: %s', proc.returncode)
   logging.info('certbot subprocess stdout:\n%s', out)
   if proc.returncode:
      logging.info('certbot subprocess stdout:\n%s', out)
      logging.info('certbot subprocess stderr:\n%s', err)