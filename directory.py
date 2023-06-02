import os
import shutil
import sys
import time
from typing import List

from config import Config

#----------------------------------------------
def make_directory(path : str):
    os.makedirs(path, exist_ok=True)

def remove_directory(directory : str):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    else:
        print(f"Directory not found: {directory}")
        
#----------------------------------------------
image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
def get_all_image_paths(directory : str, deep: bool) -> List[str]:
    return get_all_file_paths(directory, image_extensions, deep)

def get_all_file_paths(directory : str, extensions : str, deep : bool) -> List[str] :
    file_paths = []
    if deep:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(tuple(extensions)):
                    file_paths.append(os.path.abspath(os.path.join(root, file)))
    else:
        for file in os.listdir(directory):
            if file.endswith(tuple(extensions)):
                path = os.path.abspath(os.path.join(directory, file))
                if os.path.isfile(path):
                    file_paths.append(os.path.abspath(os.path.join(directory, file)))

    return file_paths

unnecessary_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', 'bin']
def remove_unnecessary_assets(directory : str, deep: bool):
    for file_path in get_all_file_paths(directory, unnecessary_extensions, deep):
        os.remove(file_path)


def convert_file_path(target_file: str, dest_path: str, ext: str) -> str:
    target_file_name = os.path.splitext(os.path.basename(target_file))[0]
    output_path = os.path.join(dest_path, f"{target_file_name}{ext}")
    return output_path

class Directory :
     def __init__(self, texture_settings : List[Config.TextureSetting]):

        if getattr(sys, "frozen", False):
            bundle_dir = sys._MEIPASS
        else:
            bundle_dir = os.path.dirname(os.path.abspath(__file__))

        # Create 'workspace' folder in the current execution path
        self.workspace_root_path = "{}/workspace".format(bundle_dir)
        make_directory(self.workspace_root_path)

        # Create a folder in 'workspace' with the current timestamp
        self.workspace = "{}/{}".format(self.workspace_root_path, time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time())))
        make_directory(self.workspace)

        # Convert the base file to texture-separated gltf and create a base folder to save it
        self.base_model = "{}/{}".format(self.workspace, 'base')
        make_directory(self.base_model)

        self.texture : List[str] = []
        for texture_setting in texture_settings:
            texture_path = "{}/{}".format(self.workspace, texture_setting.max_size)
            make_directory(texture_path)
            self.texture.append(texture_path)
