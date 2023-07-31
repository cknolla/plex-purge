"""
UNFINISHED AND UNUSED: converted to tautulli.py for better view count data

Walk a Plex library and purge it of badly rated/unwatched content
Inspiration from https://gist.github.com/JonnyWong16/d0972e1913941790670708dd99eecf65
"""
import logging
import os
import json
import sqlite3
from datetime import datetime, timedelta

from plexapi.server import PlexServer

# from rotten_tomatoes_client import RottenTomatoesClient

logging.basicConfig(
    format="%(asctime)s:%(levelname)s:%(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join("plex-purge.log"), mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(os.path.basename(__file__).removesuffix(".py"))


def main():
    with open(os.path.join("config.json")) as config_file:
        logger.info("Loading config")
        config = json.load(config_file)
    # Connect to the Plex server
    logger.info(f"Connecting to the Plex server at [{config['plex_url']}]...")
    try:
        plex = PlexServer(config["plex_url"], config["plex_token"])
    except Exception as err:
        logger.error(f"No Plex server found at: {config['plex_url']}\nExiting script.")
        return

    # Get list of movies from the Plex server
    logger.info(
        f"Retrieving a list of movies from the [{config['library_name']}] library in Plex..."
    )
    try:
        movie_library = plex.library.section(config["library_name"])
    except:
        logger.info(f"The [{config['library_name']}] library does not exist in Plex.")
        return

    conn_db = sqlite3.connect(config["plex_database_file"])
    cursor = conn_db.cursor()
    now = datetime.utcnow()

    for plex_movie in movie_library.all():
        if plex_movie.title == "Zootopia":
            logger.info(
                f"Movie: {plex_movie.title}, viewCount: {plex_movie.viewCount}, lastViewedAt: {plex_movie.lastViewedAt}"
            )
            if now - plex_movie.addedAt > timedelta(days=182):
                logger.info(f"added over 6 months ago {plex_movie.addedAt}")
            if plex_movie.audienceRating and plex_movie.audienceRating < 7:
                logger.info(f"audience rating less than 7 {plex_movie.audienceRating}")
            if plex_movie.rating and plex_movie.rating < 7:
                logger.info(f"rating less than 7 {plex_movie.rating}")


if __name__ == "__main__":
    main()
