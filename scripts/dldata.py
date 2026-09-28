import io
import os
import zipfile
import requests

# Official Sean Lahman CSV release URL
LAHMAN_URL = "https://www.seanlahman.com/files/database/lahman-csv_2022-10-08.zip"
OUTPUT_DIR = "data"


def download_lahman_data(url: str = LAHMAN_URL, output_dir: str = OUTPUT_DIR):
    """Downloads and extracts the Lahman Baseball CSV database archive."""
    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading Lahman data archive from {url}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    print("Extracting CSV files...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # Extract files flattening nested subdirectories if present
        for member in z.infolist():
            filename = os.path.basename(member.filename)
            # Skip directories or non-CSV files
            if not filename or not filename.lower().endswith(".csv"):
                continue

            target_path = os.path.join(output_dir, filename)
            with z.open(member) as source, open(target_path, "wb") as target:
                target.write(source.read())

    print(f"Extraction complete! Files are saved in: {output_dir}/")


if __name__ == "__main__":
    download_lahman_data()
