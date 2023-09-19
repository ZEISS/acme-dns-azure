import os

class FileManager():
    def __init__(self) -> None:
        pass
    
    def create_file(self, file_name: str):
        with open(file_name, 'w', encoding="utf8") as file:
            file.close()
