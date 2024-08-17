import os
import sys
import json
import shutil
from ftplib import FTP

HOME = os.path.expanduser("~")
CONFIG_FOLDER = HOME + "/.rc"


def create_config() -> None:
    os.mkdir(CONFIG_FOLDER)
    with open(CONFIG_FOLDER + "/config.json", "w") as conf_file:
        json.dump({"ftp_config": {"ip": "", "user": "", "passwd": "", "port": 21}, "local_conf": {}}, conf_file, indent=2)

def get_filepaths(path):
    f = []
    for (dirpath, _, filenames) in os.walk(path):
        for file in filenames:
            f.append(dirpath + "/" + file)
        break
    return f

def get_filenames(path):
    f = []
    for (_, _, filenames) in os.walk(path):
        for file in filenames:
            f.append(file)
        break
    return f


def main() -> None:
    if not os.path.isdir(CONFIG_FOLDER):
        print("No config file found. Creating config folder")
        create_config()
    if len(sys.argv) < 2:
        print("No arguments found")
        return
    if sys.argv[1].lower() == "remote":
        print("Please note that all data is kept in plain text")
        ip = input("Enter ftp server ip: ")
        user = input("Enter ftp server user: ")
        passwd = input("Enter ftp server password: ")
        data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
        data["ftp_config"] = {"ip": ip, "user": user, "passwd": passwd, "port": 21}
        with open(CONFIG_FOLDER + "/config.json", "w") as fp:
            json.dump(data, fp, indent=2)
        return
    if sys.argv[1].lower() == "add":
        folders = sys.argv[2:]
        names = []
        for f in folders.copy():
            if os.path.isdir(f):
                names.append(input(f"Enter ID/Name for folder '{f}': "))
            else:
                print(f"Folder not found '{f}'")
                folders.remove(f)
        data = json.load(open(CONFIG_FOLDER + "/config.json", "r")) 
        for i, f in enumerate(folders):
            data["local_conf"][names[i]] = f
        with open(CONFIG_FOLDER + "/config.json", "w") as fp:
            json.dump(data, fp, indent=2)
        return
    if sys.argv[1].lower() == "reset":
        shutil.rmtree(CONFIG_FOLDER)
        create_config()
        print("Config reset")
        return
    if sys.argv[1].lower() == "sync":
        data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
        print(f"Syncing to remote at '{data["ftp_config"]["ip"]}'")
        ftp = FTP(data["ftp_config"]["ip"])
        print("FTP: " + ftp.login(user=data["ftp_config"]["user"], passwd=data["ftp_config"]["passwd"]))
        items = ftp.nlst()
        if "raincloud" not in items:
            ftp.mkd("raincloud")
        ftp.cwd("raincloud")
        items = ftp.nlst()
        for dir in data["local_conf"]:
            if dir not in items:
                ftp.mkd(dir)
            ftp.cwd(dir)
            files = get_filepaths(data["local_conf"][dir])
            names = get_filenames(data["local_conf"][dir])
            for i, f in enumerate(files):
                fp = open(f, "rb")
                ftp.storbinary(f"STOR {names[i]}", fp)
            ftp.cwd("..")
        print("FTP: " + ftp.quit())
        return
    print(f"Unrecognized command 'sys.argv[1]'")


if __name__ == '__main__':
    main()
