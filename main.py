import os
import sys
import json
from zipfile import ZipFile
from typing import Iterable
from multiprocessing.pool import ThreadPool
from math import ceil
from urllib.error import HTTPError

import librosa
from pytubefix import YouTube, Playlist, Channel
from pytubefix.helpers import DeferredGeneratorList, safe_filename
from pytubefix.exceptions import MaxRetriesExceeded
from pydub import AudioSegment
import requests
from mutagen.id3 import ID3, APIC
from mutagen.easyid3 import EasyID3
from ytmusicapi import YTMusic

from log import create_logger
import shutil


log = create_logger("ytdownloader")

root = os.path.dirname(os.path.abspath(__file__))

# import ssl
# from pytube import request
# from pytube import extract
# from pytube.innertube import _default_clients
# from pytube.exceptions import RegexMatchError

# _default_clients["ANDROID"]["context"]["client"]["clientVersion"] = "19.08.35"
# _default_clients["IOS"]["context"]["client"]["clientVersion"] = "19.08.35"
# _default_clients["ANDROID_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
# _default_clients["IOS_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"
# _default_clients["IOS_MUSIC"]["context"]["client"]["clientVersion"] = "6.41"
# _default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID"]

# import pytube, re
# def patched_get_throttling_function_name(js: str) -> str:
#     function_patterns = [
#         r'a\.[a-zA-Z]\s*&&\s*\([a-z]\s*=\s*a\.get\("n"\)\)\s*&&.*?\|\|\s*([a-z]+)',
#         r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])?\([a-z]\)',
#         r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])\([a-z]\)',
#     ]
#     for pattern in function_patterns:
#         regex = re.compile(pattern)
#         function_match = regex.search(js)
#         if function_match:
#             if len(function_match.groups()) == 1:
#                 return function_match.group(1)
#             idx = function_match.group(2)
#             if idx:
#                 idx = idx.strip("[]")
#                 array = re.search(
#                     r'var {nfunc}\s*=\s*(\[.+?\]);'.format(
#                         nfunc=re.escape(function_match.group(1))),
#                     js
#                 )
#                 if array:
#                     array = array.group(1).strip("[]").split(",")
#                     array = [x.strip() for x in array]
#                     return array[int(idx)]

#     raise RegexMatchError(
#         caller="get_throttling_function_name", pattern="multiple"
#     )

# ssl._create_default_https_context = ssl._create_unverified_context
# pytube.cipher.get_throttling_function_name = patched_get_throttling_function_name

# Rewrite Playlist class to enable oauth within YouTube class
class Playlist(Playlist):
    def __init__(self, url: str):
        super().__init__(url)

    def videos_generator(self):
        for url in self.video_urls:
            yield YouTube(url, use_oauth=True)

    @property
    def videos(self) -> Iterable[YouTube]:
        """Yields YouTube objects of videos in this playlist

        :rtype: List[YouTube]
        :returns: List of YouTube
        """
        return DeferredGeneratorList(self.videos_generator())


# Function to manually edit id3 tags for every album with year '0000'
def fix_zero():
    for folder in os.listdir(root):
        try:
            if os.path.isdir(os.path.join(root, folder)) and folder.split(" - ")[1] == "0000":
                input_year = input(
                    f"Enter year for album {folder.split(' - ')[2]} - {folder.split(' - ')[0]}: "
                )
                for file in os.listdir(os.path.join(root, folder)):
                    if file.endswith(".mp3"):
                        audio = EasyID3(os.path.join(root, folder, file))
                        audio["date"] = input_year
                        audio["originaldate"] = input_year
                        audio.save()
                os.rename(
                    os.path.join(root, folder),
                    os.path.join(root, f"{folder.split(' - ')[0]} - {input_year} - {folder.split('-')[2]}"),
                )
        except IndexError:
            pass
# Function to find bpm of song
def find_bpm(file_path):
    print(f"Finding bpm for {file_path.split('/')[-1]}"+" "*20, end="\r")
    audio_file = librosa.load(file_path)
    y, sr = audio_file
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    audio = EasyID3(file_path)
    audio["bpm"] = str(int(tempo[0]))
    audio.save()
    return file_path.split("/")[-1]

