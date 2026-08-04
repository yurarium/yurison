#!/usr/bin/env python3
"""magapoke.py: how long the platform says its own series is."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import magapoke  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/magapoke.py"]

# Quoted from the served 将来的に死んでくれ page, shortened to five episodes. The array after the
# key holds positions into the page's value table and the ids follow it, which is the whole reason
# this needs a parser rather than a JSON load.
PAGE = ('"thumbnail_rect_image_url":243,"episode_id_list":244,"total_episode_count":153}'
        ',195,"将来的に死んでくれ","長門知大",'
        '[245,246,247,248,249],152378,154585,156461,158606,160031,'
        '{"status":5,"response_code":6}')


def main(s):
    s.eq(magapoke.episode_ids(PAGE), [152378, 154585, 156461, 158606, 160031],
         "the ids are read from the run that follows, not from the positions")
    s.eq(magapoke.total_episodes(PAGE), 5, "which is how long the platform says the series is")

    # THE FAULT THIS GUARDS. The positions are a numeric array of exactly the right length sitting
    # exactly where a list of ids would be, so taking it gives a believable and wholly wrong answer.
    s.check(245 not in magapoke.episode_ids(PAGE),
            "a position is never returned as an id, however plausible the length looks")

    s.eq(magapoke.episode_ids("<html>nothing to say</html>"), [],
         "a page that lists no episodes lists none")
    s.eq(magapoke.total_episodes("<html>nothing to say</html>"), None,
         "and states no total rather than a total of zero")
    s.eq(magapoke.episode_ids(""), [], "and neither does an empty page")

    s.eq(magapoke.episode_ids('"episode_id_list":244,[245,246],"a string, not a run"'), [],
         "positions with no run behind them are not answered from the positions")
    s.eq(magapoke.episode_ids('[245,246,247],152378,154585,156461'), [],
         "and a page that never names the list is not read for one")

    # A run of a different length is a shape we do not understand, so it yields nothing rather than
    # a guess. This is what a page redesign would look like.
    s.eq(magapoke.episode_ids('"episode_id_list":244,[245,246,247],152378,154585'), [],
         "positions and ids disagreeing on how many there are decides nothing")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
