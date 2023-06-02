import os
import shutil
import subprocess
import sys
import time
import json
import getopt

import concurrent.futures

from pathlib import Path
from shutil import copy
from typing import List

from config import Config, parse_config
from directory import Directory, remove_directory, get_all_file_paths, convert_file_path, get_all_image_paths, remove_unnecessary_assets

#----------------------------------------------

def run(base_model_input_path : str, final_output_path : str, config_file : str, update_mode : bool):
    start_time = time.time()

    if not os.path.exists(final_output_path):    
        print('\nOutput path does not exist. Please enter the correct path.\n')
        sys.exit()

#----------------------------------------------
    # Initialize

    # Read config JSON
    with open(config_file, 'r') as file:
        config = parse_config(json.load(file))

    # Check target base models
    target_file_paths = get_all_file_paths(base_model_input_path, ['glb', 'gltf'], True)
    if not target_file_paths:
        print("At least 1 model file(glb/gltf) is required.")
        sys.exit(2)

#----------------------------------------------
    # Check if the file already exists in the output folder. In update mode 
    if update_mode:
        target_file_paths = get_not_exist_file_paths(config, target_file_paths, final_output_path)
        if len(target_file_paths) == 0:
            print("All modeling already exists in the output path. Clear --update to run nonetheless")
            sys.exit(2)

    print("\n\n-----------------------\n")
    for file_path in target_file_paths:
        print("{}".format(file_path))
    print("\n-----------------------\n\n")

#----------------------------------------------
    # Create paths
    dir = Directory(config.texture_settings)

#----------------------------------------------
    # Convert base file to texture-separated gltf with base folder path
    copy_models(config, dir, target_file_paths)

#----------------------------------------------
    # Optimize Texture
    optimize_textures(config, dir)
    
#----------------------------------------------
    # Optimize Mesh
    optimize_models(config, dir)
    
#--------------------------------------------
    # Remove unnecessary assets
    remove_unnecessary_assets(dir.workspace, False)
    remove_directory(dir.base_model)

#--------------------------------------------
    # Move output path

    for file_path in os.listdir(dir.workspace):
        path = Path(file_path)
        if path.suffix and not (path.suffix in config.output_exts):
            continue
           
        source_file_path = os.path.join(dir.workspace, file_path)
        destination_file_path = os.path.join(final_output_path, file_path)
        if os.path.exists(destination_file_path):
            if os.path.isdir(destination_file_path):
                shutil.rmtree(destination_file_path)
            elif os.path.isfile(destination_file_path):
                os.remove(destination_file_path)

        shutil.move(source_file_path, destination_file_path)

    # shutil.rmtree(workspace_path)

#--------------------------------------------
    # Print total time
    end_time = time.time()
    execution_time = end_time - start_time
    print("total execution time: {:.2f}s".format(execution_time))

#--------------------------------------------

def get_not_exist_file_paths(config, target_base_model_file_paths, final_output_path):

    suffixs = []
    for model_setting in config.model_settings:
        suffixs.append(model_setting.suffix)

    target_paths = []
    for file_path in target_base_model_file_paths:
        file_name = os.path.splitext(os.path.basename(file_path))[0]

        is_not_exist_file = False
        for ext in config.output_exts:
            for suffix in suffixs:
                output_path = "{}/{}{}{}".format(final_output_path, file_name, suffix, ext)
                if not os.path.exists(output_path):
                    is_not_exist_file = True
                    break
        if is_not_exist_file:
            target_paths.append(file_path)
            
    return target_paths
 
#--------------------------------------------
def contains_substring(string_array, target_string):
    return any(string in target_string for string in string_array)

#--------------------------------------------
def copy_models(config: Config, dir: Directory, target_file_paths: List[str]):
     with concurrent.futures.ThreadPoolExecutor() as executor:
        tasks = [(config, file_path, dir.base_model) for file_path in target_file_paths]
        futures = [executor.submit(copy_and_convert_gltf, *task) for task in tasks]
        concurrent.futures.wait(futures)

def copy_and_convert_gltf(config: Config, source: str, dest: str):
    gltf_path = convert_file_path(source, dest, ".gltf")
    subprocess.run(config.model_settings[0].gltf_separate.format(source, gltf_path), shell=True)

