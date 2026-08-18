from src.services.pipeline import run_pipeline, GAMES_TO_SCRAPE

if __name__ == "__main__":
    run_pipeline(download_images_locally=True)
