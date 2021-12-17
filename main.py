from __future__ import unicode_literals

import re

from flask import Flask, jsonify, abort, request, send_from_directory
from werkzeug.exceptions import HTTPException
from hashlib import sha256
import threading
import time
import os
import ssl
from urllib.request import Request, urlopen
from operator import itemgetter
from re import search
from math import ceil
import youtube_dl
import sys
import subprocess

__SCRIPT_VERSION__ = '1.0.0'
__SECURITY_HASH__ = '62ed212a46b5787bbb2c846f33e11cee1609fa53d6f3bc8357dde66c897200f3'


# try:
#     from pip import main as pipmain
# except ImportError:
#     from pip._internal import main as pipmain


def get_host_ip(index=0):
    hosts = [
        "https://checkip.amazonaws.com/",
        "http://ipecho.net/plain",
        "http://icanhazip.com/",
        "https://api.ipify.org/",
        "https://ident.me",
        "http://ipgrab.io/",
        "http://ip.42.pl/raw"
    ]
    if index > len(hosts):
        return ""

    ssl._create_default_https_context = ssl._create_unverified_context
    regex = r'^((\d{1,2}|1\d{2}|2[0-4]\d|25[0-5])\.){3}(\d{1,2}|1\d{2}|2[0-4]\d|25[0-5])$'
    try:
        req = Request(
            hosts[index],
            headers={
                'User-Agent':
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            }
        )
        response = urlopen(req, timeout=5)
        ip = response.read().decode('utf-8')
        ip_regex = re.search(regex, ip)
        if ip_regex:
            return ip_regex[0].replace('\n', ' ').replace('\r', '')
        else:
            return get_host_ip(index=index + 1)
    except Exception:
        return get_host_ip(index=index + 1)


def isStringBlank(myString):
    if myString and myString.strip():
        return False
    return True


def touch_file():
    with open('touch.txt', 'w') as f:
        f.write(str(time.time()))


file_exists = os.path.exists("touch.txt")
if not file_exists:
    touch_file()

if not os.path.exists("storage"):
    os.makedirs("storage")


def delete_olds():
    one_days_ago = time.time() - (1 * 86400)
    dir_addr = "storage"
    if os.path.exists(dir_addr):
        for f in os.listdir(dir_addr):
            f = os.path.join(dir_addr, f)
            if os.stat(f).st_mtime < one_days_ago:
                if os.path.isfile(f):
                    os.remove(f)


app = Flask(__name__)


def get_is_thread_running(name):
    running_threads = threading.enumerate()
    for thread in running_threads:
        if thread.name == name:
            return True
    return False


def get_download_main_files(url, file):
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        req = Request(
            url,
            headers={
                'User-Agent':
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            }
        )
        response = urlopen(req, timeout=20)
        data = response.read().decode('utf-8')
        with open(file, 'w') as f:
            f.write(data)
        return True
    except Exception:
        return False


def get_app_updater(update_type):
    if update_type == 'script':
        requirements = get_download_main_files(
            "https://raw.githubusercontent.com/BluestarCo/MyApp/master/requirements.txt",
            "requirements.txt")
        if not requirements:
            print("Error in download requirements.txt file")
            return

        r_d = get_download_main_files(
            "https://raw.githubusercontent.com/BluestarCo/MyApp/master/r_d",
            "r_d")
        if not r_d:
            print("Error in download r_d file")
            return

        print("Installing requirements.txt")
        # pipmain(["install", "--upgrade", "-r", "requirements.txt"])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', '-r',
                               'requirements.txt'])
        main = get_download_main_files("https://raw.githubusercontent.com/BluestarCo/MyApp/master/main.py",
                                       "main.py")
        if not main:
            print("Error in download main.py file")
            return
    elif update_type == 'pip':
        requirements = get_download_main_files(
            "https://raw.githubusercontent.com/BluestarCo/MyApp/master/requirements.txt",
            "requirements.txt")
        if not requirements:
            print("Error in download requirements.txt file")
            return

        r_d = get_download_main_files(
            "https://raw.githubusercontent.com/BluestarCo/MyApp/master/r_d",
            "r_d")
        if not r_d:
            print("Error in download r_d file")
            return

        # pipmain(["install", "--upgrade", "-r", "requirements.txt"])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', '-r',
                               'requirements.txt'])
        touch_file()
    elif update_type in 'git':
        # pipmain(["install", "--upgrade", "git+https://github.com/ytdl-org/youtube-dl.git@master"])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade',
                               'git+https://github.com/ytdl-org/youtube-dl.git@master'])
        touch_file()


