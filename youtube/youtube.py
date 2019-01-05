import mimetypes
import urllib.parse
import os
from youtube import local_playlist, watch, search, playlist, channel, comments, common, post_comment, accounts
import settings
YOUTUBE_FILES = (
    "/shared.css",
    '/comments.css',
    '/favicon.ico',
)
get_handlers = {
    'search':           search.get_search_page,
    '':                 search.get_search_page,
    'comments':         comments.get_comments_page,
    'watch':            watch.get_watch_page,
    'playlist':         playlist.get_playlist_page,
    'post_comment':     post_comment.get_post_comment_page,
    'delete_comment':   post_comment.get_delete_comment_page,
    'login':            accounts.get_account_login_page,
}
post_handlers = {
    'edit_playlist':    local_playlist.edit_playlist,
    'login':            accounts.add_account,
}

def youtube(env, start_response):
    path, method, query_string = env['PATH_INFO'], env['REQUEST_METHOD'], env['QUERY_STRING']
    env['qs_fields'] = urllib.parse.parse_qs(query_string)
    env['fields'] = dict(env['qs_fields'])

    path_parts = path.rstrip('/').lstrip('/').split('/')
    env['path_parts'] = path_parts

    if method == "GET":
        try:
            handler = get_handlers[path_parts[0]]
        except KeyError:
            pass
        else:
            return handler(env, start_response)

        if path in YOUTUBE_FILES:
            with open("youtube" + path, 'rb') as f:
                mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
                start_response('200 OK',  (('Content-type',mime_type),) )
                return f.read()
        
        elif path.startswith("/channel/"):
            start_response('200 OK',  (('Content-type','text/html'),) )
            return channel.get_channel_page(path[9:], query_string=query_string).encode()

        elif path.startswith("/user/") or path.startswith("/c/"):
            start_response('200 OK',  (('Content-type','text/html'),) )
            return channel.get_channel_page_general_url(path, query_string=query_string).encode()

        elif path.startswith("/playlists"):
            start_response('200 OK',  (('Content-type','text/html'),) )
            return local_playlist.get_playlist_page(path[10:], query_string=query_string).encode()

        elif path.startswith("/data/playlist_thumbnails/"):
            with open(os.path.join(settings.data_dir, os.path.normpath(path[6:])), 'rb') as f:
                start_response('200 OK',  (('Content-type', "image/jpeg"),) )
                return f.read()

        elif path.startswith("/api/"):
            start_response('200 OK',  () )
            result = common.fetch_url('https://www.youtube.com' + path + ('?' + query_string if query_string else ''))
            result = result.replace(b"align:start position:0%", b"")
            return result

        elif path == "/opensearch.xml":
            with open("youtube" + path, 'rb') as f:
                mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
                start_response('200 OK',  (('Content-type',mime_type),) )
                return f.read().replace(b'$port_number', str(settings.port_number).encode())

        elif path == "/comment_delete_success":
            start_response('200 OK',  () )
            return b'Successfully deleted comment'

        elif path == "/comment_delete_fail":
            start_response('200 OK',  () )
            return b'Failed to deleted comment'

        else:
            start_response('200 OK',  (('Content-type','text/html'),) )
            return channel.get_channel_page_general_url(path, query_string=query_string).encode()

    elif method == "POST":
        post_fields = urllib.parse.parse_qs(env['wsgi.input'].read().decode())
        env['post_fields'] = post_fields
        env['fields'].update(post_fields)
        fields = post_fields

        try:
            handler = post_handlers[path_parts[0]]
        except KeyError:
            pass
        else:
            return handler(env, start_response)

        if path.startswith("/playlists"):
            if fields['action'][0] == 'remove':
                playlist_name = path[11:]
                local_playlist.remove_from_playlist(playlist_name, fields['video_info_list'])
                start_response('303 See Other', (('Location', common.URL_ORIGIN + path),) )
                return local_playlist.get_playlist_page(playlist_name).encode() 

            else:
                start_response('400 Bad Request', ())
                return b'400 Bad Request'

        elif path in ("/post_comment", "/comments"):
            parameters = urllib.parse.parse_qs(query_string)
            post_comment.post_comment(parameters, fields)
            if 'parent_id' in parameters:
                start_response('303 See Other',  (('Location', common.URL_ORIGIN + '/comments?' + query_string),) )
            else:
                try:
                    video_id = fields['video_id'][0]
                except KeyError:
                    video_id = parameters['video_id'][0]
                start_response('303 See Other',  (('Location', common.URL_ORIGIN + '/comments?ctoken=' + comments.make_comment_ctoken(video_id, sort=1)),) )
            return ''

        elif path == "/delete_comment":
            parameters = urllib.parse.parse_qs(query_string)
            code = post_comment.delete_comment(parameters, fields)
            if code == "SUCCESS":
                start_response('303 See Other',  (('Location', common.URL_ORIGIN + '/comment_delete_success'),) )
            else:
                start_response('303 See Other',  (('Location', common.URL_ORIGIN + '/comment_delete_fail'),) )

        else:
            start_response('404 Not Found', ())
            return b'404 Not Found' 

    else:
        start_response('501 Not Implemented', ())
        return b'501 Not Implemented'