# Add BPM tag to all songs inside folder
def add_bpm_to_all(file_path):
    pool = ThreadPool(processes=os.cpu_count())
    pool.map(find_bpm, [os.path.join(file_path, file) for file in os.listdir(file_path) if file.endswith(".mp3")])
    # for i, file in enumerate(os.listdir(file_path)):
    #     try:
    #         if file.endswith(".mp3"):
    #             print(f"{i}/{len(os.listdir(file_path))} : {file}"+" "*20, end="\r")
    #             find_bpm(os.path.join(file_path, file))
    #     except:
    #         print()
    #         print(f"Erro em {file}")
    #         print()


# Create function to insert tags to mp3 file
def edit_tags(file_path, unsafe_title, author, album, year, number, image_path):
    with open(image_path, "rb") as art:
        audio = ID3(file_path)
        audio["APIC"] = APIC(
            encoding=3, mime="image/jpeg", type=3, desc="Cover", data=art.read()
        )
        audio.save()
    find_bpm(file_path)
    audio = EasyID3(file_path)
    audio["title"] = unsafe_title
    audio["artist"] = author
    audio["albumartist"] = author
    audio["album"] = album
    audio["date"] = year
    audio["originaldate"] = year
    audio["tracknumber"] = number
    audio.save()


def get_album_year(author, album_title):
    """Gets album information from the MusicBrainz API.

    Args:
        author (str): The author of the album.
        album_title (str): The title of the album.

    Returns:
        str: A string containing the release year of the album.

    Raises:
        Exception: If there is an HTTPError.
    """
    # Get musicbrainz artist ID
    artist_request = requests.get(
        f"https://musicbrainz.org/ws/2/artist?query={author}&fmt=json"
    )
    artist_request.raise_for_status()
    artist_id = artist_request.json()["artists"][0]["id"]

    # Get musicbrainz release year
    release_request = requests.get(
        f"https://musicbrainz.org/ws/2/release?query={album_title}%20AND%20arid:{artist_id}&fmt=json"
    )
    release_request.raise_for_status()
    release_year = release_request.json()["releases"][0]["date"].split("-")[0]
    return release_year


