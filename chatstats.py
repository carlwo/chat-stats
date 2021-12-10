#!/usr/bin/python
# -*- coding: utf-8 -*-

from chat_downloader import ChatDownloader, errors
from flask import Flask, request, render_template, jsonify, redirect, url_for
from re import sub, search
from multiprocessing import Process, Pipe
from time import sleep
import os
import sqlite3
import logging

def get_config(param = None):
    filedir = os.path.dirname(os.path.abspath(__file__))
    config = {"db": os.path.join(filedir, 'db', 'chat.db'),
              "logfile": os.path.join(filedir, 'log', 'chatstats.log'),
              "download_lock": os.path.join(filedir, 'download.lock'),
              "exit_lock": os.path.join(filedir, 'exit.lock')}
    return config[param] if param else config

def clean_msg(msg):
    """Used to clean a chat message before inserting it into the database."""
    i = 'áÁàÀâÂãÃåÅçÇéÉèÈêÊëËíÍìÌîÎïÏñÑóÓòÒôÔõÕúÚùÙûÛ'
    o = 'aAaAaAaAaAcCeEeEeEeEiIiIiIiInNoOoOoOoOuUuUuU'
    transtab = str.maketrans(i, o)
    msg = msg.lower()                   # transform to lower case
    msg = msg.translate(transtab)       # replace common characters with accents
    msg = sub(':[a-z_]+:', '', msg)     # remove emojis
    msg = msg.strip()                   # remove spaces at the beginning and at the end
    return msg

def download_chat(pipe,url,broadcast_type,start_time,end_time,chat_type):
    """Retrieve the chat massages and insert them into the database."""
    config = get_config()

    try:
        if os.path.exists(config["db"]):
            os.remove(config["db"])
        if not os.path.exists(os.path.dirname(config["db"])):
            os.mkdir(os.path.dirname(config["db"]))

        con = sqlite3.connect(config["db"], isolation_level = None)
        cur = con.cursor()

        cur.execute('PRAGMA journal_mode = OFF')
        cur.execute('CREATE TABLE messages (unix_time integer, author_id text, author_name text, message_type text, message text, status text)')

        chat = ChatDownloader().get_chat(url=url, start_time=start_time, end_time=end_time, chat_type=chat_type)
        with open(config["download_lock"],'w') as lockfile:
            lockfile.write(str(os.getpid()) + chr(31) + broadcast_type + chr(31) + chat.title + chr(31) + url)
        pipe.send({"status":"OK", "message":chat.title})
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
    except (errors.URLNotProvided, errors.ChatGeneratorError, errors.SiteNotSupported, errors.InvalidURL, errors.NoChatReplay) as ex:
        pipe.send({"status":"ERROR", "message":str(ex)})
    finally:
        pipe.close()
        if os.path.exists(config["exit_lock"]):
            os.remove(config["exit_lock"])
        if os.path.exists(config["download_lock"]):
            os.remove(config["download_lock"])

def get_time_in_seconds(hh,mm,ss):
    if len(hh) == 0 and len(mm) == 0 and len(ss) == 0:
        return None
    else:
        return int("0" + hh) * 60 * 60 + int("0" + mm) * 60 + int("0" + ss)

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    download_lock = get_config("download_lock")
    if request.method == 'POST':
        if os.path.exists(download_lock):
            with open(download_lock,'r') as lockfile:
                lockinfo = lockfile.readline().split(chr(31),3)
                return render_template('chatstats.html', url = lockinfo[3], broadcast_type = lockinfo[1], status = "OK", message = lockinfo[2], locked = True)
        else:
            url = request.form['url']
            broadcast_type = request.form['broadcast_type']
            start_time = get_time_in_seconds(request.form['start_hh'],request.form['start_mm'],request.form['start_ss']) if broadcast_type == "past_broadcast" else None
            end_time = get_time_in_seconds(request.form['end_hh'],request.form['end_mm'],request.form['end_ss']) if broadcast_type == "past_broadcast" else None
            chat_type = request.form['chat_type']
            parent, child = Pipe()
            p = Process(target=download_chat, args=(child,url,broadcast_type,start_time,end_time,chat_type,))
            p.start()
            p_response = parent.recv()
            return render_template('chatstats.html', url = url, broadcast_type = broadcast_type, status = p_response["status"], message = p_response["message"])
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
