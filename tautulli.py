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
"""

import os
import logging
import json
import time
from typing import Any, Generator
from datetime import datetime, timedelta

from requests import Session


logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join("plex-purge.log"), mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(os.path.basename(__file__).removesuffix(".py"))


CONFIG = {}
URL = ""
NOW = datetime.now()
MAX_RATING = 10.0


class Media:
    def __init__(self):
        self.added_at: datetime = NOW
        self.title = ""
        self.sort_title = ""
        self.audience_rating = MAX_RATING
        self.rating = MAX_RATING
        self.file_path = ""
        self.file_size = 0
        self.play_count = 0
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


def get_libraries(session: Session) -> dict[str, str]:
    """Get dict mapping of {'library_name': 'section_id'}."""
    if CONFIG["refresh_libraries"]:
        refresh_response = session.get(
            URL,
            params={
                "cmd": "refresh_libraries_list",
            },
        )
        assert refresh_response.json()["response"]["result"] == "success"
    get_libraries_response = session.get(
        URL,
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
    section_id: str,
) -> Generator[dict[str, Any], None, None]:
    """Get paged library media info."""
    offset = 0
    limit = 50
    while True:
        logging.debug("Fetching media info")
        media_info = session.get(
            URL,
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


def get_docs(session: Session) -> None:
    """View Tautulli docs as dict."""
    logging.debug("Retrieving docs")
    docs_filepath = "tautulli_docs.json"
    docs_response = session.get(
        URL,
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


def main() -> None:
    global URL
    global CONFIG
    start_time = time.time()
    with open(os.path.join("config.json")) as config_file:
        logger.info("Loading config")
        CONFIG = json.load(config_file)

    URL = CONFIG["tautulli_url"]
    api_key = CONFIG["tautulli_api_key"]
    session = Session()
    session.params = {
        "apikey": api_key,
    }
    blacklist: list[Media] = []
    total_media_count = 0
    total_file_size = 0
    if CONFIG["generate_docs"]:
        get_docs(session=session)
        # bail early just to view docs
        return
    libraries = get_libraries(session=session)
    for media_info in get_media_info(
        session=session,
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
        if media.recently_watched:
            logging.info("\tRecently watched, skipping")
            continue
        metadata = get_metadata(session=session, rating_key=media_info["rating_key"])
        if not metadata:
            logger.warning(
                f"\t{media.title} has no metadata which means it was probably deleted. Skipping"
            )
            continue
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
    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f"Execution took {execution_time:.2f} seconds")


if __name__ == "__main__":
    main()
