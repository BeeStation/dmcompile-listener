import subprocess
import random
import string
import shutil
import time
import platform
from flask import Flask, jsonify, request, abort
from pathlib import Path

app = Flask(__name__)

CODE_FILE = Path.cwd().joinpath("templates/code.dm")
HOST = "127.0.0.1"
HOST_OS = platform.system()
MAIN_PROC = "/proc/main()"
TEST_DME = Path.cwd().joinpath("templates/test.dme")

template = None
test_killed = False

@app.route("/compile", methods = ["POST"])
def setName():
    if request.method == 'POST':
        posted_data = request.get_json()
        if 'code_to_compile' in posted_data:
            return jsonify(compileTest(posted_data['code_to_compile']))
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

def compileTest(codeText:str):
    randomDir = Path.cwd().joinpath(randomString())
    randomDir.mkdir()
    shutil.copyfile(TEST_DME, randomDir.joinpath("test.dme"))
    with open(randomDir.joinpath("code.dm"), 'a') as fc:
        if MAIN_PROC not in codeText:
            fc.write(loadTemplate(codeText))
        else:
            fc.write(loadTemplate(codeText, False))
    if HOST_OS == "Windows":
        proc = subprocess.Popen(["docker", "run", "--name", f"{randomDir.name}", "--rm", "-v", f"{randomDir}:/app/code:ro", "test"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        proc = subprocess.Popen([Path.home().joinpath("/bin/docker"), "run", "--name", f"{randomDir.name}", "--rm", "-v", f"{randomDir}:/app/code:ro", "test"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        outs, errs = proc.communicate(timeout=30)
        test_killed = False
    except subprocess.TimeoutExpired:
        proc.kill()
        if HOST_OS == "Windows":
            subprocess.run(["docker", "stop", f"{randomDir.name}"], capture_output=True)
        else:
            subprocess.run([Path.home().joinpath("/bin/docker"), "stop", f"{randomDir.name}"], capture_output=True)
        outs, errs = proc.communicate()
        test_killed = True

    outs = outs.decode('utf-8')
    errs = errs.decode('utf-8')
    outs = (outs[:1200] + '...') if len(outs) > 1200 else outs
    errs = (errs[:1200] + '...') if len(errs) > 1200 else errs
      
    shutil.rmtree(randomDir)
    results = {
        "compile_log":outs,
        "run_log":errs,
        "timeout":test_killed
    }
    return results

if __name__=='__main__':
    app.run(host=HOST)
