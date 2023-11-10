#!/usr/bin/env python3.11
"""
Use Tautulli API to get data about media and purge unwanted files.

For an API key, visit Tautulli -> Settings -> Web Interface -> API key
Screening criteria:
    min_age_days: If media was added within this number of days recently, skip it
    recently_watched_days: if media was watched within this number of days recently, skip it
    min_play_count: if media was watched at least this many times total, skip it
    rating_min: if critic rating is at least this high, skip it
    audience_rating_min: if audience rating is at least this high, skip it

https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference
https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference#get_libraries
https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference#get_library_media_info
https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference#get_metadata
https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference#refresh_libraries_list
https://github.com/Tautulli/Tautulli/wiki/Tautulli-API-Reference#get_item_user_stats

Radarr API docs: https://radarr.video/docs/api/
Ombi API docs: https://requests.cknolla.com/swagger
"""

import os
import logging
import json
import time
from http import HTTPStatus
from shutil import rmtree
from typing import Any, Generator
from datetime import datetime, timedelta

from requests import Session


logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(
            os.path.join(
                "logs",
                f"plex-purge_{datetime.now().isoformat().replace(':', '-')}.log",
            ),
            mode="w",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(os.path.basename(__file__).removesuffix(".py"))


CONFIG = {}
NOW = datetime.now()
MAX_RATING = 10.0


class Media:
    def __init__(self):
        self.added_at: datetime = NOW
        self.title: str = ""
        self.sort_title: str = ""
        self.tmdb_id: int = 0
        self.radarr_id: int = 0
        self.audience_rating: float = MAX_RATING
        self.rating: float = MAX_RATING
        self.file_path: str = ""
        self.file_size: int = 0
        self.play_count: int = 0
        self.last_played: datetime = NOW

    def __repr__(self) -> str:
        return f"<Media {self.title}>"

    def __str__(self) -> str:
        return f"{self.title}"

    @property
    def new(self) -> bool:
        """Return whether the media was added recently."""
        return NOW - self.added_at < timedelta(days=CONFIG["min_age_days"])

    @property
    def recently_watched(self) -> bool:
        if not self.last_played:
            return False
        return NOW - self.last_played < timedelta(days=CONFIG["recently_watched_days"])

    @property
    def popular(self) -> bool:
        return self.play_count >= CONFIG["min_play_count"]

    @property
    def well_rated(self) -> bool:
        return (
            self.rating >= CONFIG["rating_min"]
            or self.audience_rating >= CONFIG["audience_rating_min"]
        )


def get_libraries(session: Session, tautulli_url: str) -> dict[str, str]:
    """Get dict mapping of {'library_name': 'section_id'}."""
    if CONFIG["refresh_libraries"]:
        refresh_response = session.get(
            tautulli_url,
            params={
                "cmd": "refresh_libraries_list",
            },
        )
        assert refresh_response.json()["response"]["result"] == "success"
    get_libraries_response = session.get(
        tautulli_url,
        params={
            "cmd": "get_libraries",
        },
    )
    get_libraries_data = get_libraries_response.json()["response"]["data"]
    libraries = {
        library["section_name"]: library["section_id"] for library in get_libraries_data
    }
    return libraries


def get_media_info(
    session: Session,
    tautulli_url: str,
    section_id: str,
) -> Generator[dict[str, Any], None, None]:
    """Get paged library media info."""
    offset = 0
    limit = 50
    while True:
        logging.debug("Fetching media info")
        media_info = session.get(
            tautulli_url,
            params={
                "cmd": "get_library_media_info",
                "section_id": section_id,
                "start": offset,
                "length": limit,
                # refresh cache on first query only
                "refresh": "true" if offset == 0 else "false",
            },
        )
        media_info_data = media_info.json()["response"]["data"]["data"]
        if not media_info_data:
            return
        for media_info in media_info_data:
            yield media_info
        offset += limit


def get_metadata(
    session: Session, tautulli_url: str, rating_key: str
) -> dict[str, Any]:
    """Get a single item's metadata."""
    logging.debug("Fetching metadata")
    get_metadata_response = session.get(
        tautulli_url,
        params={
            "cmd": "get_metadata",
            "rating_key": rating_key,
        },
    )
    metadata = get_metadata_response.json()["response"]["data"]
    return metadata


def get_docs(session: Session, tautulli_url: str) -> None:
    """View Tautulli docs as dict."""
    logging.debug("Retrieving docs")
    docs_filepath = "tautulli_docs.json"
    docs_response = session.get(
        tautulli_url,
        params={
            "cmd": "docs",
        },
    )
    logging.info(f"Writing Tautulli docs to {docs_filepath}")
    with open(docs_filepath, "w") as file:
        json.dump(
            docs_response.json()["response"]["data"],
            file,
            indent=2,
        )


def remove_from_ombi(session: Session, ombi_url: str, blacklist: list[Media]):
    """Remove requests from ombi to not leave dangling pointers."""
    in_ombi: list[str] = []
    errors_in_ombi: list[str] = []
    not_in_ombi: list[str] = []
    requests: list[dict] = session.get(
        f"{ombi_url}/Request/movie",
    ).json()
    keyed_requests = {request["theMovieDbId"]: request["id"] for request in requests}
    for media in blacklist:
        if media.tmdb_id not in keyed_requests:
            not_in_ombi.append(media.title)
            continue
        delete_response = session.delete(
            f"{ombi_url}/Request/movie/{keyed_requests[media.tmdb_id]}"
        )
        if delete_response.status_code != HTTPStatus.OK:
            errors_in_ombi.append(media.title)
        else:
            in_ombi.append(media.title)
    if in_ombi:
        logger.info(f"The following were removed from Ombi: {in_ombi}")
    if errors_in_ombi:
        logger.error(
            f"The following had errors when trying to remove from Ombi: {errors_in_ombi}"
        )
    if not_in_ombi:
        logger.warning(f"The following were not found in Ombi: {not_in_ombi}")


def remove_from_radarr(
    session: Session, radarr_url: str, blacklist: list[Media]
) -> list[Media]:
    """Unmonitor movies in Radarr."""
    in_radarr: list[Media] = []
    not_in_radarr: list[Media] = []
    for media in blacklist:
        movie_details: dict = session.get(
            f"{radarr_url}/movie",
            params={
                "tmdbid": media.tmdb_id,
            },
        ).json()
        if len(movie_details) > 0:
            media.radarr_id = movie_details[0]["id"]
            in_radarr.append(media)
        else:
            not_in_radarr.append(media)
    if not_in_radarr:
        logging.warning(
            f"The following were not in Radarr and can't be deleted through it:"
            f" {[media.title for media in not_in_radarr]}"
        )
    if in_radarr:
        logger.info(
            f"Deleting the following from Radarr and filesystem:"
            f" {[media.title for media in in_radarr]}"
        )
        delete_response = session.delete(
            f"{radarr_url}/movie/editor",
            json={
                "movieIds": [media.radarr_id for media in blacklist if media.radarr_id],
                "deleteFiles": True,
            },
        )
        if delete_response.status_code != HTTPStatus.OK:
            logger.error(f"Error deleting from Radarr: {delete_response.json()}")
    return not_in_radarr


def direct_delete(medias: list[Media]):
    """If it couldn't be gracefully removed via Radarr, use file system to delete."""
    for media in medias:
        if os.path.exists(media.file_path):
            logger.info(f"Directly deleting {media.title} at {media.file_path}")
            os.remove(media.file_path)


def empty_trash(trash_dirs: list[str]):
    """Delete trash folders on mounted drive."""
    logger.info(f"Removing trash dirs: {trash_dirs}")
    for trash_dir in trash_dirs:
        if os.path.exists(trash_dir):
            rmtree(trash_dir)


def main() -> None:
    global CONFIG
    start_time = time.time()
    with open(os.path.join("config.json")) as config_file:
        logger.info("Loading config")
        CONFIG = json.load(config_file)
    if CONFIG["trash_dirs"]:
        if (
            input(
                f"trash_dirs are currently: "
                f"{[directory for directory in CONFIG['trash_dirs']]}."
                f"\nThese will be completely deleted. Ok? (y/n)"
            ).lower()
            != "y"
        ):
            return
    tautulli_url = CONFIG["tautulli_url"]
    tautulli_api_key = CONFIG["tautulli_api_key"]
    radarr_url = CONFIG["radarr_url"]
    radarr_api_key = CONFIG["radarr_api_key"]
    ombi_url = CONFIG["ombi_url"]
    ombi_api_key = CONFIG["ombi_api_key"]
    tautulli_session = Session()
    tautulli_session.params = {
        "apikey": tautulli_api_key,
    }
    radarr_session = Session()
    radarr_session.params = {
        "apikey": radarr_api_key,
    }
    ombi_session = Session()
    ombi_session.headers = {
        "ApiKey": ombi_api_key,
    }
    blacklist: list[Media] = []
    total_media_count = 0
    total_file_size = 0
    if CONFIG["generate_docs"]:
        get_docs(
            session=tautulli_session,
            tautulli_url=tautulli_url,
        )
        # bail early just to view docs
        return
    libraries = get_libraries(
        session=tautulli_session,
        tautulli_url=tautulli_url,
    )
    for media_info in get_media_info(
        session=tautulli_session,
        tautulli_url=tautulli_url,
        section_id=libraries[CONFIG["library_name"]],
    ):
        media = Media()
        total_media_count += 1
        media.title = media_info["title"]
        media.sort_title = media_info["sort_title"]
        logging.info(f"Examining {media.title}")
        if media.title in CONFIG["whitelist"]:
            logging.info("\tIn whitelist, skipping")
            continue
        media.added_at = datetime.fromtimestamp(int(media_info["added_at"]))
        if media.new:
            logging.info("\tAdded recently, skipping")
            continue
        media.play_count = media_info["play_count"] or 0
        if media.popular:
            logging.info("\tPopular, skipping")
            continue
        media.last_played = (
            datetime.fromtimestamp(media_info["last_played"])
            if media_info["last_played"]
            else None
        )
        # if media.recently_watched:
        #     logging.info("\tRecently watched, skipping")
        #     continue
        metadata = get_metadata(
            session=tautulli_session,
            tautulli_url=tautulli_url,
            rating_key=media_info["rating_key"],
        )
        if not metadata:
            logger.warning(
                f"\t{media.title} has no metadata which means it was probably deleted. Skipping"
            )
            continue
        for guid in metadata["guids"]:
            if guid.startswith("tmdb"):
                media.tmdb_id = int(guid.removeprefix("tmdb://"))
        media.rating = float(metadata["rating"]) if metadata["rating"] else MAX_RATING
        media.audience_rating = (
            float(metadata["audience_rating"])
            if metadata["audience_rating"]
            else MAX_RATING
        )
        if media.well_rated:
            logging.info("\tWell-rated, skipping")
            continue
        media.file_path = metadata["media_info"][0]["parts"][0]["file"]
        media.file_size = int(media_info["file_size"])
        logging.warning(f"\t{media.title} has met all the criteria to be blacklisted")
        blacklist.append(media)
        total_file_size += media.file_size

    logging.info(
        "Blacklist: "
        + json.dumps(
            [item.title for item in sorted(blacklist, key=lambda x: x.sort_title)],
            indent=2,
        )
    )
    logging.info(f"Total media count: {total_media_count}")
    logging.info(
        f"Blacklist size: {len(blacklist)}, {(len(blacklist)/total_media_count * 100):.2f}%"
    )
    logging.info(f"Total file size to clear: {total_file_size/1_000_000_000:.2f}GB")
    remove_from_ombi(
        session=ombi_session,
        ombi_url=ombi_url,
        blacklist=blacklist,
    )
    not_in_radarr = remove_from_radarr(
        session=radarr_session,
        radarr_url=radarr_url,
        blacklist=blacklist,
    )
    if not_in_radarr:
        direct_delete(medias=not_in_radarr)
    empty_trash(CONFIG["trash_dirs"])
    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f"Execution took {execution_time:.2f} seconds")


if __name__ == "__main__":
    main()