#--------------------------------------------
def optimize_textures(config : Config, dir : Directory):
    index = 0
    for texture_setting in config.texture_settings:
        texture_path = dir.texture[index]
        texture_file_paths = get_all_image_paths(dir.base_model, False)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Texture Copy
            copy_tasks = [(file_path, texture_path) for file_path in texture_file_paths]
            copy_futures = [executor.submit(texture_copy, *task) for task in copy_tasks]
            concurrent.futures.wait(copy_futures)
            
            # Texture Resize
            resize_tasks = [(texture_setting, file_path, texture_path) for file_path in texture_file_paths]
            resize_futures = [executor.submit(texture_resize, *task) for task in resize_tasks]
            concurrent.futures.wait(resize_futures)
            
            # Texture Convert KTX2
            convert_tasks = [(texture_setting, texture_path, file_path) for file_path in get_all_file_paths(texture_path, [".png"], False)]
            convert_futures = [executor.submit(to_ktx, *task) for task in convert_tasks]
            concurrent.futures.wait(convert_futures)
        index += 1
      
#--------------------------------------------
command_copy_to_dest = "cp {} {}"
def texture_copy(file_path : str, texture_path : str):
    copy_path = convert_file_path(file_path, texture_path, ".png")
    subprocess.run(command_copy_to_dest.format(file_path, copy_path), shell=True)

#--------------------------------------------
def texture_resize(texture_setting : Config.TextureSetting, file_path : str, texture_path : str):
    copy_path = convert_file_path(file_path, texture_path, ".png")
    subprocess.run(texture_setting.resize.format(copy_path), shell=True)
    subprocess.run(texture_setting.resize_scale.format(copy_path), shell=True)

#--------------------------------------------
def to_ktx(texture_setting : Config.TextureSetting, texture_path : str, file_path : str):
    ktx_path = convert_file_path(file_path, texture_path, ".ktx2")
    if texture_setting.keywords and contains_substring(texture_setting.keywords, file_path): # LightMap
        if texture_setting.default_format == "uastc":
            subprocess.run(texture_setting.to_etc1s.format(ktx_path, file_path), shell=True)
        else:
            subprocess.run(texture_setting.to_uastc.format(ktx_path, file_path), shell=True)
    else: 
        if texture_setting.default_format == "uastc":
            subprocess.run(texture_setting.to_uastc.format(ktx_path, file_path), shell=True)
        else:
            subprocess.run(texture_setting.to_etc1s.format(ktx_path, file_path), shell=True)

    os.remove(file_path)

#--------------------------------------------

def optimize_models(config: Config, dir: Directory):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []

        for model_setting in config.model_settings:
            file_paths = get_all_file_paths(dir.base_model, [".gltf"], False)
            for file_path in file_paths:
                future = executor.submit(
                    optimize_model, model_setting, dir, file_path
                )
                futures.append(future)

        concurrent.futures.wait(futures)