@app.before_request
def get_check_hash():
    delete_olds()
    cloud_token = ''
    if 'cloud_token' in request.headers:
        cloud_token = request.headers['cloud_token']
    if not cloud_token or (__SECURITY_HASH__ != sha256(cloud_token.encode()).hexdigest()):
        return abort(401)


# @app.after_request
# def after_request(response):
#     response.headers.add("Access-Control-Allow-Origin", "*")
#     response.headers.add("Access-Control-Allow-Headers", "*")
#     response.headers.add("Access-Control-Allow-Methods", "*")
#     return response


@app.route('/main/status/', methods=['GET'])
def get_status():
    return jsonify({'status': True, 'platform': 'python', "downloader_version": youtube_dl.options.__version__,
                    "script_version": __SCRIPT_VERSION__, "server_ip": get_host_ip()}), 200


@app.route('/main/update/<string:update_type>/', methods=['GET'])
def get_update(update_type):
    if update_type != "script" and update_type != "pip" and update_type != "git":
        return abort(400)

    thread_name = str("app_updater")
    if get_is_thread_running(thread_name):
        return jsonify({'status': False, "code": 200}), 200
    else:
        updater = threading.Thread(target=get_app_updater, args=(update_type,))
        updater.daemon = True
        updater.setDaemon(True)
        updater.name = thread_name
        updater.setName(thread_name)
        updater.start()
        return jsonify({'status': True, "code": 200}), 200


class Logger(object):
    def debug(self, msg):
        print(msg)

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)
        if "429" in msg or "403" in msg:
            return abort(429)
        else:
            return abort(500)


def get_download_url(url, file):
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        req = Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            }
        )
        response = urlopen(req, timeout=20)
        with open('storage/' + file, 'wb') as output:
            output.write(response.read())
        return True
    except Exception:
        return False


def validate_sc_url(url):
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        req = Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            }
        )
        response = urlopen(req, timeout=20)
        url_info = response.info()
        if url_info.get_content_type() == "text/html" or url_info.get_content_type() == "application/xml":
            return False
        else:
            return True
    except Exception as r:
        print(r)
        return False


