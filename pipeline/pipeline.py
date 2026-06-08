#
# pipeline.py
#

## LIBRERIAS

import logging
import os
import time
import yaml
import pandas as pd
from pathlib import Path

from lib_utils import find_project_root, setup_logging, opt_get, find_file, info_desc, retry



## FUNCIONES


# -------------------------
# ETL STEPS
# -------------------------

@retry(retries=3)
def extract(config):
    logging.info("Inicio Extract")

    in_path = find_file( config["data"].get("source") )
    logging.debug("Ruta datos de entrada: %s", in_path)
    

    if not in_path.exists() or in_path.stat().st_size == 0:
        raise ValueError("No se extrajo data")

    df = pd.read_csv(in_path)
    info_desc(df)

    logging.info("Extract completado")
    return df




@retry(retries=2)
def transform(data, config):
    logging.info("Inicio Transform")

    data = data.copy()  # avoid mutating input unexpectedly

    data["month"] = config.get("month")
    data["year"] = config.get("year")
    logging.debug(f"Columns: {list(data.columns)}")

    logging.info("Transform completado")
    return data


@retry(retries=3)
def load(data, config, out_dir = "output"):
    logging.info("Inicio load")

    # input_file = config.get("source")
    output_path = ROOT / out_dir

    os.makedirs(output_path, exist_ok=True)  

    output_file = output_path / f"pipeline_res_{time.strftime('%Y%m%d_%H%M%S')}.parquet"

    data.to_parquet( output_file )

    logging.info(f"Data guardada en {output_file}")


# -------------------------
# PIPELINE
# -------------------------
def run_pipeline(config):
    logging.info("Inicio Pipeline")

    data = extract(config)
    tform_data = transform(data, config["pipeline"])
    load(tform_data, config["data"])

    logging.info("Pipeline finalizado")


# -------------------------
# CONFIG
# -------------------------
def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)




# -------------------------
# MAIN
# -------------------------

def main():

    config_path = find_file(
        opt_get("config", default="config.yaml")
    )

    config = load_config(config_path)
    setup_logging( config["pipeline"].get("verbose") )

    logging.info("START")
    logging.debug("ROOT: %s", ROOT)
    logging.debug("Ruta config: %s", config_path)

    # in_path = find_file(
    #     opt_get("in", default="data_in/data_entry.csv")
    # )

    # out_path = find_file(
    #     opt_get("out", default="output/result.parquet")
    # )

    run_pipeline(config)



if __name__ == "__main__":

    ROOT = find_project_root()
    main()