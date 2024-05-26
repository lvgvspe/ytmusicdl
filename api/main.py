import os
import sys
from typing import Iterable
from multiprocessing.pool import ThreadPool
from math import ceil
from urllib.error import HTTPError

from pytube import YouTube, Playlist
from pytube.helpers import DeferredGeneratorList, safe_filename
from pytube.exceptions import MaxRetriesExceeded
from pydub import AudioSegment
import requests
from mutagen.id3 import ID3, APIC
from mutagen.easyid3 import EasyID3
from ytmusicapi import YTMusic

from log import create_logger
import shutil


log = create_logger("ytdownloader")

root = os.path.dirname(os.path.abspath(__file__))


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


# Create function to insert tags to mp3 file
def edit_tags(file_path, unsafe_title, author, album, year, number, image_path):
    with open(image_path, "rb") as art:
        audio = ID3(file_path)
        audio["APIC"] = APIC(
            encoding=3, mime="image/jpeg", type=3, desc="Cover", data=art.read()
        )
        audio.save()
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


def download_song(i, video, album_title, author, playlist, album_year, image_path):
    # Download audio only
    extension = None
    bitrate = None
    try:
        bitrate = "256"
        video.streams.get_by_itag(141).download(output_path=os.path.join(root, album_title))
    except:
        log.warning(f"Failed {video.title} from {album_title} - {author}. Trying lower")
        try:
            video.streams.get_by_itag(140).download(output_path=os.path.join(root, album_title))
        except:
            log.warning(
                f"Failed {video.title} from {album_title} - {author}. Trying lowest"
            )
            try:
                video.streams.get_by_itag(139).download(output_path=os.path.join(root, album_title))
            except:
                log.warning(
                    f"Failed {video.title} from {album_title} - {author}. Trying webm"
                )
                extension = "webm"
                try:
                    bitrate = "160"
                    video.streams.get_by_itag(140).download(output_path=os.path.join(root, album_title))
                except:
                    log.warning(
                        f"Failed {video.title} from {album_title} - {author}. Trying lower webm"
                    )
                    try:
                        video.streams.get_by_itag(139).download(output_path=os.path.join(root, album_title))
                    except:
                        log.warning(
                            f"Failed {video.title} from {album_title} - {author}. Trying lowest webm"
                        )
                        try:
                            video.streams.get_by_itag(139).download(
                                output_path=os.path.join(root, album_title)
                            )
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
        + safe_filename(video.title)
        + (".webm" if extension else ".mp4"),
        format="webm" if extension else "m4a",
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
        + safe_filename(video.title)
        + (".webm" if extension else ".mp4")
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
        author = playlist.videos[0].author
    except IndexError:
        log.error(f"Error: Playlist {url} is empty")
        return
    log.info(f"Now processing {playlist.title.replace('Album - ', '')} - {author}")
    try:
        album_year = get_album_year(
            author, playlist.title.replace("Album - ", "").strip()
        )
    except:
        album_year = "0000"
        log.error(f"Year ZERO error for Album {playlist.title.replace('Album', f'{author} - {album_year}')}. Run fix_zero after script to fix.")
    album_title = playlist.title.replace("Album", f"{author} - {album_year}")

    # Create folder for the playlist
    os.makedirs(os.path.join(root, album_title), exist_ok=True)

    download_image(
        playlist.videos[0].thumbnail_url, os.path.join(root, album_title, "image.jpg")
    )
    image_path = os.path.join(root, album_title, "image.jpg")
    items = [
        (i, video, safe_filename(album_title), author, playlist, album_year, image_path)
        for i, video in enumerate(playlist.videos, start=1)
    ]
    pool = ThreadPool(processes=2)
    pool.starmap(download_song, items)

    os.remove(image_path)

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
    upload_all()
    log.info("Upload finished!")


if __name__ == "__main__":
    try:
        globals()[sys.argv[1]](sys.argv[2])
    except IndexError:
        globals()[sys.argv[1]]()
