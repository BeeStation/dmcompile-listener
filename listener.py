import subprocess
import random
import string
import shutil
import time
import platform
import docker
import re
from flask import Flask, jsonify, request, abort
from pathlib import Path

app = Flask(__name__)
client = docker.from_env()

CODE_FILE = Path.cwd().joinpath("templates/code.dm")
HOST = "127.0.0.1"
HOST_OS = platform.system()
MAIN_PROC = "proc/main()"
TEST_DME = Path.cwd().joinpath("templates/test.dme")

template = None
test_killed = False

@app.route("/compile", methods = ["POST"])
def startCompile():
    if request.method == 'POST':
        posted_data = request.get_json()
        if 'code_to_compile' in posted_data:
            return jsonify(compileTest(posted_data['code_to_compile'], posted_data['byond_version']))
        else:
            abort(400)


def loadTemplate(line:str, includeProc=True):
    with open(CODE_FILE) as filein:
        template = string.Template(filein.read())

    if includeProc:
        line = '\n\t'.join(line.splitlines())
        d = {'proc':MAIN_PROC, 'code':f'{line}\n'}
    else:
        d = {'proc':line, 'code':''}

    return template.substitute(d)

def randomString(stringLength=24):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

def checkVersions(version:str):
    try:
        image_list = client.images.list(name='beestation/byond')
    except IndexError:
        return False

    for image in image_list:
        if f"beestation/byond:{version}" in image.tags:
            return True

    return False

def buildVersion(version:str):
    #Check if the version is already built
    if checkVersions(version=version):
        return
    else:
        try:
            print(f"Attempting to build version: {version}")
            return client.images.build(path=f'https://github.com/BeeStation/byond-docker.git', rm=True, pull=True, tag=f'beestation/byond:{version}', buildargs={
                'buildtime_BYOND_MAJOR': version.split('.')[0],
                'buildtime_BYOND_MINOR': version.split('.')[1]
                })
        except docker.errors.BuildError:
            raise

def compileTest(codeText:str, version:str):
    try:
        buildVersion(version=version)
    except docker.errors.BuildError as e:
        results = {
            "build_error": True,
            "exception": str(e) 
        }
        return results

    randomDir = Path.cwd().joinpath(randomString())
    randomDir.mkdir()
    shutil.copyfile(TEST_DME, randomDir.joinpath("test.dme"))
    with open(randomDir.joinpath("code.dm"), 'a') as fc:
        if MAIN_PROC not in codeText:
            fc.write(loadTemplate(codeText))
        else:
            fc.write(loadTemplate(codeText, False))
    command = ['bash', '-c', 'cp code/* .; DreamMaker test.dme; DreamDaemon test.dmb -close -verbose -ultrasafe | cat']
    if HOST_OS == "Windows":
        #To get cleaner outputs, we run docker as a subprocess rather than through the API
        proc = subprocess.Popen(["docker", "run", "--name", f"{randomDir.name}", "--rm", "--network", "none", "-v", f"{randomDir}:/app/code:ro", "-w", "/app", f"beestation/byond:{version}"] + command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        #Expects the linux user to be running docker locally, not as root
        proc = subprocess.Popen([f"/usr/bin/docker", "run", "--name", f"{randomDir.name}", "--rm", "--network", "none", "-v", f"{randomDir}:/app/code:ro", "-w", "/app", f"beestation/byond:{version}"] + command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        compile_log, run_log = proc.communicate(timeout=30) #A bit hacky, but provides exceptionally clean results. The main output will be captured as the compile_log while the "error" output is captured as run_log
        test_killed = False
    except subprocess.TimeoutExpired:
        proc.kill()
        if HOST_OS == "Windows":
            subprocess.run(["docker", "stop", f"{randomDir.name}"], capture_output=True)
        else:
            subprocess.run([f"{Path.home()}/bin/docker", "stop", f"{randomDir.name}"], capture_output=True)
        compile_log, run_log = proc.communicate()
        test_killed = True

    compile_log = compile_log.decode('utf-8')
    run_log = run_log.decode('utf-8')
    run_log = re.sub(r'The BYOND hub reports that port \d* is not reachable.', '', run_log) #remove the network error message
    run_log = re.sub(r'\n---------------\n', '\n', run_log) #remove the dashes
    run_log = re.sub(r'World opened on network port \d*\.\n', '', run_log)
    compile_log = re.sub(r'loading test.dme\n', '', compile_log)
    compile_log = re.sub(r'saving test.dmb\n', '', compile_log)
    compile_log = (compile_log[:1200] + '...') if len(compile_log) > 1200 else compile_log
    run_log = (run_log[:1200] + '...') if len(run_log) > 1200 else run_log
      
    shutil.rmtree(randomDir)

    if f"Unable to find image 'byond:{version}' locally" in run_log:
        results = {
            "build_error": True,
            "exception": run_log
        }
    else:
        results = {
            "compile_log":compile_log,
            "run_log":run_log,
            "timeout":test_killed
        }

    return results

if __name__=='__main__':
    app.run(host=HOST)
