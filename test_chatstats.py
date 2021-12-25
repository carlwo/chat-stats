#!/usr/bin/python
# -*- coding: utf-8 -*-

import pytest
import chatstats as cs
import os
from time import sleep

def test_clean_msg():
    assert cs.clean_msg(" Test ") == "Test"
    assert cs.clean_msg("Test :cat:") == "Test"

def test_time2seconds():
    assert cs.time2seconds("","","") == None
    assert cs.time2seconds() == None
    assert cs.time2seconds("2","","") == 2*60*60
    assert cs.time2seconds("","3","") == 3*60
    assert cs.time2seconds("","","4") == 4
    assert cs.time2seconds("4","3","") == 4*60*60 + 3*60
    assert cs.time2seconds("","3","2") == 3*60 + 2
    assert cs.time2seconds("4","","2") == 4*60*60 + 2

def test_levenshtein_distance():
    assert cs.levenshtein_distance("Test","test") == 1
    assert cs.levenshtein_distance("Test1","test") == 2
    assert cs.levenshtein_distance("Test!","Test") == 1
    assert cs.levenshtein_distance("!Test!","Test") == 2
    
def test_is_similar():
    assert cs.is_similar("Test","test")
    assert cs.is_similar("Test","Test!")
    assert not cs.is_similar("test","Test!","sensitive",1)
    assert cs.is_similar("test","Test!","sensitive",2)
    assert cs.is_similar("test","TEST!","insensitive",1)

@pytest.fixture
def client():
    app = cs.create_app()
    with app.test_client() as client:
        yield client

def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.data
    assert b'<input type="text" name="url"' in html
    assert b'<input type="radio" name="broadcast_type" value="livestream"' in html
    assert b'<input type="radio" name="broadcast_type" value="past_broadcast"' in html
    assert b'<input type="text" name="start_hh" id="start_hh"' in html
    assert b'<input type="text" name="start_mm" id="start_mm"' in html
    assert b'<input type="text" name="start_ss" id="start_ss"' in html
    assert b'<input type="text" name="end_hh" id="end_hh"' in html
    assert b'<input type="text" name="end_mm" id="end_mm"' in html
    assert b'<input type="text" name="end_ss" id="end_ss"' in html
    assert b'<input type="radio" name="chat_type" value="live"' in html
    assert b'<input type="radio" name="chat_type" value="top"' in html
    assert b'<button class="button is-link">Continue</button>' in html

def test_past_broadcast_youtube(client):
    config =  cs.get_config()
    response = client.post('/', data={'url': 'https://www.youtube.com/watch?v=fXvIn_nz7UA',
                                      'broadcast_type': 'past_broadcast',
                                      'chat_type': 'top',
                                      'start_hh': '', 'start_mm': '27', 'start_ss': '18',
                                      'end_hh': '', 'end_mm': '29', 'end_ss': '00'})
    assert response.status_code == 200
    assert os.path.exists(config["download_lock"])
    assert os.path.exists(config["db"])
    assert os.path.exists(config["logfile"])
    html = response.data
    assert b'<div id="stats"></div>' in html
    assert b'<div id="btn"><button class="button is-success" onclick="start()">Start</button></div>' not in html
    
    sleep(5)
    assert not os.path.exists(config["download_lock"])
    
    response = client.get('/get_current_top_10')
    assert response.status_code == 200
    json = response.json
    assert json[0]["message"] == "Berge des Wahnsinns"
    assert json[0]["count"] == 12
    assert json[0]["total_count"] == 56
    assert json[0]["percent"] == 21.429
