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
            ret=subprocess.run(["unzip", "-o", "-d", "dicom", "dicom.zip"], cwd=outdir)
            if ret.returncode != 0: 
                print("failed to unzip")
                sys.exit(ret.returncode)            

            print("running dcm2niix on %s" % outdir)
            #-v : verbose (n/y or 0/1/2, default 0) [no, yes, logorrheic
            #-z : gz compress images (y/o/i/n/3, default n) [y=pigz, o=optimal pigz, i=internal:miniz, n=no, 3=no,3D]
            #-d : directory search depth. Convert DICOMs in sub-folders of in_folder? (0..9, default 5
            #-w : write behavior for name conflicts (0,1,2, default 2: 0=skip duplicates, 1=overwrite, 2=add suffix)
            #-b : BIDS sidecar (y/n/o [o=only: no NIfTI], default y)
            #-f : filename 
            #. < input folder
            ret=subprocess.run(["dcm2niix", "-v", "1", "-z", "o", "-d", "10", "-w", "1", "-b", "y", "-f", name, "."], cwd=outdir)
            if ret.returncode != 0: 
                print("failed to run dcm2niix")
                sys.exit(ret.returncode)            

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


