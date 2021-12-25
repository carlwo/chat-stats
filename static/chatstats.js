function sanitizeHTML(text) {
  var element = document.createElement('div');
  element.innerText = text;
  return element.innerHTML;
}

function update_stats(data) {
    if (data.length == 0) { return; }
    var output = 'number of messages: ' + data[0]['total_count'] + '<br><table class="table top10 is-striped is-narrow">';
    data.forEach(row => output += '<tr><td><progress class="progress is-info" value="' + row['count'] + '" max="' + row['total_count'] + '"></progress></td><td>' + row['count'] + '<span class="icon"><i class="bi bi-person"></i></span></td><td>' + row['percent'].toFixed(1) + '&#8202;%</td><td>' + sanitizeHTML(row['message']) + '</td></tr>');
    output += '</table>';
    document.getElementById('stats').innerHTML = output;
}

function fetch_stats() {
    fetch('get_current_top_10')
      .then(response => response.json())
      .then(data => update_stats(data));
}

var intervalID;

function start(broadcast_type = 'live') {
    if (broadcast_type == 'live') {
        fetch('archive_messages');
        document.getElementById('btn').innerHTML = '<button class="button is-danger" onclick="stop()">Stop</button>';
    }
    document.getElementById('stats').innerHTML = '<br><table class="table top10 is-striped is-narrow"><tr><td><progress class="progress is-info" max="100"></progress></td><td>gathering chat messages...</td></tr></table>';
    intervalID = setInterval(fetch_stats, 1500);
}

function stop() {
    clearInterval(intervalID);
    document.getElementById('btn').innerHTML = '<button class="button is-success" onclick="start()">Start</button>';
}

function hide_notification(notification_id) {
    document.getElementById('notification_' + notification_id).style.display = "none";
}

function to_time(text, next_input_id) {
    num = text.replace(/[^0-9]/g, '');
    if ((next_input_id) && (num.length >= 2)) {
        document.getElementById(next_input_id).focus();
    }
    return (num > 59) ? "59" : num;
}

function check_broadcast_type() {
    if (document.getElementById('radio_past_broadcast').checked) {
        document.getElementById('time_input').style.display = "table";
    } else {
        document.getElementById('time_input').style.display = "none";
    }
}
