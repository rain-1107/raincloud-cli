import os
import json
from ftplib import FTP, error_perm

def connect_to_server() -> FTP:
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    print(f"Syncing to remote at '{data['ftp_config']['ip']}'")
    ftp = FTP(data["ftp_config"]["ip"], timeout=5)
    ftp.login(user=data["ftp_config"]["user"], passwd=data["ftp_config"]["passwd"])
    return ftp

def create_folder_structure(name: str, struct: dict, ftp: FTP) -> None:
    try:
        ftp.mkd(name)
    except error_perm:
        pass
    ftp.cwd(name)
    for key in struct:
        create_server_folder_structure(key, struct[key], ftp)
    ftp.cwd("..")

def get_file_bytes(ftp: FTP, file: str) -> bytes:
    data = []

    def callback(b):
        data.append(b)
    
    ftp.retrbinary(f"RETR {file}", callback)
    b = data.pop(0)
    for block in data:
        if type(block) == bytes:
            b = b + block
    return b