def download_image(url, file_path):
    """Downloads an image from the specified URL and saves it to the given file path.

    Args:
        url: The URL of the image to download.
        file_path: The path to save the downloaded image.

    Raises:
        Exception: If there is an error downloading the image.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for unsuccessful requests
        with open(file_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        raise Exception(f"Error downloading image: {e}") from e


def download_song(i, video, album_title, author, playlist, album_year, image_path, url):
    # Download audio only
    extension = None
    bitrate = None
    filename = None
    try:
        bitrate = "256"
        stream = video.streams.get_by_itag(141)
        extension = stream.default_filename.split(".")[-1]
        filename = safe_filename(video.title)+"."+extension
        stream.download(output_path=os.path.join(root, album_title), filename=filename)
    except:
        log.warning(f"Failed {video.title} from {album_title} - {author}. Trying lower")
        try:
            stream = video.streams.get_by_itag(140)
            extension = stream.default_filename.split(".")[-1]
            filename = safe_filename(video.title)+"."+extension
            stream.download(output_path=os.path.join(root, album_title), filename=filename)
        except:
            log.warning(
                f"Failed {video.title} from {album_title} - {author}. Trying lowest"
            )
            try:
                stream = video.streams.get_by_itag(139)
                extension = stream.default_filename.split(".")[-1]
                filename = safe_filename(video.title)+"."+extension
                stream.download(output_path=os.path.join(root, album_title), filename=filename)
            except:
                log.warning(
                    f"Failed {video.title} from {album_title} - {author}. Trying webm"
                )
                extension = "webm"
                try:
                    bitrate = "160"
                    stream = video.streams.get_by_itag(140)
                    extension = stream.default_filename.split(".")[-1]
                    filename = safe_filename(video.title)+"."+extension
                    stream.download(output_path=os.path.join(root, album_title), filename=filename)
                except:
                    log.warning(
                        f"Failed {video.title} from {album_title} - {author}. Trying lower webm"
                    )
                    try:
                        stream = video.streams.get_by_itag(139)
                        extension = stream.default_filename.split(".")[-1]
                        filename = safe_filename(video.title)+"."+extension
                        stream.download(output_path=os.path.join(root, album_title), filename=filename)
                    except:
                        log.warning(
                            f"Failed {video.title} from {album_title} - {author}. Trying lowest webm"
                        )
                        try:
                            stream = video.streams.get_by_itag(139)
                            extension = stream.default_filename.split(".")[-1]
                            filename = safe_filename(video.title)+"."+extension
                            stream.download(output_path=os.path.join(root, album_title), filename=filename)
                        except AttributeError:
                            log.error(
                                f"Attribute error while downloading {video.title} from {album_title} - {author}"
                            )
                            return
                        except HTTPError:
                            log.error(
                                f"HTTP error while downloading {video.title} from {album_title} - {author}"
                            )
                            return
                        except MaxRetriesExceeded:
                            log.error(
                                f"Max Retries error while downloading {video.title} from {album_title} - {author}"
                            )
                            return

    # Convert file to mp3 using pydub
    sound = AudioSegment.from_file(
        os.path.join(root, album_title)
        + "/"
        + filename,
        format=extension,
    )
    sound.export(
        os.path.join(root, album_title)
        + "/"
        + str(i).zfill(2)
        + " - "
        + safe_filename(video.title)
        + ".mp3",
        format="mp3",
        bitrate=bitrate if bitrate else None,
    )
    edit_tags(
        os.path.join(root, album_title)
        + "/"
        + str(i).zfill(2)
        + " - "
        + safe_filename(video.title)
        + ".mp3",
        video.title,
        author,
        playlist.title.replace("Album - ", ""),
        album_year,
        str(i),
        image_path,
    )
    # Delete file
    os.remove(
        os.path.join(root, album_title)
        + "/"
        + filename
    )


# Download songs from youtube playlist and save them to a folder with the name of the playlist
def download_playlist(url):
    """Downloads songs from a YouTube playlist and saves them to a folder with the name of the playlist.

    Args:
        url (str): The URL of the YouTube playlist.

    Returns:
        None
    """
    log.debug(f"Playlist: {url}")
    playlist = Playlist(url)
    try:
        # author = playlist.videos[0].author.replace(' - Topic', '')
        channel = Channel(playlist.videos[0].channel_url)
        author = channel.channel_name.replace(' - Topic', '')
    except IndexError:
        log.error(f"Error: Playlist {url} is empty")
        return
    log.info(f"Now processing {playlist.title.replace('Album - ', '')} - {author}")
    try:
        album_year = get_album_year(
            author, playlist.title.replace("Album - ", "").strip()
        )
        if len(album_year) != 4:
            album_year = "0000"
            log.error(f"Year ZERO error for Album {playlist.title.replace('Album', f'{author} - {album_year}')}. Run fix_zero after script to fix.")
    except:
        album_year = "0000"
        log.error(f"Year ZERO error for Album {playlist.title.replace('Album', f'{author} - {album_year}')}. Run fix_zero after script to fix.")
    # def get_year(url):
    #     id = url.split('=')[-1]
    #     albums = json.load(open(os.path.join(root, 'lists.json'), 'rt'))
    #     for album in albums:
    #         if album[3] == id:
    #             return album[2]
    # album_year = get_year(url)
    album_title = playlist.title.replace("Album", f"{author} - {album_year}")

    # Create folder for the playlist
    os.makedirs(os.path.join(root, album_title), exist_ok=True)

    download_image(
        playlist.videos[0].thumbnail_url, os.path.join(root, album_title, "image.jpg")
    )
    image_path = os.path.join(root, album_title, "image.jpg")
    items = [
        (i, video, safe_filename(album_title), author, playlist, album_year, image_path, url)
        for i, video in enumerate(playlist.videos, start=1)
    ]
    pool = ThreadPool(processes=2)
    pool.starmap(download_song, items)
    try:
        os.remove(image_path)
    except:
        pass

#Upload the songs to YouTube Music
def upload_all():
    yt = YTMusic(os.path.join(root, 'browser.json'))
    for folder in os.listdir(root):
        try:
            if os.path.isdir(os.path.join(root, folder)) and folder.split(" - ")[1].isnumeric():
                if folder.split(" - ")[1] == "0000":
                    log.error(f"Album with year '0000' for {folder}, skip upload.")
                    continue
                log.info(f"Now uploading {folder}")
                album_list = [file for file in os.listdir(os.path.join(root, folder)) if file.endswith(".mp3")]
                total_uploaded = 0
                for file in album_list:
                    if file.endswith(".mp3"):
                        yt.upload_song(os.path.join(root, folder, file))
                        total_uploaded += 1
                if total_uploaded == len(album_list):
                    shutil.rmtree(os.path.join(root, folder))
                else:
                    log.error(f"Uploading failed for {len(album_list) - total_uploaded} songs for {folder}")
        except IndexError:
            pass

#Serve static file zipped
def zip_all():
    try:
        os.remove(os.path.join(root, "files.zip"))
    except:
        pass
    with ZipFile(os.path.join(root, "static", "files.zip"), "w") as zip_file:
        for folder in os.listdir(root):
            try:
                if os.path.isdir(os.path.join(root, folder)) and folder.split(" - ")[1].isnumeric():
                    if folder.split(" - ")[1] == "0000":
                        log.error(f"Album with year '0000' for {folder}, skip upload.")
                        continue
                    log.info(f"Now zipping {folder}")
                    album_list = [file for file in os.listdir(os.path.join(root, folder)) if file.endswith(".mp3")]
                    total_uploaded = 0
                    for file in album_list:
                        if file.endswith(".mp3"):
                            zip_file.write(os.path.join(root, folder, file), file)
                            total_uploaded += 1
                    if total_uploaded == len(album_list):
                        shutil.rmtree(os.path.join(root, folder))
                    else:
                        log.error(f"Uploading failed for {len(album_list) - total_uploaded} songs for {folder}")
            except IndexError:
                pass
            
def zip_again():
    with ZipFile(os.path.join(root, "static", "files.zip"), "a") as zip_file:
        for folder in os.listdir(root):
            try:
                if os.path.isdir(os.path.join(root, folder)) and folder.split(" - ")[1].isnumeric():
                    if folder.split(" - ")[1] == "0000":
                        log.error(f"Album with year '0000' for {folder}, skip upload.")
                        continue
                    log.info(f"Now zipping {folder}")
                    album_list = [file for file in os.listdir(os.path.join(root, folder)) if file.endswith(".mp3")]
                    total_uploaded = 0
                    for file in album_list:
                        if file.endswith(".mp3"):
                            zip_file.write(os.path.join(root, folder, file), file)
                            total_uploaded += 1
                    if total_uploaded == len(album_list):
                        shutil.rmtree(os.path.join(root, folder))
                    else:
                        log.error(f"Uploading failed for {len(album_list) - total_uploaded} songs for {folder}")
            except IndexError:
                pass

def save_all():
    for folder in os.listdir(root):
        try:
            if os.path.isdir(os.path.join(root, folder)) and folder.split(" - ")[1].isnumeric():
                if folder.split(" - ")[1] == "0000":
                    log.error(f"Album with year '0000' for {folder}, skip saving.")
                    continue
                log.info(f"Now Saving {folder}")
                album_list = [file for file in os.listdir(os.path.join(root, folder)) if file.endswith(".mp3")]
                total_uploaded = 0
                for file in album_list:
                    if file.endswith(".mp3"):
                        shutil.copyfile(os.path.join(root, folder, file), os.path.join(os.path.expanduser("~"), "Músicas", file))
                        total_uploaded += 1
                if total_uploaded == len(album_list):
                    shutil.rmtree(os.path.join(root, folder))
                else:
                    log.error(f"Saving failed for {len(album_list) - total_uploaded} songs for {folder}")
        except IndexError:
            pass

def run():
    with open(os.path.join(root, "lists.txt"), "rt") as file:
        for i, link in enumerate(file.readlines(), start=1):
            try:
                playlist = (
                    Playlist(link.strip()).videos[0].streams.get_by_itag(251).filesize
                )  # only to trigger login code
            except IndexError:
                continue
            else:
                break
    with open(os.path.join(root, "lists.txt"), "rt") as file:
        pool = ThreadPool(processes=int(os.cpu_count()/2))
        pool.map(download_playlist, [link.strip() for link in file.readlines() if link.strip()])
        # for link in file.readlines():
        #     download_playlist(link.strip())
    log.info("Download finished! Starting upload...")
    # upload_all()
    # zip_all()
    save_all()
    log.info("Upload finished!")


if __name__ == "__main__":
    try:
        globals()[sys.argv[1]](sys.argv[2])
    except IndexError:
        globals()[sys.argv[1]]()
