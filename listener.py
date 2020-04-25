import subprocess
import random
import string
import os
import shutil
import time
from flask import Flask, jsonify, request, abort

app= Flask(__name__)

codeFile = "templates/code.dm"
testDME = "templates/test.dme"
template = None
mainProc = "/proc/main()"
host = "127.0.0.1"

@app.route("/compile", methods=["POST"])
def setName():
    if request.method=='POST':
        posted_data = request.get_json()
        try:
            if 'code_to_compile' in posted_data:
                data = compileTest(posted_data['code_to_compile'])
                return data
            else:
                abort(400)
        except:
            abort(400)

def loadTemplate(line:str, includeProc=True):
    with open(codeFile) as filein:
        template = string.Template(filein.read())

    if includeProc:
        line = '\n\t'.join(line.splitlines())
        d = {'proc':mainProc, 'code':f'{line}\n'}
    else:
        d = {'proc':line, 'code':''}

    return template.substitute(d)

def randomString(stringLength=24):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

def compileTest(codeText:str):
    randomDir = randomString()
    os.mkdir(randomDir)
    shutil.copyfile(testDME, f"./{randomDir}/test.dme")
    with open(f'./{randomDir}/code.dm', 'a') as fc:
        if '/proc/main()' not in codeText:
            fc.write(loadTemplate(codeText))
        else:
            fc.write(loadTemplate(codeText, False))

    proc = subprocess.Popen(["cmd", "/c", f"docker run --name {randomDir} --rm -v {os.getcwd()}/{randomDir}:/app/code:ro test"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        outs, errs = proc.communicate(timeout=5.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        subprocess.run(["cmd", "/c", f"docker stop {randomDir}"], capture_output=True)
        outs, errs = proc.communicate()

    outs = outs.decode('utf-8')
    errs = errs.decode('utf-8')
    outs = (outs[:1200] + '...') if len(outs) > 1200 else outs
    errs = (errs[:1200] + '...') if len(errs) > 1200 else errs
      
    shutil.rmtree(randomDir)

    return (f"{outs}\n{errs}")

if __name__=='__main__':
    app.run(host=host)
