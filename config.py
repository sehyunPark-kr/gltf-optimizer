
import sys
from typing import List


def parse_config(data):

    # Check output ext
    output_exts = data.get('output_exts', '')
    if not output_exts:
        print("output_exts is required.")
        sys.exit(2)
    config = Config(output_exts)

    # Check texture setting
    texture_settings = data.get('texture_settings', [])
    if not texture_settings:
        print("At least 1 texture setting is required.")
        sys.exit(2)
    config.parse_texture_settings(texture_settings)

    # Check model setting
    model_settings = data.get('model_settings', [])
    if not model_settings:
        print("At least 1 model setting is required.")
        sys.exit(2)
    config.parse_model_settings(model_settings)
    
    return config

class Config:
    def __init__(self, output_exts : List[str]):
        self.output_exts = output_exts
        self.texture_settings : List[Config.TextureSetting] = []
        self.model_settings : List[Config.ModelSetting] = []

    def parse_texture_settings(self, texture_settings):
        for setting in texture_settings:
            texture_setting = self.TextureSetting(
                # resize
                setting.get('max_size', 2048),
                setting.get("scale", 1),
                # format
                setting.get("defualt_format", "etc1s"),
                setting.get('keywords', ""),
                # uastc
                setting.get("astc_blk_d", "8x8"),
                setting.get("uastc_quality", 2),
                setting.get("uastc_rdo_l", 0.5),
                setting.get("uastc_rdo_d", 8192),
                setting.get("zcmp", 22),
                # etc1s
                setting.get("clevel", 1),
                setting.get("qlevel", 128),
                # common
                setting.get("assign_oetf", "srgb")
            )
            self.texture_settings.append(texture_setting)

    def parse_model_settings(self, model_settings):
        for setting in model_settings:
            model_setting = self.ModelSetting(
                setting.get("suffix", ""),
                # weld
                setting.get("tolerance", -1),
                # simplify
                setting.get("ratio", -1),
                setting.get("error", 0.01),
                setting.get("lock_border", False),
                # draco
                setting.get("decode_speed", 7),
                setting.get("encode_speed", 7),
                setting.get("quantize_position", 11),
                setting.get("quantize_normal", 8),
                setting.get("quantize_texcoord", 10),
                setting.get("quantize_color", 8)
            )
            self.model_settings.append(model_setting)

    class TextureSetting:
        def __init__(self, max_size: int, scale: float, default_format: str, keywords: List[str], 
                     astc_blk_d: str, uastc_quality: int, uastc_rdo_l: float, uastc_rdo_d: int, zcmp: int, 
                     clevel: float, qlevel: int, assign_oetf: str):
            self.max_size = max_size
            self.scale = min(max(0.01, scale), 1) * 100
            self.default_format = default_format
            self.keywords = keywords
            self.astc_blk_d = astc_blk_d
            self.uastc_quality = uastc_quality
            self.uastc_rdo_l = uastc_rdo_l
            self.uastc_rdo_d = uastc_rdo_d
            self.zcmp = zcmp
            self.clevel = clevel
            self.qlevel = qlevel
            self.assign_oetf = assign_oetf

            # resize command
            self.resize = f"mogrify -resize {self.max_size}x{self.max_size}\>" + " {}"
            # resize scale command
            self.resize_scale = f"mogrify -resize {self.scale}%" + " {}"
            # to etc1 ktx2 command
            self.to_etc1s = f"toktx --genmipmap --t2 --encode {self.default_format} --clevel {self.clevel} --qlevel {self.qlevel} --assign_oetf {self.assign_oetf} --assign_primaries none" + " '{}' '{}'"
            # to uastc ktx2 command
            self.to_uastc = f"toktx --genmipmap --t2 --encode uastc --astc_blk_d {self.astc_blk_d} --uastc_quality {self.uastc_quality} --uastc_rdo_l {self.uastc_rdo_l} --uastc_rdo_d {self.uastc_rdo_d} --zcmp {self.zcmp} --assign_oetf {self.assign_oetf} --assign_primaries none" + " '{}' '{}'"
            

    class ModelSetting:
        def __init__(self, suffix: str, tolerance: float, ratio: float, error: float, lock_border: bool, 
                     decode_speed: int, encode_speed: int, quantize_position: int, quantize_normal: int, 
                     quantize_texcoord: int, quantize_color: int):
            self.suffix = suffix
            self.tolerance = tolerance
            self.ratio = ratio
            self.error = error
            self.lock_border = lock_border
            self.decode_speed = decode_speed
            self.encode_speed = encode_speed
            self.quantize_position = quantize_position
            self.quantize_normal = quantize_normal
            self.quantize_texcoord = quantize_texcoord
            self.quantize_color = quantize_color
            
            self.glb = "gltf-pipeline -i {} -o {} -b --keepUnusedElements --keepLegacyExtensions"
            self.glb_separate = "gltf-pipeline -i {} -o {} -b -t --keepUnusedElements --keepLegacyExtensions"
            self.gltf_separate = "gltf-pipeline -i {} -o {} -t --keepUnusedElements --keepLegacyExtensions"
            
            self.weld = f"gltf-transform weld --tolerance {self.tolerance}" + " {} {}"
            self.simplify = f"gltf-transform simplify --ratio {self.ratio} --error {self.error} --lock_border {self.lock_border}" + " {} {}"
            self.draco = "gltf-transform draco {} {} " + f"--decode-speed {self.decode_speed} --encode-speed {self.encode_speed} --quantize-position {self.quantize_position} --quantize-normal {self.quantize_normal} --quantize-texcoord {self.quantize_normal} --quantize-color {self.quantize_color}"
