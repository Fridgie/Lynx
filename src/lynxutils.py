import os
import shutil
import sys
from confvar import *

def lynxQuit():
    if os.path.isdir("./temp/"):
        shutil.rmtree("./temp")
    print("Browser exited successfully")

def decodeLynxUrl(qurl):
    if qurl.toString() == "lynx:blank":
        return qurl.toString()
    if str(qurl.toString())[:5] == "lynx:":
        base = qurl.toString().replace("lynx:", "")
        lfile = str(qurl.toString()).split(":")[1]
        if os.path.isfile(BASE_PATH + "lynx/" + base + "/" + BROWSER_STYLESHEET + "_" + lfile + ".html"):
            lfile = BROWSER_STYLESHEET + "_" + lfile
        elif os.path.isfile(BASE_PATH + "lynx/" + base + "/" + lfile + ".html"):
            lfile = lfile
        lfile = os.path.abspath(BASE_PATH + "lynx/" + base + "/" + lfile)
    else:
        return qurl.toString()
    lfile = lfile.replace("\\", "/")
    return "file:///" + lfile + ".html"

def encodeLynxUrl(qurl):
    if str(qurl.toString())[:8] == "file:///" and "lynx/" in qurl.toString():
        lfile = str(qurl.toString()).split("/")
        lfile = lfile[len(lfile)-1]
    else:
        return qurl.toString()
    if "_" in lfile:
        return "lynx:" + lfile.split("_")[1][:-5] 
    return "lynx:" + lfile[:-5]

def checkLynxUrl(qurl):
    if str(qurl.toString())[:5] == "lynx:":
        return True
    return False
