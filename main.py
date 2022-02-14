#!/usr/bin/env python3

import json
import subprocess
import errno
import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth
import base64
from pathlib import Path

#TODO - I should validate paths specified in file src/dest to make sure it doesn't go outside the workdir

def makedirp(dir):
    try: 
        os.makedirs(dir)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(dir):
            pass
        else:
            raise

with open("config.json") as config_json:
    config = json.load(config_json)
    for dataset in config["datasets"]:
        print("staging %s" % dataset["id"])
        storage = "wrangler"
        if "storage" in dataset:
            storage = dataset["storage"]

        print("using storage", storage)

        outdir=dataset["id"]
        if 'outdir' in dataset:
            outdir=dataset["outdir"]

        if storage == "wrangler" or storage == "osiris" or storage == "osn":
            if 'BRAINLIFE_RATAR_AUTOFS_'+storage in os.environ:
                print("accessing through ratar", storage)
                ratarPath = os.environ["BRAINLIFE_RATAR_AUTOFS_"+storage]+"/"+dataset["project"]+"."+dataset["id"]
                if not os.path.exists(ratarPath):
                    print("ratar directory does not exist", ratarPath);
                    sys.exit(1)
                ratarDir = os.listdir(ratarPath)
                if len(ratarDir) == 0:
                    print("ratar directory is empty.. maybe filesystem offline?", ratarPath)
                    sys.exit(1)
                if not os.path.exists(outdir):
                    print("creating symlink", outdir)
                    os.symlink(ratarPath, outdir, True)
                else:
                    print(outdir, "already exists")
            else:
                print("untarring from archive", storage);
                makedirp(outdir)
                src=os.environ["BRAINLIFE_ARCHIVE_"+storage]+"/"+dataset["project"]+"/"+dataset["id"]+".tar"
                code=subprocess.call(["tar", "xvf", src, "--strip", "6", "-C", outdir])
                if code != 0:
                    sys.exit(code)
        elif storage == "url":
            makedirp(outdir)
            for file in dataset["storage_config"]["files"]:
                #use requests.get?
                code=subprocess.call(["wget", "-O", outdir+"/"+file["local"], file["url"]])
                if code != 0:
                    sys.exit(code)

                #if .nii is found on the remote url, compress it to make it .nii.gz as 
                #all brainlife nifti file needs to be in .nii.gz (for openneuro)
                if file["url"].endswith(".nii"):
                    print("compressiong .nii to nii.gz")
                    tmpname=outdir+"/"+file["local"][:-3] #strip .gz
                    subprocess.call(["mv", outdir+"/"+file["local"], tmpname]) 
                    subprocess.call(["gzip", tmpname])

        elif storage == "datalad":
            makedirp(outdir)
            path = dataset["storage_config"]["path"]
            for file in dataset["storage_config"]["files"]:
                cwd="/mnt/datalad"
                src = file["src"]
                src_tokens = src.split("/")
        
                #move first dir path to cwd so datalad will find the dataset
                for p in path.split("/"):
                    src_tokens.pop(0)
                    cwd += "/"+p
                src_sub = "/".join(src_tokens)
                code=subprocess.call(["datalad", "get", src_sub], cwd=cwd)
                if code != 0:
                    sys.exit(code)

                #if .nii is found on the remote url, compress it to make it .nii.gz as 
                #all brainlife nifti file needs to be in .nii.gz (for openneuro)
                if src.endswith(".nii"):
                    print("compressiong .nii to nii.gz")
                    dest=outdir+"/"+file["dest"][:-3]
                    subprocess.call(["cp", cwd+"/"+src_sub, dest]) 
                    subprocess.call(["gzip", "-f", dest]) 
                else:
                    subprocess.call(["ln", "-sf", cwd+"/"+src_sub, outdir+"/"+file["dest"]]) 

        elif storage == "xnat":
            makedirp(outdir)
            storage_config = dataset["storage_config"]
            hostname = storage_config["hostname"]
            project = storage_config["project"]
            token = storage_config["token"]
            path = storage_config["path"]

            meta = None
            for output in config["_outputs"]:
                if output["id"] == dataset["id"]:
                    meta = output["meta"] 

            subject = meta["subject"]
            experiment = meta["session"]
            scan = dataset["id"]
            if "xnat_scan" in meta:
                scan = meta["xnat_scan"]

            openssl = subprocess.Popen(["openssl", "rsautl", "-inkey", str(Path.home())+"/.ssh/configEncrypt.key", "-decrypt"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            openssl.stdin.write(base64.b64decode(dataset["storage_config"]["secretEnc"]))
            secret = openssl.communicate()[0]
            openssl.stdin.close()

            url = hostname+"/data/projects/"+project+"/subjects/"+subject+"/experiments/"+experiment+"/scans/"+scan+"/"+path
            res = requests.get(url,
                auth=HTTPBasicAuth(storage_config["token"], secret),
                params={"format": "zip"})
            if res.status_code != 200:
                print("xnat returned non-200")
                print(res)
                sys.exit(1)
            open(outdir+"/xnat.zip", "wb").write(res.content)
        else:
            #download from brainlife download server
            code=subprocess.call(["bl", "dataset", "download", dataset["id"], outdir])
            if code != 0:
                sys.exit(code)

    #validate
    for dataset in config["datasets"]:
        outdir=dataset["id"]
        if 'outdir' in dataset:
            outdir=dataset["outdir"]

        if not os.path.exists(outdir):
            print("failed to stage", outdir)
            sys.exit(1)

print("main.py done")

