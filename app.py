from flask import Flask,render_template,request,session,redirect,url_for,flash,jsonify
from flask_session import Session
from datetime import datetime
from essential_generators import DocumentGenerator
# from simplecrypt import encrypt, decrypt
from io import BytesIO

import pymongo
import os
import json
import base64
import copy

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plot


app = Flask(__name__)

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["SESSION_PERMANENT"] = False
app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")
app.config["SESSION_TYPE"] = "filesystem"
app.config['development'] = True
app.config['SECRET_KEY'] = '#KR#'

Session(app)

cluster = pymongo.MongoClient(os.getenv("DATABASE_URL"))["type-tester"]
crypt = os.getenv("CRYPT_CODE")

@app.route("/")
def index():
    if session.get('email') != None:
        return render_template('gameset.html',email = session['email'])

    return render_template('index.html',email = None)

@app.route("/tester/<string:email>")
def testing(email):
    session['email'] = email
    return jsonify({"status":"success"}),200

@app.route("/register")
def register():
    if session.get('email') != None:
        return render_template('gameset.html',email = session['email'])

    return render_template('index.html',email = None)

@app.route("/registration",methods=["POST"])
def registration():
    db = cluster['users']
    reg = {}
    reg['user']=request.form.get("uname")
    reg['email']=request.form.get("email")
    reg['password']=request.form.get("password")
    
    if db.find_one({"user":reg['user']}) != None:
        flash('User already exists')
        return render_template('index.html',email = None)
    elif db.find_one({"email":reg['email']}) != None:
        flash('User already exists')
        return render_template('index.html',email = None)

    db.insert_one(reg)


    flash('registered successfully')
    return render_template('login.html',email=None)

@app.route("/loginpage",methods=["POST","GET"])
def loginpage():
    if session.get('email') != None:
        return render_template('gameset.html',email = session['email'])

    return render_template('login.html',email = None)

@app.route("/gameset",methods=["GET","POST"])
def gameset():
    if session.get('email') == None:
        return render_template('login.html',email = None)
    return render_template('gameset.html',email = session['email'])

@app.route("/logout",methods=["GET","POST"])
def logout():
    session.clear()
    return redirect(url_for('loginpage'))

@app.route("/login",methods=["POST"])
def login():
    db = cluster['users']
    mail = request.form.get("email")
    reg = {'email':mail}
    user = db.find_one(reg)

    if user!=None and user['password'] == request.form.get("password"):
        session['email'] = mail
        return render_template('gameset.html',email = session['email'])

    flash('Invalid credentials entered')
    return render_template('login.html',email = None)

@app.route("/game",methods=["POST","GET"])
def game():
    gen = DocumentGenerator()
    if session.get('email') == None:
        return render_template('index.html',email=None)
    points = request.args.get("points")
    points = int(points)
    print("Points =",points)
    buffer = gen.gen_sentence(max_words=points)
    # sentence = buffer
    sentence = ""
    i=0
    for b in buffer:
        sentence += "<span id='pe"+str(i)+"'>"+b+"</span>"
        i = i+1
    return render_template('game.html',email=session['email'],sentence=sentence,length=len(buffer),bufferSentence=buffer)

@app.route("/gameover/<string:sec>/<string:object>",methods=["POST","GET"])
def gameover(sec,object):
    print("object =", object)
    object = json.loads(object)
    frame = pd.DataFrame(object)

    max = len(frame['char'])
    score = frame['hit'].sum()
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    date_time = datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%S.000Z")
    db = cluster['scores']
    print("max =",max,", score =",score,", time stamp =",sec)
    db.insert_one({"email": session['email'], "total": int(max), "scored": int(score), "timestamp": date_time,"completion": sec+" sec"})
    scores = db.find({"email": session['email']}).sort([('timestamp', -1)]).limit(10)  
    if scores != None:
        scores = list(scores)
        scores = pd.DataFrame(scores)
    else:
        scores = pd.DataFrame([["NA", 0, 0, sec]], columns=["email", "total", "scored", "timestamp"])

    # scores = scores.sort_values(by='timestamp', ascending=False)
    # scores = scores.head(10)
    print(scores)

    maximums = scores['total'].tolist()
    scored = scores['scored'].tolist()
    times = scores['completion'].tolist()
    plt = copymodule(plot)
    # plt = copy.deepcopy(plot)
    plt.figure()
    print("address of plt 1",hex(id(plt)))
    # plt = plot
    print("total =",maximums)
    print("score =",scored)
    x_pos = [i for i, _ in enumerate(maximums)]
    plt.bar(x_pos,scored)
    plt.xticks(x_pos, maximums)
    plt.title('score of last ten games')
    plt.xlabel('Total')
    plt.ylabel("Scored")

    for i in range(len(maximums)):
        plt.annotate(times[i], xy=(x_pos[i],scored[i]), ha='center', va='bottom')
    
    # plt.show();
    data = 'data:image/png;base64,' + image_data(plt)

    frame = frame[(frame['char'] != "")]
    uni = frame['char'].unique()

    char,total,scored = [],[],[]
    for un in uni:
        tot = len(frame[(frame['char'] == un)])
        sc= frame[(frame['char'] == un)]['hit'].sum()
        char.append(un)
        total.append(tot)
        scored.append(sc)
    d = {"char":char,"total":total,"scored":scored}
    d = pd.DataFrame(d)
    d.sort_values(by="scored")
    char, score, total = d["char"].tolist(),d["scored"].tolist(),d["total"].tolist()
    cplt = copymodule(plot)
    # cplt = copy.deepcopy(plot)
    cplt.figure()
    print("address of plt 2",hex(id(cplt)))
    # cplt = plot
    print("total =",total)
    print("score =",score)
    x_pos = [i for i, _ in enumerate(total)]
    cplt.bar(x_pos,score)
    cplt.xticks(x_pos, total)
    cplt.xlabel('Total')
    cplt.ylabel("Scored")
    cplt.title('This game\'s result')

    for i in range(len(score)):
        cplt.annotate(char[i], xy=(x_pos[i],score[i]), ha='center', va='bottom')
    # cplt.show()
    cdata = 'data:image/png;base64,' + image_data(cplt)

    return render_template('gameover.html',email=session['email'],games=data,data=cdata,time=sec+" sec")

def copymodule(old):
    new = type(old)(old.__name__, old.__doc__)
    new.__dict__.update(old.__dict__)
    return new

def image_data(plt):
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return data