def get_download_cover_sc_function(song_id, song_title, song_artist, exclude, by_name=False):
    ydl_opts = {
        'skip_download': True,
        'ignoreerrors': True,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 20,
        'nocheckcertificate': True,
        'logger': Logger()
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        if by_name:
            extractor = ydl.extract_info(url=str('scsearch2:' + song_title), download=False)
        else:
            extractor = ydl.extract_info(url=str('scsearch2:' + song_artist + " " + song_title), download=False)

        if extractor:
            track = extractor.get("entries")
            track = sorted(track, key=itemgetter('view_count', 'like_count'), reverse=True)
            if len(track) < 1:
                if not by_name:
                    return get_download_cover_sc_function(song_id, song_title, song_artist, exclude, by_name=True)

            return_list = []
            for single_track in track:
                single_track_title = single_track["title"]
                if single_track_title and ("نت" not in single_track_title) and (
                        search(single_track_title.lower(), song_title.lower()) or search(song_title.lower(),
                                                                                         single_track_title.lower())):
                    return_list.append(single_track)

            if len(return_list) < 1:
                return_list = track

            if len(return_list) > 0:
                return_list = sorted(return_list, key=itemgetter('view_count', 'like_count'), reverse=True)
                return_res = return_list[0]["thumbnail"].replace("original", "t500x500").replace("large", "t500x500")
                if validate_sc_url(return_res):
                    return return_res
                else:
                    if by_name:
                        return False
                    else:
                        return get_download_cover_sc_function(song_id, song_title, song_artist, exclude, by_name=True)

            else:
                if by_name:
                    return False
                else:
                    return get_download_cover_sc_function(song_id, song_title, song_artist, exclude, by_name=True)
        else:
            if by_name:
                return False
            else:
                return get_download_cover_sc_function(song_id, song_title, song_artist, exclude, by_name=True)


def get_remove_file(file):
    if os.path.exists("storage/" + file):
        os.remove("storage/" + file)


def get_remove_file_full_path(file):
    if os.path.exists("storage/" + file):
        os.remove("storage/" + file)


@app.route('/main/download/cover/', methods=['POST'])
def get_download_cover_sc():
    song_id = request.form.get("id")
    song_title = request.form.get("title")
    song_artist = request.form.get("artist")
    exclude = request.form.get("exclude")

    if isStringBlank(song_id) or isStringBlank(song_title) or isStringBlank(song_artist) or isStringBlank(exclude):
        return abort(400)

    c_file = song_id + ".jpg"
    cover = get_download_cover_sc_function(song_id, song_title, song_artist, exclude)
    cover_dl = get_download_url(cover, c_file)
    if cover_dl:
        return jsonify({"status": True, "delete": True, "cover": c_file}), 200

    else:
        if cover:
            return jsonify({"status": True, "delete": False, "cover": cover}), 200
        else:
            return abort(404)


def my_downloader_hook(d):
    if d['status'] == 'error':
        get_remove_file_full_path(d["tmpfilename"])


def get_youtube_download_search(song_id, song_title, song_artist, exclude):
    file_to_dl = "storage/" + song_id + ".m4a"
    ydl_opts = {
        'format': "bestaudio[ext=m4a]",
        'rejecttitle': str(exclude),
        'outtmpl': file_to_dl,
        'socket_timeout': 200,
        'geo_bypass': True,
        'ignoreerrors': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'nooverwrites': False,
        'logger': Logger(),
        'progress_hooks': [my_downloader_hook]

    }

    itag = {
        140: 128,
        171: 128,
        251: 160,
        141: 256,
        250: 70,
        249: 50,
        139: 48
    }

    song_title = re.sub(' +', ' ', song_title)
    song_artist = re.sub(' +', ' ', song_artist)
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        extractor = ydl.extract_info(("ytsearch4:" + song_artist + " " + song_title + " Official"), download=False)
        if extractor:
            track = extractor.get("entries")
            track = sorted(track, key=itemgetter('view_count', 'like_count'), reverse=True)

            return_list = []
            for single_track in track:
                duration = single_track["duration"]
                filesize = single_track["filesize"]
                if duration <= 900 and filesize <= 52428800:
                    return_list.append(single_track)

            if len(return_list) < 1:
                return 404

            index_to_dl = 0
            initial_title = re.sub(' +', ' ', return_list[0]["title"])
            return_list = sorted(return_list, key=itemgetter('view_count', 'like_count'), reverse=True)
            if song_title.lower() not in str(initial_title).lower():
                for index, single_fix in enumerate(return_list):
                    if song_title.lower() in str(re.sub(' +', ' ', single_fix["title"])).lower():
                        index_to_dl = index
                        break

            ydl.download([return_list[index_to_dl]["webpage_url"]])

            tube_itag = return_list[index_to_dl]["format_id"]
            try:
                abr = itag[int(tube_itag)]
            except Exception:
                abr = ceil(return_list[index_to_dl]["abr"])

            if os.path.exists(file_to_dl):
                return jsonify({"status": True, "delete": True, "audio": file_to_dl.replace("storage/", ""),
                                "id": return_list[index_to_dl]["id"], "ext": return_list[index_to_dl]["ext"],
                                "format_id": return_list[index_to_dl]["format_id"], "abr": abr,
                                "source": "youtube"})
            else:
                return 404

        else:
            return 404


def get_soundcloud_download_search(song_id, song_title, song_artist, song_artist_single, exclude, single=False):
    file_to_dl = "storage/" + song_id + ".mp3"
    ydl_opts = {
        'format': "bestaudio[ext=mp3]",
        'rejecttitle': str(exclude),
        'outtmpl': file_to_dl,
        'socket_timeout': 200,
        'geo_bypass': True,
        'ignoreerrors': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'nooverwrites': False,
        'logger': Logger(),
        'progress_hooks': [my_downloader_hook]

    }

    song_artist_single = re.sub(' +', ' ', song_artist_single)
    song_artist = re.sub(' +', ' ', song_artist)
    song_title = re.sub(' +', ' ', song_title)
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        if single:
            extractor = ydl.extract_info(("scsearch4:" + song_artist_single + " " + song_title), download=False)
        else:
            extractor = ydl.extract_info(("scsearch4:" + song_artist + " " + song_title), download=False)

        if extractor:
            track = extractor.get("entries")
            track = sorted(track, key=itemgetter('view_count', 'like_count'), reverse=True)

            return_list = []
            for single_track in track:
                duration = single_track["duration"]
                if duration <= 900:
                    return_list.append(single_track)

            if len(return_list) < 1:
                if single:
                    return 404
                else:
                    return get_soundcloud_download_search(song_id, song_title, song_artist, song_artist_single, exclude,
                                                          single=True)
            index_to_dl = 0
            initial_title = re.sub(' +', ' ', return_list[0]["title"])
            return_list = sorted(return_list, key=itemgetter('view_count', 'like_count'), reverse=True)
            if song_title.lower() not in str(initial_title).lower():
                for index, single_fix in enumerate(return_list):
                    if song_title.lower() in str(re.sub(' +', ' ', single_fix["title"])).lower() and "نت" not in \
                            single_fix["title"]:
                        index_to_dl = index
                        break

            ydl.download([return_list[index_to_dl]["webpage_url"]])

            abr = ceil(return_list[index_to_dl]["abr"])

            if os.path.exists(file_to_dl):
                print(return_list[index_to_dl])
                return jsonify({"status": True, "delete": True, "audio": file_to_dl.replace("storage/", ""),
                                "id": return_list[index_to_dl]["id"], "ext": return_list[index_to_dl]["ext"],
                                "format_id": return_list[index_to_dl]["format_id"], "abr": abr,
                                "source": "soundcloud"})
            else:
                if single:
                    return 404
                else:
                    return get_soundcloud_download_search(song_id, song_title, song_artist, song_artist_single, exclude,
                                                          single=True)
        else:
            if single:
                return 404
            else:
                return get_soundcloud_download_search(song_id, song_title, song_artist, song_artist_single, exclude,
                                                      single=True)


@app.route('/main/download/audio/search/', methods=['POST'])
def get_download_audio_search():
    song_id = request.form.get("id")
    song_title = request.form.get("title")
    song_artist = request.form.get("artist")
    song_artist_single = request.form.get("artist_single")
    mirror_type = request.form.get("mirror_type")
    exclude = request.form.get("exclude")

    if isStringBlank(song_id) or isStringBlank(song_title) or isStringBlank(song_artist) or isStringBlank(
            song_artist_single) or isStringBlank(mirror_type) or isStringBlank(exclude):
        abort(400)

    if mirror_type == "youtube":
        youtube_download_search = get_youtube_download_search(song_id, song_title, song_artist, exclude)
        if youtube_download_search == 404:
            abort(404)
        else:
            return youtube_download_search, 200

    elif mirror_type == "soundcloud":
        soundcloud_download_search = get_soundcloud_download_search(song_id, song_title, song_artist,
                                                                    song_artist_single, exclude)
        if soundcloud_download_search == 404:
            abort(404)
        else:
            return soundcloud_download_search, 200

    elif mirror_type == "auto":
        youtube_download_search = get_youtube_download_search(song_id, song_title, song_artist, exclude)
        if youtube_download_search == 404:
            soundcloud_download_search = get_soundcloud_download_search(song_id, song_title, song_artist,
                                                                        song_artist_single, exclude)
            if soundcloud_download_search == 404:
                abort(404)
            else:
                return soundcloud_download_search, 200

        else:
            return youtube_download_search, 200

    else:
        abort(400)


@app.route('/main/download/audio/url/', methods=['POST'])
def get_download_audio_url():
    song_id = request.form.get("id")
    song_url = request.form.get("url")
    mirror_type = request.form.get("mirror_type")

    if isStringBlank(song_id) or isStringBlank(song_url) or isStringBlank(
            mirror_type):
        abort(400)

    if mirror_type == "youtube":
        file_to_dl = "storage/" + song_id + ".m4a"
        ydl_opts = {
            'format': "bestaudio[ext=m4a]",
            'outtmpl': file_to_dl,
            'socket_timeout': 200,
            'geo_bypass': True,
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'nooverwrites': False,
            'logger': Logger(),
            'progress_hooks': [my_downloader_hook]

        }

        itag = {
            140: 128,
            171: 128,
            251: 160,
            141: 256,
            250: 70,
            249: 50,
            139: 48
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            extractor = ydl.extract_info(song_url, download=True)
            if extractor:
                tube_itag = extractor["format_id"]
                try:
                    abr = itag[int(tube_itag)]
                except Exception:
                    abr = ceil(extractor["abr"])

                if os.path.exists(file_to_dl):
                    return jsonify({"status": True, "delete": True, "audio": file_to_dl.replace("storage/", ""),
                                    "id": extractor["id"], "ext": extractor["ext"],
                                    "format_id": extractor["format_id"], "abr": abr,
                                    "source": "youtube"})
                else:
                    return 404

            else:
                return 404

    elif mirror_type == "soundcloud":
        file_to_dl = "storage/" + song_id + ".mp3"
        ydl_opts = {
            'format': "bestaudio[ext=mp3]",
            'outtmpl': file_to_dl,
            'socket_timeout': 200,
            'geo_bypass': True,
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'nooverwrites': False,
            'logger': Logger(),
            'progress_hooks': [my_downloader_hook]

        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            extractor = ydl.extract_info(song_url, download=True)
            if extractor:
                ydl.download([extractor["webpage_url"]])

                abr = ceil(extractor["abr"])

                if os.path.exists(file_to_dl):
                    return jsonify({"status": True, "delete": True, "audio": file_to_dl.replace("storage/", ""),
                                    "id": extractor["id"], "ext": extractor["ext"],
                                    "format_id": extractor["format_id"], "abr": abr,
                                    "source": "soundcloud"})
                else:
                    return 404

            else:
                return 404

    else:
        abort(400)


@app.route('/main/file/download/<string:file>/', methods=['GET'])
def get_download_local_file(file):
    if isStringBlank(file) or not os.path.exists("storage/" + file):
        abort(404)

    full_path = os.path.join(app.root_path, "storage")
    return send_from_directory(full_path, file)


@app.route('/main/file/delete/<string:file>/', methods=['GET'])
def get_delete_local_file(file):
    if isStringBlank(file):
        abort(404)

    if file == "all":
        list(map(os.unlink, (os.path.join("storage", f) for f in os.listdir("storage"))))
    else:
        get_remove_file(file)
    return jsonify({"status": True, "code": 200}), 200


@app.errorhandler(Exception)
def get_error(e):
    if isinstance(e, HTTPException):
        return jsonify({"status": False, "code": e.code}), e.code

    return jsonify({"status": False, "code": 500}), 500


if __name__ == '__main__':
    app_port = os.environ.get('PORT')
    if app_port:
        app.run(port=app_port, host='0.0.0.0', use_reloader=True, load_dotenv=True, extra_files=['touch.txt'])
    else:
        app.run(use_reloader=True, host='0.0.0.0', load_dotenv=True, extra_files=['touch.txt'])