def optimize_model(model_setting : Config.ModelSetting, dir : Directory, file_path : str):
    command_move_to_dest = "mv {} {}"

    copy_to_glb_path = convert_file_path(file_path, dir.workspace, "{}.glb".format(model_setting.suffix))
    subprocess.run(model_setting.glb.format(file_path, copy_to_glb_path), shell=True)

    with open(file_path, 'r') as file:
        gltf_data = json.load(file)

    buffers = gltf_data.get("buffers", [])
    if len(buffers) > 0:
        extensionsUsed = gltf_data.get("extensionsUsed", [])
        extensionsUsed.append("KHR_texture_basisu")
        extensionsUsed.append("KHR_draco_mesh_compression")
        extensionsRequired = gltf_data.get("extensionsRequired", [])
        extensionsRequired.append("KHR_texture_basisu")
        extensionsRequired.append("KHR_draco_mesh_compression")
        samplers = gltf_data.get("samplers", [])
        textures = gltf_data.get("textures", [])
        materials = gltf_data.get("materials", [])

        if model_setting.tolerance != -1:
            subprocess.run(model_setting.weld.format(copy_to_glb_path, copy_to_glb_path), shell=True)

        if model_setting.ratio != -1:
            subprocess.run(model_setting.simplify.format(copy_to_glb_path, copy_to_glb_path), shell=True)

        subprocess.run(model_setting.draco.format(copy_to_glb_path, copy_to_glb_path), shell=True)

        copy_to_gltf_path = convert_file_path(file_path, dir.workspace, "{}.gltf".format(model_setting.suffix))
        subprocess.run(model_setting.gltf_separate.format(copy_to_glb_path, copy_to_gltf_path), shell=True)

        with open(copy_to_gltf_path, 'r') as file:
            gltf_data = json.load(file)

        images = gltf_data.get("images", [])
        for image in images:
            image["mimeType"] = "image/ktx2"
            image["uri"] = image["uri"].replace(".png", ".ktx2")

        gltf_data["extensionsUsed"] = extensionsUsed
        gltf_data["extensionsRequired"] = extensionsRequired
        gltf_data["samplers"] = samplers
        gltf_data["textures"] = textures
        gltf_data["materials"] = materials

        with open(copy_to_gltf_path, 'w') as file:
            json.dump(gltf_data, file, indent=4)
    else:
        copy_to_gltf_path = convert_file_path(file_path, dir.workspace, "{}.gltf".format(model_setting.suffix))
        subprocess.run(model_setting.gltf_separate.format(copy_to_glb_path, copy_to_gltf_path), shell=True)

#--------------------------------------------
    # After moving gltf, convert it to glb and put it back
    # moving gltf
    move_gltf_path = convert_file_path(copy_to_gltf_path, dir.texture[0], ".gltf")
    subprocess.run(command_move_to_dest.format(copy_to_gltf_path, move_gltf_path), shell=True)

    # convert glb
    glb_file_path = convert_file_path(copy_to_gltf_path, dir.texture[0], ".glb")
    subprocess.run(model_setting.glb_separate.format(move_gltf_path, glb_file_path), shell=True)

    # put it back
    workspace_glb_path = convert_file_path(move_gltf_path, dir.workspace, ".glb")
    subprocess.run(command_move_to_dest.format(glb_file_path, workspace_glb_path), shell=True)

    # put it back
    workspace_gltf_path_back = convert_file_path(glb_file_path, dir.workspace, ".gltf")
    subprocess.run(command_move_to_dest.format(move_gltf_path, workspace_gltf_path_back), shell=True)
    
#----------------------------------------------
# CLI
def main(argv):

    FILE_NAME     = argv[0] 
    INPUT_PATH = ""
    OUTPUT_PATH = ""
    CONPIG_PATH  = ""        
    UPDATE_MODE = False
    
    try:
        opts, etc_args = getopt.getopt(argv[1:], \
                                 "hi:c:", ["help", "path=", "output=", "config=", "update"])

    except getopt.GetoptError: 
        print(FILE_NAME, '--path <input gltf path> --output <output gltf path> --config <config json path)> --update')
        sys.exit(2)

    for opt, arg in opts: 
        if opt in ("-h", "--help"): 
            print(FILE_NAME, '--config <config path>)>')
            sys.exit()

        elif opt in ("--p", "--path"): 
            INPUT_PATH = os.path.abspath(arg)

        elif opt in ("--o", "--output"): 
            OUTPUT_PATH = os.path.abspath(arg)

        elif opt in ("--c", "--config"): 
            CONPIG_PATH = os.path.abspath(arg)

        elif opt in ("--u", "--update"): 
            UPDATE_MODE = os.path.abspath(arg)

    if len(INPUT_PATH) < 1: 
        print(FILE_NAME, "--path option is mandatory") 
        sys.exit(2)

    if len(OUTPUT_PATH) < 1: 
        print(FILE_NAME, "--output option is mandatory") 
        sys.exit(2)

    if len(CONPIG_PATH) < 1: 
        print(FILE_NAME, "--config option is mandatory") 
        sys.exit(2)
        
    run(INPUT_PATH, OUTPUT_PATH, CONPIG_PATH, UPDATE_MODE)

if __name__ == "__main__":
    main(sys.argv)
