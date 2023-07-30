"""
Use Tautulli API to get data about media and purge unwanted files.

https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference
https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference#get_libraries
https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference#get_library_media_info
https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference#get_metadata
"""

import os
import logging
import json
from typing import Any, Generator

import requests
from requests import Session


logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(message)s",
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler(
            os.path.join("plex-purge.log"), mode="w"
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(os.path.basename(__file__).removesuffix(".py"))


URL = ""


def get_libraries(session: Session) -> dict[str, str]:
    """Get dict mapping of {'library_name': 'section_id'}."""
    get_libraries_response = session.get(
        URL,
        params={
            "cmd": "get_libraries",
        },
    )
    get_libraries_data = get_libraries_response.json()["response"]["data"]
    libraries = {
        library["section_name"]: library["section_id"]
        for library in get_libraries_data
    }
    return libraries


def get_media_info(session: Session, section_id: str) -> Generator[dict[str, Any], None, None]:
    """Get paged library media info."""
    offset = 0
    limit = 25
    while True:
        logging.debug("Fetching media info")
        media_info = session.get(
            URL,
            params={
                "cmd": "get_library_media_info",
                "section_id": section_id,
                "start": offset,
                "length": limit,
            },
        )
        media_info_data = media_info.json()["response"]["data"]["data"]
        if not media_info_data:
            return
        for media_info in media_info_data:
            yield media_info
        offset += 1
    # [{'section_id': 1, 'section_type': 'movie', 'added_at': '1471813628', 'media_type': 'movie', 'rating_key': '9660', 'parent_rating_key': '', 'grandparent_rating_key': '', 'title': 'Zootopia', 'sort_title': 'Zootopia', 'year': '2016', 'media_index': '', 'parent_media_index': '', 'thumb': '/library/metadata/9660/thumb/1689479203', 'container': 'mkv', 'bitrate': '7692', 'video_codec': 'h264', 'video_resolution': '720', 'video_framerate': '24p', 'audio_codec': 'dca', 'audio_channels': '6', 'file_size': '6273349739', 'last_played': 1671398122, 'play_count': 16}]


def get_metadata(session: Session, rating_key: str) -> dict[str, Any]:
    """Get a single item's metadata."""
    logging.debug("Fetching metadata")
    get_metadata_response = session.get(
        URL,
        params={
            "cmd": "get_metadata",
            "rating_key": rating_key,
        },
    )
    metadata = get_metadata_response.json()["response"]["data"]
    return metadata
    # {'media_type': 'movie', 'section_id': '1', 'library_name': 'Movies', 'rating_key': '9660', 'parent_rating_key': '', 'grandparent_rating_key': '', 'title': 'Zootopia', 'parent_title': '', 'grandparent_title': '', 'original_title': '', 'sort_title': '', 'edition_title': '', 'media_index': '', 'parent_media_index': '', 'studio': 'Walt Disney Animation Studios', 'content_rating': 'PG', 'summary': 'From the largest elephant to the smallest shrew, the city of Zootopia is a mammal metropolis where various animals live and thrive. When Judy Hopps becomes the first rabbit to join the police force, she quickly learns how tough it is to enforce the law. Determined to prove herself, Judy jumps at the opportunity to solve a mysterious case. Unfortunately, that means working with Nick Wilde, a wily fox who makes her job even harder.', 'tagline': 'Welcome to the urban jungle.', 'rating': '9.8', 'rating_image': 'rottentomatoes://image.rating.ripe', 'audience_rating': '9.2', 'audience_rating_image': 'rottentomatoes://image.rating.upright', 'user_rating': '', 'duration': '6524685', 'year': '2016', 'parent_year': '', 'grandparent_year': '', 'thumb': '/library/metadata/9660/thumb/1689479203', 'parent_thumb': '', 'grandparent_thumb': '', 'art': '/library/metadata/9660/art/1689479203', 'banner': '', 'originally_available_at': '2016-02-10', 'added_at': '1471813628', 'updated_at': '1689479203', 'last_viewed_at': '1472074173', 'guid': 'plex://movie/5d776ad596b655001fdfb0f3', 'parent_guid': '', 'grandparent_guid': '', 'directors': ['Byron Howard', 'Rich Moore'], 'writers': ['Jim Reardon', 'Byron Howard', 'Rich Moore', 'Phil Johnston', 'Jennifer Lee'], 'actors': ['Jason Bateman', 'Ginnifer Goodwin', 'Idris Elba', 'Jenny Slate', 'Nate Torrence', 'Bonnie Hunt', 'Don Lake', 'Tommy Chong', 'J.K. Simmons', 'Octavia Spencer', 'Alan Tudyk', 'Shakira', 'Raymond S. Persi', 'Della Saba', 'Maurice LaMarche', 'Phil Johnston', 'Fuschia!', 'John DiMaggio', 'Katie Lowes', 'Gita Reddy', 'Jesse Corti', 'Tommy Lister Jr.', 'Josh Dallas', 'Leah Latham', 'Rich Moore', 'Kath Soucie', 'Peter Mansbridge', 'Byron Howard', 'Jared Bush', 'Mark Rhino Smith', 'Josie Trinidad', 'John Lavelle', 'Kristen Bell', 'Evelyn Wilson Bresee', 'Hewitt Bush', 'Jill Cordes', 'Madeleine Curry', 'Terri Douglas', 'Melissa Goodwin Shepherd', 'Zach King', 'Dave Kohut', 'Jeremy Milton', 'Pace Paulsen', 'Fabienne Rawley', 'Bradford Simonsen', 'Claire K. Smith', 'Jackson Stein', 'David A. Thibodeau', 'Hannah G. Williams', 'Daveed Diggs'], 'genres': ['Animation', 'Adventure', 'Family', 'Comedy', 'Crime', 'Mystery'], 'labels': [], 'collections': [], 'guids': ['imdb://tt2948356', 'tmdb://269149', 'tvdb://77'], 'markers': [{'id': 106344, 'type': 'credits', 'start_time_offset': 5799982, 'end_time_offset': 6524685, 'first': True, 'final': True}], 'parent_guids': [], 'grandparent_guids': [], 'full_title': 'Zootopia', 'children_count': 0, 'live': 0, 'media_info': [{'id': '65233', 'container': 'mkv', 'bitrate': '7692', 'height': '536', 'width': '1280', 'aspect_ratio': '2.35', 'video_codec': 'h264', 'video_resolution': '720', 'video_full_resolution': '720p', 'video_framerate': '24p', 'video_profile': 'high', 'audio_codec': 'dca', 'audio_channels': '6', 'audio_channel_layout': '5.1', 'audio_profile': 'dts', 'optimized_version': 0, 'channel_call_sign': '', 'channel_identifier': '', 'channel_thumb': '', 'parts': [{'id': '66144', 'file': '/mnt/ds1019/media/videos/movies/Zootopia (2016)/Zootopia.mkv', 'file_size': '6273349739', 'indexes': 0, 'streams': [{'id': '149995', 'type': '1', 'video_codec': 'h264', 'video_codec_level': '42', 'video_bitrate': '6156', 'video_bit_depth': '8', 'video_chroma_subsampling': '4:2:0', 'video_color_primaries': 'bt709', 'video_color_range': 'tv', 'video_color_space': 'bt709', 'video_color_trc': 'bt709', 'video_dynamic_range': 'SDR', 'video_frame_rate': '23.976', 'video_ref_frames': '4', 'video_height': '536', 'video_width': '1280', 'video_language': '', 'video_language_code': '', 'video_profile': 'high', 'video_scan_type': 'progressive', 'selected': 0}, {'id': '149996', 'type': '2', 'audio_codec': 'dca', 'audio_bitrate': '1536', 'audio_bitrate_mode': '', 'audio_channels': '6', 'audio_channel_layout': '5.1(side)', 'audio_sample_rate': '48000', 'audio_language': 'English', 'audio_language_code': 'eng', 'audio_profile': 'dts', 'selected': 1}, {'id': '302272', 'type': '3', 'subtitle_codec': 'srt', 'subtitle_container': '', 'subtitle_format': 'srt', 'subtitle_forced': 0, 'subtitle_location': 'external', 'subtitle_language': '', 'subtitle_language_code': '', 'selected': 0}], 'selected': 0}]}]}


def main():
    global URL
    with open(os.path.join("config.json")) as config_file:
        logger.info("Loading config")
        config = json.load(config_file)

    URL = config["tautulli_url"]
    api_key = config["tautulli_api_key"]
    session = Session()
    session.params = {
        "apikey": api_key,
    }
    libraries = get_libraries(session=session)
    for media_info in get_media_info(session=session, section_id=libraries["Movies"]):
        metadata = get_metadata(session=session, rating_key=media_info["rating_key"])


if __name__ == "__main__":
    main()


