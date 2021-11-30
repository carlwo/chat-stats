# Chat Stats
A small tool to retrieve statistics about chat messages from livestreams and past broadcasts from YouTube, Twitch or Reddit.

## Installation

This application requires [Python 3](https://www.python.org/), [Flask](https://palletsprojects.com/p/flask/) and the [Chat-Downloader](https://github.com/xenova/chat-downloader). If you already have python, you can install the rest with the following commands:

    pip install Flask
    pip install chat-downloader

Alternatively, you can build a docker container for the app with the following command:

    docker-compose build

## Usage

Execute the script chatstats.py to start a server on port 5000:

    python chatstats.py

Or start the docker container:

    docker-compose up -d

Then open up your favorite browser and navigate to [http://localhost:5000](http://localhost:5000).

On the index page you will be asked to enter a URL of a livestream or past broadcast from YouTube, Twitch or Reddit.

## Statistics

After gathering the chat messages from the given stream, a top 10 statistic of the most frequent chat messages will be shown. Duplicate messages from the same author will be ignored.

This is particularly useful when a question is asked during a livestream and you want to know which answer is given most frequently.

Maybe there will be more statistics someday.

## Acknowledgements

Many thanks to all contributors of the following projects:

 * [Python](https://www.python.org/)
 * [Flask](https://palletsprojects.com/p/flask/)
 * [Chat-Downloader](https://github.com/xenova/chat-downloader)
 * [Bulma CSS framework](https://bulma.io/)
