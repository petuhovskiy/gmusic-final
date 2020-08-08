import gmusicapi
import os
from os.path import isfile, join
import json
import eyed3
import requests
import time

mobile = gmusicapi.Mobileclient()

device_id = ''

if not mobile.oauth_login(device_id, oauth_credentials='./mobileclient.cred'):
    print('mobile auth failed')
    exit()

print(mobile.get_registered_devices())
print('Subscription:', mobile.is_subscribed)

def save_library():
    data = mobile.get_all_songs()
    with open('library.json', 'w') as outfile:
        json.dump(data, outfile)

def save_playlists():
    playlists = mobile.get_all_playlists()
    with open('playlists.json', 'w') as outfile:
        json.dump(playlists, outfile)

def save_my_playlists_content():
    data = mobile.get_all_user_playlist_contents()
    with open('my_playlists.json', 'w') as outfile:
        json.dump(data, outfile)

def cnv(t):
    if t == None:
        return ''
    return t.strip().lower()

def cint(t):
    if t == None:
        return 0
    if t == '':
        return 0
    return t

def checkgenre(tags, track):
    genre = '' if 'genre' not in track else track['genre']
    genre2name = '' if tags.tag.genre == None else tags.tag.genre.name

    if cnv(genre2name) == cnv(genre):
        return True

    if tags.tag.genre != None and genre == '({})'.format(tags.tag.genre.id):
        return True

    return False

def checkmatch(tags, track):
    track_title = '' if 'title' not in track else track['title']
    track_album = '' if 'album' not in track else track['album']
    track_artist = '' if 'artist' not in track else track['artist']
    track_composer = '' if 'composer' not in track else track['composer']
    album_artist = '' if 'albumArtist' not in track else track['albumArtist']

    if cnv(tags.tag.title) != cnv(track_title):
        return False

    if cnv(tags.tag.album) != cnv(track_album):
        return False

    if cnv(tags.tag.artist) != cnv(track_artist):
        return False

    if cint(tags.tag._getTrackNum()[0]) != cint(track['trackNumber']):
        return False

    if cnv(tags.tag.composer) != cnv(track_composer):
        return False

    if cnv(tags.tag.album_artist) != cnv(album_artist):
        return False

    if not checkgenre(tags, track):
        return False

    return True

def fix_uploaded_tracks(loc='./tracks'):
    library = mobile.get_all_songs()
    library = [t for t in library if 'explicitType' not in t]
    print(len(library))

    files = os.listdir(loc)
    print(len(files))

    for file in files:
        print(file)
        tags = eyed3.load(loc + '/' + file)

        matches = []
        for track in library:
            if checkmatch(tags, track):
                matches.append(track)

        for match in matches:
            if match['id'] == file[:-4]:
                matches = [match]
                break

        if len(matches) != 1:
            print('bad matches')
            print(file)
            print(matches)
            continue
        
        match = matches[0]
        match['my_count'] = match.get('my_count', 0) + 1

        old_name = loc + '/' + file
        new_name = loc + '/' + match['id'] + '.mp3'

        if old_name == new_name:
            continue

        os.rename(old_name, new_name)

    for lib in library:
        if lib.get('my_count', 0) != 1:
            print('bad count')
            print(lib)

def tagTrack(track, file):
    audiofile = eyed3.load(file)
    audiofile.initTag()
    audiofile.tag.title = track['title']
    audiofile.tag.artist = track['artist']
    audiofile.tag.composer = track['composer']
    audiofile.tag.album = track['album']
    audiofile.tag.album_artist = track['albumArtist']

    if 'year' in track and track['year'] > 0:
        audiofile.tag.release_date = track['year']

    if 'comment' in track and track['comment'] != '':
        audiofile.tag.comment = track['comment']

    audiofile.tag.track_num = (track.get('trackNumber', None), track.get('totalTrackCount', None))

    if 'genre' in track and track['genre'] != '':
        audiofile.tag.genre = track['genre']

    audiofile.tag.disc_num = (track.get('discNumber', None), track.get('totalDiscCount', None))

    if 'albumArtRef' in track and len(track['albumArtRef']) > 0:
        cover_url = track['albumArtRef'][0]['url']
        resp = requests.get(cover_url)
        audiofile.tag.images.set(eyed3.id3.frames.ImageFrame.FRONT_COVER, resp.content, resp.headers['content-type'])

    audiofile.tag.save()

def download_track(track, file):
    print('downloading ', track)

    try:
        stream = mobile.get_stream_url(track['id'])
    except gmusicapi.exceptions.CallFailure as err:
        print('failed to download', file, err)
        if len(err.args) > 0 and err.args[0].startswith('403'):
            print('rate limited :(')
            exit(2)
        return

    resp = requests.get(stream)
    with open(file, 'wb') as f:
        f.write(resp.content)
    tagTrack(track, file)

    print(file)
    time.sleep(40)

def download_library(loc='./tracks'):
    library = mobile.get_all_songs()

    for track in library:
        file = loc + '/' + track['id'] + '.mp3'
        try:
            st = os.stat(file)
        except:
            download_track(track, file)
            continue

        # if 'estimatedSize' in track and abs(st.st_size - int(track['estimatedSize'])) > 700000:
        #     print('warn: size mismatch', st.st_size, int(track['estimatedSize']))
        #     print(track)


# save_library()
# save_playlists()
# save_my_playlists_content()
# fix_uploaded_tracks()
# download_library()
