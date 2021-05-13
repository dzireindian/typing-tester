from flask import Flask,render_template,request,session,redirect,url_for,flash
from flask_session import Session
from datetime import datetime
from essential_generators import DocumentGenerator
from io import BytesIO

import pymongo
import os
import json
import base64

import pandas as pd
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


@app.route("/")
def index():
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

@app.route("/login",methods=["POST"])
def login():
    db = cluster['users']
    mail = request.form.get("email")
    reg = {'email':mail}
    user = db.find_one(reg)

    if user!=None and user['password'] == request.form.get("password"):
        session['email'] = mail
        return render_template('gameset.html',email = None)

    flash('Invalid credentials entered')
    return render_template('login.html',email = None)

@app.route("/game",methods=["POST","GET"])
def game():
    gen = DocumentGenerator()
    if session['email'] == None:
        return render_template('index.html',email=None)
    points = request.args.get("points")
    points = int(points)
    print("Points =",points)
    buffer = gen.gen_sentence(max_words=points)
    sentence = buffer
    # sentence = ""
    # i=0
    # for b in buffer:
    #     sentence += "<span id='pe"+str(i)+"'>"+b+"</span>"
    #     i = i+1
    return render_template('game.html',email=session['email'],sentence=sentence,length=len(buffer))

@app.route("/gameover/<object>",methods=["POST","GET"])
def gameover(object):
    object = json.loads(object)
    frame = pd.DataFrame(object)

    max = len(frame['char'])
    score = frame['hit'].sum()
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    date_time = datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%S.000Z")
    db = cluster['scores']
    db.insert_one({"email":session['email'],"total":max,"scored":score,"timestamp":date_time})
    scores = db.find({"email":session['email']})
    if scores != None:
        scores = list(scores)
        scores = pd.DataFrame(scores)
    else:
        scores = pd.DataFrame([["NA",0,0,date_time]],columns=["email","total","scored","timestamp"])

    scores = scores.head(10)
    scores = scores.sort_values(by='timestamp',ascending=True)

    maximums = scores['total'].tolist()
    scored = scores['scored'].tolist()
    times = scores['timestamp'].tolist()
    plt = plot
    fig, ax = plt.subplots(figsize=(9, 4))
    style = dict(size=10, color='black')
    plt.fill_between(maximums, scored, capstyle='round', joinstyle='round')
    for i in range(len(scored)):
        ax.text(maximums[i], scored[i], times[i], **style)
    ax.set(title=' total vs scored', xlabel='total',
           ylabel='scored')
    
    data = 'data:image/png;base64,'+image_data(plt)

    uni = frame['char'].unique()
    x,y = [], []
    for un in uni:
        total = frame[(frame['char'] == un)].sum()
        x.append(un)
        y.append(total)
    plt.bar(x,y)
    cdata = 'data:image/png;base64,'+image_data(plt)

    return render_template('gameover.html',email=session['email'],games=data,data=cdata)

def image_data(plt):
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return data