import os

from acme_dns_azure.log import setup_custom_logger

logger = setup_custom_logger(__name__)

class FileManager():
    def __init__(self) -> None:
        pass
    
    def create_file(self, file_path: str, lines : [str]):
        with open(file_path, 'w', encoding="utf8") as file:
            file.writelines(s + '\n' for s in lines)
            file.close()
            
    def create_dir(self, dir_path: str, exist_ok: bool=False):
        os.makedirs(dir_path, exist_ok=exist_ok)
        logger.debug("Created directory '%s'" % dir_path)