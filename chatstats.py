#!/usr/bin/python
# -*- coding: utf-8 -*-

from chat_downloader import ChatDownloader
from flask import Flask, request, render_template, jsonify, redirect, url_for
from re import sub, search
from multiprocessing import Process
from time import sleep
import os
import sqlite3
import logging
import requests

def get_config(param = None):
    filedir = os.path.dirname(os.path.abspath(__file__))
    config = {"db": os.path.join(filedir, 'db', 'chat.db'),
              "logfile": os.path.join(filedir, 'log', 'chatstats.log'),
              "download_lock": os.path.join(filedir, 'download.lock'),
              "exit_lock": os.path.join(filedir, 'exit.lock')}
    return config[param] if param else config

def clean_msg(msg):
    i = 'áÁàÀâÂãÃåÅçÇéÉèÈêÊëËíÍìÌîÎïÏñÑóÓòÒôÔõÕúÚùÙûÛ'
    o = 'aAaAaAaAaAcCeEeEeEeEiIiIiIiInNoOoOoOoOuUuUuU'
    transtab = str.maketrans(i, o)
    msg = msg.lower()                   # transform to lower case
    msg = msg.translate(transtab)       # replace common characters with accents
    msg = sub(':[a-z_]+:', '', msg)     # remove emojis
    msg = msg.strip()                   # remove spaces at the beginning and at the end
    return msg

def download_chat(url):
    config = get_config()

    if os.path.exists(config["download_lock"]):
        return

    with open(config["download_lock"],'w') as lockfile:
        lockfile.write(str(os.getpid()) + chr(31) + url)

    try:
        if os.path.exists(config["db"]):
            os.remove(config["db"])
        if not os.path.exists(os.path.dirname(config["db"])):
            os.mkdir(os.path.dirname(config["db"]))
        con = sqlite3.connect(config["db"], isolation_level = None)
        cur = con.cursor()
        
        cur.execute('PRAGMA journal_mode = OFF')
        cur.execute('CREATE TABLE messages (unix_time integer, author_id text, author_name text, message_type text, message text, status text)')
        
        chat = ChatDownloader().get_chat(url)
        for row in chat:
            if os.path.exists(config["exit_lock"]) or not os.path.exists(config["download_lock"]):
                break
            clean_message = clean_msg(row['message'])
            if len(clean_message) != 0:
                cur.execute('INSERT INTO messages (unix_time, author_id, author_name, message_type, message, status) VALUES (?, ?, ?, ?, ?, ?)',
                                [int(row['timestamp']),row['author']['id'],row['author']['name'],row['message_type'],clean_message,'C'])
        
        con.close()
    except KeyboardInterrupt:
        pass
    finally:
        if os.path.exists(config["exit_lock"]):
            os.remove(config["exit_lock"])
        if os.path.exists(config["download_lock"]):
            os.remove(config["download_lock"])

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    download_lock = get_config("download_lock")
    if request.method == 'POST':
        if os.path.exists(download_lock):
            with open(download_lock,'r') as lockfile:
                lockinfo = lockfile.readline().split(chr(31),1)
                return render_template('chatstats.html', url = lockinfo[1], locked = True)
        else:
            p = Process(target=download_chat, args=(request.form['url'],))
            p.start()
            return render_template('chatstats.html', url = request.form['url'])
    else:
        return render_template('index.html')

@app.route("/archive_messages")
def archive_messages():
    db = get_config("db")
    con = sqlite3.connect(db, isolation_level = None)
    cur = con.cursor()
    cur.execute('PRAGMA journal_mode = OFF')
    cur.execute("UPDATE messages SET status = 'A' WHERE status = 'C'")
    total_changes = con.total_changes
    con.close()
    return jsonify(str(total_changes) + ' messages have been archived.')

@app.route("/get_current_top_10")
def get_current_top_10():
    db = get_config("db")
    con = sqlite3.connect(db, isolation_level = None)
    cur = con.cursor()
    cur.execute(''' 
        WITH filtered_messages AS
		(SELECT DISTINCT author_id, message FROM messages WHERE status = 'C')
		SELECT 
            m.message,
            m.cnt,
            t.total_cnt,
            round(100.0*m.cnt/t.total_cnt,1) pct
        FROM
        (SELECT message, count(*) cnt FROM filtered_messages GROUP BY message) m
        CROSS JOIN
        (SELECT count(*) total_cnt FROM filtered_messages) t
        ORDER BY m.cnt desc
        LIMIT 10''')
    result = cur.fetchall()
    con.close()
    return jsonify(result)

@app.route("/get_title", methods=['POST'])
def get_title():
    url = request.json
    match = search(r'<title[^>]*>([^<]+)</title>', requests.get(url).text)
    return jsonify(match.group(1) if match else request.json)

@app.route("/exit")
def exit():
    config = get_config()

    if os.path.exists(config["download_lock"]):
        with open(config["exit_lock"],'w') as lockfile:
            pass
    return redirect(url_for('index'))

if __name__ == '__main__':
    logfile = get_config("logfile")
    if not os.path.exists(os.path.dirname(logfile)):
        os.mkdir(os.path.dirname(logfile))
    logging.basicConfig(filename=logfile, filemode='w', level=logging.INFO)

    print("[INFO] Press CTRL+C to quit.")

    os.environ['FLASK_ENV'] = 'development'
    app.run(host='0.0.0.0', port=5000, debug=False)
