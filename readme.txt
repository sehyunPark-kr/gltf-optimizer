npm install -g imagemagick
npm install -g gltf-pipeline
npm install -g @gltf-transform/cli

// npm install -g ghostscript (temp)

source venv/bin/activate

----

pip install pygltflib

python3 gltf_optimizer_cli.py --config config.json

----

toktx : chmod +x toktx

// gltfpack : chmod +x gltfpack (temp. gltf metadata를 변경시켜 일단 사용 안함)

를 입력해 unix 파일로 변경하고 (변경이 안되어 있다면)

-----

- /usr/local/bin 폴더에 넣거나
- bash_profile에 해당 경로를 export PATH="{경로를 입력하세요}:$PATH" 를 입력하고 source ~/.bash_profile 로 적용합니다.


 "build-gltf": "yarn gltf-optimize --update 1 && yarn gltf-optimize-half --update 1 && yarn gltf-optimize-quarter --update 1 && yarn gltf-optimize-eighth --update 1",
    "build-gltf-all": "yarn gltf-optimize && yarn gltf-optimize-half && yarn gltf-optimize-quarter && yarn gltf-optimize-eighth",
    "gltf-optimize": "python3 tools/gltf-optimizer/gltf_optimizer_cli.py --path ./source --output ./public/assets/gltf/full --resolution 1",
    "gltf-optimize-half": "yarn gltf-optimize --output ./public/assets/gltf/half --resolution 0.5",
    "gltf-optimize-quarter": "yarn gltf-optimize --output ./public/assets/gltf/quarter --resolution 0.25",
    "gltf-optimize-eighth": "yarn gltf-optimize --output ./public/assets/gltf/eighth --resolution 0.125"