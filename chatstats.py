#!/usr/bin/python
# -*- coding: utf-8 -*-

from chat_downloader import ChatDownloader
from flask import Flask, request, render_template, jsonify
from re import sub, search
from multiprocessing import Process
import os
import sqlite3
import logging
import requests

def clean_msg(msg):
    i = 'áÁàÀâÂãÃåÅçÇéÉèÈêÊëËíÍìÌîÎïÏñÑóÓòÒôÔõÕúÚùÙûÛ'
    o = 'aAaAaAaAaAcCeEeEeEeEiIiIiIiInNoOoOoOoOuUuUuU'
    transtab = str.maketrans(i, o)
    msg = msg.lower()                   # transform to lower case
    msg = msg.translate(transtab)       # replace common characters with accents
    msg = sub(':[a-z_]+:', '', msg)     # remove emojis
    msg = msg.strip()                   # remove spaces at the beginning and at the end
    return msg

def get_db():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db', 'chat.db')

def download_chat(url,lockfile_abspath):
    if os.path.exists(lockfile_abspath):
        return

    with open(lockfile_abspath,'w') as lockfile:
        lockfile.write(str(os.getpid()) + chr(31) + url)

    try:
        db = get_db()
        if os.path.exists(db):
            os.remove(db)
        if not os.path.exists(os.path.dirname(db)):
            os.mkdir(os.path.dirname(db))
        con = sqlite3.connect(db, isolation_level = None)
        cur = con.cursor()

        cur.execute('CREATE TABLE messages (unix_time integer, author_id text, author_name text, message_type text, message text, status text)')

        chat = ChatDownloader().get_chat(url)
        for row in chat:
            clean_message = clean_msg(row['message'])
            if len(clean_message) != 0:
                cur.execute('INSERT INTO messages (unix_time, author_id, author_name, message_type, message, status) VALUES (?, ?, ?, ?, ?, ?)', [int(row['timestamp']),row['author']['id'],row['author']['name'],row['message_type'],clean_message,'C'])

        con.close()
    except KeyboardInterrupt:
        pass
    finally:
        if os.path.exists(lockfile_abspath):
            os.remove(lockfile_abspath)

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        lockfile_abspath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chatdownload.lock')
        if os.path.exists(lockfile_abspath):
            with open(lockfile_abspath,'r') as lockfile:
                lockinfo = lockfile.readline().split(chr(31),1)
                return render_template('chatstats.html', url = lockinfo[1], locked = True)
        else:
            p = Process(target=download_chat, args=(request.form['url'],lockfile_abspath))
            p.start()
            return render_template('chatstats.html', url = request.form['url'])
    else:
        return render_template('index.html')

@app.route("/archive_messages")
def archive_messages():
    db = get_db()
    con = sqlite3.connect(db, isolation_level = None)
    cur = con.cursor()
    cur.execute("UPDATE messages SET status = 'A' WHERE status = 'C'")
    total_changes = con.total_changes
    con.close()
    return str(total_changes) + ' messages have been archived.'

@app.route("/get_current_top_10")
def get_current_top_10():
    db = get_db()
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

if __name__ == '__main__':
    logfile_abspath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log', 'chatstats.log')
    if not os.path.exists(os.path.dirname(logfile_abspath)):
        os.mkdir(os.path.dirname(logfile_abspath))
    logging.basicConfig(filename=logfile_abspath, filemode='w', level=logging.INFO)

    os.environ['FLASK_ENV'] = 'development'
    app.run(host='localhost', port=5000, debug=False)
