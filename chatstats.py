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
    global DB, DOWNLOAD_LOCK
    
    if os.path.exists(DOWNLOAD_LOCK):
        return

    with open(DOWNLOAD_LOCK,'w') as lockfile:
        lockfile.write(str(os.getpid()) + chr(31) + url)

    try:
        if os.path.exists(DB):
            os.remove(DB)
        if not os.path.exists(os.path.dirname(DB)):
            os.mkdir(os.path.dirname(DB))
        con = sqlite3.connect(DB, isolation_level = None)
        cur = con.cursor()
        
        cur.execute('PRAGMA journal_mode = OFF')
        cur.execute('CREATE TABLE messages (unix_time integer, author_id text, author_name text, message_type text, message text, status text)')
        
        chat = ChatDownloader().get_chat(url)
        for row in chat:
            clean_message = clean_msg(row['message'])
            if len(clean_message) != 0:
                cur.execute('INSERT INTO messages (unix_time, author_id, author_name, message_type, message, status) VALUES (?, ?, ?, ?, ?, ?)',
                                [int(row['timestamp']),row['author']['id'],row['author']['name'],row['message_type'],clean_message,'C'])
        
        con.close()
    except KeyboardInterrupt:
        pass
    finally:
        if os.path.exists(DOWNLOAD_LOCK):
            os.remove(DOWNLOAD_LOCK)

def manage_download(url):
    global DOWNLOAD_LOCK, EXIT_LOCK
    
    try:
        d = Process(target=download_chat, args=(url,), daemon=True)
        d.start()
        while d.is_alive():
            sleep(1)
            if os.path.exists(EXIT_LOCK) or not os.path.exists(DOWNLOAD_LOCK):
                d.terminate()
                d.join()
    except KeyboardInterrupt:
        pass
    finally:
        if os.path.exists(DOWNLOAD_LOCK):
            os.remove(DOWNLOAD_LOCK)
        if os.path.exists(EXIT_LOCK):
            os.remove(EXIT_LOCK)

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    global DOWNLOAD_LOCK
    if request.method == 'POST':
        if os.path.exists(DOWNLOAD_LOCK):
            with open(DOWNLOAD_LOCK,'r') as lockfile:
                lockinfo = lockfile.readline().split(chr(31),1)
                return render_template('chatstats.html', url = lockinfo[1], locked = True)
        else:
            p = Process(target=manage_download, args=(request.form['url'],))
            p.start()
            return render_template('chatstats.html', url = request.form['url'])
    else:
        return render_template('index.html')

@app.route("/archive_messages")
def archive_messages():
    global DB
    con = sqlite3.connect(DB, isolation_level = None)
    cur = con.cursor()
    cur.execute('PRAGMA journal_mode = OFF')
    cur.execute("UPDATE messages SET status = 'A' WHERE status = 'C'")
    total_changes = con.total_changes
    con.close()
    return str(total_changes) + ' messages have been archived.'

@app.route("/get_current_top_10")
def get_current_top_10():
    global DB
    con = sqlite3.connect(DB, isolation_level = None)
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
    global EXIT_LOCK, DOWNLOAD_LOCK
    if os.path.exists(DOWNLOAD_LOCK):
        with open(EXIT_LOCK,'w') as lockfile:
            pass
    return redirect(url_for('index'))

if __name__ == '__main__':
    # set global constants
    FILEDIR = os.path.dirname(os.path.abspath(__file__))
    DB            = os.path.join(FILEDIR, 'db', 'chat.db')
    LOGFILE       = os.path.join(FILEDIR, 'log', 'chatstats.log')
    DOWNLOAD_LOCK = os.path.join(FILEDIR, 'download.lock')
    EXIT_LOCK     = os.path.join(FILEDIR, 'exit.lock')

    if not os.path.exists(os.path.dirname(LOGFILE)):
        os.mkdir(os.path.dirname(LOGFILE))
    logging.basicConfig(filename=LOGFILE, filemode='w', level=logging.INFO)

    os.environ['FLASK_ENV'] = 'development'
    app.run(host='0.0.0.0', port=5000, debug=False)
