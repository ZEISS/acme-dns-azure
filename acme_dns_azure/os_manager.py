import os
import zipfile
import shutil
from typing import List
from acme_dns_azure.log import setup_custom_logger

logger = setup_custom_logger(__name__)


class FileManager:
    def create_file(self, file_path: str, lines: List[str], chmod: int = None):
        with open(file_path, "w", encoding="utf8") as file:
            file.writelines(s + "\n" for s in lines)
            file.close()
        if chmod is not None:
            os.chmod(file_path, chmod)

    def create_dir(self, dir_path: str, exist_ok: bool = False):
        os.makedirs(dir_path, exist_ok=exist_ok)
        logger.debug("Created directory '%s'", dir_path)

    def create_symlink(self, src: str, dest: str):
        os.symlink(src, dest)

    def delete_file(self, file_path: str):
        os.remove(file_path)

    # max size of a secret is 25kb, size of the dir with 1 account is 3,4kb. On the long term we could not zip meta.json per account to save space
    def zip_archive(self, src_dir_path: str, dest_file_path: str):
        with zipfile.ZipFile(dest_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(src_dir_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    archive_path = os.path.relpath(file_path, src_dir_path)
                    zipf.write(file_path, archive_path)
        return dest_file_path

    def unzip_archive(self, src_zip_path: str, dest_dir_path: str):
        shutil.unpack_archive(filename=src_zip_path, extract_dir=dest_dir_path)
