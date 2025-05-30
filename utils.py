import requests
import zipfile
import os



def extract_file(manifest_r: requests.Response) -> None: 
    with open("manifest.zip", "wb") as f:
        f.write(manifest_r.content)

    with zipfile.ZipFile("manifest.zip", "r") as f:
        f.extractall("manifest")
    
    os.remove("manifest.zip")