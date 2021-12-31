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

def time2seconds(hh="",mm="",ss=""):
    if len(hh) == 0 and len(mm) == 0 and len(ss) == 0:
        return None
    else:
        return int("0" + hh) * 60 * 60 + int("0" + mm) * 60 + int("0" + ss)

def levenshtein_distance(s, t):
    ''' Compute the Levenshtein distance between s and t.
        For mor information see: https://en.wikipedia.org/wiki/Levenshtein_distance
    '''
    if len(s) > len(t):
        s, t = t, s
    v0 = list(range(len(t) + 1))
    for i,x in enumerate(s):
        v1 = [i+1]
        for j,y in enumerate(t):
            v1.append(min((v0[j + 1] + 1, v1[j] + 1, v0[j] if x == y else v0[j] + 1)))
        v0 = v1
    return v0[-1]

def is_similar(s, t, case_sensitivity = "insensitive", max_distance = 1):
    ''' Return True if s is similar to t. '''
    if case_sensitivity == "insensitive":
        s, t = s.lower(), t.lower()
    if abs(len(s)-len(t)) > max_distance:
        return False
    elif s == t:
        return True
    else:
        return (levenshtein_distance(s, t) <= max_distance)

def clean_msg(message):
    """ Remove emojis and leading/trailing white spaces from message."""
    message = sub(':[a-z_]+:', '', message)  # remove emojis
    message = message.strip()                # remove spaces at the beginning and at the end
    return message

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
            lockfile.write(str(os.getpid()) + chr(31) + broadcast_type + chr(31) + chat.title.replace(chr(31),"") + chr(31) + url.replace(chr(31),""))
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

def create_app():
    app = Flask(__name__)
    
    logfile = get_config("logfile")
    if not os.path.exists(os.path.dirname(logfile)):
        os.mkdir(os.path.dirname(logfile))
    logging.basicConfig(filename=logfile, filemode='w', level=logging.INFO)
    
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
                start_time = time2seconds(request.form['start_hh'],request.form['start_mm'],request.form['start_ss']) if broadcast_type == "past_broadcast" else None
                end_time = time2seconds(request.form['end_hh'],request.form['end_mm'],request.form['end_ss']) if broadcast_type == "past_broadcast" else None
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

    @app.route("/get_current_top_10/<string:case_sensitivity>/<int:max_distance>")
    def get_current_top_10(case_sensitivity, max_distance):
        db = get_config("db")
        con = sqlite3.connect(db, isolation_level = None)
        cur = con.cursor()
        data = cur.execute(''' 
            WITH current_messages AS (SELECT unix_time, author_id, message FROM messages WHERE status = 'C')
            SELECT base.message, count(*) cnt
            FROM current_messages base
            JOIN (SELECT author_id, max(unix_time) AS max_unix_time FROM current_messages GROUP BY author_id) sub
            ON base.author_id = sub.author_id AND base.unix_time = sub.max_unix_time
            GROUP BY base.message
            ORDER BY count(*) DESC, max(base.unix_time) DESC''')
        result = []
        total_count = 0
        for row in data:
            for result_row in result:
                if is_similar(row[0], result_row["message"], case_sensitivity, max_distance):
                    result_row["details"] += ", " + row[0] + " ("+str(row[1])+")"
                    result_row["count"] += row[1]
                    total_count += row[1]
                    break
            else:
                result.append({"message":row[0],"details":"("+str(row[1])+")","count":row[1]})
                total_count += row[1]
    
        con.close()
        result.sort(key = lambda row: row["count"], reverse=True)
        return jsonify([{**row , "percent":round(100.0*row["count"]/total_count,3), "total_count":total_count} for row in result[:10]])

    @app.route("/exit")
    def exit():
        config = get_config()
        if os.path.exists(config["download_lock"]):
            with open(config["exit_lock"],'w') as lockfile:
                pass
        return redirect(url_for('index'))
        
    return app

if __name__ == '__main__':
    print("[INFO] Press CTRL+C to quit.")
    os.environ['FLASK_ENV'] = 'development'
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
