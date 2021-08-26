#!/usr/bin/env python3

import subprocess
import os
import sys
import json
import shutil
import glob

T1W="58c33bcee13a50849b25879a"
T2W="594c0325fa1d2e5a1f0beda5"
TASK="59b685a08e5d38b0b331ddc5"
DWI="58c33c5fe13a50849b25879b"

with open("config.json") as config_json:
    config = json.load(config_json)
    for dataset in config["datasets"]:
        print("converting %s" % dataset["id"])

        storage = "wrangler"
        if "storage" in dataset:
            storage = dataset["storage"]

        outdir=dataset["id"]
        if 'outdir' in dataset:
            outdir=dataset["outdir"]

        if storage == "xnat":
            #find information about this object from _outputs
            datatype=None
            for output in config["_outputs"]:
                if output["dataset_id"] == dataset["id"]:
                    meta = output["meta"]
                    datatype = output["datatype"]

            #figure out appropriate file prefix for brainlife datatype
            name="unknown"
            if datatype == T1W:
                name="t1"
            if datatype == T2W:
                name="t2"
            if datatype == TASK:
                name="bold"
            if datatype == DWI:
                name="dwi"

            print("unzipping")
            code=subprocess.call(["unzip", "-o", "-d", "dicom", "dicom.zip"], cwd=outdir)
            print("running dcm2niix on %s" % outdir)
            code=subprocess.call(["dcm2niix", "-v", "1", "-z", "o", "-d", "10", "-w", "1", "-f", name, "."], cwd=outdir)


            print("loading sidecar .json and creating product.json")
            sidecar_jsons = glob.glob(outdir+"/*.json")
            with open(sidecar_jsons[0]) as sidecar_f:
                sidecar = json.load(sidecar_f)

            #merge meta from output
            for key in sidecar:
                meta[key] = sidecar[key]

            with open("product.json", "w") as f:
                json.dump({"meta": meta}, f)

            #rename file products to brainlife datatype file names
            if datatype == DWI:
                bvecs = glob.glob(outdir+"/*.bvec")
                subprocess.call(["mv", bvecs[0], outdir+"/dwi.bvecs"])
                bvals = glob.glob(outdir+"/*.bval")
                subprocess.call(["mv", bvals[0], outdir+"/dwi.bvals"])

            #clean up things
            os.remove(outdir+"/dicom.zip")
            shutil.rmtree(outdir+"/dicom")
            os.remove(sidecar_jsons[0]) #sidecar

        else:
            None

print("convert.py done")


