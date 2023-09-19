from acme_dns_azure.os_manager import FileManager

class CertbotManager():
    def __init__(self, work_dir : str = "./") -> None:
        self._work_dir = work_dir
        self._os_manager= FileManager()
        self._create_certbot_init_files()
    
    def _create_certbot_init_files(self):
        certbot_ini_file_path = self._work_dir + 'certbot.ini'
        self._os_manager.create_file(file_name=certbot_ini_file_path)
        certbot_ini_file_path = self._work_dir + 'certbot_dns_azure.ini'
        self._os_manager.create_file(file_name=certbot_ini_file_path)
    
    