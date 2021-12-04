function sanitizeHTML(text) {
  var element = document.createElement('div');
  element.innerText = text;
  return element.innerHTML;
}

function update_stats(data) {
    if (data.length == 0) { return; }
    var output = 'number of messages: ' + data[0][2] + '<br><table class="table top10 is-striped is-narrow">';
    data.forEach(row => output += '<tr><td><progress class="progress is-info" value="' + row[1] + '" max="' + row[2] + '"></progress></td><td>' + row[1] + '</td><td>' + row[3].toFixed(1) + '%</td><td>' + sanitizeHTML(row[0]) + '</td></tr>');
    output += '</table>';
    document.getElementById('stats').innerHTML = output;
}

function fetch_stats() {
    fetch('get_current_top_10')
      .then(response => response.json())
      .then(data => update_stats(data));
}

function fetch_title(url) {
    fetch('get_title', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(url)})
      .then(response => response.json())
      .then(title => document.getElementById('subtitle').innerText = title);
}

var intervalID;

function start() {
    fetch('archive_messages');
    document.getElementById('btn').innerHTML = '<button class="button is-danger" onclick="stop()">Stop</button>';
    document.getElementById('stats').innerHTML = '<br><table class="table top10 is-striped is-narrow"><tr><td><progress class="progress is-info" max="100"></progress></td><td>gathering chat messages...</td></tr></table>';
    intervalID = setInterval(fetch_stats, 2000);
}

function stop() {
    clearInterval(intervalID);
    document.getElementById('btn').innerHTML = '<button class="button is-success" onclick="start()">Start</button>';
}

function hide_notification(notification_id) {
    document.getElementById('notification_' + notification_id).style.display = "none";
}

function to_time(text) {
    num = text.replace(/[^0-9]/g, '');
    return (num > 59) ? "59" : num;
}

function check_broadcast_type() {
    if (document.getElementById('radio_past_broadcast').checked) {
        document.getElementById('time_input').style.display = "table";
    } else {
        document.getElementById('time_input').style.display = "none";
    }
}
