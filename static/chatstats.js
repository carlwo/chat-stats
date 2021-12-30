function sanitizeHTML(text) {
  var element = document.createElement('div');
  element.innerText = text;
  return element.innerHTML;
}

function update_stats(data) {
    if (data.length == 0) { return; }
    var output = data[0]['total_count'] + ' messages<br><table class="table top10 is-striped is-hoverable is-narrow is-fullwidth">';
    data.forEach(row => output += '<tr><td><progress class="progress is-info" value="' + row['count'] + '" max="' + row['total_count'] + '"></progress></td><td>' + row['count'] + '<span class="icon"><i class="bi bi-person"></i></span></td><td>' + row['percent'].toFixed(1) + '&#8202;%</td><td>' + sanitizeHTML(row['message']) + '<span class="details">&nbsp;' + sanitizeHTML(row['details']) + '</span></td></tr>');
    output += '</table>';
    document.getElementById('stats').innerHTML = output;
}

function fetch_stats() {
    if (document.getElementById('radio_sensitive').checked) {
        case_sensitivity = 'sensitive';
    } else {
        case_sensitivity = 'insensitive';
    }
    max_distance = document.getElementById('max_distance').value;
    fetch('get_current_top_10/' + case_sensitivity + '/' + max_distance)
      .then(response => response.json())
      .then(data => update_stats(data));
}

var intervalID;

function start(broadcast_type = 'live') {
    if (broadcast_type == 'live') {
        fetch('archive_messages');
        document.getElementById('btn').innerHTML = '<button class="button is-danger" onclick="stop()"><span class="icon"><i class="bi bi-stop-circle"></i></span><span class="text">Stop</span></button>';
    }
    document.getElementById('stats').innerHTML = '<br><table class="table top10 is-striped is-narrow"><tr><td><progress class="progress is-info" max="100"></progress></td><td>gathering chat messages...</td></tr></table>';
    intervalID = setInterval(fetch_stats, 1500);
}

function stop() {
    clearInterval(intervalID);
    document.getElementById('btn').innerHTML = '<button class="button is-success" onclick="start()"><span class="icon"><i class="bi bi-play-circle"></i></span><span class="text">Start</span></button>';
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
        document.getElementById('time-input').style.display = "table";
    } else {
        document.getElementById('time-input').style.display = "none";
    }
}

function show_group_members(option) {
    if (option == 'yes') {
        document.querySelector(':root').style.setProperty('--display-details', 'inline-block');
    } else {
        document.querySelector(':root').style.setProperty('--display-details', 'none');
    }
}
