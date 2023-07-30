"""
Walk a Plex library and purge it of badly rated/unwatched content
Inspiration from https://gist.github.com/JonnyWong16/d0972e1913941790670708dd99eecf65
"""
import logging
import re
import sqlite3
from plexapi.server import PlexServer
# from rotten_tomatoes_client import RottenTomatoesClient

logger = logging.getLogger(__file__)


PLEX_URL = "https://plex.kansai:32400"
PLEX_TOKEN = "xxxxxxxxxx"
MOVIE_LIBRARY_NAME = "Movies"
PLEX_DATABASE_FILE = "com.plexapp.plugins.library.db"


def main():
    # Connect to the Plex server
    logger.info(f"Connecting to the Plex server at '{PLEX_URL}'...")
    try:
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    except:
        logger.error(f"No Plex server found at: {PLEX_URL}\nExiting script.")
        return

    # Get list of movies from the Plex server
    logger.info(
        f"Retrieving a list of movies from the '{MOVIE_LIBRARY_NAME}' library in Plex..."
    )
    try:
        movie_library = plex.library.section(MOVIE_LIBRARY_NAME)
    except:
        logger.info(f"The '{MOVIE_LIBRARY_NAME}' library does not exist in Plex.")
        return


if __name__ == '__main__':
   main()



