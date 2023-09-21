import os
from acme_dns_azure.logger import LoggingHandler

class FileManager(LoggingHandler):
    def __init__(self) -> None:
        super(FileManager, self).__init__()
    
    def create_file(self, file_path: str, lines : [str]):
        with open(file_path, 'w', encoding="utf8") as file:
            file.writelines(s + '\n' for s in lines)
            file.close()
            
    def create_dir(self, dir_path: str, exist_ok: bool=False):
        os.makedirs(dir_path, exist_ok=exist_ok)
        self._log.info("Created dir")