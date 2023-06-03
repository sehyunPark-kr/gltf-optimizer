from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    
    @dataclass
    class TextureSetting:
        max_size: int = 2048
        scale: float = 1.0
        default_format: str = "etc1s"
        keywords: List[str] = field(default_factory=list)
        astc_blk_d: str = "8x8"
        uastc_quality: int = 2
        uastc_rdo_l: float = 0.5
        uastc_rdo_d: int = 8192
        zcmp: int = 22
        clevel: int = 1
        qlevel: int = 128
        assign_oetf: str = "srgb"

        # imagemagic commands
        # ref : https://imagemagick.org/Usage/resize/

        # resize command
        def resize(self, src) -> str:
            return (
                "mogrify -resize "
                f"{self.max_size}x{self.max_size}\> "
                "{}"
            ).format(src)
        
        # resize scale command
        def resize_scale(self, src) -> str:
            scale = min(max(0.01, self.scale), 1) * 100
            return (
                "mogrify -resize "
                f"{scale}% " 
                "{}"
            ).format(src)
        

        # toktx commands
        # ref : https://github.khronos.org/KTX-Software/ktxtools/toktx.html

        # to ktx common command
        def to_ktx_common(self) -> str:
            return (
                "toktx "
                "--genmipmap "
                "--t2 "
                "--assign_primaries none "
            )
    
        # to etc1 ktx2 command
        def to_etc1s(self, src, dst) -> str:
            return self.to_ktx_common() + (
                "--encode etc1s "
                f"--assign_oetf {self.assign_oetf} "
                "'{}' '{}' "
            ).format(dst, src)
        
        # to uastc ktx2 command
        def to_uastc(self, src, dst) -> str:
            return self.to_ktx_common() + (
                "--encode uastc "
                f"--astc_blk_d {self.astc_blk_d} "
                f"--uastc_quality {self.uastc_quality} "
                f"--uastc_rdo_l {self.uastc_rdo_l} "
                f"--uastc_rdo_d {self.uastc_rdo_d} "
                f"--zcmp {self.zcmp} "
                f"--assign_oetf {self.assign_oetf} "
                "'{}' '{}' "
            ).format(dst, src)
        
        # set default format to ktx2 command
        def to_ktx(self, src, dst) -> str: 
            if self.default_format == 'uastc':
                return self.to_uastc(src, dst)
            else:
                return self.to_etc1s(src, dst)
        
        # other format to ktx2 command
        def to_ktx_other(self, src, dst) -> str:
            if self.default_format == 'uastc':
                return self.to_etc1s(src, dst)
            else:
                return self.to_uastc(src, dst)
            

                
    @dataclass
    class ModelSetting:
        suffix: str = ""
        tolerance: float = -1
        ratio: float = -1
        error: float = 0.01
        lock_border: bool = False
        decode_speed: int = 7
        encode_speed: int = 7
        quantize_position: int = 11
        quantize_normal: int = 8
        quantize_texcoord: int = 10
        quantize_color: int = 8

        # gltf-pipeline commands
        # ref : https://github.com/CesiumGS/gltf-pipeline
        def gltf_pipeline(self, src, dst) -> str:
            return "gltf-pipeline -i {} -o {} --keepUnusedElements --keepLegacyExtensions".format(src, dst)

        def to_glb(self, src, dst) -> str: 
            return self.gltf_pipeline(src, dst) + " -b"
        
        def to_glb_separate(self, src, dst) -> str: 
            return self.gltf_pipeline(src, dst) + " -b -t"
        
        def to_gltf_separate(self, src, dst) -> str: 
            return self.gltf_pipeline(src, dst) + " -t"
        
        # gltf-transform commands
        # ref : https://gltf-transform.donmccurdy.com/cli
        def weld(self, src, dst) -> str:
            return (
                "gltf-transform weld " 
                f"--tolerance {self.tolerance} " 
                "{} {}"
            ).format(src, dst)

        def simplify(self, src, dst) -> str:
            return (
                "gltf-transform simplify "
                f"--ratio {self.ratio} "
                f"--error {self.error} " 
                f"--lock_border {self.lock_border} "
                "{} {}"
            ).format(src, dst)

        def draco(self, src, dst) -> str:
            return (
                "gltf-transform draco "
                f"--decode-speed {self.decode_speed} --encode-speed {self.encode_speed} "
                f"--quantize-position {self.quantize_position} "
                f"--quantize-normal {self.quantize_normal} "
                f"--quantize-texcoord {self.quantize_texcoord} "
                f"--quantize-color {self.quantize_color} "
                "{} {}"
            ).format(src, dst)


    def __init__(self, output_exts: List[str]):
        self.output_exts = output_exts
        self.texture_settings: List[Config.TextureSetting] = []
        self.model_settings: List[Config.ModelSetting] = []

    def parse_texture_settings(self, texture_settings):
        for setting in texture_settings:
            self.texture_settings.append(
                Config.TextureSetting(
                    max_size=setting.get('max_size', 2048),
                    scale=setting.get("scale", 1),
                    default_format=setting.get("default_format", "etc1s"),
                    keywords=setting.get('keywords', []),
                    astc_blk_d=setting.get("astc_blk_d", "8x8"),
                    uastc_quality=setting.get("uastc_quality", 2),
                    uastc_rdo_l=setting.get("uastc_rdo_l", 0.5),
                    uastc_rdo_d=setting.get("uastc_rdo_d", 8192),
                    zcmp=setting.get("zcmp", 22),
                    clevel=setting.get("clevel", 1),
                    qlevel=setting.get("qlevel", 128),
                    assign_oetf=setting.get("assign_oetf", "srgb")
                )
            )

    def parse_model_settings(self, model_settings):
        for setting in model_settings:
            model_setting = Config.ModelSetting(
                suffix=setting.get("suffix", ""),
                tolerance=setting.get("tolerance", -1),
                ratio=setting.get("ratio", -1),
                error=setting.get("error", 0.01),
                lock_border=setting.get("lock_border", False),
                decode_speed=setting.get("decode_speed", 7),
                encode_speed=setting.get("encode_speed", 7),
                quantize_position=setting.get("quantize_position", 11),
                quantize_normal=setting.get("quantize_normal", 8),
                quantize_texcoord=setting.get("quantize_texcoord", 10),
                quantize_color=setting.get("quantize_color", 8)
            )
            self.model_settings.append(model_setting)


def parse_config(data) -> Config:
    # Check output ext
    output_exts = data.get('output_exts', [])
    if not output_exts:
        raise ValueError("output_exts is required.")

    config = Config(output_exts)

    # Check texture setting
    texture_settings = data.get('texture_settings', [])
    if not texture_settings:
        raise ValueError("At least 1 texture setting is required.")

    config.parse_texture_settings(texture_settings)

    # Check model setting
    model_settings = data.get('model_settings', [])
    if not model_settings:
        raise ValueError("At least 1 model setting is required.")

    config.parse_model_settings(model_settings)

    return config
