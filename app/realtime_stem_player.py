# python -m app.realtime_stem_player

from app.stem_player_engine import RealTimeStemPlayer

if __name__ == "__main__":
    app = RealTimeStemPlayer()
    app.run()