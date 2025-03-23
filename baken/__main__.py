from dataclasses import dataclass, field
from enum import Enum, auto, StrEnum
import re

import requests
from bs4 import BeautifulSoup


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
class HorseEntry:
    horse: Horse
    post_position: int | None = None
    odds: float | None = None
    jockey: str | None = None
    factors: dict = field(default_factory=dict)


if __name__ == "__main__":
    race_info = RaceInfo()
    netkeiba_shutuba_url = input("netkeiba raceid：")
    if netkeiba_shutuba_url == "":
        netkeiba_shutuba_url = (
            r"https://race.netkeiba.com/race/shutuba.html?race_id=202509010811"
        )
    netkeiba_odds_url = input("netkeiba odds：")
    if netkeiba_odds_url == "":
        netkeiba_odds_url = (
            r"https://race.netkeiba.com/odds/index.html?race_id=202509010811"
        )
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(
        netkeiba_shutuba_url,
        headers=headers,
    )
    response.encoding = response.apparent_encoding
    shutsuba_html_interface = BeautifulSoup(response.text, "html.parser")
    surface_and_distance = (
        shutsuba_html_interface.find("div", class_="RaceData01")
        .find("span")
        .get_text()
        .lstrip()
    )
    race_info.track_surface = TrackSurface(surface_and_distance[:1])
    race_info.distance_in_meters = int(surface_and_distance[1:-1])
    # print(vars(race_info))
    entry_table = shutsuba_html_interface.select("table.Shutuba_Table")
    # print(entry_table[0])
    for row in entry_table[0].select("tr.HorseList"):
        post_position = row.find("td", class_=re.compile(r"Umaban[1-8]")).get_text()
        horse_name = row.find(class_="HorseName").get_text()
        age = int(row.find(class_="Barei").get_text()[1:])
        jockey = row.find(class_="Jockey").get_text().strip()
        horse = Horse(name=horse_name, age=age)
        trainer = row.find(class_="Trainer").get_text()
        traning_center, trainer = trainer[:2], trainer[2:]
        print(post_position, horse_name, age, jockey, traning_center, trainer)

    # for data in horse_datas:
    #     race_info.entries.append(
    #         HorseEntry(horse=Horse(data.find("span", class_="HorseName").text, 1))
    #     )
    #     odds = data.find(class_="Txt_R Popular")
    #     # print(
    #     #     horse_name.text,
    #     #     horse_name.find("a").get("href"),
    #     # )
    # for entry in race_info.entries:
    #     print(entry)
