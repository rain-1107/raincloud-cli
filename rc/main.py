import os
import sys
from time import time
import json
import shutil
from ftplib import FTP

HOME = os.path.expanduser("~")
CONFIG_FOLDER = HOME + "/.rc"

def create_config() -> None:
    os.mkdir(CONFIG_FOLDER)
    os.mkdir(os.path.join(CONFIG_FOLDER, "data"))
    with open(CONFIG_FOLDER + "/config.json", "w") as conf_file:
        json.dump({"ftp_config": {"ip": "", "user": "", "passwd": "", "port": 21}, "local_conf": {}}, conf_file, indent=2)

def get_folder_structure(path):
    dirs = []
    for (_, dirnames, _) in os.walk(os.path.expanduser(path)):
        dirs = dirnames
        break
    if dirs:
        struct = {}
        for d in dirs:
            struct[d] = get_folder_structure(path + "/" + d)
        return struct
    return {}

def create_folder_structure(name, struct, ftp):
    ftp.mkd(name)
    ftp.cwd(name)
    for key in struct:
        create_folder_structure(key, struct[key], ftp)
    ftp.cwd("..")

def get_filepaths(path, local = False):
    f = []
    for (dirpath, _, filenames) in os.walk(path):
        for file in filenames:
            name = os.path.join(dirpath, file)
            if local:
                name = name[len(path):]
            f.append(name)
    return f

def get_mtimes(path):
    files = get_filepaths(path)
    names = get_filepaths(path, True)
    data = {}
    for i, f in enumerate(files):
        data[names[i]] = os.path.getmtime(f)
    return data

def connect_to_server():
    data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
    print(f"Syncing to remote at '{data["ftp_config"]["ip"]}'")
    ftp = FTP(data["ftp_config"]["ip"])
    print("FTP: " + ftp.login(user=data["ftp_config"]["user"], passwd=data["ftp_config"]["passwd"])) 
    return ftp

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
    if sys.argv[1].lower() == "remove":
        names = sys.argv[2:]
        data: dict = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
        for n in names:
            if n in data["local_conf"]:
                data["local_conf"].pop(n)
        with open(CONFIG_FOLDER + "/config.json", "w") as fp:
            json.dump(data, fp, indent=2)
        return
    if sys.argv[1].lower() == "list":
        data = json.load(open(CONFIG_FOLDER + "/config.json", "r"))
        for name in data["local_conf"]:
            print(f"{name} - '{data["local_conf"][name]}'")
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
                # Upload all
                mtime_data = get_mtimes(data["local_conf"][dir]) 
                with open(os.path.join(CONFIG_FOLDER, f"{dir}.json"), "w") as mtime_file:
                    json.dump(mtime_data, mtime_file)
                folder = get_folder_structure(data["local_conf"][dir])
                create_folder_structure(dir, folder, ftp)
                with open(os.path.join(CONFIG_FOLDER, f"{dir}.json"), "rb") as mtime_file:
                    ftp.storbinary(f"STOR {dir}.json", mtime_file)
                ftp.cwd(dir)
                paths = get_filepaths(data["local_conf"][dir])
                names = get_filepaths(data["local_conf"][dir], local = True)
                for i, f in enumerate(paths):
                    with open(f, "rb") as fp:
                        ftp.storbinary(f"STOR {names[i]}", fp)
            else:

                ftp.cwd(dir)
                # Individual folder logic
                files = get_filepaths(data["local_conf"][dir])
                names = []
                for f in files:
                    names.append(f.split("/")[-1])
                for i, f in enumerate(files):
                    with open(f, "rb") as fp:
                        ftp.storbinary(f"STOR {names[i]}", fp)
                # -----------------------
            ftp.cwd("..")
        print("FTP: " + ftp.quit())
        return
    print(f"Unrecognized command '{sys.argv[1]}'")


if __name__ == '__main__':
    main()
