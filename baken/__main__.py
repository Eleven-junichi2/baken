from dataclasses import dataclass, field
from enum import Enum, auto, StrEnum
import re

from selenium import webdriver
from bs4 import BeautifulSoup
import requests

RACE_SEARCH_DETAIL_SITEURL = r"https://db.netkeiba.com/?pid=race_search_detail"
UPCOMING_AND_RECENT_RACE_LIST_SITEURL = r"https://race.netkeiba.com/top/race_list.html"

class TrackSurface(StrEnum):
    DIRT = "ダ"
    TURF = "芝"


class Weather(Enum):
    SUNNY = auto()
    CLOUDY = auto()
    RAINY = auto()


class TrackCondition(Enum):
    GOOD = auto()  # 良
    FIRM = auto()  # 稍重
    SOFT = auto()  # 重
    HEAVY = auto()  # 不良


@dataclass
class RaceInfo:
    course: str | None = None
    track_surface: TrackSurface | None = None
    distance_in_meters: int | None = None
    track_condition: TrackCondition | None = None
    weather: Weather | None = None
    entries: list["HorseEntry"] = field(default_factory=list)

    # 勝率を計算するメソッド
    def calc_win_rate(self) -> float:
        # 単勝人気順に勝率が定義されたタプル
        win_rate_values_by_popularity = (
            0.328,
            0.19,
            0.133,
            0.092,
            0.075,
            0.055,
            0.038,
            0.031,
            0.022,
            0.012,
            0.013,
            0.009,
            0.007,
            0.0001,
            0.002,
            0.001,
            0.0001,
            0.0001,
        )
        sorted_entries: tuple[HorseEntry] = tuple(
            sorted(self.entries, key=lambda x: x.odds)
        )
        for popularity, (entry, win_rate_by_popularity) in enumerate(
            zip(sorted_entries, win_rate_values_by_popularity)
        ):
            print(
                f"{popularity}番人気の勝率={win_rate_by_popularity} {entry.horse.name} オッズ：{entry.odds} 期待値={entry.odds * win_rate_by_popularity}"
            )


class TrainingCenter(StrEnum):
    RITTO = "栗東"
    MIHO = "美浦"


@dataclass
class Trainer:
    name: str
    training_center: TrainingCenter


@dataclass
class Horse:
    name: str
    age: int
    trainer: Trainer | None = None

@dataclass
class Horses:
    horses: list[Horse] = field(default_factory=list)


@dataclass
class HorseEntry:
    horse: Horse
    post_position: int | None = None
    weight: int | None = None
    odds: float | None = None
    jockey: str | None = None
    factors: dict = field(default_factory=dict)

def cli():
    print(f"レース詳細検索url：{RACE_SEARCH_DETAIL_SITEURL} 直近レース一覧url:{UPCOMING_AND_RECENT_RACE_LIST_SITEURL}")
    print("helpを入力すると 使い方を表示、exitを入力すると 終了")
    print("調べたいレースのnetkeibaでの`race_id`を入力してください")

    while True:
        userinput = input("> ")
        if userinput == "help":
            print("使い方：race_idを調べて入力してください。")
            print("上記urlから出馬表・レース結果等を参照すると、そのページのurlから見つけることができます。")
            print(r"例1：https://db.netkeiba.com/race/レースID/")
            print(r"例2:https://race.netkeiba.com/race/shutuba.html?race_id=レースID")
        if userinput == "exit":
            break
        else:
            # レース結果が存在する（開催済みであり、反映されている）か確認する
            # 正規表現による書式で判定
            # -- TODO --

            # スクレイピング対象テーブルの存在で判定
            race_result_url = fr"https://race.netkeiba.com/race/result.html?race_id={userinput}"
            driver = webdriver.Firefox()
            driver.get(race_result_url)
            soup = BeautifulSoup(driver.page_source.encode("utf-8"), "html.parser")
            driver.quit()
            table = soup.select_one("table#All_Result_Table")
            for row in table.select_one("tbody").select("tr.HorseList"):
                print(row.get_text())
            break



if __name__ == "__main__":
    race_info = RaceInfo()
    cli()