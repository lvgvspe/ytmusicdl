import os
import json

from ytmusicapi import YTMusic

root = os.path.dirname(os.path.abspath(__file__))

yt = YTMusic(os.path.join(root, 'browser.json'))

# Get uploaded albums
def save_albums_list():
    with open(os.path.join(root, 'resp.json'), 'wt') as file:
        file.write(json.dumps(yt.get_library_upload_albums(limit=None), indent=2))

def get_artists():
    return sorted(list(set([r['artists'][0]['name'].lower().title() for r in json.load(open(os.path.join(root, 'resp.json'), 'rt'))])))

def get_list():
    lista = []
    for artist in get_artists():
        try:
            browseId = [r for r in yt.search(artist, "artists") if r['resultType'] == 'artist'][0]['browseId']
            # with open(os.path.join(root, 'artist.json'), 'wt') as file:
            #     file.write(json.dumps(yt.get_artist(browseId), indent=2))
            albums = yt.get_artist(browseId)['albums']['results']
            my_albums = [r['title'] for r in json.load(open(os.path.join(root, 'resp.json'), 'rt'))]
            for r in albums:
                # if r['title'] in my_albums:
                lista.append([artist, r['title'], r['year'], r['audioPlaylistId']])
        except:
            print(f"Error with {artist}")
    with open(os.path.join(root, 'lists.json'), 'wt') as file:
        file.write(json.dumps(lista, indent=2))

def get_missing():
    saved_albums = [l[1] for l in json.load(open(os.path.join(root, 'lists.json'), 'rt'))]
    my_albums = [r['title'] for r in json.load(open(os.path.join(root, 'resp.json'), 'rt'))]
    missing = sorted([album for album in my_albums if album not in saved_albums])
    print(missing)
        
def create_list():
    downloaded = [l.strip() for l in open(os.path.join(root, 'lists copy.txt'), 'rt').readlines()]
    with open(os.path.join(root, 'lists.txt'), 'wt') as file:
        file.writelines(['https://music.youtube.com/playlist?list=' + l[3] + '\n' for l in json.load(open(os.path.join(root, 'lists.json'), 'rt')) if ('https://music.youtube.com/playlist?list=' + l[3]) not in downloaded])

def get_year(url):
    id = url.split('=')[-1]
    albums = json.load(open(os.path.join(root, 'lists.json'), 'rt'))
    for album in albums:
        if album[3] == id:
            return album[2]

get_list()