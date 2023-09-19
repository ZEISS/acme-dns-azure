import os

class FileManager():
    def __init__(self) -> None:
        pass
    
    def create_file(self, file_path: str, lines : [str]):
        with open(file_path, 'w', encoding="utf8") as file:
            file.writelines(s + '\n' for s in lines)
            file.close()
